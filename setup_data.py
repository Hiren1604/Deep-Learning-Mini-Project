"""Download the original public dataset and reproduce its FAISS row mapping."""
from pathlib import Path
import re
import time
import urllib.request
import zipfile

import faiss
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
URL = "https://www.kaggle.com/api/v1/datasets/download/paramaggarwal/fashion-product-images-small"


def main():
    DATA.mkdir(exist_ok=True)
    archive = DATA / "fashion-product-images-small.zip"
    if not (DATA / ".extracted").exists():
        if not archive.exists():
            temporary = archive.with_suffix(".part")
            print("Downloading Fashion Product Images (Small) from Kaggle...", flush=True)
            request = urllib.request.Request(URL, headers={"User-Agent": "product-search-local-setup/1.0"})
            with urllib.request.urlopen(request, timeout=60) as response, temporary.open("wb") as output:
                downloaded = 0
                last_report = time.monotonic()
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
                    downloaded += len(chunk)
                    if time.monotonic() - last_report > 10:
                        print(f"Downloaded {downloaded / 1024**2:.0f} MiB", flush=True)
                        last_report = time.monotonic()
            if not zipfile.is_zipfile(temporary):
                raise RuntimeError("Kaggle did not return a ZIP archive. Download the dataset manually and extract it into data/.")
            temporary.replace(archive)
        print("Extracting dataset...", flush=True)
        with zipfile.ZipFile(archive) as zipped:
            # The archive also contains a duplicate myntradataset/ tree.
            # Accept only these exact paths, excluding traversal and duplicates.
            members = [member for member in zipped.infolist()
                       if member.filename == "styles.csv"
                       or re.fullmatch(r"images/[0-9]+\.jpg", member.filename)]
            for i, member in enumerate(members):
                destination = DATA / member.filename
                if not destination.exists() or destination.stat().st_size != member.file_size:
                    zipped.extract(member, DATA)
                if (i + 1) % 5000 == 0:
                    print(f"Extracted {i + 1} files", flush=True)
        (DATA / ".extracted").touch()

    # Notebook 3 removes invalid images before generating both indexes.
    # Preserve CSV order and reproduce that filter to keep product IDs aligned.
    products = pd.read_csv(DATA / "styles.csv", on_bad_lines="skip")
    valid = []
    print(f"Validating {len(products)} product images...", flush=True)
    for i, product_id in enumerate(products["id"]):
        path = DATA / "images" / f"{product_id}.jpg"
        try:
            with Image.open(path) as image:
                image.verify()
            valid.append(True)
        except (OSError, ValueError):
            valid.append(False)
        if (i + 1) % 5000 == 0:
            print(f"Validated {i + 1} images", flush=True)
    products = products.loc[valid].reset_index(drop=True)
    for name in ("text_index.faiss", "image_index.faiss"):
        index = faiss.read_index(str(ROOT / "indexes" / name))
        if index.ntotal != len(products):
            raise RuntimeError(f"{name} has {index.ntotal} rows but dataset has {len(products)} valid products; do not use mismatched metadata.")
    products["images_path"] = products["id"].map(lambda product_id: str(DATA / "images" / f"{product_id}.jpg"))
    products.to_csv(DATA / "cleaned_products.csv", index=False)
    print(f"Ready: {len(products)} products matched to both indexes.", flush=True)


if __name__ == "__main__":
    main()

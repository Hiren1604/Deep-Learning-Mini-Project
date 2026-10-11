"""Get original photo URLs from the full version of the current Kaggle dataset."""
import csv
import io
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parent
URL = "https://www.kaggle.com/api/v1/datasets/download/paramaggarwal/fashion-product-images-dataset/fashion-dataset%2Fimages.csv"


def main():
    path = ROOT / "data" / "image_links.csv"
    if path.exists():
        print(f"Image URL mapping already exists: {path}")
        return
    with urllib.request.urlopen(URL, timeout=30) as response:
        content = response.read(15 * 1024 * 1024)
    if zipfile.is_zipfile(io.BytesIO(content)):
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            name = next(name for name in archive.namelist() if name.endswith("images.csv"))
            content = archive.read(name)
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"))))
    if not rows or not {"filename", "link"} <= rows[0].keys():
        raise RuntimeError("Kaggle did not return the expected image URL CSV.")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".part")
    temporary.write_bytes(content)
    temporary.replace(path)
    print(f"Ready: original image URLs for {len(rows)} products. Images will download when viewed.")


if __name__ == "__main__":
    main()

"""Fetch original catalog photos for display while preserving search inputs."""
import csv
import io
from pathlib import Path
from threading import Lock
from urllib.parse import urlparse, urlunparse

from PIL import Image
import requests


class ProductImages:
    def __init__(self, project_dir):
        self.data_dir = Path(project_dir) / "data"
        self.cache_dir = self.data_dir / "images_hd"
        self.links_path = self.data_dir / "image_links.csv"
        self.links = None
        self.lock = Lock()
        self.failed = set()

    def load_links(self):
        if self.links is None:
            links = {}
            if self.links_path.exists():
                with self.links_path.open(encoding="utf-8-sig", newline="") as file:
                    for row in csv.DictReader(file):
                        filename = row.get("filename", "")
                        if filename.endswith(".jpg") and filename[:-4].isdigit():
                            parsed = urlparse(row.get("link", ""))
                            if parsed.hostname == "assets.myntassets.com" and parsed.scheme in ("http", "https"):
                                links[int(filename[:-4])] = urlunparse(parsed._replace(scheme="https"))
            self.links = links

    @staticmethod
    def validate(content):
        with Image.open(io.BytesIO(content)) as image:
            if image.format != "JPEG" or min(image.size) < 200:
                raise ValueError("Original photo must be a JPEG at least 200 pixels on each side.")
            image.verify()

    def get(self, product_id):
        fallback = self.data_dir / "images" / f"{product_id}.jpg"
        if not fallback.is_file():
            raise FileNotFoundError(f"Unknown product image: {product_id}")
        cached = self.cache_dir / f"{product_id}.jpg"
        if cached.is_file():
            return cached
        with self.lock:
            self.load_links()
        if product_id in self.failed or product_id not in self.links:
            return fallback
        try:
            response = requests.get(self.links[product_id], timeout=(4, 8), stream=True)
            with response:
                response.raise_for_status()
                content = bytearray()
                for chunk in response.iter_content(chunk_size=65536):
                    content.extend(chunk)
                    if len(content) > 10 * 1024 * 1024:
                        raise ValueError("Original image exceeds the cache size limit.")
            self.validate(content)
            # Keep original JPEG bytes; no generated details or image alteration.
            with self.lock:
                self.cache_dir.mkdir(parents=True, exist_ok=True)
                if not cached.exists():
                    temporary = cached.with_suffix(".part")
                    temporary.write_bytes(content)
                    temporary.replace(cached)
            return cached
        except (requests.RequestException, OSError, ValueError):
            self.failed.add(product_id)
            return fallback

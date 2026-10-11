import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from PIL import Image
import requests

from src.product_images import ProductImages


class ProductImageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "data/images").mkdir(parents=True)
        self.fallback = self.root / "data/images/15970.jpg"
        Image.new("RGB", (60, 80), "white").save(self.fallback)
        (self.root / "data/image_links.csv").write_text(
            "filename,link\n15970.jpg,http://assets.myntassets.com/example.jpg\n",
            encoding="utf-8",
        )
        buffer = io.BytesIO()
        Image.new("RGB", (600, 800), "blue").save(buffer, format="JPEG")
        self.original = buffer.getvalue()
        self.store = ProductImages(self.root)

    def response(self, content):
        response = MagicMock()
        response.iter_content.return_value = [content]
        return response

    @patch("src.product_images.requests.get")
    def test_downloads_and_caches_original_without_changing_search_image(self, get):
        get.return_value = self.response(self.original)
        original_thumbnail = self.fallback.read_bytes()
        result = self.store.get(15970)
        self.assertEqual(result.read_bytes(), self.original)
        self.assertEqual(self.fallback.read_bytes(), original_thumbnail)
        self.assertEqual(self.store.get(15970), result)
        get.assert_called_once()
        self.assertTrue(get.call_args.args[0].startswith("https://"))

    @patch("src.product_images.requests.get", side_effect=requests.Timeout)
    def test_unreachable_original_falls_back_and_does_not_retry_every_view(self, get):
        self.assertEqual(self.store.get(15970), self.fallback)
        self.assertEqual(self.store.get(15970), self.fallback)
        get.assert_called_once()

    @patch("src.product_images.requests.get")
    def test_invalid_download_falls_back_without_caching(self, get):
        get.return_value = self.response(b"<html>not an image</html>")
        self.assertEqual(self.store.get(15970), self.fallback)
        self.assertFalse((self.root / "data/images_hd/15970.jpg").exists())

    @patch("src.product_images.requests.get")
    def test_missing_mapping_uses_existing_thumbnail(self, get):
        (self.root / "data/image_links.csv").unlink()
        self.assertEqual(self.store.get(15970), self.fallback)
        get.assert_not_called()

    @patch("src.product_images.requests.get")
    def test_unknown_product_is_rejected_without_network_request(self, get):
        with self.assertRaises(FileNotFoundError):
            self.store.get(123456)
        get.assert_not_called()


if __name__ == "__main__":
    unittest.main()

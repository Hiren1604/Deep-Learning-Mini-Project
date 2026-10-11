import os
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from src.catalog import ProductCatalog


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / "data").mkdir()
        self.path = self.root / "data" / "product_details.csv"
        self.product = pd.Series({"id": 15970, "productDisplayName": "Blue Shirt", "articleType": "Shirts", "gender": "Men", "baseColour": "Blue", "usage": float("nan")})
        self.catalog = ProductCatalog(self.root)

    def write_details(self, rows):
        pd.DataFrame(rows).to_csv(self.path, index=False)

    def test_missing_fields_are_honest_and_search_link_is_encoded(self):
        details = self.catalog.describe(self.product)
        self.assertEqual(details["price_display"], "Price unavailable")
        self.assertIsNone(details["price"])
        self.assertIsNone(details["product_url"])
        self.assertEqual(details["type"], "Shirts")
        self.assertIn("Colour: Blue", details["description"])
        self.assertNotIn("nan", details["description"])
        self.assertIn("q=Blue+Shirt+buy+price", details["shopping_search_url"])

    def test_retailer_fields_join_by_id_not_row_position(self):
        self.write_details([
            {"id": 39386, "price": 999, "currency": "INR"},
            {"id": 15970, "price": 1499, "currency": "INR", "description": "Catalog description", "product_url": "https://example.com/products/15970"},
        ])
        details = self.catalog.describe(self.product)
        self.assertEqual(details["price_display"], "INR 1,499.00")
        self.assertEqual(details["description"], "Catalog description")
        self.assertEqual(details["description_source"], "catalog")
        self.assertEqual(details["product_url"], "https://example.com/products/15970")

    def test_zero_price_is_shown_but_unknown_currency_is_not_assumed(self):
        self.write_details([{"id": 15970, "price": 0, "currency": "INR"}])
        self.assertEqual(self.catalog.describe(self.product)["price_display"], "INR 0.00")
        self.path.unlink()
        self.catalog.describe(self.product)
        self.write_details([{"id": 15970, "price": 1499}])
        self.assertEqual(self.catalog.describe(self.product)["price_display"], "Price unavailable")

    def test_updates_and_removal_refresh_details(self):
        self.catalog.describe(self.product)
        self.write_details([{"id": 15970, "price": 100, "currency": "INR"}])
        self.assertEqual(self.catalog.describe(self.product)["price"], 100)
        previous = self.path.stat().st_mtime_ns
        self.write_details([{"id": 15970, "price": 200, "currency": "INR"}])
        os.utime(self.path, ns=(previous + 1_000_000_000, previous + 1_000_000_000))
        self.assertEqual(self.catalog.describe(self.product)["price"], 200)
        self.path.unlink()
        self.assertIsNone(self.catalog.describe(self.product)["price"])

    def test_invalid_prices_and_urls_are_not_presented_as_valid(self):
        self.write_details([{"id": 15970, "price": -1, "currency": "INR", "product_url": "javascript:alert(1)"}])
        details = self.catalog.describe(self.product)
        self.assertIsNone(details["price"])
        self.assertIsNone(details["product_url"])

    def test_duplicate_product_ids_are_rejected(self):
        self.write_details([{"id": 15970}, {"id": 15970}])
        with self.assertRaisesRegex(ValueError, "unique product id"):
            self.catalog.describe(self.product)


if __name__ == "__main__":
    unittest.main()

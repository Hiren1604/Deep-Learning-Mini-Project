"""Product presentation data, with optional retailer details keyed by product ID."""
from pathlib import Path
from urllib.parse import urlencode, urlparse
import math

import pandas as pd


def value(row, field):
    item = row.get(field)
    if item is None or pd.isna(item):
        return None
    return str(item).strip() or None


class ProductCatalog:
    def __init__(self, project_dir):
        self.details_path = Path(project_dir) / "data" / "product_details.csv"
        self.details = {}
        self.modified = None

    def load_details(self):
        modified = self.details_path.stat().st_mtime_ns if self.details_path.exists() else None
        if modified == self.modified:
            return
        self.details = {}
        if modified is not None:
            data = pd.read_csv(self.details_path)
            if "id" not in data.columns or data["id"].duplicated().any():
                raise ValueError("product_details.csv must contain one row per unique product id.")
            self.details = {int(row["id"]): row for _, row in data.iterrows()}
        self.modified = modified

    def describe(self, product):
        self.load_details()
        product_id = int(product["id"])
        extra = self.details.get(product_id, {})
        name = value(product, "productDisplayName") or "Unnamed product"
        attributes = {
            "type": value(product, "articleType"),
            "catalog_category": value(product, "masterCategory"),
            "subcategory": value(product, "subCategory"),
            "gender": value(product, "gender"),
            "color": value(product, "baseColour"),
            "usage": value(product, "usage"),
            "season": value(product, "season"),
        }
        description = value(extra, "description")
        description_source = "catalog" if description else "attributes"
        if not description:
            facts = [f"{label}: {attributes[field]}" for label, field in
                     (("Product type", "type"), ("For", "gender"), ("Colour", "color"),
                      ("Use", "usage"), ("Season", "season")) if attributes[field]]
            description = ". ".join(facts) + "." if facts else "Description unavailable."
        price = None
        raw_price = value(extra, "price")
        if raw_price:
            try:
                parsed = float(raw_price)
                if math.isfinite(parsed) and parsed >= 0:
                    price = parsed
            except ValueError:
                pass
        currency = value(extra, "currency")
        price_display = f"{currency.upper()} {price:,.2f}" if price is not None and currency else "Price unavailable"
        product_url = value(extra, "product_url")
        if product_url:
            parsed_url = urlparse(product_url)
            if parsed_url.scheme not in ("https", "http") or not parsed_url.netloc:
                product_url = None
        return {
            **attributes,
            "description": description,
            "description_source": description_source,
            "price": price,
            "currency": currency,
            "price_display": price_display,
            "product_url": product_url,
            "shopping_search_url": "https://www.google.com/search?" + urlencode({"q": f"{name} buy price"}),
        }

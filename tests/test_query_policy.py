import unittest

import pandas as pd

from src.query_policy import CatalogQueryPolicy


class QueryPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = CatalogQueryPolicy(pd.DataFrame({
            "articleType": ["Sports Shoes", "Shirts", "Watches", "Lipstick", "Laptop Bag"],
            "productDisplayName": ["Nike Women Shoes", "Roadster Men Shirt", "Casio Watch", "Lakme Lipstick", "Puma Laptop Bag"],
            "gender": ["Women", "Men", "Unisex", "Women", "Unisex"],
            "baseColour": ["Black", "Blue", "Silver", "Red", "Black"],
            "usage": ["Sports", "Casual", "Casual", "Party", "Casual"],
            "season": ["Summer"] * 5,
        }))

    def test_supported_products_attributes_and_brands(self):
        for query in ("shoes women", "women’s sneakers", "blue shirt", "red lipstick", "laptop bag", "blue", "Nike", "black Nike", "something comfortable for running", "summer outfit"):
            with self.subTest(query=query):
                self.assertTrue(self.policy.supports(query))

    def test_unrelated_queries_do_not_force_product_matches(self):
        for query in ("what is the weather today", "write python code", "tell me a joke", "pizza recipe", "bitcoin price", "capital of India", "laptop", "gaming computer", "asdfghjkl", "what is deep learning", "explain blue skies", "", "123456"):
            with self.subTest(query=query):
                self.assertFalse(self.policy.supports(query))


if __name__ == "__main__":
    unittest.main()

import unittest
from unittest.mock import Mock

import faiss
import numpy as np
import pandas as pd

from src.pipeline import ProductSearchPipeline


class SearchFilterTests(unittest.TestCase):
    def make_pipeline(self, genders):
        pipeline = ProductSearchPipeline(".")
        pipeline.metadata = pd.DataFrame({
            "gender": genders,
            "productDisplayName": [f"Product {i} Shoes" for i in range(len(genders))],
            "articleType": ["Sports Shoes"] * len(genders),
        })
        # The first products are deliberately much closer to the query.
        vectors = np.column_stack((np.arange(len(genders), 0, -1), np.zeros(len(genders)))).astype("float32")
        pipeline.text_index = faiss.IndexFlatIP(2)
        pipeline.image_index = faiss.IndexFlatIP(2)
        pipeline.text_index.add(vectors)
        pipeline.image_index.add(vectors)
        pipeline.load_models = Mock()
        pipeline.embed_text = Mock(return_value=np.array([1, 0], dtype="float32"))
        pipeline.embed_image = Mock(return_value=np.array([1, 0], dtype="float32"))
        return pipeline

    def test_audience_detection_uses_whole_words_and_handles_variants(self):
        for query in ("shoes women", "women's shoes", "WOMENS shoes", "female trainers", "ladies shoes"):
            with self.subTest(query=query):
                self.assertEqual(ProductSearchPipeline.detect_query_genders(query), {"Women"})
        self.assertEqual(ProductSearchPipeline.detect_query_genders("men’s shoes"), {"Men"})
        self.assertEqual(ProductSearchPipeline.detect_query_genders("boys and girls shoes"), {"Boys", "Girls"})
        self.assertEqual(ProductSearchPipeline.detect_query_genders("kids shoes"), {"Boys", "Girls"})
        self.assertIsNone(ProductSearchPipeline.detect_query_genders("snowmen print shoes"))
        self.assertIsNone(ProductSearchPipeline.detect_query_genders("shoes"))

    def test_expands_pool_to_find_women_despite_closer_men(self):
        pipeline = self.make_pipeline(["Men"] * 100 + ["Women", "Women"])
        results = pipeline.search_text("shoes women", top_k=2)
        self.assertEqual([int(idx) for idx, _ in results], [100, 101])

    def test_no_audience_term_preserves_similarity_ranking(self):
        pipeline = self.make_pipeline(["Men", "Women", "Women"])
        self.assertEqual(int(pipeline.search_text("shoes", top_k=1)[0][0]), 0)

    def test_fewer_matches_are_returned_without_wrong_audience_fillers(self):
        pipeline = self.make_pipeline(["Men", "Women", "Men"])
        results = pipeline.search_text("shoes women", top_k=5)
        self.assertEqual([int(idx) for idx, _ in results], [1])
        self.assertEqual(pipeline.search_text("girls shoes", top_k=5), [])

    def test_multimodal_image_candidates_obey_text_audience(self):
        pipeline = self.make_pipeline(["Men"] * 100 + ["Women", "Women"])
        results = pipeline.search_multimodal(text="shoes women", image=object(), top_k=2)
        self.assertEqual({int(idx) for idx, _ in results}, {100, 101})

    def test_multimodal_no_matching_audience_returns_empty(self):
        pipeline = self.make_pipeline(["Men", "Men"])
        self.assertEqual(pipeline.search_multimodal(text="shoes women", image=object()), [])

    def test_small_image_catalog_has_no_negative_or_duplicate_ids(self):
        pipeline = self.make_pipeline(["Men", "Women"])
        ids, scores = pipeline.search_image(object(), top_k=5)
        self.assertEqual(ids.tolist(), [0, 1])
        self.assertEqual(len(scores), 2)

    def test_wrong_product_types_are_removed_in_text_and_multimodal(self):
        pipeline = self.make_pipeline(["Women", "Women", "Women"])
        pipeline.metadata.loc[0, "articleType"] = "Watches"
        pipeline.metadata.loc[0, "productDisplayName"] = "Women Watch"
        for results in (
            pipeline.search_text("shoes women", top_k=3),
            pipeline.search_multimodal(text="shoes women", image=object(), top_k=3),
        ):
            self.assertEqual({int(idx) for idx, _ in results}, {1, 2})

    def test_unsupported_query_skips_model_and_image_fusion(self):
        pipeline = self.make_pipeline(["Women", "Men"])
        self.assertEqual(pipeline.search_text("write python code"), [])
        self.assertEqual(pipeline.search_multimodal(text="write python code", image=object()), [])
        pipeline.load_models.assert_not_called()
        pipeline.embed_text.assert_not_called()
        pipeline.embed_image.assert_not_called()

    def test_category_detection_uses_product_words(self):
        pipeline = self.make_pipeline(["Women"])
        for query, category in (("women shoes", "shoes"), ("sneakers", "shoes"), ("dresses", "dress"), ("watches", "watch"), ("t-shirts", "shirt")):
            self.assertEqual(pipeline.detect_query_category(query), category)
        self.assertIsNone(pipeline.detect_query_category("running shorts"))
        self.assertIsNone(pipeline.detect_query_category("address"))


if __name__ == "__main__":
    unittest.main()

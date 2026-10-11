import os
import re
import numpy as np
import pandas as pd
import torch
from PIL import Image
import faiss
from transformers import CLIPProcessor, CLIPModel
from src.query_policy import CatalogQueryPolicy

class ProductSearchPipeline:
    def __init__(self, project_dir : str):
        self.project_dir = project_dir
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'

        self.model = None
        self.processor = None
        
        self.text_index = None
        self.image_index = None

        self.metadata = None
        self.query_cache = {}
        self.query_policy = None

        # Mapping of keywords to product categories
        self.category_keywords = {
            "jacket" : ["jacket", "coat", "jerkin", "tuxedo"],
            "shirt": ["shirt", "tshirt", "t-shirt"],
            "shoes": ["shoe", "sneaker", "trainer", "boot"],
            "jeans": ["jeans", "denim"],
            "dress": ["dress", "gown"],
            "watch": ["watch", "wristwatch", "pocket-watch"],
            "bag": ["bag", "handbag", "backpack", "carrier-bag"]
        }
        self.category_types = {
            "jacket": {"Jackets", "Rain Jacket", "Nehru Jackets", "Blazers"},
            "shirt": {"Shirts", "Tshirts", "Lounge Tshirts"},
            "shoes": {"Casual Shoes", "Sports Shoes", "Formal Shoes", "Flats", "Heels", "Booties"},
            "jeans": {"Jeans", "Jeggings"},
            "dress": {"Dresses"},
            "watch": {"Watches"},
            "bag": {"Handbags", "Backpacks", "Duffel Bag", "Laptop Bag", "Messenger Bag", "Trolley Bag", "Rucksacks"},
        }
    

    def load_models(self):
        """
        Load CLIP model and processor
        This should be done ONCE per session
        """
        
        if self.model is None or self.processor is None:
            self.model = CLIPModel.from_pretrained(
                "openai/clip-vit-base-patch32",
                cache_dir=os.path.join(self.project_dir, "models")
            ).to(self.device).eval()

            self.processor = CLIPProcessor.from_pretrained(
                "openai/clip-vit-base-patch32",
                cache_dir=os.path.join(self.project_dir, "models")
            )

    def load_metadata(self):
        """
            Load product metadata for filtering search results.

            This includes:
            - articleType
            - productDisplayName 
        """
            
        if not hasattr(self, "metadata") or self.metadata is None:
            metadata_path = os.path.join(
                self.project_dir,
                "data/cleaned_products.csv"
            )

            self.metadata = pd.read_csv(metadata_path)


    def detect_query_category(self, query_text):
        """
            Improve category detection using substring + semantic matching
        """

        tokens = set(re.findall(r"[a-z]+(?:-[a-z]+)?", query_text.lower()))
        for category, keywords in self.category_keywords.items():
            aliases = {category, *keywords}
            aliases.update(word + "s" for word in list(aliases))
            aliases.update(word + "es" for word in list(aliases) if word.endswith(("ss", "ch")))
            if tokens & aliases:
                return category
        
        return None # fallback if nothing matches
    
    def detect_color(self, query_text):
        """
            Extract color from query for better filtering of the products
        """

        colors = ["black", "blue", "green", "yellow", "orange", "red", "purple", "pink", "white", "brown", "grey"]

        query_text = query_text.lower()

        for color in colors:
            if color in query_text:
                return color
            
        return None

    @staticmethod
    def detect_query_genders(query_text):
        """Treat explicit audience words as catalog constraints, using whole words."""
        tokens = set(re.findall(r"[a-z]+", (query_text or "").lower()))
        aliases = {
            "Women": {"women", "womens", "woman", "female", "ladies", "lady"},
            "Men": {"men", "mens", "man", "male", "gentlemen"},
            "Girls": {"girl", "girls"},
            "Boys": {"boy", "boys"},
            "Unisex": {"unisex"},
        }
        genders = {gender for gender, words in aliases.items() if tokens & words}
        if tokens & {"kid", "kids", "child", "children"}:
            genders.update(("Girls", "Boys"))
        return genders or None

    def query_supported(self, query_text):
        self.load_metadata()
        if self.query_policy is None:
            self.query_policy = CatalogQueryPolicy(self.metadata)
        return self.query_policy.supports(query_text)

    def _search_candidates(self, index, embedding, count, allowed_genders=None, allowed_category=None):
        """Expand the retrieval pool until enough eligible products are available."""
        self.load_metadata()
        total = int(index.ntotal)
        eligible = np.zeros(total, dtype=bool)
        catalog_size = min(total, len(self.metadata))
        if allowed_genders is None:
            eligible[:catalog_size] = True
        elif "gender" in self.metadata.columns:
            audiences = self.metadata["gender"].fillna("").astype(str).str.strip().str.casefold()
            eligible[:catalog_size] = audiences.iloc[:catalog_size].isin(
                {gender.casefold() for gender in allowed_genders}
            ).to_numpy()
        if allowed_category:
            types = self.metadata["articleType"].fillna("").astype(str).str.strip().str.casefold()
            eligible[:catalog_size] &= types.iloc[:catalog_size].isin(
                {name.casefold() for name in self.category_types[allowed_category]}
            ).to_numpy()
        target = min(max(int(count), 0), int(eligible.sum()))
        if target == 0:
            return np.array([], dtype=np.int64), np.array([], dtype=np.float32)
        pool_size = min(total, target * 2 if allowed_genders else target)
        while True:
            scores, indices = index.search(embedding, pool_size)
            valid = (indices[0] >= 0) & (indices[0] < total)
            candidate_ids, candidate_scores = indices[0][valid], scores[0][valid]
            keep = eligible[candidate_ids]
            candidate_ids, candidate_scores = candidate_ids[keep], candidate_scores[keep]
            if len(candidate_ids) >= target or pool_size == total:
                return candidate_ids[:target], candidate_scores[:target]
            pool_size = min(total, pool_size * 2)
    
    # -----------------------
    # Embedding utilities
    # -----------------------

    @staticmethod
    def _normalize(embedding : torch.Tensor) -> np.ndarray:
        """
            L2-normalize the embeddings for cosine similarity

            This ensures that dot product = cosine similarity,
            which is required for FAISS inner-product search.
        """
        
        # If embedding is a HuggingFace model output, extract tensor
        if hasattr(embedding, "pooler_output"):
            embedding = embedding.pooler_output

        # Ensure the embedding is a tensor
        if not isinstance(embedding, torch.Tensor):
            embedding = torch.tensor(embedding)

        # Normalize the vectors
        embedding = embedding / embedding.norm(dim = -1, keepdim = True)

        # Convert to numpy float32 for FAISS
        return embedding.detach().cpu().numpy().astype("float32")
    

    def _normalize_scores(self, scores):
        """
            Normalize similarity scores between 0 and 1.

            This ensure fair combination of text and image scores during multimodal fusion
        """


        if len(scores) == 0:
            return []
        min_s = min(scores)
        max_s = max(scores)

        # Avoid division by zero
        if max_s - min_s == 0:
            return [1.0 for _ in scores]

        return [(s - min_s) / (max_s - min_s) for s in scores]
    
    def embed_text(self, text : str) -> np.ndarray:
        """
            Generate CLIP embeddings for a single text input query

            If the same query is repeated, we reuse the embedding 
            through caching instead of recomputing it.
        """

        # Return cached result if exists
        if text in self.query_cache:
            return self.query_cache[text]
        
        self.load_models()
        
        # Prepare input for CLIP
        inputs = self.processor(
            text = [text],
            return_tensors = "pt",
            padding = True,
            truncation = True
        ).to(self.device)

        with torch.no_grad():
            # Use CLIP feature extractor
            text_features = self.model.get_text_features(**inputs)
        
        # Normalize the embeddings
        embedding = self._normalize(text_features)[0]

        # Store in cache
        self.query_cache[text] = embedding

        return embedding
    

    def embed_image(self, image: Image.Image) -> np.ndarray:
        """
        Generate CLIP embedding for a single image
        """

        self.load_models()

        inputs = self.processor(
            images = image,
            return_tensors = "pt"
        ).to(self.device)

        with torch.no_grad():
            # Use CLIP feature extractor
            image_features = self.model.get_image_features(**inputs)

        return self._normalize(image_features)[0]
    

    # -----------------------
    # Batch Helpers(used in notebooks)
    # -----------------------

    def embed_text_batch(self, texts, batch_size=32):
        '''
        Embed a list of texts in batches
        Used during offline embedding generation 
        '''

        self.load_models()
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i+batch_size]
            inputs = self.processor(
                text = batch,
                return_tensors = "pt",
                padding = True,
                truncation = True,
            ).to(self.device)

            with torch.no_grad():
                text_features = self.model.get_text_features(**inputs)
            
            all_embeddings.append(self._normalize(text_features))

        return np.vstack(all_embeddings)
    
    def embed_image_batch(self, image_paths, batch_size = 32):
        """
        Embed a list of images in batches
        """

        self.load_models()
        all_embeddings = []

        for i in range(0, len(image_paths), batch_size):
            batch_paths = image_paths[i : i+batch_size]

            images = []

            for p in batch_paths:
                try:
                    img = Image.open(p).convert("RGB")
                    images.append(img)
                except:
                    continue

            inputs = self.processor(
                images = images,
                return_tensors = "pt",
            ).to(self.device)

            with torch.no_grad():
                image_features = self.model.get_image_features(**inputs)

            all_embeddings.append(self._normalize(image_features))

        return np.vstack(all_embeddings)
    

    def load_indexes(self):
        """
            Load FAISS indexes from disk

            This allows the search system to quickly retrieve 
            nearest product vectors without recomputing embeddings every time
        """

        if self.text_index is None or self.image_index is None:
            text_index_path = os.path.join(
                self.project_dir, "indexes/text_index.faiss"
            )
        
            image_index_path = os.path.join(
                self.project_dir, "indexes/image_index.faiss"
            )

            # Load FAISS indexes
            self.text_index = faiss.read_index(text_index_path)
            self.image_index = faiss.read_index(image_index_path)

    def search_text(self, query_text, top_k = 10):
        """
            Performs text based product search with dynamic filtering

            Searches using:
                - category filtering
                - color filtering
                - keyword matching
                - re-ranking
            Steps:
                1. Convert the query to CLIP embeddings
                2. Retrieve candidates from FAISS
                3. Detect query category
                4. Filter results based on category
                5. Return top_k filtered results
        """

        if not self.query_supported(query_text):
            return []
        self.load_models()
        self.load_indexes()
        self.load_metadata()

        # Convert the query into embeddings
        # Reshape it into 2-d array so that FIASS library can perform similarity search
        query_embeddings = self.embed_text(query_text).reshape(1, -1)

        # Search FAISS index
        # Get "similarity scores" between query embeddings and top_k most similar text embeddings found in the index
        # Get "indices" corresponding to the top_k similar image embeddings.
        # We can use these indices to retrieve the most similar texts
        indices, scores = self._search_candidates(
            self.text_index, query_embeddings, top_k * 10,
            allowed_genders=self.detect_query_genders(query_text),
            allowed_category=self.detect_query_category(query_text),
        )

        # detect the category from the query
        detected_category = self.detect_query_category(query_text)

        # detect color from the query
        detected_color = self.detect_color(query_text)

        query_tokens = query_text.lower().split() 

        results = []

        for idx, score in zip(indices, scores):

            product = self.metadata.iloc[idx]

            # Extract product name for keyword matching
            product_name = str(self.metadata.iloc[idx]["productDisplayName"]).lower()
            # Extract product type from dataset 
            product_type = str(self.metadata.iloc[idx]["articleType"]).lower()

            # Matching category and color
            keyword_match = any(token in product_name for token in query_tokens)
            category_match = detected_category and product_type in {
                name.casefold() for name in self.category_types[detected_category]
            }
            color_match = detected_color and detected_color in product_name

            # Re-ranking score boost
            boost = 0

            if category_match:
                boost += 2.0   # strong signal

            if keyword_match:
                boost += 1.5

            if color_match:
                boost += 1.0

            final_score = score + boost

            results.append((idx, final_score))

        # Sort results
        results = sorted(results, key = lambda x:x[1], reverse = True)

        return results[: top_k]

    
    def search_image(self, image, top_k = 10, allowed_genders=None, allowed_category=None):
        """
            Search products using an input image

            Steps:
                1. Convert input image into embeddings
                2. Query FAISS image index
                3. Return top matching products
        """

        self.load_models()
        self.load_indexes()

        # Convert the input image into vector representation (embeddings)
        # Reshape it into 2-d array so that FIASS library can perform similarity search
        query_image_embeddings = self.embed_image(image).reshape(1, -1)

        # Get "similarity scores" between query embeddings and top_k most similar image embeddings found in the index
        # Get "indices" corresponding to the top_k similar image embeddings.
        # We can use these indices to retrieve the most similar images or their metadata
        return self._search_candidates(
            self.image_index, query_image_embeddings, top_k,
            allowed_genders=allowed_genders,
            allowed_category=allowed_category,
        )


    def search_multimodal(self, text = None, image = None, top_k = 10, alpha = 0.5):
        """
            Multimodal search combining text and image queries

            alpha = weight for the text
            1 - alpha = weight for image
        """

        if text and not self.query_supported(text):
            return []
        self.load_models()
        self.load_indexes()

        final_scores = {}

        # if text query is provided
        # find similar items related to text provided
        # Took larger pool (top_k*2) of candidates to ensure not missing items scoring high in one modality
        # but not make the cut off  in the initial individual search    
        if text is not None:
            # Get list of (idx, score)
            text_results = self.search_text(text, top_k*2)

            # Separate indices and scores
            text_indices = [i for i, s in text_results]
            text_scores = [s for i, s in text_results]

            # Normalize scores
            text_scores = self._normalize_scores(text_scores)

            for idx, score in zip(text_indices, text_scores):
                final_scores[idx] = final_scores.get(idx, 0) + (alpha * score)
        
        # if image query is provided
        # finds similar items related to image provided
        # Took larger pool (top_k*2) of candidates to ensure not missing items scoring high in one modality
        # but not make the cut off  in the initial individual search
        if image is not None:
            image_indices, image_scores = self.search_image(
                image, top_k * 2, allowed_genders=self.detect_query_genders(text),
                allowed_category=self.detect_query_category(text) if text else None,
            )

            # Normalize image scores
            image_scores = self._normalize_scores(image_scores)

            for idx, score in zip(image_indices, image_scores):
                final_scores[idx] = final_scores.get(idx, 0) + ((1-alpha) * score)

        # sort the tuples based on the 2nd element of each tuple (i.e. here "scores") 
        ranked_results = sorted(
            final_scores.items(),
            key = lambda x : x[1],
            reverse = True
        )

        return ranked_results[: top_k]

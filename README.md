# Product Search Engine
End-to-end **multimodal product search engine** that allows the user to search products using test, images, or both, built with **CLIP (Computer Vision + NLP)**, **FAISS**, **FastAPI + Streamlit**.  This repository documents the complete ML lifecycle, starting with data ingestion, preprocessing, and exploratory analysis on Google Colab


## Project Overview
This project aims to build an end-to-end multimodal product search engine that allows users to search for product using text queries, images, or both. The system leverages **Computer Vision** and **Natural Language Processing** using transformer based model **CLIP**(Contrastive Language-Image Pretraining) to map texts and images into a shared embedding space, enabling efficient similarity-based retrieval.

The project is designed to closely mimic e-commerce search systems, used by companies such as Amazon, Zalando, and Flipkart, with a strong focus on production ready ML practices i.e. modular pipelines, scalable embeddings, & API-based development


### Dataset
This project uses the **Fashion Product Images (Small)** dataset sourced from Kaggle.
#### Dataset Description
The dataset contains 44,000+ fashion product images along with structured metadata commonly found in e-commerce catalogs. Each product is represented by:
- A high-quality product image
- Product name and category information
- Attributes such as gender, season, color, and usage

Link: [Fashion Product Images (Small)](https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-small)


### Step - 1 : Embedding Pipeline
- Implemented reusable CLIP-based embedding pipeline
- Centralized image and text embedding logic
- Added batch processing for scalable offline embedding
- Ensured cosine-normalized embeddings for retrieval


### Step - 2 : Vector Search
Built FAISS vector indexes to enable fast nearest-neighbor search over CLIP embeddings.

Indexes created:
- text_index.faiss
- image_index.faiss

These indexes allow millisecond-level similarity search.


### Step - 3 : Multimodal Search Engine
Implemented full search pipeline:
- Text search
- Image search
- Multimodal fusion search

Search uses FAISS vector indexes built from CLIP embeddings.


### Step - 4 : Improvements
- Added hybrid retrieval (CLIP similarity + keyword matching)
- Implemented score normalization for multimodal fusion so that neither text query nor image query dominates randomly 
- Improved query understanding with token-based matching
- Added caching for faster repeated queries


### Step - 5 : Deployment & UI

#### FastAPI Backend
Handles all inference requests
- Supports:
  - Text search
  - Image search
  - Multimodal search
- Loads FAISS indexes and CLIP model for the real time retrieval

#### Streamlit Frontend
- Interactive UI for users
- Supports:
  - Text queries
  - Image uploads
  - Combined multimodal search
- Communicates with FastAPI via REST API calls


### How to Run the Full System

#### Product details and scores

The small dataset stores 60 x 80 pixel thumbnails. For sharper result photos,
run `.venv\Scripts\python.exe setup_image_links.py` and restart the backend.
This downloads only the image URL CSV from the
[full Fashion Product Images Dataset](https://www.kaggle.com/datasets/paramaggarwal/fashion-product-images-dataset).
The API fetches original JPEG photos when viewed and caches them in
`data/images_hd/`. Cards provide a full-size photo link. If an original cannot
be downloaded, the existing thumbnail is shown. The original search images and
indexes remain paired; replacing images for model input requires rebuilding
the image index separately.

Result cards show each product's name, type, description, price availability,
and a link. The small dataset contains product attributes but no prices,
retailer descriptions, or purchase URLs. Descriptions are assembled from its
attributes, missing prices are marked unavailable, and links lead to shopping
searches unless a retailer URL is supplied.

To add real details, copy `product_details.example.csv` to
`data/product_details.csv` and fill rows using the dataset's product IDs:
`id,price,currency,description,product_url`. Use numeric prices, a currency such
as `INR`, and an HTTP(S) retailer URL. Do not change the order of
`cleaned_products.csv`; IDs join the extra details without changing index rows.
The API reloads supplemental details when the file changes; search again to
see them.

Ranking scores order matches within a search; they are not confidence or
accuracy percentages. Text scores include model similarity plus type (+2),
keyword (+1.5), and colour (+1) bonuses. Image scores use image-model
similarity. Combined scores blend the candidate-normalized text and image
rankings with equal weights. Scores cannot be compared across search modes.

#### Windows local setup

Run these commands from this repository's folder (Python 3.12 is supported):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe setup_data.py
```

`setup_data.py` downloads the original public Kaggle dataset (about 565 MiB),
extracts the images, and creates `data/cleaned_products.csv`. It reproduces the
notebooks' image-validation filter so metadata rows match the included FAISS
indexes. The first search downloads the CLIP model into `models/`.

Start both services in the background:

```powershell
powershell -ExecutionPolicy Bypass -File .\start.ps1
```

Open http://localhost:8501 for the UI or http://127.0.0.1:8000/docs for the API.
Service logs and process IDs are saved in `.cache/`. To stop the services:

```powershell
taskkill.exe /PID (Get-Content .cache\backend.pid) /T /F
taskkill.exe /PID (Get-Content .cache\frontend.pid) /T /F
```

Alternatively, run the following backend and frontend commands in separate
terminals using the virtual environment's Python.

#### Start Backend API

```bash
python -m uvicorn src.api:app --reload
```

Runs at : http://127.0.0.1:8000

#### Start Frontend UI
```bash
python -m streamlit run src/ui.py
```

Runs at : http://localhost:8501

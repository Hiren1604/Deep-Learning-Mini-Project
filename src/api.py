from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
from PIL import Image
import io

from src.pipeline import ProductSearchPipeline
from src.catalog import ProductCatalog
from src.product_images import ProductImages

# Initialize FastApi app
app = FastAPI(
    title = "Multimodal Product Search API",
    description = "Search products using text, image, or both",
)

# Initialize pipeline
PROJECT_DIR = Path(__file__).resolve().parents[1]
pipeline = ProductSearchPipeline(project_dir=str(PROJECT_DIR))
catalog = ProductCatalog(PROJECT_DIR)
product_images = ProductImages(PROJECT_DIR)
app.mount("/images", StaticFiles(directory=str(PROJECT_DIR / "data" / "images"), check_dir=False), name="images")


def format_results(results, mode):
    pipeline.load_metadata()
    formatted = []
    for idx, score in results:
        idx = int(idx)
        if idx < 0 or idx >= len(pipeline.metadata):
            continue
        product = pipeline.metadata.iloc[idx]
        product_id = int(product["id"])
        formatted.append({
            "idx": idx,
            "id": product_id,
            "score": float(score),
            "name": str(product["productDisplayName"]),
            "category": str(product["articleType"]),
            "image_path": f"images/{product_id}.jpg",
            "display_image_path": f"product-images/{product_id}.jpg",
            **catalog.describe(product),
        })
    explanations = {
        "text": "Text-model similarity plus bonuses for matching the product type, query keywords, and colour.",
        "image": "Image-model similarity between your uploaded photo and catalog photos.",
        "multimodal": "A weighted combination of text and image rankings, scaled relative to the candidates in this search.",
    }
    return {
        "results": formatted,
        "search_mode": mode,
        "score_explanation": explanations[mode] + " Higher ranks first. This is not an accuracy percentage; compare scores only within this search.",
    }


# ---------------------------
# Health Check
# ---------------------------
@app.get("/")
def root():
    return {"message" : "API is running"}


@app.get("/product-images/{product_id}.jpg")
def product_image(product_id: int):
    try:
        path = product_images.get(product_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Product image not found.")
    return FileResponse(path, media_type="image/jpeg")


# ---------------------------
# Text Search Endpoint
# ---------------------------
@app.post("/search/text")
def search_text(query : str):
    """
        Search products using text query
    """

    if not query.strip():
        raise HTTPException(status_code=400, detail="Enter a search query.")
    results = pipeline.search_text(query, top_k = 5)

    return format_results(results, "text")


# ---------------------------
# Image Search Endpoint
# ---------------------------
@app.post("/search/image")
async def search_image(file : UploadFile = File(...)):
    """
        Search Product using uploaded image
    """

    # Read image file
    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    indices, scores = pipeline.search_image(image, top_k=5)

    return format_results(zip(indices, scores), "image")


# ---------------------------
# Multimodal Search Endpoint
# ---------------------------
@app.post("/search/multimodal")
async def search_multimodal(
    query: str = Form(None),
    file: UploadFile = File(None)
):
    """
        Search using both text + image
    """

    if not (query and query.strip()) and file is None:
        raise HTTPException(status_code=400, detail="Enter a query or upload an image.")
    query = query.strip() if query and query.strip() else None
    image = None

    if file is not None:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")

    if query and image is not None:
        results = pipeline.search_multimodal(text=query, image=image, top_k=5)
        mode = "multimodal"
    elif query:
        results = pipeline.search_text(query, top_k=5)
        mode = "text"
    else:
        indices, scores = pipeline.search_image(image, top_k=5)
        results = zip(indices, scores)
        mode = "image"
    return format_results(results, mode)

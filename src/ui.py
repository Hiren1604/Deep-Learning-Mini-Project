import io

import requests
import streamlit as st
from PIL import Image

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Product Search", layout="wide")
st.title("Multimodal Product Search Engine")
st.caption("Find fashion products by description, photo, or both.")

left, right = st.columns(2)
with left:
    query = st.text_input("Enter search query", placeholder="e.g. blue shirt or black running shoes")
with right:
    uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg"])

image = None
if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")
    st.image(image, caption="Uploaded Image", width=200)

if st.button("Search", type="primary"):
    query = query.strip()
    if not query and image is None:
        st.warning("Enter a search query or upload an image.")
        st.stop()
    with st.spinner("Searching..."):
        try:
            files = None
            if image is not None:
                buffered = io.BytesIO()
                image.save(buffered, format="PNG")
                files = {"file": ("image.png", buffered.getvalue(), "image/png")}
            if image is not None and query:
                response = requests.post(f"{API_URL}/search/multimodal", data={"query": query}, files=files, timeout=180)
            elif image is not None:
                response = requests.post(f"{API_URL}/search/image", files=files, timeout=180)
            else:
                response = requests.post(f"{API_URL}/search/text", params={"query": query}, timeout=180)
            response.raise_for_status()
            st.session_state["search_response"] = response.json()
        except requests.RequestException as error:
            st.error(f"Search failed: {error}")
            st.stop()

if "search_response" in st.session_state:
    response_data = st.session_state["search_response"]
    results = response_data.get("results", [])
    st.subheader("Results")
    st.caption("Higher ranking scores mean stronger matches within this search. Scores are not accuracy percentages.")
    with st.expander("What does the score mean?"):
        st.write(response_data.get("score_explanation", "Higher scores rank first; compare only within the same search."))
        st.write("Text-search bonuses: +2 for product type, +1.5 for a query keyword, and +1 for colour. Combined search uses equal text and image weights.")
    if not results:
        st.warning("No results found.")
    elif any(item.get("price_display") == "Price unavailable" or not item.get("product_url") for item in results):
        st.info("Some prices and purchase links are missing from this catalog. Shopping-search links can help you find current listings.")

    for row_start in range(0, len(results), 3):
        columns = st.columns(3)
        for column, item in zip(columns, results[row_start:row_start + 3]):
            with column, st.container(border=True):
                image_path = item.get("display_image_path", item["image_path"])
                st.image(f"{API_URL}/{image_path}", width=250)
                st.link_button("Open full-size photo", f"{API_URL}/{image_path}")
                st.subheader(item["name"])
                st.markdown(f"**Product type:** {item.get('type') or item['category']}")
                st.markdown(f"**Price:** {item.get('price_display', 'Price unavailable')}")
                st.write(item.get("description", "Description unavailable."))
                if item.get("description_source") == "attributes":
                    st.caption("Description from catalog attributes.")
                st.caption(f"Ranking score: {item['score']:.3f}")
                if item.get("product_url"):
                    st.link_button("View product", item["product_url"])
                else:
                    st.link_button("Search shopping listings", item["shopping_search_url"])

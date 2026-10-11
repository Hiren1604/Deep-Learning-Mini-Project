import io

import requests
import streamlit as st
from PIL import Image

from src.product_cards import CARD_STYLES, render_product_card
from src.search_panel import SEARCH_INTRO, SEARCH_STYLES

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Product Search", layout="wide")
st.markdown(CARD_STYLES + SEARCH_STYLES, unsafe_allow_html=True)
st.title("Multimodal Product Search Engine")
st.caption("Find fashion products by description, photo, or both.")

with st.container(key="search_panel"):
    st.markdown(SEARCH_INTRO, unsafe_allow_html=True)
    left, right = st.columns([3, 2])
    with left:
        query = st.text_input("What are you looking for?", placeholder="Black running shoes, a blue shirt...")
    with right:
        uploaded_file = st.file_uploader("Add a reference photo", type=["png", "jpg", "jpeg"])
    image = None
    if uploaded_file is not None:
        image = Image.open(uploaded_file).convert("RGB")
        st.image(image, caption="Your reference photo", width=160)
    search_clicked = st.button("Find my matches", type="primary")

if search_clicked:
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
    if not results:
        message = response_data.get("message") or "No products match this search. Try a broader description."
        if response_data.get("status") == "out_of_scope":
            st.info(message)
        else:
            st.warning(message)
    else:
        st.subheader("Your matches")
        st.caption(f"{len(results)} finds, ordered by relevance. Select a photo for a closer look.")
        with st.expander("What does the score mean?"):
            st.write(response_data.get("score_explanation", "Higher scores rank first; compare only within the same search."))
            st.write("Text-search bonuses: +2 for product type, +1.5 for a query keyword, and +1 for colour. Combined search uses equal text and image weights.")
        cards = "".join(render_product_card(item, rank, API_URL) for rank, item in enumerate(results, 1))
        st.markdown(f'<div class="product-grid">{cards}</div>', unsafe_allow_html=True)

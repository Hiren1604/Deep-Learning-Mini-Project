"""HTML presentation for product search results."""
from html import escape
from textwrap import dedent
from urllib.parse import urlparse


CARD_STYLES = """
<style>
.product-grid {
    display: grid; grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 24px; padding: 8px 0 28px;
}
.product-card {
    min-width: 0; overflow: hidden; display: flex; flex-direction: column;
    background: #ffffff; color: #172c30; border: 1px solid #e5ece9;
    border-radius: 22px; box-shadow: 0 6px 24px rgba(26, 54, 48, .045);
    transition: transform .2s ease, box-shadow .2s ease, border-color .2s ease;
}
.product-card:hover {
    transform: translateY(-5px); border-color: #b8d2c7;
    box-shadow: 0 16px 36px rgba(26, 54, 48, .12);
}
.product-card .product-photo {
    position: relative; display: block; background: #fafbf9;
    padding: 28px 24px 12px; border-bottom: 1px solid #f0f3f1;
}
.product-card .product-photo img {
    display: block; width: 100%; height: 264px; object-fit: contain;
    mix-blend-mode: multiply; transition: transform .25s ease;
}
.product-card:hover .product-photo img { transform: scale(1.035); }
.product-card .product-rank {
    position: absolute; z-index: 1; top: 16px; left: 16px;
    font-size: 11px; font-weight: 700; letter-spacing: .065em;
    color: #315950; background: #eaf2ed; border-radius: 20px; padding: 6px 10px;
}
.product-card .product-rank.first { background: #163e35; color: #fff; }
.product-card .photo-open {
    position: absolute; right: 16px; top: 16px; width: 30px; height: 30px;
    display: grid; place-items: center; border-radius: 50%;
    background: #fff; color: #315950; border: 1px solid #e5ece9; font-size: 17px;
}
.product-card .product-content { padding: 22px; flex: 1; display: flex; flex-direction: column; }
.product-card .product-type {
    color: #548173; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .12em; margin-bottom: 9px;
}
.product-card .product-name {
    font-size: 19px; line-height: 1.4; font-weight: 650; color: #172c30;
    padding: 0; margin: 0 0 16px; min-height: 54px;
}
.product-card .product-tags {
    display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px; margin-bottom: 22px;
}
.product-card .product-tag {
    display: flex; flex-direction: column; align-items: flex-start;
    gap: 4px; padding: 11px 13px; min-width: 0;
    border: 1px solid #e7eee8; border-radius: 12px; background: #f4f7f3;
    line-height: 1.4; overflow-wrap: anywhere;
}
.product-card .tag-label { font-size: 12px; font-weight: 500; color: #52685d; }
.product-card .product-tag strong { font-size: 16px; font-weight: 650; color: #233f31; }
.product-card .product-tag:nth-child(2) { background: #f1f5fa; border-color: #e3eaf3; }
.product-card .product-tag:nth-child(3) { background: #fff7eb; border-color: #f3eadb; }
.product-card .product-tag:nth-child(4) { background: #f6f2f9; border-color: #ece4f1; }
.product-card .product-description { font-size: 13px; color: #65716b; margin: 0 0 20px; }
.product-card .product-footer {
    margin-top: auto; padding-top: 17px; border-top: 1px solid #edf1ee;
    display: flex; align-items: center; justify-content: space-between; gap: 12px;
}
.product-card .score-label { display: block; font-size: 10px; color: #738278; margin-bottom: 3px; }
.product-card .score-value { font-size: 17px; font-weight: 650; font-variant-numeric: tabular-nums; }
.product-card a.product-action {
    display: inline-flex; align-items: center; gap: 9px; padding: 10px 13px;
    color: #fff; background: #163e35; border-radius: 10px;
    text-decoration: none; font-size: 12px; font-weight: 600;
    transition: background .2s ease;
}
.product-card a.product-action:hover { background: #286553; color: #fff; }
.product-card a:focus-visible { outline: 3px solid #dd9856; outline-offset: 4px; }
@media (max-width: 1100px) { .product-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 640px) { .product-grid { grid-template-columns: 1fr; gap: 18px; } }
@media (prefers-reduced-motion: reduce) {
    .product-card, .product-card .product-photo img, .product-card a.product-action { transition: none; }
    .product-card:hover, .product-card:hover .product-photo img { transform: none; }
}
</style>
"""


def safe_link(url):
    url = str(url or "")
    parsed = urlparse(url)
    return escape(url, quote=True) if parsed.scheme in ("http", "https") and parsed.netloc else ""


def render_product_card(item, rank, api_url):
    name = escape(str(item.get("name") or "Unnamed product"))
    product_type = escape(str(item.get("type") or item.get("category") or "Product"))
    image_path = item.get("display_image_path") or item["image_path"]
    image_url = safe_link(f"{api_url}/{image_path}")
    tags = "".join(
        f'<span class="product-tag"><span class="tag-label">{label}</span><strong>{escape(str(item[field]))}</strong></span>'
        for label, field in (("For", "gender"), ("Colour", "color"), ("Occasion", "usage"), ("Season", "season"))
        if item.get(field)
    )
    description = ""
    if item.get("description_source") == "catalog" and item.get("description"):
        description = f'<p class="product-description">{escape(str(item["description"]))}</p>'
    product_url = safe_link(item.get("product_url"))
    action_url = product_url or safe_link(item.get("shopping_search_url"))
    action_label = "View product" if product_url else "Explore listings"
    action = (
        f'<a class="product-action" href="{action_url}" target="_blank" rel="noopener noreferrer" '
        f'aria-label="{action_label}: {name}">{action_label} <span aria-hidden="true">↗</span></a>'
        if action_url else ""
    )
    badge = "TOP MATCH" if rank == 1 else f"MATCH {rank:02d}"
    rank_class = " first" if rank == 1 else ""
    return dedent(f"""\
    <article class="product-card" aria-label="{name}">
    <a class="product-photo" href="{image_url}" target="_blank" rel="noopener noreferrer" aria-label="Open full-size photo: {name}">
    <span class="product-rank{rank_class}">{badge}</span><span class="photo-open" aria-hidden="true">↗</span>
    <img src="{image_url}" alt="{name}" loading="lazy" width="400" height="264">
    </a>
    <div class="product-content">
    <div class="product-type">{product_type}</div><div class="product-name" role="heading" aria-level="3">{name}</div>
    <div class="product-tags">{tags}</div>{description}
    <div class="product-footer">
    <div title="Ranking score within this search, not a confidence percentage"><span class="score-label">Match score</span><span class="score-value">{float(item['score']):.3f}</span></div>
    {action}</div></div></article>
    """)

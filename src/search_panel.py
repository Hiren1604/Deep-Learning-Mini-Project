"""Scoped styling for the native Streamlit search controls."""

SEARCH_STYLES = """
<style>
.st-key-search_panel {
    background: linear-gradient(120deg, #f0f6f1 0%, #f8faf5 60%, #f4f7fb 100%);
    border: 1px solid #dce8de; border-radius: 24px;
    padding: 28px 30px; margin: 16px 0 28px;
    box-shadow: 0 8px 28px rgba(26, 54, 48, .04);
}
.search-eyebrow {
    color: #477663; font-size: 12px; font-weight: 700;
    text-transform: uppercase; letter-spacing: .13em; margin-bottom: 8px;
}
.search-heading { color: #173d32; font-size: 28px; font-weight: 650; line-height: 1.25; margin-bottom: 8px; }
.search-hint { color: #536d60; font-size: 15px; line-height: 1.6; margin-bottom: 8px; }
.st-key-search_panel [data-testid="stWidgetLabel"] p { color: #344f42; font-size: 14px; font-weight: 600; }
.st-key-search_panel [data-testid="stTextInput"] [data-baseweb="input"],
.st-key-search_panel [data-testid="stTextInputRootElement"] {
    background: #fff; border: 1px solid #d2e0d6; border-radius: 14px;
    min-height: 56px; height: auto;
    box-shadow: 0 3px 10px rgba(26, 54, 48, .035);
}
.st-key-search_panel [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
.st-key-search_panel [data-testid="stTextInputRootElement"]:focus-within {
    border-color: #35775d; box-shadow: 0 0 0 3px rgba(53, 119, 93, .12);
}
.st-key-search_panel [data-testid="stTextInput"] input {
    font-size: 16px; min-height: 54px; color: #173d32; padding: 12px 16px;
    background: transparent;
}
.st-key-search_panel [data-testid="stTextInput"] input::placeholder { color: #7b8e83; }
.st-key-search_panel [data-testid="stFileUploaderDropzone"] {
    background: rgba(255, 255, 255, .8); border: 1px dashed #c2d5c8; border-radius: 14px;
}
.st-key-search_panel [data-testid="stFileUploaderDropzone"] button {
    border: 1px solid #cbdccf; border-radius: 10px; background: #fff; color: #244f3e;
}
.st-key-search_panel [data-testid="stBaseButton-primary"] {
    background: #163e35; border: 1px solid #163e35; border-radius: 13px;
    min-height: 50px; padding: 12px 28px; box-shadow: 0 5px 12px rgba(22, 62, 53, .12);
}
.st-key-search_panel [data-testid="stBaseButton-primary"] p { color: #fff; font-size: 16px; font-weight: 600; }
.st-key-search_panel [data-testid="stBaseButton-primary"]:hover { background: #286553; border-color: #286553; }
.st-key-search_panel [data-testid="stBaseButton-primary"]:focus-visible { outline: 3px solid #dd9856; outline-offset: 3px; }
.st-key-search_panel [data-testid="stCaptionContainer"] { color: #5e7869; }
@media (max-width: 640px) {
    .st-key-search_panel { padding: 20px 16px; border-radius: 20px; }
    .search-heading { font-size: 24px; }
    .st-key-search_panel [data-testid="stBaseButton-primary"] { width: 100%; }
}
</style>
"""

SEARCH_INTRO = """
<div class="search-eyebrow">A little inspiration. A better match.</div>
<div class="search-heading" role="heading" aria-level="2">Find it your way.</div>
<div class="search-hint">Describe your style, add a photo, or combine both to discover your next find.</div>
"""

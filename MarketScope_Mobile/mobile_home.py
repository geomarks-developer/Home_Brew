"""MarketScope Mobile home screen."""
from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="MarketScope Mobile",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
[data-testid="stSidebar"] {display: none;}
[data-testid="collapsedControl"] {display: none;}
.block-container {
    max-width: 520px;
    padding-top: 2.5rem;
    padding-left: 1rem;
    padding-right: 1rem;
    padding-bottom: 5rem;
}
.ms-brand {
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.1;
    margin-bottom: .2rem;
}
.ms-subtitle {
    color: #9aa3b2;
    font-size: .95rem;
    margin-bottom: 1.25rem;
}
.ms-card {
    border: 1px solid rgba(128,128,128,.25);
    background: rgba(128,128,128,.055);
    border-radius: 18px;
    padding: 1rem 1rem .8rem 1rem;
    margin-bottom: .65rem;
}
.ms-card-title {
    font-size: 1.18rem;
    font-weight: 750;
    margin-bottom: .2rem;
}
.ms-card-text {
    color: #9aa3b2;
    font-size: .88rem;
    line-height: 1.4;
}
.quick-label {
    font-size: .9rem;
    color: #9aa3b2;
    margin-top: .8rem;
    margin-bottom: .25rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="ms-brand">📱 MarketScope Mobile</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="ms-subtitle">Stocks, ETFs, value, growth, and income research in one mobile-first workspace.</div>',
    unsafe_allow_html=True,
)

search = st.text_input(
    "Search",
    placeholder="Search a ticker, ETF, or company...",
    label_visibility="collapsed",
)
if search:
    st.session_state["mobile_search"] = search.strip().upper()

st.markdown('<div class="quick-label">RESEARCH</div>', unsafe_allow_html=True)

cards = [
    ("📈", "Growth", "Find businesses with strong expansion, quality, and momentum.", "pages/growth.py"),
    ("💎", "Value", "Find attractive valuations while watching quality and value-trap risk.", "pages/value.py"),
    ("💰", "Dividend", "Research income, dividend quality, sustainability, and safety.", "pages/dividend.py"),
    ("🌐", "ETF", "Explore ETFs, sectors, performance, expenses, and allocation ideas.", "pages/etf.py"),
]

for icon, title, description, page in cards:
    st.markdown(
        f'<div class="ms-card"><div class="ms-card-title">{icon} {title}</div>'
        f'<div class="ms-card-text">{description}</div></div>',
        unsafe_allow_html=True,
    )
    st.page_link(page, label=f"Open {title}", icon=icon, width="stretch")

st.markdown('<div class="quick-label">QUICK ACCESS</div>', unsafe_allow_html=True)
q1, q2 = st.columns(2)
with q1:
    st.page_link("pages/watchlist.py", label="Watchlist", icon="⭐", width="stretch")
    st.page_link("pages/compare.py", label="Compare", icon="⚖️", width="stretch")
with q2:
    st.page_link("pages/markets.py", label="Markets", icon="🌐", width="stretch")
    st.page_link("pages/settings.py", label="Settings", icon="⚙️", width="stretch")

st.divider()
st.caption("MarketScope Mobile • Research tools for informational and educational use")

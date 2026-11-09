from __future__ import annotations

import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="MarketScope Dividend",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Application title
# ---------------------------------------------------------

st.title("💰 MarketScope Dividend")

st.caption(
    "Dividend Aristocrat screening, analysis, comparison, "
    "and portfolio research."
)


# ---------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------

with st.sidebar:

    st.markdown("## 💰 MarketScope Dividend")

    st.caption(
        "Dividend Aristocrat research and portfolio analysis"
    )

    st.markdown("---")


# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

pages = {
    "Market Analysis": [
        st.Page(
            "pages/summary.py",
            title="Summary",
            icon="📊",
            default=True,
        ),
        st.Page(
            "pages/dividend_screener.py",
            title="Dividend Screener",
            icon="💵",
        ),
        st.Page(
            "pages/heatmap.py",
            title="Dividend Heatmap",
            icon="🔥",
        ),
    ],

    "Research": [
        st.Page(
            "pages/stock_explorer.py",
            title="Stock Explorer",
            icon="🔎",
        ),
        st.Page(
            "pages/compare_stocks.py",
            title="Compare Stocks",
            icon="⚖️",
        ),
    ],

    "Portfolio": [
        st.Page(
            "pages/portfolio_builder.py",
            title="Portfolio Builder",
            icon="🧺",
        ),
    ],

    "Information": [
        st.Page(
            "pages/methodology.py",
            title="Methodology",
            icon="🧮",
        ),
        st.Page(
            "pages/risk.py",
            title="Risk Disclosure",
            icon="⚠️",
        ),
        st.Page(
            "pages/about.py",
            title="About",
            icon="ℹ️",
        ),
    ],
}


navigation = st.navigation(pages)

navigation.run()
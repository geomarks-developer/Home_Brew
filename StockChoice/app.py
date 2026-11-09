from __future__ import annotations

import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="StockChoice",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# APPLICATION HEADER
# ============================================================

st.title("💎 StockChoice")

st.caption(
    "The right stock for the right strategy."
)


# ============================================================
# SIDEBAR BRANDING
# ============================================================

with st.sidebar:

    st.markdown("# 💎 StockChoice")

    st.caption(
        "Data-driven stock screening, "
        "ranking, research and portfolio analysis."
    )

    st.markdown("---")


# ============================================================
# NAVIGATION
# ============================================================

pages = {

    "Dashboard": [

        st.Page(
            "pages/dashboard.py",
            title="Dashboard",
            icon="📊",
            default=True,
        ),

    ],

    "Research": [

        st.Page(
            "pages/screener.py",
            title="Screener",
            icon="🔎",
        ),

        st.Page(
            "pages/heatmap.py",
            title="Heatmap",
            icon="🔥",
        ),

        st.Page(
            "pages/stock_explorer.py",
            title="Stock Explorer",
            icon="🔬",
        ),

        st.Page(
            "pages/compare_stocks.py",
            title="Compare Stocks",
            icon="⚖️",
        ),

    ],

    "Portfolio": [

        #st.Page(
        #    "pages/watchlists.py",
        #    title="Watchlists",
        #    icon="👀",
        #),

        #st.Page(
        #    "pages/portfolio_builder.py",
        #    title="Portfolio Builder",
        #    icon="🧺",
        #),

    ],

    "Information": [

        st.Page(
            "pages/methodology.py",
            title="Methodology",
            icon="🧮",
        ),

        st.Page(
            "pages/about.py",
            title="About",
            icon="ℹ️",
        ),

    ],
}


# ============================================================
# RUN NAVIGATION
# ============================================================

navigation = st.navigation(
    pages
)

navigation.run()
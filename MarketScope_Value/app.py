from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="MarketScope Value",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Main application header
# =========================================================
st.title("💎 MarketScope Value")
st.caption(
    "Value-stock research focused on valuation, business quality, financial strength, "
    "sustainable growth, momentum, and value-trap awareness."
)


# =========================================================
# Navigation
# =========================================================
pages = {
    "Market Analysis": [
        st.Page(
            "pages/summary.py",
            title="Summary",
            icon="📊",
            default=True,
        ),
        st.Page(
            "pages/market_overview.py",
            title="Market Overview",
            icon="🌐",
        ),
        st.Page(
            "pages/value_screener.py",
            title="Value Screener",
            icon="💎",
        ),
        st.Page(
            "pages/sectors.py",
            title="Sectors",
            icon="🧩",
        ),
        st.Page(
            "pages/market_calendar.py",
            title="Market Calendar",
            icon="🗓️",
        ),
    ],
    "Stock Research": [
        st.Page(
            "pages/stock_detail.py",
            title="Stock Detail",
            icon="🔎",
        ),
        st.Page(
            "pages/compare_stocks.py",
            title="Compare Stocks",
            icon="⚖️",
        ),
        st.Page(
            "pages/watchlist.py",
            title="Watchlist",
            icon="⭐",
        ),
    ],
    "Portfolio & Risk": [
        st.Page(
            "pages/portfolio_builder.py",
            title="Portfolio Builder",
            icon="🧺",
        ),
        st.Page(
            "pages/value_trap_dashboard.py",
            title="Value Trap Dashboard",
            icon="⚠️",
        ),
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

navigation = st.navigation(pages)


# =========================================================
# Sidebar branding
# =========================================================
with st.sidebar:
    st.divider()
    st.markdown("### 💎 MarketScope Value")
    st.caption(
        "Value-stock research with an emphasis on identifying attractive valuations "
        "while avoiding potential value traps."
    )


# Keep one navigation.run() call at the bottom of app.py.
navigation.run()

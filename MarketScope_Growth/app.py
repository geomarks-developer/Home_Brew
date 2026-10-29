from __future__ import annotations
from market_data import cache_age_hours, load_market_data

import streamlit as st


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="MarketScope Growth",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------
# Application title
# ---------------------------------------------------------
st.title("📈 MarketScope Growth")
st.caption(
    "Growth-stock screening, market analysis, stock research, "
    "portfolio construction, and risk analysis."
)


# ---------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------
#with st.sidebar:
#    st.markdown("## 📈 MarketScope Growth")
#    st.caption("Growth-stock research and portfolio analysis")
#    st.markdown("---")


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
            "pages/market_overview.py",
            title="Market Overview",
            icon="🌐",
        ),
        st.Page(
            "pages/growth_screener.py",
            title="Growth Screener",
            icon="🚀",
        ),
        st.Page(
            "pages/sectors.py",
            title="Sectors",
            icon="🧩",
        ),
        st.Page(
            "pages/market_calendar.py",
            title="Market Calendar",
            icon="📅",
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
            "pages/risk_dashboard.py",
            title="Risk Dashboard",
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


with st.sidebar:
    st.markdown("## 📈 MarketScope Growth")
    st.caption("Growth-stock research and portfolio analysis")
    st.markdown("---")

    st.markdown("### Growth Dashboard")

    refresh = st.button(
        "🔄 Refresh Market Data",
        type="secondary",
        use_container_width=True,
    )

    if refresh:
        st.cache_data.clear()

        with st.spinner("Refreshing MarketScope Growth data..."):
            load_market_data(force_refresh=True)

        st.rerun()

    age = cache_age_hours()

    if age is not None:
        age_text = (
            f"{age * 60:.0f} minutes"
            if age < 1
            else f"{age:.1f} hours"
        )

        st.caption(f"Data cache age: {age_text}")

    st.markdown("---")


navigation = st.navigation(pages)
navigation.run()

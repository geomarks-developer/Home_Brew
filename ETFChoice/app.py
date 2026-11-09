import streamlit as st
from market_data import (
    clear_market_data_cache,
    initialize_market_data,
)

# ---------------------------------------------------------
# Streamlit page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="MarketScope ETF",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------
# Initialize shared ETF market data
# ---------------------------------------------------------

try:
    market_data = initialize_market_data()

except Exception as error:
    st.error(
        "MarketScope ETF could not load its market data."
    )

    st.exception(error)
    st.stop()

# ---------------------------------------------------------
# Application pages
# ---------------------------------------------------------

summary_page = st.Page(
    "pages/summary.py",
    title="Summary",
    icon="🏠",
    default=True,
)

etf_screener_page = st.Page(
    "pages/etf_screener.py",
    title="ETF Screener",
    icon="🔎",
)

sectors_page = st.Page(
    "pages/sectors.py",
    title="Market & Sectors",
    icon="🌎",
)

heatmap_page = st.Page(
    "pages/heatmap.py",
    title="ETF Heatmap",
    icon="🔥",
)

explorer_page = st.Page(
    "pages/etf_explorer.py",
    title="ETF Explorer",
    icon="📈",
)

compare_page = st.Page(
    "pages/compare.py",
    title="Compare ETFs",
    icon="⚖️",
)

portfolio_page = st.Page(
    "pages/portfolio.py",
    title="Portfolio Builder",
    icon="💼",
)

about_page = st.Page(
    "pages/about.py",
    title="About MarketScope ETF",
    icon="ℹ️",
)

methodology_page = st.Page(
    "pages/methodology.py",
    title="Methodology",
    icon="📖",
)

risk_page = st.Page(
    "pages/risk.py",
    title="Risk Disclosure",
    icon="⚠️",
)


# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

pages = {
    "MarketScope ETF": [
        summary_page,
        etf_screener_page,
        sectors_page,
        heatmap_page,
        explorer_page,
        compare_page,
        portfolio_page,
    ],
"About": [
    about_page,
    methodology_page,
    risk_page,
    ],
}

navigation = st.navigation(
    pages,
    position="sidebar",
    expanded=True,
)


# ---------------------------------------------------------
# Sidebar branding
# ---------------------------------------------------------

with st.sidebar:
    #st.markdown("---")

    st.markdown(
        """
        ### 📊 MarketScope ETF

        **ETF & Sector Market Analysis**

        Screen ETFs, analyze sector leadership,
        compare funds, and explore market trends.
        """
    )

    st.markdown("---")

    if st.button(
        "🔄 Refresh Market Data",
        width="stretch",
        key="refresh_market_data",
    ):
        clear_market_data_cache()

        st.session_state.pop(
            "market_data",
            None,
        )

        st.session_state.pop(
            "market_data_session_key",
            None,
        )

        st.rerun()

    st.markdown("---")

    st.caption(
        "MarketScope ETF is provided for informational "
        "and educational purposes only. "
        "It is not investment advice."
    )


# ---------------------------------------------------------
# Run selected page
# ---------------------------------------------------------

navigation.run()
import streamlit as st

from config import (
    APP_DESCRIPTION,
    APP_NAME,
    APP_VERSION,
)


# =========================================================
# HEADER
# =========================================================

st.title("ℹ️ About MarketScope ETF")

st.caption(
    "A focused ETF research dashboard for screening funds, "
    "analyzing market sectors, comparing ETFs, and exploring "
    "portfolio ideas."
)


# =========================================================
# ABOUT
# =========================================================

st.markdown("## What Is MarketScope ETF?")

st.write(
    f"""
    **{APP_NAME}** is an ETF-focused market research application
    designed to bring several types of ETF analysis together in
    one dashboard.

    Instead of focusing on individual stocks, MarketScope ETF
    looks across ETFs representing broad markets, sectors,
    investment styles, international markets, bonds, real estate,
    commodities, factors, and thematic strategies.

    The goal is to make it easier to answer questions such as:

    - Which ETFs currently have the strongest momentum?
    - Which market sectors are leading or lagging?
    - Which ETFs are outperforming the broader market?
    - How do similar ETFs compare on performance and risk?
    - What does an ETF's current technical trend look like?
    - How might highly ranked ETFs fit into a diversified model portfolio?
    """
)


# =========================================================
# PURPOSE
# =========================================================

st.markdown("---")

st.markdown("## What MarketScope ETF Is Designed To Do")

st.write(
    """
    MarketScope ETF combines market data with a quantitative
    screening framework to organize ETFs into a consistent
    research process.

    Rather than relying on a single metric, the application
    evaluates multiple dimensions of ETF behavior, including
    momentum, trend, historical risk, liquidity, relative
    strength, and available fund characteristics.
    """
)


# =========================================================
# APPLICATION FEATURES
# =========================================================

st.markdown("---")

st.markdown("## Application Features")


# ---------------------------------------------------------
# Summary
# ---------------------------------------------------------

st.markdown("### 🏠 Summary")

st.write(
    """
    The Summary dashboard provides a high-level view of the
    MarketScope ETF universe.

    It highlights:

    - ETF market breadth
    - Highly ranked ETFs
    - Momentum leaders
    - Leading and lagging sectors
    - Sector leadership
    - Current MarketScope ETF scores
    """
)


# ---------------------------------------------------------
# ETF Screener
# ---------------------------------------------------------

st.markdown("### 🔎 ETF Screener")

st.write(
    """
    The ETF Screener ranks and filters ETFs using the
    MarketScope scoring framework.

    ETFs can be evaluated across categories such as broad market,
    growth, value, dividends, sectors, international markets,
    bonds, real estate, commodities, factors, and thematic funds.
    """
)


# ---------------------------------------------------------
# Market and Sectors
# ---------------------------------------------------------

st.markdown("### 🌎 Market & Sectors")

st.write(
    """
    The sector analysis features are designed to identify areas
    of market leadership and weakness.

    MarketScope evaluates the major sector ETFs using performance,
    trend, and MarketScope scoring information.
    """
)


# ---------------------------------------------------------
# Heatmap
# ---------------------------------------------------------

st.markdown("### 🔥 ETF Heatmap")

st.write(
    """
    The ETF Heatmap provides a visual way to compare performance
    across ETFs, sectors, and market categories over different
    time periods.
    """
)


# ---------------------------------------------------------
# Explorer
# ---------------------------------------------------------

st.markdown("### 📈 ETF Explorer")

st.write(
    """
    ETF Explorer provides a detailed view of an individual ETF.

    The page includes:

    - Historical price performance
    - 50-day and 200-day moving averages
    - MarketScope ETF Score
    - Momentum and trend measures
    - RSI
    - Volatility
    - Maximum drawdown
    - Relative strength versus the market benchmark
    - Available fund characteristics
    """
)


# ---------------------------------------------------------
# Compare
# ---------------------------------------------------------

st.markdown("### ⚖️ Compare ETFs")

st.write(
    """
    Compare ETFs allows multiple funds to be evaluated side by side.

    The comparison includes performance, risk, technical indicators,
    MarketScope scores, relative strength, and hypothetical growth
    of an equal starting investment.
    """
)


# ---------------------------------------------------------
# Portfolio Builder
# ---------------------------------------------------------

st.markdown("### 💼 Portfolio Builder")

st.write(
    """
    The Portfolio Builder combines predefined asset-allocation
    models with current MarketScope ETF rankings.

    Available models include:

    - Conservative
    - Balanced
    - Growth
    - Income
    - Aggressive

    MarketScope searches the appropriate ETF categories and selects
    highly ranked qualifying ETFs for each portfolio allocation.
    """
)


# =========================================================
# HOW IT FITS TOGETHER
# =========================================================

st.markdown("---")

st.markdown("## How MarketScope ETF Fits Together")

st.markdown(
    """
    **ETF Universe**

    ↓

    **Market Data**

    ↓

    **Performance + Technical Analysis**

    ↓

    **Momentum + Trend + Risk + Other Scores**

    ↓

    **MarketScope ETF Score**

    ↓

    **Screener + Explorer + Compare**

    ↓

    **Sector Analysis + Portfolio Builder**
    """
)


# =========================================================
# DESIGN PHILOSOPHY
# =========================================================

st.markdown("---")

st.markdown("## Design Philosophy")

st.write(
    """
    MarketScope ETF is built around a few simple principles:
    """
)

st.markdown(
    """
    **Keep the analysis understandable**

    Scores should be traceable back to recognizable measures such
    as returns, moving averages, volatility, drawdown, and relative
    strength.

    **Look at more than one time horizon**

    Short-term performance can be noisy. MarketScope combines
    several periods when evaluating momentum and market leadership.

    **Separate data from presentation**

    Market data is loaded centrally and shared throughout the
    application so individual pages can work from the same dataset.

    **Use rankings as research signals, not predictions**

    A high MarketScope score describes conditions measured by the
    current model. It does not predict future returns.

    **Keep the system modular**

    ETF analysis, sector analysis, portfolio construction, data
    loading, and Streamlit presentation are separated so the
    application can evolve without requiring a complete rewrite.
    """
)


# =========================================================
# DATA
# =========================================================

st.markdown("---")

st.markdown("## Market Data")

st.write(
    """
    MarketScope ETF uses historical market information retrieved
    through the application's shared data layer.

    Data is cached so that navigating between pages, selecting ETFs,
    comparing funds, or changing portfolio settings does not require
    the entire ETF universe to be downloaded again.
    """
)

st.caption(
    "Market data availability and individual ETF fields may vary."
)


# =========================================================
# METHODOLOGY
# =========================================================

st.markdown("---")

st.markdown("## Want to Know How the Scores Work?")

st.write(
    """
    The **Methodology** page provides the detailed explanation of
    the MarketScope framework, including:

    - ETF Score weights
    - Momentum calculations
    - Trend analysis
    - Risk scoring
    - Relative strength
    - Sector rankings
    - Portfolio construction
    """
)


# =========================================================
# VERSION
# =========================================================

st.markdown("---")

st.markdown("## Application Information")

info_col1, info_col2 = st.columns(2)


with info_col1:

    st.metric(
        "Application",
        APP_NAME,
    )


with info_col2:

    st.metric(
        "Version",
        APP_VERSION,
    )


st.write(APP_DESCRIPTION)


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.warning(
    """
    **Important**

    MarketScope ETF is a research and educational application.

    MarketScope scores, ETF rankings, sector rankings, technical
    indicators, comparisons, and model portfolios are not investment
    recommendations and should not be treated as predictions of
    future performance.

    Investment decisions should consider individual financial
    circumstances, objectives, time horizon, liquidity needs,
    tax considerations, and tolerance for risk.
    """
)
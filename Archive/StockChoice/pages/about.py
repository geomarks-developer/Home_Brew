"""
StockChoice About Page
"""

from __future__ import annotations

import streamlit as st


# ============================================================
# PAGE HEADER
# ============================================================

st.title("ℹ️ About StockChoice")

st.caption(
    "The right stock for the right strategy."
)


# ============================================================
# MISSION
# ============================================================

st.subheader("Our Mission")

st.markdown(
    """
    StockChoice was created to help investors make
    better stock selection decisions using a
    disciplined, multi-factor approach.

    Rather than focusing exclusively on growth,
    dividends, or valuation, StockChoice evaluates
    stocks across multiple dimensions and allows
    investors to select the strategy that best
    matches their investing style.
    """
)


# ============================================================
# HOW IT WORKS
# ============================================================

st.subheader("How StockChoice Works")

st.markdown(
    """
    Every stock is evaluated across six factors:

    ### 📈 Growth
    Revenue, earnings and cash flow growth.

    ### 🛡️ Quality
    Profitability, financial strength and efficiency.

    ### 🏷️ Value
    Relative valuation metrics.

    ### 💰 Dividend
    Yield, sustainability and dividend quality.

    ### 🚀 Momentum
    Price performance and technical strength.

    ### ⚠️ Risk
    Volatility, drawdowns and financial risk.

    Each factor receives a score from:

    **0 to 100**

    Strategy scores are calculated using different
    weightings based on the selected investment
    approach.
    """
)


# ============================================================
# INVESTMENT STRATEGIES
# ============================================================

st.subheader("Investment Strategies")

st.markdown(
    """
    ### 💎 GARP (Recommended)
    Growth At A Reasonable Price.

    Focuses on quality companies with solid growth
    trading at attractive valuations.

    ### ⭐ Core
    Balanced multi-factor investing.

    ### 💰 Dividend
    Income-oriented investing.

    ### 🏷️ Value
    Valuation-focused investing.

    ### 📈 Growth
    Revenue and earnings acceleration.

    ### 🚀 Momentum
    Trend-following and relative strength.

    ### 🛡️ Quality
    Financial strength and consistency.
    """
)


# ============================================================
# TECHNICAL ANALYSIS
# ============================================================

st.subheader("Technical Analysis")

st.markdown(
    """
    StockChoice incorporates technical indicators
    alongside fundamental analysis.

    Current technical inputs include:

    - 50-Day Moving Average
    - 200-Day Moving Average
    - Trend Classification
    - Relative Price Strength
    - Historical Performance

    Trend classifications include:

    - Strong Uptrend
    - Uptrend
    - Neutral
    - Downtrend
    - Strong Downtrend
    """
)


# ============================================================
# DATA SOURCES
# ============================================================

st.subheader("Data Sources")

st.markdown(
    """
    Market data and company information are sourced
    from publicly available financial data providers.

    Sources may include:

    - Yahoo Finance
    - Company Financial Filings
    - Historical Price Data
    - Market Statistics

    Information may occasionally be delayed,
    incomplete, or subject to change.
    """
)


# ============================================================
# IMPORTANT DISCLAIMER
# ============================================================

st.subheader("Important Disclaimer")

st.warning(
    """
    StockChoice is provided for educational and
    research purposes only.

    Nothing within this application should be
    considered financial, investment, tax,
    accounting, or legal advice.

    Investors should perform their own due
    diligence before making any investment
    decisions.

    Past performance does not guarantee future
    results.
    """
)


# ============================================================
# VERSION
# ============================================================

st.subheader("Version Information")

col1, col2 = st.columns(2)

with col1:

    st.metric(
        "Version",
        "1.0"
    )

with col2:

    st.metric(
        "Default Strategy",
        "💎 GARP"
    )


# ============================================================
# ROADMAP
# ============================================================

with st.expander("Future Roadmap"):

    st.markdown(
        """
        Planned enhancements include:

        - Watchlists
        - Portfolio Builder
        - Portfolio Analysis
        - Sector Rankings
        - Market Breadth Indicators
        - Advanced Screening Filters
        - AI-Powered Stock Explanations
        - Portfolio Tracking
        - ETF Analysis
        - Strategy Backtesting
        """
    )


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "StockChoice • The right stock for the right strategy."
)
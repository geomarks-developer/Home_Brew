import streamlit as st

from config import (
    ETF_SCORE_WEIGHTS,
    PERFORMANCE_WINDOWS,
    PORTFOLIO_MODELS,
    SECTOR_SCORE_WEIGHTS,
    SMA_LONG,
    SMA_SHORT,
    RSI_PERIOD,
)


# =========================================================
# HEADER
# =========================================================

st.title("📖 Methodology")

st.caption(
    "How MarketScope ETF evaluates ETFs, identifies trends, "
    "ranks sectors, and constructs model portfolios."
)

st.info(
    "MarketScope ETF uses a rules-based quantitative approach. "
    "Scores and rankings are designed as research tools and should "
    "not be interpreted as predictions or investment recommendations."
)


# =========================================================
# OVERVIEW
# =========================================================

st.markdown("## MarketScope ETF Framework")

st.write(
    """
    MarketScope ETF combines price performance, technical trends,
    historical risk, liquidity, fund characteristics, and relative
    strength into a structured framework for comparing ETFs.

    The application separates the analysis into several layers:

    1. **ETF Analysis** evaluates individual ETFs.
    2. **Sector Analysis** compares major market sectors.
    3. **Relative Strength** measures performance against the primary benchmark.
    4. **Portfolio Models** combine highly ranked ETFs into diversified model allocations.
    """
)


# =========================================================
# ETF UNIVERSE
# =========================================================

st.markdown("---")

st.markdown("## ETF Universe")

st.write(
    """
    The MarketScope ETF universe is organized into broad investment
    categories rather than treating every ETF as interchangeable.

    Current categories include:
    """
)

st.markdown(
    """
    - Broad Market
    - Sector
    - Growth
    - Value
    - Dividend
    - International
    - Bonds
    - Real Estate
    - Commodities
    - Factor / Quality
    - Thematic / Industry
    """
)

st.write(
    """
    An ETF may belong to more than one category. This allows the
    Screener, Compare page, ETF Explorer, and Portfolio Builder to
    evaluate the same ETF in different investment contexts.
    """
)


# =========================================================
# PERFORMANCE
# =========================================================

st.markdown("---")

st.markdown("## Performance Analysis")

st.write(
    """
    MarketScope calculates percentage price returns over multiple
    periods so that both recent momentum and longer-term performance
    can be evaluated.
    """
)

performance_data = [
    {
        "Period": label,
        "Approximate Trading Days":
            str(window),
    }
    for label, window in PERFORMANCE_WINDOWS.items()
]

st.dataframe(
    performance_data,
    width="stretch",
    hide_index=True,
)

st.caption(
    "YTD is calculated from the first available trading price "
    "of the current calendar year rather than using a fixed "
    "number of trading days."
)


# =========================================================
# MOVING AVERAGES
# =========================================================

st.markdown("---")

st.markdown("## Trend Analysis")

st.write(
    f"""
    MarketScope uses the **{SMA_SHORT}-day** and
    **{SMA_LONG}-day simple moving averages (SMA)** to help
    evaluate an ETF's intermediate and long-term price trend.

    The engine considers relationships including:

    - Price versus SMA {SMA_SHORT}
    - Price versus SMA {SMA_LONG}
    - SMA {SMA_SHORT} versus SMA {SMA_LONG}
    - Recent price performance
    """
)

st.markdown("### Trend Classifications")

trend_data = [
    {
        "Trend": "Strong Uptrend",
        "Interpretation":
            "Price and moving-average structure indicate a strong positive trend.",
    },
    {
        "Trend": "Uptrend",
        "Interpretation":
            "Price is trading above important trend levels.",
    },
    {
        "Trend": "Neutral",
        "Interpretation":
            "Trend signals are mixed or inconclusive.",
    },
    {
        "Trend": "Downtrend",
        "Interpretation":
            "Price is trading below important trend levels.",
    },
    {
        "Trend": "Strong Downtrend",
        "Interpretation":
            "Price and moving-average structure indicate a strong negative trend.",
    },
]

st.dataframe(
    trend_data,
    width="stretch",
    hide_index=True,
)


# =========================================================
# RSI
# =========================================================

st.markdown("---")

st.markdown("## Relative Strength Index")

st.write(
    f"""
    MarketScope calculates a **{RSI_PERIOD}-period RSI** as part
    of the technical trend analysis.

    RSI is evaluated alongside moving averages and price position.
    MarketScope does not use RSI by itself to determine whether an
    ETF should rank highly.
    """
)


# =========================================================
# MOMENTUM
# =========================================================

st.markdown("---")

st.markdown("## Momentum Score")

st.write(
    """
    The Momentum Score measures price strength across several
    time horizons.

    MarketScope currently emphasizes:
    """
)

momentum_data = [
    {
        "Period": "1 Month",
        "Weight": "15%",
    },
    {
        "Period": "3 Months",
        "Weight": "30%",
    },
    {
        "Period": "6 Months",
        "Weight": "30%",
    },
    {
        "Period": "1 Year",
        "Weight": "25%",
    },
]

st.dataframe(
    momentum_data,
    width="stretch",
    hide_index=True,
)

st.write(
    """
    Each period return is normalized into a score from 0 to 100
    before the weighted Momentum Score is calculated.

    This gives intermediate-term performance more influence than
    very short-term movements.
    """
)


# =========================================================
# TREND SCORE
# =========================================================

st.markdown("---")

st.markdown("## Trend Score")

st.write(
    """
    The Trend Score combines several technical conditions into
    a score from 0 to 100.

    The calculation considers:
    """
)

st.markdown(
    """
    - Price above or below the 50-day SMA
    - Price above or below the 200-day SMA
    - 50-day SMA relative to the 200-day SMA
    - RSI
    - Distance from the 52-week high
    """
)


# =========================================================
# RISK
# =========================================================

st.markdown("---")

st.markdown("## Risk Score")

st.write(
    """
    MarketScope evaluates historical risk using two primary measures:
    """
)

st.markdown(
    """
    **Annualized Volatility**

    Measures the variability of daily ETF returns and annualizes
    that historical variability.

    **Maximum Drawdown**

    Measures the largest historical percentage decline from a
    previous price peak within the available dataset.
    """
)

st.write(
    """
    Lower historical volatility and smaller maximum drawdowns
    generally produce higher MarketScope Risk Scores.
    """
)


# =========================================================
# LIQUIDITY
# =========================================================

st.markdown("---")

st.markdown("## Liquidity Score")

st.write(
    """
    MarketScope currently estimates liquidity using average daily
    share volume.

    Higher-volume ETFs receive stronger liquidity scores because
    trading activity is greater.

    Average share volume is only a simplified liquidity measure.
    The current model does not directly evaluate bid-ask spreads
    or dollar trading volume.
    """
)


# =========================================================
# FUND CHARACTERISTICS
# =========================================================

st.markdown("---")

st.markdown("## Cost and Dividend Scores")

st.write(
    """
    The scoring framework includes components for:

    **Cost Score**

    Lower ETF expense ratios receive higher scores.

    **Dividend Score**

    Higher reported distribution yields receive progressively
    higher scores within the current scoring model.
    """
)

st.warning(
    "Fund metadata may not yet be available for every ETF. "
    "When a component is unavailable, MarketScope excludes that "
    "component and re-normalizes the remaining ETF Score weights."
)


# =========================================================
# ETF SCORE
# =========================================================

st.markdown("---")

st.markdown("## MarketScope ETF Score")

st.write(
    """
    The overall ETF Score combines the individual analytical
    components into a score from 0 to 100.
    """
)

weight_data = []

for component, weight in ETF_SCORE_WEIGHTS.items():

    weight_data.append(
        {
            "Component":
                component.replace(
                    "_",
                    " ",
                ).title(),

            "Weight":
                f"{weight * 100:.0f}%",
        }
    )

st.dataframe(
    weight_data,
    width="stretch",
    hide_index=True,
)

st.write(
    """
    A higher ETF Score indicates stronger results across the
    MarketScope framework. It does not represent an expected
    investment return or probability of future success.
    """
)

st.info(
    "When one or more score components are unavailable, "
    "MarketScope calculates the overall score using the available "
    "components and proportionally re-normalizes their weights."
)


# =========================================================
# RELATIVE STRENGTH
# =========================================================

st.markdown("---")

st.markdown("## Relative Strength")

st.write(
    """
    Relative Strength compares an ETF's percentage return with
    the return of the MarketScope benchmark over the same period.

    The current primary benchmark is **SPY**.
    """
)

st.code(
    "Relative Strength = ETF Return - Benchmark Return",
    language=None,
)

st.write(
    """
    A positive value indicates that the ETF outperformed the
    benchmark during that period.

    A negative value indicates that the ETF underperformed the
    benchmark.
    """
)


# =========================================================
# SECTOR ANALYSIS
# =========================================================

st.markdown("---")

st.markdown("## Sector Analysis")

st.write(
    """
    MarketScope separately evaluates the major sector ETFs to help
    identify market leadership and areas of relative weakness.

    Sector analysis currently incorporates multiple performance
    periods together with the ETF trend score.
    """
)

sector_weight_data = []

for component, weight in (
    SECTOR_SCORE_WEIGHTS.items()
):

    label = (
        "Trend"
        if component == "trend"
        else component
    )

    sector_weight_data.append(
        {
            "Component": label,
            "Weight":
                f"{weight * 100:.0f}%",
        }
    )

st.dataframe(
    sector_weight_data,
    width="stretch",
    hide_index=True,
)

st.write(
    """
    The resulting rankings are used by the Summary and sector
    analysis features to identify leaders and laggards.
    """
)


# =========================================================
# PORTFOLIO BUILDER
# =========================================================

st.markdown("---")

st.markdown("## Portfolio Builder")

st.write(
    """
    The Portfolio Builder uses predefined asset-allocation models
    and the current MarketScope ETF rankings.

    For each category required by a portfolio model, MarketScope
    searches the available ETFs in that category and selects the
    highest-ranked qualifying ETF.

    When possible, the Portfolio Builder avoids selecting the same
    ETF for multiple allocation categories.
    """
)

st.markdown("### Available Models")

for model_name, allocation in (
    PORTFOLIO_MODELS.items()
):

    with st.expander(model_name):

        model_table = []

        for category, weight in (
            allocation.items()
        ):

            model_table.append(
                {
                    "Category": category,
                    "Allocation":
                        f"{weight * 100:.0f}%",
                }
            )

        st.dataframe(
            model_table,
            width="stretch",
            hide_index=True,
        )


# =========================================================
# WHOLE SHARES
# =========================================================

st.markdown("### Portfolio Share Calculation")

st.write(
    """
    The current Portfolio Builder uses whole ETF shares.

    MarketScope first calculates the target dollar allocation for
    each portfolio category and then determines how many whole
    shares can be purchased without exceeding that target.

    Any amount remaining after the whole-share calculation is
    displayed as cash.
    """
)


# =========================================================
# DATA AND CACHE
# =========================================================

st.markdown("---")

st.markdown("## Data Processing")

st.write(
    """
    MarketScope separates data collection from analysis.

    Market data is loaded centrally and shared throughout the
    application. The Summary, Screener, ETF Explorer, Compare,
    sector analysis, and Portfolio Builder pages operate from the
    shared dataset rather than independently requesting price data
    whenever a user changes pages.
    """
)

st.write(
    """
    Cached data is used to improve application performance and
    reduce unnecessary repeated data requests.
    """
)


# =========================================================
# LIMITATIONS
# =========================================================

st.markdown("---")

st.markdown("## Important Limitations")

st.markdown(
    """
    MarketScope ETF has several important limitations:

    - Historical performance does not predict future returns.
    - Technical indicators can generate false or conflicting signals.
    - MarketScope scores depend on the metrics available to the model.
    - ETF classifications can overlap.
    - Volatility and drawdown are historical measures.
    - Portfolio models are hypothetical and not personalized.
    - Fund metadata may be unavailable for some ETFs.
    - Scores can change as market prices and underlying data change.
    """
)


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.warning(
    """
    **Investment Risk**

    MarketScope ETF is provided for informational and educational
    purposes only.

    ETF rankings, sector rankings, MarketScope scores, model
    portfolios, technical indicators, and other information displayed
    by the application do not constitute investment, financial, tax,
    or legal advice.

    Investors should independently evaluate investments based on
    their own objectives, financial circumstances, time horizon,
    and tolerance for risk.
    """
)
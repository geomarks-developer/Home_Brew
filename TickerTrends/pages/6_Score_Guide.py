"""
TickerTrends Score Guide
========================

Explains:

    - The 100-point TickerTrends score
    - Technical scoring
    - Fundamental scoring
    - Trend states
    - Missing-data handling

This page is intentionally static and performs no market-data
requests or database calculations.
"""

from __future__ import annotations

import streamlit as st


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Score Guide | TickerTrends",
    page_icon="📖",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# NAVIGATION
# ============================================================

if st.button(
    "🏠 Home",
    key="home_button",
    use_container_width=False,
):
    st.switch_page("Summary.py")

# ============================================================
# HEADER
# ============================================================

st.title("📖 Score Guide")

st.caption(
    "How TickerTrends evaluates trend, quality, "
    "valuation, and performance."
)


# ============================================================
# PHILOSOPHY
# ============================================================

st.subheader("TickerTrends Philosophy")

st.info(
    "TickerTrends is built around a simple idea: "
    "follow healthy long-term trends while also considering "
    "the fundamental quality and valuation of the company."
)

st.markdown(
    """
**Trend first. Fundamentals second.**

TickerTrends does not attempt to predict short-term price
movements or generate frequent trading signals.

The **200-day moving average** establishes the long-term
trend.

The **50-day moving average** helps describe the
intermediate trend.

**RSI** helps identify whether momentum is healthy,
cooling, weak, or extended.

Fundamentals then provide additional context about
valuation, cash generation, and relative market performance.
"""
)


# ============================================================
# 100 POINT MODEL
# ============================================================

st.subheader("100-Point Score")

score_col1, score_col2 = st.columns(2)


with score_col1:

    st.metric(
        "Technical",
        "60 Points",
    )

    st.caption(
        "Long-term trend, moving averages, and RSI."
    )


with score_col2:

    st.metric(
        "Fundamentals",
        "40 Points",
    )

    st.caption(
        "Valuation, cash flow, and relative performance."
    )


st.markdown(
    """
### Total Score

**Technical Score + Fundamental Score = TickerTrends Score**

The maximum score is **100**.
"""
)


# ============================================================
# SCORE RATINGS
# ============================================================

st.subheader("Score Ratings")


rating_data = [
    ("90–100", "A+", "Exceptional"),
    ("85–89.9", "A", "Excellent"),
    ("80–84.9", "A-", "Very Strong"),
    ("75–79.9", "B+", "Strong"),
    ("70–74.9", "B", "Good"),
    ("65–69.9", "B-", "Above Average"),
    ("60–64.9", "C+", "Average"),
    ("50–59.9", "C", "Mixed"),
    ("40–49.9", "D", "Weak"),
    ("Below 40", "F", "Very Weak"),
]


for score_range, grade, label in rating_data:

    with st.container(
        border=True
    ):

        col1, col2, col3 = st.columns(
            [
                1.5,
                1,
                2,
            ]
        )

        with col1:
            st.write(
                f"**{score_range}**"
            )

        with col2:
            st.write(
                f"**{grade}**"
            )

        with col3:
            st.write(
                label
            )


# ============================================================
# TECHNICAL SCORE
# ============================================================

st.divider()

st.header("📈 Technical Score")

st.caption(
    "Maximum: 60 points"
)


# ============================================================
# PRICE VS 200D
# ============================================================

with st.expander(
    "Price vs 200-Day SMA • 20 Points",
    expanded=True,
):

    st.markdown(
        """
The 200-day moving average is the foundation of the
TickerTrends model.

| Condition | Points |
|---|---:|
| At or above 200D | **20** |
| 0% to 3% below | **12** |
| 3% to 7% below | **6** |
| More than 7% below | **0** |

A stock below its 200-day moving average is considered
to be in a **Bearish long-term regime**, even if other
technical indicators remain positive.
"""
    )


# ============================================================
# 200D SLOPE
# ============================================================

with st.expander(
    "200-Day SMA Slope • 10 Points"
):

    st.markdown(
        """
TickerTrends measures the percentage change in the
200-day moving average over the recent slope lookback.

| 200D Direction | Points |
|---|---:|
| Strongly rising | **10** |
| Rising | **8** |
| Slightly rising | **6** |
| Approximately flat | **4** |
| Falling | **2** |
| Strongly falling | **0** |

This helps distinguish a stock that is simply above its
200D from one whose long-term trend is actually improving.
"""
    )


# ============================================================
# PRICE VS 50D
# ============================================================

with st.expander(
    "Price vs 50-Day SMA • 10 Points"
):

    st.markdown(
        """
The 50-day moving average represents the intermediate
trend.

TickerTrends rewards stocks trading in a healthy position
above the 50D without rewarding extreme extension.

| Price Position | Points |
|---|---:|
| 0% to 10% above 50D | **10** |
| 10% to 15% above | **7** |
| More than 15% above | **4** |
| 0% to 3% below | **7** |
| 3% to 7% below | **4** |
| More than 7% below | **0** |
"""
    )


# ============================================================
# 50D VS 200D
# ============================================================

with st.expander(
    "50-Day vs 200-Day SMA • 10 Points"
):

    st.markdown(
        """
This measures the alignment of the intermediate and
long-term trends.

| Moving Average Alignment | Points |
|---|---:|
| 50D at least 5% above 200D | **10** |
| 50D above 200D | **8** |
| 50D within 3% below 200D | **4** |
| 50D more than 3% below 200D | **0** |

A 50D above the 200D supports a bullish trend structure.
"""
    )


# ============================================================
# RSI
# ============================================================

with st.expander(
    "RSI-14 • 10 Points"
):

    st.markdown(
        """
RSI is used to describe momentum within the larger trend.

TickerTrends does **not** treat RSI as a standalone
buy/sell indicator.

| RSI | Condition | Points |
|---|---|---:|
| 50–69.9 | Healthy Momentum | **10** |
| 40–49.9 | Cooled | **8** |
| 30–39.9 | Weak | **4** |
| 70–79.9 | Extended | **6** |
| 80+ | Highly Extended | **2** |
| Below 30 | Oversold / Weak | **0** |

A high RSI can reduce the score because TickerTrends is
designed to avoid rewarding stocks simply for becoming
increasingly stretched.
"""
    )


# ============================================================
# FUNDAMENTAL SCORE
# ============================================================

st.divider()

st.header("💼 Fundamental Score")

st.caption(
    "Maximum: 40 points"
)

st.markdown(
    """
TickerTrends intentionally uses only **four fundamental
measures**.

Each contributes a maximum of **10 points**.
"""
)


# ============================================================
# PE
# ============================================================

with st.expander(
    "P/E Ratio • 10 Points",
    expanded=True,
):

    st.markdown(
        """
P/E provides a simple measure of valuation relative to
earnings.

| P/E | Points |
|---|---:|
| 15 or below | **10** |
| 15–20 | **9** |
| 20–25 | **8** |
| 25–30 | **7** |
| 30–40 | **5** |
| 40–50 | **3** |
| Above 50 | **1** |

A lower P/E receives more points, but P/E represents only
10% of the overall TickerTrends score.
"""
    )


# ============================================================
# PEG
# ============================================================

with st.expander(
    "PEG Ratio • 10 Points"
):

    st.markdown(
        """
PEG considers valuation relative to expected earnings
growth.

| PEG | Points |
|---|---:|
| 1.0 or below | **10** |
| 1.0–1.5 | **8** |
| 1.5–2.0 | **6** |
| 2.0–2.5 | **4** |
| 2.5–3.0 | **2** |
| Above 3.0 | **1** |

This helps prevent the P/E ratio from being the only
valuation perspective in the model.
"""
    )


# ============================================================
# FCF
# ============================================================

with st.expander(
    "Free Cash Flow Margin • 10 Points"
):

    st.markdown(
        """
TickerTrends calculates Free Cash Flow from the company's
financial statements:

**Operating Cash Flow − Capital Expenditures**

FCF Margin is then calculated as:

**Free Cash Flow ÷ Revenue**

Using margin rather than raw dollars makes the measure more
comparable across companies of different sizes.

| FCF Margin | Points |
|---|---:|
| 20% or higher | **10** |
| 15–20% | **9** |
| 10–15% | **8** |
| 5–10% | **6** |
| 0–5% | **3** |
| Negative | **0** |
"""
    )


# ============================================================
# RELATIVE PERFORMANCE
# ============================================================

with st.expander(
    "Relative Performance • 10 Points"
):

    st.markdown(
        """
TickerTrends compares the stock's six-month price
performance with the S&P 500.

**Relative Performance = Stock Return − S&P 500 Return**

| Relative Performance | Points |
|---|---:|
| +15% or better | **10** |
| +5% to +15% | **8** |
| 0% to +5% | **6** |
| -5% to 0% | **4** |
| -15% to -5% | **2** |
| Below -15% | **0** |

This provides a simple measure of whether the stock has
been outperforming or underperforming the broader market.
"""
    )


# ============================================================
# TREND STATES
# ============================================================

st.divider()

st.header("🚦 Trend States")

st.caption(
    "Trend state and TickerTrends score are related, "
    "but they are not the same thing."
)


# ============================================================
# STRONG BULLISH
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 🟢 Strong Bullish"
    )

    st.write(
        "The long-term and intermediate trends are aligned."
    )

    st.caption(
        "Price is above the key moving averages, the 50D "
        "is above the 200D, the 200D is rising, and momentum "
        "is healthy without being excessively extended."
    )


# ============================================================
# BULLISH
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 🟢 Bullish"
    )

    st.write(
        "The long-term bullish regime remains intact."
    )

    st.caption(
        "Price remains above the 200D, but the stock does "
        "not currently meet the more specific Strong Bullish, "
        "Accumulation, Extended, or Weakening conditions."
    )


# ============================================================
# ACCUMULATION
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 🔵 Accumulation"
    )

    st.write(
        "A constructive pullback inside a healthy "
        "long-term trend."
    )

    st.caption(
        "Price remains above the 200D, the 50D remains "
        "above the 200D, the 200D is rising, and momentum "
        "has cooled near the 50-day moving average."
    )


# ============================================================
# EXTENDED
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 🟡 Extended"
    )

    st.write(
        "The bullish trend remains intact, but the stock "
        "appears stretched."
    )

    st.caption(
        "Extended is triggered by elevated RSI or significant "
        "distance above the 50-day moving average. Distance "
        "above the 200D alone does not create this state."
    )


# ============================================================
# WEAKENING
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 🟠 Weakening"
    )

    st.write(
        "The long-term regime has not completely broken, "
        "but technical conditions are deteriorating."
    )

    st.caption(
        "Examples include price dropping below the 50D, "
        "weak RSI, a falling 200D, or price approaching "
        "the 200-day moving average."
    )


# ============================================================
# BEARISH
# ============================================================

with st.container(
    border=True
):

    st.markdown(
        "### 🔴 Bearish"
    )

    st.write(
        "Price is below the 200-day moving average."
    )

    st.caption(
        "TickerTrends treats this as a break in the "
        "long-term bullish regime, even when some other "
        "technical or fundamental measures remain strong."
    )


# ============================================================
# SCORE VS TREND
# ============================================================

st.divider()

st.header("Score vs Trend")

st.warning(
    "A high score does not automatically mean Strong Bullish, "
    "and a fundamentally strong company can still be Bearish."
)


st.markdown(
    """
Consider the two questions separately:

### 1. What is the trend?

The **Trend State** describes the stock's current technical
condition.

### 2. How strong is the overall setup?

The **TickerTrends Score** combines technical condition with
valuation, cash generation, and relative performance.

This distinction is intentional.

A company can have excellent fundamentals while its stock
is below the 200D.

Likewise, a stock can have a very strong trend while its
valuation metrics are less attractive.
"""
)


# ============================================================
# EXAMPLE
# ============================================================

st.subheader(
    "Example"
)


example_col1, example_col2 = (
    st.columns(2)
)


with example_col1:

    st.metric(
        "Technical",
        "60 / 60",
    )


with example_col2:

    st.metric(
        "Fundamental",
        "32 / 40",
    )


st.metric(
    "TickerTrends Score",
    "92 / 100",
)


st.caption(
    "This would represent a technically very strong stock "
    "with strong, but not perfect, fundamentals."
)


# ============================================================
# MISSING DATA
# ============================================================

st.divider()

st.header("Missing Fundamental Data")

st.markdown(
    """
TickerTrends does **not** automatically treat missing
fundamental data as a poor result.

If one fundamental metric is unavailable, the remaining
available metrics can be normalized to the 40-point
fundamental scale.

At least **75% of the fundamental scoring data** must be
available for TickerTrends to calculate a complete
fundamental score.

With four equally weighted components, that generally means
at least **3 of the 4 fundamental measures** must be
available.

If coverage is below that threshold, the Fundamental Score
and Total Score are displayed as **N/A**.
"""
)


# ============================================================
# WHAT IS NOT INCLUDED
# ============================================================

st.divider()

st.header("What TickerTrends Leaves Out")

st.markdown(
    """
TickerTrends intentionally avoids adding large numbers of
indicators and financial ratios.

The core model does **not** use:

- MACD
- Stochastics
- Bollinger Bands
- ADX
- Analyst ratings
- Dividend yield scoring
- Growth / Value / Dividend classifications
- Short-term trading signals

The goal is not to include every available metric.

The goal is to make the stock's **long-term trend and basic
fundamental condition easy to understand**.
"""
)


# ============================================================
# WATCHLIST
# ============================================================

st.divider()

st.header("🔔 Watchlist Changes")

st.markdown(
    """
TickerTrends stores each stock's current trend state.

When a Watchlist stock moves from one state to another,
TickerTrends records the transition.

Examples:

**🟢 Bullish → 🔵 Accumulation**

**🟢 Bullish → 🟠 Weakening**

**🟠 Weakening → 🔴 Bearish**

**🔴 Bearish → 🟢 Bullish**

These alerts are intended to highlight meaningful changes
that deserve attention rather than encourage reactions to
every daily price movement.
"""
)


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "TickerTrends is a research and screening tool. "
    "Scores and trend states describe the rules of the "
    "TickerTrends model and are not guarantees of future "
    "investment performance."
)
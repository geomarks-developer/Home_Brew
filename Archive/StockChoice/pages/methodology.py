"""
StockChoice Methodology
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from strategy_config import (
    STRATEGIES,
    STRATEGY_ORDER,
)

from factor_config import (
    FACTORS,
    FACTOR_ORDER,
    FACTOR_METRICS,
)


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🧮 Methodology")

st.caption(
    "Understand how StockChoice evaluates and ranks stocks."
)


# ============================================================
# OVERVIEW
# ============================================================

st.markdown(
    """
    StockChoice uses a multi-factor investment model.

    Every stock receives individual scores for:

    - 📈 Growth
    - 🛡️ Quality
    - 🏷️ Value
    - 💰 Dividend
    - 🚀 Momentum
    - ⚠️ Risk

    Each factor is scored from:

    **0 - 100**

    Strategy scores are created by applying
    different weightings to these factors.
    """
)


# ============================================================
# FACTORS
# ============================================================

st.subheader("Factor Definitions")

factor_rows = []

for factor_key in FACTOR_ORDER:

    factor = FACTORS[factor_key]

    factor_rows.append({
        "Factor": f"{factor.icon} {factor.name}",
        "Description": factor.description,
    })

st.dataframe(
    pd.DataFrame(factor_rows),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# FACTOR METRICS
# ============================================================

st.subheader("Factor Components")

selected_factor = st.selectbox(
    "Factor",
    FACTOR_ORDER,
    format_func=lambda x:
        f"{FACTORS[x].icon} {FACTORS[x].name}"
)

metrics = FACTOR_METRICS.get(
    selected_factor,
    {}
)

metric_rows = []

for metric, weight in metrics.items():

    metric_rows.append({
        "Metric": metric.replace(
            "_",
            " "
        ).title(),
        "Weight": f"{weight * 100:.0f}%"
    })

st.dataframe(
    pd.DataFrame(metric_rows),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# STRATEGIES
# ============================================================

st.subheader("Investment Strategies")

selected_strategy = st.selectbox(
    "Strategy",
    STRATEGY_ORDER,
    format_func=lambda x:
        f"{STRATEGIES[x].icon} "
        f"{STRATEGIES[x].name}"
)

strategy = STRATEGIES[
    selected_strategy
]

st.info(
    f"{strategy.icon} "
    f"**{strategy.name}**\n\n"
    f"{strategy.description}"
)

if strategy.recommended:

    st.success(
        "⭐ Recommended Strategy"
    )


strategy_rows = []

for factor in FACTOR_ORDER:

    strategy_rows.append({
        "Factor":
            FACTORS[factor].name,

        "Weight":
            f"{strategy.weights[factor] * 100:.0f}%"
    })

st.dataframe(
    pd.DataFrame(strategy_rows),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# ALL STRATEGIES MATRIX
# ============================================================

st.subheader(
    "Strategy Comparison Matrix"
)

matrix_rows = []

for strategy_key in STRATEGY_ORDER:

    strategy = STRATEGIES[
        strategy_key
    ]

    row = {
        "Strategy":
            f"{strategy.icon} "
            f"{strategy.name}"
    }

    for factor in FACTOR_ORDER:

        row[
            FACTORS[factor].name
        ] = (
            f"{strategy.weights[factor] * 100:.0f}%"
        )

    matrix_rows.append(row)

st.dataframe(
    pd.DataFrame(matrix_rows),
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# RATING SCALE
# ============================================================

st.subheader(
    "Rating Scale"
)

rating_df = pd.DataFrame({

    "Score Range": [

        "95 - 100",

        "90 - 94",

        "80 - 89",

        "70 - 79",

        "60 - 69",

        "Below 60",
    ],

    "Rating": [

        "Elite",

        "Strong Buy",

        "Buy",

        "Accumulate",

        "Hold",

        "Avoid",
    ]
})

st.dataframe(
    rating_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# TREND STATUS
# ============================================================

st.subheader(
    "Trend Classification"
)

trend_df = pd.DataFrame({

    "Status": [

        "Strong Uptrend",

        "Uptrend",

        "Neutral",

        "Downtrend",

        "Strong Downtrend",
    ],

    "Definition": [

        "Price > SMA50 > SMA200",

        "Price > SMA200",

        "Mixed signals",

        "Price < SMA200",

        "Price < SMA50 < SMA200",
    ]
})

st.dataframe(
    trend_df,
    use_container_width=True,
    hide_index=True,
)


# ============================================================
# GARP FOCUS
# ============================================================

st.subheader(
    "Why GARP?"
)

st.markdown(
    """
    StockChoice is built around the concept of:

    **💎 Growth At A Reasonable Price (GARP)**

    GARP seeks companies that combine:

    - Strong business growth
    - High quality operations
    - Reasonable valuation
    - Positive momentum
    - Controlled risk

    Rather than chasing the fastest-growing stocks
    or the cheapest stocks, GARP attempts to find
    businesses capable of compounding value over
    long periods of time.

    It is the recommended starting strategy
    for most investors using StockChoice.
    """
)
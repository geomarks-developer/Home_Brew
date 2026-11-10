"""
StockChoice Dashboard
"""

from __future__ import annotations

import streamlit as st

from universe_scorer import (
    get_top_stocks,
)

from strategy_config import (
    get_strategy,
)


# ============================================================
# PAGE HEADER
# ============================================================

st.title("📊 Dashboard")

st.caption(
    "Market overview and top-ranked opportunities."
)


# ============================================================
# DEFAULT SETTINGS
# ============================================================

DEFAULT_UNIVERSE = "all"

DEFAULT_TOP = 10


# ============================================================
# STRATEGY OVERVIEW
# ============================================================

st.subheader(
    "Investment Strategies"
)

strategy_cols = st.columns(7)

strategies = [

    "garp",
    "core",
    "dividend",
    "value",
    "growth",
    "momentum",
    "quality",

]

for idx, strategy_key in enumerate(strategies):

    strategy = get_strategy(
        strategy_key
    )

    with strategy_cols[idx]:

        st.metric(
            strategy.icon,
            strategy.name
        )

        if strategy.recommended:

            st.caption(
                "⭐ Recommended"
            )


# ============================================================
# TOP GARP STOCKS
# ============================================================

st.subheader(
    "💎 Top GARP Stocks"
)

with st.spinner(
    "Loading GARP rankings..."
):

    try:

        garp_df = get_top_stocks(
            universe=DEFAULT_UNIVERSE,
            strategy="garp",
            top_n=DEFAULT_TOP,
        )

        if not garp_df.empty:

            st.dataframe(

                garp_df[
                    [

                        "rank",

                        "ticker",

                        "strategy_score",

                        "rating",

                        "trend",

                    ]

                ],

                use_container_width=True,
                hide_index=True,
            )

        else:

            st.warning(
                "No GARP data available."
            )

    except Exception as ex:

        st.error(ex)


# ============================================================
# STRATEGY LEADERS
# ============================================================

st.subheader(
    "🏆 Strategy Leaders"
)

leader_cols = st.columns(6)

leader_config = [

    (
        "value",
        "🏷️ Value"
    ),

    (
        "growth",
        "📈 Growth"
    ),

    (
        "dividend",
        "💰 Dividend"
    ),

    (
        "quality",
        "🛡️ Quality"
    ),

    (
        "momentum",
        "🚀 Momentum"
    ),

    (
        "core",
        "⭐ Core"
    ),

]

for idx, (
    strategy_key,
    title
) in enumerate(
    leader_config
):

    with leader_cols[idx]:

        try:

            df = get_top_stocks(
                universe=DEFAULT_UNIVERSE,
                strategy=strategy_key,
                top_n=1,
            )

            if not df.empty:

                winner = df.iloc[0]

                st.metric(
                    title,
                    winner["ticker"]
                )

                st.caption(
                    f"Score: "
                    f"{winner['strategy_score']:.1f}"
                )

        except Exception:

            st.metric(
                title,
                "N/A"
            )


# ============================================================
# QUICK RESEARCH
# ============================================================

st.subheader(
    "🔬 Stocks To Research"
)

research_col1, research_col2 = st.columns(2)

with research_col1:

    try:

        quality_df = get_top_stocks(
            universe="all",
            strategy="quality",
            top_n=5,
        )

        st.markdown(
            "### 🛡️ Quality Leaders"
        )

        for _, row in quality_df.iterrows():

            st.write(

                f"{row['ticker']}  "

                f"({row['strategy_score']:.1f})"

            )

    except Exception:
        pass

with research_col2:

    try:

        value_df = get_top_stocks(
            universe="all",
            strategy="value",
            top_n=5,
        )

        st.markdown(
            "### 🏷️ Value Leaders"
        )

        for _, row in value_df.iterrows():

            st.write(

                f"{row['ticker']}  "

                f"({row['strategy_score']:.1f})"

            )

    except Exception:
        pass


# ============================================================
# PHILOSOPHY
# ============================================================

with st.expander(
    "About StockChoice"
):

    st.markdown(
        """
        StockChoice evaluates stocks using six
        independent factors:

        - 📈 Growth
        - 🛡️ Quality
        - 🏷️ Value
        - 💰 Dividend
        - 🚀 Momentum
        - ⚠️ Risk

        The flagship strategy is:

        **💎 GARP (Growth At A Reasonable Price)**

        designed to identify quality companies
        growing earnings while trading at
        reasonable valuations.
        """
    )
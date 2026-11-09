"""
StockChoice Screener

Main stock screening page.
"""

from __future__ import annotations

import streamlit as st

from strategy_config import (
    STRATEGY_ORDER,
    get_strategy,
)

from stock_universe import (
    DEFAULT_UNIVERSE,
    get_available_universes,
    get_universe_name,
)

from universe_scorer import (
    get_top_stocks,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.title("🔎 Stock Screener")

st.caption(
    "Screen stocks using GARP, Core, Dividend, "
    "Value, Growth, Momentum and Quality strategies."
)


# ============================================================
# FILTERS
# ============================================================

col1, col2, col3 = st.columns(3)

with col1:

    strategy = st.selectbox(
        "Strategy",
        STRATEGY_ORDER,
        index=0,
        format_func=lambda x:
            f"{get_strategy(x).icon} "
            f"{get_strategy(x).name}"
    )

with col2:

    universe = st.selectbox(
        "Universe",
        get_available_universes(),
        index=get_available_universes().index(
            DEFAULT_UNIVERSE
        ),
        format_func=get_universe_name
    )

with col3:

    top_n = st.selectbox(
        "Top Results",
        [10, 25, 50, 100],
        index=2
    )


# ============================================================
# STRATEGY DESCRIPTION
# ============================================================

selected_strategy = get_strategy(
    strategy
)

st.info(
    f"{selected_strategy.icon} "
    f"**{selected_strategy.name}**\n\n"
    f"{selected_strategy.description}"
)

if selected_strategy.recommended:
    st.success(
        "⭐ Recommended Strategy"
    )


# ============================================================
# RUN SCREEN
# ============================================================

if st.button(
    "Run Screen",
    type="primary",
    use_container_width=True,
):

    with st.spinner(
        "Scoring stocks..."
    ):

        try:

            df = get_top_stocks(
                universe=universe,
                strategy=strategy,
                top_n=top_n,
            )

            if df.empty:

                st.warning(
                    "No results returned."
                )

            else:

                display_columns = [

                    "rank",
                    "ticker",

                    "strategy_score",

                    "rating",

                    "growth_score",

                    "quality_score",

                    "value_score",

                    "dividend_score",

                    "momentum_score",

                    "risk_score",

                    "trend",
                ]

                st.subheader(
                    "Results"
                )

                st.dataframe(
                    df[display_columns],
                    use_container_width=True,
                    hide_index=True,
                )

                #
                # Summary Metrics
                #
                st.subheader(
                    "Summary"
                )

                c1, c2, c3, c4 = (
                    st.columns(4)
                )

                with c1:

                    st.metric(
                        "Stocks Returned",
                        len(df)
                    )

                with c2:

                    st.metric(
                        "Average Score",
                        round(
                            df[
                                "strategy_score"
                            ].mean(),
                            1,
                        )
                    )

                with c3:

                    st.metric(
                        "Top Score",
                        round(
                            df[
                                "strategy_score"
                            ].max(),
                            1,
                        )
                    )

                with c4:

                    st.metric(
                        "Strategy",
                        selected_strategy.name
                    )

                #
                # Download
                #
                csv = (
                    df.to_csv(
                        index=False
                    )
                    .encode("utf-8")
                )

                st.download_button(
                    "Download Results",
                    csv,
                    file_name=
                    f"{strategy}_"
                    f"{universe}.csv",
                    mime="text/csv",
                )

        except Exception as ex:

            st.error(
                f"Screening failed: {ex}"
            )
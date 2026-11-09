"""
StockChoice Heatmap

Visual factor score heatmap.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd

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
# PAGE HEADER
# ============================================================

st.title("🔥 Heatmap")

st.caption(
    "Visualize stock rankings across all "
    "StockChoice factors."
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
        "Top Stocks",
        [25, 50, 100],
        index=1
    )


# ============================================================
# HEATMAP COLORS
# ============================================================

def color_score(value):

    if pd.isna(value):
        return ""

    if value >= 90:
        return (
            "background-color: "
            "#006400; color: white"
        )

    if value >= 80:
        return (
            "background-color: "
            "#228B22; color: white"
        )

    if value >= 70:
        return (
            "background-color: "
            "#90EE90; color: black"
        )

    if value >= 60:
        return (
            "background-color: "
            "#FFFF99; color: black"
        )

    if value >= 50:
        return (
            "background-color: "
            "#FFA500; color: black"
        )

    return (
        "background-color: "
        "#FF6347; color: white"
    )


# ============================================================
# RUN HEATMAP
# ============================================================

if st.button(
    "Generate Heatmap",
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
                    "No data returned."
                )

            else:

                selected_strategy = (
                    get_strategy(
                        strategy
                    )
                )

                st.success(

                    f"{selected_strategy.icon} "

                    f"{selected_strategy.name}"
                )

                heatmap_cols = [

                    "rank",

                    "ticker",

                    "strategy_score",

                    "growth_score",

                    "quality_score",

                    "value_score",

                    "dividend_score",

                    "momentum_score",

                    "risk_score",
                ]

                display_df = df[
                    heatmap_cols
                ]

                styled_df = (
                    display_df
                    .style
                    .map(
                        color_score,
                        subset=[
                            "strategy_score",

                            "growth_score",

                            "quality_score",

                            "value_score",

                            "dividend_score",

                            "momentum_score",

                            "risk_score",
                        ]
                    )
                )

                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                )

                #
                # Top 10 Chart
                #
                st.subheader(
                    "Top Ranked Stocks"
                )

                chart_df = (
                    df.head(10)
                    .set_index(
                        "ticker"
                    )
                )

                st.bar_chart(
                    chart_df[
                        "strategy_score"
                    ]
                )

                #
                # Factor Averages
                #
                st.subheader(
                    "Universe Factor Averages"
                )

                factor_avg = pd.DataFrame({

                    "Growth": [
                        round(
                            df[
                                "growth_score"
                            ].mean(),
                            1
                        )
                    ],

                    "Quality": [
                        round(
                            df[
                                "quality_score"
                            ].mean(),
                            1
                        )
                    ],

                    "Value": [
                        round(
                            df[
                                "value_score"
                            ].mean(),
                            1
                        )
                    ],

                    "Dividend": [
                        round(
                            df[
                                "dividend_score"
                            ].mean(),
                            1
                        )
                    ],

                    "Momentum": [
                        round(
                            df[
                                "momentum_score"
                            ].mean(),
                            1
                        )
                    ],

                    "Risk": [
                        round(
                            df[
                                "risk_score"
                            ].mean(),
                            1
                        )
                    ],
                })

                st.bar_chart(
                    factor_avg.T
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
                    label="Download Heatmap",
                    data=csv,
                    file_name=
                    f"heatmap_"
                    f"{strategy}_"
                    f"{universe}.csv",
                    mime="text/csv",
                )

        except Exception as ex:

            st.error(
                f"Heatmap failed: {ex}"
            )
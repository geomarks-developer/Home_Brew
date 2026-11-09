"""
StockChoice Stock Explorer

Deep dive into a single stock.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from stock_scorer import score_stock

from strategy_config import (
    STRATEGY_ORDER,
    get_strategy,
)


# ============================================================
# PAGE HEADER
# ============================================================

st.title("🔬 Stock Explorer")

st.caption(
    "Analyze individual stocks using StockChoice factors."
)


# ============================================================
# INPUTS
# ============================================================

col1, col2 = st.columns([2, 1])

with col1:

    ticker = st.text_input(
        "Ticker",
        value="MSFT"
    ).upper()

with col2:

    strategy = st.selectbox(
        "Strategy",
        STRATEGY_ORDER,
        format_func=lambda x:
            f"{get_strategy(x).icon} "
            f"{get_strategy(x).name}"
    )


# ============================================================
# ANALYZE
# ============================================================

if st.button(
    "Analyze Stock",
    type="primary",
    use_container_width=True
):

    with st.spinner(
        f"Analyzing {ticker}..."
    ):

        try:

            stock_score, details = score_stock(
                ticker=ticker,
                strategy=strategy
            )

            factors = (
                stock_score.factor_scores
            )

            #
            # Top Summary
            #
            st.subheader(
                f"{ticker} Summary"
            )

            c1, c2, c3, c4 = st.columns(4)

            with c1:
                st.metric(
                    "Strategy Score",
                    round(
                        stock_score.strategy_score,
                        2
                    )
                )

            with c2:
                st.metric(
                    "Rating",
                    stock_score.rating
                )

            with c3:
                st.metric(
                    "Trend",
                    stock_score.trend_status
                )

            with c4:
                st.metric(
                    "Strategy",
                    get_strategy(
                        strategy
                    ).name
                )

            #
            # Factor Scores
            #
            st.subheader(
                "Factor Scores"
            )

            factor_df = pd.DataFrame({

                "Factor": [
                    "Growth",
                    "Quality",
                    "Value",
                    "Dividend",
                    "Momentum",
                    "Risk",
                ],

                "Score": [
                    round(factors.growth, 2),
                    round(factors.quality, 2),
                    round(factors.value, 2),
                    round(factors.dividend, 2),
                    round(factors.momentum, 2),
                    round(factors.risk, 2),
                ],
            })

            st.dataframe(
                factor_df,
                use_container_width=True,
                hide_index=True
            )

            #
            # Strengths / Weaknesses
            #
            scores = {

                "Growth": factors.growth,

                "Quality": factors.quality,

                "Value": factors.value,

                "Dividend": factors.dividend,

                "Momentum": factors.momentum,

                "Risk": factors.risk,
            }

            best = sorted(
                scores.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]

            worst = sorted(
                scores.items(),
                key=lambda x: x[1]
            )[:2]

            col1, col2 = st.columns(2)

            with col1:

                st.success(
                    f"✅ Strengths\n\n"
                    f"{best[0][0]} ({best[0][1]:.1f})\n\n"
                    f"{best[1][0]} ({best[1][1]:.1f})"
                )

            with col2:

                st.warning(
                    f"⚠️ Weaknesses\n\n"
                    f"{worst[0][0]} ({worst[0][1]:.1f})\n\n"
                    f"{worst[1][0]} ({worst[1][1]:.1f})"
                )

            #
            # Strategy Breakdown
            #
            st.subheader(
                "📊 Strategy Breakdown"
            )

            selected_strategy_obj = (
                get_strategy(strategy)
            )

            strategy_weights = (
                selected_strategy_obj.weights
            )

            breakdown_df = pd.DataFrame({

                "Factor": [
                    "Growth",
                    "Quality",
                    "Value",
                    "Dividend",
                    "Momentum",
                    "Risk",
                ],

                "Score": [
                    factors.growth,
                    factors.quality,
                    factors.value,
                    factors.dividend,
                    factors.momentum,
                    factors.risk,
                ],

                "Weight": [

                    strategy_weights["growth"] * 100,

                    strategy_weights["quality"] * 100,

                    strategy_weights["value"] * 100,

                    strategy_weights["dividend"] * 100,

                    strategy_weights["momentum"] * 100,

                    strategy_weights["risk"] * 100,
                ],
            })

            breakdown_df["Contribution"] = (

                breakdown_df["Score"]

                * (
                    breakdown_df["Weight"]
                    / 100
                )

            ).round(2)

            st.dataframe(
                breakdown_df,
                use_container_width=True,
                hide_index=True
            )

            st.success(

                f"{selected_strategy_obj.icon} "

                f"{selected_strategy_obj.name} Score = "

                f"{breakdown_df['Contribution'].sum():.2f}"
            )
            st.bar_chart(
                breakdown_df.set_index(
                    "Factor"
                )["Contribution"]
            )

            #
            # Technical Analysis
            #
            technical = (
                details["technical"]
            )

            st.subheader(
                "Technical Analysis"
            )

            t1, t2, t3, t4 = st.columns(4)

            with t1:

                st.metric(
                    "Price",
                    round(
                        technical["price"],
                        2
                    )
                )

            with t2:

                st.metric(
                    "SMA 50",
                    round(
                        technical["sma50"],
                        2
                    )
                )

            with t3:

                st.metric(
                    "SMA 200",
                    round(
                        technical["sma200"],
                        2
                    )
                )

            with t4:

                st.metric(
                    "% Above SMA200",
                    round(
                        technical[
                            "pct_above_sma200"
                        ],
                        2
                    )
                )

            #
            # Detail Tabs
            #
            tab1, tab2, tab3, tab4, tab5, tab6 = (
                st.tabs(
                    [
                        "Growth",
                        "Quality",
                        "Value",
                        "Dividend",
                        "Momentum",
                        "Risk",
                    ]
                )
            )

            with tab1:
                st.json(
                    details["growth"]
                )

            with tab2:
                st.json(
                    details["quality"]
                )

            with tab3:
                st.json(
                    details["value"]
                )

            with tab4:
                st.json(
                    details["dividend"]
                )

            with tab5:
                st.json(
                    details["momentum"]
                )

            with tab6:
                st.json(
                    details["risk"]
                )

        except Exception as ex:

            st.error(
                f"Error analyzing {ticker}: {ex}"
            )
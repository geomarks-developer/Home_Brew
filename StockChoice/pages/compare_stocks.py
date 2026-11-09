"""
StockChoice Compare Stocks

Compare multiple stocks using
StockChoice factor scoring.
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

st.title("⚖️ Compare Stocks")

st.caption(
    "Compare stocks across Growth, Quality, "
    "Value, Dividend, Momentum and Risk."
)


# ============================================================
# INPUTS
# ============================================================

ticker_input = st.text_area(
    "Tickers (comma separated)",
    value="MSFT,GOOGL,V,COST",
    height=100,
)

strategy = st.selectbox(
    "Strategy",
    STRATEGY_ORDER,
    index=0,
    format_func=lambda x:
        f"{get_strategy(x).icon} "
        f"{get_strategy(x).name}"
)

tickers = [

    ticker.strip().upper()

    for ticker in ticker_input.split(",")

    if ticker.strip()

]


# ============================================================
# RUN COMPARISON
# ============================================================

if st.button(
    "Compare Stocks",
    type="primary",
    use_container_width=True,
):

    results = []

    progress_bar = st.progress(0)

    total = len(tickers)

    for idx, ticker in enumerate(
        tickers,
        start=1
    ):

        try:

            stock_score, details = score_stock(
                ticker=ticker,
                strategy=strategy,
            )

            factors = (
                stock_score.factor_scores
            )

            results.append({

                "Ticker":
                    stock_score.ticker,

                "Strategy Score":
                    stock_score.strategy_score,

                "Rating":
                    stock_score.rating,

                "Trend":
                    stock_score.trend_status,

                "Growth":
                    factors.growth,

                "Quality":
                    factors.quality,

                "Value":
                    factors.value,

                "Dividend":
                    factors.dividend,

                "Momentum":
                    factors.momentum,

                "Risk":
                    factors.risk,

                "Price":
                    round(
                        details[
                            "technical"
                        ]["price"],
                        2,
                    ),
            })

        except Exception as ex:

            st.warning(
                f"Unable to score {ticker}: {ex}"
            )

        progress_bar.progress(
            idx / total
        )

    #
    # Results
    #
    if results:

        df = pd.DataFrame(
            results
        )

        df = df.sort_values(
            by="Strategy Score",
            ascending=False,
        )

        #
        # Winner
        #
        winner = df.iloc[0]

        st.success(

            f"🏆 Top Ranked: "
            f"{winner['Ticker']} "

            f"(Score "
            f"{winner['Strategy Score']:.1f})"
        )

        #
        # Main Table
        #
        st.subheader(
            "Comparison"
        )

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
        )

        #
        # Factor Comparison
        #
        st.subheader(
            "Factor Score Comparison"
        )

        factor_chart = (
            df.set_index("Ticker")[

                [

                    "Growth",

                    "Quality",

                    "Value",

                    "Dividend",

                    "Momentum",

                    "Risk",
                ]

            ]
        )

        st.bar_chart(
            factor_chart
        )

        #
        # Strategy Scores
        #
        st.subheader(
            "Strategy Score Ranking"
        )

        ranking_chart = (
            df.set_index("Ticker")[

                "Strategy Score"

            ]
        )

        st.bar_chart(
            ranking_chart
        )

        #
        # Export
        #
        csv = (
            df.to_csv(
                index=False
            )
            .encode("utf-8")
        )

        st.download_button(
            label="Download Comparison",
            data=csv,
            file_name=
                "stock_comparison.csv",
            mime="text/csv"
        )
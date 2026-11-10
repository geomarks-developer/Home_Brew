"""
StockChoice Universe Scorer

Scores every ticker in a universe
and returns ranked results.

Examples:

    score_universe(
        universe="all",
        strategy="garp"
    )

    score_universe(
        universe="sp500",
        strategy="quality"
    )
"""

from __future__ import annotations

import pandas as pd

from stock_scorer import score_stock

from stock_engine import (
    stock_score_to_dict,
)

from stock_universe import (
    get_universe,
)

import streamlit as st

# ============================================================
# SCORE SINGLE TICKER
# ============================================================

def score_ticker(
    ticker: str,
    strategy: str,
) -> dict | None:

    try:

        stock_score, details = score_stock(
            ticker=ticker,
            strategy=strategy,
        )

        row = stock_score_to_dict(
            stock_score
        )

        row["trend"] = (
            stock_score.trend_status
        )

        return row

    except Exception as ex:

        print(
            f"Error scoring {ticker}: {ex}"
        )

        return None


# ============================================================
# SCORE UNIVERSE
# ============================================================

def score_universe(
    universe: str = "all",
    strategy: str = "garp",
) -> pd.DataFrame:

    tickers = get_universe(
        universe
    )

    results = []

    progress_bar = st.progress(0)

    status_text = st.empty()

    total = len(tickers)

    for idx, ticker in enumerate(
        tickers,
        start=1
    ):

        status_text.text(
            f"Scoring {ticker} "
            f"({idx}/{total}) "
            f"- {round(idx/total*100)}%"
        )

        row = score_ticker(
            ticker=ticker,
            strategy=strategy,
        )

        if row:
            results.append(row)

        progress_bar.progress(
            idx / total
        )

    status_text.empty()
    progress_bar.empty()

    if not results:

        return pd.DataFrame()

    df = pd.DataFrame(
        results
    )

    df = df.sort_values(
        by="strategy_score",
        ascending=False,
    )

    df = df.reset_index(
        drop=True
    )

    df.insert(
        0,
        "rank",
        range(
            1,
            len(df) + 1
        )
    )

    return df


# ============================================================
# TOP N
# ============================================================

def get_top_stocks(
    universe: str = "all",
    strategy: str = "garp",
    top_n: int = 25,
) -> pd.DataFrame:

    df = score_universe(
        universe=universe,
        strategy=strategy,
    )

    return df.head(top_n)


# ============================================================
# SCREEN
# ============================================================

def run_screen(
    universe: str,
    strategy: str,
    min_score: float = 0,
    top_n: int = 100,
) -> pd.DataFrame:

    df = score_universe(
        universe=universe,
        strategy=strategy,
    )

    if df.empty:
        return df

    df = df[
        df["strategy_score"]
        >= min_score
    ]

    return df.head(
        top_n
    )


# ============================================================
# STRATEGY LEADERS
# ============================================================

def get_strategy_leaders(
    universe: str = "all",
) -> dict:

    strategies = [

        "garp",

        "core",

        "dividend",

        "value",

        "growth",

        "momentum",

        "quality",
    ]

    leaders = {}

    for strategy in strategies:

        try:

            df = get_top_stocks(
                universe=universe,
                strategy=strategy,
                top_n=1,
            )

            if not df.empty:

                leaders[
                    strategy
                ] = (
                    df.iloc[0]
                    .to_dict()
                )

        except Exception:
            pass

    return leaders


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    df = get_top_stocks(
        universe="sp500",
        strategy="garp",
        top_n=10,
    )

    print()

    print(
        df[
            [
                "rank",
                "ticker",
                "strategy_score",
                "rating",
                "trend",
            ]
        ]
    )
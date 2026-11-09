"""
StockChoice Momentum Factor

Measures:

    - 3 Month Return
    - 6 Month Return
    - 12 Month Return
    - Relative Strength
    - MA200 Strength
    - Trend Status

Returns:

    Momentum Score (0-100)
"""

from __future__ import annotations

import pandas as pd

from factor_config import MOMENTUM_METRICS
from technical import (
    calculate_technical_metrics,
    score_ma200_strength,
    score_trend_status,
)


# ============================================================
# RETURN CALCULATIONS
# ============================================================

def calculate_return(
    prices: pd.Series,
    periods_back: int
) -> float:

    if len(prices) <= periods_back:
        return 0.0

    current_price = float(prices.iloc[-1])

    previous_price = float(
        prices.iloc[-periods_back]
    )

    if previous_price <= 0:
        return 0.0

    return (
        (current_price - previous_price)
        / previous_price
        * 100
    )


# ============================================================
# SCORING
# ============================================================

def score_return(
    return_pct: float
) -> float:
    """
    Convert return percent into
    0-100 score.
    """

    if return_pct >= 50:
        return 100

    if return_pct >= 30:
        return 90

    if return_pct >= 20:
        return 80

    if return_pct >= 10:
        return 70

    if return_pct >= 0:
        return 60

    if return_pct >= -10:
        return 40

    if return_pct >= -20:
        return 20

    return 0


# ============================================================
# RELATIVE STRENGTH
# ============================================================

def score_relative_strength(
    return_12m: float
) -> float:
    """
    Placeholder implementation.

    Future enhancement:
    Compare stock performance
    against SPY.
    """

    return score_return(return_12m)


# ============================================================
# FACTOR CALCULATION
# ============================================================

def calculate_momentum_score(
    history_df: pd.DataFrame
) -> tuple[float, dict]:

    if history_df.empty:

        return 0.0, {}

    close = history_df["Close"]

    #
    # Returns
    #
    return_3m = calculate_return(
        close,
        63
    )

    return_6m = calculate_return(
        close,
        126
    )

    return_12m = calculate_return(
        close,
        252
    )

    #
    # Technical Metrics
    #
    technical = (
        calculate_technical_metrics(
            history_df
        )
    )

    #
    # Individual Scores
    #
    score_3m = score_return(
        return_3m
    )

    score_6m = score_return(
        return_6m
    )

    score_12m = score_return(
        return_12m
    )

    relative_strength_score = (
        score_relative_strength(
            return_12m
        )
    )

    ma200_score = (
        score_ma200_strength(
            technical.pct_above_sma200
        )
    )

    trend_score = (
        score_trend_status(
            technical.trend_status
        )
    )

    #
    # Weighted Composite
    #
    factor_score = (

        score_3m
        * MOMENTUM_METRICS["return_3m"]

        + score_6m
        * MOMENTUM_METRICS["return_6m"]

        + score_12m
        * MOMENTUM_METRICS["return_12m"]

        + relative_strength_score
        * MOMENTUM_METRICS["relative_strength"]

        + ma200_score
        * MOMENTUM_METRICS["ma200_strength"]

        + trend_score
        * MOMENTUM_METRICS["trend_status"]

    )

    details = {

        "return_3m":
            round(return_3m, 2),

        "return_6m":
            round(return_6m, 2),

        "return_12m":
            round(return_12m, 2),

        "relative_strength_score":
            round(
                relative_strength_score,
                2
            ),

        "ma200_score":
            round(
                ma200_score,
                2
            ),

        "trend_status":
            technical.trend_status,

        "trend_score":
            round(
                trend_score,
                2
            ),

        "pct_above_sma50":
            round(
                technical.pct_above_sma50,
                2
            ),

        "pct_above_sma200":
            round(
                technical.pct_above_sma200,
                2
            ),
    }

    return round(factor_score, 2), details
"""
StockChoice Technical Analysis

Provides:

- SMA 50
- SMA 200
- Price vs SMA 50
- Price vs SMA 200
- Trend Status
- Moving Average Scores

Used by:

    momentum.py
    risk.py
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


# ============================================================
# DATA CLASS
# ============================================================

@dataclass
class TechnicalMetrics:

    current_price: float

    sma50: float
    sma200: float

    pct_above_sma50: float
    pct_above_sma200: float

    trend_status: str

    ma50_above_ma200: bool


# ============================================================
# HELPERS
# ============================================================

def percent_difference(
    current: float,
    reference: float
) -> float:
    """
    Percent difference from reference value.
    """

    if reference == 0:
        return 0.0

    return (
        (current - reference)
        / reference
        * 100
    )
def score_ma200_strength(
    pct_above_sma200: float
) -> float:
    """
    Momentum-oriented score.
    """

    if pct_above_sma200 >= 20:
        return 100

    if pct_above_sma200 >= 10:
        return 90

    if pct_above_sma200 >= 0:
        return 75

    if pct_above_sma200 >= -10:
        return 50

    if pct_above_sma200 >= -20:
        return 25

    return 0

def score_trend_status(
    trend_status: str
) -> float:

    mapping = {
        "Strong Uptrend": 100,
        "Uptrend": 80,
        "Neutral": 60,
        "Downtrend": 30,
        "Strong Downtrend": 0,
        "Unknown": 0,
    }

    return mapping.get(
        trend_status,
        0
    )


# ============================================================
# MOVING AVERAGES
# ============================================================

def calculate_sma(
    prices: pd.Series,
    period: int
) -> float:

    if len(prices) < period:
        return np.nan

    return float(
        prices.tail(period).mean()
    )


# ============================================================
# TREND STATUS
# ============================================================

def determine_trend_status(
    current_price: float,
    sma50: float,
    sma200: float
) -> str:
    """
    Categorize trend.
    """

    if np.isnan(sma50) or np.isnan(sma200):
        return "Unknown"

    # Strong Uptrend
    if (
        current_price > sma50
        and sma50 > sma200
    ):
        return "Strong Uptrend"

    # Uptrend
    if (
        current_price > sma200
        and sma50 >= sma200
    ):
        return "Uptrend"

    # Strong Downtrend
    if (
        current_price < sma50
        and sma50 < sma200
    ):
        return "Strong Downtrend"

    # Downtrend
    if current_price < sma200:
        return "Downtrend"

    return "Neutral"


# ============================================================
# BUILD METRICS
# ============================================================

def calculate_technical_metrics(
    history_df: pd.DataFrame
) -> TechnicalMetrics:
    """
    Expects dataframe from yfinance.history()

    Requires:
        Close
    """

    if history_df.empty:

        return TechnicalMetrics(
            current_price=0,
            sma50=0,
            sma200=0,
            pct_above_sma50=0,
            pct_above_sma200=0,
            trend_status="Unknown",
            ma50_above_ma200=False,
        )

    close = history_df["Close"]

    current_price = float(close.iloc[-1])

    sma50 = calculate_sma(close, 50)

    sma200 = calculate_sma(close, 200)

    pct_above_sma50 = percent_difference(
        current_price,
        sma50
    )

    pct_above_sma200 = percent_difference(
        current_price,
        sma200
    )

    trend_status = determine_trend_status(
        current_price=current_price,
        sma50=sma50,
        sma200=sma200,
    )

    return TechnicalMetrics(
        current_price=current_price,
        sma50=sma50,
        sma200=sma200,
        pct_above_sma50=pct_above_sma50,
        pct_above_sma200=pct_above_sma200,
        trend_status=trend_status,
        ma50_above_ma200=sma50 > sma200,
    )


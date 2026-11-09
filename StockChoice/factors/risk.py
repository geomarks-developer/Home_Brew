"""
StockChoice Risk Factor

Measures:

    - Beta
    - Volatility
    - Debt to Equity
    - Maximum Drawdown
    - Distance From 200 DMA

Returns:

    Risk Score (0-100)

Higher score = lower risk
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from factor_config import RISK_METRICS
from technical import calculate_technical_metrics


# ============================================================
# VOLATILITY
# ============================================================

def calculate_volatility(
    close: pd.Series
) -> float:

    returns = close.pct_change().dropna()

    if returns.empty:
        return 0.0

    return float(
        returns.std() * np.sqrt(252) * 100
    )


# ============================================================
# MAX DRAWDOWN
# ============================================================

def calculate_max_drawdown(
    close: pd.Series
) -> float:

    if close.empty:
        return 0.0

    rolling_max = close.cummax()

    drawdown = (
        (close - rolling_max)
        / rolling_max
        * 100
    )

    return float(drawdown.min())


# ============================================================
# SCORING
# ============================================================

def score_beta(
    beta: float | None
) -> float:

    if beta is None:
        return 50

    beta = abs(beta)

    if beta <= 0.60:
        return 100

    if beta <= 0.80:
        return 90

    if beta <= 1.00:
        return 80

    if beta <= 1.20:
        return 70

    if beta <= 1.50:
        return 50

    if beta <= 2.00:
        return 25

    return 0


def score_volatility(
    volatility: float
) -> float:

    if volatility <= 15:
        return 100

    if volatility <= 20:
        return 90

    if volatility <= 25:
        return 80

    if volatility <= 30:
        return 70

    if volatility <= 40:
        return 50

    if volatility <= 50:
        return 25

    return 0


def score_debt_to_equity(
    debt_to_equity: float | None
) -> float:

    if debt_to_equity is None:
        return 50

    if debt_to_equity <= 0.25:
        return 100

    if debt_to_equity <= 0.50:
        return 90

    if debt_to_equity <= 1.00:
        return 75

    if debt_to_equity <= 2.00:
        return 50

    if debt_to_equity <= 3.00:
        return 25

    return 0


def score_max_drawdown(
    drawdown: float
) -> float:

    drawdown = abs(drawdown)

    if drawdown <= 10:
        return 100

    if drawdown <= 20:
        return 85

    if drawdown <= 30:
        return 70

    if drawdown <= 40:
        return 50

    if drawdown <= 50:
        return 25

    return 0


def score_distance_from_ma200(
    pct_above_ma200: float
) -> float:

    if pct_above_ma200 >= 15:
        return 100

    if pct_above_ma200 >= 5:
        return 90

    if pct_above_ma200 >= 0:
        return 80

    if pct_above_ma200 >= -10:
        return 60

    if pct_above_ma200 >= -20:
        return 30

    return 0


# ============================================================
# FACTOR CALCULATION
# ============================================================

def calculate_risk_score(
    history_df: pd.DataFrame,
    beta: float | None = None,
    debt_to_equity: float | None = None,
) -> tuple[float, dict]:

    if history_df.empty:
        return 0.0, {}

    close = history_df["Close"]

    volatility = calculate_volatility(
        close
    )

    max_drawdown = calculate_max_drawdown(
        close
    )

    technical = calculate_technical_metrics(
        history_df
    )

    beta_score = score_beta(beta)

    volatility_score = score_volatility(
        volatility
    )

    debt_score = score_debt_to_equity(
        debt_to_equity
    )

    drawdown_score = score_max_drawdown(
        max_drawdown
    )

    distance_score = (
        score_distance_from_ma200(
            technical.pct_above_sma200
        )
    )

    risk_score = (

        beta_score
        * RISK_METRICS["beta"]

        + volatility_score
        * RISK_METRICS["volatility"]

        + debt_score
        * RISK_METRICS["debt_to_equity"]

        + drawdown_score
        * RISK_METRICS["max_drawdown"]

        + distance_score
        * RISK_METRICS["distance_from_ma200"]

    )

    details = {

        "beta":
            beta,

        "beta_score":
            round(beta_score, 2),

        "volatility":
            round(volatility, 2),

        "volatility_score":
            round(volatility_score, 2),

        "debt_to_equity":
            debt_to_equity,

        "debt_score":
            round(debt_score, 2),

        "max_drawdown":
            round(max_drawdown, 2),

        "drawdown_score":
            round(drawdown_score, 2),

        "pct_above_sma200":
            round(
                technical.pct_above_sma200,
                2
            ),

        "distance_score":
            round(distance_score, 2),
    }

    return round(risk_score, 2), details
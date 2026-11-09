"""
StockChoice Core Scoring Engine

Responsibilities
----------------
1. Store factor scores
2. Calculate strategy scores
3. Generate ratings
4. Provide stock scoring results

Factor calculations are handled by:

    factors/growth.py
    factors/quality.py
    factors/value.py
    factors/dividend.py
    factors/momentum.py
    factors/risk.py

Strategy weights come from:

    strategy_config.py
"""

from __future__ import annotations

from dataclasses import dataclass

from strategy_config import get_strategy


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class FactorScores:
    growth: float = 0.0
    quality: float = 0.0
    value: float = 0.0
    dividend: float = 0.0
    momentum: float = 0.0
    risk: float = 0.0


@dataclass
class StockScore:
    ticker: str

    strategy: str

    strategy_score: float

    rating: str

    trend_status: str

    factor_scores: FactorScores


# ============================================================
# RATING ENGINE
# ============================================================

def get_rating(score: float) -> str:
    """
    Convert numeric score into rating.
    """

    if score >= 95:
        return "Elite"

    if score >= 90:
        return "Strong Buy"

    if score >= 80:
        return "Buy"

    if score >= 70:
        return "Accumulate"

    if score >= 60:
        return "Hold"

    return "Avoid"


# ============================================================
# STRATEGY SCORE
# ============================================================

def calculate_strategy_score(
    factor_scores: FactorScores,
    strategy_key: str
) -> float:
    """
    Calculate weighted strategy score.
    """

    strategy = get_strategy(strategy_key)

    score = (
        factor_scores.growth
        * strategy.weights["growth"]

        + factor_scores.quality
        * strategy.weights["quality"]

        + factor_scores.value
        * strategy.weights["value"]

        + factor_scores.dividend
        * strategy.weights["dividend"]

        + factor_scores.momentum
        * strategy.weights["momentum"]

        + factor_scores.risk
        * strategy.weights["risk"]
    )

    return round(score, 2)


# ============================================================
# STOCK SCORE BUILDER
# ============================================================

def build_stock_score(
    ticker: str,
    strategy_key: str,
    factor_scores: FactorScores,
    trend_status: str = "Unknown"
) -> StockScore:
    """
    Build complete stock score object.
    """

    strategy_score = calculate_strategy_score(
        factor_scores=factor_scores,
        strategy_key=strategy_key
    )

    rating = get_rating(strategy_score)

    return StockScore(
        ticker=ticker,
        strategy=strategy_key,
        strategy_score=strategy_score,
        rating=rating,
        trend_status=trend_status,
        factor_scores=factor_scores
    )


# ============================================================
# EXPORT HELPERS
# ============================================================

def stock_score_to_dict(
    stock_score: StockScore
) -> dict:

    return {
        "ticker": stock_score.ticker,
        "strategy": stock_score.strategy,
        "strategy_score": stock_score.strategy_score,
        "rating": stock_score.rating,
        "trend_status": stock_score.trend_status,

        "growth_score":
            stock_score.factor_scores.growth,

        "quality_score":
            stock_score.factor_scores.quality,

        "value_score":
            stock_score.factor_scores.value,

        "dividend_score":
            stock_score.factor_scores.dividend,

        "momentum_score":
            stock_score.factor_scores.momentum,

        "risk_score":
            stock_score.factor_scores.risk,
    }
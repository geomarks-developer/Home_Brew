"""
MarketScope Growth scoring engine.

This module converts normalized stock data into four 0-100 category scores:
Growth, Quality, Valuation, and Momentum. It then calculates a weighted
Overall Score using the settings in config.py.

Important design choice:
Missing values are excluded from the applicable weighted calculation rather
than being scored as zero. Coverage values show how much of each score was
supported by available data.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from config import (
    CATEGORY_WEIGHTS,
    GROWTH_SCORE_RATINGS,
    GROWTH_THRESHOLDS,
    GROWTH_WEIGHTS,
    QUALITY_THRESHOLDS,
    QUALITY_WEIGHTS,
    RATING_THRESHOLDS,
    VALUATION_SCORE_RATINGS,
    VALUATION_THRESHOLDS,
    VALUATION_WEIGHTS,
    MOMENTUM_WEIGHTS,
)


# =========================================================
# General helpers
# =========================================================

MISSING_STRINGS = {"", "-", "--", "n/a", "na", "none", "null", "nan"}


def safe_float(value: Any) -> float:
    """Convert a value to float, returning np.nan when it is unusable."""
    if value is None:
        return np.nan

    if isinstance(value, str):
        cleaned = value.strip().lower().replace(",", "")
        if cleaned in MISSING_STRINGS:
            return np.nan
        if cleaned.endswith("%"):
            try:
                return float(cleaned[:-1]) / 100.0
            except ValueError:
                return np.nan
        value = cleaned

    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan

    return result if np.isfinite(result) else np.nan


def clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    """Limit a numeric score to the requested range."""
    return float(max(low, min(high, value)))


def first_value(record: Mapping[str, Any], *keys: str) -> float:
    """Return the first usable numeric value found for a list of aliases."""
    for key in keys:
        if key in record:
            value = safe_float(record[key])
            if not np.isnan(value):
                return value
    return np.nan


def weighted_available_score(
    scores: Mapping[str, float],
    weights: Mapping[str, float],
) -> tuple[float, float]:
    """
    Calculate a weighted average using only available component scores.

    Returns:
        score: Weighted score from 0 to 100, or np.nan if nothing is available.
        coverage: Fraction of configured weight supported by available data.
    """
    total_configured_weight = sum(max(0.0, float(w)) for w in weights.values())
    if total_configured_weight <= 0:
        return np.nan, 0.0

    weighted_total = 0.0
    available_weight = 0.0

    for key, weight in weights.items():
        weight = max(0.0, float(weight))
        score = safe_float(scores.get(key))
        if weight > 0 and not np.isnan(score):
            weighted_total += score * weight
            available_weight += weight

    if available_weight <= 0:
        return np.nan, 0.0

    score = weighted_total / available_weight
    coverage = available_weight / total_configured_weight
    return round(clamp(score), 1), round(clamp(coverage, 0.0, 1.0), 3)


def interpolate_score(value: float, points: list[tuple[float, float]]) -> float:
    """Linearly interpolate a score from ordered (value, score) points."""
    value = safe_float(value)
    if np.isnan(value):
        return np.nan

    points = sorted(points, key=lambda item: item[0])
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    return round(clamp(float(np.interp(value, x_values, y_values))), 1)


def score_higher_is_better(value: float, thresholds: Mapping[str, float]) -> float:
    """Score metrics where larger values are generally preferable."""
    value = safe_float(value)
    if np.isnan(value):
        return np.nan

    minimum = safe_float(thresholds.get("minimum", 0.0))
    moderate = safe_float(thresholds.get("moderate"))
    strong = safe_float(thresholds.get("strong"))
    excellent = safe_float(thresholds.get("excellent"))

    if any(np.isnan(x) for x in (minimum, moderate, strong, excellent)):
        return np.nan

    lower_anchor = minimum - max(abs(moderate - minimum), 0.05)
    upper_anchor = excellent + max(abs(excellent - strong), 0.05)

    return interpolate_score(
        value,
        [
            (lower_anchor, 0.0),
            (minimum, 25.0),
            (moderate, 50.0),
            (strong, 75.0),
            (excellent, 95.0),
            (upper_anchor, 100.0),
        ],
    )


def score_quality_metric(value: float, thresholds: Mapping[str, float]) -> float:
    """Score a quality metric using moderate, strong, and excellent levels."""
    expanded = {
        "minimum": 0.0,
        "moderate": thresholds.get("moderate"),
        "strong": thresholds.get("strong"),
        "excellent": thresholds.get("excellent"),
    }
    return score_higher_is_better(value, expanded)


def score_lower_is_better(value: float, thresholds: Mapping[str, float]) -> float:
    """Score valuation metrics where lower positive values are preferable."""
    value = safe_float(value)
    if np.isnan(value) or value <= 0:
        return np.nan

    excellent = safe_float(thresholds.get("excellent"))
    good = safe_float(thresholds.get("good"))
    fair = safe_float(thresholds.get("fair"))
    expensive = safe_float(thresholds.get("expensive"))

    if any(np.isnan(x) for x in (excellent, good, fair, expensive)):
        return np.nan

    upper_anchor = expensive + max(expensive - fair, excellent)

    return interpolate_score(
        value,
        [
            (0.0, 100.0),
            (excellent, 95.0),
            (good, 80.0),
            (fair, 60.0),
            (expensive, 30.0),
            (upper_anchor, 0.0),
        ],
    )


def rating_from_thresholds(score: float, thresholds: Mapping[int, str]) -> str:
    """Return the label associated with the highest threshold met."""
    score = safe_float(score)
    if np.isnan(score):
        return "Insufficient Data"

    for minimum_score in sorted(thresholds, reverse=True):
        if score >= minimum_score:
            return thresholds[minimum_score]

    return "Insufficient Data"


# =========================================================
# Growth scoring
# =========================================================


def calculate_growth_score(record: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate growth component scores and the combined Growth Score."""
    values = {
        "revenue_growth": first_value(record, "Revenue Growth", "revenueGrowth", "revenue_growth"),
        "earnings_growth": first_value(record, "Earnings Growth", "earningsGrowth", "earnings_growth"),
        "eps_growth": first_value(record, "EPS Growth", "epsGrowth", "eps_growth"),
        "forward_eps_growth": first_value(
            record,
            "Forward EPS Growth",
            "forwardEpsGrowth",
            "forward_eps_growth",
        ),
    }

    components = {
        key: score_higher_is_better(value, GROWTH_THRESHOLDS[key])
        for key, value in values.items()
    }
    score, coverage = weighted_available_score(components, GROWTH_WEIGHTS)

    return {
        "Growth Score": score,
        "Growth Coverage": coverage,
        "Growth Rating": rating_from_thresholds(score, GROWTH_SCORE_RATINGS),
        "Growth Components": components,
    }


# =========================================================
# Quality scoring
# =========================================================


def score_free_cash_flow(value: float) -> float:
    """Reward positive free cash flow without over-rewarding its raw size."""
    value = safe_float(value)
    if np.isnan(value):
        return np.nan
    if value > 0:
        return 100.0
    if value == 0:
        return 50.0
    return 0.0


def score_debt_control(record: Mapping[str, Any]) -> float:
    """
    Score balance-sheet debt using net debt as a percentage of market cap.

    Negative net debt means cash exceeds debt and receives the highest score.
    """
    debt = first_value(record, "Total Debt", "totalDebt", "total_debt")
    cash = first_value(record, "Total Cash", "totalCash", "total_cash")
    market_cap = first_value(record, "Market Cap", "marketCap", "market_cap")

    if np.isnan(debt) or np.isnan(market_cap) or market_cap <= 0:
        return np.nan

    cash = 0.0 if np.isnan(cash) else cash
    net_debt_ratio = (debt - cash) / market_cap

    return interpolate_score(
        net_debt_ratio,
        [
            (-0.20, 100.0),
            (0.00, 90.0),
            (0.10, 75.0),
            (0.25, 55.0),
            (0.50, 30.0),
            (1.00, 0.0),
        ],
    )


def calculate_quality_score(record: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate quality component scores and the combined Quality Score."""
    roe = first_value(record, "ROE", "returnOnEquity", "roe")
    operating_margin = first_value(
        record, "Operating Margin", "operatingMargins", "operating_margin"
    )
    profit_margin = first_value(record, "Profit Margin", "profitMargins", "profit_margin")
    free_cash_flow = first_value(record, "Free Cash Flow", "freeCashflow", "free_cash_flow")

    components = {
        "roe": score_quality_metric(roe, QUALITY_THRESHOLDS["roe"]),
        "operating_margin": score_quality_metric(
            operating_margin, QUALITY_THRESHOLDS["operating_margin"]
        ),
        "profit_margin": score_quality_metric(
            profit_margin, QUALITY_THRESHOLDS["profit_margin"]
        ),
        "free_cash_flow": score_free_cash_flow(free_cash_flow),
        "debt_control": score_debt_control(record),
    }

    score, coverage = weighted_available_score(components, QUALITY_WEIGHTS)
    return {
        "Quality Score": score,
        "Quality Coverage": coverage,
        "Quality Components": components,
    }


# =========================================================
# Valuation scoring
# =========================================================


def calculate_valuation_score(record: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate valuation component scores and the combined Valuation Score."""
    values = {
        "forward_pe": first_value(record, "Forward PE", "forwardPE", "forward_pe"),
        "peg": first_value(record, "PEG", "pegRatio", "peg"),
        "price_to_sales": first_value(
            record,
            "Price/Sales",
            "priceToSalesTrailing12Months",
            "price_to_sales",
        ),
    }

    components = {
        key: score_lower_is_better(value, VALUATION_THRESHOLDS[key])
        for key, value in values.items()
    }
    score, coverage = weighted_available_score(components, VALUATION_WEIGHTS)

    return {
        "Valuation Score": score,
        "Valuation Coverage": coverage,
        "Valuation Rating": rating_from_thresholds(score, VALUATION_SCORE_RATINGS),
        "Valuation Components": components,
    }


# =========================================================
# Momentum scoring
# =========================================================


def score_total_return(value: float, horizon: str) -> float:
    """Score a decimal total return for a six- or twelve-month horizon."""
    if horizon == "6m":
        points = [
            (-0.30, 0.0),
            (-0.10, 20.0),
            (0.00, 40.0),
            (0.10, 60.0),
            (0.25, 80.0),
            (0.50, 100.0),
        ]
    else:
        points = [
            (-0.40, 0.0),
            (-0.15, 20.0),
            (0.00, 40.0),
            (0.15, 60.0),
            (0.35, 80.0),
            (0.70, 100.0),
        ]
    return interpolate_score(value, points)


def score_price_vs_average(price: float, moving_average: float) -> float:
    """Score price location relative to a moving average."""
    price = safe_float(price)
    moving_average = safe_float(moving_average)
    if np.isnan(price) or np.isnan(moving_average) or moving_average <= 0:
        return np.nan

    distance = price / moving_average - 1.0
    return interpolate_score(
        distance,
        [
            (-0.25, 0.0),
            (-0.10, 25.0),
            (0.00, 55.0),
            (0.10, 75.0),
            (0.25, 90.0),
            (0.50, 100.0),
        ],
    )


def score_distance_from_high(price: float, high_52w: float) -> float:
    """Score how close the current price is to its 52-week high."""
    price = safe_float(price)
    high_52w = safe_float(high_52w)
    if np.isnan(price) or np.isnan(high_52w) or high_52w <= 0:
        return np.nan

    distance = price / high_52w - 1.0
    return interpolate_score(
        distance,
        [
            (-0.60, 0.0),
            (-0.40, 20.0),
            (-0.25, 45.0),
            (-0.15, 65.0),
            (-0.05, 85.0),
            (0.00, 100.0),
            (0.10, 100.0),
        ],
    )


def calculate_momentum_score(record: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate momentum component scores and the combined Momentum Score."""
    price = first_value(record, "Price", "currentPrice", "price")
    return_6m = first_value(record, "6M Return", "return_6m", "six_month_return")
    return_12m = first_value(record, "12M Return", "return_12m", "twelve_month_return")
    ma_50 = first_value(record, "50D MA", "fiftyDayAverage", "ma_50")
    ma_200 = first_value(record, "200D MA", "twoHundredDayAverage", "ma_200")
    high_52w = first_value(record, "52W High", "fiftyTwoWeekHigh", "high_52w")

    components = {
        "return_6m": score_total_return(return_6m, "6m"),
        "return_12m": score_total_return(return_12m, "12m"),
        "above_50dma": score_price_vs_average(price, ma_50),
        "above_200dma": score_price_vs_average(price, ma_200),
        "distance_52w_high": score_distance_from_high(price, high_52w),
    }

    score, coverage = weighted_available_score(components, MOMENTUM_WEIGHTS)
    return {
        "Momentum Score": score,
        "Momentum Coverage": coverage,
        "Momentum Components": components,
    }


# =========================================================
# Combined scoring
# =========================================================


def calculate_scores(record: Mapping[str, Any]) -> dict[str, Any]:
    """Calculate all MarketScope Growth scores for one stock record."""
    growth = calculate_growth_score(record)
    quality = calculate_quality_score(record)
    valuation = calculate_valuation_score(record)
    momentum = calculate_momentum_score(record)

    category_scores = {
        "growth": growth["Growth Score"],
        "quality": quality["Quality Score"],
        "valuation": valuation["Valuation Score"],
        "momentum": momentum["Momentum Score"],
    }
    overall_score, overall_coverage = weighted_available_score(
        category_scores,
        CATEGORY_WEIGHTS,
    )

    return {
        **growth,
        **quality,
        **valuation,
        **momentum,
        "Overall Score": overall_score,
        "Overall Coverage": overall_coverage,
        "Rating": rating_from_thresholds(overall_score, RATING_THRESHOLDS),
    }


def score_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a flat copy of a stock record with calculated score columns."""
    result = dict(record)
    scores = calculate_scores(record)

    # Keep table-friendly values. Detailed component dictionaries remain
    # available through calculate_scores() for explorer/detail pages.
    for key, value in scores.items():
        if not key.endswith("Components"):
            result[key] = value

    return result


def score_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Calculate MarketScope Growth scores for every row in a DataFrame."""
    if data is None or data.empty:
        return pd.DataFrame() if data is None else data.copy()

    scored_rows = [score_record(row.to_dict()) for _, row in data.iterrows()]
    result = pd.DataFrame(scored_rows, index=data.index)

    if "Overall Score" in result.columns:
        result = result.sort_values(
            by="Overall Score",
            ascending=False,
            na_position="last",
        )

    return result.reset_index(drop=True)


# Friendly aliases for other MarketScope modules
calculate_stock_scores = calculate_scores
apply_growth_scores = score_dataframe


if __name__ == "__main__":
    sample_stock = {
        "Ticker": "DEMO",
        "Company": "Demonstration Company",
        "Price": 125.0,
        "Market Cap": 50_000_000_000,
        "Revenue Growth": 0.22,
        "Earnings Growth": 0.28,
        "EPS Growth": 0.25,
        "Forward EPS Growth": 0.18,
        "ROE": 0.24,
        "Operating Margin": 0.21,
        "Profit Margin": 0.16,
        "Free Cash Flow": 2_500_000_000,
        "Total Debt": 5_000_000_000,
        "Total Cash": 3_000_000_000,
        "Forward PE": 31.0,
        "PEG": 1.6,
        "Price/Sales": 7.0,
        "6M Return": 0.18,
        "12M Return": 0.32,
        "50D MA": 118.0,
        "200D MA": 105.0,
        "52W High": 132.0,
    }

    demo_scores = score_record(sample_stock)
    for field in (
        "Growth Score",
        "Quality Score",
        "Valuation Score",
        "Momentum Score",
        "Overall Score",
        "Overall Coverage",
        "Rating",
    ):
        print(f"{field}: {demo_scores.get(field)}")

"""MarketScope Value scoring and value-trap risk engine."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd

from config import (
    CATEGORY_WEIGHTS,
    FINANCIAL_STRENGTH_THRESHOLDS,
    FINANCIAL_STRENGTH_WEIGHTS,
    GROWTH_THRESHOLDS,
    GROWTH_WEIGHTS,
    MOMENTUM_WEIGHTS,
    QUALITY_THRESHOLDS,
    QUALITY_WEIGHTS,
    RATING_THRESHOLDS,
    VALUATION_SCORE_RATINGS,
    VALUATION_THRESHOLDS,
    VALUATION_WEIGHTS,
    VALUE_TRAP_RATINGS,
    VALUE_TRAP_THRESHOLDS,
    VALUE_TRAP_WEIGHTS,
)


MISSING_STRINGS = {"", "-", "--", "n/a", "na", "none", "null", "nan"}


# =========================================================
# General helpers
# =========================================================

def safe_float(value: Any) -> float:
    """Return a finite float or NaN for an unusable value."""
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
    """Clamp a numeric result to a range."""
    return float(max(low, min(high, value)))


def first_value(record: Mapping[str, Any], *keys: str) -> float:
    """Return the first usable numeric value found among aliases."""
    for key in keys:
        if key in record:
            value = safe_float(record[key])
            if not np.isnan(value):
                return value
    return np.nan


def interpolate_score(value: float, points: list[tuple[float, float]]) -> float:
    """Interpolate a 0-100 score from ordered value/score anchor points."""
    value = safe_float(value)
    if np.isnan(value):
        return np.nan

    points = sorted(points, key=lambda item: item[0])
    x_values = [point[0] for point in points]
    y_values = [point[1] for point in points]
    score = float(np.interp(value, x_values, y_values))
    return round(clamp(score), 1)


def weighted_available_score(
    scores: Mapping[str, float],
    weights: Mapping[str, float],
) -> tuple[float, float]:
    """Calculate a weighted score using only components with available data."""
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


def rating_from_thresholds(score: float, thresholds: Mapping[int, str]) -> str:
    """Return the label associated with the highest threshold met."""
    score = safe_float(score)
    if np.isnan(score):
        return "Insufficient Data"

    for threshold in sorted(thresholds, reverse=True):
        if score >= threshold:
            return thresholds[threshold]

    return "Insufficient Data"


def score_higher_is_better(value: float, thresholds: Mapping[str, float]) -> float:
    """Score metrics where a larger value is preferable."""
    value = safe_float(value)
    minimum = safe_float(thresholds.get("minimum"))
    moderate = safe_float(thresholds.get("moderate"))
    strong = safe_float(thresholds.get("strong"))
    excellent = safe_float(thresholds.get("excellent"))

    if np.isnan(value) or any(np.isnan(x) for x in (minimum, moderate, strong, excellent)):
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


def score_lower_is_better(value: float, thresholds: Mapping[str, float]) -> float:
    """Score positive valuation multiples where lower is preferable."""
    value = safe_float(value)
    excellent = safe_float(thresholds.get("excellent"))
    good = safe_float(thresholds.get("good"))
    fair = safe_float(thresholds.get("fair"))
    expensive = safe_float(thresholds.get("expensive"))

    if np.isnan(value) or value <= 0:
        return np.nan
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


def score_low_ratio_is_better(value: float, thresholds: Mapping[str, float]) -> float:
    """Score ratios that may legitimately be zero or negative, such as net debt."""
    value = safe_float(value)
    excellent = safe_float(thresholds.get("excellent"))
    good = safe_float(thresholds.get("good"))
    fair = safe_float(thresholds.get("fair"))
    weak = safe_float(thresholds.get("weak"))
    poor = safe_float(thresholds.get("poor", weak + max(weak - fair, 0.25)))

    if np.isnan(value) or any(np.isnan(x) for x in (excellent, good, fair, weak, poor)):
        return np.nan

    return interpolate_score(
        value,
        [
            (excellent, 100.0),
            (good, 90.0),
            (fair, 65.0),
            (weak, 30.0),
            (poor, 0.0),
        ],
    )


# =========================================================
# Derived metrics
# =========================================================

def calculate_derived_metrics(record: Mapping[str, Any]) -> dict[str, float]:
    """Calculate reusable valuation, cash-flow, and leverage measures."""
    market_cap = first_value(record, "Market Cap", "marketCap", "market_cap")
    free_cash_flow = first_value(record, "Free Cash Flow", "freeCashflow", "free_cash_flow")
    operating_cash_flow = first_value(
        record, "Operating Cash Flow", "operatingCashflow", "operating_cash_flow"
    )
    total_debt = first_value(record, "Total Debt", "totalDebt", "total_debt")
    total_cash = first_value(record, "Total Cash", "totalCash", "total_cash")
    trailing_pe = first_value(record, "Trailing PE", "trailingPE", "trailing_pe")

    fcf_yield = (
        free_cash_flow / market_cap
        if not np.isnan(free_cash_flow) and not np.isnan(market_cap) and market_cap > 0
        else np.nan
    )
    earnings_yield = 1.0 / trailing_pe if not np.isnan(trailing_pe) and trailing_pe > 0 else np.nan
    cash_conversion = (
        free_cash_flow / operating_cash_flow
        if not np.isnan(free_cash_flow)
        and not np.isnan(operating_cash_flow)
        and operating_cash_flow > 0
        else np.nan
    )
    net_debt_to_market_cap = (
        (total_debt - (0.0 if np.isnan(total_cash) else total_cash)) / market_cap
        if not np.isnan(total_debt) and not np.isnan(market_cap) and market_cap > 0
        else np.nan
    )
    cash_to_debt = (
        total_cash / total_debt
        if not np.isnan(total_cash) and not np.isnan(total_debt) and total_debt > 0
        else np.nan
    )

    return {
        "FCF Yield": fcf_yield,
        "Earnings Yield": earnings_yield,
        "Cash Conversion": cash_conversion,
        "Net Debt/Market Cap": net_debt_to_market_cap,
        "Cash/Debt": cash_to_debt,
    }


# =========================================================
# Valuation score
# =========================================================

def calculate_valuation_score(record: Mapping[str, Any]) -> dict[str, Any]:
    derived = calculate_derived_metrics(record)
    values = {
        "forward_pe": first_value(record, "Forward PE", "forwardPE", "forward_pe"),
        "trailing_pe": first_value(record, "Trailing PE", "trailingPE", "trailing_pe"),
        "price_to_book": first_value(record, "Price/Book", "priceToBook", "price_to_book"),
        "price_to_sales": first_value(
            record, "Price/Sales", "priceToSalesTrailing12Months", "price_to_sales"
        ),
        "ev_to_ebitda": first_value(
            record, "EV/EBITDA", "enterpriseToEbitda", "ev_to_ebitda"
        ),
        "fcf_yield": safe_float(derived["FCF Yield"]),
        "earnings_yield": safe_float(derived["Earnings Yield"]),
    }

    components = {
        "forward_pe": score_lower_is_better(values["forward_pe"], VALUATION_THRESHOLDS["forward_pe"]),
        "trailing_pe": score_lower_is_better(values["trailing_pe"], VALUATION_THRESHOLDS["trailing_pe"]),
        "price_to_book": score_lower_is_better(values["price_to_book"], VALUATION_THRESHOLDS["price_to_book"]),
        "price_to_sales": score_lower_is_better(values["price_to_sales"], VALUATION_THRESHOLDS["price_to_sales"]),
        "ev_to_ebitda": score_lower_is_better(values["ev_to_ebitda"], VALUATION_THRESHOLDS["ev_to_ebitda"]),
        "fcf_yield": score_higher_is_better(values["fcf_yield"], VALUATION_THRESHOLDS["fcf_yield"]),
        "earnings_yield": score_higher_is_better(
            values["earnings_yield"], VALUATION_THRESHOLDS["earnings_yield"]
        ),
    }
    score, coverage = weighted_available_score(components, VALUATION_WEIGHTS)

    return {
        **derived,
        "Valuation Score": score,
        "Valuation Coverage": coverage,
        "Valuation Rating": rating_from_thresholds(score, VALUATION_SCORE_RATINGS),
        "Valuation Components": components,
    }


# =========================================================
# Quality score
# =========================================================

def score_positive_cash_flow(value: float) -> float:
    value = safe_float(value)
    if np.isnan(value):
        return np.nan
    if value > 0:
        return 100.0
    if value == 0:
        return 50.0
    return 0.0


def calculate_quality_score(record: Mapping[str, Any]) -> dict[str, Any]:
    derived = calculate_derived_metrics(record)
    values = {
        "roe": first_value(record, "ROE", "returnOnEquity", "roe"),
        "operating_margin": first_value(
            record, "Operating Margin", "operatingMargins", "operating_margin"
        ),
        "profit_margin": first_value(record, "Profit Margin", "profitMargins", "profit_margin"),
        "free_cash_flow": first_value(
            record, "Free Cash Flow", "freeCashflow", "free_cash_flow"
        ),
        "cash_conversion": safe_float(derived["Cash Conversion"]),
    }

    components = {
        "roe": score_higher_is_better(values["roe"], QUALITY_THRESHOLDS["roe"]),
        "operating_margin": score_higher_is_better(
            values["operating_margin"], QUALITY_THRESHOLDS["operating_margin"]
        ),
        "profit_margin": score_higher_is_better(
            values["profit_margin"], QUALITY_THRESHOLDS["profit_margin"]
        ),
        "free_cash_flow": score_positive_cash_flow(values["free_cash_flow"]),
        "cash_conversion": score_higher_is_better(
            values["cash_conversion"], QUALITY_THRESHOLDS["cash_conversion"]
        ),
    }
    score, coverage = weighted_available_score(components, QUALITY_WEIGHTS)

    return {
        "Quality Score": score,
        "Quality Coverage": coverage,
        "Quality Components": components,
    }


# =========================================================
# Financial-strength score
# =========================================================

def calculate_financial_strength_score(record: Mapping[str, Any]) -> dict[str, Any]:
    derived = calculate_derived_metrics(record)
    values = {
        "net_debt_to_market_cap": safe_float(derived["Net Debt/Market Cap"]),
        "debt_to_equity": first_value(record, "Debt/Equity", "debtToEquity", "debt_to_equity"),
        "current_ratio": first_value(record, "Current Ratio", "currentRatio", "current_ratio"),
        "cash_to_debt": safe_float(derived["Cash/Debt"]),
    }

    components = {
        "net_debt_to_market_cap": score_low_ratio_is_better(
            values["net_debt_to_market_cap"],
            FINANCIAL_STRENGTH_THRESHOLDS["net_debt_to_market_cap"],
        ),
        "debt_to_equity": score_lower_is_better(
            values["debt_to_equity"],
            FINANCIAL_STRENGTH_THRESHOLDS["debt_to_equity"],
        ),
        "current_ratio": score_higher_is_better(
            values["current_ratio"],
            FINANCIAL_STRENGTH_THRESHOLDS["current_ratio"],
        ),
        "cash_to_debt": score_higher_is_better(
            values["cash_to_debt"],
            FINANCIAL_STRENGTH_THRESHOLDS["cash_to_debt"],
        ),
    }
    score, coverage = weighted_available_score(components, FINANCIAL_STRENGTH_WEIGHTS)

    return {
        "Financial Strength Score": score,
        "Financial Strength Coverage": coverage,
        "Financial Strength Components": components,
    }


# =========================================================
# Growth score
# =========================================================

def calculate_growth_score(record: Mapping[str, Any]) -> dict[str, Any]:
    values = {
        "revenue_growth": first_value(
            record, "Revenue Growth", "revenueGrowth", "revenue_growth"
        ),
        "earnings_growth": first_value(
            record, "Earnings Growth", "earningsGrowth", "earnings_growth"
        ),
        "eps_growth": first_value(record, "EPS Growth", "epsGrowth", "eps_growth"),
        "forward_eps_growth": first_value(
            record, "Forward EPS Growth", "forwardEpsGrowth", "forward_eps_growth"
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
        "Growth Components": components,
    }


# =========================================================
# Momentum score
# =========================================================

def score_total_return(value: float, horizon: str) -> float:
    points = (
        [(-0.30, 0.0), (-0.10, 20.0), (0.00, 45.0), (0.10, 65.0), (0.25, 85.0), (0.50, 100.0)]
        if horizon == "6m"
        else [(-0.40, 0.0), (-0.15, 20.0), (0.00, 45.0), (0.15, 65.0), (0.35, 85.0), (0.70, 100.0)]
    )
    return interpolate_score(value, points)


def score_price_vs_average(price: float, moving_average: float) -> float:
    price = safe_float(price)
    moving_average = safe_float(moving_average)
    if np.isnan(price) or np.isnan(moving_average) or moving_average <= 0:
        return np.nan

    distance = price / moving_average - 1.0
    return interpolate_score(
        distance,
        [(-0.25, 0.0), (-0.10, 25.0), (0.00, 55.0), (0.10, 75.0), (0.25, 90.0), (0.50, 100.0)],
    )


def score_distance_from_high(price: float, high_52w: float) -> float:
    price = safe_float(price)
    high_52w = safe_float(high_52w)
    if np.isnan(price) or np.isnan(high_52w) or high_52w <= 0:
        return np.nan

    distance = price / high_52w - 1.0
    return interpolate_score(
        distance,
        [(-0.60, 0.0), (-0.40, 20.0), (-0.25, 45.0), (-0.15, 65.0), (-0.05, 85.0), (0.00, 100.0)],
    )


def calculate_momentum_score(record: Mapping[str, Any]) -> dict[str, Any]:
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
# Value-trap risk
# =========================================================

def risk_from_decline(value: float, thresholds: Mapping[str, float]) -> float:
    """Convert a growth/profitability value to risk where lower is worse."""
    value = safe_float(value)
    low_risk = safe_float(thresholds.get("low_risk"))
    moderate = safe_float(thresholds.get("moderate_risk"))
    high_risk = safe_float(thresholds.get("high_risk"))

    if np.isnan(value) or any(np.isnan(x) for x in (low_risk, moderate, high_risk)):
        return np.nan

    severe = high_risk - max(abs(moderate - high_risk), 0.10)
    return interpolate_score(
        value,
        [(severe, 100.0), (high_risk, 85.0), (moderate, 50.0), (low_risk, 15.0), (low_risk + 0.10, 0.0)],
    )


def risk_from_high_ratio(value: float, thresholds: Mapping[str, float]) -> float:
    """Convert a leverage ratio to risk where higher is worse."""
    value = safe_float(value)
    low_risk = safe_float(thresholds.get("low_risk"))
    moderate = safe_float(thresholds.get("moderate_risk"))
    high_risk = safe_float(thresholds.get("high_risk"))

    if np.isnan(value) or any(np.isnan(x) for x in (low_risk, moderate, high_risk)):
        return np.nan

    severe = high_risk + max(abs(high_risk - moderate), 0.30)
    return interpolate_score(
        value,
        [(min(low_risk - 0.20, -0.10), 0.0), (low_risk, 15.0), (moderate, 50.0), (high_risk, 85.0), (severe, 100.0)],
    )


def risk_negative_cash_flow(value: float) -> float:
    value = safe_float(value)
    if np.isnan(value):
        return np.nan
    if value > 0:
        return 0.0
    if value == 0:
        return 50.0
    return 100.0


def risk_price_below_average(price: float, moving_average: float) -> float:
    price = safe_float(price)
    moving_average = safe_float(moving_average)
    if np.isnan(price) or np.isnan(moving_average) or moving_average <= 0:
        return np.nan

    distance = price / moving_average - 1.0
    return interpolate_score(
        distance,
        [(-0.40, 100.0), (-0.25, 85.0), (-0.10, 65.0), (0.00, 35.0), (0.10, 10.0), (0.25, 0.0)],
    )


def calculate_value_trap_risk(
    record: Mapping[str, Any],
    quality_score: float | None = None,
) -> dict[str, Any]:
    derived = calculate_derived_metrics(record)

    revenue_growth = first_value(record, "Revenue Growth", "revenueGrowth", "revenue_growth")
    earnings_growth = first_value(record, "Earnings Growth", "earningsGrowth", "earnings_growth")
    free_cash_flow = first_value(record, "Free Cash Flow", "freeCashflow", "free_cash_flow")
    profit_margin = first_value(record, "Profit Margin", "profitMargins", "profit_margin")
    price = first_value(record, "Price", "currentPrice", "price")
    ma_200 = first_value(record, "200D MA", "twoHundredDayAverage", "ma_200")
    return_12m = first_value(record, "12M Return", "return_12m", "twelve_month_return")

    if quality_score is None:
        quality_score = calculate_quality_score(record)["Quality Score"]
    quality_score = safe_float(quality_score)

    low_quality_risk = np.nan
    if not np.isnan(quality_score):
        low_quality_risk = round(clamp(100.0 - quality_score), 1)

    components = {
        "negative_revenue_growth": risk_from_decline(
            revenue_growth, VALUE_TRAP_THRESHOLDS["revenue_growth"]
        ),
        "negative_earnings_growth": risk_from_decline(
            earnings_growth, VALUE_TRAP_THRESHOLDS["earnings_growth"]
        ),
        "negative_free_cash_flow": risk_negative_cash_flow(free_cash_flow),
        "weak_profitability": risk_from_decline(
            profit_margin, VALUE_TRAP_THRESHOLDS["profit_margin"]
        ),
        "high_net_debt": risk_from_high_ratio(
            derived["Net Debt/Market Cap"],
            VALUE_TRAP_THRESHOLDS["net_debt_to_market_cap"],
        ),
        "below_200dma": risk_price_below_average(price, ma_200),
        "weak_12m_return": risk_from_decline(
            return_12m, VALUE_TRAP_THRESHOLDS["return_12m"]
        ),
        "low_quality_score": low_quality_risk,
    }

    score, coverage = weighted_available_score(components, VALUE_TRAP_WEIGHTS)

    return {
        "Value Trap Risk": score,
        "Value Trap Coverage": coverage,
        "Value Trap Rating": rating_from_thresholds(score, VALUE_TRAP_RATINGS),
        "Value Trap Components": components,
    }


# =========================================================
# Combined scoring
# =========================================================

def calculate_scores(record: Mapping[str, Any]) -> dict[str, Any]:
    valuation = calculate_valuation_score(record)
    quality = calculate_quality_score(record)
    financial_strength = calculate_financial_strength_score(record)
    growth = calculate_growth_score(record)
    momentum = calculate_momentum_score(record)

    category_scores = {
        "valuation": valuation["Valuation Score"],
        "quality": quality["Quality Score"],
        "financial_strength": financial_strength["Financial Strength Score"],
        "growth": growth["Growth Score"],
        "momentum": momentum["Momentum Score"],
    }
    overall_score, overall_coverage = weighted_available_score(category_scores, CATEGORY_WEIGHTS)

    value_trap = calculate_value_trap_risk(
        record,
        quality_score=quality["Quality Score"],
    )

    return {
        **valuation,
        **quality,
        **financial_strength,
        **growth,
        **momentum,
        **value_trap,
        "Overall Score": overall_score,
        "Overall Coverage": overall_coverage,
        "Rating": rating_from_thresholds(overall_score, RATING_THRESHOLDS),
    }


def score_record(record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a flat record containing table-friendly score fields."""
    result = dict(record)
    scores = calculate_scores(record)

    for key, value in scores.items():
        if not key.endswith("Components"):
            result[key] = value

    return result


def score_dataframe(data: pd.DataFrame) -> pd.DataFrame:
    """Score every row and sort by Overall Score descending."""
    if data is None or data.empty:
        return pd.DataFrame() if data is None else data.copy()

    rows = [score_record(row.to_dict()) for _, row in data.iterrows()]
    result = pd.DataFrame(rows, index=data.index)

    if "Overall Score" in result.columns:
        result = result.sort_values(
            "Overall Score",
            ascending=False,
            na_position="last",
        )

    return result.reset_index(drop=True)


# Friendly aliases for page and data modules.
calculate_stock_scores = calculate_scores
apply_value_scores = score_dataframe


if __name__ == "__main__":
    sample = {
        "Ticker": "DEMO",
        "Price": 80.0,
        "Market Cap": 40_000_000_000,
        "Trailing PE": 12.0,
        "Forward PE": 10.0,
        "Price/Book": 1.8,
        "Price/Sales": 1.5,
        "EV/EBITDA": 7.5,
        "Revenue Growth": 0.06,
        "Earnings Growth": 0.10,
        "EPS Growth": 0.09,
        "Forward EPS Growth": 0.08,
        "ROE": 0.18,
        "Operating Margin": 0.16,
        "Profit Margin": 0.12,
        "Free Cash Flow": 3_200_000_000,
        "Operating Cash Flow": 4_000_000_000,
        "Total Debt": 8_000_000_000,
        "Total Cash": 5_000_000_000,
        "Debt/Equity": 55.0,
        "Current Ratio": 1.5,
        "6M Return": 0.08,
        "12M Return": 0.15,
        "50D MA": 77.0,
        "200D MA": 70.0,
        "52W High": 84.0,
    }

    result = score_record(sample)
    for field in (
        "Valuation Score",
        "Quality Score",
        "Financial Strength Score",
        "Growth Score",
        "Momentum Score",
        "Overall Score",
        "Rating",
        "Value Trap Risk",
        "Value Trap Rating",
    ):
        print(f"{field}: {result.get(field)}")

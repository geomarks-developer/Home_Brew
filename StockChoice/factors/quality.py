"""
StockChoice Quality Factor

Measures:

    - Return on Equity
    - Return on Assets
    - Profit Margin
    - Operating Margin
    - Financial Health

Returns:

    Quality Score (0-100)

Higher score = stronger business quality
"""

from __future__ import annotations

from factor_config import QUALITY_METRICS
from utils.conversions import decimal_to_pct
from utils.conversions import (
    normalize_debt_to_equity
)

# ============================================================
# SCORING
# ============================================================

def score_roe(value: float | None) -> float:

    if value is None:
        return 0

    if value >= 25:
        return 100

    if value >= 20:
        return 90

    if value >= 15:
        return 80

    if value >= 10:
        return 70

    if value >= 5:
        return 50

    return 0


def score_roa(value: float | None) -> float:

    if value is None:
        return 0

    if value >= 15:
        return 100

    if value >= 10:
        return 90

    if value >= 7:
        return 80

    if value >= 5:
        return 70

    if value >= 2:
        return 50

    return 0


def score_margin(value: float | None) -> float:

    if value is None:
        return 0

    if value >= 30:
        return 100

    if value >= 20:
        return 90

    if value >= 15:
        return 80

    if value >= 10:
        return 70

    if value >= 5:
        return 50

    return 0


def score_financial_health(
    current_ratio: float | None,
    debt_to_equity: float | None,
) -> float:

    score = 50

    #
    # Liquidity
    #
    if current_ratio is not None:

        if current_ratio >= 2:
            score += 25

        elif current_ratio >= 1:
            score += 10

    #
    # Debt
    #
    if debt_to_equity is not None:

        if debt_to_equity <= 0.50:
            score += 25

        elif debt_to_equity <= 1.00:
            score += 10

    return min(score, 100)


# ============================================================
# FACTOR CALCULATION
# ============================================================

def calculate_quality_score(
    return_on_equity: float | None = None,
    return_on_assets: float | None = None,
    profit_margin: float | None = None,
    operating_margin: float | None = None,
    current_ratio: float | None = None,
    debt_to_equity: float | None = None,
) -> tuple[float, dict]:

    roe_score = score_roe(
        return_on_equity
    )

    roa_score = score_roa(
        return_on_assets
    )

    profit_margin_score = score_margin(
        profit_margin
    )

    operating_margin_score = score_margin(
        operating_margin
    )

    financial_health_score = (
        score_financial_health(
            current_ratio=current_ratio,
            debt_to_equity=debt_to_equity,
        )
    )

    quality_score = (

        roe_score
        * QUALITY_METRICS["return_on_equity"]

        + roa_score
        * QUALITY_METRICS["return_on_assets"]

        + profit_margin_score
        * QUALITY_METRICS["profit_margin"]

        + operating_margin_score
        * QUALITY_METRICS["operating_margin"]

        + financial_health_score
        * QUALITY_METRICS["financial_health"]

    )

    details = {

        "roe":
            return_on_equity,

        "roe_score":
            round(roe_score, 2),

        "roa":
            return_on_assets,

        "roa_score":
            round(roa_score, 2),

        "profit_margin":
            profit_margin,

        "profit_margin_score":
            round(profit_margin_score, 2),

        "operating_margin":
            operating_margin,

        "operating_margin_score":
            round(operating_margin_score, 2),

        "current_ratio":
            current_ratio,

        "debt_to_equity":
            debt_to_equity,

        "financial_health_score":
            round(
                financial_health_score,
                2
            ),
    }

    return round(quality_score, 2), details


# ============================================================
# YFINANCE HELPER
# ============================================================

def build_quality_score_from_yfinance(
    info: dict
):

    return calculate_quality_score(

        return_on_equity=decimal_to_pct(
            info.get("returnOnEquity")
        ),

        return_on_assets=decimal_to_pct(
            info.get("returnOnAssets")
        ),

        profit_margin=decimal_to_pct(
            info.get("profitMargins")
        ),

        operating_margin=decimal_to_pct(
            info.get("operatingMargins")
        ),

        current_ratio=info.get(
            "currentRatio"
        ),

        debt_to_equity=info.get(
            "debtToEquity"
        ),
    )

    debt_to_equity=normalize_debt_to_equity(
        info.get("debtToEquity")
    )
"""
StockChoice Dividend Factor

Measures:

    - Dividend Yield
    - Dividend Growth
    - Payout Ratio
    - Years of Dividend Growth

Returns:

    Dividend Score (0-100)

Higher score = stronger dividend profile
"""

from __future__ import annotations

from factor_config import DIVIDEND_METRICS
from utils.conversions import decimal_to_pct


# ============================================================
# SCORING
# ============================================================

def score_dividend_yield(
    value: float | None
) -> float:

    if value is None:
        return 0

    if value >= 6:
        return 100

    if value >= 5:
        return 90

    if value >= 4:
        return 80

    if value >= 3:
        return 70

    if value >= 2:
        return 60

    if value >= 1:
        return 40

    return 20


def score_dividend_growth(
    value: float | None
) -> float:

    if value is None:
        return 0

    if value >= 15:
        return 100

    if value >= 12:
        return 90

    if value >= 10:
        return 80

    if value >= 7:
        return 70

    if value >= 5:
        return 60

    if value >= 0:
        return 40

    return 0


def score_payout_ratio(
    value: float | None
) -> float:
    """
    Lower is generally better.

    Assumes percentage (0-100).
    """

    if value is None:
        return 50

    if value <= 40:
        return 100

    if value <= 50:
        return 90

    if value <= 60:
        return 80

    if value <= 70:
        return 65

    if value <= 80:
        return 45

    if value <= 100:
        return 25

    return 0


def score_years_growth(
    value: int | None
) -> float:

    if value is None:
        return 0

    if value >= 25:
        return 100

    if value >= 15:
        return 90

    if value >= 10:
        return 80

    if value >= 5:
        return 60

    if value >= 1:
        return 40

    return 0


# ============================================================
# FACTOR CALCULATION
# ============================================================

def calculate_dividend_score(
    dividend_yield: float | None = None,
    dividend_growth: float | None = None,
    payout_ratio: float | None = None,
    years_of_growth: int | None = None,
) -> tuple[float, dict]:

    yield_score = score_dividend_yield(
        dividend_yield
    )

    growth_score = score_dividend_growth(
        dividend_growth
    )

    payout_score = score_payout_ratio(
        payout_ratio
    )

    years_score = score_years_growth(
        years_of_growth
    )

    dividend_score = (

        yield_score
        * DIVIDEND_METRICS["dividend_yield"]

        + growth_score
        * DIVIDEND_METRICS["dividend_growth"]

        + payout_score
        * DIVIDEND_METRICS["payout_ratio"]

        + years_score
        * DIVIDEND_METRICS["years_of_growth"]

    )

    details = {

        "dividend_yield":
            dividend_yield,

        "yield_score":
            round(yield_score, 2),

        "dividend_growth":
            dividend_growth,

        "growth_score":
            round(growth_score, 2),

        "payout_ratio":
            payout_ratio,

        "payout_score":
            round(payout_score, 2),

        "years_of_growth":
            years_of_growth,

        "years_score":
            round(years_score, 2),
    }

    return round(dividend_score, 2), details


# ============================================================
# YFINANCE HELPER
# ============================================================

def build_dividend_score_from_yfinance(
    info: dict,
    years_of_growth: int | None = None,
):

    return calculate_dividend_score(

        dividend_yield=decimal_to_pct(
            info.get("dividendYield")
        ),

        dividend_growth=decimal_to_pct(
            info.get("fiveYearAvgDividendYield")
        ),

        payout_ratio=decimal_to_pct(
            info.get("payoutRatio")
        ),

        years_of_growth=years_of_growth,
    )
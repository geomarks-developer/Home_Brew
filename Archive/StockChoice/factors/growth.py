"""
StockChoice Growth Factor

Measures:

    - Revenue Growth
    - Earnings Growth
    - Free Cash Flow Growth
    - Forward Growth

Returns:

    Growth Score (0-100)

Higher score = stronger growth profile
"""

from __future__ import annotations

from factor_config import GROWTH_METRICS
from utils.conversions import decimal_to_pct



# ============================================================
# SCORING
# ============================================================

def score_growth_rate(
    growth_rate: float | None
) -> float:
    """
    Convert growth percentage
    into a 0-100 score.
    """

    if growth_rate is None:
        return 0

    if growth_rate >= 30:
        return 100

    if growth_rate >= 20:
        return 90

    if growth_rate >= 15:
        return 80

    if growth_rate >= 10:
        return 70

    if growth_rate >= 5:
        return 60

    if growth_rate >= 0:
        return 40

    if growth_rate >= -10:
        return 20

    return 0

# ============================================================
# FACTOR CALCULATION
# ============================================================

def calculate_growth_score(
    revenue_growth: float | None = None,
    earnings_growth: float | None = None,
    free_cash_flow_growth: float | None = None,
    forward_growth: float | None = None,
) -> tuple[float, dict]:

    revenue_score = score_growth_rate(
        revenue_growth
    )

    earnings_score = score_growth_rate(
        earnings_growth
    )

    fcf_score = score_growth_rate(
        free_cash_flow_growth
    )

    forward_score = score_growth_rate(
        forward_growth
    )

    growth_score = (

        revenue_score
        * GROWTH_METRICS["revenue_growth"]

        + earnings_score
        * GROWTH_METRICS["earnings_growth"]

        + fcf_score
        * GROWTH_METRICS["free_cash_flow_growth"]

        + forward_score
        * GROWTH_METRICS["forward_growth"]

    )

    details = {

        "revenue_growth":
            revenue_growth,

        "revenue_score":
            round(revenue_score, 2),

        "earnings_growth":
            earnings_growth,

        "earnings_score":
            round(earnings_score, 2),

        "free_cash_flow_growth":
            free_cash_flow_growth,

        "free_cash_flow_score":
            round(fcf_score, 2),

        "forward_growth":
            forward_growth,

        "forward_growth_score":
            round(forward_score, 2),
    }

    return round(growth_score, 2), details

def build_growth_score_from_yfinance(
    info: dict
):

    return calculate_growth_score(
        revenue_growth=decimal_to_pct(
            info.get("revenueGrowth")
        ),
        earnings_growth=decimal_to_pct(
            info.get("earningsGrowth")
        ),
        forward_growth=decimal_to_pct(
            info.get("earningsQuarterlyGrowth")
        ),
    )
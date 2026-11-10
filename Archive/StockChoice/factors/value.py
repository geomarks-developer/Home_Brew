"""
StockChoice Value Factor

Measures:

    - P/E Ratio
    - Forward P/E
    - PEG Ratio
    - Price to Book
    - Price to Sales
    - Free Cash Flow Yield

Returns:

    Value Score (0-100)

Higher score = more attractive valuation
"""

from __future__ import annotations

from factor_config import VALUE_METRICS


# ============================================================
# SCORING
# ============================================================

def score_pe_ratio(
    value: float | None
) -> float:

    if value is None or value <= 0:
        return 50

    if value <= 10:
        return 100

    if value <= 15:
        return 90

    if value <= 20:
        return 80

    if value <= 25:
        return 70

    if value <= 30:
        return 60

    if value <= 40:
        return 50

    if value <= 50:
        return 35

    return 20


def score_forward_pe(
    value: float | None
) -> float:

    return score_pe_ratio(value)


def score_peg_ratio(
    value: float | None
) -> float:
    """
    PEG Ratio

    Lower is better.
    """

    if value is None or value <= 0:
        return 50

    if value <= 1.0:
        return 100

    if value <= 1.5:
        return 85

    if value <= 2.0:
        return 70

    if value <= 3.0:
        return 40

    return 10


def score_price_to_book(
    value: float | None
) -> float:
    """
    Softer scoring for asset-light
    technology and software companies.
    """

    if value is None or value <= 0:
        return 50

    if value <= 2:
        return 100

    if value <= 4:
        return 90

    if value <= 6:
        return 80

    if value <= 8:
        return 70

    if value <= 12:
        return 60

    if value <= 20:
        return 40

    return 20


def score_price_to_sales(
    value: float | None
) -> float:
    """
    More forgiving for high-margin
    technology and software companies.
    """

    if value is None or value <= 0:
        return 50

    if value <= 2:
        return 100

    if value <= 4:
        return 90

    if value <= 6:
        return 80

    if value <= 10:
        return 70

    if value <= 15:
        return 50

    if value <= 25:
        return 30

    return 10


def score_fcf_yield(
    value: float | None
) -> float:
    """
    Free Cash Flow Yield (%)

    Higher is better.
    """

    if value is None:
        return 50

    if value >= 10:
        return 100

    if value >= 8:
        return 90

    if value >= 6:
        return 80

    if value >= 4:
        return 70

    if value >= 2:
        return 50

    if value >= 0:
        return 30

    return 0


# ============================================================
# FACTOR CALCULATION
# ============================================================

def calculate_value_score(
    pe_ratio: float | None = None,
    forward_pe: float | None = None,
    peg_ratio: float | None = None,
    price_to_book: float | None = None,
    price_to_sales: float | None = None,
    free_cash_flow_yield: float | None = None,
) -> tuple[float, dict]:

    pe_score = score_pe_ratio(
        pe_ratio
    )

    forward_pe_score = score_forward_pe(
        forward_pe
    )

    peg_score = score_peg_ratio(
        peg_ratio
    )

    pb_score = score_price_to_book(
        price_to_book
    )

    ps_score = score_price_to_sales(
        price_to_sales
    )

    fcf_yield_score = score_fcf_yield(
        free_cash_flow_yield
    )

    value_score = (

        pe_score
        * VALUE_METRICS["pe_ratio"]

        + forward_pe_score
        * VALUE_METRICS["forward_pe"]

        + peg_score
        * VALUE_METRICS["peg_ratio"]

        + pb_score
        * VALUE_METRICS["price_to_book"]

        + ps_score
        * VALUE_METRICS["price_to_sales"]

        + fcf_yield_score
        * VALUE_METRICS["free_cash_flow_yield"]

    )

    details = {

        "pe_ratio":
            pe_ratio,

        "pe_score":
            round(pe_score, 2),

        "forward_pe":
            forward_pe,

        "forward_pe_score":
            round(forward_pe_score, 2),

        "peg_ratio":
            round(peg_ratio, 2)
            if peg_ratio is not None
            else None,

        "peg_score":
            round(peg_score, 2),

        "price_to_book":
            price_to_book,

        "price_to_book_score":
            round(pb_score, 2),

        "price_to_sales":
            price_to_sales,

        "price_to_sales_score":
            round(ps_score, 2),

        "free_cash_flow_yield":
            free_cash_flow_yield,

        "free_cash_flow_yield_score":
            round(fcf_yield_score, 2),
    }

    return round(value_score, 2), details


# ============================================================
# HELPERS
# ============================================================

def calculate_fcf_yield(
    market_cap: float | None,
    free_cash_flow: float | None,
) -> float | None:

    if (
        market_cap is None
        or market_cap <= 0
        or free_cash_flow is None
    ):
        return None

    return (
        free_cash_flow
        / market_cap
        * 100
    )


def calculate_peg_ratio(
    pe_ratio: float | None,
    earnings_growth: float | None,
) -> float | None:

    if (
        pe_ratio is None
        or earnings_growth is None
        or earnings_growth <= 0
    ):
        return None

    return (
        pe_ratio
        / earnings_growth
    )


# ============================================================
# YFINANCE HELPER
# ============================================================

def build_value_score_from_yfinance(
    info: dict
):

    free_cash_flow_yield = (
        calculate_fcf_yield(
            market_cap=info.get(
                "marketCap"
            ),
            free_cash_flow=info.get(
                "freeCashflow"
            ),
        )
    )

    earnings_growth = info.get(
        "earningsGrowth"
    )

    if earnings_growth is not None:
        earnings_growth *= 100

    peg_ratio = calculate_peg_ratio(
        pe_ratio=info.get(
            "trailingPE"
        ),
        earnings_growth=earnings_growth,
    )

    return calculate_value_score(

        pe_ratio=info.get(
            "trailingPE"
        ),

        forward_pe=info.get(
            "forwardPE"
        ),

        peg_ratio=peg_ratio,

        price_to_book=info.get(
            "priceToBook"
        ),

        price_to_sales=info.get(
            "priceToSalesTrailing12Months"
        ),

        free_cash_flow_yield=
            free_cash_flow_yield,
    )
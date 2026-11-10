"""
TickerTrends Fundamental Analysis
=================================

Retrieves the fundamental metrics used by TickerTrends.

Core metrics:

    - P/E ratio
    - PEG ratio
    - Free cash flow
    - Free cash flow margin
    - 6-month stock performance
    - 6-month relative performance vs S&P 500

Free Cash Flow is calculated from financial statements:

    Free Cash Flow =
        Operating Cash Flow - Capital Expenditures

TickerTrends fundamental scoring:

    P/E                  10 points
    PEG                  10 points
    Free Cash Flow       10 points
    Relative Performance 10 points

Actual scoring is handled later in scoring.py.
"""

from __future__ import annotations

import math
from typing import Any

import pandas as pd
import yfinance as yf


# ============================================================
# CONSTANTS
# ============================================================

BENCHMARK = "^GSPC"
PERFORMANCE_PERIOD = "6mo"


# ============================================================
# SYMBOL NORMALIZATION
# ============================================================

def normalize_ticker(ticker: str) -> str:
    """
    Normalize ticker symbols for yfinance.

    Examples:
        msft  -> MSFT
        BRK.B -> BRK-B
        BF.B  -> BF-B
    """

    return ticker.strip().upper().replace(".", "-")


# ============================================================
# SAFE NUMBER HELPERS
# ============================================================

def safe_float(value: Any) -> float | None:
    """
    Convert a value to a finite Python float.

    Returns None for missing, invalid, NaN,
    or infinite values.
    """

    if value is None:
        return None

    try:
        number = float(value)

    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return number


def first_valid(
    *values: Any,
) -> float | None:
    """
    Return the first usable numeric value.
    """

    for value in values:

        result = safe_float(value)

        if result is not None:
            return result

    return None


# ============================================================
# COMPANY INFO
# ============================================================

def get_company_info(
    ticker: str,
) -> dict[str, Any]:
    """
    Retrieve Yahoo Finance company information.

    Returns an empty dictionary if information
    cannot be retrieved.
    """

    ticker = normalize_ticker(ticker)

    try:

        stock = yf.Ticker(ticker)

        info = stock.info

        if not isinstance(info, dict):
            return {}

        return info

    except Exception:
        return {}


# ============================================================
# P/E RATIO
# ============================================================

def get_pe_ratio(
    info: dict[str, Any],
) -> float | None:
    """
    Retrieve a usable P/E ratio.

    TickerTrends prefers trailing P/E.

    Forward P/E is used only if trailing P/E
    is unavailable.
    """

    trailing_pe = safe_float(
        info.get("trailingPE")
    )

    if (
        trailing_pe is not None
        and trailing_pe > 0
    ):
        return trailing_pe

    forward_pe = safe_float(
        info.get("forwardPE")
    )

    if (
        forward_pe is not None
        and forward_pe > 0
    ):
        return forward_pe

    return None


def get_pe_source(
    info: dict[str, Any],
) -> str | None:
    """
    Identify which P/E value was used.
    """

    trailing_pe = safe_float(
        info.get("trailingPE")
    )

    if (
        trailing_pe is not None
        and trailing_pe > 0
    ):
        return "Trailing"

    forward_pe = safe_float(
        info.get("forwardPE")
    )

    if (
        forward_pe is not None
        and forward_pe > 0
    ):
        return "Forward"

    return None


# ============================================================
# PEG RATIO
# ============================================================

def get_peg_ratio(
    info: dict[str, Any],
) -> float | None:
    """
    Retrieve a positive PEG ratio.

    trailingPegRatio is preferred.

    pegRatio is used as a fallback.
    """

    peg = safe_float(
        info.get("trailingPegRatio")
    )

    if peg is None:

        peg = safe_float(
            info.get("pegRatio")
        )

    if peg is None:
        return None

    if peg <= 0:
        return None

    return peg


# ============================================================
# CASH FLOW HELPERS
# ============================================================

def get_cash_flow_value(
    cash_flow: pd.DataFrame,
    labels: list[str],
) -> float | None:
    """
    Find the first usable numeric value for one of the
    supplied cash-flow statement labels.
    """

    if cash_flow is None:
        return None

    if not isinstance(
        cash_flow,
        pd.DataFrame,
    ):
        return None

    if cash_flow.empty:
        return None

    for label in labels:

        if label not in cash_flow.index:
            continue

        row = cash_flow.loc[label]

        if isinstance(
            row,
            pd.Series,
        ):

            for value in row:

                result = safe_float(
                    value
                )

                if result is not None:
                    return result

        else:

            result = safe_float(
                row
            )

            if result is not None:
                return result

    return None


# ============================================================
# FREE CASH FLOW
# ============================================================

def get_statement_free_cash_flow(
    ticker: str,
) -> dict[str, Any]:
    """
    Calculate free cash flow from the company's
    cash-flow statement.

    Formula:

        Free Cash Flow =
            Operating Cash Flow
            - Capital Expenditures

    TTM cash-flow data is preferred.

    Annual cash-flow data is used as a fallback.

    Capital expenditures are converted to an absolute
    value because they are commonly represented as a
    negative cash-flow item.
    """

    ticker = normalize_ticker(
        ticker
    )

    try:

        stock = yf.Ticker(
            ticker
        )

    except Exception:

        return {
            "operating_cash_flow": None,
            "capital_expenditures": None,
            "free_cash_flow": None,
            "fcf_source": None,
        }

    # --------------------------------------------------------
    # TRY TTM CASH FLOW FIRST
    # --------------------------------------------------------

    try:

        cash_flow = (
            stock.ttm_cash_flow
        )

    except Exception:

        cash_flow = pd.DataFrame()

    source = (
        "TTM Cash Flow Statement"
    )

    # --------------------------------------------------------
    # FALL BACK TO ANNUAL CASH FLOW
    # --------------------------------------------------------

    if (
        cash_flow is None
        or not isinstance(
            cash_flow,
            pd.DataFrame,
        )
        or cash_flow.empty
    ):

        try:

            cash_flow = (
                stock.cash_flow
            )

        except Exception:

            cash_flow = (
                pd.DataFrame()
            )

        source = (
            "Annual Cash Flow Statement"
        )

    # --------------------------------------------------------
    # NO USABLE STATEMENT
    # --------------------------------------------------------

    if (
        cash_flow is None
        or not isinstance(
            cash_flow,
            pd.DataFrame,
        )
        or cash_flow.empty
    ):

        return {
            "operating_cash_flow": None,
            "capital_expenditures": None,
            "free_cash_flow": None,
            "fcf_source": None,
        }

    # --------------------------------------------------------
    # OPERATING CASH FLOW
    # --------------------------------------------------------

    operating_cash_flow = (
        get_cash_flow_value(
            cash_flow,
            [
                "Operating Cash Flow",
                "Total Cash From Operating Activities",
                (
                    "Cash Flow From Continuing "
                    "Operating Activities"
                ),
            ],
        )
    )

    # --------------------------------------------------------
    # CAPITAL EXPENDITURES
    # --------------------------------------------------------

    capital_expenditures = (
        get_cash_flow_value(
            cash_flow,
            [
                "Capital Expenditure",
                "Capital Expenditures",
            ],
        )
    )

    # --------------------------------------------------------
    # MISSING COMPONENT
    # --------------------------------------------------------

    if (
        operating_cash_flow is None
        or capital_expenditures is None
    ):

        return {
            "operating_cash_flow": (
                operating_cash_flow
            ),

            "capital_expenditures": (
                capital_expenditures
            ),

            "free_cash_flow": None,

            "fcf_source": (
                source
            ),
        }

    # --------------------------------------------------------
    # NORMALIZE CAPEX
    # --------------------------------------------------------

    capex_amount = abs(
        capital_expenditures
    )

    # --------------------------------------------------------
    # CALCULATE FREE CASH FLOW
    # --------------------------------------------------------

    free_cash_flow = (
        operating_cash_flow
        - capex_amount
    )

    return {
        "operating_cash_flow": (
            operating_cash_flow
        ),

        "capital_expenditures": (
            capex_amount
        ),

        "free_cash_flow": (
            free_cash_flow
        ),

        "fcf_source": (
            source
        ),
    }


# ============================================================
# REVENUE
# ============================================================

def get_revenue(
    info: dict[str, Any],
) -> float | None:
    """
    Retrieve trailing revenue.

    Revenue is used to calculate FCF margin.
    """

    revenue = safe_float(
        info.get("totalRevenue")
    )

    if revenue is None:
        return None

    if revenue <= 0:
        return None

    return revenue


# ============================================================
# FREE CASH FLOW MARGIN
# ============================================================

def calculate_fcf_margin(
    free_cash_flow: float | None,
    revenue: float | None,
) -> float | None:
    """
    Calculate free cash flow margin.

    Formula:

        FCF Margin =
            Free Cash Flow / Revenue * 100

    Example:

        18.5 means free cash flow equals
        18.5% of revenue.
    """

    if free_cash_flow is None:
        return None

    if revenue is None:
        return None

    if revenue <= 0:
        return None

    return (
        free_cash_flow
        / revenue
    ) * 100


# ============================================================
# PERFORMANCE HISTORY
# ============================================================

def download_performance_history(
    tickers: list[str],
    period: str = PERFORMANCE_PERIOD,
) -> pd.DataFrame:
    """
    Download adjusted price history used for
    performance calculations.
    """

    try:

        data = yf.download(
            tickers,
            period=period,
            interval="1d",
            auto_adjust=True,
            actions=False,
            progress=False,
            threads=True,
            group_by="column",
        )

    except Exception:

        return pd.DataFrame()

    if data is None:
        return pd.DataFrame()

    return data


# ============================================================
# CLOSE PRICE EXTRACTION
# ============================================================

def extract_close_series(
    data: pd.DataFrame,
    ticker: str,
) -> pd.Series | None:
    """
    Extract one ticker's closing prices from a
    yfinance download result.

    Handles both regular and MultiIndex columns.
    """

    if data is None:
        return None

    if data.empty:
        return None

    ticker = normalize_ticker(
        ticker
    )

    try:

        # ----------------------------------------------------
        # MULTIPLE SYMBOL DOWNLOAD
        # ----------------------------------------------------

        if isinstance(
            data.columns,
            pd.MultiIndex,
        ):

            if (
                "Close",
                ticker,
            ) in data.columns:

                series = data[
                    ("Close", ticker)
                ]

            elif (
                ticker
                in data.columns.get_level_values(-1)
            ):

                ticker_data = data.xs(
                    ticker,
                    axis=1,
                    level=-1,
                )

                if (
                    "Close"
                    not in ticker_data.columns
                ):
                    return None

                series = (
                    ticker_data["Close"]
                )

            else:
                return None

        # ----------------------------------------------------
        # SINGLE SYMBOL DOWNLOAD
        # ----------------------------------------------------

        else:

            if (
                "Close"
                not in data.columns
            ):
                return None

            series = (
                data["Close"]
            )

    except Exception:

        return None

    series = pd.to_numeric(
        series,
        errors="coerce",
    ).dropna()

    if series.empty:
        return None

    return series


# ============================================================
# RETURN CALCULATION
# ============================================================

def calculate_return(
    prices: pd.Series | None,
) -> float | None:
    """
    Calculate percentage return over the downloaded period.

    Formula:

        (Last Price / First Price - 1) * 100
    """

    if prices is None:
        return None

    prices = prices.dropna()

    if len(prices) < 2:
        return None

    first = safe_float(
        prices.iloc[0]
    )

    last = safe_float(
        prices.iloc[-1]
    )

    if (
        first is None
        or last is None
    ):
        return None

    if first <= 0:
        return None

    return (
        (last / first) - 1
    ) * 100


# ============================================================
# RELATIVE PERFORMANCE
# ============================================================

def get_relative_performance(
    ticker: str,
    benchmark: str = BENCHMARK,
    period: str = PERFORMANCE_PERIOD,
) -> dict[str, float | None]:
    """
    Compare stock performance with the benchmark.

    Relative Performance:

        Stock Return - Benchmark Return

    Example:

        Stock             +18%
        S&P 500           +10%
        Relative           +8%

    Positive values indicate outperformance.
    """

    ticker = normalize_ticker(
        ticker
    )

    benchmark = normalize_ticker(
        benchmark
    )

    data = (
        download_performance_history(
            [
                ticker,
                benchmark,
            ],
            period=period,
        )
    )

    if data.empty:

        return {
            "price_performance": None,
            "benchmark_performance": None,
            "relative_performance": None,
        }

    stock_prices = extract_close_series(
        data,
        ticker,
    )

    benchmark_prices = (
        extract_close_series(
            data,
            benchmark,
        )
    )

    stock_return = calculate_return(
        stock_prices
    )

    benchmark_return = (
        calculate_return(
            benchmark_prices
        )
    )

    relative = None

    if (
        stock_return is not None
        and benchmark_return is not None
    ):

        relative = (
            stock_return
            - benchmark_return
        )

    return {
        "price_performance": (
            stock_return
        ),

        "benchmark_performance": (
            benchmark_return
        ),

        "relative_performance": (
            relative
        ),
    }


# ============================================================
# FUNDAMENTAL SNAPSHOT
# ============================================================

def get_fundamentals(
    ticker: str,
) -> dict[str, Any]:
    """
    Retrieve the complete TickerTrends
    fundamental snapshot.

    No scoring is performed here.
    """

    ticker = normalize_ticker(
        ticker
    )

    # --------------------------------------------------------
    # COMPANY INFO
    # --------------------------------------------------------

    info = get_company_info(
        ticker
    )

    # --------------------------------------------------------
    # P/E
    # --------------------------------------------------------

    pe_ratio = get_pe_ratio(
        info
    )

    pe_source = get_pe_source(
        info
    )

    # --------------------------------------------------------
    # PEG
    # --------------------------------------------------------

    peg_ratio = get_peg_ratio(
        info
    )

    # --------------------------------------------------------
    # CASH FLOW
    # --------------------------------------------------------

    cash_flow_data = (
        get_statement_free_cash_flow(
            ticker
        )
    )

    operating_cash_flow = (
        cash_flow_data[
            "operating_cash_flow"
        ]
    )

    capital_expenditures = (
        cash_flow_data[
            "capital_expenditures"
        ]
    )

    free_cash_flow = (
        cash_flow_data[
            "free_cash_flow"
        ]
    )

    fcf_source = (
        cash_flow_data[
            "fcf_source"
        ]
    )

    # --------------------------------------------------------
    # REVENUE + FCF MARGIN
    # --------------------------------------------------------

    revenue = get_revenue(
        info
    )

    fcf_margin = (
        calculate_fcf_margin(
            free_cash_flow,
            revenue,
        )
    )

    # --------------------------------------------------------
    # RELATIVE PERFORMANCE
    # --------------------------------------------------------

    performance = (
        get_relative_performance(
            ticker
        )
    )

    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    return {
        "ticker": ticker,

        "company_name": (
            info.get("longName")
            or info.get("shortName")
        ),

        "sector": (
            info.get("sector")
        ),

        "industry": (
            info.get("industry")
        ),

        "pe_ratio": pe_ratio,

        "pe_source": (
            pe_source
        ),

        "peg_ratio": (
            peg_ratio
        ),

        "operating_cash_flow": (
            operating_cash_flow
        ),

        "capital_expenditures": (
            capital_expenditures
        ),

        "free_cash_flow": (
            free_cash_flow
        ),

        "fcf_source": (
            fcf_source
        ),

        "revenue": (
            revenue
        ),

        "fcf_margin": (
            fcf_margin
        ),

        "price_performance": (
            performance[
                "price_performance"
            ]
        ),

        "benchmark_performance": (
            performance[
                "benchmark_performance"
            ]
        ),

        "relative_performance": (
            performance[
                "relative_performance"
            ]
        ),
    }


# ============================================================
# DISPLAY HELPERS
# ============================================================

def format_money(
    value: float | None,
) -> str:
    """
    Format monetary values for console testing.
    """

    if value is None:
        return "N/A"

    absolute = abs(
        value
    )

    if absolute >= 1_000_000_000_000:

        return (
            f"${value / 1_000_000_000_000:.2f}T"
        )

    if absolute >= 1_000_000_000:

        return (
            f"${value / 1_000_000_000:.2f}B"
        )

    if absolute >= 1_000_000:

        return (
            f"${value / 1_000_000:.2f}M"
        )

    return f"${value:,.0f}"


def format_number(
    value: float | None,
    decimals: int = 2,
) -> str:
    """
    Format a numeric value.
    """

    if value is None:
        return "N/A"

    return (
        f"{value:.{decimals}f}"
    )


def format_percent(
    value: float | None,
) -> str:
    """
    Format a percentage.
    """

    if value is None:
        return "N/A"

    return f"{value:+.2f}%"


# ============================================================
# CONSOLE DISPLAY
# ============================================================

def print_fundamental_snapshot(
    snapshot: dict[str, Any],
) -> None:
    """
    Print a readable TickerTrends fundamental snapshot.
    """

    ticker = snapshot[
        "ticker"
    ]

    company = (
        snapshot.get(
            "company_name"
        )
        or ticker
    )

    print()

    print(
        f"TickerTrends Fundamentals: "
        f"{ticker}"
    )

    print("=" * 42)

    print(
        f"Company:               "
        f"{company}"
    )

    print(
        f"Sector:                "
        f"{snapshot.get('sector') or 'N/A'}"
    )

    print(
        f"Industry:              "
        f"{snapshot.get('industry') or 'N/A'}"
    )

    print(
        f"P/E:                   "
        f"{format_number(snapshot.get('pe_ratio'))}"
    )

    print(
        f"P/E Source:            "
        f"{snapshot.get('pe_source') or 'N/A'}"
    )

    print(
        f"PEG:                   "
        f"{format_number(snapshot.get('peg_ratio'))}"
    )

    print()

    print("CASH FLOW")
    print("-" * 42)

    print(
        f"Operating Cash Flow:   "
        f"{format_money(snapshot.get('operating_cash_flow'))}"
    )

    print(
        f"Capital Expenditures:  "
        f"{format_money(snapshot.get('capital_expenditures'))}"
    )

    print(
        f"Free Cash Flow:        "
        f"{format_money(snapshot.get('free_cash_flow'))}"
    )

    print(
        f"FCF Source:            "
        f"{snapshot.get('fcf_source') or 'N/A'}"
    )

    print(
        f"Revenue:               "
        f"{format_money(snapshot.get('revenue'))}"
    )

    print(
        f"FCF Margin:            "
        f"{format_percent(snapshot.get('fcf_margin'))}"
    )

    print()

    print("PERFORMANCE")
    print("-" * 42)

    print(
        f"6M Stock Performance: "
        f"{format_percent(snapshot.get('price_performance'))}"
    )

    print(
        f"6M S&P 500:           "
        f"{format_percent(snapshot.get('benchmark_performance'))}"
    )

    print(
        f"Relative Performance: "
        f"{format_percent(snapshot.get('relative_performance'))}"
    )

    print()


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    TEST_TICKER = "MSFT"

    print(
        f"Loading fundamentals for "
        f"{TEST_TICKER}..."
    )

    result = get_fundamentals(
        TEST_TICKER
    )

    print_fundamental_snapshot(
        result
    )
from __future__ import annotations

from pathlib import Path


# =========================================================
# PROJECT PATHS
# =========================================================

ROOT_DIR = Path(__file__).resolve().parent

DATA_DIR = ROOT_DIR / "data"

TICKER_FILE = DATA_DIR / "dividend_aristocrat_tickers.txt"

CACHE_FILE = ROOT_DIR / "dividend_cache.pkl"


# =========================================================
# APPLICATION SETTINGS
# =========================================================

APP_NAME = "MarketScope Dividend"

APP_ICON = "💰"

APP_DESCRIPTION = (
    "Dividend Aristocrat screening, analysis, comparison, "
    "and portfolio research."
)


# =========================================================
# MARKET SETTINGS
# =========================================================

# Broad-market benchmark
BENCHMARK_TICKER = "^GSPC"

# Historical period downloaded from Yahoo Finance
HISTORY_PERIOD = "5y"

# Daily price history
HISTORY_INTERVAL = "1d"

# Number of tickers downloaded in each batch.
# Smaller batches allow more frequent progress updates.
DOWNLOAD_BATCH_SIZE = 15


# =========================================================
# TECHNICAL INDICATOR SETTINGS
# =========================================================

SMA_SHORT = 50
SMA_LONG = 200

RSI_PERIOD = 14

RETURN_PERIODS = {
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "1Y": 252,
}


# =========================================================
# DIVIDEND SETTINGS
# =========================================================

# Used later by the dividend scoring engine.

MIN_DIVIDEND_YIELD = 0.0

# Payout-ratio ranges used for scoring.
PAYOUT_RATIO_IDEAL_MAX = 0.60
PAYOUT_RATIO_ACCEPTABLE_MAX = 0.80

# Dividend-growth periods we intend to calculate.
DIVIDEND_GROWTH_YEARS = [
    1,
    3,
    5,
]


# =========================================================
# SCORING WEIGHTS
# =========================================================

# Overall MarketScope Dividend Score
#
# Must total 1.00

SCORE_WEIGHTS = {
    "dividend": 0.30,
    "quality": 0.25,
    "value": 0.20,
    "momentum": 0.15,
    "risk": 0.10,
}


# =========================================================
# DIVIDEND SCORE COMPONENTS
# =========================================================

DIVIDEND_WEIGHTS = {
    "yield": 0.35,
    "payout_ratio": 0.25,
    "dividend_growth": 0.25,
    "dividend_consistency": 0.15,
}


# =========================================================
# QUALITY SCORE COMPONENTS
# =========================================================

QUALITY_WEIGHTS = {
    "roe": 0.25,
    "profit_margin": 0.20,
    "free_cash_flow": 0.20,
    "debt_to_equity": 0.20,
    "earnings_quality": 0.15,
}


# =========================================================
# VALUE SCORE COMPONENTS
# =========================================================

VALUE_WEIGHTS = {
    "pe_ratio": 0.30,
    "forward_pe": 0.25,
    "peg_ratio": 0.20,
    "price_to_book": 0.10,
    "price_to_fcf": 0.15,
}


# =========================================================
# MOMENTUM SCORE COMPONENTS
# =========================================================

MOMENTUM_WEIGHTS = {
    "price_vs_sma50": 0.20,
    "price_vs_sma200": 0.25,
    "six_month_return": 0.20,
    "one_year_return": 0.25,
    "rsi": 0.10,
}


# =========================================================
# RISK SCORE COMPONENTS
# =========================================================

RISK_WEIGHTS = {
    "beta": 0.30,
    "volatility": 0.30,
    "max_drawdown": 0.25,
    "52_week_position": 0.15,
}


# =========================================================
# PORTFOLIO SETTINGS
# =========================================================

DEFAULT_PORTFOLIO_VALUE = 10_000

DEFAULT_NUMBER_OF_HOLDINGS = 10

MAX_PORTFOLIO_HOLDINGS = 30


# =========================================================
# DISPLAY SETTINGS
# =========================================================

PERCENT_DECIMALS = 2

PRICE_DECIMALS = 2

SCORE_DECIMALS = 1


# =========================================================
# TICKER LOADING
# =========================================================

def load_dividend_tickers() -> list[str]:
    """
    Load the Dividend Aristocrat universe from the ticker file.

    Blank lines are ignored and ticker symbols are converted
    to uppercase.
    """

    if not TICKER_FILE.exists():
        raise FileNotFoundError(
            f"Dividend ticker file not found: {TICKER_FILE}"
        )

    tickers = []

    with open(TICKER_FILE, "r", encoding="utf-8") as file:
        for line in file:
            ticker = line.strip().upper()

            if ticker:
                tickers.append(ticker)

    # Remove duplicates while preserving original order.
    return list(dict.fromkeys(tickers))


# =========================================================
# SCORE VALIDATION
# =========================================================

def validate_weights(
    weights: dict[str, float],
    name: str,
) -> None:
    """
    Confirm that a scoring-weight dictionary totals 1.00.
    """

    total = sum(weights.values())

    if abs(total - 1.0) > 0.0001:
        raise ValueError(
            f"{name} weights total {total:.4f}; "
            "expected 1.0000."
        )


def validate_config() -> None:
    """
    Validate MarketScope Dividend scoring configuration.
    """

    validate_weights(
        SCORE_WEIGHTS,
        "Overall score",
    )

    validate_weights(
        DIVIDEND_WEIGHTS,
        "Dividend score",
    )

    validate_weights(
        QUALITY_WEIGHTS,
        "Quality score",
    )

    validate_weights(
        VALUE_WEIGHTS,
        "Value score",
    )

    validate_weights(
        MOMENTUM_WEIGHTS,
        "Momentum score",
    )

    validate_weights(
        RISK_WEIGHTS,
        "Risk score",
    )
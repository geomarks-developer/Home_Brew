"""
StockChoice Universe Management

Provides:

    - All Stocks
    - S&P 500
    - Nasdaq 100
    - Dow 30
    - Dividend Universe
    - Custom Lists

Used by:

    Screener
    Heatmap
    Portfolio Builder
"""

from __future__ import annotations

from pathlib import Path


# ============================================================
# PATHS
# ============================================================

DATA_DIR = Path("data")

SP100_FILE = DATA_DIR / "sp100.txt"

NASDAQ100_FILE = DATA_DIR / "nasdaq100.txt"

DOW30_FILE = DATA_DIR / "dow30.txt"

DIVIDEND_FILE = DATA_DIR / "aristocrats.txt"


# ============================================================
# FILE LOADER
# ============================================================

def load_ticker_file(
    filepath: Path
) -> list[str]:

    if not filepath.exists():
        return []

    with open(
        filepath,
        "r",
        encoding="utf-8"
    ) as file:

        tickers = [
            line.strip().upper()
            for line in file
            if line.strip()
        ]

    return sorted(
        list(
            set(tickers)
        )
    )


# ============================================================
# STANDARD UNIVERSES
# ============================================================

def get_sp100_tickers() -> list[str]:

    return load_ticker_file(
        SP100_FILE
    )


def get_nasdaq100_tickers() -> list[str]:

    return load_ticker_file(
        NASDAQ100_FILE
    )


def get_dow30_tickers() -> list[str]:

    return load_ticker_file(
        DOW30_FILE
    )


def get_dividend_tickers() -> list[str]:

    return load_ticker_file(
        DIVIDEND_FILE
    )


# ============================================================
# COMBINED UNIVERSE
# ============================================================

def get_all_tickers() -> list[str]:

    tickers = (
        get_sp100_tickers()
        + get_nasdaq100_tickers()
        + get_dow30_tickers()
        + get_dividend_tickers()
    )

    return sorted(
        list(
            set(tickers)
        )
    )


# ============================================================
# CUSTOM UNIVERSE
# ============================================================

def get_custom_tickers(
    ticker_string: str
) -> list[str]:

    if not ticker_string:
        return []

    tickers = [
        ticker.strip().upper()
        for ticker in ticker_string.split(",")
        if ticker.strip()
    ]

    return sorted(
        list(
            set(tickers)
        )
    )


# ============================================================
# UNIVERSE LOOKUP
# ============================================================

UNIVERSES = {

    "all":
        get_all_tickers,

    "sp100":
        get_sp100_tickers,

    "nasdaq100":
        get_nasdaq100_tickers,

    "dow30":
        get_dow30_tickers,

    "dividend":
        get_dividend_tickers,
}


def get_universe(
    universe_name: str | None
) -> list[str]:

    if not universe_name:
        return []

    loader = UNIVERSES.get(
        universe_name.lower()
    )

    if loader is None:
        return []

    return loader()


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_UNIVERSE = "sp100"
DEFAULT_STRATEGY = "garp"


# ============================================================
# UNIVERSE METADATA
# ============================================================

UNIVERSE_DISPLAY_NAMES = {

    "all":
        "All Stocks",

    "sp100":
        "S&P 100",

    "nasdaq100":
        "Nasdaq 100",

    "dow30":
        "Dow 30",

    "dividend":
        "Dividend Growth",
}


def get_universe_name(
    key: str
) -> str:

    return UNIVERSE_DISPLAY_NAMES.get(
        key,
        key
    )


def get_available_universes() -> list[str]:

    return list(
        UNIVERSES.keys()
    )


# ============================================================
# VALIDATION
# ============================================================

def universe_stats() -> dict:

    return {

        "all":
            len(
                get_all_tickers()
            ),

        "sp100":
            len(
                get_sp100_tickers()
            ),

        "nasdaq100":
            len(
                get_nasdaq100_tickers()
            ),

        "dow30":
            len(
                get_dow30_tickers()
            ),

        "dividend":
            len(
                get_dividend_tickers()
            ),
    }


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print()

    print("Universe Counts")
    print("----------------")

    for name, count in universe_stats().items():
        print(
            f"{name}: {count}"
        )

    print()

    print(
        "Available Universes:"
    )

    print(
        get_available_universes()
    )
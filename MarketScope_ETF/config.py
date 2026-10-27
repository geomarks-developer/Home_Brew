"""
MarketScope ETF
Configuration and ETF universe definitions.
"""

# =========================================================
# APPLICATION SETTINGS
# =========================================================

APP_NAME = "MarketScope ETF"

APP_DESCRIPTION = (
    "ETF screening, sector analysis, market trend analysis, "
    "ETF comparison, and portfolio construction."
)

APP_VERSION = "0.1.0"


# =========================================================
# BENCHMARKS
# =========================================================

PRIMARY_BENCHMARK = "SPY"

BENCHMARKS = {
    "S&P 500": "SPY",
    "Nasdaq 100": "QQQ",
    "Dow Jones": "DIA",
    "Russell 2000": "IWM",
    "Total US Market": "VTI",
    "International": "VXUS",
}


# =========================================================
# SECTOR ETFs
# =========================================================
#
# These are the Select Sector SPDR ETFs used for the
# MarketScope sector leadership and rotation analysis.
#

SECTOR_ETFS = {
    "Communication Services": "XLC",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
}


SECTOR_TICKER_TO_NAME = {
    ticker: sector
    for sector, ticker in SECTOR_ETFS.items()
}


# =========================================================
# BROAD MARKET ETFs
# =========================================================

BROAD_MARKET_ETFS = [
    "SPY",
    "VOO",
    "IVV",
    "VTI",
    "QQQ",
    "DIA",
    "IWM",
    "IJH",
    "RSP",
]


# =========================================================
# GROWTH ETFs
# =========================================================

GROWTH_ETFS = [
    "VUG",
    "SCHG",
    "IWF",
    "QQQ",
    "QQQM",
    "MGK",
    "VONG",
]


# =========================================================
# VALUE ETFs
# =========================================================

VALUE_ETFS = [
    "VTV",
    "SCHV",
    "IWD",
    "IVE",
    "VOOV",
    "RPV",
]


# =========================================================
# DIVIDEND / INCOME ETFs
# =========================================================

DIVIDEND_ETFS = [
    "SCHD",
    "VIG",
    "VYM",
    "DGRO",
    "HDV",
    "DVY",
    "SDY",
    "NOBL",
    "DGRW",
]


# =========================================================
# INTERNATIONAL ETFs
# =========================================================

INTERNATIONAL_ETFS = [
    "VXUS",
    "VEA",
    "IEFA",
    "EFA",
    "VWO",
    "IEMG",
    "EEM",
    "SCHF",
    "SCHY",
]


# =========================================================
# BOND ETFs
# =========================================================

BOND_ETFS = [
    "BND",
    "AGG",
    "TLT",
    "IEF",
    "SHY",
    "SGOV",
    "BIL",
    "LQD",
    "HYG",
    "JNK",
    "TIP",
]


# =========================================================
# REAL ESTATE ETFs
# =========================================================

REAL_ESTATE_ETFS = [
    "VNQ",
    "SCHH",
    "IYR",
    "USRT",
    "XLRE",
]


# =========================================================
# COMMODITY / PRECIOUS METAL ETFs
# =========================================================

COMMODITY_ETFS = [
    "GLD",
    "IAU",
    "SLV",
    "DBC",
    "PDBC",
]


# =========================================================
# FACTOR / QUALITY ETFs
# =========================================================

FACTOR_ETFS = [
    "QUAL",
    "MTUM",
    "USMV",
    "VLUE",
    "SPHQ",
    "VFMF",
]


# =========================================================
# THEMATIC / INDUSTRY ETFs
# =========================================================

THEMATIC_ETFS = [
    "SMH",
    "SOXX",
    "IGV",
    "CIBR",
    "HACK",
    "SKYY",
    "BOTZ",
    "ARKK",
    "XBI",
    "IBB",
    "ITA",
    "PAVE",
    "ICLN",
]


# =========================================================
# ETF CATEGORIES
# =========================================================
#
# Used throughout Streamlit for filters, dropdowns,
# heatmaps, comparisons, and portfolio construction.
#

ETF_CATEGORIES = {
    "Broad Market": BROAD_MARKET_ETFS,
    "Sector": list(SECTOR_ETFS.values()),
    "Growth": GROWTH_ETFS,
    "Value": VALUE_ETFS,
    "Dividend": DIVIDEND_ETFS,
    "International": INTERNATIONAL_ETFS,
    "Bonds": BOND_ETFS,
    "Real Estate": REAL_ESTATE_ETFS,
    "Commodities": COMMODITY_ETFS,
    "Factor / Quality": FACTOR_ETFS,
    "Thematic / Industry": THEMATIC_ETFS,
}


# =========================================================
# COMPLETE ETF UNIVERSE
# =========================================================
#
# Remove duplicates because some ETFs intentionally appear
# in multiple categories.
#
# Example:
# QQQ = Broad Market + Growth
# XLRE = Sector + Real Estate
#

ETF_UNIVERSE = sorted(
    {
        ticker
        for tickers in ETF_CATEGORIES.values()
        for ticker in tickers
    }
)


# =========================================================
# ETF CATEGORY LOOKUP
# =========================================================
#
# A ticker can belong to multiple MarketScope categories.
#

ETF_CATEGORY_LOOKUP = {}

for category, tickers in ETF_CATEGORIES.items():

    for ticker in tickers:

        if ticker not in ETF_CATEGORY_LOOKUP:
            ETF_CATEGORY_LOOKUP[ticker] = []

        ETF_CATEGORY_LOOKUP[ticker].append(category)


def get_etf_categories(ticker):
    """
    Return all MarketScope categories associated with an ETF.
    """

    return ETF_CATEGORY_LOOKUP.get(
        ticker.upper(),
        ["Unclassified"],
    )


# =========================================================
# PERFORMANCE WINDOWS
# =========================================================

PERFORMANCE_WINDOWS = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "YTD": "YTD",
    "1Y": 252,
}


# =========================================================
# MOVING AVERAGES
# =========================================================

SMA_SHORT = 50
SMA_LONG = 200

MOVING_AVERAGES = [
    SMA_SHORT,
    SMA_LONG,
]


# =========================================================
# RSI SETTINGS
# =========================================================

RSI_PERIOD = 14

RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70


# =========================================================
# ETF SCORING WEIGHTS
# =========================================================
#
# These can eventually become adjustable from Streamlit.
#

ETF_SCORE_WEIGHTS = {
    "momentum": 0.30,
    "trend": 0.25,
    "cost": 0.15,
    "liquidity": 0.10,
    "dividend": 0.10,
    "risk": 0.10,
}


# =========================================================
# SECTOR SCORING WEIGHTS
# =========================================================

SECTOR_SCORE_WEIGHTS = {
    "1M": 0.15,
    "3M": 0.25,
    "6M": 0.25,
    "1Y": 0.20,
    "trend": 0.15,
}


# =========================================================
# TREND DEFINITIONS
# =========================================================

TREND_LABELS = {
    5: "Strong Uptrend",
    4: "Uptrend",
    3: "Neutral",
    2: "Downtrend",
    1: "Strong Downtrend",
}


TREND_COLORS = {
    "Strong Uptrend": "#008000",
    "Uptrend": "#2E8B57",
    "Neutral": "#DAA520",
    "Downtrend": "#FF8C00",
    "Strong Downtrend": "#B22222",
}


# =========================================================
# HEATMAP SETTINGS
# =========================================================

HEATMAP_PERIODS = [
    "1D",
    "1W",
    "1M",
    "3M",
    "6M",
    "YTD",
    "1Y",
]


# =========================================================
# DATA SETTINGS
# =========================================================

HISTORY_PERIOD = "2y"

PRICE_INTERVAL = "1d"

CACHE_FILENAME = "marketscope_etf_cache.pkl"

CACHE_MAX_AGE_HOURS = 24


# =========================================================
# PORTFOLIO SETTINGS
# =========================================================

DEFAULT_PORTFOLIO_VALUE = 10000


PORTFOLIO_MODELS = {

    "Conservative": {
        "Broad Market": 0.30,
        "Dividend": 0.15,
        "International": 0.10,
        "Bonds": 0.35,
        "Real Estate": 0.05,
        "Commodities": 0.05,
    },

    "Balanced": {
        "Broad Market": 0.35,
        "Growth": 0.10,
        "Dividend": 0.10,
        "International": 0.15,
        "Bonds": 0.20,
        "Real Estate": 0.05,
        "Commodities": 0.05,
    },

    "Growth": {
        "Broad Market": 0.35,
        "Growth": 0.25,
        "International": 0.15,
        "Sector": 0.15,
        "Bonds": 0.05,
        "Real Estate": 0.05,
    },

    "Income": {
        "Dividend": 0.35,
        "Broad Market": 0.20,
        "Bonds": 0.30,
        "Real Estate": 0.10,
        "International": 0.05,
    },

    "Aggressive": {
        "Growth": 0.35,
        "Broad Market": 0.25,
        "Sector": 0.20,
        "Thematic / Industry": 0.10,
        "International": 0.10,
    },
}
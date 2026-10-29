# =========================================================
# MarketScope Growth
# config.py
#
# Central configuration for:
#   - Stock universe
#   - Growth scoring
#   - Quality scoring
#   - Valuation scoring
#   - Momentum scoring
#   - Overall score
#   - Rating thresholds
# =========================================================


# =========================================================
# APPLICATION
# =========================================================

APP_NAME = "MarketScope Growth"
APP_VERSION = "1.0"

BENCHMARK = "SPY"

CACHE_FILE = "growth_market_data.pkl"
CACHE_MAX_AGE_HOURS = 12


# =========================================================
# STOCK UNIVERSE
# =========================================================
#
# Broad collection of established and emerging growth
# companies across multiple sectors.
#
# We can expand or replace this later with an automated
# universe such as the S&P 500, Nasdaq-100, or Russell 1000.
# =========================================================

GROWTH_TICKERS = [

    # -----------------------------------------------------
    # Technology
    # -----------------------------------------------------
    "AAPL",
    "MSFT",
    "NVDA",
    "AVGO",
    "AMD",
    "MU",
    "QCOM",
    "TXN",
    "ADI",
    "MRVL",
    "ARM",
    "INTC",

    "CRM",
    "NOW",
    "ADBE",
    "ORCL",
    "INTU",
    "PANW",
    "CRWD",
    "FTNT",
    "ZS",
    "DDOG",
    "MDB",
    "SNOW",
    "NET",
    "PLTR",
    "TEAM",
    "HUBS",
    "SHOP",

    # -----------------------------------------------------
    # Communication Services / Internet
    # -----------------------------------------------------
    "GOOG",
    "GOOGL",
    "META",
    "NFLX",
    "TTD",
    "SPOT",
    "PINS",
    "RDDT",

    # -----------------------------------------------------
    # Consumer Discretionary
    # -----------------------------------------------------
    "AMZN",
    "TSLA",
    "BKNG",
    "ABNB",
    "MELI",
    "UBER",
    "DASH",
    "CMG",
    "CAVA",
    "LULU",
    "NKE",
    "TJX",
    "ROST",
    "ORLY",
    "AZO",

    # -----------------------------------------------------
    # Financial / Fintech
    # -----------------------------------------------------
    "V",
    "MA",
    "AXP",
    "PYPL",
    "COIN",
    "HOOD",
    "SOFI",
    "NU",

    # -----------------------------------------------------
    # Healthcare
    # -----------------------------------------------------
    "LLY",
    "NVO",
    "ISRG",
    "VRTX",
    "REGN",
    "DXCM",
    "TMO",
    "DHR",
    "ABT",
    "SYK",
    "BSX",

    # -----------------------------------------------------
    # Industrials
    # -----------------------------------------------------
    "GE",
    "GEV",
    "ETN",
    "PH",
    "CAT",
    "DE",
    "URI",
    "PWR",
    "FIX",
    "TT",
    "HUBB",

    # -----------------------------------------------------
    # Energy
    # -----------------------------------------------------
    "FANG",
    "EQT",

    # -----------------------------------------------------
    # Consumer Staples
    # -----------------------------------------------------
    "COST",
    "WMT",

    # -----------------------------------------------------
    # Emerging / Higher-Risk Growth
    # -----------------------------------------------------
    "RKLB",
    "ASTS",
    "IONQ",
    "RGTI",
    "SOUN",
    "TEM",
    "HIMS",
    "APP",
]


# Remove duplicates while preserving order
GROWTH_TICKERS = list(dict.fromkeys(GROWTH_TICKERS))


# =========================================================
# MINIMUM COMPANY SIZE
# =========================================================

MIN_MARKET_CAP = 2_000_000_000

LARGE_CAP = 10_000_000_000
MEGA_CAP = 200_000_000_000


# =========================================================
# SCORING MODEL
# =========================================================
#
# Overall Score:
#
# Growth      40%
# Quality     25%
# Valuation   15%
# Momentum    20%
#
# Growth intentionally receives the largest weight.
# =========================================================

CATEGORY_WEIGHTS = {
    "growth": 0.40,
    "quality": 0.25,
    "valuation": 0.15,
    "momentum": 0.20,
}


# =========================================================
# GROWTH SCORE WEIGHTS
# =========================================================

GROWTH_WEIGHTS = {
    "revenue_growth": 0.30,
    "earnings_growth": 0.25,
    "eps_growth": 0.20,
    "forward_eps_growth": 0.25,
}


# =========================================================
# QUALITY SCORE WEIGHTS
# =========================================================

QUALITY_WEIGHTS = {
    "roe": 0.30,
    "operating_margin": 0.25,
    "profit_margin": 0.20,
    "free_cash_flow": 0.15,
    "debt_control": 0.10,
}


# =========================================================
# VALUATION SCORE WEIGHTS
# =========================================================

VALUATION_WEIGHTS = {
    "forward_pe": 0.40,
    "peg": 0.40,
    "price_to_sales": 0.20,
}


# =========================================================
# MOMENTUM SCORE WEIGHTS
# =========================================================

MOMENTUM_WEIGHTS = {
    "return_6m": 0.25,
    "return_12m": 0.30,
    "above_50dma": 0.15,
    "above_200dma": 0.20,
    "distance_52w_high": 0.10,
}


# =========================================================
# GROWTH THRESHOLDS
# =========================================================
#
# Values represent decimal percentages.
#
# Example:
# 0.20 = 20%
# =========================================================

GROWTH_THRESHOLDS = {

    "revenue_growth": {
        "excellent": 0.25,
        "strong": 0.15,
        "moderate": 0.08,
        "minimum": 0.00,
    },

    "earnings_growth": {
        "excellent": 0.30,
        "strong": 0.20,
        "moderate": 0.10,
        "minimum": 0.00,
    },

    "eps_growth": {
        "excellent": 0.30,
        "strong": 0.20,
        "moderate": 0.10,
        "minimum": 0.00,
    },

    "forward_eps_growth": {
        "excellent": 0.25,
        "strong": 0.15,
        "moderate": 0.08,
        "minimum": 0.00,
    },
}


# =========================================================
# QUALITY THRESHOLDS
# =========================================================

QUALITY_THRESHOLDS = {

    "roe": {
        "excellent": 0.25,
        "strong": 0.18,
        "moderate": 0.12,
    },

    "operating_margin": {
        "excellent": 0.25,
        "strong": 0.18,
        "moderate": 0.10,
    },

    "profit_margin": {
        "excellent": 0.20,
        "strong": 0.12,
        "moderate": 0.05,
    },
}


# =========================================================
# VALUATION THRESHOLDS
# =========================================================

VALUATION_THRESHOLDS = {

    "forward_pe": {
        "excellent": 20,
        "good": 30,
        "fair": 40,
        "expensive": 60,
    },

    "peg": {
        "excellent": 1.0,
        "good": 1.5,
        "fair": 2.0,
        "expensive": 3.0,
    },

    "price_to_sales": {
        "excellent": 3.0,
        "good": 6.0,
        "fair": 10.0,
        "expensive": 15.0,
    },
}


# =========================================================
# MOMENTUM SETTINGS
# =========================================================

PRICE_HISTORY_PERIOD = "2y"

MA_SHORT = 50
MA_LONG = 200


# =========================================================
# OVERALL SCORE RATINGS
# =========================================================

RATING_THRESHOLDS = {
    85: "Elite Growth",
    75: "Strong Growth",
    65: "Attractive Growth",
    55: "Moderate Growth",
    45: "Watch",
    0: "Weak Growth",
}


# =========================================================
# GROWTH CLASSIFICATION
# =========================================================

GROWTH_SCORE_RATINGS = {
    80: "Exceptional Growth",
    65: "Strong Growth",
    50: "Moderate Growth",
    35: "Slow Growth",
    0: "Weak Growth",
}


# =========================================================
# VALUATION CLASSIFICATION
# =========================================================

VALUATION_SCORE_RATINGS = {
    80: "Attractive",
    65: "Reasonable",
    50: "Fair",
    35: "Expensive",
    0: "Very Expensive",
}


# =========================================================
# PRESET SCREENS
# =========================================================

PRESET_SCREENS = {

    "All Growth Stocks": {
        "min_overall_score": 0,
    },

    "Elite Growth": {
        "min_growth_score": 80,
        "min_quality_score": 60,
    },

    "Strong Growth": {
        "min_growth_score": 65,
    },

    "Profitable Growth": {
        "min_growth_score": 65,
        "min_quality_score": 70,
    },

    "Growth at a Reasonable Price": {
        "min_growth_score": 60,
        "min_valuation_score": 60,
    },

    "Growth + Momentum": {
        "min_growth_score": 65,
        "min_momentum_score": 65,
    },

    "High Conviction": {
        "min_overall_score": 75,
        "min_growth_score": 70,
        "min_quality_score": 60,
    },
}


# =========================================================
# DISPLAY SETTINGS
# =========================================================

DEFAULT_TOP_N = 25

SCORE_DECIMALS = 1

PERCENT_DECIMALS = 1

PRICE_DECIMALS = 2


# =========================================================
# TABLE COLORS
# =========================================================

SCORE_COLORS = {

    "excellent": "#1b5e20",

    "strong": "#2e7d32",

    "good": "#66bb6a",

    "neutral": "#fbc02d",

    "weak": "#ef6c00",

    "poor": "#c62828",
}


# =========================================================
# SECTOR COLORS
# =========================================================
#
# These can later be shared between:
# - Sector bar charts
# - Donut charts
# - Heatmaps
# - Stock Explorer
# =========================================================

SECTOR_COLORS = {

    "Technology": "#1f77b4",

    "Communication Services": "#9467bd",

    "Consumer Cyclical": "#ff7f0e",

    "Consumer Defensive": "#2ca02c",

    "Healthcare": "#e377c2",

    "Financial Services": "#17becf",

    "Industrials": "#7f7f7f",

    "Energy": "#8c564b",

    "Basic Materials": "#bcbd22",

    "Real Estate": "#d62728",

    "Utilities": "#aec7e8",

    "Unknown": "#bdbdbd",
}


# =========================================================
# DATA COLUMNS
# =========================================================

SCREENER_COLUMNS = [

    "Ticker",
    "Company",
    "Sector",

    "Price",
    "Market Cap",

    "Revenue Growth",
    "Earnings Growth",
    "EPS Growth",
    "Forward EPS Growth",

    "ROE",
    "Operating Margin",
    "Profit Margin",

    "Forward PE",
    "PEG",
    "Price/Sales",

    "6M Return",
    "12M Return",

    "50D MA",
    "200D MA",
    "52W High",

    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",

    "Overall Score",
    "Rating",
]


# =========================================================
# REQUIRED DATA FIELDS
# =========================================================
#
# growth_engine.py can use this mapping when translating
# raw data into MarketScope column names.
# =========================================================

INFO_FIELDS = {

    "shortName": "Company",

    "sector": "Sector",

    "currentPrice": "Price",

    "marketCap": "Market Cap",

    "revenueGrowth": "Revenue Growth",

    "earningsGrowth": "Earnings Growth",

    "returnOnEquity": "ROE",

    "operatingMargins": "Operating Margin",

    "profitMargins": "Profit Margin",

    "forwardPE": "Forward PE",

    "pegRatio": "PEG",

    "priceToSalesTrailing12Months": "Price/Sales",

    "freeCashflow": "Free Cash Flow",

    "totalDebt": "Total Debt",

    "totalCash": "Total Cash",

    "fiftyDayAverage": "50D MA",

    "twoHundredDayAverage": "200D MA",

    "fiftyTwoWeekHigh": "52W High",
}
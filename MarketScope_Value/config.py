"""MarketScope Value configuration and scoring definitions."""
from __future__ import annotations


# =========================================================
# APPLICATION
# =========================================================

APP_NAME = "MarketScope Value"
APP_DESCRIPTION = (
    "Value-stock screening, quality analysis, financial-strength analysis, "
    "momentum review, portfolio construction, and value-trap detection."
)
APP_VERSION = "0.1.0"


# =========================================================
# VALUE UNIVERSE
# =========================================================
# Initial diversified large/mid-cap research universe.
# We can replace this later with a broader imported universe without changing
# the scoring engine or page architecture.

VALUE_TICKERS = [
    # Technology / Communication
    "AAPL", "ACN", "ADBE", "CSCO", "GOOG", "GOOGL", "HPQ", "IBM",
    "INTC", "META", "MU", "ORCL", "QCOM", "TXN", "VZ",

    # Financials
    "AFL", "AIG", "AXP", "BAC", "BK", "BLK", "C", "CB", "GS", "JPM",
    "MET", "MS", "PNC", "PRU", "SCHW", "TROW", "USB", "WFC",

    # Health Care
    "ABBV", "BMY", "CVS", "GILD", "JNJ", "MDT", "MRK", "PFE", "UNH",

    # Consumer
    "BBY", "CMCSA", "CVS", "F", "GM", "HD", "LOW", "MCD", "NKE",
    "SBUX", "TGT", "WMT",

    # Industrials / Transportation
    "CAT", "CSX", "DE", "EMR", "FDX", "GD", "HON", "LMT", "MMM",
    "NSC", "UPS",

    # Energy
    "COP", "CVX", "EOG", "HAL", "MPC", "OXY", "PSX", "SLB", "XOM",

    # Materials
    "APD", "DOW", "FCX", "LIN", "NEM", "NUE",

    # Utilities
    "AEP", "D", "DUK", "ED", "EXC", "NEE", "SO", "SRE", "XEL",

    # Real Estate
    "AMT", "CCI", "DLR", "O", "PLD", "SPG", "VICI",

    # Staples
    "ADM", "CL", "GIS", "KHC", "KO", "KMB", "KR", "MDLZ", "MO",
    "PEP", "PG", "SYY",
]

# Preserve order while removing duplicate symbols.
VALUE_TICKERS = list(dict.fromkeys(VALUE_TICKERS))


# =========================================================
# DATA SETTINGS
# =========================================================

CACHE_FILE = "marketscope_value_cache.pkl"
CACHE_MAX_AGE_HOURS = 24
PRICE_HISTORY_PERIOD = "2y"
PRICE_INTERVAL = "1d"
MA_SHORT = 50
MA_LONG = 200
MIN_MARKET_CAP = 2_000_000_000
DEFAULT_TOP_N = 15


# =========================================================
# YFINANCE INFO FIELDS
# =========================================================
# source field -> MarketScope column

INFO_FIELDS = {
    "currentPrice": "Price",
    "marketCap": "Market Cap",
    "enterpriseValue": "Enterprise Value",

    # Valuation
    "trailingPE": "Trailing PE",
    "forwardPE": "Forward PE",
    "priceToBook": "Price/Book",
    "priceToSalesTrailing12Months": "Price/Sales",
    "enterpriseToEbitda": "EV/EBITDA",
    "enterpriseToRevenue": "EV/Revenue",
    "pegRatio": "PEG",

    # Earnings / growth
    "earningsGrowth": "Earnings Growth",
    "revenueGrowth": "Revenue Growth",
    "earningsQuarterlyGrowth": "EPS Growth",

    # Profitability / quality
    "returnOnEquity": "ROE",
    "returnOnAssets": "ROA",
    "operatingMargins": "Operating Margin",
    "profitMargins": "Profit Margin",
    "grossMargins": "Gross Margin",
    "ebitda": "EBITDA",

    # Cash flow / balance sheet
    "freeCashflow": "Free Cash Flow",
    "operatingCashflow": "Operating Cash Flow",
    "totalCash": "Total Cash",
    "totalDebt": "Total Debt",
    "debtToEquity": "Debt/Equity",
    "currentRatio": "Current Ratio",
    "quickRatio": "Quick Ratio",

    # Income / shareholder return
    "dividendYield": "Dividend Yield",
    "payoutRatio": "Payout Ratio",

    # Identity
    "longName": "Company",
    "sector": "Sector",
    "industry": "Industry",
}


# =========================================================
# OVERALL VALUE SCORE WEIGHTS
# =========================================================

CATEGORY_WEIGHTS = {
    "valuation": 0.40,
    "quality": 0.25,
    "financial_strength": 0.15,
    "growth": 0.10,
    "momentum": 0.10,
}


# =========================================================
# VALUATION SCORE
# =========================================================
# Lower multiples generally score better. FCF and earnings yields score higher
# when larger and positive. Missing measures should be excluded and remaining
# weights normalized by the scoring engine.

VALUATION_WEIGHTS = {
    "forward_pe": 0.18,
    "trailing_pe": 0.10,
    "price_to_book": 0.10,
    "price_to_sales": 0.10,
    "ev_to_ebitda": 0.17,
    "fcf_yield": 0.20,
    "earnings_yield": 0.15,
}

VALUATION_THRESHOLDS = {
    "forward_pe": {
        "excellent": 10.0,
        "good": 15.0,
        "fair": 22.0,
        "expensive": 32.0,
    },
    "trailing_pe": {
        "excellent": 10.0,
        "good": 15.0,
        "fair": 22.0,
        "expensive": 32.0,
    },
    "price_to_book": {
        "excellent": 1.0,
        "good": 2.0,
        "fair": 3.5,
        "expensive": 6.0,
    },
    "price_to_sales": {
        "excellent": 1.0,
        "good": 2.0,
        "fair": 4.0,
        "expensive": 7.0,
    },
    "ev_to_ebitda": {
        "excellent": 6.0,
        "good": 9.0,
        "fair": 13.0,
        "expensive": 20.0,
    },
    "fcf_yield": {
        "minimum": 0.00,
        "moderate": 0.04,
        "strong": 0.07,
        "excellent": 0.10,
    },
    "earnings_yield": {
        "minimum": 0.00,
        "moderate": 0.04,
        "strong": 0.07,
        "excellent": 0.10,
    },
}


# =========================================================
# QUALITY SCORE
# =========================================================

QUALITY_WEIGHTS = {
    "roe": 0.25,
    "operating_margin": 0.20,
    "profit_margin": 0.20,
    "free_cash_flow": 0.20,
    "cash_conversion": 0.15,
}

QUALITY_THRESHOLDS = {
    "roe": {
        "minimum": 0.00,
        "moderate": 0.10,
        "strong": 0.18,
        "excellent": 0.28,
    },
    "operating_margin": {
        "minimum": 0.00,
        "moderate": 0.08,
        "strong": 0.15,
        "excellent": 0.25,
    },
    "profit_margin": {
        "minimum": 0.00,
        "moderate": 0.06,
        "strong": 0.12,
        "excellent": 0.20,
    },
    "cash_conversion": {
        "minimum": 0.00,
        "moderate": 0.50,
        "strong": 0.75,
        "excellent": 1.00,
    },
}


# =========================================================
# FINANCIAL STRENGTH SCORE
# =========================================================

FINANCIAL_STRENGTH_WEIGHTS = {
    "net_debt_to_market_cap": 0.35,
    "debt_to_equity": 0.25,
    "current_ratio": 0.20,
    "cash_to_debt": 0.20,
}

FINANCIAL_STRENGTH_THRESHOLDS = {
    "net_debt_to_market_cap": {
        "excellent": -0.10,
        "good": 0.00,
        "fair": 0.20,
        "weak": 0.50,
        "poor": 1.00,
    },
    "debt_to_equity": {
        "excellent": 20.0,
        "good": 60.0,
        "fair": 120.0,
        "weak": 200.0,
    },
    "current_ratio": {
        "minimum": 0.60,
        "moderate": 1.00,
        "strong": 1.50,
        "excellent": 2.00,
    },
    "cash_to_debt": {
        "minimum": 0.00,
        "moderate": 0.25,
        "strong": 0.60,
        "excellent": 1.00,
    },
}


# =========================================================
# GROWTH SCORE
# =========================================================
# Growth receives a smaller weight than in MarketScope Growth. Here its main
# purpose is to distinguish healthy inexpensive businesses from deteriorating
# businesses that merely appear cheap.

GROWTH_WEIGHTS = {
    "revenue_growth": 0.35,
    "earnings_growth": 0.35,
    "eps_growth": 0.20,
    "forward_eps_growth": 0.10,
}

GROWTH_THRESHOLDS = {
    "revenue_growth": {
        "minimum": -0.10,
        "moderate": 0.00,
        "strong": 0.08,
        "excellent": 0.15,
    },
    "earnings_growth": {
        "minimum": -0.15,
        "moderate": 0.00,
        "strong": 0.10,
        "excellent": 0.20,
    },
    "eps_growth": {
        "minimum": -0.15,
        "moderate": 0.00,
        "strong": 0.10,
        "excellent": 0.20,
    },
    "forward_eps_growth": {
        "minimum": -0.10,
        "moderate": 0.00,
        "strong": 0.08,
        "excellent": 0.15,
    },
}


# =========================================================
# MOMENTUM SCORE
# =========================================================

MOMENTUM_WEIGHTS = {
    "return_6m": 0.20,
    "return_12m": 0.25,
    "above_50dma": 0.15,
    "above_200dma": 0.25,
    "distance_52w_high": 0.15,
}


# =========================================================
# VALUE-TRAP RISK
# =========================================================
# These weights define independent risk signals. The future value_engine.py
# will convert each signal to 0-100 risk, where a larger score means more
# evidence of a possible value trap.

VALUE_TRAP_WEIGHTS = {
    "negative_revenue_growth": 0.14,
    "negative_earnings_growth": 0.16,
    "negative_free_cash_flow": 0.16,
    "weak_profitability": 0.14,
    "high_net_debt": 0.14,
    "below_200dma": 0.10,
    "weak_12m_return": 0.08,
    "low_quality_score": 0.08,
}

VALUE_TRAP_THRESHOLDS = {
    "revenue_growth": {
        "low_risk": 0.05,
        "moderate_risk": 0.00,
        "high_risk": -0.10,
    },
    "earnings_growth": {
        "low_risk": 0.05,
        "moderate_risk": 0.00,
        "high_risk": -0.15,
    },
    "profit_margin": {
        "low_risk": 0.10,
        "moderate_risk": 0.04,
        "high_risk": 0.00,
    },
    "net_debt_to_market_cap": {
        "low_risk": 0.10,
        "moderate_risk": 0.30,
        "high_risk": 0.60,
    },
    "return_12m": {
        "low_risk": 0.05,
        "moderate_risk": -0.10,
        "high_risk": -0.30,
    },
}

VALUE_TRAP_RATINGS = {
    75: "High Value-Trap Risk",
    50: "Elevated Value-Trap Risk",
    25: "Moderate Value-Trap Risk",
    0: "Low Value-Trap Risk",
}


# =========================================================
# VALUE RATINGS
# =========================================================

RATING_THRESHOLDS = {
    85: "Exceptional Value",
    75: "Attractive Value",
    65: "Good Value",
    55: "Fair Value",
    45: "Watch",
    0: "Weak Value",
}

VALUATION_SCORE_RATINGS = {
    85: "Deep Value",
    75: "Attractive",
    60: "Reasonable",
    45: "Fair",
    0: "Expensive",
}


# =========================================================
# SCREENER DEFAULTS
# =========================================================

DEFAULT_FILTERS = {
    "minimum_overall_score": 60.0,
    "minimum_valuation_score": 60.0,
    "minimum_quality_score": 50.0,
    "maximum_value_trap_risk": 60.0,
    "minimum_market_cap": MIN_MARKET_CAP,
}


# =========================================================
# SECTOR COLORS
# =========================================================

SECTOR_COLORS = {
    "Communication Services": "#636EFA",
    "Consumer Discretionary": "#EF553B",
    "Consumer Defensive": "#00CC96",
    "Consumer Staples": "#00CC96",
    "Energy": "#AB63FA",
    "Financial Services": "#FFA15A",
    "Financials": "#FFA15A",
    "Healthcare": "#19D3F3",
    "Health Care": "#19D3F3",
    "Industrials": "#FF6692",
    "Basic Materials": "#B6E880",
    "Materials": "#B6E880",
    "Real Estate": "#FF97FF",
    "Technology": "#FECB52",
    "Utilities": "#2CA02C",
    "Unknown": "#9E9E9E",
}

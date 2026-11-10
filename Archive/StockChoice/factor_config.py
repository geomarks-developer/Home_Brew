"""
StockChoice Factor Definitions

All stock scoring is built from these factors.

Each factor should ultimately produce a score from:
0 - 100

The strategy engine combines these factor scores
using the weights defined in strategy_config.py.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Factor:
    key: str
    name: str
    icon: str
    description: str


# ============================================================
# FACTORS
# ============================================================

FACTORS = {

    # --------------------------------------------------------
    # Growth
    # --------------------------------------------------------
    "growth": Factor(
        key="growth",
        name="Growth",
        icon="📈",
        description="Revenue, earnings and cash flow growth."
    ),

    # --------------------------------------------------------
    # Quality
    # --------------------------------------------------------
    "quality": Factor(
        key="quality",
        name="Quality",
        icon="🛡️",
        description="Financial strength, profitability and efficiency."
    ),

    # --------------------------------------------------------
    # Value
    # --------------------------------------------------------
    "value": Factor(
        key="value",
        name="Value",
        icon="🏷️",
        description="Valuation attractiveness relative to fundamentals."
    ),

    # --------------------------------------------------------
    # Dividend
    # --------------------------------------------------------
    "dividend": Factor(
        key="dividend",
        name="Dividend",
        icon="💰",
        description="Income, dividend growth and sustainability."
    ),

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------
    "momentum": Factor(
        key="momentum",
        name="Momentum",
        icon="🚀",
        description="Price strength and trend confirmation."
    ),

    # --------------------------------------------------------
    # Risk
    # --------------------------------------------------------
    "risk": Factor(
        key="risk",
        name="Risk",
        icon="⚠️",
        description="Volatility, drawdown and financial risk."
    ),
}


# ============================================================
# FACTOR ORDER
# ============================================================

FACTOR_ORDER = [
    "growth",
    "quality",
    "value",
    "dividend",
    "momentum",
    "risk",
]


# ============================================================
# GROWTH METRICS
# ============================================================

GROWTH_METRICS = {
    "revenue_growth": 0.35,
    "earnings_growth": 0.35,
    "free_cash_flow_growth": 0.15,
    "forward_growth": 0.15,
}


# ============================================================
# QUALITY METRICS
# ============================================================

QUALITY_METRICS = {
    "return_on_equity": 0.25,
    "return_on_assets": 0.15,
    "profit_margin": 0.20,
    "operating_margin": 0.20,
    "financial_health": 0.20,
}


# ============================================================
# VALUE METRICS
# ============================================================

VALUE_METRICS = {
    "pe_ratio": 0.25,
    "forward_pe": 0.20,
    "peg_ratio": 0.25,
    "price_to_book": 0.05,
    "price_to_sales": 0.10,
    "free_cash_flow_yield": 0.15,
}


# ============================================================
# DIVIDEND METRICS
# ============================================================

DIVIDEND_METRICS = {
    "dividend_yield": 0.25,
    "dividend_growth": 0.30,
    "payout_ratio": 0.20,
    "years_of_growth": 0.25,
}
# ============================================================
# MOMENTUM METRICS
# ============================================================

MOMENTUM_METRICS = {
    "return_3m": 0.15,
    "return_6m": 0.20,
    "return_12m": 0.25,
    "relative_strength": 0.15,
    "ma200_strength": 0.15,
    "trend_status": 0.10,
}
# ============================================================
# RISK METRICS
# ============================================================

RISK_METRICS = {
    "beta": 0.20,
    "volatility": 0.20,
    "debt_to_equity": 0.20,
    "max_drawdown": 0.15,
    "distance_from_ma200": 0.25,
}


# ============================================================
# LOOKUPS
# ============================================================

FACTOR_METRICS = {
    "growth": GROWTH_METRICS,
    "quality": QUALITY_METRICS,
    "value": VALUE_METRICS,
    "dividend": DIVIDEND_METRICS,
    "momentum": MOMENTUM_METRICS,
    "risk": RISK_METRICS,
}


# ============================================================
# HELPERS
# ============================================================

def get_factor(factor_key: str) -> Factor:
    return FACTORS[factor_key]


def get_factor_metrics(factor_key: str) -> dict:
    return FACTOR_METRICS.get(factor_key, {})
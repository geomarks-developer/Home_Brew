"""
StockChoice Strategy Definitions

The strategy weights should always total 1.00 (100%).

Core Factors
------------
growth
quality
value
dividend
momentum
risk
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Strategy:
    key: str
    name: str
    icon: str
    description: str
    recommended: bool
    weights: dict[str, float]


# ============================================================
# STRATEGIES
# ============================================================

STRATEGIES = {

    # --------------------------------------------------------
    # GARP (Default / Flagship)
    # --------------------------------------------------------
    "garp": Strategy(
        key="garp",
        name="GARP",
        icon="💎",
        description="Growth at a Reasonable Price",
        recommended=True,
        weights={
            "growth": 0.30,
            "quality": 0.25,
            "value": 0.25,
            "momentum": 0.10,
            "risk": 0.10,
            "dividend": 0.00,
        }
    ),

    # --------------------------------------------------------
    # Core
    # --------------------------------------------------------
    "core": Strategy(
        key="core",
        name="Core",
        icon="⭐",
        description="Balanced multi-factor investing",
        recommended=False,
        weights={
            "growth": 0.20,
            "quality": 0.20,
            "value": 0.20,
            "dividend": 0.15,
            "momentum": 0.15,
            "risk": 0.10,
        }
    ),

    # --------------------------------------------------------
    # Dividend
    # --------------------------------------------------------
    "dividend": Strategy(
        key="dividend",
        name="Dividend",
        icon="💰",
        description="Income and dividend growth",
        recommended=False,
        weights={
            "growth": 0.00,
            "quality": 0.25,
            "value": 0.15,
            "dividend": 0.40,
            "momentum": 0.10,
            "risk": 0.10,
        }
    ),

    # --------------------------------------------------------
    # Value
    # --------------------------------------------------------
    "value": Strategy(
        key="value",
        name="Value",
        icon="🏷️",
        description="Undervalued quality companies",
        recommended=False,
        weights={
            "growth": 0.00,
            "quality": 0.25,
            "value": 0.40,
            "dividend": 0.10,
            "momentum": 0.10,
            "risk": 0.15,
        }
    ),

    # --------------------------------------------------------
    # Growth
    # --------------------------------------------------------
    "growth": Strategy(
        key="growth",
        name="Growth",
        icon="📈",
        description="Fast-growing businesses",
        recommended=False,
        weights={
            "growth": 0.40,
            "quality": 0.20,
            "value": 0.10,
            "dividend": 0.00,
            "momentum": 0.20,
            "risk": 0.10,
        }
    ),

    # --------------------------------------------------------
    # Momentum
    # --------------------------------------------------------
    "momentum": Strategy(
        key="momentum",
        name="Momentum",
        icon="🚀",
        description="Market leadership and trend strength",
        recommended=False,
        weights={
            "growth": 0.20,
            "quality": 0.15,
            "value": 0.00,
            "dividend": 0.00,
            "momentum": 0.50,
            "risk": 0.15,
        }
    ),

    # --------------------------------------------------------
    # Quality
    # --------------------------------------------------------
    "quality": Strategy(
        key="quality",
        name="Quality",
        icon="🛡️",
        description="Financial strength and consistency",
        recommended=False,
        weights={
            "growth": 0.15,
            "quality": 0.50,
            "value": 0.15,
            "dividend": 0.00,
            "momentum": 0.00,
            "risk": 0.20,
        }
    ),
}


# ============================================================
# DEFAULTS
# ============================================================

DEFAULT_STRATEGY = "garp"

STRATEGY_ORDER = [
    "garp",
    "core",
    "dividend",
    "value",
    "growth",
    "momentum",
    "quality",
]


# ============================================================
# HELPERS
# ============================================================

def get_strategy(strategy_key: str) -> Strategy:
    return STRATEGIES.get(
        strategy_key,
        STRATEGIES[DEFAULT_STRATEGY]
    )


def get_strategy_names() -> list[str]:
    return [
        STRATEGIES[key].name
        for key in STRATEGY_ORDER
    ]
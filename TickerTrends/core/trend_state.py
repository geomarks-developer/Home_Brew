"""
TickerTrends Trend State Engine
===============================

Converts TickerTrends technical indicators into one
easy-to-understand trend state.

States:

    Strong Bullish
    Bullish
    Accumulation
    Extended
    Weakening
    Bearish

Core philosophy:

    200-day SMA = long-term regime
    50-day SMA  = intermediate trend
    RSI-14      = current condition

TickerTrends is designed as a trend-aware investment
screener, not a short-term trading system.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


# ============================================================
# TREND STATE NAMES
# ============================================================

STRONG_BULLISH = "Strong Bullish"
BULLISH = "Bullish"
ACCUMULATION = "Accumulation"
EXTENDED = "Extended"
WEAKENING = "Weakening"
BEARISH = "Bearish"


TREND_STATES = [
    STRONG_BULLISH,
    BULLISH,
    ACCUMULATION,
    EXTENDED,
    WEAKENING,
    BEARISH,
]


# ============================================================
# THRESHOLDS
# ============================================================

# RSI
RSI_OVERSOLD = 30.0
RSI_WEAK = 40.0
RSI_NEUTRAL = 50.0
RSI_STRONG = 55.0
RSI_EXTENDED = 70.0


# Price distance from 50D SMA
#
# A stock within roughly +/- 3% of its 50-day average can be
# treated as being "near" the intermediate trend.
NEAR_SMA50_PCT = 3.0


# Price distance from 200D SMA
#
# A bullish-regime stock approaching its 200-day average
# deserves more caution.
NEAR_SMA200_PCT = 3.0


# Extension thresholds
#
# These are intentionally conservative starting values.
# We can adjust them after examining real stocks.
EXTENDED_FROM_SMA50_PCT = 10.0


# 200-day slope
#
# technicals.py measures this as the percentage change
# in the 200D SMA across the previous 20 trading observations.
SLOPE_RISING = 0.25
SLOPE_FALLING = -0.25


# ============================================================
# DISPLAY INFORMATION
# ============================================================

TREND_DISPLAY = {

    STRONG_BULLISH: {
        "icon": "🟢",
        "color": "green",
        "label": "Strong Bullish",
        "description": (
            "Strong long-term and intermediate "
            "uptrend with healthy momentum."
        ),
    },

    BULLISH: {
        "icon": "🟢",
        "color": "green",
        "label": "Bullish",
        "description": (
            "Long-term trend remains favorable."
        ),
    },

    ACCUMULATION: {
        "icon": "🔵",
        "color": "blue",
        "label": "Accumulation",
        "description": (
            "Long-term bullish trend remains intact "
            "while price or momentum has cooled."
        ),
    },

    EXTENDED: {
        "icon": "🟡",
        "color": "yellow",
        "label": "Extended",
        "description": (
            "Trend remains bullish, but price or momentum "
            "appears stretched."
        ),
    },

    WEAKENING: {
        "icon": "🟠",
        "color": "orange",
        "label": "Weakening",
        "description": (
            "Long-term trend has not completely broken, "
            "but technical conditions are deteriorating."
        ),
    },

    BEARISH: {
        "icon": "🔴",
        "color": "red",
        "label": "Bearish",
        "description": (
            "Price is below the 200-day moving average."
        ),
    },
}


# ============================================================
# RESULT MODEL
# ============================================================

@dataclass
class TrendStateResult:
    """
    Full result returned by the trend-state engine.
    """

    state: str
    reason: str

    price_above_50: bool
    price_above_200: bool
    sma50_above_200: bool

    sma200_rising: bool
    sma200_falling: bool

    rsi: float | None

    pct_from_sma50: float | None
    pct_from_sma200: float | None

    @property
    def icon(self) -> str:
        return TREND_DISPLAY[self.state]["icon"]

    @property
    def label(self) -> str:
        return TREND_DISPLAY[self.state]["label"]

    @property
    def display(self) -> str:
        return f"{self.icon} {self.label}"

    @property
    def description(self) -> str:
        return TREND_DISPLAY[self.state]["description"]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert result into a dictionary for Streamlit,
        scoring, database storage, or DataFrames.
        """

        return {
            "trend_state": self.state,
            "trend_display": self.display,
            "trend_reason": self.reason,
            "price_above_50": self.price_above_50,
            "price_above_200": self.price_above_200,
            "sma50_above_200": self.sma50_above_200,
            "sma200_rising": self.sma200_rising,
            "sma200_falling": self.sma200_falling,
            "rsi_14": self.rsi,
            "pct_from_sma50": self.pct_from_sma50,
            "pct_from_sma200": self.pct_from_sma200,
        }


# ============================================================
# SAFE VALUES
# ============================================================

def is_valid_number(value: Any) -> bool:
    """
    Return True when value can safely be treated as a number.
    """

    if value is None:
        return False

    try:
        number = float(value)
    except (TypeError, ValueError):
        return False

    return number == number


# ============================================================
# CONDITION HELPERS
# ============================================================

def is_extended(
    *,
    rsi: float | None,
    pct_from_sma50: float | None,
    pct_from_sma200: float | None,
) -> bool:
    """
    Determine whether a bullish stock appears stretched.

    Extended is based primarily on current/intermediate
    conditions:

        - RSI >= 70
        - Price >= 10% above the 50-day SMA

    Distance above the 200-day SMA remains useful context,
    but does not trigger Extended by itself.
    """

    if (
        rsi is not None
        and rsi >= RSI_EXTENDED
    ):
        return True

    if (
        pct_from_sma50 is not None
        and pct_from_sma50 >= EXTENDED_FROM_SMA50_PCT
    ):
        return True

    return False


def is_accumulation_setup(
    *,
    price_above_200: bool,
    sma50_above_200: bool,
    sma200_rising: bool,
    rsi: float | None,
    pct_from_sma50: float | None,
) -> bool:
    """
    Identify a constructive pullback inside a bullish
    long-term trend.

    This is one of the most important TickerTrends states.

    We want:

        - price still above the 200D
        - 50D still above the 200D
        - 200D still rising
        - momentum cooled
        - price relatively close to the 50D
    """

    if not price_above_200:
        return False

    if not sma50_above_200:
        return False

    if not sma200_rising:
        return False

    if rsi is None:
        return False

    if pct_from_sma50 is None:
        return False

    healthy_pullback = (
        RSI_WEAK <= rsi <= RSI_STRONG
    )

    near_50_day = (
        abs(pct_from_sma50)
        <= NEAR_SMA50_PCT
    )

    return (
        healthy_pullback
        and near_50_day
    )


# ============================================================
# TREND STATE ENGINE
# ============================================================

def determine_trend_state(
    technicals: dict[str, Any],
) -> TrendStateResult | None:
    """
    Determine the TickerTrends state from a technical snapshot.

    Expected technical dictionary fields:

        price
        sma_50
        sma_200
        sma_200_slope
        pct_from_sma50
        pct_from_sma200
        rsi_14
    """

    price = technicals.get("price")
    sma_50 = technicals.get("sma_50")
    sma_200 = technicals.get("sma_200")

    if not (
        is_valid_number(price)
        and is_valid_number(sma_50)
        and is_valid_number(sma_200)
    ):
        return None

    price = float(price)
    sma_50 = float(sma_50)
    sma_200 = float(sma_200)

    slope_raw = technicals.get(
        "sma_200_slope"
    )

    rsi_raw = technicals.get(
        "rsi_14"
    )

    pct_50_raw = technicals.get(
        "pct_from_sma50"
    )

    pct_200_raw = technicals.get(
        "pct_from_sma200"
    )

    slope = (
        float(slope_raw)
        if is_valid_number(slope_raw)
        else None
    )

    rsi = (
        float(rsi_raw)
        if is_valid_number(rsi_raw)
        else None
    )

    pct_from_sma50 = (
        float(pct_50_raw)
        if is_valid_number(pct_50_raw)
        else None
    )

    pct_from_sma200 = (
        float(pct_200_raw)
        if is_valid_number(pct_200_raw)
        else None
    )

    # --------------------------------------------------------
    # CORE CONDITIONS
    # --------------------------------------------------------

    price_above_50 = (
        price >= sma_50
    )

    price_above_200 = (
        price >= sma_200
    )

    sma50_above_200 = (
        sma_50 >= sma_200
    )

    sma200_rising = (
        slope is not None
        and slope >= SLOPE_RISING
    )

    sma200_falling = (
        slope is not None
        and slope <= SLOPE_FALLING
    )

    # --------------------------------------------------------
    # 1. BEARISH
    # --------------------------------------------------------
    #
    # The 200-day average is the foundation of the model.
    #
    # Once price is below it, the stock enters the Bearish
    # long-term regime.
    # --------------------------------------------------------

    if not price_above_200:

        reason = (
            "Price is below the 200-day moving average."
        )

        if sma200_falling:
            reason += (
                " The 200-day moving average is also falling."
            )

        return TrendStateResult(
            state=BEARISH,
            reason=reason,
            price_above_50=price_above_50,
            price_above_200=price_above_200,
            sma50_above_200=sma50_above_200,
            sma200_rising=sma200_rising,
            sma200_falling=sma200_falling,
            rsi=rsi,
            pct_from_sma50=pct_from_sma50,
            pct_from_sma200=pct_from_sma200,
        )

    # --------------------------------------------------------
    # 2. EXTENDED
    # --------------------------------------------------------
    #
    # The trend remains bullish, but the stock may have moved
    # far enough or fast enough that chasing it is less
    # attractive.
    # --------------------------------------------------------

    if is_extended(
        rsi=rsi,
        pct_from_sma50=pct_from_sma50,
        pct_from_sma200=pct_from_sma200,
    ):

        reasons: list[str] = []

        if (
            rsi is not None
            and rsi >= RSI_EXTENDED
        ):
            reasons.append(
                f"RSI is elevated at {rsi:.1f}"
            )

        if (
            pct_from_sma50 is not None
            and pct_from_sma50
            >= EXTENDED_FROM_SMA50_PCT
        ):
            reasons.append(
                "price is well above the 50-day average"
            )


        reason = "; ".join(reasons)

        if reason:
            reason = reason[0].upper() + reason[1:] + "."

        else:
            reason = (
                "The stock appears extended within its "
                "bullish trend."
            )

        return TrendStateResult(
            state=EXTENDED,
            reason=reason,
            price_above_50=price_above_50,
            price_above_200=price_above_200,
            sma50_above_200=sma50_above_200,
            sma200_rising=sma200_rising,
            sma200_falling=sma200_falling,
            rsi=rsi,
            pct_from_sma50=pct_from_sma50,
            pct_from_sma200=pct_from_sma200,
        )

    # --------------------------------------------------------
    # 3. ACCUMULATION
    # --------------------------------------------------------
    #
    # This represents the constructive-pullback condition
    # we discussed.
    # --------------------------------------------------------

    if is_accumulation_setup(
        price_above_200=price_above_200,
        sma50_above_200=sma50_above_200,
        sma200_rising=sma200_rising,
        rsi=rsi,
        pct_from_sma50=pct_from_sma50,
    ):

        return TrendStateResult(
            state=ACCUMULATION,
            reason=(
                "The long-term uptrend remains intact while "
                "price is near the 50-day average and RSI "
                "has cooled."
            ),
            price_above_50=price_above_50,
            price_above_200=price_above_200,
            sma50_above_200=sma50_above_200,
            sma200_rising=sma200_rising,
            sma200_falling=sma200_falling,
            rsi=rsi,
            pct_from_sma50=pct_from_sma50,
            pct_from_sma200=pct_from_sma200,
        )

    # --------------------------------------------------------
    # 4. WEAKENING
    # --------------------------------------------------------
    #
    # Still above the 200D, but one or more intermediate
    # conditions are deteriorating.
    # --------------------------------------------------------

    near_200 = (
        pct_from_sma200 is not None
        and 0 <= pct_from_sma200 <= NEAR_SMA200_PCT
    )

    weak_rsi = (
        rsi is not None
        and rsi < RSI_WEAK
    )

    if (
        not price_above_50
        or not sma50_above_200
        or sma200_falling
        or weak_rsi
        or near_200
    ):

        reasons: list[str] = []

        if not price_above_50:
            reasons.append(
                "price is below the 50-day average"
            )

        if not sma50_above_200:
            reasons.append(
                "the 50-day average is below the 200-day average"
            )

        if sma200_falling:
            reasons.append(
                "the 200-day average is falling"
            )

        if weak_rsi:
            reasons.append(
                f"RSI has weakened to {rsi:.1f}"
            )

        if near_200:
            reasons.append(
                "price is approaching the 200-day average"
            )

        reason = "; ".join(reasons)

        if reason:
            reason = reason[0].upper() + reason[1:] + "."

        else:
            reason = (
                "Technical conditions are weakening."
            )

        return TrendStateResult(
            state=WEAKENING,
            reason=reason,
            price_above_50=price_above_50,
            price_above_200=price_above_200,
            sma50_above_200=sma50_above_200,
            sma200_rising=sma200_rising,
            sma200_falling=sma200_falling,
            rsi=rsi,
            pct_from_sma50=pct_from_sma50,
            pct_from_sma200=pct_from_sma200,
        )

    # --------------------------------------------------------
    # 5. STRONG BULLISH
    # --------------------------------------------------------

    strong_rsi = (
        rsi is not None
        and RSI_STRONG <= rsi < RSI_EXTENDED
    )

    if (
        price_above_50
        and price_above_200
        and sma50_above_200
        and sma200_rising
        and strong_rsi
    ):

        return TrendStateResult(
            state=STRONG_BULLISH,
            reason=(
                "Price is above both moving averages, the "
                "50-day average is above the 200-day average, "
                "the 200-day trend is rising, and momentum "
                "is strong without being extended."
            ),
            price_above_50=price_above_50,
            price_above_200=price_above_200,
            sma50_above_200=sma50_above_200,
            sma200_rising=sma200_rising,
            sma200_falling=sma200_falling,
            rsi=rsi,
            pct_from_sma50=pct_from_sma50,
            pct_from_sma200=pct_from_sma200,
        )

    # --------------------------------------------------------
    # 6. BULLISH
    # --------------------------------------------------------
    #
    # Default condition for a stock remaining above its 200D
    # without meeting one of the more specific classifications.
    # --------------------------------------------------------

    return TrendStateResult(
        state=BULLISH,
        reason=(
            "Price remains above the 200-day moving average "
            "and the long-term bullish regime remains intact."
        ),
        price_above_50=price_above_50,
        price_above_200=price_above_200,
        sma50_above_200=sma50_above_200,
        sma200_rising=sma200_rising,
        sma200_falling=sma200_falling,
        rsi=rsi,
        pct_from_sma50=pct_from_sma50,
        pct_from_sma200=pct_from_sma200,
    )


# ============================================================
# DISPLAY HELPERS
# ============================================================

def get_state_icon(
    state: str,
) -> str:
    """
    Return the display icon for a trend state.
    """

    info = TREND_DISPLAY.get(state)

    if info is None:
        return "⚪"

    return info["icon"]


def get_state_description(
    state: str,
) -> str:
    """
    Return the short description for a trend state.
    """

    info = TREND_DISPLAY.get(state)

    if info is None:
        return "Unknown trend state."

    return info["description"]


def format_state(
    state: str,
) -> str:
    """
    Format a state for compact Streamlit display.

    Example:

        🟢 Strong Bullish
    """

    return (
        f"{get_state_icon(state)} {state}"
    )


# ============================================================
# TEST SCENARIOS
# ============================================================

def run_test_scenarios() -> None:
    """
    Run several synthetic scenarios through the state engine.

    This lets us verify the classification logic without
    downloading market data.
    """

    scenarios = {

        "Strong Bullish": {
            "price": 110,
            "sma_50": 105,
            "sma_200": 95,
            "sma_200_slope": 2.0,
            "pct_from_sma50": 4.76,
            "pct_from_sma200": 15.79,
            "rsi_14": 62,
        },

        "Accumulation": {
            "price": 102,
            "sma_50": 100,
            "sma_200": 90,
            "sma_200_slope": 1.5,
            "pct_from_sma50": 2.0,
            "pct_from_sma200": 13.33,
            "rsi_14": 47,
        },

        "Extended": {
            "price": 125,
            "sma_50": 110,
            "sma_200": 100,
            "sma_200_slope": 2.0,
            "pct_from_sma50": 13.64,
            "pct_from_sma200": 25.0,
            "rsi_14": 74,
        },

        "Weakening": {
            "price": 101,
            "sma_50": 103,
            "sma_200": 100,
            "sma_200_slope": 0.5,
            "pct_from_sma50": -1.94,
            "pct_from_sma200": 1.0,
            "rsi_14": 39,
        },

        "Bearish": {
            "price": 94,
            "sma_50": 98,
            "sma_200": 100,
            "sma_200_slope": -1.2,
            "pct_from_sma50": -4.08,
            "pct_from_sma200": -6.0,
            "rsi_14": 36,
        },
    }

    print()
    print("TickerTrends Trend State Tests")
    print("==============================")

    for expected, technicals in scenarios.items():

        result = determine_trend_state(
            technicals
        )

        if result is None:
            actual = "ERROR"
            passed = False

        else:
            actual = result.state
            passed = (
                actual == expected
            )

        status = (
            "PASS"
            if passed
            else "FAIL"
        )

        print(
            f"{status:4} | "
            f"Expected: {expected:15} | "
            f"Actual: {actual}"
        )

    print()


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":
    run_test_scenarios()
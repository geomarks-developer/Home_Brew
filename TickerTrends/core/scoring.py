"""
TickerTrends Scoring Engine
===========================

Calculates the 100-point TickerTrends score.

Technical Score:   60 points
Fundamental Score: 40 points
Total Score:      100 points

Technical Components
--------------------

    Price vs 200-day SMA       20 points
    200-day SMA slope          10 points
    Price vs 50-day SMA        10 points
    50-day vs 200-day SMA      10 points
    RSI-14                     10 points

Fundamental Components
----------------------

    P/E ratio                  10 points
    PEG ratio                  10 points
    Free cash flow margin      10 points
    Relative performance       10 points

Missing fundamental values are not automatically treated as
poor values. TickerTrends calculates:

    raw score
    available points
    coverage percentage
    adjusted score

The displayed total score uses the adjusted component scores
when sufficient data is available.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from core.fundamentals import get_fundamentals
from core.technicals import get_technicals
from core.trend_state import (
    TrendStateResult,
    determine_trend_state,
)


# ============================================================
# MODEL POINTS
# ============================================================

TECHNICAL_MAX = 60.0
FUNDAMENTAL_MAX = 40.0
TOTAL_MAX = 100.0

PRICE_VS_200_MAX = 20.0
SMA200_SLOPE_MAX = 10.0
PRICE_VS_50_MAX = 10.0
SMA50_VS_200_MAX = 10.0
RSI_MAX = 10.0

PE_MAX = 10.0
PEG_MAX = 10.0
FCF_MARGIN_MAX = 10.0
RELATIVE_PERFORMANCE_MAX = 10.0


# ============================================================
# MINIMUM COVERAGE
# ============================================================

# At least three of the four fundamental metrics should be
# available before the adjusted fundamental score is used.
MIN_FUNDAMENTAL_COVERAGE = 75.0


# ============================================================
# RESULT MODELS
# ============================================================

@dataclass
class ScoreComponent:
    """
    Result for one scoring component.
    """

    name: str
    value: float | None
    points: float | None
    max_points: float
    label: str
    reason: str
    available: bool = True

    def to_dict(self) -> dict[str, Any]:
        """
        Convert one score component into a dictionary.
        """

        return {
            "name": self.name,
            "value": self.value,
            "points": self.points,
            "max_points": self.max_points,
            "label": self.label,
            "reason": self.reason,
            "available": self.available,
        }


@dataclass
class ScoreSummary:
    """
    Complete TickerTrends scoring result.
    """

    ticker: str

    technical_raw_score: float
    technical_available_points: float
    technical_score: float
    technical_coverage: float

    fundamental_raw_score: float
    fundamental_available_points: float
    fundamental_score: float | None
    fundamental_coverage: float

    total_score: float | None
    score_grade: str
    score_label: str

    trend_state: str | None
    trend_display: str | None
    trend_reason: str | None

    technical_components: list[ScoreComponent]
    fundamental_components: list[ScoreComponent]

    def to_dict(self) -> dict[str, Any]:
        """
        Convert the scoring result into one dictionary.
        """

        return {
            "ticker": self.ticker,

            "technical_raw_score": (
                self.technical_raw_score
            ),

            "technical_available_points": (
                self.technical_available_points
            ),

            "technical_score": (
                self.technical_score
            ),

            "technical_coverage": (
                self.technical_coverage
            ),

            "fundamental_raw_score": (
                self.fundamental_raw_score
            ),

            "fundamental_available_points": (
                self.fundamental_available_points
            ),

            "fundamental_score": (
                self.fundamental_score
            ),

            "fundamental_coverage": (
                self.fundamental_coverage
            ),

            "total_score": (
                self.total_score
            ),

            "score_grade": (
                self.score_grade
            ),

            "score_label": (
                self.score_label
            ),

            "trend_state": (
                self.trend_state
            ),

            "trend_display": (
                self.trend_display
            ),

            "trend_reason": (
                self.trend_reason
            ),

            "technical_components": [
                component.to_dict()
                for component
                in self.technical_components
            ],

            "fundamental_components": [
                component.to_dict()
                for component
                in self.fundamental_components
            ],
        }


# ============================================================
# SAFE NUMBER HELPERS
# ============================================================

def safe_float(
    value: Any,
) -> float | None:
    """
    Convert a value into a finite float.
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


def clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    """
    Limit a numeric value to a specified range.
    """

    return max(
        minimum,
        min(value, maximum),
    )


def round_score(
    value: float,
) -> float:
    """
    Round displayed scores consistently.
    """

    return round(value, 1)


# ============================================================
# COMPONENT HELPERS
# ============================================================

def unavailable_component(
    name: str,
    max_points: float,
    reason: str,
) -> ScoreComponent:
    """
    Create a component for missing data.
    """

    return ScoreComponent(
        name=name,
        value=None,
        points=None,
        max_points=max_points,
        label="Unavailable",
        reason=reason,
        available=False,
    )


def calculate_coverage(
    components: list[ScoreComponent],
) -> tuple[float, float]:
    """
    Return:

        available points
        coverage percentage
    """

    maximum = sum(
        component.max_points
        for component in components
    )

    available = sum(
        component.max_points
        for component in components
        if component.available
    )

    if maximum <= 0:
        return 0.0, 0.0

    coverage = (
        available / maximum
    ) * 100

    return (
        round_score(available),
        round_score(coverage),
    )


def sum_component_points(
    components: list[ScoreComponent],
) -> float:
    """
    Sum the available component points.
    """

    total = sum(
        component.points or 0.0
        for component in components
    )

    return round_score(total)


def normalize_score(
    raw_score: float,
    available_points: float,
    target_points: float,
) -> float | None:
    """
    Normalize a partial score to its intended target scale.

    Example:

        Raw score:       22
        Available:       30
        Target scale:    40

        Adjusted score:
            22 / 30 * 40 = 29.3
    """

    if available_points <= 0:
        return None

    score = (
        raw_score
        / available_points
    ) * target_points

    return round_score(
        clamp(
            score,
            0.0,
            target_points,
        )
    )


# ============================================================
# TECHNICAL: PRICE VS 200D
# ============================================================

def score_price_vs_200(
    technicals: dict[str, Any],
) -> ScoreComponent:
    """
    Score price relative to the 200-day SMA.

    Maximum: 20 points

        At or above 200D: 20
        0% to 3% below:   12
        3% to 7% below:    6
        More than 7%:      0
    """

    value = safe_float(
        technicals.get("pct_from_sma200")
    )

    if value is None:
        return unavailable_component(
            "Price vs 200D",
            PRICE_VS_200_MAX,
            "Distance from the 200-day average is unavailable.",
        )

    if value >= 0:
        points = 20.0
        label = "Bullish"
        reason = "Price is at or above the 200-day average."

    elif value >= -3:
        points = 12.0
        label = "Near 200D"
        reason = (
            "Price is slightly below the 200-day average."
        )

    elif value >= -7:
        points = 6.0
        label = "Below 200D"
        reason = (
            "Price is moderately below the 200-day average."
        )

    else:
        points = 0.0
        label = "Bearish"
        reason = (
            "Price is substantially below the 200-day average."
        )

    return ScoreComponent(
        name="Price vs 200D",
        value=value,
        points=points,
        max_points=PRICE_VS_200_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# TECHNICAL: 200D SLOPE
# ============================================================

def score_sma200_slope(
    technicals: dict[str, Any],
) -> ScoreComponent:
    """
    Score the direction of the 200-day SMA.

    technicals.py calculates the percentage change in the
    200-day SMA over the previous 20 trading observations.

    Maximum: 10 points

        >= +1.00%: 10
        +0.25 to 1%: 8
        0 to +0.25%: 6
        -0.25 to 0%: 4
        -1 to -0.25%: 2
        Below -1%: 0
    """

    value = safe_float(
        technicals.get("sma_200_slope")
    )

    if value is None:
        return unavailable_component(
            "200D Slope",
            SMA200_SLOPE_MAX,
            "The 200-day slope is unavailable.",
        )

    if value >= 1.0:
        points = 10.0
        label = "Strongly Rising"

    elif value >= 0.25:
        points = 8.0
        label = "Rising"

    elif value >= 0:
        points = 6.0
        label = "Slightly Rising"

    elif value > -0.25:
        points = 4.0
        label = "Flat"

    elif value > -1.0:
        points = 2.0
        label = "Falling"

    else:
        points = 0.0
        label = "Strongly Falling"

    reason = (
        f"The 200-day average changed "
        f"{value:+.2f}% over the slope lookback."
    )

    return ScoreComponent(
        name="200D Slope",
        value=value,
        points=points,
        max_points=SMA200_SLOPE_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# TECHNICAL: PRICE VS 50D
# ============================================================

def score_price_vs_50(
    technicals: dict[str, Any],
) -> ScoreComponent:
    """
    Score price relative to the 50-day SMA.

    Maximum: 10 points

        0% through +10%:    10
        +10% through +15%:   7
        Above +15%:          4
        0% through -3%:      7
        -3% through -7%:     4
        Below -7%:           0

    This gives full credit to a healthy bullish position
    without rewarding extreme extension.
    """

    value = safe_float(
        technicals.get("pct_from_sma50")
    )

    if value is None:
        return unavailable_component(
            "Price vs 50D",
            PRICE_VS_50_MAX,
            "Distance from the 50-day average is unavailable.",
        )

    if 0 <= value <= 10:
        points = 10.0
        label = "Healthy"

    elif 10 < value <= 15:
        points = 7.0
        label = "Elevated"

    elif value > 15:
        points = 4.0
        label = "Extended"

    elif -3 <= value < 0:
        points = 7.0
        label = "Near 50D"

    elif -7 <= value < -3:
        points = 4.0
        label = "Below 50D"

    else:
        points = 0.0
        label = "Weak"

    reason = (
        f"Price is {value:+.2f}% from the 50-day average."
    )

    return ScoreComponent(
        name="Price vs 50D",
        value=value,
        points=points,
        max_points=PRICE_VS_50_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# TECHNICAL: 50D VS 200D
# ============================================================

def score_sma50_vs_200(
    technicals: dict[str, Any],
) -> ScoreComponent:
    """
    Score the relationship between the 50-day and
    200-day moving averages.

    Maximum: 10 points
    """

    sma_50 = safe_float(
        technicals.get("sma_50")
    )

    sma_200 = safe_float(
        technicals.get("sma_200")
    )

    if sma_50 is None or sma_200 is None:
        return unavailable_component(
            "50D vs 200D",
            SMA50_VS_200_MAX,
            "One or both moving averages are unavailable.",
        )

    if sma_200 == 0:
        return unavailable_component(
            "50D vs 200D",
            SMA50_VS_200_MAX,
            "The 200-day average is invalid.",
        )

    spread = (
        (sma_50 / sma_200) - 1
    ) * 100

    if spread >= 5:
        points = 10.0
        label = "Strong Bullish Alignment"

    elif spread >= 0:
        points = 8.0
        label = "Bullish Alignment"

    elif spread >= -3:
        points = 4.0
        label = "Near Crossover"

    else:
        points = 0.0
        label = "Bearish Alignment"

    reason = (
        f"The 50-day average is {spread:+.2f}% "
        f"from the 200-day average."
    )

    return ScoreComponent(
        name="50D vs 200D",
        value=spread,
        points=points,
        max_points=SMA50_VS_200_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# TECHNICAL: RSI
# ============================================================

def score_rsi(
    technicals: dict[str, Any],
) -> ScoreComponent:
    """
    Score RSI condition.

    Maximum: 10 points

        50 through 69.99: 10
        40 through 49.99:  8
        30 through 39.99:  4
        70 through 79.99:  6
        80 and above:      2
        Below 30:          0

    Healthy positive momentum gets full credit.
    Extended or deeply weak conditions receive less credit.
    """

    value = safe_float(
        technicals.get("rsi_14")
    )

    if value is None:
        return unavailable_component(
            "RSI-14",
            RSI_MAX,
            "RSI-14 is unavailable.",
        )

    if 50 <= value < 70:
        points = 10.0
        label = "Healthy Momentum"

    elif 40 <= value < 50:
        points = 8.0
        label = "Cooled"

    elif 30 <= value < 40:
        points = 4.0
        label = "Weak"

    elif 70 <= value < 80:
        points = 6.0
        label = "Extended"

    elif value >= 80:
        points = 2.0
        label = "Highly Extended"

    else:
        points = 0.0
        label = "Oversold"

    reason = (
        f"RSI-14 is {value:.1f}."
    )

    return ScoreComponent(
        name="RSI-14",
        value=value,
        points=points,
        max_points=RSI_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# FUNDAMENTAL: P/E
# ============================================================

def score_pe(
    fundamentals: dict[str, Any],
) -> ScoreComponent:
    """
    Score positive P/E ratio.

    Maximum: 10 points

        <= 15:       10
        15 to 20:     9
        20 to 25:     8
        25 to 30:     7
        30 to 40:     5
        40 to 50:     3
        Above 50:     1

    Missing or non-positive P/E is treated as unavailable.
    """

    value = safe_float(
        fundamentals.get("pe_ratio")
    )

    if value is None or value <= 0:
        return unavailable_component(
            "P/E",
            PE_MAX,
            "A positive P/E ratio is unavailable.",
        )

    if value <= 15:
        points = 10.0
        label = "Very Attractive"

    elif value <= 20:
        points = 9.0
        label = "Attractive"

    elif value <= 25:
        points = 8.0
        label = "Reasonable"

    elif value <= 30:
        points = 7.0
        label = "Moderate"

    elif value <= 40:
        points = 5.0
        label = "Elevated"

    elif value <= 50:
        points = 3.0
        label = "High"

    else:
        points = 1.0
        label = "Very High"

    source = (
        fundamentals.get("pe_source")
        or "P/E"
    )

    reason = (
        f"{source} P/E is {value:.2f}."
    )

    return ScoreComponent(
        name="P/E",
        value=value,
        points=points,
        max_points=PE_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# FUNDAMENTAL: PEG
# ============================================================

def score_peg(
    fundamentals: dict[str, Any],
) -> ScoreComponent:
    """
    Score positive PEG ratio.

    Maximum: 10 points

        <= 1.00:      10
        1.00 to 1.50:  8
        1.50 to 2.00:  6
        2.00 to 2.50:  4
        2.50 to 3.00:  2
        Above 3.00:     1
    """

    value = safe_float(
        fundamentals.get("peg_ratio")
    )

    if value is None or value <= 0:
        return unavailable_component(
            "PEG",
            PEG_MAX,
            "A positive PEG ratio is unavailable.",
        )

    if value <= 1.0:
        points = 10.0
        label = "Attractive"

    elif value <= 1.5:
        points = 8.0
        label = "Reasonable"

    elif value <= 2.0:
        points = 6.0
        label = "Moderate"

    elif value <= 2.5:
        points = 4.0
        label = "Elevated"

    elif value <= 3.0:
        points = 2.0
        label = "High"

    else:
        points = 1.0
        label = "Very High"

    reason = (
        f"PEG ratio is {value:.2f}."
    )

    return ScoreComponent(
        name="PEG",
        value=value,
        points=points,
        max_points=PEG_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# FUNDAMENTAL: FCF MARGIN
# ============================================================

def score_fcf_margin(
    fundamentals: dict[str, Any],
) -> ScoreComponent:
    """
    Score free cash flow margin.

    Maximum: 10 points

        >= 20%:      10
        15% to 20%:   9
        10% to 15%:   8
        5% to 10%:    6
        0% to 5%:     3
        Below 0%:     0
    """

    value = safe_float(
        fundamentals.get("fcf_margin")
    )

    if value is None:
        return unavailable_component(
            "FCF Margin",
            FCF_MARGIN_MAX,
            "Free cash flow margin is unavailable.",
        )

    if value >= 20:
        points = 10.0
        label = "Excellent"

    elif value >= 15:
        points = 9.0
        label = "Strong"

    elif value >= 10:
        points = 8.0
        label = "Good"

    elif value >= 5:
        points = 6.0
        label = "Positive"

    elif value >= 0:
        points = 3.0
        label = "Low"

    else:
        points = 0.0
        label = "Negative"

    reason = (
        f"Free cash flow margin is {value:+.2f}%."
    )

    return ScoreComponent(
        name="FCF Margin",
        value=value,
        points=points,
        max_points=FCF_MARGIN_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# FUNDAMENTAL: RELATIVE PERFORMANCE
# ============================================================

def score_relative_performance(
    fundamentals: dict[str, Any],
) -> ScoreComponent:
    """
    Score six-month relative performance vs the S&P 500.

    Maximum: 10 points

        >= +15%:       10
        +5% to +15%:    8
        0% to +5%:      6
        -5% to 0%:      4
        -15% to -5%:    2
        Below -15%:     0
    """

    value = safe_float(
        fundamentals.get("relative_performance")
    )

    if value is None:
        return unavailable_component(
            "Relative Performance",
            RELATIVE_PERFORMANCE_MAX,
            "Six-month relative performance is unavailable.",
        )

    if value >= 15:
        points = 10.0
        label = "Strong Outperformance"

    elif value >= 5:
        points = 8.0
        label = "Outperforming"

    elif value >= 0:
        points = 6.0
        label = "Slightly Outperforming"

    elif value >= -5:
        points = 4.0
        label = "Slightly Underperforming"

    elif value >= -15:
        points = 2.0
        label = "Underperforming"

    else:
        points = 0.0
        label = "Weak Performance"

    reason = (
        f"Six-month relative performance is {value:+.2f}%."
    )

    return ScoreComponent(
        name="Relative Performance",
        value=value,
        points=points,
        max_points=RELATIVE_PERFORMANCE_MAX,
        label=label,
        reason=reason,
    )


# ============================================================
# TECHNICAL SCORE
# ============================================================

def calculate_technical_score(
    technicals: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate the 60-point technical score.
    """

    components = [
        score_price_vs_200(technicals),
        score_sma200_slope(technicals),
        score_price_vs_50(technicals),
        score_sma50_vs_200(technicals),
        score_rsi(technicals),
    ]

    raw_score = sum_component_points(
        components
    )

    available_points, coverage = (
        calculate_coverage(
            components
        )
    )

    adjusted_score = normalize_score(
        raw_score=raw_score,
        available_points=available_points,
        target_points=TECHNICAL_MAX,
    )

    return {
        "raw_score": raw_score,
        "available_points": available_points,
        "coverage": coverage,
        "adjusted_score": (
            adjusted_score
            if adjusted_score is not None
            else 0.0
        ),
        "components": components,
    }


# ============================================================
# FUNDAMENTAL SCORE
# ============================================================

def calculate_fundamental_score(
    fundamentals: dict[str, Any],
) -> dict[str, Any]:
    """
    Calculate the 40-point fundamental score.

    Missing metrics are excluded from the raw denominator.

    The adjusted score is only accepted when at least
    75% of fundamental points are available.
    """

    components = [
        score_pe(fundamentals),
        score_peg(fundamentals),
        score_fcf_margin(fundamentals),
        score_relative_performance(fundamentals),
    ]

    raw_score = sum_component_points(
        components
    )

    available_points, coverage = (
        calculate_coverage(
            components
        )
    )

    adjusted_score = normalize_score(
        raw_score=raw_score,
        available_points=available_points,
        target_points=FUNDAMENTAL_MAX,
    )

    if coverage < MIN_FUNDAMENTAL_COVERAGE:
        adjusted_score = None

    return {
        "raw_score": raw_score,
        "available_points": available_points,
        "coverage": coverage,
        "adjusted_score": adjusted_score,
        "components": components,
    }


# ============================================================
# SCORE LABEL
# ============================================================

def get_score_label(
    total_score: float | None,
) -> tuple[str, str]:
    """
    Return score grade and descriptive label.
    """

    if total_score is None:
        return "N/A", "Insufficient Data"

    if total_score >= 90:
        return "A+", "Exceptional"

    if total_score >= 85:
        return "A", "Excellent"

    if total_score >= 80:
        return "A-", "Very Strong"

    if total_score >= 75:
        return "B+", "Strong"

    if total_score >= 70:
        return "B", "Good"

    if total_score >= 65:
        return "B-", "Above Average"

    if total_score >= 60:
        return "C+", "Average"

    if total_score >= 50:
        return "C", "Mixed"

    if total_score >= 40:
        return "D", "Weak"

    return "F", "Very Weak"


# ============================================================
# COMPLETE SCORE
# ============================================================

def calculate_score(
    ticker: str,
    technicals: dict[str, Any],
    fundamentals: dict[str, Any],
) -> ScoreSummary:
    """
    Calculate the complete TickerTrends score from existing
    technical and fundamental snapshots.

    This function performs no network requests.
    """

    ticker = ticker.strip().upper().replace(
        ".",
        "-",
    )

    technical_result = (
        calculate_technical_score(
            technicals
        )
    )

    fundamental_result = (
        calculate_fundamental_score(
            fundamentals
        )
    )

    trend: TrendStateResult | None = (
        determine_trend_state(
            technicals
        )
    )

    technical_score = float(
        technical_result[
            "adjusted_score"
        ]
    )

    fundamental_score = (
        fundamental_result[
            "adjusted_score"
        ]
    )

    total_score: float | None = None

    if fundamental_score is not None:
        total_score = round_score(
            technical_score
            + fundamental_score
        )

    grade, label = get_score_label(
        total_score
    )

    return ScoreSummary(
        ticker=ticker,

        technical_raw_score=(
            technical_result[
                "raw_score"
            ]
        ),

        technical_available_points=(
            technical_result[
                "available_points"
            ]
        ),

        technical_score=(
            technical_score
        ),

        technical_coverage=(
            technical_result[
                "coverage"
            ]
        ),

        fundamental_raw_score=(
            fundamental_result[
                "raw_score"
            ]
        ),

        fundamental_available_points=(
            fundamental_result[
                "available_points"
            ]
        ),

        fundamental_score=(
            fundamental_score
        ),

        fundamental_coverage=(
            fundamental_result[
                "coverage"
            ]
        ),

        total_score=(
            total_score
        ),

        score_grade=grade,
        score_label=label,

        trend_state=(
            trend.state
            if trend
            else None
        ),

        trend_display=(
            trend.display
            if trend
            else None
        ),

        trend_reason=(
            trend.reason
            if trend
            else None
        ),

        technical_components=(
            technical_result[
                "components"
            ]
        ),

        fundamental_components=(
            fundamental_result[
                "components"
            ]
        ),
    )


def get_ticker_score(
    ticker: str,
) -> ScoreSummary | None:
    """
    Download technical and fundamental inputs and calculate
    the complete TickerTrends score.
    """

    technicals = get_technicals(
        ticker
    )

    if technicals is None:
        return None

    fundamentals = get_fundamentals(
        ticker
    )

    return calculate_score(
        ticker=ticker,
        technicals=technicals,
        fundamentals=fundamentals,
    )


# ============================================================
# CONSOLE DISPLAY
# ============================================================

def print_component(
    component: ScoreComponent,
) -> None:
    """
    Print one scoring component.
    """

    if not component.available:
        point_text = (
            f"N/A / {component.max_points:.0f}"
        )

    else:
        point_text = (
            f"{component.points:.1f} / "
            f"{component.max_points:.0f}"
        )

    print(
        f"{component.name:24} "
        f"{point_text:10} "
        f"{component.label}"
    )


def print_score_summary(
    result: ScoreSummary,
) -> None:
    """
    Print a complete TickerTrends score.
    """

    print()
    print(
        f"TickerTrends Score: {result.ticker}"
    )

    print("=" * 54)

    print(
        f"Trend:              "
        f"{result.trend_display or 'N/A'}"
    )

    print(
        f"Technical Score:    "
        f"{result.technical_score:.1f} / 60"
    )

    if result.fundamental_score is None:
        fundamental_text = "N/A"

    else:
        fundamental_text = (
            f"{result.fundamental_score:.1f} / 40"
        )

    print(
        f"Fundamental Score:  "
        f"{fundamental_text}"
    )

    if result.total_score is None:
        total_text = "N/A"

    else:
        total_text = (
            f"{result.total_score:.1f} / 100"
        )

    print(
        f"Total Score:        "
        f"{total_text}"
    )

    print(
        f"Grade:              "
        f"{result.score_grade}"
    )

    print(
        f"Rating:             "
        f"{result.score_label}"
    )

    print(
        f"Fundamental Data:   "
        f"{result.fundamental_coverage:.0f}%"
    )

    print()
    print("TECHNICAL COMPONENTS")
    print("-" * 54)

    for component in result.technical_components:
        print_component(
            component
        )

    print()
    print("FUNDAMENTAL COMPONENTS")
    print("-" * 54)

    for component in result.fundamental_components:
        print_component(
            component
        )

    print()


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    #TEST_TICKER = "MSFT"
    #TEST_TICKER = "AAPL"    
    TEST_TICKER = "NVDA"

    print(
        f"Calculating TickerTrends score "
        f"for {TEST_TICKER}..."
    )

    result = get_ticker_score(
        TEST_TICKER
    )

    if result is None:
        print(
            f"Unable to calculate score "
            f"for {TEST_TICKER}."
        )

    else:
        print_score_summary(
            result
        )
"""
MarketScope ETF
Sector analysis engine.

Uses the ETF screener output to calculate:

- Sector rankings
- Sector leadership
- Relative strength
- Trend rankings
- Market rotation scores
- Heatmap-ready datasets
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import (
    SECTOR_ETFS,
    SECTOR_SCORE_WEIGHTS,
)


# =========================================================
# UTILITIES
# =========================================================

def number(value, default=np.nan):
    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except Exception:
        pass

    return default


def clamp(
    value,
    minimum=0,
    maximum=100,
):
    value = number(value)

    if pd.isna(value):
        return np.nan

    return max(minimum, min(value, maximum))

def normalize_return(
    value: float,
    lower_bound: float,
    upper_bound: float,
) -> float:
    """
    Normalize a return value to a 0-100 scale.

    Returns at or below lower_bound score 0.
    Returns at or above upper_bound score 100.
    """

    value = number(value)

    if pd.isna(value):
        return np.nan

    if upper_bound <= lower_bound:
        return np.nan

    score = (
        (value - lower_bound)
        / (upper_bound - lower_bound)
    ) * 100

    return clamp(score)

# =========================================================
# SECTOR SCORE
# =========================================================

def calculate_sector_score(
    row: pd.Series,
) -> float:
    """
    Calculate the normalized MarketScope Sector Score.

    All components are converted to a 0-100 scale before
    applying the configured sector weights.
    """

    normalized_metrics = {
        "1M": normalize_return(
            row.get("Return 1M %"),
            lower_bound=-10,
            upper_bound=15,
        ),

        "3M": normalize_return(
            row.get("Return 3M %"),
            lower_bound=-15,
            upper_bound=25,
        ),

        "6M": normalize_return(
            row.get("Return 6M %"),
            lower_bound=-20,
            upper_bound=40,
        ),

        "1Y": normalize_return(
            row.get("Return 1Y %"),
            lower_bound=-30,
            upper_bound=60,
        ),

        "trend": clamp(
            row.get("Trend Score")
        ),
    }

    weighted_total = 0.0
    available_weight = 0.0

    for metric, score in normalized_metrics.items():

        if pd.isna(score):
            continue

        weight = number(
            SECTOR_SCORE_WEIGHTS.get(
                metric,
                0,
            ),
            default=0,
        )

        if weight <= 0:
            continue

        weighted_total += (
            score * weight
        )

        available_weight += weight

    if available_weight == 0:
        return np.nan

    sector_score = (
        weighted_total
        / available_weight
    )

    return round(
        clamp(sector_score),
        2,
    )


# =========================================================
# LEADERSHIP CLASSIFICATION
# =========================================================

def classify_sector_strength(
    score: float,
) -> str:
    """
    Convert sector score into descriptive text.
    """

    score = number(score)

    if pd.isna(score):
        return "Unknown"

    if score >= 85:
        return "Strong Leader"

    if score >= 70:
        return "Leader"

    if score >= 55:
        return "Neutral"

    if score >= 40:
        return "Lagging"

    return "Weak"


# =========================================================
# RELATIVE STRENGTH
# =========================================================

def calculate_relative_strength(
    sector_return: float,
    benchmark_return: float,
):
    """
    Relative performance versus benchmark.
    """

    sector_return = number(sector_return)
    benchmark_return = number(benchmark_return)

    if (
        pd.isna(sector_return)
        or pd.isna(benchmark_return)
    ):
        return np.nan

    return sector_return - benchmark_return


# =========================================================
# MARKET ROTATION
# =========================================================

def determine_rotation_status(
    row: pd.Series,
) -> str:
    """
    Identify sector rotation behavior.
    """

    one_month = number(
        row.get("Return 1M %")
    )

    three_month = number(
        row.get("Return 3M %")
    )

    etf_score = number(
        row.get("ETF Score")
    )

    if (
        pd.isna(one_month)
        or pd.isna(three_month)
        or pd.isna(etf_score)
    ):
        return "Unknown"

    if (
        one_month > three_month
        and etf_score >= 70
    ):
        return "Improving"

    if (
        one_month < three_month
        and etf_score >= 70
    ):
        return "Cooling"

    if etf_score < 50:
        return "Weakening"

    return "Stable"


# =========================================================
# BUILD SECTOR TABLE
# =========================================================

def build_sector_rankings(
    sector_df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build sector leadership rankings.
    """

    if (
        sector_df is None
        or sector_df.empty
    ):
        return pd.DataFrame()

    rankings = sector_df.copy()

    rankings["Sector Score"] = rankings.apply(
        calculate_sector_score,
        axis=1,
    )

    rankings["Sector Strength"] = (
        rankings["Sector Score"]
        .apply(classify_sector_strength)
    )

    rankings["Rotation"] = rankings.apply(
        determine_rotation_status,
        axis=1,
    )

    rankings = rankings.sort_values(
        "Sector Score",
        ascending=False,
        na_position="last",
    )

    rankings["Rank"] = (
        range(
            1,
            len(rankings) + 1,
        )
    )

    return rankings.reset_index(
        drop=True
    )


# =========================================================
# SECTOR LEADERS
# =========================================================

def get_top_sectors(
    rankings: pd.DataFrame,
    count: int = 5,
) -> pd.DataFrame:
    """
    Return strongest sectors.
    """

    if rankings.empty:
        return pd.DataFrame()

    return rankings.head(count)


def get_bottom_sectors(
    rankings: pd.DataFrame,
    count: int = 5,
) -> pd.DataFrame:
    """
    Return weakest sectors.
    """

    if rankings.empty:
        return pd.DataFrame()

    return rankings.tail(count)


# =========================================================
# HEATMAP DATA
# =========================================================

def build_heatmap_dataset(
    sector_df: pd.DataFrame,
    period_column: str = "Return 1M %",
):
    """
    Prepare sector data for heatmaps.
    """

    if (
        sector_df is None
        or sector_df.empty
    ):
        return pd.DataFrame()

    heatmap = sector_df.copy()

    columns = [
        "Sector",
        "Ticker",
        period_column,
    ]

    columns = [
        col
        for col in columns
        if col in heatmap.columns
    ]

    return heatmap[columns]


# =========================================================
# SUMMARY DASHBOARD
# =========================================================

def build_sector_summary(
    rankings: pd.DataFrame,
) -> dict:
    """
    Generate dashboard summary metrics.
    """

    if rankings.empty:

        return {
            "top_sector": None,
            "bottom_sector": None,
            "average_score": np.nan,
        }

    top_sector = rankings.iloc[0]

    bottom_sector = rankings.iloc[-1]

    return {
        "top_sector": top_sector["Sector"],
        "top_sector_ticker": top_sector["Ticker"],
        "top_sector_score": top_sector["Sector Score"],
        "bottom_sector": bottom_sector["Sector"],
        "bottom_sector_ticker": bottom_sector["Ticker"],
        "bottom_sector_score": bottom_sector["Sector Score"],
        "average_score": rankings[
            "Sector Score"
        ].mean(),
    }


# =========================================================
# MAIN ENTRY POINT
# =========================================================

def analyze_sectors(
    sector_df: pd.DataFrame,
):
    """
    Main callable used by Streamlit pages.

    Returns:

    {
        "rankings": dataframe,
        "leaders": dataframe,
        "laggards": dataframe,
        "summary": dict,
    }
    """

    rankings = build_sector_rankings(
        sector_df
    )

    return {
        "rankings": rankings,
        "leaders": get_top_sectors(
            rankings
        ),
        "laggards": get_bottom_sectors(
            rankings
        ),
        "summary": build_sector_summary(
            rankings
        ),
    }


# =========================================================
# TEST
# =========================================================

if __name__ == "__main__":

    print(
        "MarketScope ETF sector engine loaded."
    )

    print(
        f"{len(SECTOR_ETFS)} sectors configured."
    )
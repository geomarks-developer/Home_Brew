"""
TickerTrends Technical Analysis
===============================

Calculates the technical indicators used by TickerTrends.

Core indicators:
    - Current price
    - 50-day simple moving average
    - 200-day simple moving average
    - 200-day moving-average slope
    - Percent distance from 50-day SMA
    - Percent distance from 200-day SMA
    - RSI-14

TickerTrends intentionally keeps the technical model simple.

The 200-day SMA establishes the long-term trend.
The 50-day SMA describes the intermediate trend.
RSI describes the current condition within that trend.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import yfinance as yf


# ============================================================
# CONSTANTS
# ============================================================

SMA_SHORT = 50
SMA_LONG = 200
RSI_PERIOD = 14

# Number of trading days used to evaluate the direction
# of the 200-day moving average.
SMA_SLOPE_LOOKBACK = 20

# We need substantially more than 200 observations because
# calculation of the 200-day SMA itself consumes 200 rows.
DOWNLOAD_PERIOD = "2y"


# ============================================================
# TICKER NORMALIZATION
# ============================================================

def normalize_ticker(ticker: str) -> str:
    """
    Normalize ticker symbols into the format used by yfinance.

    Examples:
        msft  -> MSFT
        BRK.B -> BRK-B
        BF.B  -> BF-B
    """

    return ticker.strip().upper().replace(".", "-")


# ============================================================
# PRICE DOWNLOAD
# ============================================================

def download_price_history(
    ticker: str,
    period: str = DOWNLOAD_PERIOD,
) -> pd.DataFrame:
    """
    Download daily adjusted price history for one ticker.

    Returns an empty DataFrame when no usable data is returned.
    """

    ticker = normalize_ticker(ticker)

    try:
        data = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            actions=False,
            progress=False,
            threads=False,
            multi_level_index=False,
        )

    except Exception:
        return pd.DataFrame()

    if data is None or data.empty:
        return pd.DataFrame()

    data = data.copy()

    # Make sure the index is in chronological order.
    data.sort_index(inplace=True)

    # Remove rows that do not contain a usable closing price.
    if "Close" not in data.columns:
        return pd.DataFrame()

    data = data.dropna(
        subset=["Close"]
    )

    return data


# ============================================================
# RSI
# ============================================================

def calculate_rsi(
    close: pd.Series,
    period: int = RSI_PERIOD,
) -> pd.Series:
    """
    Calculate RSI using Wilder-style smoothing.

    Returns a pandas Series aligned with the input series.
    """

    close = pd.to_numeric(
        close,
        errors="coerce",
    )

    delta = close.diff()

    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    average_gain = gains.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = losses.ewm(
        alpha=1 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    relative_strength = (
        average_gain / average_loss
    )

    rsi = 100 - (
        100 / (1 + relative_strength)
    )

    # Handle periods where there are gains but no losses.
    rsi = rsi.mask(
        (average_loss == 0)
        & (average_gain > 0),
        100.0,
    )

    # Handle periods where there are losses but no gains.
    rsi = rsi.mask(
        (average_gain == 0)
        & (average_loss > 0),
        0.0,
    )

    # If neither gains nor losses exist, RSI is neutral.
    rsi = rsi.mask(
        (average_gain == 0)
        & (average_loss == 0),
        50.0,
    )

    return rsi


# ============================================================
# MOVING AVERAGES
# ============================================================

def add_moving_averages(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add the 50-day and 200-day simple moving averages.
    """

    frame = data.copy()

    frame["SMA_50"] = frame["Close"].rolling(
        window=SMA_SHORT,
        min_periods=SMA_SHORT,
    ).mean()

    frame["SMA_200"] = frame["Close"].rolling(
        window=SMA_LONG,
        min_periods=SMA_LONG,
    ).mean()

    return frame


# ============================================================
# TECHNICAL COLUMNS
# ============================================================

def add_technical_columns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Add all TickerTrends technical columns to price history.
    """

    frame = add_moving_averages(data)

    frame["RSI_14"] = calculate_rsi(
        frame["Close"]
    )

    # Percent above/below 50-day SMA.
    frame["Pct_From_SMA50"] = (
        (
            frame["Close"]
            / frame["SMA_50"]
        )
        - 1
    ) * 100

    # Percent above/below 200-day SMA.
    frame["Pct_From_SMA200"] = (
        (
            frame["Close"]
            / frame["SMA_200"]
        )
        - 1
    ) * 100

    return frame


# ============================================================
# 200-DAY SLOPE
# ============================================================

def calculate_sma200_slope(
    sma_200: pd.Series,
    lookback: int = SMA_SLOPE_LOOKBACK,
) -> float | None:
    """
    Calculate the percentage change in the 200-day SMA
    over the specified lookback period.

    Positive:
        200-day SMA is rising.

    Negative:
        200-day SMA is falling.

    Example:
        +1.25 means the 200-day SMA increased approximately
        1.25% over the lookback period.
    """

    valid = sma_200.dropna()

    if len(valid) <= lookback:
        return None

    current = float(valid.iloc[-1])

    previous = float(
        valid.iloc[-1 - lookback]
    )

    if previous == 0:
        return None

    slope = (
        (current / previous) - 1
    ) * 100

    return float(slope)


# ============================================================
# SAFE VALUE HELPERS
# ============================================================

def safe_float(
    value: Any,
) -> float | None:
    """
    Convert a value to a plain Python float.

    Returns None for invalid, NaN, or infinite values.
    """

    if value is None:
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not np.isfinite(number):
        return None

    return number


# ============================================================
# TECHNICAL SNAPSHOT
# ============================================================

def calculate_technicals_from_history(
    ticker: str,
    data: pd.DataFrame,
) -> dict[str, Any] | None:
    """
    Calculate the latest technical snapshot from downloaded
    price history.

    This function does not perform any network requests.
    """

    ticker = normalize_ticker(ticker)

    if data is None or data.empty:
        return None

    if "Close" not in data.columns:
        return None

    frame = add_technical_columns(data)

    if frame.empty:
        return None

    # We require a valid 200-day SMA because it is the
    # foundation of the TickerTrends trend model.
    valid = frame.dropna(
        subset=["SMA_200"]
    )

    if valid.empty:
        return None

    latest = frame.iloc[-1]

    price = safe_float(
        latest["Close"]
    )

    sma_50 = safe_float(
        latest["SMA_50"]
    )

    sma_200 = safe_float(
        latest["SMA_200"]
    )

    rsi_14 = safe_float(
        latest["RSI_14"]
    )

    pct_from_sma50 = safe_float(
        latest["Pct_From_SMA50"]
    )

    pct_from_sma200 = safe_float(
        latest["Pct_From_SMA200"]
    )

    sma_200_slope = calculate_sma200_slope(
        frame["SMA_200"]
    )

    if price is None or sma_200 is None:
        return None

    return {
        "ticker": ticker,
        "price": price,
        "sma_50": sma_50,
        "sma_200": sma_200,
        "sma_200_slope": sma_200_slope,
        "pct_from_sma50": pct_from_sma50,
        "pct_from_sma200": pct_from_sma200,
        "rsi_14": rsi_14,
    }


def get_technicals(
    ticker: str,
) -> dict[str, Any] | None:
    """
    Download price history and calculate the latest
    TickerTrends technical snapshot.
    """

    ticker = normalize_ticker(ticker)

    data = download_price_history(ticker)

    if data.empty:
        return None

    return calculate_technicals_from_history(
        ticker,
        data,
    )


# ============================================================
# CHART DATA
# ============================================================

def get_chart_data(
    ticker: str,
    period: str = DOWNLOAD_PERIOD,
) -> pd.DataFrame:
    """
    Return historical price data with TickerTrends indicators.

    Intended for the Details page chart.

    Returned columns include:

        Close
        SMA_50
        SMA_200
        RSI_14
        Pct_From_SMA50
        Pct_From_SMA200
    """

    data = download_price_history(
        ticker,
        period=period,
    )

    if data.empty:
        return pd.DataFrame()

    return add_technical_columns(data)


# ============================================================
# BATCH CALCULATION
# ============================================================

def calculate_universe_technicals(
    tickers: list[str],
) -> list[dict[str, Any]]:
    """
    Calculate technical snapshots for a list of tickers.

    This simple version processes one ticker at a time.

    We can optimize universe-wide downloads later after the
    calculations and scoring model have been validated.
    """

    results: list[dict[str, Any]] = []

    total = len(tickers)

    for number, ticker in enumerate(
        tickers,
        start=1,
    ):
        normalized = normalize_ticker(ticker)

        print(
            f"[{number}/{total}] "
            f"Calculating {normalized}..."
        )

        technicals = get_technicals(
            normalized
        )

        if technicals is not None:
            results.append(technicals)

    return results


# ============================================================
# DISPLAY / TESTING
# ============================================================

def print_technical_snapshot(
    snapshot: dict[str, Any],
) -> None:
    """
    Print one technical snapshot in a readable format.
    """

    ticker = snapshot["ticker"]

    print()
    print(f"TickerTrends Technicals: {ticker}")
    print("=" * 34)

    price = snapshot.get("price")
    sma_50 = snapshot.get("sma_50")
    sma_200 = snapshot.get("sma_200")
    slope = snapshot.get("sma_200_slope")
    pct_50 = snapshot.get("pct_from_sma50")
    pct_200 = snapshot.get("pct_from_sma200")
    rsi = snapshot.get("rsi_14")

    if price is not None:
        print(f"Price:             ${price:,.2f}")

    if sma_50 is not None:
        print(f"50-day SMA:        ${sma_50:,.2f}")

    if sma_200 is not None:
        print(f"200-day SMA:       ${sma_200:,.2f}")

    if slope is not None:
        print(f"200-day slope:      {slope:+.2f}%")

    if pct_50 is not None:
        print(f"From 50-day SMA:    {pct_50:+.2f}%")

    if pct_200 is not None:
        print(f"From 200-day SMA:   {pct_200:+.2f}%")

    if rsi is not None:
        print(f"RSI-14:             {rsi:.1f}")

    print()


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    # MSFT gives us a familiar first test ticker before
    # running calculations against all 214 securities.
    TEST_TICKER = "MSFT"

    print(
        f"Downloading technical data for "
        f"{TEST_TICKER}..."
    )

    result = get_technicals(
        TEST_TICKER
    )

    if result is None:
        print(
            f"Unable to calculate technicals "
            f"for {TEST_TICKER}."
        )

    else:
        print_technical_snapshot(
            result
        )
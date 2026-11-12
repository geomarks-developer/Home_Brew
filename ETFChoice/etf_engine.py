"""
MarketScope ETF
ETF analysis and scoring engine.

This module calculates:

- Historical returns
- Moving averages
- Relative strength
- RSI
- Volatility
- Maximum drawdown
- Distance from 52-week high
- Trend classification
- Momentum score
- Trend score
- Risk score
- Overall MarketScope ETF score

The module does not download market data. Historical price data
must be supplied by market_data.py or another data-loading module.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from config import (
    ETF_CATEGORY_LOOKUP,
    ETF_SCORE_WEIGHTS,
    PERFORMANCE_WINDOWS,
    PRIMARY_BENCHMARK,
    RSI_PERIOD,
    SMA_LONG,
    SMA_SHORT,
)


# =========================================================
# GENERAL UTILITIES
# =========================================================


def number(value: Any, default: float = np.nan) -> float:
    """
    Convert a value to float.

    Returns the supplied default when conversion is not possible.
    """

    if value is None:
        return default

    try:
        converted = float(value)

        if not np.isfinite(converted):
            return default

        return converted

    except (TypeError, ValueError):
        return default


def clamp(
    value: Any,
    minimum: float = 0.0,
    maximum: float = 100.0,
) -> float:
    """
    Restrict a numeric value to a specified range.
    """

    converted = number(value)

    if pd.isna(converted):
        return np.nan

    return float(max(minimum, min(converted, maximum)))


def safe_mean(values: list[Any], default: float = np.nan) -> float:
    """
    Calculate the mean of valid numeric values.
    """

    clean_values = [
        number(value)
        for value in values
        if pd.notna(number(value))
    ]

    if not clean_values:
        return default

    return float(np.mean(clean_values))


def round_or_nan(
    value: Any,
    digits: int = 2,
) -> float:
    """
    Round a number while preserving missing values.
    """

    converted = number(value)

    if pd.isna(converted):
        return np.nan

    return round(converted, digits)


# =========================================================
# PRICE DATA PREPARATION
# =========================================================


def prepare_history(history: pd.DataFrame | None) -> pd.DataFrame:
    """
    Validate and clean an ETF price-history DataFrame.

    Expected columns may include:

    - Open
    - High
    - Low
    - Close
    - Adj Close
    - Volume

    The resulting DataFrame always uses a numeric Close column.
    If Adj Close exists, it is preferred for return calculations.
    """

    if history is None:
        return pd.DataFrame()

    if not isinstance(history, pd.DataFrame):
        return pd.DataFrame()

    if history.empty:
        return pd.DataFrame()

    data = history.copy()

    # Flatten columns when data came from a MultiIndex structure.
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [
            column[-1] if isinstance(column, tuple) else column
            for column in data.columns
        ]

    # Remove duplicate column names after flattening.
    data = data.loc[:, ~data.columns.duplicated()].copy()

    price_column = None

    if "Adj Close" in data.columns:
        price_column = "Adj Close"

    elif "Close" in data.columns:
        price_column = "Close"

    if price_column is None:
        return pd.DataFrame()

    data["Close"] = pd.to_numeric(
        data[price_column],
        errors="coerce",
    )

    if "Volume" in data.columns:
        data["Volume"] = pd.to_numeric(
            data["Volume"],
            errors="coerce",
        )

    data = data.dropna(subset=["Close"])

    if data.empty:
        return pd.DataFrame()

    data = data.sort_index()

    data = data[
        ~data.index.duplicated(keep="last")
    ]

    return data


def extract_ticker_history(
    price_data: pd.DataFrame,
    ticker: str,
) -> pd.DataFrame:
    """
    Extract one ticker's history from a multi-ticker DataFrame.

    Supports common yfinance MultiIndex layouts:

    Layout 1:
        Price field -> ticker

    Layout 2:
        Ticker -> price field

    It also accepts an already-extracted single-ticker DataFrame.
    """

    if price_data is None or price_data.empty:
        return pd.DataFrame()

    ticker = ticker.upper().strip()

    if not isinstance(price_data.columns, pd.MultiIndex):
        return prepare_history(price_data)

    level_zero = set(
        str(value).upper()
        for value in price_data.columns.get_level_values(0)
    )

    level_one = set(
        str(value).upper()
        for value in price_data.columns.get_level_values(1)
    )

    ticker_data = pd.DataFrame()

    try:
        if ticker in level_zero:
            ticker_data = price_data[ticker].copy()

        elif ticker in level_one:
            ticker_data = price_data.xs(
                ticker,
                axis=1,
                level=1,
            ).copy()

    except (KeyError, IndexError, TypeError):
        return pd.DataFrame()

    return prepare_history(ticker_data)


# =========================================================
# RETURN CALCULATIONS
# =========================================================


def calculate_period_return(
    close: pd.Series,
    trading_days: int,
) -> float:
    """
    Calculate percentage return over a trading-day window.

    Example:
        21 trading days approximates one month.
    """

    clean_close = pd.to_numeric(
        close,
        errors="coerce",
    ).dropna()

    if len(clean_close) <= trading_days:
        return np.nan

    current_price = number(clean_close.iloc[-1])
    previous_price = number(clean_close.iloc[-(trading_days + 1)])

    if (
        pd.isna(current_price)
        or pd.isna(previous_price)
        or previous_price == 0
    ):
        return np.nan

    return ((current_price / previous_price) - 1.0) * 100.0


def calculate_ytd_return(close: pd.Series) -> float:
    """
    Calculate year-to-date percentage return.
    """

    clean_close = pd.to_numeric(
        close,
        errors="coerce",
    ).dropna()

    if clean_close.empty:
        return np.nan

    if not isinstance(clean_close.index, pd.DatetimeIndex):
        try:
            clean_close.index = pd.to_datetime(clean_close.index)
        except (TypeError, ValueError):
            return np.nan

    latest_date = clean_close.index.max()
    current_year = latest_date.year

    year_prices = clean_close[
        clean_close.index.year == current_year
    ]

    if len(year_prices) < 2:
        return np.nan

    starting_price = number(year_prices.iloc[0])
    current_price = number(year_prices.iloc[-1])

    if (
        pd.isna(starting_price)
        or pd.isna(current_price)
        or starting_price == 0
    ):
        return np.nan

    return ((current_price / starting_price) - 1.0) * 100.0


def calculate_returns(close: pd.Series) -> dict[str, float]:
    """
    Calculate all configured MarketScope performance windows.
    """

    results: dict[str, float] = {}

    for label, window in PERFORMANCE_WINDOWS.items():

        if window == "YTD":
            result = calculate_ytd_return(close)
        else:
            result = calculate_period_return(
                close,
                int(window),
            )

        results[label] = round_or_nan(result)

    return results


# =========================================================
# TECHNICAL INDICATORS
# =========================================================


def calculate_rsi(
    close: pd.Series,
    period: int = RSI_PERIOD,
) -> pd.Series:
    """
    Calculate Wilder-style Relative Strength Index.

    Returns a Series aligned to the supplied close-price Series.
    """

    clean_close = pd.to_numeric(
        close,
        errors="coerce",
    )

    delta = clean_close.diff()

    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)

    average_gain = gains.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    average_loss = losses.ewm(
        alpha=1.0 / period,
        adjust=False,
        min_periods=period,
    ).mean()

    relative_strength = average_gain / average_loss.replace(
        0,
        np.nan,
    )

    rsi = 100.0 - (
        100.0 / (1.0 + relative_strength)
    )

    # Continuous gains imply an RSI of 100.
    rsi = rsi.mask(
        (average_loss == 0) & (average_gain > 0),
        100.0,
    )

    # No gains or losses implies neutral RSI.
    rsi = rsi.mask(
        (average_loss == 0) & (average_gain == 0),
        50.0,
    )

    return rsi


def calculate_annualized_volatility(
    close: pd.Series,
    trading_days: int = 252,
) -> float:
    """
    Calculate annualized historical volatility as a percentage.
    """

    daily_returns = pd.to_numeric(
        close,
        errors="coerce",
    ).pct_change(fill_method=None)

    daily_returns = daily_returns.replace(
        [np.inf, -np.inf],
        np.nan,
    ).dropna()

    if len(daily_returns) < 2:
        return np.nan

    volatility = (
        daily_returns.std(ddof=1)
        * np.sqrt(trading_days)
        * 100.0
    )

    return float(volatility)


def calculate_max_drawdown(close: pd.Series) -> float:
    """
    Calculate maximum drawdown as a negative percentage.

    Example:
        -20.0 means the ETF experienced a 20% peak-to-trough decline.
    """

    clean_close = pd.to_numeric(
        close,
        errors="coerce",
    ).dropna()

    if clean_close.empty:
        return np.nan

    running_high = clean_close.cummax()

    drawdown = (
        clean_close / running_high
    ) - 1.0

    return float(drawdown.min() * 100.0)


def calculate_distance_from_high(
    close: pd.Series,
    lookback: int = 252,
) -> float:
    """
    Calculate the current price's distance from its lookback high.

    A value of:
        0.0 means the ETF is at its high.
        -10.0 means the ETF is 10% below its high.
    """

    clean_close = pd.to_numeric(
        close,
        errors="coerce",
    ).dropna()

    if clean_close.empty:
        return np.nan

    window = clean_close.tail(lookback)

    current_price = number(window.iloc[-1])
    period_high = number(window.max())

    if (
        pd.isna(current_price)
        or pd.isna(period_high)
        or period_high == 0
    ):
        return np.nan

    return ((current_price / period_high) - 1.0) * 100.0


def calculate_average_volume(
    history: pd.DataFrame,
    period: int = 20,
) -> float:
    """
    Calculate average daily trading volume.
    """

    if "Volume" not in history.columns:
        return np.nan

    volume = pd.to_numeric(
        history["Volume"],
        errors="coerce",
    ).dropna()

    if volume.empty:
        return np.nan

    return float(volume.tail(period).mean())


# =========================================================
# RELATIVE STRENGTH
# =========================================================


def calculate_relative_strength(
    etf_close: pd.Series,
    benchmark_close: pd.Series,
    trading_days: int = 63,
) -> float:
    """
    Calculate ETF return minus benchmark return.

    Positive values mean the ETF outperformed the benchmark.
    Negative values mean the ETF underperformed the benchmark.
    """

    etf_return = calculate_period_return(
        etf_close,
        trading_days,
    )

    benchmark_return = calculate_period_return(
        benchmark_close,
        trading_days,
    )

    if (
        pd.isna(etf_return)
        or pd.isna(benchmark_return)
    ):
        return np.nan

    return float(etf_return - benchmark_return)


# =========================================================
# TREND CLASSIFICATION
# =========================================================


def classify_trend(
    current_price: float,
    sma_50: float,
    sma_200: float,
    return_3m: float = np.nan,
) -> tuple[int, str]:
    """
    Classify an ETF's trend on a five-level scale.

    Returns:
        trend_score, trend_label

    Scores:
        5 = Strong Uptrend
        4 = Uptrend
        3 = Neutral
        2 = Downtrend
        1 = Strong Downtrend
    """

    if pd.isna(current_price):
        return 3, "Neutral"

    has_sma_50 = pd.notna(sma_50)
    has_sma_200 = pd.notna(sma_200)

    if not has_sma_50 and not has_sma_200:
        return 3, "Neutral"

    if has_sma_50 and has_sma_200:

        if (
            current_price > sma_50
            and sma_50 > sma_200
            and (
                pd.isna(return_3m)
                or return_3m > 0
            )
        ):
            return 5, "Strong Uptrend"

        if (
            current_price > sma_200
            and current_price > sma_50
        ):
            return 4, "Uptrend"

        if (
            current_price < sma_50
            and sma_50 < sma_200
            and (
                pd.isna(return_3m)
                or return_3m < 0
            )
        ):
            return 1, "Strong Downtrend"

        if current_price < sma_200:
            return 2, "Downtrend"

        return 3, "Neutral"

    if has_sma_50:

        if current_price > sma_50:
            return 4, "Uptrend"

        if current_price < sma_50:
            return 2, "Downtrend"

    return 3, "Neutral"


# =========================================================
# COMPONENT SCORES
# =========================================================


def normalize_return_score(
    return_value: float,
    lower_bound: float,
    upper_bound: float,
) -> float:
    """
    Convert a return into a score from 0 to 100.

    Values at or below lower_bound receive 0.
    Values at or above upper_bound receive 100.
    """

    value = number(return_value)

    if pd.isna(value):
        return np.nan

    if upper_bound <= lower_bound:
        return np.nan

    score = (
        (value - lower_bound)
        / (upper_bound - lower_bound)
    ) * 100.0

    return clamp(score)


def calculate_momentum_score(
    returns: dict[str, float],
) -> float:
    """
    Calculate a weighted momentum score from 0 to 100.

    Higher recent and intermediate-term returns receive
    higher scores.
    """

    period_scores = {
        "1M": normalize_return_score(
            returns.get("1M", np.nan),
            -10.0,
            15.0,
        ),
        "3M": normalize_return_score(
            returns.get("3M", np.nan),
            -15.0,
            25.0,
        ),
        "6M": normalize_return_score(
            returns.get("6M", np.nan),
            -20.0,
            40.0,
        ),
        "1Y": normalize_return_score(
            returns.get("1Y", np.nan),
            -30.0,
            60.0,
        ),
    }

    period_weights = {
        "1M": 0.15,
        "3M": 0.30,
        "6M": 0.30,
        "1Y": 0.25,
    }

    weighted_total = 0.0
    available_weight = 0.0

    for period, score in period_scores.items():

        if pd.isna(score):
            continue

        weight = period_weights[period]

        weighted_total += score * weight
        available_weight += weight

    if available_weight == 0:
        return np.nan

    return clamp(weighted_total / available_weight)


def calculate_trend_score(
    current_price: float,
    sma_50: float,
    sma_200: float,
    rsi: float,
    distance_from_high: float,
) -> float:
    """
    Calculate a technical trend score from 0 to 100.
    """

    components: list[float] = []

    if pd.notna(current_price) and pd.notna(sma_50):
        components.append(
            100.0 if current_price > sma_50 else 25.0
        )

    if pd.notna(current_price) and pd.notna(sma_200):
        components.append(
            100.0 if current_price > sma_200 else 20.0
        )

    if pd.notna(sma_50) and pd.notna(sma_200):
        components.append(
            100.0 if sma_50 > sma_200 else 20.0
        )

    if pd.notna(rsi):

        if 50.0 <= rsi <= 70.0:
            components.append(100.0)

        elif 40.0 <= rsi < 50.0:
            components.append(70.0)

        elif 30.0 <= rsi < 40.0:
            components.append(45.0)

        elif rsi > 70.0:
            components.append(75.0)

        else:
            components.append(20.0)

    if pd.notna(distance_from_high):

        if distance_from_high >= -5.0:
            components.append(100.0)

        elif distance_from_high >= -10.0:
            components.append(80.0)

        elif distance_from_high >= -20.0:
            components.append(55.0)

        else:
            components.append(25.0)

    return clamp(safe_mean(components))


def calculate_risk_score(
    volatility: float,
    max_drawdown: float,
) -> float:
    """
    Calculate a risk score from 0 to 100.

    A higher score represents lower historical risk.
    """

    components: list[float] = []

    if pd.notna(volatility):

        if volatility <= 10.0:
            components.append(100.0)

        elif volatility <= 15.0:
            components.append(85.0)

        elif volatility <= 20.0:
            components.append(70.0)

        elif volatility <= 30.0:
            components.append(45.0)

        elif volatility <= 40.0:
            components.append(25.0)

        else:
            components.append(10.0)

    if pd.notna(max_drawdown):

        drawdown_size = abs(max_drawdown)

        if drawdown_size <= 10.0:
            components.append(100.0)

        elif drawdown_size <= 15.0:
            components.append(85.0)

        elif drawdown_size <= 25.0:
            components.append(65.0)

        elif drawdown_size <= 35.0:
            components.append(40.0)

        elif drawdown_size <= 50.0:
            components.append(20.0)

        else:
            components.append(5.0)

    return clamp(safe_mean(components))


def calculate_liquidity_score(
    average_volume: float,
) -> float:
    """
    Estimate ETF liquidity from average daily share volume.

    This score is a practical screening measure and is not
    a replacement for bid-ask spread or dollar-volumeme analysis.
    """

    volume = number(average_volume)

    if pd.isna(volume):
        return np.nan

    if volume >= 5_000_000:
      return 100.0

    if volume >= 1_000_000:
        return 90.0

    if volume >= 500_000:
        return 75.0

    if volume >= 100_000:
        return 55.0

    if volume >= 25_000:
        return 30.0

    return 10.0


def calculate_cost_score(
    expense_ratio: float,
) -> float:
    """
    Calculate an expense-ratio score from 0 to 100.

    expense_ratio is expected in percentage form.

    Examples:
        0.03 represents 0.03%
        0.35 represents 0.35%
    """

    expense = number(expense_ratio)

    if pd.isna(expense):
        return np.nan

    if expense <= 0.05:
        return 100.0

    if expense <= 0.10:
        return 95.0

    if expense <= 0.20:
        return 85.0

    if expense <= 0.35:
        return 70.0

    if expense <= 0.50:
        return 55.0

    if expense <= 0.75:
        return 35.0

    return 15.0


def calculate_dividend_score(
    dividend_yield: float,
) -> float:
    """
    Calculate a dividend score from 0 to 100.

    dividend_yield is expected in percentage form.

    Examples:
        1.50 represents 1.50%
        4.00 represents 4.00%
    """

    yield_value = number(dividend_yield)

    if pd.isna(yield_value):
        return np.nan

    if yield_value >= 5.0:
        return 100.0

    if yield_value >= 4.0:
        return 90.0

    if yield_value >= 3.0:
        return 80.0

    if yield_value >= 2.0:
        return 65.0

    if yield_value >= 1.0:
        return 45.0

    if yield_value > 0:
        return 25.0

    return 10.0


def calculate_overall_score(
    momentum_score: float,
    trend_score: float,
    risk_score: float,
    liquidity_score: float = np.nan,
    cost_score: float = np.nan,
    dividend_score: float = np.nan,
) -> float:
    """
    Calculate the overall MarketScope ETF score.

    Missing component scores are excluded and the remaining
    configured weights are re-normalized.
    """

    component_scores = {
        "momentum": momentum_score,
        "trend": trend_score,
        "cost": cost_score,
        "liquidity": liquidity_score,
        "dividend": dividend_score,
        "risk": risk_score,
    }

    weighted_total = 0.0
    available_weight = 0.0

    for component, score in component_scores.items():

        score_value = number(score)
        weight = number(
            ETF_SCORE_WEIGHTS.get(component, 0.0),
            default=0.0,
        )

        if pd.isna(score_value) or weight <= 0:
            continue

        weighted_total += score_value * weight
        available_weight += weight

    if available_weight == 0:
        return np.nan

    return clamp(weighted_total / available_weight)


# =========================================================
# ETF ANALYSIS
# =========================================================


def analyze_etf(
    ticker: str,
    history: pd.DataFrame,
    benchmark_history: pd.DataFrame | None = None,
    fund_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Analyze one ETF and return a single result dictionary.

    Parameters
    ----------
    ticker:
        ETF ticker symbol.

    history:
        Historical OHLCV DataFrame for the ETF.

    benchmark_history:
        Optional historical DataFrame for the benchmark ETF.

    fund_data:
        Optional dictionary containing ETF metadata such as:

        - name
        - expense_ratio
        - dividend_yield
        - total_assets

    Returns
    -------
    dict
        One row suitable for conversion into a DataFrame.
    """

    ticker = ticker.upper().strip()
    fund_data = fund_data or {}

    data = prepare_history(history)

    if data.empty:
        return {
            "Ticker": ticker,
            "Name": fund_data.get("name", ticker),
            "Categories": ", ".join(
                ETF_CATEGORY_LOOKUP.get(
                    ticker,
                    ["Unclassified"],
                )
            ),
            "Data Available": False,
            "Error": "No usable price history",
        }

    close = data["Close"]

    current_price = number(close.iloc[-1])

    sma_50_series = close.rolling(
        window=SMA_SHORT,
        min_periods=SMA_SHORT,
    ).mean()

    sma_200_series = close.rolling(
        window=SMA_LONG,
        min_periods=SMA_LONG,
    ).mean()

    sma_50 = (
        number(sma_50_series.iloc[-1])
        if not sma_50_series.empty
        else np.nan
    )

    sma_200 = (
        number(sma_200_series.iloc[-1])
        if not sma_200_series.empty
        else np.nan
    )

    rsi_series = calculate_rsi(close)
    rsi = (
        number(rsi_series.iloc[-1])
        if not rsi_series.empty
        else np.nan
    )

    returns = calculate_returns(close)

    volatility = calculate_annualized_volatility(close)
    max_drawdown = calculate_max_drawdown(close)
    distance_from_high = calculate_distance_from_high(close)
    average_volume = calculate_average_volume(data)

    relative_strength_3m = np.nan
    relative_strength_6m = np.nan
    relative_strength_1y = np.nan

    benchmark_data = prepare_history(benchmark_history)

    if not benchmark_data.empty:

        benchmark_close = benchmark_data["Close"]

        relative_strength_3m = calculate_relative_strength(
            close,
            benchmark_close,
            63,
        )

        relative_strength_6m = calculate_relative_strength(
            close,
            benchmark_close,
            126,
        )

        relative_strength_1y = calculate_relative_strength(
            close,
            benchmark_close,
            252,
        )

    trend_level, trend_label = classify_trend(
        current_price=current_price,
        sma_50=sma_50,
        sma_200=sma_200,
        return_3m=returns.get("3M", np.nan),
    )

    momentum_score = calculate_momentum_score(returns)

    technical_trend_score = calculate_trend_score(
        current_price=current_price,
        sma_50=sma_50,
        sma_200=sma_200,
        rsi=rsi,
        distance_from_high=distance_from_high,
    )

    risk_score = calculate_risk_score(
        volatility=volatility,
        max_drawdown=max_drawdown,
    )

    liquidity_score = calculate_liquidity_score(
        average_volume,
    )

    expense_ratio = number(
        fund_data.get("expense_ratio")
    )

    dividend_yield = number(
        fund_data.get("dividend_yield")
    )

    cost_score = calculate_cost_score(
        expense_ratio,
    )

    dividend_score = calculate_dividend_score(
        dividend_yield,
    )

    overall_score = calculate_overall_score(
        momentum_score=momentum_score,
        trend_score=technical_trend_score,
        risk_score=risk_score,
        liquidity_score=liquidity_score,
        cost_score=cost_score,
        dividend_score=dividend_score,
    )

    result = {
        "Ticker": ticker,
        "Name": fund_data.get("name", ticker),
        "Categories": ", ".join(
            ETF_CATEGORY_LOOKUP.get(
                ticker,
                ["Unclassified"],
            )
        ),
        "Benchmark": PRIMARY_BENCHMARK,
        "Data Available": True,
        "Last Date": data.index[-1],
        "Price": round_or_nan(current_price),
        "SMA 50": round_or_nan(sma_50),
        "SMA 200": round_or_nan(sma_200),
        "Above SMA 50": (
            current_price > sma_50
            if pd.notna(sma_50)
            else False
        ),
        "Above SMA 200": (
            current_price > sma_200
            if pd.notna(sma_200)
            else False
        ),
        "SMA 50 Above SMA 200": (
            sma_50 > sma_200
            if pd.notna(sma_50) and pd.notna(sma_200)
            else False
        ),
        "RSI 14": round_or_nan(rsi),
        "52W High Distance %": round_or_nan(
            distance_from_high
        ),
        "Volatility %": round_or_nan(volatility),
        "Max Drawdown %": round_or_nan(max_drawdown),
        "Average Volume": round_or_nan(
            average_volume,
            digits=0,
        ),
        "Relative Strength 3M %": round_or_nan(
            relative_strength_3m
        ),
        "Relative Strength 6M %": round_or_nan(
            relative_strength_6m
        ),
        "Relative Strength 1Y %": round_or_nan(
            relative_strength_1y
        ),
        "Trend Level": trend_level,
        "Trend": trend_label,
        "Momentum Score": round_or_nan(momentum_score),
        "Trend Score": round_or_nan(
            technical_trend_score
        ),
        "Risk Score": round_or_nan(risk_score),
        "Liquidity Score": round_or_nan(
            liquidity_score
        ),
        "Cost Score": round_or_nan(cost_score),
        "Dividend Score": round_or_nan(
            dividend_score
        ),
        "ETF Score": round_or_nan(overall_score),
        "Expense Ratio %": round_or_nan(
            expense_ratio,
            digits=3,
        ),
        "Dividend Yield %": round_or_nan(
            dividend_yield
        ),
        "Total Assets": number(
            fund_data.get("total_assets")
        ),
        "Error": "",
    }

    for label, value in returns.items():
        result[f"Return {label} %"] = round_or_nan(value)

    return result


# =========================================================
# UNIVERSE ANALYSIS
# =========================================================


def analyze_etf_universe(
    price_data: pd.DataFrame,
    tickers: list[str],
    benchmark_ticker: str = PRIMARY_BENCHMARK,
    fund_data_by_ticker: dict[str, dict[str, Any]] | None = None,
) -> pd.DataFrame:
    """
    Analyze an entire ETF universe.

    Parameters
    ----------
    price_data:
        Multi-ticker historical price DataFrame.

    tickers:
        ETF symbols to analyze.

    benchmark_ticker:
        Benchmark used for relative-strength calculations.

    fund_data_by_ticker:
        Optional dictionary keyed by ticker.

    Returns
    -------
    pandas.DataFrame
        An ETF screener DataFrame sorted by ETF Score.
    """

    fund_data_by_ticker = fund_data_by_ticker or {}

    benchmark_history = extract_ticker_history(
        price_data,
        benchmark_ticker,
    )

    rows: list[dict[str, Any]] = []

    unique_tickers = list(
        dict.fromkeys(
            ticker.upper().strip()
            for ticker in tickers
            if ticker
        )
    )

    for ticker in unique_tickers:

        history = extract_ticker_history(
            price_data,
            ticker,
        )

        fund_data = fund_data_by_ticker.get(
            ticker,
            {},
        )

        try:
            row = analyze_etf(
                ticker=ticker,
                history=history,
                benchmark_history=benchmark_history,
                fund_data=fund_data,
            )

        except Exception as error:
            row = {
                "Ticker": ticker,
                "Name": fund_data.get("name", ticker),
                "Categories": ", ".join(
                    ETF_CATEGORY_LOOKUP.get(
                        ticker,
                        ["Unclassified"],
                    )
                ),
                "Data Available": False,
                "ETF Score": np.nan,
                "Error": str(error),
            }

        rows.append(row)

    results = pd.DataFrame(rows)

    if results.empty:
        return results

    if "ETF Score" in results.columns:
        results = results.sort_values(
            by=[
                "Data Available",
                "ETF Score",
            ],
            ascending=[
                False,
                False,
            ],
            na_position="last",
        )

    return results.reset_index(drop=True)


# =========================================================
# DISPLAY HELPERS
# =========================================================


def get_screener_columns() -> list[str]:
    """
    Return the recommended ETF Screener display columns.
    """

    return [
        "Ticker",
        "Name",
        "Categories",
        "Price",
        "ETF Score",
        "Trend",
        "Momentum Score",
        "Trend Score",
        "Risk Score",
        "Return 1M %",
        "Return 3M %",
        "Return 6M %",
        "Return YTD %",
        "Return 1Y %",
        "Relative Strength 3M %",
        "RSI 14",
        "52W High Distance %",
        "Volatility %",
        "Max Drawdown %",
        "Dividend Yield %",
        "Expense Ratio %",
        "Average Volume",
    ]



def prepare_screener_display(
    results: pd.DataFrame,
) -> pd.DataFrame:
    """
    Prepare analysis results for the Streamlit ETF Screener.
    """

    if results is None or results.empty:
        return pd.DataFrame()

    display_columns = [
        column
        for column in get_screener_columns()
        if column in results.columns
    ]

    return results[display_columns].copy()


# =========================================================
# MODULE TEST
# =========================================================


if __name__ == "__main__":

    print("MarketScope ETF analysis engine loaded.")
    print(
        "This module expects historical price data "
        "from market_data.py."
    )
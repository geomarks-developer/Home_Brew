from __future__ import annotations

from typing import Any, Callable

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    DIVIDEND_WEIGHTS,
    MOMENTUM_WEIGHTS,
    QUALITY_WEIGHTS,
    RETURN_PERIODS,
    RISK_WEIGHTS,
    RSI_PERIOD,
    SCORE_WEIGHTS,
    SMA_LONG,
    SMA_SHORT,
    VALUE_WEIGHTS,
    validate_config,
)


ProgressCallback = Callable[[int, int, str], None]


def _number(value: Any) -> float:
    """Convert a value to float, returning NaN when unavailable."""
    try:
        result = float(value)
        return result if np.isfinite(result) else np.nan
    except (TypeError, ValueError):
        return np.nan


def _first(info: dict[str, Any], *keys: str) -> float:
    """Return the first usable numeric value among several Yahoo fields."""
    for key in keys:
        value = _number(info.get(key))
        if np.isfinite(value):
            return value
    return np.nan


def _close_series(history: pd.DataFrame | None) -> pd.Series:
    if history is None or history.empty or "Close" not in history.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(history["Close"], errors="coerce").dropna()


def calculate_rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    if len(close) <= period:
        return np.nan
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / period, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(alpha=1 / period, adjust=False).mean()
    denominator = loss.iloc[-1]
    if denominator == 0:
        return 100.0 if gain.iloc[-1] > 0 else 50.0
    return float(100 - (100 / (1 + gain.iloc[-1] / denominator)))


def period_return(close: pd.Series, trading_days: int) -> float:
    if len(close) <= trading_days or close.iloc[-trading_days - 1] == 0:
        return np.nan
    return float(close.iloc[-1] / close.iloc[-trading_days - 1] - 1)


def annualized_volatility(close: pd.Series) -> float:
    returns = close.pct_change().dropna()
    if returns.empty:
        return np.nan
    return float(returns.std(ddof=1) * np.sqrt(252))


def max_drawdown(close: pd.Series) -> float:
    if close.empty:
        return np.nan
    running_high = close.cummax()
    drawdowns = close / running_high - 1
    return float(drawdowns.min())


def price_position_52_week(close: pd.Series) -> float:
    window = close.tail(252)
    if window.empty:
        return np.nan
    low = window.min()
    high = window.max()
    if high == low:
        return 0.5
    return float((window.iloc[-1] - low) / (high - low))


def _annual_dividends(dividends: pd.Series | None) -> pd.Series:
    if dividends is None or dividends.empty:
        return pd.Series(dtype=float)
    series = pd.to_numeric(dividends, errors="coerce").dropna()
    if series.empty:
        return pd.Series(dtype=float)
    try:
        index = pd.to_datetime(series.index, utc=True).tz_convert(None)
    except (TypeError, ValueError):
        index = pd.to_datetime(series.index)
    series.index = index
    annual = series.groupby(series.index.year).sum().sort_index()
    current_year = pd.Timestamp.now().year
    if current_year in annual.index and series.index.max().month < 11:
        annual = annual.drop(current_year, errors="ignore")
    return annual


def dividend_cagr(dividends: pd.Series | None, years: int = 5) -> float:
    annual = _annual_dividends(dividends)
    if len(annual) < 2:
        return np.nan
    end_year = int(annual.index[-1])
    eligible = annual[annual.index <= end_year - years]
    if eligible.empty:
        start_value = float(annual.iloc[0])
        periods = int(annual.index[-1] - annual.index[0])
    else:
        start_value = float(eligible.iloc[-1])
        periods = int(end_year - eligible.index[-1])
    end_value = float(annual.iloc[-1])
    if periods <= 0 or start_value <= 0 or end_value <= 0:
        return np.nan
    return float((end_value / start_value) ** (1 / periods) - 1)


def dividend_consistency(dividends: pd.Series | None, years: int = 5) -> float:
    annual = _annual_dividends(dividends).tail(years + 1)
    if len(annual) < 2:
        return np.nan
    changes = annual.pct_change().dropna()
    if changes.empty:
        return np.nan
    return float((changes >= -0.005).mean())


def get_ticker_details(
    ticker: str,
    info_cache: dict[str, dict[str, Any]],
    dividend_cache: dict[str, pd.Series],
) -> tuple[dict[str, Any], pd.Series]:
    """Fetch and cache Yahoo company information and dividend history."""
    if ticker not in info_cache:
        try:
            info_cache[ticker] = yf.Ticker(ticker).get_info() or {}
        except Exception:
            info_cache[ticker] = {}

    if ticker not in dividend_cache:
        try:
            dividend_cache[ticker] = yf.Ticker(ticker).get_dividends(period="max")
        except Exception:
            dividend_cache[ticker] = pd.Series(dtype=float)

    return info_cache[ticker], dividend_cache[ticker]


def build_raw_row(
    ticker: str,
    history: pd.DataFrame | None,
    info: dict[str, Any],
    dividends: pd.Series | None,
) -> dict[str, Any]:
    close = _close_series(history)
    price = float(close.iloc[-1]) if not close.empty else _first(
        info, "currentPrice", "regularMarketPrice", "previousClose"
    )

    sma50 = float(close.tail(SMA_SHORT).mean()) if len(close) >= SMA_SHORT else np.nan
    sma200 = float(close.tail(SMA_LONG).mean()) if len(close) >= SMA_LONG else np.nan

    annual_dividend = _first(info, "dividendRate", "trailingAnnualDividendRate")
    dividend_yield = _first(info, "dividendYield", "trailingAnnualDividendYield")
    if not np.isfinite(dividend_yield) and np.isfinite(annual_dividend) and price > 0:
        dividend_yield = annual_dividend / price

    free_cash_flow = _first(info, "freeCashflow")
    market_cap = _first(info, "marketCap")
    price_to_fcf = (
        market_cap / free_cash_flow
        if np.isfinite(market_cap) and np.isfinite(free_cash_flow) and free_cash_flow > 0
        else np.nan
    )

    return {
        "Ticker": ticker,
        "Company": info.get("shortName") or info.get("longName") or ticker,
        "Sector": info.get("sector") or "Unknown",
        "Industry": info.get("industry") or "Unknown",
        "Price": price,
        "Market Cap": market_cap,
        "Dividend Rate": annual_dividend,
        "Dividend Yield": dividend_yield,
        "Payout Ratio": _first(info, "payoutRatio"),
        "Dividend Growth 1Y": dividend_cagr(dividends, 1),
        "Dividend Growth 3Y": dividend_cagr(dividends, 3),
        "Dividend Growth 5Y": dividend_cagr(dividends, 5),
        "Dividend Consistency": dividend_consistency(dividends, 5),
        "Ex-Dividend Date": info.get("exDividendDate"),
        "ROE": _first(info, "returnOnEquity"),
        "Profit Margin": _first(info, "profitMargins"),
        "Operating Margin": _first(info, "operatingMargins"),
        "Free Cash Flow": free_cash_flow,
        "Operating Cash Flow": _first(info, "operatingCashflow"),
        "Debt to Equity": _first(info, "debtToEquity"),
        "Earnings Growth": _first(info, "earningsGrowth"),
        "Revenue Growth": _first(info, "revenueGrowth"),
        "P/E": _first(info, "trailingPE"),
        "Forward P/E": _first(info, "forwardPE"),
        "PEG": _first(info, "pegRatio", "trailingPegRatio"),
        "Price to Book": _first(info, "priceToBook"),
        "Price to FCF": price_to_fcf,
        "SMA 50": sma50,
        "SMA 200": sma200,
        "Price vs SMA 50": price / sma50 - 1 if np.isfinite(price) and sma50 > 0 else np.nan,
        "Price vs SMA 200": price / sma200 - 1 if np.isfinite(price) and sma200 > 0 else np.nan,
        "Return 1M": period_return(close, RETURN_PERIODS["1M"]),
        "Return 3M": period_return(close, RETURN_PERIODS["3M"]),
        "Return 6M": period_return(close, RETURN_PERIODS["6M"]),
        "Return 1Y": period_return(close, RETURN_PERIODS["1Y"]),
        "RSI": calculate_rsi(close),
        "Beta": _first(info, "beta"),
        "Volatility": annualized_volatility(close),
        "Max Drawdown": max_drawdown(close),
        "52-Week Position": price_position_52_week(close),
        "Analyst Target": _first(info, "targetMeanPrice"),
    }


def _percentile_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == 0:
        return pd.Series(50.0, index=series.index)
    ranked = numeric.rank(pct=True, ascending=higher_is_better) * 100
    # For lower-is-better, ascending=False gives the smallest value the highest percentile.
    return ranked.fillna(50.0).clip(0, 100)


def _target_score(series: pd.Series, target: float, width: float) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    score = 100 - ((numeric - target).abs() / width * 100)
    return score.clip(0, 100).fillna(50.0)


def _weighted_score(parts: dict[str, pd.Series], weights: dict[str, float]) -> pd.Series:
    first = next(iter(parts.values()))
    result = pd.Series(0.0, index=first.index)
    for name, values in parts.items():
        result += values * weights[name]
    return result.clip(0, 100)


def add_scores(frame: pd.DataFrame) -> pd.DataFrame:
    """Add category scores, overall score, rating, and rank."""
    if frame.empty:
        return frame.copy()

    validate_config()
    df = frame.copy()

    payout = pd.to_numeric(df["Payout Ratio"], errors="coerce")
    payout_score = _target_score(payout, target=0.55, width=0.55)
    payout_score = payout_score.where(payout <= 1.20, 0)

    dividend_parts = {
        "yield": _percentile_score(df["Dividend Yield"], True),
        "payout_ratio": payout_score,
        "dividend_growth": _percentile_score(df["Dividend Growth 5Y"], True),
        "dividend_consistency": pd.to_numeric(
            df["Dividend Consistency"], errors="coerce"
        ).mul(100).fillna(50).clip(0, 100),
    }
    df["Dividend Score"] = _weighted_score(dividend_parts, DIVIDEND_WEIGHTS)

    quality_parts = {
        "roe": _percentile_score(df["ROE"], True),
        "profit_margin": _percentile_score(df["Profit Margin"], True),
        "free_cash_flow": _percentile_score(df["Free Cash Flow"], True),
        "debt_to_equity": _percentile_score(df["Debt to Equity"], False),
        "earnings_quality": _percentile_score(df["Earnings Growth"], True),
    }
    df["Quality Score"] = _weighted_score(quality_parts, QUALITY_WEIGHTS)

    positive_pe = df["P/E"].where(pd.to_numeric(df["P/E"], errors="coerce") > 0)
    positive_forward_pe = df["Forward P/E"].where(
        pd.to_numeric(df["Forward P/E"], errors="coerce") > 0
    )
    positive_peg = df["PEG"].where(pd.to_numeric(df["PEG"], errors="coerce") > 0)
    positive_pb = df["Price to Book"].where(
        pd.to_numeric(df["Price to Book"], errors="coerce") > 0
    )
    positive_pfcf = df["Price to FCF"].where(
        pd.to_numeric(df["Price to FCF"], errors="coerce") > 0
    )

    value_parts = {
        "pe_ratio": _percentile_score(positive_pe, False),
        "forward_pe": _percentile_score(positive_forward_pe, False),
        "peg_ratio": _percentile_score(positive_peg, False),
        "price_to_book": _percentile_score(positive_pb, False),
        "price_to_fcf": _percentile_score(positive_pfcf, False),
    }
    df["Value Score"] = _weighted_score(value_parts, VALUE_WEIGHTS)

    momentum_parts = {
        "price_vs_sma50": _percentile_score(df["Price vs SMA 50"], True),
        "price_vs_sma200": _percentile_score(df["Price vs SMA 200"], True),
        "six_month_return": _percentile_score(df["Return 6M"], True),
        "one_year_return": _percentile_score(df["Return 1Y"], True),
        "rsi": _target_score(df["RSI"], target=55, width=35),
    }
    df["Momentum Score"] = _weighted_score(momentum_parts, MOMENTUM_WEIGHTS)

    beta_score = _target_score(df["Beta"], target=0.85, width=0.85)
    risk_parts = {
        "beta": beta_score,
        "volatility": _percentile_score(df["Volatility"], False),
        "max_drawdown": _percentile_score(df["Max Drawdown"], True),
        "52_week_position": _target_score(df["52-Week Position"], 0.65, 0.65),
    }
    df["Risk Score"] = _weighted_score(risk_parts, RISK_WEIGHTS)

    overall_parts = {
        "dividend": df["Dividend Score"],
        "quality": df["Quality Score"],
        "value": df["Value Score"],
        "momentum": df["Momentum Score"],
        "risk": df["Risk Score"],
    }
    df["Overall Score"] = _weighted_score(overall_parts, SCORE_WEIGHTS)
    df["Rank"] = df["Overall Score"].rank(method="min", ascending=False).astype(int)
    df["Rating"] = pd.cut(
        df["Overall Score"],
        bins=[-np.inf, 40, 55, 70, 85, np.inf],
        labels=["Weak", "Fair", "Good", "Very Good", "Excellent"],
    ).astype(str)

    score_columns = [
        "Dividend Score",
        "Quality Score",
        "Value Score",
        "Momentum Score",
        "Risk Score",
        "Overall Score",
    ]
    df[score_columns] = df[score_columns].round(1)
    return df.sort_values(["Rank", "Ticker"]).reset_index(drop=True)


def build_dividend_dataframe(
    tickers: list[str],
    histories: dict[str, pd.DataFrame],
    info_cache: dict[str, dict[str, Any]] | None = None,
    dividend_cache: dict[str, pd.Series] | None = None,
    progress_callback: ProgressCallback | None = None,
) -> tuple[pd.DataFrame, dict[str, dict[str, Any]], dict[str, pd.Series]]:
    """Build the complete Dividend Aristocrat analysis table."""
    info_cache = info_cache if info_cache is not None else {}
    dividend_cache = dividend_cache if dividend_cache is not None else {}
    rows: list[dict[str, Any]] = []
    total = len(tickers)

    for index, ticker in enumerate(tickers, start=1):
        if progress_callback is not None:
            progress_callback(index, total, ticker)
        info, dividends = get_ticker_details(ticker, info_cache, dividend_cache)
        rows.append(build_raw_row(ticker, histories.get(ticker), info, dividends))

    return add_scores(pd.DataFrame(rows)), info_cache, dividend_cache


def heatmap_dataframe(dividend_df: pd.DataFrame) -> pd.DataFrame:
    """Return the compact dataset used by the future heatmap page."""
    columns = [
        "Ticker",
        "Company",
        "Sector",
        "Price",
        "Dividend Yield",
        "Return 1Y",
        "Dividend Score",
        "Quality Score",
        "Value Score",
        "Momentum Score",
        "Risk Score",
        "Overall Score",
        "Rank",
    ]
    available = [column for column in columns if column in dividend_df.columns]
    return dividend_df[available].copy()

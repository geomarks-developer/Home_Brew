"""
MarketScope Growth market-data loader.

Responsibilities:
- Download adjusted daily price history in one batch.
- Retrieve company fundamentals and analyst growth estimates per ticker.
- Calculate 6-month and 12-month returns, moving averages, and 52-week high.
- Cache the normalized, scored DataFrame locally.
- Pass normalized data to growth_engine.score_dataframe().

Yahoo/yfinance data may be missing for individual securities. Missing values are
kept as NaN so the scoring engine can reweight around unavailable metrics.
"""

from __future__ import annotations

import os
import pickle
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import numpy as np
import pandas as pd
import yfinance as yf

from config import (
    CACHE_FILE,
    CACHE_MAX_AGE_HOURS,
    GROWTH_TICKERS,
    INFO_FIELDS,
    MA_LONG,
    MA_SHORT,
    MIN_MARKET_CAP,
    PRICE_HISTORY_PERIOD,
)
from growth_engine import score_dataframe


CACHE_SCHEMA_VERSION = 1
DEFAULT_BATCH_SIZE = 50
DEFAULT_PAUSE_SECONDS = 0.20


# =========================================================
# Generic helpers
# =========================================================


def _safe_float(value: Any) -> float:
    """Return a finite float or NaN."""
    if value is None:
        return np.nan
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def _clean_tickers(tickers: Iterable[str] | None) -> list[str]:
    """Normalize symbols and remove duplicates while preserving order."""
    source = GROWTH_TICKERS if tickers is None else tickers
    cleaned: list[str] = []
    seen: set[str] = set()

    for ticker in source:
        symbol = str(ticker).strip().upper()
        if symbol and symbol not in seen:
            cleaned.append(symbol)
            seen.add(symbol)

    return cleaned


def _chunks(values: list[str], size: int) -> Iterable[list[str]]:
    """Yield fixed-size slices from a list."""
    size = max(1, int(size))
    for start in range(0, len(values), size):
        yield values[start : start + size]


def _notify(callback: Callable[[int, int, str], None] | None,
            completed: int, total: int, message: str) -> None:
    """Send progress updates without requiring Streamlit in this module."""
    if callback is not None:
        callback(completed, total, message)


# =========================================================
# Cache management
# =========================================================


def cache_path() -> Path:
    """Return the configured cache path relative to the project folder."""
    path = Path(CACHE_FILE)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent / path
    return path


def cache_age_hours(path: Path | None = None) -> float | None:
    """Return cache age in hours, or None when no cache exists."""
    path = path or cache_path()
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - modified).total_seconds() / 3600.0


def is_cache_fresh(max_age_hours: float = CACHE_MAX_AGE_HOURS,
                   path: Path | None = None) -> bool:
    """Return True when the cache exists and is within the allowed age."""
    age = cache_age_hours(path)
    return age is not None and age <= float(max_age_hours)


def load_cache(path: Path | None = None) -> pd.DataFrame | None:
    """Load a valid cache payload; return None for incompatible/corrupt data."""
    path = path or cache_path()
    if not path.exists():
        return None

    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, EOFError, pickle.UnpicklingError, AttributeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None

    data = payload.get("data")
    return data.copy() if isinstance(data, pd.DataFrame) else None


def save_cache(data: pd.DataFrame, path: Path | None = None) -> Path:
    """Write the cache atomically to reduce the chance of partial files."""
    path = path or cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "data": data.copy(),
    }

    with tempfile.NamedTemporaryFile(
        mode="wb", delete=False, dir=path.parent, prefix=path.name, suffix=".tmp"
    ) as temporary:
        pickle.dump(payload, temporary, protocol=pickle.HIGHEST_PROTOCOL)
        temporary_path = Path(temporary.name)

    os.replace(temporary_path, path)
    return path


def clear_cache(path: Path | None = None) -> bool:
    """Delete the cache file and report whether a file was removed."""
    path = path or cache_path()
    if path.exists():
        path.unlink()
        return True
    return False


# =========================================================
# Price history
# =========================================================


def download_price_history(
    tickers: Iterable[str] | None = None,
    period: str = PRICE_HISTORY_PERIOD,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> pd.DataFrame:
    """Download adjusted daily history for all requested symbols."""
    symbols = _clean_tickers(tickers)
    if not symbols:
        return pd.DataFrame()

    frames: list[pd.DataFrame] = []

    for batch in _chunks(symbols, batch_size):
        try:
            history = yf.download(
                tickers=batch,
                period=period,
                interval="1d",
                auto_adjust=True,
                actions=False,
                progress=False,
                group_by="column",
                threads=True,
            )
        except Exception:
            continue

        if history is not None and not history.empty:
            frames.append(history)

    if not frames:
        return pd.DataFrame()

    if len(frames) == 1:
        return frames[0].sort_index()

    # Multiple batches produce compatible MultiIndex column blocks.
    combined = pd.concat(frames, axis=1)
    combined = combined.loc[:, ~combined.columns.duplicated()]
    return combined.sort_index()


def _close_series(history: pd.DataFrame, ticker: str, ticker_count: int) -> pd.Series:
    """Extract one ticker's adjusted Close series from yfinance output."""
    if history is None or history.empty:
        return pd.Series(dtype=float)

    close: pd.Series | pd.DataFrame

    if isinstance(history.columns, pd.MultiIndex):
        level_zero = set(history.columns.get_level_values(0))
        level_one = set(history.columns.get_level_values(1))

        if "Close" in level_zero:
            close_block = history["Close"]
            if isinstance(close_block, pd.Series):
                close = close_block
            elif ticker in close_block.columns:
                close = close_block[ticker]
            else:
                return pd.Series(dtype=float)
        elif "Close" in level_one:
            try:
                close = history[ticker]["Close"]
            except (KeyError, TypeError):
                return pd.Series(dtype=float)
        else:
            return pd.Series(dtype=float)
    else:
        if "Close" not in history.columns:
            return pd.Series(dtype=float)
        close = history["Close"]

    if isinstance(close, pd.DataFrame):
        if ticker in close.columns:
            close = close[ticker]
        elif ticker_count == 1 and close.shape[1] == 1:
            close = close.iloc[:, 0]
        else:
            return pd.Series(dtype=float)

    return pd.to_numeric(close, errors="coerce").dropna()


def calculate_price_metrics(close: pd.Series) -> dict[str, float]:
    """Calculate current price, returns, moving averages, and 52-week high."""
    close = pd.to_numeric(close, errors="coerce").dropna()
    if close.empty:
        return {
            "Price": np.nan,
            "6M Return": np.nan,
            "12M Return": np.nan,
            "50D MA": np.nan,
            "200D MA": np.nan,
            "52W High": np.nan,
        }

    price = float(close.iloc[-1])

    # Trading-day approximations: 126 sessions ~= 6 months; 252 ~= 12 months.
    return_6m = price / float(close.iloc[-127]) - 1.0 if len(close) >= 127 else np.nan
    return_12m = price / float(close.iloc[-253]) - 1.0 if len(close) >= 253 else np.nan
    ma_50 = float(close.tail(MA_SHORT).mean()) if len(close) >= MA_SHORT else np.nan
    ma_200 = float(close.tail(MA_LONG).mean()) if len(close) >= MA_LONG else np.nan
    high_52w = float(close.tail(252).max()) if len(close) >= 1 else np.nan

    return {
        "Price": price,
        "6M Return": return_6m,
        "12M Return": return_12m,
        "50D MA": ma_50,
        "200D MA": ma_200,
        "52W High": high_52w,
    }


# =========================================================
# Fundamental and growth estimate retrieval
# =========================================================


def _safe_info(stock: yf.Ticker) -> dict[str, Any]:
    """Retrieve the info dictionary without allowing one failure to stop a run."""
    try:
        info = stock.get_info()
    except Exception:
        try:
            info = stock.info
        except Exception:
            return {}
    return info if isinstance(info, dict) else {}


def _safe_dataframe(attribute: Any) -> pd.DataFrame:
    """Coerce a yfinance analyst-data attribute to a DataFrame."""
    try:
        value = attribute() if callable(attribute) else attribute
    except Exception:
        return pd.DataFrame()
    return value.copy() if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _index_row(frame: pd.DataFrame, candidates: Iterable[str]) -> pd.Series | None:
    """Find an analyst-estimate row using tolerant text matching."""
    if frame is None or frame.empty:
        return None

    normalized = {str(index).strip().lower(): index for index in frame.index}
    for candidate in candidates:
        match = normalized.get(candidate.strip().lower())
        if match is not None:
            row = frame.loc[match]
            return row.iloc[0] if isinstance(row, pd.DataFrame) else row
    return None


def _row_value(row: pd.Series | None, candidates: Iterable[str]) -> float:
    """Read the first usable value from a row using case-insensitive columns."""
    if row is None:
        return np.nan

    normalized = {str(column).strip().lower(): column for column in row.index}
    for candidate in candidates:
        column = normalized.get(candidate.strip().lower())
        if column is not None:
            value = _safe_float(row[column])
            if not np.isnan(value):
                return value
    return np.nan


def _forward_eps_growth(stock: yf.Ticker, info: dict[str, Any]) -> float:
    """Get next-year EPS growth, preferring analyst estimates when available."""
    estimates = _safe_dataframe(getattr(stock, "earnings_estimate", None))
    next_year = _index_row(estimates, ["+1y", "1y", "next year"])
    growth = _row_value(next_year, ["growth"])

    if not np.isnan(growth):
        return growth

    for key in ("earningsQuarterlyGrowth", "earningsGrowth"):
        fallback = _safe_float(info.get(key))
        if not np.isnan(fallback):
            return fallback

    return np.nan


def _eps_growth(info: dict[str, Any]) -> float:
    """Retrieve a usable recent EPS growth proxy from the info dictionary."""
    for key in ("earningsQuarterlyGrowth", "earningsGrowth"):
        value = _safe_float(info.get(key))
        if not np.isnan(value):
            return value
    return np.nan


def fetch_fundamentals(ticker: str) -> dict[str, Any]:
    """Retrieve and normalize one company's fundamental data."""
    stock = yf.Ticker(ticker)
    info = _safe_info(stock)

    record: dict[str, Any] = {"Ticker": ticker}
    for source_name, target_name in INFO_FIELDS.items():
        record[target_name] = info.get(source_name, np.nan)

    # Identity fallbacks
    record["Company"] = info.get("longName") or info.get("shortName") or ticker
    record["Sector"] = info.get("sector") or "Unknown"
    record["Industry"] = info.get("industry") or "Unknown"

    # Growth fields not fully covered by config.INFO_FIELDS
    record["EPS Growth"] = _eps_growth(info)
    record["Forward EPS Growth"] = _forward_eps_growth(stock, info)

    return record


# =========================================================
# Combined dataset
# =========================================================


def build_market_data(
    tickers: Iterable[str] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
    pause_seconds: float = DEFAULT_PAUSE_SECONDS,
    include_below_min_market_cap: bool = False,
) -> pd.DataFrame:
    """Download, normalize, filter, and score the MarketScope Growth universe."""
    symbols = _clean_tickers(tickers)
    if not symbols:
        return pd.DataFrame()

    _notify(progress_callback, 0, len(symbols), "Downloading price history")
    history = download_price_history(symbols)

    records: list[dict[str, Any]] = []

    for position, ticker in enumerate(symbols, start=1):
        _notify(progress_callback, position - 1, len(symbols), f"Loading {ticker}")

        try:
            record = fetch_fundamentals(ticker)
        except Exception:
            record = {
                "Ticker": ticker,
                "Company": ticker,
                "Sector": "Unknown",
                "Industry": "Unknown",
            }

        close = _close_series(history, ticker, len(symbols))
        price_metrics = calculate_price_metrics(close)

        # Prefer batch price-history calculations over possibly stale info values.
        for column, value in price_metrics.items():
            if not np.isnan(_safe_float(value)):
                record[column] = value
            else:
                record.setdefault(column, np.nan)

        records.append(record)
        _notify(progress_callback, position, len(symbols), f"Loaded {ticker}")

        if pause_seconds > 0 and position < len(symbols):
            time.sleep(pause_seconds)

    data = pd.DataFrame(records)

    if not include_below_min_market_cap and "Market Cap" in data.columns:
        market_cap = pd.to_numeric(data["Market Cap"], errors="coerce")
        data = data.loc[market_cap.isna() | (market_cap >= MIN_MARKET_CAP)].copy()

    return score_dataframe(data)


def load_market_data(
    tickers: Iterable[str] | None = None,
    force_refresh: bool = False,
    allow_stale_on_error: bool = True,
    progress_callback: Callable[[int, int, str], None] | None = None,
    include_below_min_market_cap: bool = False,
) -> pd.DataFrame:
    """
    Return cached scored data when fresh; otherwise rebuild and cache it.

    Custom ticker lists bypass the shared cache to prevent mixing universes.
    """
    symbols = _clean_tickers(tickers)
    uses_default_universe = tickers is None or symbols == _clean_tickers(None)

    if uses_default_universe and not force_refresh and is_cache_fresh():
        cached = load_cache()
        if cached is not None:
            return cached

    stale_cache = load_cache() if uses_default_universe else None

    try:
        data = build_market_data(
            tickers=symbols,
            progress_callback=progress_callback,
            include_below_min_market_cap=include_below_min_market_cap,
        )
    except Exception:
        if allow_stale_on_error and stale_cache is not None:
            return stale_cache
        raise

    if data.empty and allow_stale_on_error and stale_cache is not None:
        return stale_cache

    if uses_default_universe and not data.empty:
        save_cache(data)

    return data


# Backward-friendly aliases for page modules
get_market_data = load_market_data
refresh_market_data = lambda **kwargs: load_market_data(force_refresh=True, **kwargs)


if __name__ == "__main__":
    def print_progress(done: int, total: int, message: str) -> None:
        print(f"[{done:>3}/{total:<3}] {message}")

    frame = load_market_data(progress_callback=print_progress)
    print(f"\nLoaded {len(frame)} stocks.")

    preview_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Growth Score",
            "Quality Score",
            "Valuation Score",
            "Momentum Score",
            "Overall Score",
            "Overall Coverage",
            "Rating",
        )
        if column in frame.columns
    ]
    print(frame[preview_columns].head(15).to_string(index=False))

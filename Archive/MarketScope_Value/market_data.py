"""MarketScope Value market-data loading, enrichment, scoring, and caching."""
from __future__ import annotations

import os
import pickle
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

from config import (
    CACHE_FILE,
    CACHE_MAX_AGE_HOURS,
    INFO_FIELDS,
    MA_LONG,
    MA_SHORT,
    PRICE_HISTORY_PERIOD,
    PRICE_INTERVAL,
    VALUE_TICKERS,
)
from value_engine import score_dataframe


CACHE_SCHEMA_VERSION = 1


# =========================================================
# General helpers
# =========================================================

def normalize_tickers(tickers: Iterable[str] | None = None) -> tuple[str, ...]:
    """Return uppercase, unique ticker symbols while preserving order."""
    source = VALUE_TICKERS if tickers is None else tickers
    cleaned: list[str] = []
    seen: set[str] = set()

    for ticker in source:
        symbol = str(ticker).strip().upper()
        if symbol and symbol not in seen:
            cleaned.append(symbol)
            seen.add(symbol)

    return tuple(cleaned)


def safe_float(value: Any) -> float:
    """Return a finite float or NaN."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def cache_path() -> Path:
    """Return the project-level persistent cache path."""
    return Path(__file__).resolve().parent / CACHE_FILE


def cache_age_hours(path: Path | None = None) -> float | None:
    path = path or cache_path()
    if not path.exists():
        return None

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - modified).total_seconds() / 3600


def cache_is_fresh(
    max_age_hours: float = CACHE_MAX_AGE_HOURS,
    path: Path | None = None,
) -> bool:
    age = cache_age_hours(path)
    return age is not None and age <= max_age_hours


def clear_market_cache(path: Path | None = None) -> bool:
    """Delete the persistent MarketScope Value cache if present."""
    path = path or cache_path()
    if path.exists():
        path.unlink()
        return True
    return False


# =========================================================
# Persistent cache
# =========================================================

def load_cache(path: Path | None = None) -> dict[str, Any] | None:
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
    if not isinstance(payload.get("data"), pd.DataFrame):
        return None

    result = payload.copy()
    result["data"] = result["data"].copy()
    result["histories"] = {
        str(ticker): history.copy()
        for ticker, history in result.get("histories", {}).items()
        if isinstance(history, pd.DataFrame)
    }
    return result


def save_cache(
    data: pd.DataFrame,
    histories: dict[str, pd.DataFrame],
    tickers: tuple[str, ...],
    metadata: dict[str, Any],
    path: Path | None = None,
) -> Path:
    """Write the persistent cache atomically."""
    path = path or cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "tickers": tickers,
        "data": data.copy(),
        "histories": {ticker: frame.copy() for ticker, frame in histories.items()},
        "metadata": dict(metadata),
    }

    with tempfile.NamedTemporaryFile(
        mode="wb",
        delete=False,
        dir=path.parent,
        prefix=path.name,
        suffix=".tmp",
    ) as temporary:
        pickle.dump(payload, temporary, protocol=pickle.HIGHEST_PROTOCOL)
        temporary_path = Path(temporary.name)

    os.replace(temporary_path, path)
    return path


# =========================================================
# Historical-price retrieval and technical metrics
# =========================================================

def download_histories(tickers: tuple[str, ...]) -> dict[str, pd.DataFrame]:
    """Download adjusted daily histories for all configured tickers."""
    if not tickers:
        return {}

    raw = yf.download(
        tickers=list(tickers),
        period=PRICE_HISTORY_PERIOD,
        interval=PRICE_INTERVAL,
        auto_adjust=False,
        actions=False,
        group_by="column",
        threads=True,
        progress=False,
    )

    histories: dict[str, pd.DataFrame] = {}
    if raw is None or raw.empty:
        return histories

    if isinstance(raw.columns, pd.MultiIndex):
        level_zero = set(raw.columns.get_level_values(0))
        level_one = set(raw.columns.get_level_values(1))

        for ticker in tickers:
            try:
                if ticker in level_one:
                    frame = raw.xs(ticker, axis=1, level=1, drop_level=True)
                elif ticker in level_zero:
                    frame = raw.xs(ticker, axis=1, level=0, drop_level=True)
                else:
                    continue
            except (KeyError, TypeError):
                continue

            frame = frame.dropna(how="all")
            if not frame.empty:
                histories[ticker] = frame.copy()
    elif len(tickers) == 1:
        frame = raw.dropna(how="all")
        if not frame.empty:
            histories[tickers[0]] = frame.copy()

    return histories


def close_series(history: pd.DataFrame | None) -> pd.Series:
    if history is None or history.empty:
        return pd.Series(dtype=float)

    column = "Adj Close" if "Adj Close" in history.columns else "Close"
    if column not in history.columns:
        return pd.Series(dtype=float)

    values = pd.to_numeric(history[column], errors="coerce").dropna()
    if not values.empty and not isinstance(values.index, pd.DatetimeIndex):
        values.index = pd.to_datetime(values.index, errors="coerce")
        values = values[~values.index.isna()]

    return values.sort_index()


def trailing_return(prices: pd.Series, sessions: int) -> float:
    """Calculate a trailing return using the closest available trading session."""
    if prices.empty or len(prices) <= sessions:
        return np.nan

    latest = safe_float(prices.iloc[-1])
    prior = safe_float(prices.iloc[-(sessions + 1)])
    if np.isnan(latest) or np.isnan(prior) or prior <= 0:
        return np.nan
    return latest / prior - 1.0


def technical_metrics(history: pd.DataFrame | None) -> dict[str, float]:
    prices = close_series(history)
    if prices.empty:
        return {
            "Price": np.nan,
            "6M Return": np.nan,
            "12M Return": np.nan,
            "50D MA": np.nan,
            "200D MA": np.nan,
            "52W High": np.nan,
            "52W Low": np.nan,
        }

    return {
        "Price": safe_float(prices.iloc[-1]),
        "6M Return": trailing_return(prices, 126),
        "12M Return": trailing_return(prices, 252),
        "50D MA": safe_float(prices.tail(MA_SHORT).mean()) if len(prices) >= MA_SHORT else np.nan,
        "200D MA": safe_float(prices.tail(MA_LONG).mean()) if len(prices) >= MA_LONG else np.nan,
        "52W High": safe_float(prices.tail(252).max()),
        "52W Low": safe_float(prices.tail(252).min()),
    }


# =========================================================
# Fundamental retrieval
# =========================================================

def info_record(ticker: str) -> dict[str, Any]:
    """Fetch and normalize yfinance info for one ticker."""
    security = yf.Ticker(ticker)

    try:
        info = security.info or {}
    except Exception:
        info = {}

    record: dict[str, Any] = {"Ticker": ticker}
    for source, destination in INFO_FIELDS.items():
        record[destination] = info.get(source)

    if not record.get("Company"):
        record["Company"] = info.get("shortName") or ticker
    if not record.get("Sector"):
        record["Sector"] = "Unknown"
    if not record.get("Industry"):
        record["Industry"] = "Unknown"

    # yfinance growth estimates are optional and may vary by symbol.
    try:
        growth = security.growth_estimates
    except Exception:
        growth = None

    record["Forward EPS Growth"] = extract_forward_eps_growth(growth)
    return record


def extract_forward_eps_growth(growth: pd.DataFrame | None) -> float:
    """Extract a forward stock EPS growth estimate when yfinance provides one."""
    if growth is None or growth.empty:
        return np.nan

    frame = growth.copy()
    preferred_rows = ("+1y", "Next Year", "1y", "0y")
    preferred_columns = (
        "stockTrend",
        "Stock Trend",
        "stockGrowth",
        "Stock Growth",
    )

    for row in preferred_rows:
        if row not in frame.index:
            continue
        for column in preferred_columns:
            if column in frame.columns:
                value = safe_float(frame.loc[row, column])
                if not np.isnan(value):
                    return value

    for column in preferred_columns:
        if column in frame.columns:
            values = pd.to_numeric(frame[column], errors="coerce").dropna()
            if not values.empty:
                return safe_float(values.iloc[0])

    return np.nan


def build_fundamental_records(
    tickers: tuple[str, ...],
    progress: Any | None = None,
) -> list[dict[str, Any]]:
    """Fetch normalized fundamental records, continuing past individual failures."""
    records: list[dict[str, Any]] = []
    total = max(len(tickers), 1)

    for position, ticker in enumerate(tickers, start=1):
        if progress is not None:
            progress.progress(
                20 + int(position / total * 55),
                text=f"Loading fundamentals: {ticker} ({position}/{len(tickers)})",
            )

        try:
            record = info_record(ticker)
        except Exception:
            record = {
                "Ticker": ticker,
                "Company": ticker,
                "Sector": "Unknown",
                "Industry": "Unknown",
            }

        records.append(record)

    return records


# =========================================================
# Dataset construction
# =========================================================

def build_market_data(
    tickers: Iterable[str] | None = None,
    progress: Any | None = None,
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame], dict[str, Any]]:
    """Download, enrich, score, and rank the MarketScope Value universe."""
    normalized_tickers = normalize_tickers(tickers)
    if not normalized_tickers:
        return pd.DataFrame(), {}, {
            "ticker_count": 0,
            "history_count": 0,
            "record_count": 0,
            "failed_tickers": [],
        }

    if progress is not None:
        progress.progress(5, text="Downloading value-universe price history...")

    histories = download_histories(normalized_tickers)

    if progress is not None:
        progress.progress(20, text="Loading company fundamentals...")

    records = build_fundamental_records(normalized_tickers, progress=progress)

    if progress is not None:
        progress.progress(80, text="Calculating technical metrics...")

    rows: list[dict[str, Any]] = []
    for record in records:
        ticker = str(record.get("Ticker", "")).upper()
        row = dict(record)
        technical = technical_metrics(histories.get(ticker))

        # Prefer the latest adjusted market price when available.
        for key, value in technical.items():
            if key == "Price" and np.isnan(safe_float(value)):
                continue
            row[key] = value

        rows.append(row)

    raw_data = pd.DataFrame(rows)
    if raw_data.empty:
        scored_data = raw_data.copy()
    else:
        if progress is not None:
            progress.progress(90, text="Scoring value and value-trap factors...")
        scored_data = score_dataframe(raw_data)

    # Add a stable rank after scoring.
    if not scored_data.empty:
        scored_data.insert(0, "Rank", range(1, len(scored_data) + 1))

    failed_tickers = [ticker for ticker in normalized_tickers if ticker not in histories]
    metadata = {
        "ticker_count": len(normalized_tickers),
        "history_count": len(histories),
        "record_count": len(scored_data),
        "failed_tickers": failed_tickers,
        "last_refresh_utc": datetime.now(timezone.utc).isoformat(),
        "price_history_period": PRICE_HISTORY_PERIOD,
        "price_interval": PRICE_INTERVAL,
    }

    if progress is not None:
        progress.progress(100, text="MarketScope Value data is ready.")

    return scored_data, histories, metadata


# =========================================================
# Public loader
# =========================================================

def load_market_bundle(
    force_refresh: bool = False,
    tickers: Iterable[str] | None = None,
    show_progress: bool = False,
    allow_stale_on_error: bool = True,
) -> dict[str, Any]:
    """Return scored data, histories, and metadata from cache or a fresh build."""
    normalized_tickers = normalize_tickers(tickers)
    cached = load_cache()
    cache_matches = cached is not None and tuple(cached.get("tickers", ())) == normalized_tickers

    if not force_refresh and cache_matches and cache_is_fresh():
        metadata = dict(cached.get("metadata", {}))
        metadata.update(
            {
                "loaded_from": "cache",
                "cache_age_hours": cache_age_hours(),
                "stale": False,
            }
        )
        return {
            "data": cached["data"].copy(),
            "histories": cached.get("histories", {}),
            "metadata": metadata,
        }

    progress = None
    if show_progress:
        progress = st.progress(0, text="Preparing MarketScope Value data...")

    try:
        data, histories, metadata = build_market_data(
            tickers=normalized_tickers,
            progress=progress,
        )
        save_cache(data, histories, normalized_tickers, metadata)
        metadata = {
            **metadata,
            "loaded_from": "Yahoo Finance refresh",
            "cache_age_hours": cache_age_hours(),
            "stale": False,
        }
        return {
            "data": data,
            "histories": histories,
            "metadata": metadata,
        }
    except Exception:
        if allow_stale_on_error and cached is not None:
            metadata = dict(cached.get("metadata", {}))
            metadata.update(
                {
                    "loaded_from": "stale cache",
                    "cache_age_hours": cache_age_hours(),
                    "stale": True,
                }
            )
            return {
                "data": cached["data"].copy(),
                "histories": cached.get("histories", {}),
                "metadata": metadata,
            }
        raise
    finally:
        if progress is not None:
            progress.empty()


def load_market_data(
    force_refresh: bool = False,
    tickers: Iterable[str] | None = None,
    show_progress: bool = False,
) -> pd.DataFrame:
    """Return the scored MarketScope Value DataFrame used by most pages."""
    return load_market_bundle(
        force_refresh=force_refresh,
        tickers=tickers,
        show_progress=show_progress,
    )["data"]


def load_price_histories(
    force_refresh: bool = False,
    tickers: Iterable[str] | None = None,
    show_progress: bool = False,
) -> dict[str, pd.DataFrame]:
    """Return cached or refreshed price histories for charts and comparisons."""
    return load_market_bundle(
        force_refresh=force_refresh,
        tickers=tickers,
        show_progress=show_progress,
    )["histories"]


def get_market_metadata(
    force_refresh: bool = False,
    tickers: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Return current market-data metadata."""
    return load_market_bundle(
        force_refresh=force_refresh,
        tickers=tickers,
        show_progress=False,
    )["metadata"]


# Friendly aliases for page modules.
get_market_data = load_market_bundle
refresh_market_data = lambda: load_market_bundle(force_refresh=True, show_progress=True)


if __name__ == "__main__":
    print("Configured tickers:", len(normalize_tickers()))
    print("Cache path:", cache_path())

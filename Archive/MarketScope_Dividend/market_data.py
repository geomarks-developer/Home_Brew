from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pickle
import time
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

from config import (
    CACHE_FILE,
    DOWNLOAD_BATCH_SIZE,
    HISTORY_INTERVAL,
    HISTORY_PERIOD,
    TICKER_FILE,
    load_dividend_tickers,
)
from dividend_engine import build_dividend_dataframe, heatmap_dataframe


# =========================================================
# CACHE HELPERS
# =========================================================


def _empty_cache() -> tuple[
    dict[str, pd.DataFrame],
    dict[str, dict[str, Any]],
    dict[str, pd.Series],
]:
    return {}, {}, {}


def _load_pickle(
    path: Path,
) -> tuple[
    dict[str, pd.DataFrame],
    dict[str, dict[str, Any]],
    dict[str, pd.Series],
]:
    if not path.exists():
        return _empty_cache()

    try:
        with path.open("rb") as file:
            data = pickle.load(file)

        if not isinstance(data, dict):
            return _empty_cache()

        return (
            data.get("histories", {}),
            data.get("info_cache", {}),
            data.get("dividend_cache", {}),
        )

    except (
        OSError,
        EOFError,
        pickle.PickleError,
        AttributeError,
        TypeError,
        ValueError,
    ):
        return _empty_cache()


def _save_pickle(
    path: Path,
    histories: dict[str, pd.DataFrame],
    info_cache: dict[str, dict[str, Any]],
    dividend_cache: dict[str, pd.Series],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    temporary_path = path.with_suffix(path.suffix + ".tmp")

    with temporary_path.open("wb") as file:
        pickle.dump(
            {
                "histories": histories,
                "info_cache": info_cache,
                "dividend_cache": dividend_cache,
            },
            file,
            protocol=pickle.HIGHEST_PROTOCOL,
        )

    temporary_path.replace(path)


# =========================================================
# PROGRESS HELPERS
# =========================================================


def _update_progress(progress, value: int, text: str) -> None:
    if progress is not None:
        progress.progress(
            min(max(int(value), 0), 100),
            text=text,
        )


# =========================================================
# PRICE-HISTORY DOWNLOADS
# =========================================================


def _normalize_history(frame: pd.DataFrame | None) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame()

    result = frame.copy()
    result = result.dropna(how="all")

    if isinstance(result.index, pd.DatetimeIndex):
        try:
            if result.index.tz is not None:
                result.index = result.index.tz_convert(None)
        except (TypeError, AttributeError):
            pass

    return result


def _split_download(
    downloaded: pd.DataFrame,
    tickers: list[str],
) -> dict[str, pd.DataFrame]:
    """Convert a yfinance batch download into one DataFrame per ticker."""
    histories: dict[str, pd.DataFrame] = {}

    if downloaded is None or downloaded.empty:
        return {ticker: pd.DataFrame() for ticker in tickers}

    if len(tickers) == 1:
        ticker = tickers[0]

        if isinstance(downloaded.columns, pd.MultiIndex):
            level_zero = downloaded.columns.get_level_values(0)
            level_one = downloaded.columns.get_level_values(1)

            if ticker in level_zero:
                frame = downloaded[ticker]
            elif ticker in level_one:
                frame = downloaded.xs(ticker, axis=1, level=1)
            else:
                frame = downloaded
        else:
            frame = downloaded

        histories[ticker] = _normalize_history(frame)
        return histories

    for ticker in tickers:
        frame = pd.DataFrame()

        if isinstance(downloaded.columns, pd.MultiIndex):
            level_zero = downloaded.columns.get_level_values(0)
            level_one = downloaded.columns.get_level_values(1)

            try:
                if ticker in level_zero:
                    frame = downloaded[ticker]
                elif ticker in level_one:
                    frame = downloaded.xs(ticker, axis=1, level=1)
            except (KeyError, ValueError):
                frame = pd.DataFrame()

        histories[ticker] = _normalize_history(frame)

    return histories


def download_histories(
    tickers: list[str],
    progress=None,
    start_percent: int = 5,
    end_percent: int = 45,
) -> dict[str, pd.DataFrame]:
    """Download price history in batches with meaningful progress updates."""
    unique_tickers = list(dict.fromkeys(ticker.upper() for ticker in tickers))

    if not unique_tickers:
        return {}

    histories: dict[str, pd.DataFrame] = {}
    total = len(unique_tickers)
    batch_size = max(int(DOWNLOAD_BATCH_SIZE), 1)

    for batch_start in range(0, total, batch_size):
        batch = unique_tickers[batch_start:batch_start + batch_size]
        batch_end = batch_start + len(batch)

        percent_before = start_percent + int(
            (batch_start / total) * (end_percent - start_percent)
        )

        _update_progress(
            progress,
            percent_before,
            (
                f"Downloading price history: "
                f"{batch_start + 1}-{batch_end} of {total} tickers..."
            ),
        )

        try:
            downloaded = yf.download(
                tickers=batch,
                period=HISTORY_PERIOD,
                interval=HISTORY_INTERVAL,
                group_by="ticker",
                auto_adjust=False,
                actions=False,
                progress=False,
                threads=True,
            )
            histories.update(_split_download(downloaded, batch))

        except Exception:
            for ticker in batch:
                histories[ticker] = pd.DataFrame()

        percent_after = start_percent + int(
            (batch_end / total) * (end_percent - start_percent)
        )

        _update_progress(
            progress,
            percent_after,
            f"Downloaded price history for {batch_end} of {total} tickers.",
        )

    return histories


# =========================================================
# MARKET-DATA BUILD
# =========================================================


@st.cache_data(show_spinner=False)
def _build_market_data(
    ticker_file_string: str,
    cache_file_string: str,
    ticker_file_mtime: float,
    cache_file_mtime: float,
    refresh_generation: int,
    force_refresh: bool,
    _progress=None,
) -> dict[str, Any]:
    """
    Build the shared MarketScope Dividend dataset.

    Parameters beginning with an underscore are excluded from Streamlit's
    cache key. This lets the UI progress object be passed safely.
    """
    ticker_file = Path(ticker_file_string)
    cache_file = Path(cache_file_string)

    _update_progress(_progress, 2, "Reading Dividend Aristocrat ticker list...")

    if not ticker_file.exists():
        raise FileNotFoundError(
            f"Dividend ticker file not found: {ticker_file}"
        )

    tickers = load_dividend_tickers()

    if not tickers:
        raise ValueError("The Dividend Aristocrat ticker list is empty.")

    _update_progress(
        _progress,
        5,
        f"Loaded {len(tickers)} Dividend Aristocrat tickers.",
    )

    histories, info_cache, dividend_cache = _load_pickle(cache_file)

    if force_refresh:
        histories = {}
        info_cache = {}
        dividend_cache = {}
        tickers_to_download = tickers

        _update_progress(
            _progress,
            6,
            "Refreshing all Dividend Aristocrat market data...",
        )

    else:
        tickers_to_download = [
            ticker
            for ticker in tickers
            if (
                ticker not in histories
                or histories[ticker] is None
                or histories[ticker].empty
            )
        ]

    if tickers_to_download:
        new_histories = download_histories(
            tickers_to_download,
            progress=_progress,
            start_percent=6,
            end_percent=45,
        )
        histories.update(new_histories)
    else:
        _update_progress(
            _progress,
            45,
            f"Price history loaded from cache for {len(tickers)} tickers.",
        )

    # Remove obsolete symbols if the ticker text file was edited.
    current_ticker_set = set(tickers)
    histories = {
        ticker: history
        for ticker, history in histories.items()
        if ticker in current_ticker_set
    }
    info_cache = {
        ticker: info
        for ticker, info in info_cache.items()
        if ticker in current_ticker_set
    }
    dividend_cache = {
        ticker: dividends
        for ticker, dividends in dividend_cache.items()
        if ticker in current_ticker_set
    }

    def analysis_progress(index: int, total: int, ticker: str) -> None:
        percent = 45 + int((index / max(total, 1)) * 45)
        _update_progress(
            _progress,
            percent,
            f"Analyzing {ticker}: {index} of {total} stocks...",
        )

    _update_progress(
        _progress,
        46,
        "Calculating dividend, quality, value, momentum, and risk metrics...",
    )

    dividend_df, info_cache, dividend_cache = build_dividend_dataframe(
        tickers=tickers,
        histories=histories,
        info_cache=info_cache,
        dividend_cache=dividend_cache,
        progress_callback=analysis_progress,
    )

    _update_progress(_progress, 92, "Building dividend heatmap dataset...")
    heatmap_df = heatmap_dataframe(dividend_df)

    _update_progress(_progress, 96, "Saving MarketScope Dividend cache...")
    _save_pickle(
        cache_file,
        histories,
        info_cache,
        dividend_cache,
    )

    successful_histories = sum(
        1
        for ticker in tickers
        if ticker in histories
        and histories[ticker] is not None
        and not histories[ticker].empty
    )

    _update_progress(_progress, 99, "Preparing shared application data...")

    return {
        "tickers": tickers,
        "histories": histories,
        "info_cache": info_cache,
        "dividend_cache": dividend_cache,
        "dividend_df": dividend_df,
        "heatmap_df": heatmap_df,
        "ticker_count": len(tickers),
        "successful_history_count": successful_histories,
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
    }


# =========================================================
# PUBLIC API
# =========================================================


def get_market_data(
    force_refresh: bool = False,
    show_progress: bool = False,
) -> dict[str, Any]:
    """Return shared MarketScope Dividend data for all application pages."""
    if not TICKER_FILE.exists():
        raise FileNotFoundError(
            f"Dividend ticker file not found: {TICKER_FILE}"
        )

    st.session_state.setdefault(
        "dividend_data_refresh_generation",
        0,
    )

    if force_refresh:
        st.session_state.dividend_data_refresh_generation += 1

    progress = None

    if show_progress:
        progress = st.progress(
            0,
            text="Starting MarketScope Dividend data load...",
        )

    cache_mtime = (
        CACHE_FILE.stat().st_mtime
        if CACHE_FILE.exists()
        else 0.0
    )

    try:
        data = _build_market_data(
            str(TICKER_FILE),
            str(CACHE_FILE),
            TICKER_FILE.stat().st_mtime,
            cache_mtime,
            st.session_state.dividend_data_refresh_generation,
            force_refresh,
            _progress=progress,
        )

        if progress is not None:
            progress.progress(
                100,
                text="MarketScope Dividend data ready.",
            )
            time.sleep(0.4)

        return data

    finally:
        if progress is not None:
            progress.empty()


def refresh_market_data(show_progress: bool = True) -> dict[str, Any]:
    """Force a complete Yahoo Finance and analysis refresh."""
    return get_market_data(
        force_refresh=True,
        show_progress=show_progress,
    )


def clear_market_data_cache(delete_pickle: bool = False) -> None:
    """Clear Streamlit's computed cache and optionally delete the disk cache."""
    _build_market_data.clear()

    if delete_pickle and CACHE_FILE.exists():
        try:
            CACHE_FILE.unlink()
        except OSError:
            pass

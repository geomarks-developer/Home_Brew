from __future__ import annotations

from datetime import datetime
from pathlib import Path
import pickle

import pandas as pd
import streamlit as st

from screener_engine import (
    SECTOR_ETFS,
    WORKBOOK_NAME,
    dividend_rows,
    download_history,
    etf_rows,
    heatmap_rows,
    read_tickers,
    sector_heatmap_rows,
    stock_rows,
)


ROOT_DIR = Path(__file__).resolve().parent
WORKBOOK_PATH = ROOT_DIR / WORKBOOK_NAME
CACHE_FILE = ROOT_DIR / "screener_cache.pkl"

# Number of tickers downloaded during each yfinance request.
# A smaller number gives more frequent progress updates.
DOWNLOAD_BATCH_SIZE = 20


def _load_pickle(path: Path):
    if not path.exists():
        return {}, {}, {}

    try:
        with open(path, "rb") as file:
            data = pickle.load(file)

        return (
            data.get("histories", {}),
            data.get("cache", {}),
            data.get("fund_cache", {}),
        )

    except (
        OSError,
        EOFError,
        pickle.PickleError,
        AttributeError,
        TypeError,
    ):
        return {}, {}, {}


def _save_pickle(path: Path, histories, info_cache, fund_cache):
    with open(path, "wb") as file:
        pickle.dump(
            {
                "histories": histories,
                "cache": info_cache,
                "fund_cache": fund_cache,
            },
            file,
        )


def _all_tickers(lists):
    return list(
        dict.fromkeys(
            lists.get("stocks", [])
            + lists.get("dividends", [])
            + lists.get("etfs", [])
            + lists.get("sp100", [])
            + list(SECTOR_ETFS.values())
        )
    )


def _update_progress(progress, value: int, text: str):
    """Update the Streamlit progress bar when one was provided."""
    if progress is not None:
        progress.progress(
            min(max(value, 0), 100),
            text=text,
        )


def _download_history_with_progress(
    tickers,
    progress,
    start_percent: int = 10,
    end_percent: int = 55,
):
    """
    Download ticker history in batches and update the progress bar
    after each completed batch.
    """
    tickers = list(tickers)

    if not tickers:
        return {}

    downloaded_histories = {}
    total_tickers = len(tickers)

    for batch_start in range(0, total_tickers, DOWNLOAD_BATCH_SIZE):
        batch = tickers[
            batch_start:batch_start + DOWNLOAD_BATCH_SIZE
        ]

        batch_end = min(
            batch_start + len(batch),
            total_tickers,
        )

        _update_progress(
            progress,
            start_percent
            + int(
                (batch_start / total_tickers)
                * (end_percent - start_percent)
            ),
            (
                f"Downloading market history: "
                f"{batch_start + 1}-{batch_end} "
                f"of {total_tickers} tickers..."
            ),
        )

        batch_histories = download_history(batch)

        if batch_histories:
            downloaded_histories.update(batch_histories)

        completed = batch_end

        current_percent = start_percent + int(
            (completed / total_tickers)
            * (end_percent - start_percent)
        )

        _update_progress(
            progress,
            current_percent,
            (
                f"Downloaded market history for "
                f"{completed} of {total_tickers} tickers."
            ),
        )

    return downloaded_histories


@st.cache_data(show_spinner=False)
def _build_market_data(
    workbook_path_string: str,
    cache_path_string: str,
    workbook_mtime: float,
    cache_mtime: float,
    refresh_generation: int,
    force_refresh: bool,
    _progress=None,
):
    workbook_path = Path(workbook_path_string)
    cache_path = Path(cache_path_string)

    _update_progress(
        _progress,
        5,
        "Reading ticker lists...",
    )

    lists = read_tickers(workbook_path)
    required_tickers = _all_tickers(lists)

    _update_progress(
        _progress,
        8,
        f"Found {len(required_tickers)} unique tickers.",
    )

    histories, info_cache, fund_cache = _load_pickle(cache_path)

    if force_refresh:
        _update_progress(
            _progress,
            10,
            (
                f"Refreshing market history for "
                f"{len(required_tickers)} tickers..."
            ),
        )

        histories = _download_history_with_progress(
            required_tickers,
            _progress,
            start_percent=10,
            end_percent=55,
        )

        info_cache = {}
        fund_cache = {}

    else:
        missing_tickers = [
            ticker
            for ticker in required_tickers
            if (
                ticker not in histories
                or histories[ticker] is None
                or histories[ticker].empty
            )
        ]

        if missing_tickers:
            _update_progress(
                _progress,
                10,
                (
                    f"Downloading history for "
                    f"{len(missing_tickers)} missing tickers..."
                ),
            )

            new_histories = _download_history_with_progress(
                missing_tickers,
                _progress,
                start_percent=10,
                end_percent=55,
            )

            histories.update(new_histories)

        else:
            _update_progress(
                _progress,
                55,
                (
                    f"Market history loaded from cache for "
                    f"{len(required_tickers)} tickers."
                ),
            )

    _update_progress(
        _progress,
        60,
        "Building stock screener results...",
    )

    stock_data = stock_rows(
        lists.get("stocks", []),
        histories,
        info_cache,
    )

    _update_progress(
        _progress,
        67,
        "Building dividend screener results...",
    )

    dividend_data = dividend_rows(
        lists.get("dividends", []),
        histories,
        info_cache,
    )

    _update_progress(
        _progress,
        74,
        "Building ETF screener results...",
    )

    etf_data = etf_rows(
        lists.get("etfs", []),
        histories,
        info_cache,
        fund_cache,
    )

    _update_progress(
        _progress,
        80,
        "Building S&P 100 heatmap...",
    )

    sp100_heatmap = heatmap_rows(
        lists.get("sp100", []),
        histories,
        info_cache,
    )

    _update_progress(
        _progress,
        84,
        "Building dividend heatmap...",
    )

    dividend_heatmap = heatmap_rows(
        lists.get("dividends", []),
        histories,
        info_cache,
        True,
    )

    _update_progress(
        _progress,
        88,
        "Building ETF heatmap...",
    )

    etf_heatmap = heatmap_rows(
        lists.get("etfs", []),
        histories,
        info_cache,
    )

    _update_progress(
        _progress,
        92,
        "Building sector heatmap...",
    )

    sector_heatmap = sector_heatmap_rows(
        histories,
        info_cache,
    )

    _update_progress(
        _progress,
        96,
        "Saving shared MarketScope cache...",
    )

    _save_pickle(
        cache_path,
        histories,
        info_cache,
        fund_cache,
    )

    _update_progress(
        _progress,
        98,
        "Preparing MarketScope data tables...",
    )

    return {
        "ticker_lists": lists,
        "histories": histories,
        "info_cache": info_cache,
        "fund_cache": fund_cache,
        "stock_rows": stock_data,
        "dividend_rows": dividend_data,
        "etf_rows": etf_data,
        "stock_df": pd.DataFrame(stock_data),
        "dividend_df": pd.DataFrame(dividend_data),
        "etf_df": pd.DataFrame(etf_data),
        "sp100_heatmap_df": pd.DataFrame(sp100_heatmap),
        "dividend_heatmap_df": pd.DataFrame(dividend_heatmap),
        "etf_heatmap_df": pd.DataFrame(etf_heatmap),
        "sector_heatmap_df": pd.DataFrame(sector_heatmap),
        "loaded_at": datetime.now().isoformat(timespec="seconds"),
        "ticker_count": len(required_tickers),
    }


def get_market_data(
    force_refresh: bool = False,
    show_progress: bool = False,
):
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(
            f"Workbook not found: {WORKBOOK_PATH}"
        )

    st.session_state.setdefault(
        "market_data_refresh_generation",
        0,
    )

    if force_refresh:
        st.session_state.market_data_refresh_generation += 1

    progress = None

    if show_progress:
        progress = st.progress(
            0,
            text="Starting MarketScope data load...",
        )

    cache_mtime = (
        CACHE_FILE.stat().st_mtime
        if CACHE_FILE.exists()
        else 0.0
    )

    data = _build_market_data(
        str(WORKBOOK_PATH),
        str(CACHE_FILE),
        WORKBOOK_PATH.stat().st_mtime,
        cache_mtime,
        st.session_state.market_data_refresh_generation,
        force_refresh,
        _progress=progress,
    )

    if progress is not None:
        progress.progress(
            100,
            text="MarketScope data ready.",
        )

        # Leave 100% visible briefly enough for Streamlit
        # to render it before removing the bar.
        import time
        time.sleep(0.4)

        progress.empty()

    return data


def clear_market_data_cache():
    _build_market_data.clear()
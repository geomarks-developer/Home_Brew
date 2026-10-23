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
    except (OSError, EOFError, pickle.PickleError, AttributeError, TypeError):
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


@st.cache_data(show_spinner=False)
def _build_market_data(
    workbook_path_string: str,
    cache_path_string: str,
    workbook_mtime: float,
    cache_mtime: float,
    refresh_generation: int,
    force_refresh: bool,
):
    workbook_path = Path(workbook_path_string)
    cache_path = Path(cache_path_string)
    lists = read_tickers(workbook_path)
    required_tickers = _all_tickers(lists)

    histories, info_cache, fund_cache = _load_pickle(cache_path)

    if force_refresh:
        histories = download_history(required_tickers)
        info_cache = {}
        fund_cache = {}
    else:
        missing_tickers = [
            ticker for ticker in required_tickers
            if ticker not in histories or histories[ticker] is None or histories[ticker].empty
        ]
        if missing_tickers:
            histories.update(download_history(missing_tickers))

    stock_data = stock_rows(lists.get("stocks", []), histories, info_cache)
    dividend_data = dividend_rows(lists.get("dividends", []), histories, info_cache)
    etf_data = etf_rows(lists.get("etfs", []), histories, info_cache, fund_cache)

    sp100_heatmap = heatmap_rows(
        lists.get("sp100", []), histories, info_cache
    )
    dividend_heatmap = heatmap_rows(
        lists.get("dividends", []), histories, info_cache, True
    )
    etf_heatmap = heatmap_rows(
        lists.get("etfs", []), histories, info_cache
    )
    sector_heatmap = sector_heatmap_rows(histories, info_cache)

    _save_pickle(cache_path, histories, info_cache, fund_cache)

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


def get_market_data(force_refresh: bool = False, show_progress: bool = False):
    if not WORKBOOK_PATH.exists():
        raise FileNotFoundError(f"Workbook not found: {WORKBOOK_PATH}")

    st.session_state.setdefault("market_data_refresh_generation", 0)

    if force_refresh:
        st.session_state.market_data_refresh_generation += 1

    progress = None
    if show_progress:
        progress = st.progress(0, text="Starting MarketScope data load...")
        progress.progress(10, text="Reading ticker lists and shared cache...")

    cache_mtime = CACHE_FILE.stat().st_mtime if CACHE_FILE.exists() else 0.0

    if progress is not None:
        progress.progress(25, text="Checking market history and preparing screeners...")

    data = _build_market_data(
        str(WORKBOOK_PATH),
        str(CACHE_FILE),
        WORKBOOK_PATH.stat().st_mtime,
        cache_mtime,
        st.session_state.market_data_refresh_generation,
        force_refresh,
    )

    if progress is not None:
        progress.progress(90, text="Finalizing shared MarketScope data...")
        progress.progress(100, text="MarketScope data ready.")
        progress.empty()

    return data


def clear_market_data_cache():
    _build_market_data.clear()

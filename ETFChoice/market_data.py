"""
MarketScope ETF
Shared market-data loading and caching.
"""

from __future__ import annotations

import pickle
import tempfile
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

import pandas as pd
import streamlit as st
import yfinance as yf

from config import (
    CACHE_FILENAME,
    CACHE_MAX_AGE_HOURS,
    ETF_UNIVERSE,
    HISTORY_PERIOD,
    PRICE_INTERVAL,
    PRIMARY_BENCHMARK,
    SECTOR_ETFS,
)
from etf_engine import analyze_etf_universe, extract_ticker_history

ProgressCallback = Callable[[str, float], None]
PROJECT_DIRECTORY = Path(__file__).resolve().parent
CACHE_PATH = PROJECT_DIRECTORY / CACHE_FILENAME


def current_timestamp() -> datetime:
    return datetime.now()


def normalize_tickers(tickers) -> list[str]:
    return list(dict.fromkeys(str(t).upper().strip() for t in tickers if t and str(t).strip()))


def report_progress(callback, message: str, progress: float) -> None:
    if callback is None:
        return
    try:
        callback(message, max(0.0, min(float(progress), 1.0)))
    except Exception:
        pass


def get_cache_modified_time():
    if not CACHE_PATH.exists():
        return None
    try:
        return datetime.fromtimestamp(CACHE_PATH.stat().st_mtime)
    except OSError:
        return None


def get_cache_age():
    modified = get_cache_modified_time()
    return None if modified is None else current_timestamp() - modified


def get_cache_age_hours():
    age = get_cache_age()
    return None if age is None else age.total_seconds() / 3600.0


def is_disk_cache_fresh(max_age_hours: float = CACHE_MAX_AGE_HOURS) -> bool:
    age = get_cache_age_hours()
    return age is not None and age >= 0 and age < float(max_age_hours)


def validate_cache_payload(data: Any) -> bool:
    if not isinstance(data, dict):
        return False
    required = {"price_data", "etf_df", "sector_df", "fund_data", "download_errors", "metadata"}
    return (
        required.issubset(data.keys())
        and isinstance(data.get("price_data"), pd.DataFrame)
        and isinstance(data.get("etf_df"), pd.DataFrame)
        and isinstance(data.get("sector_df"), pd.DataFrame)
        and isinstance(data.get("fund_data"), dict)
        and isinstance(data.get("download_errors"), list)
        and isinstance(data.get("metadata"), dict)
    )


def load_disk_cache():
    if not CACHE_PATH.exists():
        return None
    try:
        with CACHE_PATH.open("rb") as f:
            data = pickle.load(f)
    except Exception:
        return None
    if not validate_cache_payload(data):
        return None
    data = data.copy()
    metadata = data.get("metadata", {}).copy()
    metadata.update({"loaded_from": "disk_cache", "cache_path": str(CACHE_PATH), "cache_age_hours": get_cache_age_hours()})
    data["metadata"] = metadata
    return data


def save_disk_cache(data: dict[str, Any]) -> bool:
    if not validate_cache_payload(data):
        return False
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix="marketscope_etf_", suffix=".tmp", dir=PROJECT_DIRECTORY, delete=False) as f:
            pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)
            temp_path = Path(f.name)
        temp_path.replace(CACHE_PATH)
        return True
    except Exception:
        return False
    finally:
        if temp_path is not None and temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass


def download_price_history(tickers, period=HISTORY_PERIOD, interval=PRICE_INTERVAL) -> pd.DataFrame:
    clean = normalize_tickers(tickers)
    if not clean:
        return pd.DataFrame()
    data = yf.download(
        tickers=clean,
        period=period,
        interval=interval,
        group_by="column",
        auto_adjust=True,
        repair=True,
        actions=False,
        threads=True,
        progress=False,
        keepna=False,
        timeout=30,
        multi_level_index=True,
    )
    if data is None or not isinstance(data, pd.DataFrame) or data.empty:
        return pd.DataFrame()
    data = data.sort_index()
    data = data[~data.index.duplicated(keep="last")]
    if isinstance(data.index, pd.DatetimeIndex) and data.index.tz is not None:
        data.index = data.index.tz_localize(None)
    return data


def find_available_tickers(price_data, tickers) -> list[str]:
    return [t for t in normalize_tickers(tickers) if not extract_ticker_history(price_data, t).empty]


def find_missing_tickers(price_data, tickers) -> list[str]:
    requested = normalize_tickers(tickers)
    available = set(find_available_tickers(price_data, requested))
    return [t for t in requested if t not in available]


def retry_missing_tickers(price_data, missing_tickers, period=HISTORY_PERIOD, interval=PRICE_INTERVAL) -> pd.DataFrame:
    combined = price_data.copy()
    for ticker in normalize_tickers(missing_tickers):
        try:
            retry = download_price_history([ticker], period, interval)
        except Exception:
            continue
        if retry.empty:
            continue
        combined = retry if combined.empty else pd.concat([combined, retry], axis=1)
        combined = combined.loc[:, ~combined.columns.duplicated(keep="last")]
    return combined.sort_index() if not combined.empty else combined


def build_empty_fund_data(tickers) -> dict[str, dict[str, Any]]:
    return {
        ticker: {"name": ticker, "expense_ratio": None, "dividend_yield": None, "total_assets": None}
        for ticker in normalize_tickers(tickers)
    }

def download_fund_data(
    tickers,
    progress_callback=None,
) -> dict[str, dict[str, Any]]:
    """
    Download shared ETF metadata from Yahoo Finance.

    Falls back to the ticker when metadata is unavailable.
    """
    clean_tickers = normalize_tickers(tickers)
    fund_data = build_empty_fund_data(clean_tickers)

    total = len(clean_tickers)

    for index, ticker in enumerate(clean_tickers, start=1):
        try:
            etf = yf.Ticker(ticker)
            info = etf.info or {}

            long_name = info.get("longName")
            short_name = info.get("shortName")

            fund_name = (
                long_name
                or short_name
                or ticker
            )

            expense_ratio = info.get("annualReportExpenseRatio")

            if expense_ratio is None:
                expense_ratio = info.get("netExpenseRatio")

            # Yahoo may return yields and expense ratios as decimals.
            dividend_yield = info.get("yield")

            if dividend_yield is None:
                dividend_yield = info.get("dividendYield")

            if (
                dividend_yield is not None
                and dividend_yield <= 1
            ):
                dividend_yield *= 100

            if (
                expense_ratio is not None
                and expense_ratio <= 1
            ):
                expense_ratio *= 100

            total_assets = (
                info.get("totalAssets")
                or info.get("netAssets")
            )

            fund_data[ticker] = {
                "name": fund_name,
                "expense_ratio": expense_ratio,
                "dividend_yield": dividend_yield,
                "total_assets": total_assets,
            }

        except Exception:
            # Preserve the default record created above.
            pass

        if total:
            metadata_progress = (
                0.56
                + (index / total) * 0.12
            )

            report_progress(
                progress_callback,

                f"Loading ETF details: {ticker} "
                f"({index} of {total})...",
                metadata_progress,
            )

    return fund_data

def build_sector_dataframe(etf_df: pd.DataFrame) -> pd.DataFrame:
    if etf_df is None or etf_df.empty or "Ticker" not in etf_df.columns:
        return pd.DataFrame()
    lookup = {ticker: sector for sector, ticker in SECTOR_ETFS.items()}
    sector_df = etf_df[etf_df["Ticker"].isin(lookup)].copy()
    if sector_df.empty:
        return sector_df
    sector_df.insert(1, "Sector", sector_df["Ticker"].map(lookup))
    sort_cols = [c for c in ["Data Available", "ETF Score"] if c in sector_df.columns]
    if sort_cols:
        sector_df = sector_df.sort_values(sort_cols, ascending=[False] * len(sort_cols), na_position="last")
    return sector_df.reset_index(drop=True)


def build_market_data(progress_callback=None) -> dict[str, Any]:
    started = current_timestamp()
    all_tickers = normalize_tickers(list(ETF_UNIVERSE) + [PRIMARY_BENCHMARK] + list(SECTOR_ETFS.values()))

    report_progress(progress_callback, "Preparing ETF universe...", 0.05)
    report_progress(progress_callback, f"Downloading price history for {len(all_tickers)} ETFs...", 0.15)
    price_data = download_price_history(all_tickers)
    if price_data.empty:
        raise RuntimeError("Yahoo Finance did not return usable ETF price data.")

    report_progress(progress_callback, "Checking downloaded ETF histories...", 0.45)
    missing = find_missing_tickers(price_data, all_tickers)
    if missing:
        report_progress(progress_callback, f"Retrying {len(missing)} missing ETFs...", 0.52)
        price_data = retry_missing_tickers(price_data, missing)

    available = find_available_tickers(
        price_data,
        all_tickers,
    )

    final_missing = find_missing_tickers(
        price_data,
        all_tickers,
    )

    report_progress(
        progress_callback,
        "Loading ETF names and fund details...",
        0.56,
    )

    fund_data = download_fund_data(
        all_tickers,
        progress_callback=progress_callback,
    )

    report_progress(
        progress_callback,
        "Calculating ETF scores and indicators...",
        0.70,
    )

    report_progress(progress_callback, "Calculating ETF scores and indicators...", 0.70)
    etf_df = analyze_etf_universe(
        price_data=price_data,
        tickers=list(ETF_UNIVERSE),
        benchmark_ticker=PRIMARY_BENCHMARK,
        fund_data_by_ticker=fund_data,
    )

    report_progress(progress_callback, "Building the sector dataset...", 0.88)
    sector_df = build_sector_dataframe(etf_df)
    completed = current_timestamp()

    data = {
        "price_data": price_data,
        "etf_df": etf_df,
        "sector_df": sector_df,
        "fund_data": fund_data,
        "available_tickers": available,
        "missing_tickers": final_missing,
        "download_errors": [{"Ticker": t, "Error": "No usable price history returned"} for t in final_missing],
        "metadata": {
            "loaded_from": "yahoo_finance",
            "download_started_at": started,
            "download_completed_at": completed,
            "last_refresh": completed,
            "duration_seconds": round((completed - started).total_seconds(), 2),
            "history_period": HISTORY_PERIOD,
            "price_interval": PRICE_INTERVAL,
            "benchmark": PRIMARY_BENCHMARK,
            "requested_ticker_count": len(all_tickers),
            "available_ticker_count": len(available),
            "missing_ticker_count": len(final_missing),
            "ETF_result_count": len(etf_df),
            "sector_result_count": len(sector_df),
            "cache_path": str(CACHE_PATH),
            "cache_age_hours": 0.0,
        },
    }

    report_progress(progress_callback, "Saving the MarketScope ETF cache...", 0.95)
    data["metadata"]["disk_cache_saved"] = save_disk_cache(data)
    report_progress(progress_callback, "MarketScope ETF data is ready.", 1.0)
    return data


@st.cache_data(show_spinner=False)
def _get_cached_market_data(cache_day: str, refresh_token: str) -> dict[str, Any]:
    del cache_day, refresh_token
    if is_disk_cache_fresh():
        cached = load_disk_cache()
        if cached is not None:
            return cached
    return build_market_data()


def get_market_data(force_refresh: bool = False, progress_callback=None) -> dict[str, Any]:
    cache_day = current_timestamp().date().isoformat()
    if force_refresh:
        clear_market_data_cache()
        return build_market_data(progress_callback)
    if progress_callback is not None and not is_disk_cache_fresh():
        built = build_market_data(progress_callback)
        _get_cached_market_data.clear()
        return built
    return _get_cached_market_data(cache_day, "normal")


def clear_disk_cache() -> bool:
    if not CACHE_PATH.exists():
        return True
    try:
        CACHE_PATH.unlink()
    except OSError:
        return False
    return not CACHE_PATH.exists()


def clear_market_data_cache() -> bool:
    _get_cached_market_data.clear()
    return clear_disk_cache()


def refresh_market_data(progress_callback=None) -> dict[str, Any]:
    clear_market_data_cache()
    return build_market_data(progress_callback)


def initialize_market_data(force_refresh: bool = False) -> dict[str, Any]:
    if force_refresh or "market_data" not in st.session_state or st.session_state["market_data"] is None:
        session_key = str(uuid.uuid4())
        progress_bar = st.progress(0.0, text="Loading MarketScope ETF data...")

        def update_progress(message: str, progress: float) -> None:
            progress_bar.progress(progress, text=message)

        try:
            data = get_market_data(force_refresh=force_refresh, progress_callback=update_progress)
            st.session_state["market_data"] = data
            st.session_state["market_data_session_key"] = session_key
        finally:
            progress_bar.empty()
    return st.session_state["market_data"]


def get_etf_results(market_data) -> pd.DataFrame:
    df = market_data.get("etf_df", pd.DataFrame())
    return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()


def get_sector_results(market_data) -> pd.DataFrame:
    df = market_data.get("sector_df", pd.DataFrame())
    return df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()


def get_price_history(market_data, ticker: str) -> pd.DataFrame:
    price_data = market_data.get("price_data", pd.DataFrame())
    if not isinstance(price_data, pd.DataFrame):
        return pd.DataFrame()
    return extract_ticker_history(price_data, ticker)


def get_market_metadata(market_data) -> dict[str, Any]:
    metadata = market_data.get("metadata", {})
    return metadata.copy() if isinstance(metadata, dict) else {}


if __name__ == "__main__":
    print("Building MarketScope ETF market data...")
    data = get_market_data(force_refresh=True)
    metadata = get_market_metadata(data)
    print("MarketScope ETF data build complete.")
    print("Requested tickers:", metadata.get("requested_ticker_count"))
    print("Available tickers:", metadata.get("available_ticker_count"))
    print("Missing tickers:", metadata.get("missing_ticker_count"))
    print("ETF result rows:", metadata.get("ETF_result_count"))
    print("Sector result rows:", metadata.get("sector_result_count"))
    print("Cache path:", metadata.get("cache_path"))

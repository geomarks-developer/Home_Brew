"""MarketScope Growth earnings calendar page with a persistent rolling cache."""
from __future__ import annotations

import os
import pickle
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

from config import GROWTH_TICKERS
from market_data import load_market_data


CALENDAR_CACHE_FILE = "marketscope_growth_calendar_cache.pkl"
CALENDAR_CACHE_SCHEMA_VERSION = 1
CALENDAR_CACHE_MAX_AGE_HOURS = 24
CALENDAR_PAST_DAYS = 30
CALENDAR_FUTURE_DAYS = 90
EARNINGS_LIMIT_PER_TICKER = 16


# =========================================================
# Market universe
# =========================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_growth_universe() -> pd.DataFrame:
    return load_market_data()


# =========================================================
# Persistent calendar cache
# =========================================================

def calendar_cache_path() -> Path:
    return Path(__file__).resolve().parent.parent / CALENDAR_CACHE_FILE


def calendar_cache_age_hours(path: Path | None = None) -> float | None:
    path = path or calendar_cache_path()
    if not path.exists():
        return None

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - modified).total_seconds() / 3600


def calendar_cache_is_fresh(
    max_age_hours: float = CALENDAR_CACHE_MAX_AGE_HOURS,
    path: Path | None = None,
) -> bool:
    age = calendar_cache_age_hours(path)
    return age is not None and age <= max_age_hours


def load_calendar_cache(path: Path | None = None) -> dict[str, Any] | None:
    path = path or calendar_cache_path()
    if not path.exists():
        return None

    try:
        with path.open("rb") as handle:
            payload = pickle.load(handle)
    except (OSError, EOFError, pickle.UnpicklingError, AttributeError, ValueError):
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("schema_version") != CALENDAR_CACHE_SCHEMA_VERSION:
        return None
    if not isinstance(payload.get("data"), pd.DataFrame):
        return None

    result = payload.copy()
    result["data"] = result["data"].copy()
    return result


def save_calendar_cache(
    calendar: pd.DataFrame,
    tickers: tuple[str, ...],
    start: date,
    end: date,
    path: Path | None = None,
) -> Path:
    path = path or calendar_cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": CALENDAR_CACHE_SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_start": start.isoformat(),
        "coverage_end": end.isoformat(),
        "tickers": tuple(tickers),
        "data": calendar.copy(),
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


def clear_calendar_cache(path: Path | None = None) -> bool:
    path = path or calendar_cache_path()
    if path.exists():
        path.unlink()
        return True
    return False


# =========================================================
# Earnings retrieval
# =========================================================

def _normalize_earnings(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Normalize yfinance earnings-date output for one ticker."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    work = frame.copy().reset_index()
    date_column = work.columns[0]
    work = work.rename(columns={date_column: "Earnings Date"})
    work["Earnings Date"] = pd.to_datetime(
        work["Earnings Date"],
        errors="coerce",
        utc=True,
    )
    work = work.dropna(subset=["Earnings Date"])
    work["Ticker"] = ticker

    work = work.rename(
        columns={
            "Surprise(%)": "EPS Surprise",
            "Surprise (%)": "EPS Surprise",
        }
    )

    keep = ["Ticker", "Earnings Date"]
    for column in ("EPS Estimate", "Reported EPS", "EPS Surprise"):
        if column in work.columns:
            keep.append(column)

    return work[keep]


def fetch_earnings_calendar(
    tickers: tuple[str, ...],
    start: date,
    end: date,
    limit_per_ticker: int = EARNINGS_LIMIT_PER_TICKER,
) -> pd.DataFrame:
    """Fetch earnings dates and retain only events inside the rolling window."""
    frames: list[pd.DataFrame] = []
    start_timestamp = pd.Timestamp(start, tz="UTC")
    end_timestamp = pd.Timestamp(end + timedelta(days=1), tz="UTC")

    progress = st.progress(0, text="Preparing earnings calendar...")
    total = max(len(tickers), 1)

    for position, ticker in enumerate(tickers, start=1):
        progress.progress(
            position / total,
            text=f"Loading earnings calendar: {ticker} ({position}/{len(tickers)})",
        )

        try:
            frame = yf.Ticker(ticker).get_earnings_dates(limit=limit_per_ticker)
        except Exception:
            continue

        normalized = _normalize_earnings(frame, ticker)
        if normalized.empty:
            continue

        normalized = normalized.loc[
            (normalized["Earnings Date"] >= start_timestamp)
            & (normalized["Earnings Date"] < end_timestamp)
        ].copy()

        if not normalized.empty:
            frames.append(normalized)

    progress.empty()

    if not frames:
        return pd.DataFrame()

    calendar = pd.concat(frames, ignore_index=True)
    calendar = calendar.drop_duplicates(
        subset=["Ticker", "Earnings Date"],
        keep="last",
    )
    return calendar.sort_values(["Earnings Date", "Ticker"]).reset_index(drop=True)


def load_earnings_calendar(
    tickers: tuple[str, ...],
    force_refresh: bool = False,
    allow_stale_on_error: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Return the persistent calendar cache or rebuild its rolling date window."""
    today = date.today()
    start = today - timedelta(days=CALENDAR_PAST_DAYS)
    end = today + timedelta(days=CALENDAR_FUTURE_DAYS)
    normalized_tickers = tuple(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))

    cached = load_calendar_cache()
    cached_tickers = tuple(cached.get("tickers", ())) if cached else ()
    cached_start = cached.get("coverage_start") if cached else None
    cached_end = cached.get("coverage_end") if cached else None

    cache_matches = (
        cached is not None
        and cached_tickers == normalized_tickers
        and cached_start == start.isoformat()
        and cached_end == end.isoformat()
    )

    if not force_refresh and cache_matches and calendar_cache_is_fresh():
        return cached["data"].copy(), {
            "source": "calendar cache",
            "created_utc": cached.get("created_utc"),
            "coverage_start": start,
            "coverage_end": end,
            "stale": False,
        }

    try:
        calendar = fetch_earnings_calendar(normalized_tickers, start, end)
        save_calendar_cache(calendar, normalized_tickers, start, end)
        return calendar, {
            "source": "Yahoo Finance refresh",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "coverage_start": start,
            "coverage_end": end,
            "stale": False,
        }
    except Exception:
        if allow_stale_on_error and cached is not None:
            return cached["data"].copy(), {
                "source": "stale calendar cache",
                "created_utc": cached.get("created_utc"),
                "coverage_start": cached.get("coverage_start"),
                "coverage_end": cached.get("coverage_end"),
                "stale": True,
            }
        raise


# =========================================================
# Page
# =========================================================

def show() -> None:
    st.title("🗓️ Growth Market Calendar")
    st.caption(
        "Track available earnings dates for companies in the MarketScope Growth universe."
    )

    try:
        market = get_growth_universe()
    except Exception as exc:
        st.error("The Growth universe could not be loaded.")
        st.exception(exc)
        return

    if market is None or market.empty:
        tickers = tuple(str(ticker).upper() for ticker in GROWTH_TICKERS)
        company_map = {ticker: ticker for ticker in tickers}
    else:
        ticker_series = market["Ticker"].dropna().astype(str).str.strip().str.upper()
        tickers = tuple(ticker_series[ticker_series != ""].unique())
        company_map = {
            str(row["Ticker"]).upper(): row.get("Company", row["Ticker"])
            for _, row in market.iterrows()
            if pd.notna(row.get("Ticker"))
        }

    today = date.today()

    control_col, status_col = st.columns([1, 3])
    with control_col:
        refresh_calendar = st.button(
            "🔄 Refresh Calendar",
            type="secondary",
            use_container_width=True,
        )

    if refresh_calendar:
        clear_calendar_cache()

    with st.spinner("Loading earnings calendar..."):
        try:
            calendar, metadata = load_earnings_calendar(
                tickers,
                force_refresh=refresh_calendar,
            )
        except Exception as exc:
            st.error("The earnings calendar could not be loaded.")
            st.exception(exc)
            return

    with status_col:
        age = calendar_cache_age_hours()
        age_text = "Just refreshed" if age is not None and age < 0.05 else (
            f"{age * 60:.0f} minutes old" if age is not None and age < 1 else
            f"{age:.1f} hours old" if age is not None else "Cache age unavailable"
        )
        coverage_start = metadata.get("coverage_start")
        coverage_end = metadata.get("coverage_end")
        st.caption(
            f"Source: {metadata.get('source', 'Unknown')}  |  "
            f"{age_text}  |  Coverage: {coverage_start} through {coverage_end}"
        )

    if metadata.get("stale"):
        st.warning("Yahoo Finance could not be refreshed, so the last available calendar cache is displayed.")

    range_choice = st.radio(
        "Calendar range",
        ["Next 7 days", "Next 30 days", "Next 90 days", "Recent 30 days"],
        horizontal=True,
    )

    if calendar.empty:
        st.info("No earnings-calendar data is currently available for the Growth universe.")
        return

    calendar = calendar.copy()
    calendar["Earnings Date"] = pd.to_datetime(
        calendar["Earnings Date"],
        errors="coerce",
        utc=True,
    )
    calendar = calendar.dropna(subset=["Earnings Date"])
    calendar["Date"] = calendar["Earnings Date"].dt.date

    if range_choice == "Next 7 days":
        start, end = today, today + timedelta(days=7)
    elif range_choice == "Next 30 days":
        start, end = today, today + timedelta(days=30)
    elif range_choice == "Next 90 days":
        start, end = today, today + timedelta(days=90)
    else:
        start, end = today - timedelta(days=30), today

    view = calendar.loc[
        (calendar["Date"] >= start) & (calendar["Date"] <= end)
    ].copy()
    view["Company"] = view["Ticker"].map(company_map).fillna(view["Ticker"])

    sector_map: dict[str, Any] = {}
    score_map: dict[str, Any] = {}
    if market is not None and not market.empty:
        lookup = market.copy()
        lookup["Ticker"] = lookup["Ticker"].astype(str).str.upper()
        if "Sector" in lookup.columns:
            sector_map = lookup.set_index("Ticker")["Sector"].to_dict()
        if "Overall Score" in lookup.columns:
            score_map = lookup.set_index("Ticker")["Overall Score"].to_dict()

    view["Sector"] = view["Ticker"].map(sector_map).fillna("Unknown")
    view["Overall Score"] = view["Ticker"].map(score_map)

    metrics = st.columns(4)
    metrics[0].metric("Events", f"{len(view):,}")
    metrics[1].metric("Companies", f"{view['Ticker'].nunique():,}")
    metrics[2].metric("Start", start.strftime("%b %d, %Y"))
    metrics[3].metric("End", end.strftime("%b %d, %Y"))

    if view.empty:
        st.info(f"No available earnings dates fall between {start:%b %d} and {end:%b %d, %Y}.")
        return

    st.divider()
    st.subheader("Earnings Schedule")

    display = view.copy()
    display["Earnings Date"] = display["Earnings Date"].dt.strftime("%Y-%m-%d %H:%M UTC")
    columns = [
        column
        for column in (
            "Earnings Date",
            "Ticker",
            "Company",
            "Sector",
            "EPS Estimate",
            "Reported EPS",
            "EPS Surprise",
            "Overall Score",
        )
        if column in display.columns
    ]

    config = {
        "Overall Score": st.column_config.ProgressColumn(
            "Overall",
            min_value=0,
            max_value=100,
            format="%.1f",
        ),
        "EPS Estimate": st.column_config.NumberColumn("EPS Estimate", format="%.2f"),
        "Reported EPS": st.column_config.NumberColumn("Reported EPS", format="%.2f"),
        "EPS Surprise": st.column_config.NumberColumn("EPS Surprise", format="percent"),
    }

    st.dataframe(
        display[columns],
        use_container_width=True,
        hide_index=True,
        column_config=config,
    )

    st.divider()
    st.subheader("Events by Day")
    daily = view.groupby("Date", as_index=False).agg(Events=("Ticker", "count"))
    daily["Date"] = daily["Date"].astype(str)
    st.bar_chart(daily.set_index("Date")["Events"])

    st.download_button(
        "Download Calendar CSV",
        display[columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_growth_calendar.csv",
        mime="text/csv",
        type="secondary",
    )

    st.caption(
        "Calendar availability and timing depend on Yahoo Finance data. Earnings dates can change, "
        "so confirm important dates with the company or another primary source before acting."
    )


show()

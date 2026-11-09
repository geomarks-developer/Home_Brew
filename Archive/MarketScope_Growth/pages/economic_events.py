"""MarketScope Growth economic-events calendar with persistent caching."""
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


CACHE_FILE = "marketscope_growth_economic_events_cache.pkl"
CACHE_SCHEMA_VERSION = 1
CACHE_MAX_AGE_HOURS = 24
PAST_DAYS = 30
FUTURE_DAYS = 90
PAGE_SIZE = 100
MAX_PAGES = 20


# =========================================================
# Persistent cache
# =========================================================

def cache_path() -> Path:
    return Path(__file__).resolve().parent.parent / CACHE_FILE


def cache_age_hours(path: Path | None = None) -> float | None:
    path = path or cache_path()
    if not path.exists():
        return None
    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (datetime.now(timezone.utc) - modified).total_seconds() / 3600


def cache_is_fresh(max_age_hours: float = CACHE_MAX_AGE_HOURS) -> bool:
    age = cache_age_hours()
    return age is not None and age <= max_age_hours


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

    payload = payload.copy()
    payload["data"] = payload["data"].copy()
    return payload


def save_cache(
    data: pd.DataFrame,
    start: date,
    end: date,
    path: Path | None = None,
) -> Path:
    path = path or cache_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "schema_version": CACHE_SCHEMA_VERSION,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "coverage_start": start.isoformat(),
        "coverage_end": end.isoformat(),
        "data": data.copy(),
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


def clear_cache(path: Path | None = None) -> bool:
    path = path or cache_path()
    if path.exists():
        path.unlink()
        return True
    return False


# =========================================================
# Retrieval and normalization
# =========================================================

def _find_date_column(frame: pd.DataFrame) -> str | None:
    candidates = (
        "Start Date",
        "Start DateTime",
        "Date",
        "Datetime",
        "Event Date",
        "Event Start Date",
    )
    for column in candidates:
        if column in frame.columns:
            return column

    for column in frame.columns:
        name = str(column).lower()
        if "date" in name or "time" in name:
            return column

    return None


def normalize_events(frame: pd.DataFrame) -> pd.DataFrame:
    """Normalize Yahoo's economic-event output without assuming a fixed schema."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    work = frame.copy()
    if not isinstance(work.index, pd.RangeIndex):
        work = work.reset_index()

    date_column = _find_date_column(work)
    if date_column is None:
        return pd.DataFrame()

    work = work.rename(columns={date_column: "Event Date"})
    work["Event Date"] = pd.to_datetime(
        work["Event Date"],
        errors="coerce",
        utc=True,
    )
    work = work.dropna(subset=["Event Date"])

    # Normalize common Yahoo column variations when present.
    aliases = {
        "Event Name": "Event",
        "Economic Event": "Event",
        "Event Title": "Event",
        "Country Name": "Country",
        "Region Name": "Region",
        "Previous Value": "Previous",
        "Forecast Value": "Forecast",
        "Actual Value": "Actual",
    }
    for source, target in aliases.items():
        if source in work.columns and target not in work.columns:
            work = work.rename(columns={source: target})

    return work.sort_values("Event Date").reset_index(drop=True)


def fetch_economic_events(start: date, end: date) -> pd.DataFrame:
    """Fetch all available pages for the rolling economic-event window."""
    calendars = yf.Calendars(start=start.isoformat(), end=end.isoformat())
    frames: list[pd.DataFrame] = []

    progress = st.progress(0, text="Loading economic events...")

    for page in range(MAX_PAGES):
        offset = page * PAGE_SIZE
        progress.progress(
            min((page + 1) / MAX_PAGES, 1.0),
            text=f"Loading economic events page {page + 1}...",
        )

        frame = calendars.get_economic_events_calendar(
            start=start.isoformat(),
            end=end.isoformat(),
            limit=PAGE_SIZE,
            offset=offset,
            force=page == 0,
        )

        if frame is None or frame.empty:
            break

        frames.append(frame.copy())
        if len(frame) < PAGE_SIZE:
            break

    progress.empty()

    if not frames:
        return pd.DataFrame()

    normalized = normalize_events(pd.concat(frames, ignore_index=True))
    if normalized.empty:
        return normalized

    # Deduplicate using all columns after string conversion for mixed schemas.
    key_frame = normalized.astype(str)
    normalized = normalized.loc[~key_frame.duplicated()].copy()
    return normalized.sort_values("Event Date").reset_index(drop=True)


def load_economic_events(
    force_refresh: bool = False,
    allow_stale_on_error: bool = True,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    today = date.today()
    start = today - timedelta(days=PAST_DAYS)
    end = today + timedelta(days=FUTURE_DAYS)

    cached = load_cache()
    cache_matches = (
        cached is not None
        and cached.get("coverage_start") == start.isoformat()
        and cached.get("coverage_end") == end.isoformat()
    )

    if not force_refresh and cache_matches and cache_is_fresh():
        return cached["data"].copy(), {
            "source": "economic-events cache",
            "created_utc": cached.get("created_utc"),
            "coverage_start": start,
            "coverage_end": end,
            "stale": False,
        }

    try:
        events = fetch_economic_events(start, end)
        save_cache(events, start, end)
        return events, {
            "source": "Yahoo Finance refresh",
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "coverage_start": start,
            "coverage_end": end,
            "stale": False,
        }
    except Exception:
        if allow_stale_on_error and cached is not None:
            return cached["data"].copy(), {
                "source": "stale economic-events cache",
                "created_utc": cached.get("created_utc"),
                "coverage_start": cached.get("coverage_start"),
                "coverage_end": cached.get("coverage_end"),
                "stale": True,
            }
        raise


# =========================================================
# Display helpers
# =========================================================

def available_column(data: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
    return next((column for column in candidates if column in data.columns), None)


def display_columns(data: pd.DataFrame) -> list[str]:
    preferred = [
        "Event Date",
        "Event",
        "Country",
        "Region",
        "Importance",
        "Actual",
        "Forecast",
        "Previous",
        "Frequency",
        "Category",
    ]
    columns = [column for column in preferred if column in data.columns]

    # Preserve useful fields returned by Yahoo even if their names change.
    excluded = set(columns) | {"Date"}
    for column in data.columns:
        if column not in excluded and len(columns) < 12:
            columns.append(column)

    return columns


def number_config(data: pd.DataFrame, columns: list[str]) -> dict[str, Any]:
    config: dict[str, Any] = {
        "Event Date": st.column_config.DatetimeColumn(
            "Event Date",
            format="MMM D, YYYY, h:mm a",
        )
    }

    for column in columns:
        if column == "Event Date" or column not in data.columns:
            continue
        if pd.api.types.is_numeric_dtype(data[column]):
            config[column] = st.column_config.NumberColumn(column, format="localized")

    return config


# =========================================================
# Page
# =========================================================

def show() -> None:
    st.title("🌐 Economic Events")
    st.caption(
        "Monitor scheduled macroeconomic releases and other economic events that may affect growth stocks."
    )

    control_col, status_col = st.columns([1, 3])
    with control_col:
        refresh = st.button(
            "🔄 Refresh Economic Calendar",
            type="secondary",
            use_container_width=True,
        )

    if refresh:
        clear_cache()

    with st.spinner("Loading economic-events calendar..."):
        try:
            events, metadata = load_economic_events(force_refresh=refresh)
        except Exception as exc:
            st.error("The economic-events calendar could not be loaded.")
            st.exception(exc)
            return

    with status_col:
        age = cache_age_hours()
        if age is None:
            age_text = "Cache age unavailable"
        elif age < 0.05:
            age_text = "Just refreshed"
        elif age < 1:
            age_text = f"{age * 60:.0f} minutes old"
        else:
            age_text = f"{age:.1f} hours old"

        st.caption(
            f"Source: {metadata.get('source', 'Unknown')}  |  {age_text}  |  "
            f"Coverage: {metadata.get('coverage_start')} through {metadata.get('coverage_end')}"
        )

    if metadata.get("stale"):
        st.warning(
            "Yahoo Finance could not be refreshed, so the last available economic-events cache is displayed."
        )

    range_choice = st.radio(
        "Calendar range",
        ["Next 7 days", "Next 30 days", "Next 90 days", "Recent 30 days"],
        horizontal=True,
    )

    if events is None or events.empty:
        st.info("No economic-event data is currently available for this date range.")
        return

    events = events.copy()
    events["Event Date"] = pd.to_datetime(events["Event Date"], errors="coerce", utc=True)
    events = events.dropna(subset=["Event Date"])
    events["Date"] = events["Event Date"].dt.date

    today = date.today()
    if range_choice == "Next 7 days":
        start, end = today, today + timedelta(days=7)
    elif range_choice == "Next 30 days":
        start, end = today, today + timedelta(days=30)
    elif range_choice == "Next 90 days":
        start, end = today, today + timedelta(days=90)
    else:
        start, end = today - timedelta(days=30), today

    view = events.loc[
        (events["Date"] >= start) & (events["Date"] <= end)
    ].copy()

    country_column = available_column(view, ("Country", "Region"))
    event_column = available_column(view, ("Event", "Category", "Type"))

    metrics = st.columns(4)
    metrics[0].metric("Events", f"{len(view):,}")
    metrics[1].metric(
        "Countries / Regions",
        f"{view[country_column].nunique():,}" if country_column else "N/A",
    )
    metrics[2].metric("Start", start.strftime("%b %d, %Y"))
    metrics[3].metric("End", end.strftime("%b %d, %Y"))

    if view.empty:
        st.info(f"No available economic events fall between {start:%b %d} and {end:%b %d, %Y}.")
        return

    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        if country_column:
            country_options = sorted(view[country_column].dropna().astype(str).unique())
            selected_countries = st.multiselect(
                f"Filter by {country_column.lower()}",
                country_options,
                default=country_options,
            )
            view = view[view[country_column].astype(str).isin(selected_countries)]

    with filter_col2:
        search_text = st.text_input("Search events", placeholder="Inflation, GDP, employment...")
        if search_text and event_column:
            view = view[
                view[event_column]
                .astype(str)
                .str.contains(search_text, case=False, na=False)
            ]

    st.divider()
    st.subheader("Economic Events Schedule")

    columns = display_columns(view)
    st.dataframe(
        view[columns],
        use_container_width=True,
        hide_index=True,
        column_config=number_config(view, columns),
    )

    st.divider()
    st.subheader("Events by Day")
    daily = view.groupby("Date", as_index=False).agg(Events=("Event Date", "count"))
    daily["Date"] = daily["Date"].astype(str)
    st.bar_chart(daily.set_index("Date")["Events"])

    st.download_button(
        "Download Economic Events CSV",
        data=view[columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_growth_economic_events.csv",
        mime="text/csv",
        type="secondary",
    )

    st.caption(
        "Economic-event availability, timing, and reported values depend on Yahoo Finance data. "
        "Confirm market-sensitive releases with the relevant government agency or another primary source."
    )


show()

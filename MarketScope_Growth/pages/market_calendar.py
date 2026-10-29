"""MarketScope Growth earnings calendar page."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from config import GROWTH_TICKERS
from market_data import load_market_data


@st.cache_data(ttl=900, show_spinner=False)
def get_growth_universe() -> pd.DataFrame:
    return load_market_data()


def _normalize_earnings(frame: pd.DataFrame, ticker: str) -> pd.DataFrame:
    """Normalize yfinance earnings-date output for one ticker."""
    if frame is None or frame.empty:
        return pd.DataFrame()

    work = frame.copy().reset_index()
    date_column = work.columns[0]
    work = work.rename(columns={date_column: "Earnings Date"})
    work["Earnings Date"] = pd.to_datetime(work["Earnings Date"], errors="coerce", utc=True)
    work = work.dropna(subset=["Earnings Date"])
    work["Ticker"] = ticker

    rename = {
        "EPS Estimate": "EPS Estimate",
        "Reported EPS": "Reported EPS",
        "Surprise(%)": "EPS Surprise",
        "Surprise (%)": "EPS Surprise",
    }
    work = work.rename(columns=rename)

    keep = ["Ticker", "Earnings Date"]
    for column in ("EPS Estimate", "Reported EPS", "EPS Surprise"):
        if column in work.columns:
            keep.append(column)
    return work[keep]


@st.cache_data(ttl=3600, show_spinner=False)
def get_earnings_calendar(tickers: tuple[str, ...], limit_per_ticker: int = 12) -> pd.DataFrame:
    """Collect available future and historical earnings dates for the universe."""
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        try:
            frame = yf.Ticker(ticker).get_earnings_dates(limit=limit_per_ticker)
        except Exception:
            continue
        normalized = _normalize_earnings(frame, ticker)
        if not normalized.empty:
            frames.append(normalized)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).sort_values("Earnings Date")


def pct(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.1%}"


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
        tickers = tuple(GROWTH_TICKERS)
        company_map = {ticker: ticker for ticker in tickers}
    else:
        tickers = tuple(market["Ticker"].astype(str).str.upper().dropna().unique())
        company_map = {
            str(row["Ticker"]).upper(): row.get("Company", row["Ticker"])
            for _, row in market.iterrows()
        }

    today = date.today()
    range_choice = st.radio(
        "Calendar range",
        ["Next 7 days", "Next 30 days", "Next 90 days", "Recent 30 days"],
        horizontal=True,
    )

    with st.spinner("Loading earnings calendar..."):
        calendar = get_earnings_calendar(tickers)

    if calendar.empty:
        st.info("No earnings-calendar data is currently available for the Growth universe.")
        return

    calendar["Date"] = calendar["Earnings Date"].dt.date
    if range_choice == "Next 7 days":
        start, end = today, today + timedelta(days=7)
    elif range_choice == "Next 30 days":
        start, end = today, today + timedelta(days=30)
    elif range_choice == "Next 90 days":
        start, end = today, today + timedelta(days=90)
    else:
        start, end = today - timedelta(days=30), today

    view = calendar.loc[(calendar["Date"] >= start) & (calendar["Date"] <= end)].copy()
    view["Company"] = view["Ticker"].map(company_map).fillna(view["Ticker"])

    sector_map = {}
    score_map = {}
    if market is not None and not market.empty:
        sector_map = market.set_index("Ticker")["Sector"].to_dict() if "Sector" in market.columns else {}
        score_map = market.set_index("Ticker")["Overall Score"].to_dict() if "Overall Score" in market.columns else {}
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
        column for column in (
            "Earnings Date", "Ticker", "Company", "Sector", "EPS Estimate",
            "Reported EPS", "EPS Surprise", "Overall Score"
        ) if column in display.columns
    ]

    config = {
        "Overall Score": st.column_config.ProgressColumn("Overall", min_value=0, max_value=100, format="%.1f"),
        "EPS Estimate": st.column_config.NumberColumn("EPS Estimate", format="%.2f"),
        "Reported EPS": st.column_config.NumberColumn("Reported EPS", format="%.2f"),
        "EPS Surprise": st.column_config.NumberColumn("EPS Surprise", format="%.1%%"),
    }
    st.dataframe(display[columns], use_container_width=True, hide_index=True, column_config=config)

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
    )

    st.caption(
        "Calendar availability and timing depend on Yahoo Finance data. Earnings dates can change, "
        "so confirm important dates with the company or another primary source before acting."
    )
# =========================================================
# Run page
# =========================================================
show()
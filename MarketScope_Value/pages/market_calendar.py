"""MarketScope Value earnings calendar."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st
import yfinance as yf

from market_data import load_market_data


@st.cache_data(ttl=86_400, show_spinner=False)
def fetch_earnings_calendar(
    tickers: tuple[str, ...],
    past_days: int = 30,
    future_days: int = 90,
) -> pd.DataFrame:
    """Fetch available earnings dates for the Value universe."""
    start = pd.Timestamp(date.today() - timedelta(days=past_days), tz="UTC")
    end = pd.Timestamp(date.today() + timedelta(days=future_days + 1), tz="UTC")
    frames: list[pd.DataFrame] = []

    for ticker in tickers:
        try:
            earnings = yf.Ticker(ticker).get_earnings_dates(limit=16)
        except Exception:
            continue

        if earnings is None or earnings.empty:
            continue

        work = earnings.copy().reset_index()
        work = work.rename(columns={work.columns[0]: "Earnings Date"})
        work["Earnings Date"] = pd.to_datetime(
            work["Earnings Date"], errors="coerce", utc=True
        )
        work = work.dropna(subset=["Earnings Date"])
        work = work[
            (work["Earnings Date"] >= start)
            & (work["Earnings Date"] < end)
        ].copy()
        if work.empty:
            continue

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
        frames.append(work[keep])

    if not frames:
        return pd.DataFrame()

    calendar = pd.concat(frames, ignore_index=True)
    calendar = calendar.drop_duplicates(
        subset=["Ticker", "Earnings Date"], keep="last"
    )
    return calendar.sort_values(["Earnings Date", "Ticker"]).reset_index(drop=True)


def column_config() -> dict:
    return {
        "Earnings Date": st.column_config.DatetimeColumn(
            "Earnings Date",
            format="MMM D, YYYY, h:mm a",
        ),
        "EPS Estimate": st.column_config.NumberColumn(
            "EPS Estimate", format="%.2f"
        ),
        "Reported EPS": st.column_config.NumberColumn(
            "Reported EPS", format="%.2f"
        ),
        "EPS Surprise": st.column_config.NumberColumn(
            "EPS Surprise", format="percent"
        ),
        "Forward PE": st.column_config.NumberColumn(
            "Forward P/E", format="%.1f"
        ),
        "FCF Yield": st.column_config.NumberColumn(
            "FCF Yield", format="percent"
        ),
        "Overall Score": st.column_config.ProgressColumn(
            "Overall", min_value=0, max_value=100, format="%.1f"
        ),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk", min_value=0, max_value=100, format="%.1f"
        ),
    }


def show() -> None:
    st.title("🗓️ Value Market Calendar")
    st.caption(
        "Track available earnings dates for companies in the MarketScope Value universe."
    )

    try:
        with st.spinner("Loading the MarketScope Value universe..."):
            market = load_market_data()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    if market is None or market.empty or "Ticker" not in market.columns:
        st.warning("No Value-universe data is currently available.")
        return

    market = market.copy()
    market["Ticker"] = market["Ticker"].astype(str).str.upper()
    tickers = tuple(market["Ticker"].dropna().unique())

    controls = st.columns([1, 3])
    with controls[0]:
        refresh = st.button(
            "🔄 Refresh Calendar",
            type="secondary",
            use_container_width=True,
        )
    with controls[1]:
        st.caption(
            "Calendar results are cached for 24 hours. Use Refresh Calendar to request current dates."
        )

    if refresh:
        fetch_earnings_calendar.clear()

    with st.spinner("Loading available earnings dates..."):
        calendar = fetch_earnings_calendar(tickers)

    if calendar.empty:
        st.info("No earnings-calendar data is currently available for the Value universe.")
        return

    lookup_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Sector",
            "Forward PE",
            "FCF Yield",
            "Overall Score",
            "Rating",
            "Value Trap Risk",
            "Value Trap Rating",
        )
        if column in market.columns
    ]
    lookup = market[lookup_columns].drop_duplicates("Ticker")
    calendar = calendar.merge(lookup, on="Ticker", how="left")
    calendar["Date"] = calendar["Earnings Date"].dt.date

    today = date.today()
    range_choice = st.radio(
        "Calendar range",
        ["Next 7 days", "Next 30 days", "Next 90 days", "Recent 30 days"],
        horizontal=True,
    )

    if range_choice == "Next 7 days":
        start, end = today, today + timedelta(days=7)
    elif range_choice == "Next 30 days":
        start, end = today, today + timedelta(days=30)
    elif range_choice == "Next 90 days":
        start, end = today, today + timedelta(days=90)
    else:
        start, end = today - timedelta(days=30), today

    filtered = calendar[
        (calendar["Date"] >= start) & (calendar["Date"] <= end)
    ].copy()

    sectors = sorted(
        filtered.get("Sector", pd.Series(dtype=str))
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
    selected_sectors = st.multiselect(
        "Sectors",
        sectors,
        default=sectors,
    )
    if sectors and "Sector" in filtered.columns:
        filtered = filtered[filtered["Sector"].astype(str).isin(selected_sectors)]

    metrics = st.columns(5)
    metrics[0].metric("Events", f"{len(filtered):,}")
    metrics[1].metric("Companies", f"{filtered['Ticker'].nunique():,}")
    metrics[2].metric("Sectors", f"{filtered['Sector'].nunique():,}" if "Sector" in filtered.columns else "N/A")
    metrics[3].metric("Start", start.strftime("%b %d, %Y"))
    metrics[4].metric("End", end.strftime("%b %d, %Y"))

    if filtered.empty:
        st.info(
            f"No available Value-universe earnings dates fall between "
            f"{start:%b %d} and {end:%b %d, %Y}."
        )
        return

    st.divider()
    st.subheader("Earnings Schedule")

    display_columns = [
        column
        for column in (
            "Earnings Date",
            "Ticker",
            "Company",
            "Sector",
            "EPS Estimate",
            "Reported EPS",
            "EPS Surprise",
            "Forward PE",
            "FCF Yield",
            "Overall Score",
            "Rating",
            "Value Trap Risk",
            "Value Trap Rating",
        )
        if column in filtered.columns
    ]

    st.dataframe(
        filtered[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=column_config(),
    )

    st.divider()
    st.subheader("Events by Day")
    daily = filtered.groupby("Date", as_index=False).agg(Events=("Ticker", "count"))
    daily["Date"] = daily["Date"].astype(str)
    st.bar_chart(daily.set_index("Date")["Events"])

    st.divider()
    st.subheader("Higher-Risk Events to Review")
    risk_view = filtered.copy()
    if "Value Trap Risk" in risk_view.columns:
        risk_view = risk_view[
            pd.to_numeric(risk_view["Value Trap Risk"], errors="coerce") >= 50
        ].sort_values("Value Trap Risk", ascending=False)

    if risk_view.empty:
        st.info("No calendar events in this range have Value-Trap Risk of 50 or higher.")
    else:
        risk_columns = [
            column
            for column in (
                "Earnings Date",
                "Ticker",
                "Company",
                "Sector",
                "Overall Score",
                "Value Trap Risk",
                "Value Trap Rating",
            )
            if column in risk_view.columns
        ]
        st.dataframe(
            risk_view[risk_columns],
            use_container_width=True,
            hide_index=True,
            column_config=column_config(),
        )

    st.download_button(
        "Download Calendar CSV",
        data=filtered[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_value_calendar.csv",
        mime="text/csv",
        type="secondary",
    )

    st.caption(
        "Earnings dates and estimates can change. Confirm important dates with the company "
        "or another primary source before making an investment decision."
    )


show()

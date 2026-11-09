"""MarketScope Growth persistent watchlist page."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config import SECTOR_COLORS
from market_data import load_market_data


WATCHLIST_FILE = Path(__file__).resolve().parent.parent / "growth_watchlist.json"
SCORE_COLUMNS = [
    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",
    "Overall Score",
]


@st.cache_data(ttl=900, show_spinner=False)
def get_watchlist_market_data() -> pd.DataFrame:
    """Load the complete scored growth universe."""
    return load_market_data()


def load_watchlist() -> dict:
    """Load saved tickers and notes from the local JSON watchlist."""
    if not WATCHLIST_FILE.exists():
        return {"tickers": [], "notes": {}}

    try:
        payload = json.loads(WATCHLIST_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"tickers": [], "notes": {}}

    tickers = payload.get("tickers", []) if isinstance(payload, dict) else []
    notes = payload.get("notes", {}) if isinstance(payload, dict) else {}

    tickers = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    notes = notes if isinstance(notes, dict) else {}
    return {"tickers": tickers, "notes": notes}


def save_watchlist(tickers: list[str], notes: dict[str, str] | None = None) -> None:
    """Persist the watchlist locally."""
    clean_tickers = list(dict.fromkeys(str(t).strip().upper() for t in tickers if str(t).strip()))
    clean_notes = {
        ticker: str((notes or {}).get(ticker, "")).strip()
        for ticker in clean_tickers
        if str((notes or {}).get(ticker, "")).strip()
    }
    payload = {
        "tickers": clean_tickers,
        "notes": clean_notes,
        "updated_utc": datetime.now(timezone.utc).isoformat(),
    }
    WATCHLIST_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def column_config() -> dict:
    """Streamlit formatting for the watchlist table."""
    config = {
        "Ticker": st.column_config.TextColumn("Ticker", pinned=True),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="$%.0f"),
        "Revenue Growth": st.column_config.NumberColumn("Revenue Growth", format="%.1%%"),
        "Forward EPS Growth": st.column_config.NumberColumn("Forward EPS Growth", format="%.1%%"),
        "6M Return": st.column_config.NumberColumn("6M Return", format="%.1%%"),
        "12M Return": st.column_config.NumberColumn("12M Return", format="%.1%%"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "PEG": st.column_config.NumberColumn("PEG", format="%.2f"),
    }
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""), min_value=0, max_value=100, format="%.1f"
        )
    return config


def watchlist_table(data: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Build the display table in saved watchlist order."""
    if not tickers:
        return pd.DataFrame()

    lookup = data.copy()
    lookup["Ticker"] = lookup["Ticker"].astype(str).str.upper()
    lookup = lookup.set_index("Ticker", drop=False)

    rows = []
    for ticker in tickers:
        if ticker in lookup.index:
            row = lookup.loc[ticker]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            rows.append(row)

    if not rows:
        return pd.DataFrame()

    result = pd.DataFrame(rows).reset_index(drop=True)
    columns = [
        column for column in (
            "Ticker", "Company", "Sector", "Price", "Market Cap",
            "Revenue Growth", "Forward EPS Growth", "Forward PE", "PEG",
            "6M Return", "12M Return", "Growth Score", "Quality Score",
            "Valuation Score", "Momentum Score", "Overall Score", "Rating",
        ) if column in result.columns
    ]
    return result[columns]


def show() -> None:
    """Render the MarketScope Growth watchlist page."""
    st.title("⭐ Growth Watchlist")
    st.caption(
        "Save growth stocks you want to follow and monitor their MarketScope scores, "
        "growth metrics, valuation, and momentum in one place."
    )

    try:
        with st.spinner("Loading growth-stock data..."):
            market_data = get_watchlist_market_data()
    except Exception as exc:
        st.error("The watchlist could not load MarketScope Growth data.")
        st.exception(exc)
        return

    if market_data is None or market_data.empty or "Ticker" not in market_data.columns:
        st.warning("No growth-stock data is currently available.")
        return

    market_data = market_data.copy()
    market_data["Ticker"] = market_data["Ticker"].astype(str).str.upper()
    saved = load_watchlist()
    saved_tickers = saved["tickers"]
    saved_notes = saved["notes"]

    company_map = {
        row["Ticker"]: f'{row["Ticker"]} | {row.get("Company", row["Ticker"])}'
        for _, row in market_data.sort_values("Ticker").iterrows()
    }
    universe = list(company_map)

    st.subheader("Manage Watchlist")
    selected = st.multiselect(
        "Stocks",
        options=universe,
        default=[ticker for ticker in saved_tickers if ticker in universe],
        format_func=lambda ticker: company_map.get(ticker, ticker),
        placeholder="Choose growth stocks to monitor",
    )

    controls = st.columns([1, 1, 3])
    if controls[0].button("Save Watchlist", type="primary", use_container_width=True):
        save_watchlist(selected, saved_notes)
        st.success(f"Saved {len(selected)} stocks to your Growth watchlist.")
        st.rerun()

    if controls[1].button("Clear Watchlist", use_container_width=True):
        save_watchlist([], {})
        st.rerun()

    watchlist = watchlist_table(market_data, saved_tickers)
    if watchlist.empty:
        st.info("Your Growth watchlist is empty. Select stocks above and choose Save Watchlist.")
        return

    st.divider()

    overall = pd.to_numeric(watchlist.get("Overall Score"), errors="coerce")
    growth = pd.to_numeric(watchlist.get("Growth Score"), errors="coerce")
    momentum = pd.to_numeric(watchlist.get("Momentum Score"), errors="coerce")

    metrics = st.columns(4)
    metrics[0].metric("Watchlist Stocks", f"{len(watchlist):,}")
    metrics[1].metric("Average Overall", f"{overall.mean():.1f}" if overall.notna().any() else "N/A")
    metrics[2].metric("Average Growth", f"{growth.mean():.1f}" if growth.notna().any() else "N/A")
    metrics[3].metric("Average Momentum", f"{momentum.mean():.1f}" if momentum.notna().any() else "N/A")

    st.subheader("Watchlist Scores")
    st.dataframe(
        watchlist,
        use_container_width=True,
        hide_index=True,
        column_config=column_config(),
    )

    st.download_button(
        "Download Watchlist CSV",
        data=watchlist.to_csv(index=False).encode("utf-8"),
        file_name="marketscope_growth_watchlist.csv",
        mime="text/csv",
    )

    st.divider()

    chart_data = watchlist.dropna(subset=["Growth Score", "Overall Score"]).copy()
    if not chart_data.empty:
        st.subheader("Growth vs. Overall Score")
        figure = px.scatter(
            chart_data,
            x="Growth Score",
            y="Overall Score",
            color="Sector" if "Sector" in chart_data.columns else None,
            color_discrete_map=SECTOR_COLORS,
            text="Ticker",
            hover_name="Company" if "Company" in chart_data.columns else "Ticker",
            hover_data=[
                column for column in ("Momentum Score", "Valuation Score", "Rating")
                if column in chart_data.columns
            ],
        )
        figure.update_traces(textposition="top center")
        figure.update_xaxes(range=[0, 100])
        figure.update_yaxes(range=[0, 100])
        figure.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(figure, use_container_width=True)

    st.divider()
    st.subheader("Watchlist Notes")
    note_ticker = st.selectbox(
        "Stock",
        options=saved_tickers,
        format_func=lambda ticker: company_map.get(ticker, ticker),
        key="watchlist_note_ticker",
    )
    note_text = st.text_area(
        "Notes",
        value=saved_notes.get(note_ticker, ""),
        height=120,
        placeholder="Why are you watching this stock? Add catalysts, valuation targets, or research notes.",
    )

    if st.button("Save Note"):
        updated_notes = dict(saved_notes)
        if note_text.strip():
            updated_notes[note_ticker] = note_text.strip()
        else:
            updated_notes.pop(note_ticker, None)
        save_watchlist(saved_tickers, updated_notes)
        st.success(f"Saved note for {note_ticker}.")
        st.rerun()

    st.caption(
        "The watchlist is stored locally in growth_watchlist.json. On hosted Streamlit "
        "deployments, local app storage may not be permanent across restarts or redeployments."
    )
# =========================================================
# Run page
# =========================================================
show()
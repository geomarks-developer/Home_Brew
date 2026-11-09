"""MarketScope Value session watchlist page."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config import SECTOR_COLORS
from market_data import load_market_data


SCORE_COLUMNS = [
    "Valuation Score",
    "Quality Score",
    "Financial Strength Score",
    "Growth Score",
    "Momentum Score",
    "Overall Score",
]

PERCENT_COLUMNS = [
    "FCF Yield",
    "Earnings Yield",
    "Revenue Growth",
    "Earnings Growth",
    "6M Return",
    "12M Return",
]


def numeric(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def table_config() -> dict:
    config = {
        "Ticker": st.column_config.TextColumn("Ticker", pinned=True),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk",
            min_value=0,
            max_value=100,
            format="%.1f",
        ),
    }
    for column in PERCENT_COLUMNS:
        config[column] = st.column_config.NumberColumn(column, format="percent")
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )
    return config


def show() -> None:
    st.title("⭐ Value Watchlist")
    st.caption(
        "Keep a focused list of MarketScope Value candidates and monitor valuation, "
        "quality, momentum, and value-trap risk together."
    )

    try:
        with st.spinner("Loading MarketScope Value data..."):
            data = load_market_data()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    if data is None or data.empty or "Ticker" not in data.columns:
        st.warning("No watchlist data is currently available.")
        return

    data = data.copy()
    data["Ticker"] = data["Ticker"].astype(str).str.upper()
    data = data.drop_duplicates(subset="Ticker", keep="first")
    tickers = data["Ticker"].sort_values().tolist()

    if "value_watchlist" not in st.session_state:
        st.session_state.value_watchlist = []

    selected = st.multiselect(
        "Watchlist stocks",
        options=tickers,
        default=[ticker for ticker in st.session_state.value_watchlist if ticker in tickers],
        placeholder="Choose stocks to monitor...",
    )
    st.session_state.value_watchlist = selected

    control1, control2, control3 = st.columns([1, 1, 2])
    with control1:
        if st.button("Add Top 10 Value", type="secondary", use_container_width=True):
            leaders = (
                data.sort_values("Overall Score", ascending=False, na_position="last")
                .head(10)["Ticker"]
                .tolist()
            )
            st.session_state.value_watchlist = list(dict.fromkeys(selected + leaders))
            st.rerun()

    with control2:
        if st.button("Clear Watchlist", type="secondary", use_container_width=True):
            st.session_state.value_watchlist = []
            st.rerun()

    with control3:
        st.caption("The watchlist is kept for the current Streamlit session.")

    selected = st.session_state.value_watchlist
    if not selected:
        st.info("Choose stocks above, or add the current Top 10 Value candidates.")
        return

    watch = data[data["Ticker"].isin(selected)].copy()
    watch["Ticker"] = pd.Categorical(watch["Ticker"], categories=selected, ordered=True)
    watch = watch.sort_values("Ticker").reset_index(drop=True)
    watch["Ticker"] = watch["Ticker"].astype(str)

    # -----------------------------------------------------
    # Watchlist snapshot
    # -----------------------------------------------------
    metrics = st.columns(5)
    metrics[0].metric("Stocks", f"{len(watch)}")
    metrics[1].metric(
        "Median Overall",
        f"{numeric(watch, 'Overall Score').median():.1f}",
    )
    metrics[2].metric(
        "Median Valuation",
        f"{numeric(watch, 'Valuation Score').median():.1f}",
    )
    metrics[3].metric(
        "Median FCF Yield",
        f"{numeric(watch, 'FCF Yield').median():.1%}",
    )
    metrics[4].metric(
        "Median Trap Risk",
        f"{numeric(watch, 'Value Trap Risk').median():.1f}",
    )

    st.divider()
    st.subheader("Watchlist")

    display_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Sector",
            "Price",
            "Market Cap",
            "Forward PE",
            "Price/Book",
            "EV/EBITDA",
            "FCF Yield",
            "Revenue Growth",
            "Earnings Growth",
            "6M Return",
            "12M Return",
            "Valuation Score",
            "Quality Score",
            "Financial Strength Score",
            "Growth Score",
            "Momentum Score",
            "Overall Score",
            "Rating",
            "Value Trap Risk",
            "Value Trap Rating",
        )
        if column in watch.columns
    ]

    st.dataframe(
        watch[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=table_config(),
    )

    st.download_button(
        "Download Watchlist CSV",
        data=watch[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_value_watchlist.csv",
        mime="text/csv",
        type="secondary",
    )

    # -----------------------------------------------------
    # Opportunity map
    # -----------------------------------------------------
    st.divider()
    st.subheader("Watchlist Opportunity Map")
    chart = watch.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()
    if not chart.empty:
        chart["Market Cap ($B)"] = numeric(chart, "Market Cap") / 1_000_000_000
        chart["Bubble Size"] = numeric(chart, "Market Cap").clip(lower=1)
        fig = px.scatter(
            chart,
            x="Valuation Score",
            y="Value Trap Risk",
            size="Bubble Size",
            size_max=55,
            color="Sector" if "Sector" in chart.columns else "Ticker",
            color_discrete_map=SECTOR_COLORS,
            text="Ticker",
            hover_name="Company" if "Company" in chart.columns else "Ticker",
            hover_data={
                "Overall Score": ":.1f",
                "Quality Score": ":.1f",
                "Financial Strength Score": ":.1f",
                "FCF Yield": ":.1%",
                "Forward PE": ":.1f",
                "12M Return": ":.1%",
                "Market Cap ($B)": ":$.1f",
                "Bubble Size": False,
            },
        )
        fig.update_traces(textposition="top center")
        fig.add_vline(x=65, line_dash="dot", line_color="gray")
        fig.add_hline(y=50, line_dash="dot", line_color="gray")
        fig.update_xaxes(range=[0, 100], title="Valuation Score → more attractive")
        fig.update_yaxes(range=[100, 0], title="Value-Trap Risk → lower is better")
        fig.update_layout(height=550, legend_title="Sector")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Research buckets
    # -----------------------------------------------------
    st.divider()
    st.subheader("Research Buckets")
    attractive = watch[
        (numeric(watch, "Valuation Score") >= 65)
        & (numeric(watch, "Value Trap Risk") <= 35)
    ].copy()
    traps = watch[
        (numeric(watch, "Valuation Score") >= 60)
        & (numeric(watch, "Value Trap Risk") >= 50)
    ].copy()
    improving = watch[
        (numeric(watch, "6M Return") > 0)
        & (numeric(watch, "Price") > numeric(watch, "200D MA"))
    ].copy()

    tab1, tab2, tab3 = st.tabs(
        ["Attractive / Lower Risk", "Potential Value Traps", "Positive Momentum"]
    )
    bucket_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Forward PE",
            "FCF Yield",
            "Valuation Score",
            "Quality Score",
            "Overall Score",
            "Value Trap Risk",
            "6M Return",
            "12M Return",
        )
        if column in watch.columns
    ]

    for tab, frame, empty_message in (
        (tab1, attractive, "No watchlist stocks currently meet the attractive/lower-risk criteria."),
        (tab2, traps, "No watchlist stocks currently meet the potential value-trap criteria."),
        (tab3, improving, "No watchlist stocks currently meet the positive-momentum criteria."),
    ):
        with tab:
            if frame.empty:
                st.info(empty_message)
            else:
                st.dataframe(
                    frame[bucket_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config=table_config(),
                )

    st.caption(
        "The watchlist is a research organizer, not a recommendation list. Recheck valuation, "
        "fundamentals, value-trap signals, and current company developments before acting."
    )


show()

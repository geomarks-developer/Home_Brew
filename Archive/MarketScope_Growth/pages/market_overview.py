"""MarketScope Growth market overview page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import SECTOR_COLORS
from market_data import load_market_data

SCORES = ["Growth Score", "Quality Score", "Valuation Score", "Momentum Score", "Overall Score"]


@st.cache_data(ttl=900, show_spinner=False)
def get_overview_data() -> pd.DataFrame:
    return load_market_data()


def num(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(np.nan, index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def pct_count(series: pd.Series, condition) -> tuple[int, float]:
    values = pd.to_numeric(series, errors="coerce").dropna()
    if values.empty:
        return 0, np.nan
    count = int(condition(values).sum())
    return count, count / len(values)


def score_config() -> dict:
    cfg = {
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Revenue Growth": st.column_config.NumberColumn("Revenue Growth", format="%.1%%"),
        "Forward EPS Growth": st.column_config.NumberColumn("Forward EPS Growth", format="%.1%%"),
        "6M Return": st.column_config.NumberColumn("6M Return", format="percent"),
        "12M Return": st.column_config.NumberColumn("12M Return", format="percent"),
    }
    for col in SCORES:
        cfg[col] = st.column_config.ProgressColumn(
        col.replace(" Score", ""),
        min_value=0,
        max_value=100,
        format="%.1f",
        )
    return cfg


def show() -> None:
    st.title("🌐 Growth Market Overview")
    st.caption(
        "A high-level view of breadth, momentum, score leadership, and sector strength "
        "across the configured MarketScope Growth universe."
    )

    try:
        with st.spinner("Loading growth market overview..."):
            data = get_overview_data()
    except Exception as exc:
        st.error("The market overview could not load data.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No growth-stock data is currently available.")
        return

    data = data.copy()
    overall = num(data, "Overall Score")
    growth = num(data, "Growth Score")
    ret6 = num(data, "6M Return")
    ret12 = num(data, "12M Return")
    price = num(data, "Price")
    ma50 = num(data, "50D MA")
    ma200 = num(data, "200D MA")

    positive12_count, positive12_pct = pct_count(ret12, lambda x: x > 0)
    above50_count, above50_pct = pct_count((price / ma50) - 1, lambda x: x > 0)
    above200_count, above200_pct = pct_count((price / ma200) - 1, lambda x: x > 0)

    metrics = st.columns(6)
    metrics[0].metric("Stocks", f"{len(data):,}")
    metrics[1].metric("Avg Overall", f"{overall.mean():.1f}" if overall.notna().any() else "N/A")
    metrics[2].metric("Avg Growth", f"{growth.mean():.1f}" if growth.notna().any() else "N/A")
    metrics[3].metric("Positive 12M", f"{positive12_pct:.0%}" if np.isfinite(positive12_pct) else "N/A", f"{positive12_count} stocks")
    metrics[4].metric("Above 50D MA", f"{above50_pct:.0%}" if np.isfinite(above50_pct) else "N/A", f"{above50_count} stocks")
    metrics[5].metric("Above 200D MA", f"{above200_pct:.0%}" if np.isfinite(above200_pct) else "N/A", f"{above200_count} stocks")

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Score Distribution")
        score_frame = data[[c for c in SCORES if c in data.columns]].melt(var_name="Category", value_name="Score").dropna()
        if not score_frame.empty:
            fig = px.box(score_frame, x="Category", y="Score", points=False)
            fig.update_yaxes(range=[0, 100])
            fig.update_layout(height=430, xaxis_title="", margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Momentum Breadth")
        breadth = pd.DataFrame({
            "Measure": ["Positive 12M Return", "Above 50D MA", "Above 200D MA"],
            "Percent": [positive12_pct, above50_pct, above200_pct],
        }).dropna()
        if not breadth.empty:
            breadth["Percent Display"] = breadth["Percent"] * 100
            fig = px.bar(breadth, x="Measure", y="Percent Display", text_auto=".0f")
            fig.update_traces(texttemplate="%{y:.0f}%", textposition="outside")
            fig.update_yaxes(range=[0, 105], title="Stocks (%)")
            fig.update_layout(height=430, xaxis_title="", showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Sector Landscape")
    if "Sector" in data.columns:
        work = data.assign(Sector=data["Sector"].fillna("Unknown"))
        agg = {"Stocks": ("Ticker", "count")}
        for col in ("Overall Score", "Growth Score", "Momentum Score"):
            if col in work.columns:
                agg[col] = (col, "mean")
        sectors = work.groupby("Sector", as_index=False).agg(**agg)
        sectors = sectors.sort_values("Overall Score", ascending=False, na_position="last")

        fig = px.scatter(
            sectors,
            x="Growth Score",
            y="Momentum Score",
            size="Stocks",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            text="Sector",
            hover_data=["Overall Score", "Stocks"],
            size_max=55,
        )
        fig.update_traces(textposition="top center")
        fig.update_xaxes(range=[0, 100])
        fig.update_yaxes(range=[0, 100])
        fig.update_layout(height=540, showlegend=False, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    leaders_col, movers_col = st.columns(2)

    with leaders_col:
        st.subheader("Overall Leaders")
        leaders = data.sort_values("Overall Score", ascending=False, na_position="last").head(10)
        cols = [c for c in ("Ticker", "Company", "Sector", "Growth Score", "Quality Score", "Momentum Score", "Overall Score", "Rating") if c in leaders.columns]
        st.dataframe(leaders[cols], use_container_width=True, hide_index=True, column_config=score_config())

    with movers_col:
        st.subheader("12-Month Momentum Leaders")
        movers = data.sort_values("12M Return", ascending=False, na_position="last").head(10)
        cols = [c for c in ("Ticker", "Company", "12M Return", "6M Return", "Growth Score", "Momentum Score", "Overall Score") if c in movers.columns]
        st.dataframe(movers[cols], use_container_width=True, hide_index=True, column_config=score_config())

    st.divider()
    st.subheader("Growth vs. Momentum")
    chart = data.dropna(subset=["Growth Score", "Momentum Score"]).copy()
    if not chart.empty:
        kwargs = dict(
            data_frame=chart,
            x="Growth Score",
            y="Momentum Score",
            color="Sector" if "Sector" in chart.columns else None,
            color_discrete_map=SECTOR_COLORS,
            hover_name="Ticker" if "Ticker" in chart.columns else None,
            hover_data=[c for c in ("Company", "Overall Score", "12M Return", "Rating") if c in chart.columns],
        )
        if "Market Cap" in chart.columns:
            chart["Chart Size"] = num(chart, "Market Cap").clip(lower=1)
            kwargs["size"] = "Chart Size"
            kwargs["size_max"] = 38
        fig = px.scatter(**kwargs)
        fig.add_vline(x=65, line_dash="dot", line_color="#888888")
        fig.add_hline(y=65, line_dash="dot", line_color="#888888")
        fig.update_xaxes(range=[0, 100])
        fig.update_yaxes(range=[0, 100])
        fig.update_layout(height=560, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "Overview statistics describe only the configured MarketScope Growth universe. "
        "They are quantitative research measures, not a forecast or investment recommendation."
    )


# =========================================================
# Run page
# =========================================================
show()
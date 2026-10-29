"""MarketScope Value market overview dashboard."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config import DEFAULT_TOP_N, SECTOR_COLORS
from market_data import cache_age_hours, load_market_bundle


SCORE_COLUMNS = [
    "Valuation Score",
    "Quality Score",
    "Financial Strength Score",
    "Growth Score",
    "Momentum Score",
    "Overall Score",
]


def numeric(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def metric_text(data: pd.DataFrame, column: str, mode: str = "median") -> str:
    values = numeric(data, column).dropna()
    if values.empty:
        return "N/A"
    value = values.mean() if mode == "mean" else values.median()
    return f"{value:.1f}"


def score_config() -> dict:
    config = {
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "Price/Sales": st.column_config.NumberColumn("P/S", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "FCF Yield": st.column_config.NumberColumn("FCF Yield", format="percent"),
        "Revenue Growth": st.column_config.NumberColumn("Revenue Growth", format="percent"),
        "Earnings Growth": st.column_config.NumberColumn("Earnings Growth", format="percent"),
        "6M Return": st.column_config.NumberColumn("6M Return", format="percent"),
        "12M Return": st.column_config.NumberColumn("12M Return", format="percent"),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk", min_value=0, max_value=100, format="%.1f"
        ),
    }
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )
    return config


def show() -> None:
    st.title("🌐 Value Market Overview")
    st.caption(
        "Assess valuation breadth, market participation, sector opportunity, momentum, "
        "and value-trap risk across the MarketScope Value universe."
    )

    refresh_col, status_col = st.columns([1, 3])
    with refresh_col:
        refresh = st.button(
            "🔄 Refresh Market Data",
            type="secondary",
            use_container_width=True,
        )

    try:
        bundle = load_market_bundle(
            force_refresh=refresh,
            show_progress=refresh,
        )
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    data = bundle.get("data", pd.DataFrame()).copy()
    metadata = bundle.get("metadata", {})
    if data.empty:
        st.warning("No MarketScope Value market data is currently available.")
        return

    if "Sector" not in data.columns:
        data["Sector"] = "Unknown"
    data["Sector"] = data["Sector"].fillna("Unknown").replace("", "Unknown")

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
            f"Source: {metadata.get('loaded_from', 'Unknown')}  |  {age_text}  |  "
            f"Universe: {metadata.get('ticker_count', len(data))} stocks"
        )

    if metadata.get("stale"):
        st.warning("Fresh market data was unavailable, so the last saved Value cache is displayed.")

    # -----------------------------------------------------
    # Market snapshot
    # -----------------------------------------------------
    st.subheader("Market Snapshot")
    metrics = st.columns(6)
    metrics[0].metric("Stocks", f"{len(data):,}")
    metrics[1].metric("Median Overall", metric_text(data, "Overall Score"))
    metrics[2].metric("Median Valuation", metric_text(data, "Valuation Score"))
    metrics[3].metric("Median Quality", metric_text(data, "Quality Score"))
    metrics[4].metric("Median Momentum", metric_text(data, "Momentum Score"))
    metrics[5].metric("Median Trap Risk", metric_text(data, "Value Trap Risk"))

    # -----------------------------------------------------
    # Breadth
    # -----------------------------------------------------
    st.divider()
    st.subheader("Value Breadth")

    total = len(data)
    attractive = int((numeric(data, "Valuation Score") >= 65).sum())
    lower_risk = int((numeric(data, "Value Trap Risk") <= 35).sum())
    attractive_low_risk = int(
        ((numeric(data, "Valuation Score") >= 65) & (numeric(data, "Value Trap Risk") <= 35)).sum()
    )
    positive_momentum = int((numeric(data, "12M Return") > 0).sum())
    above_200 = int((numeric(data, "Price") > numeric(data, "200D MA")).sum())

    breadth_cols = st.columns(5)
    breadth_cols[0].metric("Attractive Valuation", f"{attractive}", f"{attractive / total:.0%} of universe")
    breadth_cols[1].metric("Lower Trap Risk", f"{lower_risk}", f"{lower_risk / total:.0%} of universe")
    breadth_cols[2].metric("Attractive + Lower Risk", f"{attractive_low_risk}", f"{attractive_low_risk / total:.0%}")
    breadth_cols[3].metric("Positive 12M Return", f"{positive_momentum}", f"{positive_momentum / total:.0%}")
    breadth_cols[4].metric("Above 200D MA", f"{above_200}", f"{above_200 / total:.0%}")

    st.divider()

    # -----------------------------------------------------
    # Valuation / risk landscape
    # -----------------------------------------------------
    st.subheader("Value Opportunity Landscape")
    chart = data.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()
    if not chart.empty:
        chart["Market Cap ($B)"] = numeric(chart, "Market Cap") / 1_000_000_000
        chart["Bubble Size"] = numeric(chart, "Market Cap").clip(lower=1)
        hover_data = {
            "Valuation Score": ":.1f",
            "Value Trap Risk": ":.1f",
            "Overall Score": ":.1f",
            "Quality Score": ":.1f",
            "Financial Strength Score": ":.1f",
            "FCF Yield": ":.1%",
            "Forward PE": ":.1f",
            "12M Return": ":.1%",
            "Market Cap ($B)": ":$.1f",
            "Bubble Size": False,
        }
        for optional in ("Company", "Rating", "Value Trap Rating"):
            if optional in chart.columns:
                hover_data[optional] = True

        fig = px.scatter(
            chart,
            x="Valuation Score",
            y="Value Trap Risk",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            size="Bubble Size",
            size_max=45,
            hover_name="Ticker",
            hover_data=hover_data,
        )
        fig.add_vline(x=65, line_dash="dot", line_color="gray")
        fig.add_hline(y=50, line_dash="dot", line_color="gray")
        fig.update_xaxes(range=[0, 100], title="Valuation Score → more attractive")
        fig.update_yaxes(range=[100, 0], title="Value-Trap Risk → lower is better")
        fig.update_layout(height=580, margin=dict(l=10, r=10, t=20, b=10), legend_title="Sector")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Sector overview
    # -----------------------------------------------------
    st.divider()
    st.subheader("Sector Opportunity")
    sector_summary = (
        data.groupby("Sector", as_index=False)
        .agg(
            Stocks=("Ticker", "count"),
            Overall=("Overall Score", "median"),
            Valuation=("Valuation Score", "median"),
            Quality=("Quality Score", "median"),
            Strength=("Financial Strength Score", "median"),
            Momentum=("Momentum Score", "median"),
            Trap_Risk=("Value Trap Risk", "median"),
        )
        .sort_values("Overall", ascending=True)
    )

    left, right = st.columns(2)
    with left:
        fig = px.bar(
            sector_summary,
            x="Overall",
            y="Sector",
            orientation="h",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            custom_data=["Valuation", "Quality", "Strength", "Trap_Risk", "Stocks"],
            title="Median Overall Score by Sector",
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>Overall: %{x:.1f}<br>Valuation: %{customdata[0]:.1f}<br>"
                "Quality: %{customdata[1]:.1f}<br>Strength: %{customdata[2]:.1f}<br>"
                "Trap Risk: %{customdata[3]:.1f}<br>Stocks: %{customdata[4]}<extra></extra>"
            )
        )
        fig.update_xaxes(range=[0, 100])
        fig.update_layout(height=500, showlegend=False, xaxis_title="Score", yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        fig = px.scatter(
            sector_summary,
            x="Valuation",
            y="Trap_Risk",
            size="Stocks",
            size_max=55,
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            hover_name="Sector",
            hover_data={"Overall": ":.1f", "Quality": ":.1f", "Strength": ":.1f", "Stocks": True},
            title="Sector Valuation vs. Trap Risk",
        )
        fig.add_vline(x=65, line_dash="dot", line_color="gray")
        fig.add_hline(y=50, line_dash="dot", line_color="gray")
        fig.update_xaxes(range=[0, 100], title="Valuation")
        fig.update_yaxes(range=[100, 0], title="Trap Risk")
        fig.update_layout(height=500, legend_title="Sector")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Leaders
    # -----------------------------------------------------
    st.divider()
    st.subheader("Market Leaders")
    overall_tab, valuation_tab, momentum_tab, trap_tab = st.tabs(
        ["Overall", "Valuation", "Momentum", "Lowest Trap Risk"]
    )

    table_columns = [
        column for column in (
            "Ticker", "Company", "Sector", "Price", "Market Cap", "Forward PE", "FCF Yield",
            "Valuation Score", "Quality Score", "Financial Strength Score", "Momentum Score",
            "Overall Score", "Value Trap Risk", "Rating"
        ) if column in data.columns
    ]

    for tab, column, ascending in (
        (overall_tab, "Overall Score", False),
        (valuation_tab, "Valuation Score", False),
        (momentum_tab, "Momentum Score", False),
        (trap_tab, "Value Trap Risk", True),
    ):
        with tab:
            leaders = data.sort_values(column, ascending=ascending, na_position="last").head(DEFAULT_TOP_N)
            st.dataframe(
                leaders[table_columns],
                use_container_width=True,
                hide_index=True,
                column_config=score_config(),
            )

    st.caption(
        "MarketScope Value overview statistics describe the configured research universe. "
        "Value scores and value-trap indicators are quantitative screening measures, not investment recommendations."
    )


show()

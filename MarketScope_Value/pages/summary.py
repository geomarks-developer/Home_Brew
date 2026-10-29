"""MarketScope Value summary dashboard."""
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


def median_text(data: pd.DataFrame, column: str) -> str:
    value = numeric(data, column).median()
    return "N/A" if pd.isna(value) else f"{value:.1f}"


def value_table_config() -> dict:
    config = {
        "Rank": st.column_config.NumberColumn("#", format="%d"),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "Price/Sales": st.column_config.NumberColumn("P/S", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "FCF Yield": st.column_config.NumberColumn("FCF Yield", format="percent"),
        "Earnings Yield": st.column_config.NumberColumn("Earnings Yield", format="percent"),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk",
            min_value=0,
            max_value=100,
            format="%.1f",
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
    st.title("💎 Value Summary")
    st.caption(
        "A high-level view of valuation, quality, financial strength, growth, momentum, "
        "and potential value-trap risk across the MarketScope Value universe."
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
        st.error("MarketScope Value could not load market data.")
        st.exception(exc)
        return

    data = bundle.get("data", pd.DataFrame()).copy()
    metadata = bundle.get("metadata", {})

    if data.empty:
        st.warning("No MarketScope Value data is currently available.")
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
            f"Source: {metadata.get('loaded_from', 'Unknown')}  |  {age_text}  |  "
            f"Price histories: {metadata.get('history_count', 0)}/{metadata.get('ticker_count', len(data))}"
        )

    if metadata.get("stale"):
        st.warning("Fresh market data was unavailable, so the last saved MarketScope Value cache is displayed.")

    # -----------------------------------------------------
    # Headline metrics
    # -----------------------------------------------------
    metrics = st.columns(6)
    metrics[0].metric("Stocks", f"{len(data):,}")
    metrics[1].metric("Median Overall", median_text(data, "Overall Score"))
    metrics[2].metric("Median Valuation", median_text(data, "Valuation Score"))
    metrics[3].metric("Median Quality", median_text(data, "Quality Score"))
    metrics[4].metric("Median Strength", median_text(data, "Financial Strength Score"))
    metrics[5].metric("Median Trap Risk", median_text(data, "Value Trap Risk"))

    st.divider()

    # -----------------------------------------------------
    # Top value opportunities
    # -----------------------------------------------------
    st.subheader("🏆 Top Value Opportunities")
    st.caption("Highest Overall Scores, with value-trap risk visible alongside the ranking.")

    leaders = (
        data.sort_values("Overall Score", ascending=False, na_position="last")
        .head(min(DEFAULT_TOP_N, len(data)))
        .copy()
    )

    leader_columns = [
        column
        for column in (
            "Rank",
            "Ticker",
            "Company",
            "Sector",
            "Price",
            "Market Cap",
            "Forward PE",
            "FCF Yield",
            "Valuation Score",
            "Quality Score",
            "Financial Strength Score",
            "Overall Score",
            "Rating",
            "Value Trap Risk",
            "Value Trap Rating",
        )
        if column in leaders.columns
    ]

    st.dataframe(
        leaders[leader_columns],
        use_container_width=True,
        hide_index=True,
        column_config=value_table_config(),
    )

    st.divider()

    # -----------------------------------------------------
    # Attractive value vs value traps
    # -----------------------------------------------------
    left, right = st.columns(2)

    with left:
        st.subheader("💎 Attractive Value / Lower Trap Risk")
        candidates = data.copy()
        candidates = candidates[
            (numeric(candidates, "Valuation Score") >= 65)
            & (numeric(candidates, "Value Trap Risk") <= 35)
        ]
        candidates = candidates.sort_values(
            ["Overall Score", "Valuation Score"],
            ascending=[False, False],
            na_position="last",
        ).head(10)

        columns = [
            column
            for column in (
                "Ticker",
                "Company",
                "Forward PE",
                "FCF Yield",
                "Valuation Score",
                "Overall Score",
                "Value Trap Risk",
            )
            if column in candidates.columns
        ]

        if candidates.empty:
            st.info("No stocks currently meet the lower-risk value criteria.")
        else:
            st.dataframe(
                candidates[columns],
                use_container_width=True,
                hide_index=True,
                column_config=value_table_config(),
            )

    with right:
        st.subheader("⚠️ Potential Value Traps")
        traps = data.copy()
        traps = traps[
            (numeric(traps, "Valuation Score") >= 60)
            & (numeric(traps, "Value Trap Risk") >= 50)
        ]
        traps = traps.sort_values(
            ["Value Trap Risk", "Valuation Score"],
            ascending=[False, False],
            na_position="last",
        ).head(10)

        columns = [
            column
            for column in (
                "Ticker",
                "Company",
                "Forward PE",
                "FCF Yield",
                "Valuation Score",
                "Quality Score",
                "Value Trap Risk",
                "Value Trap Rating",
            )
            if column in traps.columns
        ]

        if traps.empty:
            st.info("No high-risk value candidates currently meet the trap criteria.")
        else:
            st.dataframe(
                traps[columns],
                use_container_width=True,
                hide_index=True,
                column_config=value_table_config(),
            )

    st.divider()

    # -----------------------------------------------------
    # Value vs value trap chart
    # -----------------------------------------------------
    st.subheader("Valuation vs. Value-Trap Risk")
    chart = data.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()

    if not chart.empty:
        chart["Market Cap ($B)"] = numeric(chart, "Market Cap") / 1_000_000_000
        chart["Bubble Size"] = numeric(chart, "Market Cap").clip(lower=1)

        hover_data = {
            "Valuation Score": ":.1f",
            "Value Trap Risk": ":.1f",
            "Overall Score": ":.1f" if "Overall Score" in chart.columns else False,
            "Market Cap ($B)": ":$.1f",
            "Bubble Size": False,
        }
        for optional in ("Company", "Rating", "Value Trap Rating"):
            if optional in chart.columns:
                hover_data[optional] = True

        figure = px.scatter(
            chart,
            x="Valuation Score",
            y="Value Trap Risk",
            color="Sector" if "Sector" in chart.columns else None,
            color_discrete_map=SECTOR_COLORS,
            size="Bubble Size",
            size_max=42,
            hover_name="Ticker" if "Ticker" in chart.columns else None,
            hover_data=hover_data,
        )
        figure.add_vline(x=65, line_dash="dot", line_color="gray")
        figure.add_hline(y=50, line_dash="dot", line_color="gray")
        figure.update_xaxes(range=[0, 100], title="Valuation Score → more attractive")
        figure.update_yaxes(range=[100, 0], title="Value-Trap Risk → lower is better")
        figure.update_layout(
            height=560,
            margin=dict(l=10, r=10, t=20, b=10),
            legend_title="Sector",
        )
        st.plotly_chart(figure, use_container_width=True)
    else:
        st.info("Valuation and value-trap scores are not currently available for charting.")

    st.divider()

    # -----------------------------------------------------
    # Sector summary
    # -----------------------------------------------------
    st.subheader("🏭 Value by Sector")
    if "Sector" in data.columns:
        sector_source = data.copy()
        sector_source["Sector"] = sector_source["Sector"].fillna("Unknown")
        sector_summary = (
            sector_source.groupby("Sector", as_index=False)
            .agg(
                Stocks=("Ticker", "count"),
                Median_Overall=("Overall Score", "median"),
                Median_Valuation=("Valuation Score", "median"),
                Median_Trap_Risk=("Value Trap Risk", "median"),
            )
            .sort_values("Median_Overall", ascending=True)
        )

        figure = px.bar(
            sector_summary,
            x="Median_Overall",
            y="Sector",
            orientation="h",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            custom_data=["Median_Valuation", "Median_Trap_Risk", "Stocks"],
        )
        figure.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Median Overall: %{x:.1f}<br>"
                "Median Valuation: %{customdata[0]:.1f}<br>"
                "Median Trap Risk: %{customdata[1]:.1f}<br>"
                "Stocks: %{customdata[2]}<extra></extra>"
            )
        )
        figure.update_layout(
            height=500,
            showlegend=False,
            xaxis_title="Median Overall Score",
            yaxis_title="",
            margin=dict(l=10, r=10, t=10, b=10),
        )
        figure.update_xaxes(range=[0, 100])
        st.plotly_chart(figure, use_container_width=True)

    st.caption(
        "MarketScope Value scores are quantitative research indicators. A high Valuation Score can coexist "
        "with high Value-Trap Risk, so valuation should be reviewed together with quality, financial strength, "
        "growth, momentum, and company-specific research."
    )


show()

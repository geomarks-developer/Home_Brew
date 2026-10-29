"""MarketScope Value sector analysis page."""
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


def first_existing(data: pd.DataFrame, *columns: str) -> str | None:
    return next((column for column in columns if column in data.columns), None)


def build_sector_summary(data: pd.DataFrame) -> pd.DataFrame:
    source = data.copy()
    source["Sector"] = source["Sector"].fillna("Unknown").replace("", "Unknown")

    aggregations: dict[str, tuple[str, str]] = {
        "Stocks": ("Ticker", "count"),
    }

    median_columns = [
        ("Market Cap", "Median Market Cap"),
        ("Forward PE", "Forward PE"),
        ("Price/Book", "Price/Book"),
        ("Price/Sales", "Price/Sales"),
        ("EV/EBITDA", "EV/EBITDA"),
        ("FCF Yield", "FCF Yield"),
        ("Earnings Yield", "Earnings Yield"),
        ("Revenue Growth", "Revenue Growth"),
        ("Earnings Growth", "Earnings Growth"),
        ("6M Return", "6M Return"),
        ("12M Return", "12M Return"),
        ("Valuation Score", "Valuation Score"),
        ("Quality Score", "Quality Score"),
        ("Financial Strength Score", "Financial Strength Score"),
        ("Growth Score", "Growth Score"),
        ("Momentum Score", "Momentum Score"),
        ("Overall Score", "Overall Score"),
        ("Value Trap Risk", "Value Trap Risk"),
    ]

    for source_column, result_column in median_columns:
        if source_column in source.columns:
            aggregations[result_column] = (source_column, "median")

    summary = source.groupby("Sector", as_index=False).agg(**aggregations)
    if "Overall Score" in summary.columns:
        summary = summary.sort_values("Overall Score", ascending=False, na_position="last")
    summary.insert(0, "Rank", range(1, len(summary) + 1))
    return summary.reset_index(drop=True)


def sector_table_config() -> dict:
    config = {
        "Rank": st.column_config.NumberColumn("#", format="%d"),
        "Stocks": st.column_config.NumberColumn("Stocks", format="%d"),
        "Median Market Cap": st.column_config.NumberColumn("Median Market Cap", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "Price/Sales": st.column_config.NumberColumn("P/S", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk", min_value=0, max_value=100, format="%.1f"
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


def stock_table_config() -> dict:
    config = sector_table_config()
    config.update(
        {
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        }
    )
    return config


def show() -> None:
    st.title("🧩 Value by Sector")
    st.caption(
        "Compare valuation, quality, financial strength, market performance, and value-trap risk across sectors."
    )

    try:
        with st.spinner("Loading MarketScope Value sector data..."):
            data = load_market_data()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No MarketScope Value data is currently available.")
        return

    data = data.copy()
    if "Sector" not in data.columns:
        data["Sector"] = "Unknown"
    data["Sector"] = data["Sector"].fillna("Unknown").replace("", "Unknown")

    sector_summary = build_sector_summary(data)
    if sector_summary.empty:
        st.info("Sector summary data is unavailable.")
        return

    top_sector = sector_summary.iloc[0]
    lowest_trap = (
        sector_summary.sort_values("Value Trap Risk", ascending=True, na_position="last").iloc[0]
        if "Value Trap Risk" in sector_summary.columns
        else None
    )
    best_valuation = (
        sector_summary.sort_values("Valuation Score", ascending=False, na_position="last").iloc[0]
        if "Valuation Score" in sector_summary.columns
        else None
    )

    metrics = st.columns(4)
    metrics[0].metric("Sectors", f"{len(sector_summary)}")
    metrics[1].metric(
        "Highest Overall",
        str(top_sector["Sector"]),
        f"{top_sector.get('Overall Score', float('nan')):.1f}" if pd.notna(top_sector.get("Overall Score")) else None,
    )
    metrics[2].metric(
        "Best Valuation",
        str(best_valuation["Sector"]) if best_valuation is not None else "N/A",
        f"{best_valuation.get('Valuation Score'):.1f}" if best_valuation is not None and pd.notna(best_valuation.get("Valuation Score")) else None,
    )
    metrics[3].metric(
        "Lowest Trap Risk",
        str(lowest_trap["Sector"]) if lowest_trap is not None else "N/A",
        f"{lowest_trap.get('Value Trap Risk'):.1f}" if lowest_trap is not None and pd.notna(lowest_trap.get("Value Trap Risk")) else None,
    )

    st.divider()
    st.subheader("Sector Scorecard")

    scorecard_columns = [
        column
        for column in (
            "Rank",
            "Sector",
            "Stocks",
            "Median Market Cap",
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
            "Value Trap Risk",
        )
        if column in sector_summary.columns
    ]

    st.dataframe(
        sector_summary[scorecard_columns],
        use_container_width=True,
        hide_index=True,
        column_config=sector_table_config(),
    )

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Overall Value Leadership")
        if "Overall Score" in sector_summary.columns:
            chart = sector_summary.sort_values("Overall Score", ascending=True).copy()
            fig = px.bar(
                chart,
                x="Overall Score",
                y="Sector",
                orientation="h",
                color="Sector",
                color_discrete_map=SECTOR_COLORS,
                custom_data=[
                    column
                    for column in ["Valuation Score", "Value Trap Risk", "Stocks"]
                    if column in chart.columns
                ],
            )
            fig.update_xaxes(range=[0, 100])
            fig.update_layout(
                height=500,
                showlegend=False,
                xaxis_title="Median Overall Score",
                yaxis_title="",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Value-Trap Risk by Sector")
        if "Value Trap Risk" in sector_summary.columns:
            chart = sector_summary.dropna(subset=["Value Trap Risk"]).sort_values(
                "Value Trap Risk", ascending=False
            )
            fig = px.bar(
                chart,
                x="Value Trap Risk",
                y="Sector",
                orientation="h",
                color="Value Trap Risk",
                color_continuous_scale="RdYlGn_r",
                text="Value Trap Risk",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_xaxes(range=[0, 100])
            fig.update_layout(
                height=500,
                showlegend=False,
                coloraxis_showscale=False,
                xaxis_title="Median Value-Trap Risk",
                yaxis_title="",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Valuation vs. Value-Trap Risk by Sector")

    if {"Valuation Score", "Value Trap Risk"}.issubset(sector_summary.columns):
        scatter = sector_summary.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()
        if not scatter.empty:
            scatter["Bubble Size"] = numeric(scatter, "Stocks").clip(lower=1)
            fig = px.scatter(
                scatter,
                x="Valuation Score",
                y="Value Trap Risk",
                size="Bubble Size",
                size_max=55,
                color="Sector",
                color_discrete_map=SECTOR_COLORS,
                hover_name="Sector",
                hover_data={
                    "Overall Score": ":.1f" if "Overall Score" in scatter.columns else False,
                    "Quality Score": ":.1f" if "Quality Score" in scatter.columns else False,
                    "Financial Strength Score": ":.1f" if "Financial Strength Score" in scatter.columns else False,
                    "Stocks": True,
                    "Bubble Size": False,
                },
            )
            fig.add_vline(x=65, line_dash="dot", line_color="gray")
            fig.add_hline(y=50, line_dash="dot", line_color="gray")
            fig.update_xaxes(range=[0, 100], title="Valuation Score → more attractive")
            fig.update_yaxes(range=[100, 0], title="Value-Trap Risk → lower is better")
            fig.update_layout(height=560, legend_title="Sector")
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("Sector Detail")

    selected_sector = st.selectbox(
        "Choose a sector",
        sector_summary["Sector"].astype(str).tolist(),
    )
    sector_stocks = data[data["Sector"].astype(str) == selected_sector].copy()
    sector_stocks = sector_stocks.sort_values("Overall Score", ascending=False, na_position="last")

    detail_metrics = st.columns(4)
    detail_metrics[0].metric("Stocks", f"{len(sector_stocks)}")
    detail_metrics[1].metric(
        "Median Valuation",
        f"{numeric(sector_stocks, 'Valuation Score').median():.1f}",
    )
    detail_metrics[2].metric(
        "Median Overall",
        f"{numeric(sector_stocks, 'Overall Score').median():.1f}",
    )
    detail_metrics[3].metric(
        "Median Trap Risk",
        f"{numeric(sector_stocks, 'Value Trap Risk').median():.1f}",
    )

    detail_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Price",
            "Market Cap",
            "Forward PE",
            "Price/Book",
            "EV/EBITDA",
            "FCF Yield",
            "Revenue Growth",
            "Earnings Growth",
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
        if column in sector_stocks.columns
    ]

    st.dataframe(
        sector_stocks[detail_columns],
        use_container_width=True,
        hide_index=True,
        column_config=stock_table_config(),
    )

    st.caption(
        "Sector medians help compare groups, but valuation norms differ significantly by industry and business model. "
        "Use sector results as context rather than as a substitute for company-level analysis."
    )


show()

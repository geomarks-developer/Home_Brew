"""MarketScope Value value-trap risk dashboard."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import SECTOR_COLORS
from market_data import load_market_data
from value_engine import calculate_scores


RISK_COMPONENT_LABELS = {
    "negative_revenue_growth": "Revenue deterioration",
    "negative_earnings_growth": "Earnings deterioration",
    "negative_free_cash_flow": "Negative free cash flow",
    "weak_profitability": "Weak profitability",
    "high_net_debt": "High net debt",
    "below_200dma": "Below 200-day average",
    "weak_12m_return": "Weak 12-month return",
    "low_quality_score": "Low quality score",
}

PERCENT_COLUMNS = [
    "FCF Yield",
    "Revenue Growth",
    "Earnings Growth",
    "Profit Margin",
    "Net Debt/Market Cap",
    "6M Return",
    "12M Return",
]

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


def table_config() -> dict:
    config = {
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "Debt/Equity": st.column_config.NumberColumn("Debt/Equity", format="%.1f"),
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


def risk_band(value: object) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return "Insufficient Data"
    if not np.isfinite(score):
        return "Insufficient Data"
    if score >= 75:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 25:
        return "Moderate"
    return "Low"


def component_matrix(data: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for _, record in data.iterrows():
        result = calculate_scores(record.to_dict())
        components = result.get("Value Trap Components", {})
        row: dict[str, object] = {
            "Ticker": record.get("Ticker"),
            "Company": record.get("Company"),
            "Sector": record.get("Sector"),
        }
        row.update(components)
        rows.append(row)
    return pd.DataFrame(rows)


def show() -> None:
    st.title("⚠️ Value Trap Dashboard")
    st.caption(
        "Identify companies that appear inexpensive but also show deterioration, weak cash generation, "
        "leverage, profitability, or momentum warning signs."
    )

    try:
        with st.spinner("Loading MarketScope Value risk data..."):
            data = load_market_data()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No value-trap data is currently available.")
        return

    data = data.copy()
    if "Sector" not in data.columns:
        data["Sector"] = "Unknown"
    data["Sector"] = data["Sector"].fillna("Unknown").replace("", "Unknown")
    data["Risk Band"] = data["Value Trap Risk"].apply(risk_band)

    # -----------------------------------------------------
    # Headline risk metrics
    # -----------------------------------------------------
    high = int((numeric(data, "Value Trap Risk") >= 75).sum())
    elevated = int(
        ((numeric(data, "Value Trap Risk") >= 50) & (numeric(data, "Value Trap Risk") < 75)).sum()
    )
    cheap_high_risk = int(
        ((numeric(data, "Valuation Score") >= 65) & (numeric(data, "Value Trap Risk") >= 50)).sum()
    )
    low_risk_value = int(
        ((numeric(data, "Valuation Score") >= 65) & (numeric(data, "Value Trap Risk") <= 35)).sum()
    )

    metrics = st.columns(5)
    metrics[0].metric("Stocks", f"{len(data):,}")
    metrics[1].metric("High Trap Risk", f"{high}")
    metrics[2].metric("Elevated Trap Risk", f"{elevated}")
    metrics[3].metric("Cheap + Risky", f"{cheap_high_risk}")
    metrics[4].metric("Value + Lower Risk", f"{low_risk_value}")

    # -----------------------------------------------------
    # Filters
    # -----------------------------------------------------
    st.divider()
    filter_cols = st.columns(4)
    sectors = sorted(data["Sector"].astype(str).unique())
    with filter_cols[0]:
        selected_sectors = st.multiselect("Sectors", sectors, default=sectors)
    with filter_cols[1]:
        minimum_valuation = st.slider("Minimum Valuation Score", 0.0, 100.0, 0.0, 1.0)
    with filter_cols[2]:
        minimum_risk = st.slider("Minimum Trap Risk", 0.0, 100.0, 0.0, 1.0)
    with filter_cols[3]:
        maximum_risk = st.slider("Maximum Trap Risk", 0.0, 100.0, 100.0, 1.0)

    filtered = data[data["Sector"].astype(str).isin(selected_sectors)].copy()
    filtered = filtered[
        (numeric(filtered, "Valuation Score") >= minimum_valuation)
        & (numeric(filtered, "Value Trap Risk") >= minimum_risk)
        & (numeric(filtered, "Value Trap Risk") <= maximum_risk)
    ]

    if filtered.empty:
        st.info("No stocks match the selected value-trap criteria.")
        return

    # -----------------------------------------------------
    # Opportunity / risk map
    # -----------------------------------------------------
    st.divider()
    st.subheader("Value Opportunity vs. Trap Risk")
    chart = filtered.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()
    if not chart.empty:
        chart["Market Cap ($B)"] = numeric(chart, "Market Cap") / 1_000_000_000
        chart["Bubble Size"] = numeric(chart, "Market Cap").clip(lower=1)
        fig = px.scatter(
            chart,
            x="Valuation Score",
            y="Value Trap Risk",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            size="Bubble Size",
            size_max=48,
            hover_name="Ticker",
            hover_data={
                "Company": True,
                "Overall Score": ":.1f",
                "Quality Score": ":.1f",
                "Financial Strength Score": ":.1f",
                "Revenue Growth": ":.1%",
                "Earnings Growth": ":.1%",
                "FCF Yield": ":.1%",
                "12M Return": ":.1%",
                "Market Cap ($B)": ":$.1f",
                "Bubble Size": False,
            },
        )
        fig.add_vline(x=65, line_dash="dot", line_color="gray")
        fig.add_hline(y=50, line_dash="dot", line_color="gray")
        fig.update_xaxes(range=[0, 100], title="Valuation Score → more attractive")
        fig.update_yaxes(range=[100, 0], title="Value-Trap Risk → lower is better")
        fig.update_layout(height=590, legend_title="Sector")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Risk-band distribution
    # -----------------------------------------------------
    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Risk Distribution")
        order = ["Low", "Moderate", "Elevated", "High", "Insufficient Data"]
        risk_counts = (
            filtered["Risk Band"].value_counts().reindex(order, fill_value=0).rename_axis("Risk Band").reset_index(name="Stocks")
        )
        fig = px.bar(
            risk_counts,
            x="Risk Band",
            y="Stocks",
            color="Risk Band",
            color_discrete_map={
                "Low": "#2e7d32",
                "Moderate": "#f9a825",
                "Elevated": "#ef6c00",
                "High": "#c62828",
                "Insufficient Data": "#9e9e9e",
            },
            text="Stocks",
            category_orders={"Risk Band": order},
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=430, showlegend=False, xaxis_title="", yaxis_title="Stocks")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Sector Trap Risk")
        sector_risk = (
            filtered.groupby("Sector", as_index=False)
            .agg(
                Stocks=("Ticker", "count"),
                Median_Risk=("Value Trap Risk", "median"),
                Median_Valuation=("Valuation Score", "median"),
            )
            .sort_values("Median_Risk", ascending=False)
        )
        fig = px.bar(
            sector_risk,
            x="Median_Risk",
            y="Sector",
            orientation="h",
            color="Median_Risk",
            color_continuous_scale="RdYlGn_r",
            text="Median_Risk",
            hover_data={"Stocks": True, "Median_Valuation": ":.1f"},
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_xaxes(range=[0, 100], title="Median Trap Risk")
        fig.update_layout(height=430, coloraxis_showscale=False, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Risk component analysis
    # -----------------------------------------------------
    st.divider()
    st.subheader("Risk Signal Prevalence")
    with st.spinner("Calculating individual value-trap signals..."):
        components = component_matrix(filtered)

    available_components = [column for column in RISK_COMPONENT_LABELS if column in components.columns]
    if available_components:
        component_summary = pd.DataFrame(
            {
                "Risk Signal": [RISK_COMPONENT_LABELS[column] for column in available_components],
                "Average Risk": [numeric(components, column).mean() for column in available_components],
                "Stocks Above 50": [int((numeric(components, column) >= 50).sum()) for column in available_components],
            }
        ).sort_values("Average Risk", ascending=True)

        fig = px.bar(
            component_summary,
            x="Average Risk",
            y="Risk Signal",
            orientation="h",
            color="Average Risk",
            color_continuous_scale="RdYlGn_r",
            text="Average Risk",
            hover_data={"Stocks Above 50": True},
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_xaxes(range=[0, 100], title="Average Signal Risk")
        fig.update_layout(height=500, coloraxis_showscale=False, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Candidate tables
    # -----------------------------------------------------
    st.divider()
    high_tab, cheap_tab, safe_tab = st.tabs(
        ["Highest Trap Risk", "Cheap but Risky", "Attractive / Lower Risk"]
    )

    display_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Sector",
            "Price",
            "Market Cap",
            "Forward PE",
            "EV/EBITDA",
            "FCF Yield",
            "Revenue Growth",
            "Earnings Growth",
            "Profit Margin",
            "Net Debt/Market Cap",
            "12M Return",
            "Valuation Score",
            "Quality Score",
            "Financial Strength Score",
            "Overall Score",
            "Value Trap Risk",
            "Value Trap Rating",
        )
        if column in filtered.columns
    ]

    highest = filtered.sort_values("Value Trap Risk", ascending=False, na_position="last").head(20)
    cheap_risky = filtered[
        (numeric(filtered, "Valuation Score") >= 65)
        & (numeric(filtered, "Value Trap Risk") >= 50)
    ].sort_values(["Value Trap Risk", "Valuation Score"], ascending=[False, False])
    lower_risk = filtered[
        (numeric(filtered, "Valuation Score") >= 65)
        & (numeric(filtered, "Value Trap Risk") <= 35)
    ].sort_values(["Overall Score", "Valuation Score"], ascending=[False, False])

    for tab, frame, empty_message in (
        (high_tab, highest, "No value-trap records are available."),
        (cheap_tab, cheap_risky, "No stocks currently meet the cheap-but-risky criteria."),
        (safe_tab, lower_risk, "No stocks currently meet the attractive/lower-risk criteria."),
    ):
        with tab:
            if frame.empty:
                st.info(empty_message)
            else:
                st.dataframe(
                    frame[display_columns],
                    use_container_width=True,
                    hide_index=True,
                    column_config=table_config(),
                )

    # -----------------------------------------------------
    # Individual stock signal matrix
    # -----------------------------------------------------
    st.divider()
    st.subheader("Individual Risk Signals")
    selected_ticker = st.selectbox(
        "Choose a stock",
        filtered.sort_values("Value Trap Risk", ascending=False)["Ticker"].astype(str).tolist(),
    )
    selected_components = components[components["Ticker"].astype(str) == selected_ticker]

    if not selected_components.empty and available_components:
        row = selected_components.iloc[0]
        detail = pd.DataFrame(
            {
                "Risk Signal": [RISK_COMPONENT_LABELS[column] for column in available_components],
                "Risk": [row.get(column) for column in available_components],
            }
        ).dropna().sort_values("Risk", ascending=True)
        fig = px.bar(
            detail,
            x="Risk",
            y="Risk Signal",
            orientation="h",
            color="Risk",
            color_continuous_scale="RdYlGn_r",
            text="Risk",
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_xaxes(range=[0, 100])
        fig.update_layout(height=470, coloraxis_showscale=False, yaxis_title="")
        st.plotly_chart(fig, use_container_width=True)

    st.download_button(
        "Download Value-Trap Dashboard CSV",
        data=filtered[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_value_trap_dashboard.csv",
        mime="text/csv",
        type="secondary",
    )

    st.caption(
        "Value-Trap Risk is a quantitative warning system, not proof that a stock is a value trap. "
        "Temporary weakness, cyclicality, one-time charges, and missing data can affect the risk score."
    )


show()

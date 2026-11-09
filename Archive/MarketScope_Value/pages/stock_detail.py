"""MarketScope Value individual stock-detail page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_data import load_market_bundle
from value_engine import calculate_scores


SCORE_COLUMNS = [
    "Valuation Score",
    "Quality Score",
    "Financial Strength Score",
    "Growth Score",
    "Momentum Score",
    "Overall Score",
]

PERCENT_METRICS = {
    "FCF Yield",
    "Earnings Yield",
    "Dividend Yield",
    "Payout Ratio",
    "Revenue Growth",
    "Earnings Growth",
    "EPS Growth",
    "Forward EPS Growth",
    "ROE",
    "ROA",
    "Gross Margin",
    "Operating Margin",
    "Profit Margin",
    "6M Return",
    "12M Return",
    "Net Debt/Market Cap",
}

CURRENCY_METRICS = {
    "Price",
    "Market Cap",
    "Enterprise Value",
    "Free Cash Flow",
    "Operating Cash Flow",
    "Total Cash",
    "Total Debt",
    "EBITDA",
}


def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def format_compact_currency(value: object) -> str:
    value = number(value)
    if np.isnan(value):
        return "N/A"
    absolute = abs(value)
    if absolute >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if absolute >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if absolute >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    if absolute >= 1_000:
        return f"${value / 1_000:.1f}K"
    return f"${value:,.2f}"


def format_value(label: str, value: object) -> str:
    numeric = number(value)
    if np.isnan(numeric):
        return "N/A"
    if label in PERCENT_METRICS:
        return f"{numeric:.1%}"
    if label in CURRENCY_METRICS:
        return format_compact_currency(numeric)
    if label in {"Forward PE", "Trailing PE", "EV/EBITDA"}:
        return f"{numeric:.1f}x"
    if label in {"Price/Book", "Price/Sales", "PEG", "Current Ratio", "Quick Ratio", "Cash/Debt"}:
        return f"{numeric:.2f}"
    if label == "Debt/Equity":
        return f"{numeric:.1f}"
    return f"{numeric:,.2f}"


def score_color(score: object, inverse: bool = False) -> str:
    value = number(score)
    if np.isnan(value):
        return "#9e9e9e"
    if inverse:
        if value <= 25:
            return "#2e7d32"
        if value <= 50:
            return "#f9a825"
        if value <= 75:
            return "#ef6c00"
        return "#c62828"
    if value >= 75:
        return "#2e7d32"
    if value >= 60:
        return "#66bb6a"
    if value >= 45:
        return "#f9a825"
    return "#c62828"


def close_series(history: pd.DataFrame | None) -> pd.Series:
    if history is None or history.empty:
        return pd.Series(dtype=float)
    column = "Adj Close" if "Adj Close" in history.columns else "Close"
    if column not in history.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(history[column], errors="coerce").dropna().sort_index()


def metric_grid(record: pd.Series, metrics: list[str], columns: int = 4) -> None:
    available = [metric for metric in metrics if metric in record.index]
    for start in range(0, len(available), columns):
        row_columns = st.columns(columns)
        for container, metric in zip(row_columns, available[start : start + columns]):
            container.metric(metric, format_value(metric, record.get(metric)))


def detail_table_config() -> dict:
    config: dict = {}
    for column in PERCENT_METRICS:
        config[column] = st.column_config.NumberColumn(column, format="percent")
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )
    config["Value Trap Risk"] = st.column_config.ProgressColumn(
        "Trap Risk", min_value=0, max_value=100, format="%.1f"
    )
    return config


def show() -> None:
    st.title("🔎 Stock Detail")
    st.caption(
        "Review an individual company across valuation, quality, financial strength, "
        "growth, momentum, and value-trap risk."
    )

    try:
        with st.spinner("Loading MarketScope Value data..."):
            bundle = load_market_bundle()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    data = bundle.get("data", pd.DataFrame()).copy()
    histories = bundle.get("histories", {})
    if data.empty or "Ticker" not in data.columns:
        st.warning("No stock-detail data is currently available.")
        return

    data["Ticker"] = data["Ticker"].astype(str).str.upper()
    data = data.drop_duplicates(subset="Ticker", keep="first")
    ticker_options = data["Ticker"].sort_values().tolist()

    selected_ticker = st.selectbox(
        "Choose a stock",
        ticker_options,
        index=0,
    )
    record = data.loc[data["Ticker"] == selected_ticker].iloc[0]

    company = str(record.get("Company") or selected_ticker)
    sector = str(record.get("Sector") or "Unknown")
    industry = str(record.get("Industry") or "Unknown")
    st.subheader(f"{selected_ticker} · {company}")
    st.caption(f"{sector}  |  {industry}")

    headline = st.columns(6)
    headline[0].metric("Price", format_value("Price", record.get("Price")))
    headline[1].metric("Market Cap", format_value("Market Cap", record.get("Market Cap")))
    headline[2].metric("Overall", format_value("Overall Score", record.get("Overall Score")))
    headline[3].metric("Valuation", format_value("Valuation Score", record.get("Valuation Score")))
    headline[4].metric("Trap Risk", format_value("Value Trap Risk", record.get("Value Trap Risk")))
    headline[5].metric("Rating", str(record.get("Rating") or "N/A"))

    trap_rating = str(record.get("Value Trap Rating") or "Insufficient Data")
    trap_score = record.get("Value Trap Risk")
    if number(trap_score) >= 75:
        st.error(f"Value-trap assessment: **{trap_rating}** ({number(trap_score):.1f})")
    elif number(trap_score) >= 50:
        st.warning(f"Value-trap assessment: **{trap_rating}** ({number(trap_score):.1f})")
    else:
        st.success(
            f"Value-trap assessment: **{trap_rating}**"
            + (f" ({number(trap_score):.1f})" if not np.isnan(number(trap_score)) else "")
        )

    st.divider()

    # -----------------------------------------------------
    # Score profile
    # -----------------------------------------------------
    left, right = st.columns([1.15, 1])
    with left:
        st.subheader("Score Profile")
        available_scores = [column for column in SCORE_COLUMNS if column in record.index]
        score_frame = pd.DataFrame(
            {
                "Category": [column.replace(" Score", "") for column in available_scores],
                "Score": [number(record.get(column)) for column in available_scores],
            }
        ).dropna()
        if not score_frame.empty:
            fig = px.bar(
                score_frame.sort_values("Score"),
                x="Score",
                y="Category",
                orientation="h",
                color="Score",
                color_continuous_scale="RdYlGn",
                text="Score",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_xaxes(range=[0, 100])
            fig.update_layout(
                height=410,
                showlegend=False,
                coloraxis_showscale=False,
                xaxis_title="Score",
                yaxis_title="",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Valuation Snapshot")
        metric_grid(
            record,
            [
                "Forward PE",
                "Trailing PE",
                "Price/Book",
                "Price/Sales",
                "EV/EBITDA",
                "FCF Yield",
                "Earnings Yield",
                "PEG",
            ],
            columns=2,
        )

    # -----------------------------------------------------
    # Price history
    # -----------------------------------------------------
    st.divider()
    st.subheader("Price History")
    history = histories.get(selected_ticker)
    prices = close_series(history)

    if prices.empty:
        st.info("Price history is not available for this stock.")
    else:
        price_frame = pd.DataFrame({"Date": prices.index, "Price": prices.values})
        price_frame["50-Day MA"] = price_frame["Price"].rolling(50).mean()
        price_frame["200-Day MA"] = price_frame["Price"].rolling(200).mean()

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=price_frame["Date"],
                y=price_frame["Price"],
                name="Adjusted Close",
                line=dict(width=2),
                hovertemplate="Date: %{x|%b %d, %Y}<br>Price: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=price_frame["Date"],
                y=price_frame["50-Day MA"],
                name="50-Day MA",
                line=dict(width=1.5),
                hovertemplate="50-Day MA: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.add_trace(
            go.Scatter(
                x=price_frame["Date"],
                y=price_frame["200-Day MA"],
                name="200-Day MA",
                line=dict(width=1.5),
                hovertemplate="200-Day MA: $%{y:,.2f}<extra></extra>",
            )
        )
        fig.update_layout(
            height=500,
            xaxis_title="",
            yaxis_title="Price ($)",
            legend_title="Series",
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Fundamentals
    # -----------------------------------------------------
    st.divider()
    valuation_tab, quality_tab, strength_tab, growth_tab, momentum_tab = st.tabs(
        ["Valuation", "Quality", "Financial Strength", "Growth", "Momentum"]
    )

    with valuation_tab:
        metric_grid(
            record,
            [
                "Forward PE",
                "Trailing PE",
                "Price/Book",
                "Price/Sales",
                "EV/EBITDA",
                "EV/Revenue",
                "FCF Yield",
                "Earnings Yield",
                "Enterprise Value",
            ],
        )

    with quality_tab:
        metric_grid(
            record,
            [
                "ROE",
                "ROA",
                "Gross Margin",
                "Operating Margin",
                "Profit Margin",
                "Free Cash Flow",
                "Operating Cash Flow",
                "Cash Conversion",
            ],
        )

    with strength_tab:
        metric_grid(
            record,
            [
                "Total Cash",
                "Total Debt",
                "Net Debt/Market Cap",
                "Cash/Debt",
                "Debt/Equity",
                "Current Ratio",
                "Quick Ratio",
            ],
        )

    with growth_tab:
        metric_grid(
            record,
            [
                "Revenue Growth",
                "Earnings Growth",
                "EPS Growth",
                "Forward EPS Growth",
            ],
        )

    with momentum_tab:
        metric_grid(
            record,
            [
                "6M Return",
                "12M Return",
                "50D MA",
                "200D MA",
                "52W High",
                "52W Low",
            ],
        )

    # -----------------------------------------------------
    # Value-trap component analysis
    # -----------------------------------------------------
    st.divider()
    st.subheader("⚠️ Value-Trap Risk Analysis")
    scores = calculate_scores(record.to_dict())
    components = scores.get("Value Trap Components", {})

    if components:
        labels = {
            "negative_revenue_growth": "Revenue deterioration",
            "negative_earnings_growth": "Earnings deterioration",
            "negative_free_cash_flow": "Negative free cash flow",
            "weak_profitability": "Weak profitability",
            "high_net_debt": "High net debt",
            "below_200dma": "Below 200-day average",
            "weak_12m_return": "Weak 12-month return",
            "low_quality_score": "Low quality score",
        }
        component_frame = pd.DataFrame(
            {
                "Risk Signal": [labels.get(key, key.replace("_", " ").title()) for key in components],
                "Risk": [number(value) for value in components.values()],
            }
        ).dropna()

        if component_frame.empty:
            st.info("Value-trap component data is insufficient for this stock.")
        else:
            component_frame = component_frame.sort_values("Risk", ascending=True)
            fig = px.bar(
                component_frame,
                x="Risk",
                y="Risk Signal",
                orientation="h",
                color="Risk",
                color_continuous_scale="RdYlGn_r",
                text="Risk",
            )
            fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
            fig.update_xaxes(range=[0, 100])
            fig.update_layout(
                height=470,
                coloraxis_showscale=False,
                xaxis_title="Risk contribution",
                yaxis_title="",
                margin=dict(l=10, r=10, t=10, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Peer comparison
    # -----------------------------------------------------
    st.divider()
    st.subheader("Sector Peer Comparison")
    peers = data[data.get("Sector", pd.Series(index=data.index, dtype=str)) == sector].copy()
    peer_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Forward PE",
            "FCF Yield",
            "Valuation Score",
            "Quality Score",
            "Financial Strength Score",
            "Growth Score",
            "Momentum Score",
            "Overall Score",
            "Value Trap Risk",
        )
        if column in peers.columns
    ]
    peers = peers.sort_values("Overall Score", ascending=False, na_position="last")
    st.dataframe(
        peers[peer_columns],
        use_container_width=True,
        hide_index=True,
        column_config=detail_table_config(),
    )

    st.caption(
        "MarketScope Value provides quantitative research signals and does not estimate intrinsic value. "
        "Review company filings, industry structure, cyclicality, accounting quality, and current developments "
        "before making an investment decision."
    )


show()

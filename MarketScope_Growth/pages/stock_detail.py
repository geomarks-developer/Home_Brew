"""MarketScope Growth stock-detail page."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from config import SECTOR_COLORS
from market_data import load_market_data


SCORE_COLUMNS = [
    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",
    "Overall Score",
]

PERCENT_FIELDS = [
    "Revenue Growth",
    "Earnings Growth",
    "EPS Growth",
    "Forward EPS Growth",
    "ROE",
    "Operating Margin",
    "Profit Margin",
    "6M Return",
    "12M Return",
]


@st.cache_data(ttl=900, show_spinner=False)
def get_stock_data() -> pd.DataFrame:
    """Load the scored MarketScope Growth universe."""
    return load_market_data()


@st.cache_data(ttl=900, show_spinner=False)
def get_price_history(ticker: str, period: str) -> pd.DataFrame:
    """Download adjusted daily price history for one stock."""
    try:
        history = yf.download(
            ticker,
            period=period,
            interval="1d",
            auto_adjust=True,
            actions=False,
            progress=False,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()

    if history is None or history.empty:
        return pd.DataFrame()

    history = history.copy()

    if isinstance(history.columns, pd.MultiIndex):
        history.columns = history.columns.get_level_values(0)

    history = history.loc[:, ~history.columns.duplicated()]
    history.index = pd.to_datetime(history.index)
    return history.sort_index()


def safe_number(value) -> float:
    """Convert an arbitrary value to a finite float or NaN."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def format_number(value, decimals: int = 1) -> str:
    value = safe_number(value)
    return "N/A" if np.isnan(value) else f"{value:,.{decimals}f}"


def format_currency(value) -> str:
    value = safe_number(value)
    return "N/A" if np.isnan(value) else f"${value:,.2f}"


def format_percent(value) -> str:
    value = safe_number(value)
    return "N/A" if np.isnan(value) else f"{value:.1%}"


def format_market_cap(value) -> str:
    value = safe_number(value)
    if np.isnan(value):
        return "N/A"
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    if value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    return f"${value:,.0f}"


def metric_value(row: pd.Series, field: str) -> str:
    """Format a stock-detail field according to its type."""
    value = row.get(field, np.nan)
    if field in PERCENT_FIELDS:
        return format_percent(value)
    if field == "Price":
        return format_currency(value)
    if field == "Market Cap":
        return format_market_cap(value)
    if field in {"PEG", "Price/Sales"}:
        return format_number(value, 2)
    return format_number(value, 1)


def make_score_chart(row: pd.Series) -> go.Figure:
    """Create a horizontal score profile."""
    columns = [column for column in SCORE_COLUMNS if column in row.index]
    labels = [column.replace(" Score", "") for column in columns]
    values = [safe_number(row[column]) for column in columns]

    colors = []
    for value in values:
        if np.isnan(value):
            colors.append("#9e9e9e")
        elif value >= 80:
            colors.append("#1b5e20")
        elif value >= 65:
            colors.append("#66bb6a")
        elif value >= 50:
            colors.append("#fbc02d")
        else:
            colors.append("#c62828")

    figure = go.Figure(
        go.Bar(
            x=[0 if np.isnan(value) else value for value in values],
            y=labels,
            orientation="h",
            marker_color=colors,
            text=["N/A" if np.isnan(value) else f"{value:.1f}" for value in values],
            textposition="outside",
            hovertemplate="%{y}: %{x:.1f}<extra></extra>",
        )
    )
    figure.update_xaxes(range=[0, 105], title="Score")
    figure.update_yaxes(title="")
    figure.update_layout(
        height=360,
        showlegend=False,
        margin=dict(l=10, r=45, t=10, b=10),
    )
    return figure


def make_price_chart(history: pd.DataFrame, ticker: str) -> go.Figure:
    """Create a candlestick/line chart with moving averages."""
    chart = history.copy()
    chart["50D MA"] = chart["Close"].rolling(50).mean()
    chart["200D MA"] = chart["Close"].rolling(200).mean()

    figure = go.Figure()
    if all(column in chart.columns for column in ("Open", "High", "Low", "Close")):
        figure.add_trace(
            go.Candlestick(
                x=chart.index,
                open=chart["Open"],
                high=chart["High"],
                low=chart["Low"],
                close=chart["Close"],
                name=ticker,
            )
        )
    else:
        figure.add_trace(
            go.Scatter(x=chart.index, y=chart["Close"], name=ticker, mode="lines")
        )

    figure.add_trace(
        go.Scatter(
            x=chart.index,
            y=chart["50D MA"],
            name="50-day MA",
            mode="lines",
            line=dict(width=1.5, color="#ff7f0e"),
        )
    )
    figure.add_trace(
        go.Scatter(
            x=chart.index,
            y=chart["200D MA"],
            name="200-day MA",
            mode="lines",
            line=dict(width=1.5, color="#9467bd"),
        )
    )
    figure.update_layout(
        height=540,
        xaxis_rangeslider_visible=False,
        xaxis_title="",
        yaxis_title="Adjusted Price",
        margin=dict(l=10, r=10, t=20, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
    )
    return figure


def make_growth_chart(row: pd.Series) -> go.Figure | None:
    """Create a comparison chart for reported growth metrics."""
    fields = [
        "Revenue Growth",
        "Earnings Growth",
        "EPS Growth",
        "Forward EPS Growth",
    ]
    labels = []
    values = []
    for field in fields:
        value = safe_number(row.get(field))
        if not np.isnan(value):
            labels.append(field.replace(" Growth", ""))
            values.append(value * 100)

    if not values:
        return None

    colors = ["#1f77b4" if value >= 0 else "#c62828" for value in values]
    figure = go.Figure(
        go.Bar(
            x=labels,
            y=values,
            marker_color=colors,
            text=[f"{value:.1f}%" for value in values],
            textposition="outside",
            hovertemplate="%{x}: %{y:.1f}%<extra></extra>",
        )
    )
    figure.add_hline(y=0, line_color="#777777", line_width=1)
    figure.update_layout(
        height=380,
        showlegend=False,
        xaxis_title="",
        yaxis_title="Growth Rate (%)",
        margin=dict(l=10, r=10, t=10, b=10),
    )
    return figure


def peer_table(data: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    """Return the selected stock and its closest same-sector peers."""
    sector = row.get("Sector", "Unknown")
    peers = data.loc[data["Sector"].fillna("Unknown") == sector].copy()
    peers = peers.sort_values("Overall Score", ascending=False, na_position="last")

    selected = peers.loc[peers["Ticker"] == row["Ticker"]]
    others = peers.loc[peers["Ticker"] != row["Ticker"]].head(9)
    result = pd.concat([selected, others], ignore_index=True)

    columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Growth Score",
            "Quality Score",
            "Valuation Score",
            "Momentum Score",
            "Overall Score",
            "Rating",
        )
        if column in result.columns
    ]
    return result[columns]


def score_column_config() -> dict:
    config = {}
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )
    return config


def show() -> None:
    """Render the MarketScope Growth stock-detail page."""
    st.title("📈 Stock Detail")
    st.caption(
        "Inspect a growth stock's quantitative scores, fundamentals, valuation, "
        "momentum, price trend, and same-sector peers."
    )

    try:
        with st.spinner("Loading MarketScope Growth data..."):
            data = get_stock_data()
    except Exception as exc:
        st.error("Stock-detail data could not be loaded.")
        st.exception(exc)
        return

    if data is None or data.empty or "Ticker" not in data.columns:
        st.warning("No growth-stock data is currently available.")
        return

    data = data.copy()
    data["Ticker"] = data["Ticker"].astype(str).str.upper()
    data = data.sort_values("Ticker")

    labels = {
        row["Ticker"]: f'{row["Ticker"]} | {row.get("Company", row["Ticker"])}'
        for _, row in data.iterrows()
    }
    tickers = list(labels)

    selected_ticker = st.selectbox(
        "Select a stock",
        options=tickers,
        format_func=lambda ticker: labels[ticker],
    )
    row = data.loc[data["Ticker"] == selected_ticker].iloc[0]

    company = row.get("Company", selected_ticker)
    sector = row.get("Sector", "Unknown")
    industry = row.get("Industry", "Unknown")
    rating = row.get("Rating", "Insufficient Data")

    st.markdown(f"## {company} ({selected_ticker})")
    st.caption(f"{sector} | {industry} | {rating}")

    metrics = st.columns(6)
    metrics[0].metric("Price", metric_value(row, "Price"))
    metrics[1].metric("Market Cap", metric_value(row, "Market Cap"))
    metrics[2].metric("Overall", metric_value(row, "Overall Score"))
    metrics[3].metric("Growth", metric_value(row, "Growth Score"))
    metrics[4].metric("Quality", metric_value(row, "Quality Score"))
    metrics[5].metric("Momentum", metric_value(row, "Momentum Score"))

    st.divider()

    score_col, growth_col = st.columns(2)
    with score_col:
        st.subheader("Score Profile")
        st.plotly_chart(make_score_chart(row), use_container_width=True)

    with growth_col:
        st.subheader("Growth Metrics")
        growth_figure = make_growth_chart(row)
        if growth_figure is None:
            st.info("Growth-rate details are not available for this stock.")
        else:
            st.plotly_chart(growth_figure, use_container_width=True)

    st.divider()

    st.subheader("Fundamental Snapshot")
    metric_groups = [
        (
            "Growth",
            ["Revenue Growth", "Earnings Growth", "EPS Growth", "Forward EPS Growth"],
        ),
        (
            "Quality",
            ["ROE", "Operating Margin", "Profit Margin", "Free Cash Flow"],
        ),
        (
            "Valuation",
            ["Forward PE", "PEG", "Price/Sales"],
        ),
        (
            "Momentum",
            ["6M Return", "12M Return", "50D MA", "200D MA", "52W High"],
        ),
    ]

    group_columns = st.columns(4)
    for container, (title, fields) in zip(group_columns, metric_groups):
        with container:
            st.markdown(f"**{title}**")
            for field in fields:
                if field in row.index:
                    value = row.get(field)
                    if field == "Free Cash Flow":
                        display = format_market_cap(value)
                    elif field in {"50D MA", "200D MA", "52W High"}:
                        display = format_currency(value)
                    else:
                        display = metric_value(row, field)
                    st.markdown(f"{field}: **{display}**")

    st.divider()

    st.subheader("Price History")
    period = st.radio(
        "Chart period",
        options=["6mo", "1y", "2y", "5y"],
        index=2,
        horizontal=True,
    )
    history = get_price_history(selected_ticker, period)
    if history.empty or "Close" not in history.columns:
        st.info("Price history is not currently available for this stock.")
    else:
        st.plotly_chart(
            make_price_chart(history, selected_ticker),
            use_container_width=True,
        )

    st.divider()

    st.subheader(f"{sector} Peer Comparison")
    peers = peer_table(data, row)
    st.dataframe(
        peers,
        use_container_width=True,
        hide_index=True,
        column_config=score_column_config(),
    )

    peer_chart = peers.dropna(subset=["Overall Score"]).copy()
    if not peer_chart.empty:
        peer_chart = peer_chart.sort_values("Overall Score")
        color = SECTOR_COLORS.get(sector, SECTOR_COLORS.get("Unknown", "#bdbdbd"))
        figure = px.bar(
            peer_chart,
            x="Overall Score",
            y="Ticker",
            orientation="h",
            color_discrete_sequence=[color],
            hover_data=[column for column in ("Company", "Rating") if column in peer_chart.columns],
        )
        figure.update_xaxes(range=[0, 100])
        figure.update_layout(
            height=max(360, 38 * len(peer_chart)),
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(figure, use_container_width=True)

    coverage = safe_number(row.get("Overall Coverage"))
    if not np.isnan(coverage) and coverage < 1.0:
        st.info(
            f"Overall score coverage is {coverage:.0%}. Missing metrics were excluded "
            "and the available score components were reweighted."
        )

    st.caption(
        "MarketScope Growth is a quantitative research tool and does not provide "
        "investment advice or a recommendation to buy or sell a security."
    )
# =========================================================
# Run page
# =========================================================
show()
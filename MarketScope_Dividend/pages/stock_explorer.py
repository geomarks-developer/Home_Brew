from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_data import get_market_data


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def fmt_pct(value) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.2%}"


def fmt_yield(value) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.2f}%"


def fmt_num(value, digits=1) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):,.{digits}f}"


def fmt_money(value) -> str:
    return "N/A" if pd.isna(value) else f"${float(value):,.2f}"


def fmt_large(value) -> str:
    if pd.isna(value):
        return "N/A"
    value = float(value)
    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"
    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"
    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"
    return f"${value:,.0f}"


def value(row: pd.Series, column: str):
    return row[column] if column in row.index else np.nan


# ---------------------------------------------------------
# Header and data
# ---------------------------------------------------------

st.header("🔎 Dividend Aristocrat Stock Explorer")
st.caption(
    "Explore an individual Dividend Aristocrat's price history, dividend profile, "
    "fundamentals, technical indicators, and MarketScope scores."
)

try:
    data = get_market_data(show_progress=False)
except Exception as exc:
    st.error(f"Unable to load MarketScope Dividend data: {exc}")
    st.stop()


df = data.get("dividend_df", pd.DataFrame()).copy()
histories = data.get("histories", {})
dividend_cache = data.get("dividend_cache", {})

if df.empty:
    st.warning("No Dividend Aristocrat data is currently available.")
    st.stop()


df = df.sort_values("Ticker").reset_index(drop=True)
tickers = df["Ticker"].dropna().astype(str).tolist()

selected_ticker = st.selectbox(
    "Select a Dividend Aristocrat",
    tickers,
    index=0,
)

row = df.loc[df["Ticker"] == selected_ticker].iloc[0]
history = histories.get(selected_ticker, pd.DataFrame()).copy()
dividends = dividend_cache.get(selected_ticker, pd.Series(dtype=float))

company = row.get("Company", selected_ticker)
sector = row.get("Sector", "Unknown")
industry = row.get("Industry", "Unknown")

st.subheader(f"{selected_ticker} · {company}")
st.caption(f"{sector}  |  {industry}")


# ---------------------------------------------------------
# Headline metrics
# ---------------------------------------------------------

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Price", fmt_money(value(row, "Price")))
m2.metric("Dividend Yield", fmt_yield(value(row, "Dividend Yield")))
m3.metric("5Y Dividend Growth", fmt_pct(value(row, "Dividend Growth 5Y")))
m4.metric("Payout Ratio", fmt_pct(value(row, "Payout Ratio")))
m5.metric("Overall Score", fmt_num(value(row, "Overall Score")))
m6.metric("Rank", fmt_num(value(row, "Rank"), 0))

st.divider()


# ---------------------------------------------------------
# Scorecard
# ---------------------------------------------------------

st.subheader("MarketScope Scorecard")

score_columns = [
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
    "Overall Score",
]

score_df = pd.DataFrame(
    {
        "Category": [name.replace(" Score", "") for name in score_columns],
        "Score": [pd.to_numeric(value(row, name), errors="coerce") for name in score_columns],
    }
).dropna()

score_fig = px.bar(
    score_df,
    x="Category",
    y="Score",
    color="Score",
    color_continuous_scale=[
        [0.0, "#b2182b"],
        [0.5, "#d9d9d9"],
        [1.0, "#2166ac"],
    ],
    range_color=[0, 100],
    text="Score",
)
score_fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
score_fig.update_layout(
    height=380,
    yaxis_range=[0, 110],
    yaxis_title="Score",
    xaxis_title=None,
    coloraxis_showscale=False,
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(score_fig, use_container_width=True, config={"displaylogo": False})


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------

tab_price, tab_dividend, tab_fundamentals, tab_technical = st.tabs(
    ["📈 Price", "💵 Dividend", "📋 Fundamentals", "📊 Technical"]
)


with tab_price:
    st.subheader("Price History")

    if history is None or history.empty or "Close" not in history.columns:
        st.info("Price history is not available for this ticker.")
    else:
        chart_df = history.copy()
        chart_df["Close"] = pd.to_numeric(chart_df["Close"], errors="coerce")
        chart_df = chart_df.dropna(subset=["Close"])
        chart_df["SMA 50"] = chart_df["Close"].rolling(50).mean()
        chart_df["SMA 200"] = chart_df["Close"].rolling(200).mean()

        price_fig = go.Figure()
        price_fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["Close"],
                mode="lines",
                name="Close",
                line=dict(width=2),
            )
        )
        price_fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["SMA 50"],
                mode="lines",
                name="50-Day SMA",
                line=dict(width=1.5),
            )
        )
        price_fig.add_trace(
            go.Scatter(
                x=chart_df.index,
                y=chart_df["SMA 200"],
                mode="lines",
                name="200-Day SMA",
                line=dict(width=1.5),
            )
        )
        price_fig.update_layout(
            height=520,
            xaxis_title=None,
            yaxis_title="Price ($)",
            hovermode="x unified",
            legend_title=None,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(
            price_fig,
            use_container_width=True,
            config={"displaylogo": False},
        )

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("1M Return", fmt_pct(value(row, "Return 1M")))
        p2.metric("3M Return", fmt_pct(value(row, "Return 3M")))
        p3.metric("6M Return", fmt_pct(value(row, "Return 6M")))
        p4.metric("1Y Return", fmt_pct(value(row, "Return 1Y")))


with tab_dividend:
    st.subheader("Dividend Profile")

    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Dividend Rate", fmt_money(value(row, "Dividend Rate")))
    d2.metric("Dividend Yield", fmt_yield(value(row, "Dividend Yield")))
    d3.metric("Payout Ratio", fmt_pct(value(row, "Payout Ratio")))
    d4.metric("Dividend Score", fmt_num(value(row, "Dividend Score")))

    d5, d6, d7, d8 = st.columns(4)
    d5.metric("1Y Growth", fmt_pct(value(row, "Dividend Growth 1Y")))
    d6.metric("3Y Growth", fmt_pct(value(row, "Dividend Growth 3Y")))
    d7.metric("5Y Growth", fmt_pct(value(row, "Dividend Growth 5Y")))
    d8.metric("Consistency", fmt_pct(value(row, "Dividend Consistency")))

    st.subheader("Annual Dividend History")

    if dividends is None or len(dividends) == 0:
        st.info("Dividend history is not available for this ticker.")
    else:
        series = pd.to_numeric(dividends, errors="coerce").dropna()
        try:
            series.index = pd.to_datetime(series.index, utc=True).tz_convert(None)
        except (TypeError, ValueError):
            series.index = pd.to_datetime(series.index)

        annual = (
            series.groupby(series.index.year)
            .sum()
            .reset_index()
        )
        annual.columns = ["Year", "Dividend"]
        annual = annual.tail(15)

        div_fig = px.bar(
            annual,
            x="Year",
            y="Dividend",
            text="Dividend",
        )
        div_fig.update_traces(texttemplate="$%{text:.2f}", textposition="outside")
        div_fig.update_layout(
            height=450,
            xaxis_title=None,
            yaxis_title="Dividend per Share ($)",
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(
            div_fig,
            use_container_width=True,
            config={"displaylogo": False},
        )


with tab_fundamentals:
    st.subheader("Fundamentals and Valuation")

    fundamentals = [
        ("Market Cap", fmt_large(value(row, "Market Cap"))),
        ("P/E", fmt_num(value(row, "P/E"))),
        ("Forward P/E", fmt_num(value(row, "Forward P/E"))),
        ("PEG", fmt_num(value(row, "PEG"), 2)),
        ("Price / Book", fmt_num(value(row, "Price to Book"))),
        ("Price / FCF", fmt_num(value(row, "Price to FCF"))),
        ("ROE", fmt_pct(value(row, "ROE"))),
        ("Profit Margin", fmt_pct(value(row, "Profit Margin"))),
        ("Operating Margin", fmt_pct(value(row, "Operating Margin"))),
        ("Revenue Growth", fmt_pct(value(row, "Revenue Growth"))),
        ("Earnings Growth", fmt_pct(value(row, "Earnings Growth"))),
        ("Debt / Equity", fmt_num(value(row, "Debt to Equity"))),
        ("Free Cash Flow", fmt_large(value(row, "Free Cash Flow"))),
        ("Operating Cash Flow", fmt_large(value(row, "Operating Cash Flow"))),
        ("Analyst Target", fmt_money(value(row, "Analyst Target"))),
    ]

    fundamentals_df = pd.DataFrame(fundamentals, columns=["Metric", "Value"])
    st.dataframe(
        fundamentals_df,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="medium"),
            "Value": st.column_config.TextColumn("Value", width="medium"),
        },
    )


with tab_technical:
    st.subheader("Technical and Risk Metrics")

    technical = [
        ("50-Day SMA", fmt_money(value(row, "SMA 50"))),
        ("200-Day SMA", fmt_money(value(row, "SMA 200"))),
        ("Price vs 50-Day SMA", fmt_pct(value(row, "Price vs SMA 50"))),
        ("Price vs 200-Day SMA", fmt_pct(value(row, "Price vs SMA 200"))),
        ("RSI (14)", fmt_num(value(row, "RSI"))),
        ("Beta", fmt_num(value(row, "Beta"), 2)),
        ("Annualized Volatility", fmt_pct(value(row, "Volatility"))),
        ("Maximum Drawdown", fmt_pct(value(row, "Max Drawdown"))),
        ("52-Week Position", fmt_pct(value(row, "52-Week Position"))),
        ("Momentum Score", fmt_num(value(row, "Momentum Score"))),
        ("Risk Score", fmt_num(value(row, "Risk Score"))),
    ]

    technical_df = pd.DataFrame(technical, columns=["Metric", "Value"])
    st.dataframe(
        technical_df,
        hide_index=True,
        use_container_width=True,
    )


st.divider()
st.caption(
    "MarketScope Dividend scores and market data are provided for research. "
    "They are not investment recommendations."
)

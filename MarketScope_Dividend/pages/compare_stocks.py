from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_data import get_market_data


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def pct(value) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.2%}"


def yield_pct(value) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.2f}%"


def num(value, digits=1) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):,.{digits}f}"


def money(value) -> str:
    return "N/A" if pd.isna(value) else f"${float(value):,.2f}"


def row_value(row: pd.Series, column: str):
    return row[column] if column in row.index else np.nan


# ---------------------------------------------------------
# Header and shared data
# ---------------------------------------------------------

st.header("⚖️ Compare Dividend Aristocrats")
st.caption(
    "Compare two to five Dividend Aristocrats side-by-side across dividend, "
    "quality, valuation, momentum, risk, and historical price performance."
)

try:
    data = get_market_data(show_progress=False)
except Exception as exc:
    st.error(f"Unable to load MarketScope Dividend data: {exc}")
    st.stop()


df = data.get("dividend_df", pd.DataFrame()).copy()
histories = data.get("histories", {})

if df.empty:
    st.warning("No Dividend Aristocrat data is currently available.")
    st.stop()


df = df.sort_values("Ticker").reset_index(drop=True)
tickers = df["Ticker"].dropna().astype(str).tolist()

defaults = tickers[:3] if len(tickers) >= 3 else tickers

selected = st.multiselect(
    "Select 2 to 5 stocks",
    options=tickers,
    default=defaults,
    max_selections=5,
)

if len(selected) < 2:
    st.info("Select at least two Dividend Aristocrats to compare.")
    st.stop()

compare = (
    df[df["Ticker"].isin(selected)]
    .set_index("Ticker")
    .reindex(selected)
    .reset_index()
)


# ---------------------------------------------------------
# Headline comparison cards
# ---------------------------------------------------------

st.subheader("At a Glance")
columns = st.columns(len(selected))

for container, ticker in zip(columns, selected):
    row = compare.loc[compare["Ticker"] == ticker].iloc[0]
    with container:
        st.markdown(f"### {ticker}")
        st.caption(str(row.get("Company", ticker)))
        st.metric("Overall Score", num(row_value(row, "Overall Score")))
        st.metric("Dividend Yield", yield_pct(row_value(row, "Dividend Yield")))
        st.metric("5Y Dividend Growth", pct(row_value(row, "Dividend Growth 5Y")))
        st.metric("P/E", num(row_value(row, "P/E")))

st.divider()


# ---------------------------------------------------------
# Score comparison
# ---------------------------------------------------------

st.subheader("MarketScope Score Comparison")

score_columns = [
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
    "Overall Score",
]

score_fig = go.Figure()

for ticker in selected:
    row = compare.loc[compare["Ticker"] == ticker].iloc[0]
    values = [
        pd.to_numeric(row_value(row, metric), errors="coerce")
        for metric in score_columns
    ]
    score_fig.add_trace(
        go.Bar(
            name=ticker,
            x=[metric.replace(" Score", "") for metric in score_columns],
            y=values,
        )
    )

score_fig.update_layout(
    barmode="group",
    height=470,
    yaxis_title="Score",
    yaxis_range=[0, 100],
    xaxis_title=None,
    legend_title=None,
    margin=dict(l=10, r=10, t=10, b=10),
)

st.plotly_chart(
    score_fig,
    use_container_width=True,
    config={"displaylogo": False},
)


# ---------------------------------------------------------
# Normalized price performance
# ---------------------------------------------------------

st.divider()
st.subheader("Normalized Price Performance")
st.caption("Each series starts at 100 to make historical performance comparable.")

performance_fig = go.Figure()
valid_series = 0

for ticker in selected:
    history = histories.get(ticker, pd.DataFrame())

    if history is None or history.empty or "Close" not in history.columns:
        continue

    close = pd.to_numeric(history["Close"], errors="coerce").dropna()

    if close.empty or close.iloc[0] == 0:
        continue

    normalized = close / close.iloc[0] * 100
    performance_fig.add_trace(
        go.Scatter(
            x=normalized.index,
            y=normalized,
            mode="lines",
            name=ticker,
        )
    )
    valid_series += 1

if valid_series:
    performance_fig.update_layout(
        height=520,
        xaxis_title=None,
        yaxis_title="Growth of 100",
        hovermode="x unified",
        legend_title=None,
        margin=dict(l=10, r=10, t=10, b=10),
    )
    st.plotly_chart(
        performance_fig,
        use_container_width=True,
        config={"displaylogo": False},
    )
else:
    st.info("Price histories are not available for the selected stocks.")


# ---------------------------------------------------------
# Detailed comparison table
# ---------------------------------------------------------

st.divider()
st.subheader("Detailed Comparison")

metric_rows = [
    ("Company", "Company", "text"),
    ("Sector", "Sector", "text"),
    ("Price", "Price", "money"),
    ("Dividend Yield", "Dividend Yield", "yield"),
    ("Payout Ratio", "Payout Ratio", "pct"),
    ("1Y Dividend Growth", "Dividend Growth 1Y", "pct"),
    ("3Y Dividend Growth", "Dividend Growth 3Y", "pct"),
    ("5Y Dividend Growth", "Dividend Growth 5Y", "pct"),
    ("Dividend Consistency", "Dividend Consistency", "pct"),
    ("P/E", "P/E", "num"),
    ("Forward P/E", "Forward P/E", "num"),
    ("PEG", "PEG", "num2"),
    ("Price / Book", "Price to Book", "num"),
    ("Price / FCF", "Price to FCF", "num"),
    ("ROE", "ROE", "pct"),
    ("Profit Margin", "Profit Margin", "pct"),
    ("Revenue Growth", "Revenue Growth", "pct"),
    ("Earnings Growth", "Earnings Growth", "pct"),
    ("Debt / Equity", "Debt to Equity", "num"),
    ("1Y Return", "Return 1Y", "pct"),
    ("RSI", "RSI", "num"),
    ("Beta", "Beta", "num2"),
    ("Volatility", "Volatility", "pct"),
    ("Max Drawdown", "Max Drawdown", "pct"),
    ("Dividend Score", "Dividend Score", "num"),
    ("Quality Score", "Quality Score", "num"),
    ("Value Score", "Value Score", "num"),
    ("Momentum Score", "Momentum Score", "num"),
    ("Risk Score", "Risk Score", "num"),
    ("Overall Score", "Overall Score", "num"),
    ("Rank", "Rank", "num0"),
]

rows = []

for label, source, kind in metric_rows:
    output = {"Metric": label}

    for ticker in selected:
        row = compare.loc[compare["Ticker"] == ticker].iloc[0]
        val = row.get(source, np.nan)

        if kind == "text":
            formatted = "N/A" if pd.isna(val) else str(val)
        elif kind == "money":
            formatted = money(val)
        elif kind == "pct":
            formatted = pct(val)
        elif kind == "yield":
            formatted = yield_pct(val)
        elif kind == "num2":
            formatted = num(val, 2)
        elif kind == "num0":
            formatted = num(val, 0)
        else:
            formatted = num(val, 1)

        output[ticker] = formatted

    rows.append(output)

comparison_table = pd.DataFrame(rows)

st.dataframe(
    comparison_table,
    hide_index=True,
    use_container_width=True,
    height=850,
    column_config={
        "Metric": st.column_config.TextColumn(
            "Metric",
            width="medium",
            pinned=True,
        ),
    },
)


# ---------------------------------------------------------
# Category winners
# ---------------------------------------------------------

st.divider()
st.subheader("Category Leaders")

leader_specs = [
    ("Highest Yield", "Dividend Yield", True, "yield"),
    ("Best Dividend Score", "Dividend Score", True, "num"),
    ("Best Quality", "Quality Score", True, "num"),
    ("Best Value", "Value Score", True, "num"),
    ("Best Momentum", "Momentum Score", True, "num"),
    ("Best Overall", "Overall Score", True, "num"),
]

leader_cols = st.columns(3)

for index, (label, metric, higher, kind) in enumerate(leader_specs):
    numeric = pd.to_numeric(compare[metric], errors="coerce")
    if not numeric.notna().any():
        continue

    best_idx = numeric.idxmax() if higher else numeric.idxmin()
    best = compare.loc[best_idx]
    best_value = best[metric]
    if kind == "pct":
        formatted = pct(best_value)
    elif kind == "yield":
        formatted = yield_pct(best_value)
    else:
        formatted = num(best_value)

    with leader_cols[index % 3]:
        st.metric(label, str(best["Ticker"]), formatted)


st.divider()
st.caption(
    "Comparison metrics and MarketScope scores are research indicators, not "
    "investment recommendations. Dividend payments and fundamentals can change."
)

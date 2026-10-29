from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_data import load_market_data


# =========================================================
# Page configuration
# =========================================================

st.set_page_config(
    page_title="Compare Stocks | MarketScope Growth",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Compare Growth Stocks")
st.caption(
    "Compare growth stocks across MarketScope scores, growth, quality, "
    "valuation, and momentum."
)


# =========================================================
# Helpers
# =========================================================

def safe_float(value) -> float:
    try:
        result = float(value)
        return result if np.isfinite(result) else np.nan
    except (TypeError, ValueError):
        return np.nan


def format_number(value, decimals: int = 1) -> str:
    value = safe_float(value)
    if np.isnan(value):
        return "N/A"
    return f"{value:,.{decimals}f}"


def format_currency(value) -> str:
    value = safe_float(value)
    if np.isnan(value):
        return "N/A"
    return f"${value:,.2f}"


def format_percent(value, decimals: int = 1) -> str:
    value = safe_float(value)
    if np.isnan(value):
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_market_cap(value) -> str:
    value = safe_float(value)

    if np.isnan(value):
        return "N/A"

    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"

    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"

    return f"${value:,.0f}"


def get_value(row: pd.Series, column: str):
    if column not in row.index:
        return np.nan
    return row[column]


def get_company_label(row: pd.Series) -> str:
    ticker = str(row.get("Ticker", "")).strip()
    company = str(row.get("Company", ticker)).strip()

    if company and company.lower() != "nan" and company != ticker:
        return f"{ticker} — {company}"

    return ticker


def style_score(value) -> str:
    value = safe_float(value)

    if np.isnan(value):
        return ""

    if value >= 80:
        return "background-color: #d1e7dd; color: #0f5132;"
    if value >= 70:
        return "background-color: #e2f0d9; color: #2f5d31;"
    if value >= 60:
        return "background-color: #fff3cd; color: #664d03;"
    if value >= 50:
        return "background-color: #ffe5b4; color: #7a4b00;"

    return "background-color: #f8d7da; color: #842029;"


# =========================================================
# Load shared MarketScope Growth data
# =========================================================

@st.cache_data(show_spinner=False)
def get_data() -> pd.DataFrame:
    return load_market_data()


with st.spinner("Loading MarketScope Growth data..."):
    data = get_data()


if data is None or data.empty:
    st.warning(
        "No MarketScope Growth data is currently available. "
        "Refresh the market data and try again."
    )
    st.stop()


if "Ticker" not in data.columns:
    st.error("The market dataset does not contain a Ticker column.")
    st.stop()


data = data.copy()

data["Ticker"] = (
    data["Ticker"]
    .astype(str)
    .str.strip()
    .str.upper()
)

data = (
    data[data["Ticker"] != ""]
    .drop_duplicates(subset="Ticker")
    .reset_index(drop=True)
)


# =========================================================
# Stock selection
# =========================================================

ticker_to_label = {}

for _, row in data.iterrows():
    ticker_to_label[row["Ticker"]] = get_company_label(row)


ticker_options = sorted(ticker_to_label.keys())


# Start with highly ranked stocks when possible.
default_tickers: list[str] = []

if "Overall Score" in data.columns:
    ranked = data.copy()
    ranked["Overall Score"] = pd.to_numeric(
        ranked["Overall Score"],
        errors="coerce",
    )

    default_tickers = (
        ranked
        .sort_values("Overall Score", ascending=False)
        ["Ticker"]
        .dropna()
        .head(3)
        .tolist()
    )

if len(default_tickers) < 2:
    default_tickers = ticker_options[:3]


selected_tickers = st.multiselect(
    "Select 2 to 5 stocks",
    options=ticker_options,
    default=default_tickers,
    max_selections=5,
    format_func=lambda ticker: ticker_to_label.get(ticker, ticker),
)


if len(selected_tickers) < 2:
    st.info("Select at least two stocks to begin the comparison.")
    st.stop()


comparison = (
    data[data["Ticker"].isin(selected_tickers)]
    .set_index("Ticker")
    .reindex(selected_tickers)
    .reset_index()
)


st.divider()


# =========================================================
# Stock summary cards
# =========================================================

st.subheader("Stock Overview")

columns = st.columns(len(comparison))

for column, (_, row) in zip(columns, comparison.iterrows()):

    ticker = row["Ticker"]
    company = row.get("Company", ticker)

    with column:
        st.markdown(f"### {ticker}")

        if pd.notna(company) and str(company) != ticker:
            st.caption(str(company))

        overall = safe_float(get_value(row, "Overall Score"))

        if np.isnan(overall):
            st.metric("Overall Score", "N/A")
        else:
            st.metric("Overall Score", f"{overall:.1f}")

        st.write(f"**Rating:** {row.get('Rating', 'N/A')}")
        st.write(f"**Price:** {format_currency(get_value(row, 'Price'))}")
        st.write(
            f"**Market Cap:** "
            f"{format_market_cap(get_value(row, 'Market Cap'))}"
        )
        st.write(f"**Sector:** {row.get('Sector', 'Unknown')}")


st.divider()


# =========================================================
# MarketScope score comparison
# =========================================================

st.subheader("MarketScope Score Comparison")

score_columns = [
    "Overall Score",
    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",
]

available_scores = [
    column
    for column in score_columns
    if column in comparison.columns
]


score_table = comparison[
    ["Ticker"] + available_scores
].copy()

for column in available_scores:
    score_table[column] = pd.to_numeric(
        score_table[column],
        errors="coerce",
    )


styled_scores = (
    score_table
    .set_index("Ticker")
    .style
    .format("{:.1f}", na_rep="N/A")
    .map(style_score)
)

st.dataframe(
    styled_scores,
    use_container_width=True,
)


# =========================================================
# Score radar chart
# =========================================================

radar_scores = [
    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",
]

available_radar_scores = [
    column
    for column in radar_scores
    if column in comparison.columns
]


if available_radar_scores:

    st.subheader("Score Profile")

    fig = go.Figure()

    for _, row in comparison.iterrows():

        ticker = row["Ticker"]

        values = [
            safe_float(row.get(column))
            for column in available_radar_scores
        ]

        values = [
            0 if np.isnan(value) else value
            for value in values
        ]

        categories = [
            column.replace(" Score", "")
            for column in available_radar_scores
        ]

        fig.add_trace(
            go.Scatterpolar(
                r=values + [values[0]],
                theta=categories + [categories[0]],
                fill="toself",
                name=ticker,
                opacity=0.55,
            )
        )

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
            )
        ),
        showlegend=True,
        height=500,
        margin=dict(
            l=40,
            r=40,
            t=40,
            b=40,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


st.divider()


# =========================================================
# Growth comparison
# =========================================================

st.subheader("Growth")

growth_metrics = {
    "Revenue Growth": format_percent,
    "Earnings Growth": format_percent,
    "EPS Growth": format_percent,
    "Forward EPS Growth": format_percent,
}


growth_rows = []

for metric, formatter in growth_metrics.items():

    row_data = {"Metric": metric}

    for _, stock in comparison.iterrows():
        row_data[stock["Ticker"]] = formatter(
            get_value(stock, metric)
        )

    growth_rows.append(row_data)


st.dataframe(
    pd.DataFrame(growth_rows).set_index("Metric"),
    use_container_width=True,
)


# =========================================================
# Growth bar chart
# =========================================================

growth_chart_metrics = [
    metric
    for metric in growth_metrics
    if metric in comparison.columns
]


if growth_chart_metrics:

    fig = go.Figure()

    for _, row in comparison.iterrows():

        values = []

        for metric in growth_chart_metrics:
            value = safe_float(row.get(metric))
            values.append(
                np.nan if np.isnan(value) else value * 100
            )

        fig.add_trace(
            go.Bar(
                name=row["Ticker"],
                x=[
                    metric.replace(" Growth", "")
                    for metric in growth_chart_metrics
                ],
                y=values,
                text=[
                    "" if pd.isna(value) else f"{value:.1f}%"
                    for value in values
                ],
                textposition="auto",
            )
        )

    fig.update_layout(
        barmode="group",
        yaxis_title="Growth (%)",
        legend_title="Ticker",
        height=450,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


st.divider()


# =========================================================
# Quality comparison
# =========================================================

st.subheader("Quality")

quality_metrics = {
    "ROE": format_percent,
    "Operating Margin": format_percent,
    "Profit Margin": format_percent,
    "Free Cash Flow": format_market_cap,
    "Total Debt": format_market_cap,
    "Total Cash": format_market_cap,
}


quality_rows = []

for metric, formatter in quality_metrics.items():

    row_data = {"Metric": metric}

    for _, stock in comparison.iterrows():
        row_data[stock["Ticker"]] = formatter(
            get_value(stock, metric)
        )

    quality_rows.append(row_data)


st.dataframe(
    pd.DataFrame(quality_rows).set_index("Metric"),
    use_container_width=True,
)


st.divider()


# =========================================================
# Valuation comparison
# =========================================================

st.subheader("Valuation")

valuation_metrics = {
    "Forward PE": lambda value: format_number(value, 1),
    "PEG": lambda value: format_number(value, 2),
    "Price/Sales": lambda value: format_number(value, 2),
}


valuation_rows = []

for metric, formatter in valuation_metrics.items():

    row_data = {"Metric": metric}

    for _, stock in comparison.iterrows():
        row_data[stock["Ticker"]] = formatter(
            get_value(stock, metric)
        )

    valuation_rows.append(row_data)


st.dataframe(
    pd.DataFrame(valuation_rows).set_index("Metric"),
    use_container_width=True,
)


st.divider()


# =========================================================
# Momentum comparison
# =========================================================

st.subheader("Momentum")

momentum_metrics = {
    "Price": format_currency,
    "6M Return": format_percent,
    "12M Return": format_percent,
    "50D MA": format_currency,
    "200D MA": format_currency,
    "52W High": format_currency,
}


momentum_rows = []

for metric, formatter in momentum_metrics.items():

    row_data = {"Metric": metric}

    for _, stock in comparison.iterrows():
        row_data[stock["Ticker"]] = formatter(
            get_value(stock, metric)
        )

    momentum_rows.append(row_data)


st.dataframe(
    pd.DataFrame(momentum_rows).set_index("Metric"),
    use_container_width=True,
)


# =========================================================
# Momentum chart
# =========================================================

return_columns = [
    column
    for column in ["6M Return", "12M Return"]
    if column in comparison.columns
]


if return_columns:

    fig = go.Figure()

    for _, row in comparison.iterrows():

        values = []

        for metric in return_columns:
            value = safe_float(row.get(metric))
            values.append(
                np.nan if np.isnan(value) else value * 100
            )

        fig.add_trace(
            go.Bar(
                name=row["Ticker"],
                x=[
                    column.replace(" Return", "")
                    for column in return_columns
                ],
                y=values,
                text=[
                    "" if pd.isna(value) else f"{value:+.1f}%"
                    for value in values
                ],
                textposition="auto",
            )
        )

    fig.update_layout(
        barmode="group",
        yaxis_title="Return (%)",
        legend_title="Ticker",
        height=425,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


st.divider()


# =========================================================
# Quick comparison
# =========================================================

st.subheader("Quick Comparison")

summary_metrics = [
    ("Overall Score", "Overall Score"),
    ("Growth Score", "Growth Score"),
    ("Quality Score", "Quality Score"),
    ("Valuation Score", "Valuation Score"),
    ("Momentum Score", "Momentum Score"),
    ("Revenue Growth", "Revenue Growth"),
    ("Earnings Growth", "Earnings Growth"),
    ("Forward EPS Growth", "Forward EPS Growth"),
    ("ROE", "ROE"),
    ("Forward P/E", "Forward PE"),
    ("PEG", "PEG"),
    ("6M Return", "6M Return"),
    ("12M Return", "12M Return"),
]


quick_rows = []

percentage_columns = {
    "Revenue Growth",
    "Earnings Growth",
    "Forward EPS Growth",
    "ROE",
    "6M Return",
    "12M Return",
}


for label, source_column in summary_metrics:

    if source_column not in comparison.columns:
        continue

    item = {"Metric": label}

    for _, stock in comparison.iterrows():

        value = stock.get(source_column)

        if source_column in percentage_columns:
            item[stock["Ticker"]] = format_percent(value)

        elif "Score" in source_column:
            item[stock["Ticker"]] = format_number(value, 1)

        elif source_column == "PEG":
            item[stock["Ticker"]] = format_number(value, 2)

        else:
            item[stock["Ticker"]] = format_number(value, 1)

    quick_rows.append(item)


st.dataframe(
    pd.DataFrame(quick_rows).set_index("Metric"),
    use_container_width=True,
)


# =========================================================
# Footer
# =========================================================

st.caption(
    "MarketScope Growth is a research tool and does not provide "
    "personalized investment advice."
)
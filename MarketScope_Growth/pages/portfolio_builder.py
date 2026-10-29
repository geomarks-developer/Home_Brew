from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_data import load_market_data


st.set_page_config(
    page_title="Portfolio Builder | MarketScope Growth",
    page_icon="🧺",
    layout="wide",
)

st.title("🧺 Growth Portfolio Builder")
st.caption(
    "Build a model growth-stock portfolio, set position weights, and review "
    "its score, sector, growth, valuation, and momentum profile."
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


def numeric_series(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def weighted_average(values: pd.Series, weights: pd.Series) -> float:
    values = pd.to_numeric(values, errors="coerce")
    weights = pd.to_numeric(weights, errors="coerce")
    valid = values.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def format_percent(value, decimals: int = 1) -> str:
    value = safe_float(value)
    return "N/A" if np.isnan(value) else f"{value * 100:.{decimals}f}%"


def format_score(value) -> str:
    value = safe_float(value)
    return "N/A" if np.isnan(value) else f"{value:.1f}"


def format_ratio(value, decimals: int = 2) -> str:
    value = safe_float(value)
    return "N/A" if np.isnan(value) else f"{value:.{decimals}f}"


def company_label(row: pd.Series) -> str:
    ticker = str(row.get("Ticker", "")).strip()
    company = str(row.get("Company", ticker)).strip()
    if company and company.lower() != "nan" and company != ticker:
        return f"{ticker} — {company}"
    return ticker


def normalized_weights(raw_weights: pd.Series) -> pd.Series:
    weights = pd.to_numeric(raw_weights, errors="coerce").fillna(0).clip(lower=0)
    total = weights.sum()
    if total <= 0:
        return pd.Series(1 / len(weights), index=weights.index)
    return weights / total


# =========================================================
# Load data
# =========================================================

@st.cache_data(show_spinner=False)
def get_data() -> pd.DataFrame:
    return load_market_data()


with st.spinner("Loading MarketScope Growth data..."):
    data = get_data()

if data is None or data.empty:
    st.warning("No MarketScope Growth data is available. Refresh market data and try again.")
    st.stop()

if "Ticker" not in data.columns:
    st.error("The market dataset does not contain a Ticker column.")
    st.stop()

data = data.copy()
data["Ticker"] = data["Ticker"].astype(str).str.strip().str.upper()
data = data[data["Ticker"] != ""].drop_duplicates("Ticker").reset_index(drop=True)

label_map = {
    row["Ticker"]: company_label(row)
    for _, row in data.iterrows()
}

# Default to the five highest-ranked stocks with usable prices.
ranked = data.copy()
ranked["_score"] = numeric_series(ranked, "Overall Score")
ranked["_price"] = numeric_series(ranked, "Price")
default_tickers = (
    ranked[ranked["_price"] > 0]
    .sort_values("_score", ascending=False, na_position="last")
    ["Ticker"]
    .head(5)
    .tolist()
)


# =========================================================
# Portfolio controls
# =========================================================

with st.sidebar:
    st.header("Portfolio Settings")

    budget = st.number_input(
        "Investment amount",
        min_value=100.0,
        value=10_000.0,
        step=500.0,
        format="%.2f",
    )

    weighting_method = st.selectbox(
        "Weighting method",
        options=["Equal Weight", "Score Weighted", "Custom Weight"],
        help=(
            "Score Weighted uses each stock's Overall Score. "
            "Custom Weight lets you enter target percentages."
        ),
    )

    allow_fractional = st.checkbox(
        "Allow fractional shares",
        value=True,
        help="Turn off to estimate whole-share purchases and remaining cash.",
    )

    max_position = st.slider(
        "Maximum position size",
        min_value=10,
        max_value=100,
        value=35,
        step=5,
        format="%d%%",
        disabled=weighting_method == "Custom Weight",
    )

selected_tickers = st.multiselect(
    "Select 2 to 15 growth stocks",
    options=sorted(label_map),
    default=default_tickers,
    max_selections=15,
    format_func=lambda ticker: label_map.get(ticker, ticker),
)

if len(selected_tickers) < 2:
    st.info("Select at least two stocks to build a portfolio.")
    st.stop()

portfolio = (
    data[data["Ticker"].isin(selected_tickers)]
    .set_index("Ticker")
    .reindex(selected_tickers)
    .reset_index()
)

prices = numeric_series(portfolio, "Price")
missing_prices = portfolio.loc[prices.isna() | (prices <= 0), "Ticker"].tolist()
if missing_prices:
    st.warning(
        "These stocks have no usable price and were removed: "
        + ", ".join(missing_prices)
    )
    portfolio = portfolio.loc[prices.notna() & (prices > 0)].reset_index(drop=True)

if len(portfolio) < 2:
    st.error("At least two selected stocks need valid prices.")
    st.stop()


# =========================================================
# Determine target weights
# =========================================================

if weighting_method == "Equal Weight":
    raw_weights = pd.Series(1.0, index=portfolio.index)

elif weighting_method == "Score Weighted":
    scores = numeric_series(portfolio, "Overall Score").clip(lower=0)
    raw_weights = scores.fillna(0)
    if raw_weights.sum() <= 0:
        st.info("Overall Scores are unavailable, so equal weights are being used.")
        raw_weights = pd.Series(1.0, index=portfolio.index)

    cap = max_position / 100.0
    weights = normalized_weights(raw_weights)

    # Iteratively cap oversized holdings and redistribute the remainder.
    if cap * len(weights) >= 1:
        for _ in range(25):
            over = weights > cap + 1e-10
            if not over.any():
                break
            fixed_total = cap * over.sum()
            uncapped = ~over
            weights.loc[over] = cap
            if uncapped.any():
                base = raw_weights.loc[uncapped]
                if base.sum() <= 0:
                    weights.loc[uncapped] = (1 - fixed_total) / uncapped.sum()
                else:
                    weights.loc[uncapped] = (
                        base / base.sum() * (1 - fixed_total)
                    )
        raw_weights = weights
    else:
        st.warning(
            "The maximum position size is too low for the number of stocks. "
            "Weights were normalized without the cap."
        )

else:
    st.subheader("Custom Target Weights")
    st.caption("Enter percentages. They will be normalized if the total is not exactly 100%.")

    default_weight = round(100 / len(portfolio), 2)
    custom_columns = st.columns(min(5, len(portfolio)))
    custom_values: list[float] = []

    for position, (_, row) in enumerate(portfolio.iterrows()):
        ticker = row["Ticker"]
        with custom_columns[position % len(custom_columns)]:
            value = st.number_input(
                ticker,
                min_value=0.0,
                max_value=100.0,
                value=default_weight,
                step=1.0,
                key=f"portfolio_weight_{ticker}",
                format="%.2f",
            )
            custom_values.append(value)

    entered_total = sum(custom_values)
    st.caption(f"Entered weight total: {entered_total:.2f}%")
    raw_weights = pd.Series(custom_values, index=portfolio.index)

weights = normalized_weights(raw_weights)
portfolio["Target Weight"] = weights
portfolio["Target Dollars"] = budget * portfolio["Target Weight"]
portfolio["Price"] = numeric_series(portfolio, "Price")

if allow_fractional:
    portfolio["Shares"] = portfolio["Target Dollars"] / portfolio["Price"]
    portfolio["Invested Dollars"] = portfolio["Target Dollars"]
else:
    portfolio["Shares"] = np.floor(portfolio["Target Dollars"] / portfolio["Price"])
    portfolio["Invested Dollars"] = portfolio["Shares"] * portfolio["Price"]

portfolio["Actual Weight"] = portfolio["Invested Dollars"] / budget
invested_total = float(portfolio["Invested Dollars"].sum())
remaining_cash = max(0.0, float(budget - invested_total))


# =========================================================
# Portfolio summary
# =========================================================

st.divider()
st.subheader("Portfolio Summary")

portfolio_score = weighted_average(
    numeric_series(portfolio, "Overall Score"),
    portfolio["Actual Weight"],
)
weighted_growth = weighted_average(
    numeric_series(portfolio, "Revenue Growth"),
    portfolio["Actual Weight"],
)
weighted_return = weighted_average(
    numeric_series(portfolio, "12M Return"),
    portfolio["Actual Weight"],
)

summary_columns = st.columns(5)
summary_columns[0].metric("Portfolio Value", f"${invested_total:,.2f}")
summary_columns[1].metric("Remaining Cash", f"${remaining_cash:,.2f}")
summary_columns[2].metric("Holdings", f"{len(portfolio)}")
summary_columns[3].metric("Weighted Score", format_score(portfolio_score))
summary_columns[4].metric("Weighted 12M Return", format_percent(weighted_return))

if not allow_fractional and remaining_cash > 0:
    st.caption(
        "Whole-share sizing can leave uninvested cash, so actual weights may differ "
        "from target weights."
    )


# =========================================================
# Allocation table
# =========================================================

st.subheader("Proposed Allocation")

allocation = pd.DataFrame({
    "Ticker": portfolio["Ticker"],
    "Company": portfolio.get("Company", portfolio["Ticker"]),
    "Sector": portfolio.get("Sector", "Unknown"),
    "Price": portfolio["Price"],
    "Target Weight": portfolio["Target Weight"],
    "Actual Weight": portfolio["Actual Weight"],
    "Shares": portfolio["Shares"],
    "Investment": portfolio["Invested Dollars"],
    "Overall Score": numeric_series(portfolio, "Overall Score"),
    "Rating": portfolio.get("Rating", "N/A"),
})

share_format = "{:.4f}" if allow_fractional else "{:.0f}"

st.dataframe(
    allocation.style.format({
        "Price": "${:,.2f}",
        "Target Weight": "{:.1%}",
        "Actual Weight": "{:.1%}",
        "Shares": share_format,
        "Investment": "${:,.2f}",
        "Overall Score": "{:.1f}",
    }, na_rep="N/A"),
    use_container_width=True,
    hide_index=True,
)

csv_data = allocation.to_csv(index=False).encode("utf-8")
st.download_button(
    "Download Allocation CSV",
    data=csv_data,
    file_name="marketscope_growth_portfolio.csv",
    mime="text/csv",
    type="secondary",
)


# =========================================================
# Allocation charts
# =========================================================

left_chart, right_chart = st.columns(2)

with left_chart:
    st.subheader("Holdings Allocation")
    holding_chart = px.pie(
        portfolio,
        names="Ticker",
        values="Actual Weight",
        hole=0.45,
    )
    holding_chart.update_traces(
        textposition="inside",
        texttemplate="%{label}<br>%{percent:.1%}",
        hovertemplate="%{label}<br>Weight: %{percent:.2%}<extra></extra>",
    )
    holding_chart.update_layout(height=430, margin=dict(l=20, r=20, t=30, b=20))
    st.plotly_chart(holding_chart, use_container_width=True)

with right_chart:
    st.subheader("Sector Allocation")
    sector_data = portfolio.copy()
    if "Sector" not in sector_data.columns:
        sector_data["Sector"] = "Unknown"
    sector_data["Sector"] = sector_data["Sector"].fillna("Unknown")
    sector_summary = (
        sector_data.groupby("Sector", as_index=False)["Actual Weight"]
        .sum()
        .sort_values("Actual Weight", ascending=False)
    )
    sector_chart = px.bar(
        sector_summary,
        x="Actual Weight",
        y="Sector",
        orientation="h",
        text="Actual Weight",
    )
    sector_chart.update_traces(
        texttemplate="%{text:.1%}",
        hovertemplate="%{y}<br>Weight: %{x:.2%}<extra></extra>",
    )
    sector_chart.update_layout(
        height=430,
        xaxis_tickformat=".0%",
        yaxis_title=None,
        margin=dict(l=20, r=20, t=30, b=20),
    )
    sector_chart.update_yaxes(categoryorder="total ascending")
    st.plotly_chart(sector_chart, use_container_width=True)


# =========================================================
# Score profile
# =========================================================

st.divider()
st.subheader("Portfolio Score Profile")

score_columns = [
    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",
]
available_scores = [column for column in score_columns if column in portfolio.columns]

if available_scores:
    score_values = [
        weighted_average(numeric_series(portfolio, column), portfolio["Actual Weight"])
        for column in available_scores
    ]
    labels = [column.replace(" Score", "") for column in available_scores]

    radar = go.Figure()
    radar.add_trace(go.Scatterpolar(
        r=score_values + [score_values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="Portfolio",
        hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
    ))
    radar.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        showlegend=False,
        height=460,
        margin=dict(l=40, r=40, t=30, b=30),
    )
    st.plotly_chart(radar, use_container_width=True)
else:
    st.info("Category scores are unavailable for the selected stocks.")


# =========================================================
# Weighted fundamentals
# =========================================================

st.subheader("Weighted Portfolio Metrics")

metric_specs = [
    ("Revenue Growth", "Revenue Growth", format_percent),
    ("Earnings Growth", "Earnings Growth", format_percent),
    ("Forward EPS Growth", "Forward EPS Growth", format_percent),
    ("ROE", "ROE", format_percent),
    ("Operating Margin", "Operating Margin", format_percent),
    ("Forward P/E", "Forward PE", lambda value: format_ratio(value, 1)),
    ("PEG", "PEG", lambda value: format_ratio(value, 2)),
    ("Price/Sales", "Price/Sales", lambda value: format_ratio(value, 2)),
    ("6M Return", "6M Return", format_percent),
    ("12M Return", "12M Return", format_percent),
]

metric_rows = []
for label, source, formatter in metric_specs:
    if source not in portfolio.columns:
        continue
    value = weighted_average(numeric_series(portfolio, source), portfolio["Actual Weight"])
    metric_rows.append({"Metric": label, "Portfolio Weighted Value": formatter(value)})

if metric_rows:
    metric_frame = pd.DataFrame(metric_rows)
    metric_columns = st.columns(2)
    midpoint = (len(metric_frame) + 1) // 2
    with metric_columns[0]:
        st.dataframe(metric_frame.iloc[:midpoint], use_container_width=True, hide_index=True)
    with metric_columns[1]:
        st.dataframe(metric_frame.iloc[midpoint:], use_container_width=True, hide_index=True)


# =========================================================
# Concentration checks
# =========================================================

st.divider()
st.subheader("Diversification Checks")

largest_holding = portfolio.loc[portfolio["Actual Weight"].idxmax()]
largest_sector = sector_summary.iloc[0]

diversification_columns = st.columns(3)
diversification_columns[0].metric(
    "Largest Holding",
    str(largest_holding["Ticker"]),
    f"{largest_holding['Actual Weight']:.1%}",
)
diversification_columns[1].metric(
    "Largest Sector",
    str(largest_sector["Sector"]),
    f"{largest_sector['Actual Weight']:.1%}",
)
diversification_columns[2].metric(
    "Weighted Revenue Growth",
    format_percent(weighted_growth),
)

concentration_notes: list[str] = []
if largest_holding["Actual Weight"] > 0.30:
    concentration_notes.append(
        f"{largest_holding['Ticker']} represents more than 30% of the portfolio."
    )
if largest_sector["Actual Weight"] > 0.50:
    concentration_notes.append(
        f"{largest_sector['Sector']} represents more than 50% of the portfolio."
    )
if len(portfolio) < 5:
    concentration_notes.append("The portfolio contains fewer than five holdings.")

if concentration_notes:
    st.warning(" ".join(concentration_notes))
else:
    st.success("No basic concentration warning was triggered by the selected allocation.")

st.caption(
    "This builder creates a research model from cached MarketScope Growth data. "
    "It does not place trades or provide personalized investment advice."
)

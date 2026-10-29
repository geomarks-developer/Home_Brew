from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_data import load_market_data


st.set_page_config(
    page_title="Risk Dashboard | MarketScope Growth",
    page_icon="⚠️",
    layout="wide",
)

st.title("⚠️ Growth Stock Risk Dashboard")
st.caption(
    "Review valuation, momentum, balance-sheet, concentration, and data-coverage risks "
    "across the MarketScope Growth universe."
)


# =========================================================
# Helpers
# =========================================================

def numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def safe_float(value) -> float:
    try:
        value = float(value)
        return value if np.isfinite(value) else np.nan
    except (TypeError, ValueError):
        return np.nan


def fmt_percent(value, decimals: int = 1) -> str:
    value = safe_float(value)
    return "N/A" if np.isnan(value) else f"{value * 100:.{decimals}f}%"


def fmt_number(value, decimals: int = 1) -> str:
    value = safe_float(value)
    return "N/A" if np.isnan(value) else f"{value:,.{decimals}f}"


def fmt_market_cap(value) -> str:
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


def percentile_score(series: pd.Series, higher_is_riskier: bool = True) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    ranks = values.rank(pct=True, method="average") * 100
    if not higher_is_riskier:
        ranks = 100 - ranks
    return ranks


def first_available(frame: pd.DataFrame, candidates: list[str]) -> str | None:
    return next((column for column in candidates if column in frame.columns), None)


def risk_label(score) -> str:
    score = safe_float(score)
    if np.isnan(score):
        return "Unrated"
    if score >= 75:
        return "High"
    if score >= 50:
        return "Elevated"
    if score >= 25:
        return "Moderate"
    return "Lower"


def risk_color(label: str) -> str:
    return {
        "High": "#c62828",
        "Elevated": "#ef6c00",
        "Moderate": "#f9a825",
        "Lower": "#2e7d32",
        "Unrated": "#757575",
    }.get(label, "#757575")


# =========================================================
# Load and prepare data
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

sector_column = first_available(data, ["Sector", "sector"])
company_column = first_available(data, ["Company", "Short Name", "Name"])

if sector_column is None:
    data["Sector"] = "Unknown"
    sector_column = "Sector"
else:
    data[sector_column] = data[sector_column].fillna("Unknown").replace("", "Unknown")

if company_column is None:
    data["Company"] = data["Ticker"]
    company_column = "Company"


# =========================================================
# Filters
# =========================================================

with st.sidebar:
    st.header("Risk Filters")

    sectors = sorted(data[sector_column].astype(str).unique())
    selected_sectors = st.multiselect("Sectors", sectors, default=sectors)

    minimum_market_cap = st.number_input(
        "Minimum market cap ($B)",
        min_value=0.0,
        value=0.0,
        step=1.0,
    )

    minimum_score = st.slider(
        "Minimum Overall Score",
        min_value=0,
        max_value=100,
        value=0,
    )

    risk_levels = st.multiselect(
        "Risk levels",
        ["High", "Elevated", "Moderate", "Lower", "Unrated"],
        default=["High", "Elevated", "Moderate", "Lower", "Unrated"],
    )

filtered = data[data[sector_column].astype(str).isin(selected_sectors)].copy()

if "Market Cap" in filtered.columns:
    filtered = filtered[numeric(filtered, "Market Cap").fillna(0) >= minimum_market_cap * 1_000_000_000]

if "Overall Score" in filtered.columns:
    filtered = filtered[numeric(filtered, "Overall Score").fillna(0) >= minimum_score]

if filtered.empty:
    st.info("No stocks match the current filters.")
    st.stop()


# =========================================================
# Composite risk model
# =========================================================

risk_parts: dict[str, pd.Series] = {}

# High valuation multiples are treated as higher relative risk.
for column in ["Forward PE", "PEG", "Price/Sales"]:
    if column in filtered.columns:
        risk_parts[f"{column} Risk"] = percentile_score(numeric(filtered, column), True)

# Weaker scores and weaker operating metrics are treated as higher relative risk.
for column in ["Quality Score", "Valuation Score", "Momentum Score", "Overall Score"]:
    if column in filtered.columns:
        risk_parts[f"{column} Risk"] = percentile_score(numeric(filtered, column), False)

for column in ["ROE", "Operating Margin", "Profit Margin", "Free Cash Flow"]:
    if column in filtered.columns:
        risk_parts[f"{column} Risk"] = percentile_score(numeric(filtered, column), False)

# Negative or weaker returns are treated as higher momentum risk.
for column in ["6M Return", "12M Return"]:
    if column in filtered.columns:
        risk_parts[f"{column} Risk"] = percentile_score(numeric(filtered, column), False)

# Higher debt is treated as higher balance-sheet risk.
if "Total Debt" in filtered.columns:
    risk_parts["Debt Risk"] = percentile_score(numeric(filtered, "Total Debt"), True)

if risk_parts:
    risk_frame = pd.DataFrame(risk_parts, index=filtered.index)
    filtered["Risk Score"] = risk_frame.mean(axis=1, skipna=True)
    filtered["Risk Inputs"] = risk_frame.notna().sum(axis=1)
else:
    filtered["Risk Score"] = np.nan
    filtered["Risk Inputs"] = 0

filtered["Risk Level"] = filtered["Risk Score"].apply(risk_label)
filtered = filtered[filtered["Risk Level"].isin(risk_levels)]

if filtered.empty:
    st.info("No stocks match the selected risk levels.")
    st.stop()


# =========================================================
# Headline metrics
# =========================================================

st.divider()
metric_columns = st.columns(5)
metric_columns[0].metric("Stocks Reviewed", f"{len(filtered):,}")
metric_columns[1].metric("Median Risk Score", fmt_number(filtered["Risk Score"].median(), 1))
metric_columns[2].metric("High-Risk Stocks", f"{(filtered['Risk Level'] == 'High').sum():,}")
metric_columns[3].metric("Negative 12M Return", f"{(numeric(filtered, '12M Return') < 0).sum():,}")
metric_columns[4].metric("Below 200D MA", f"{(numeric(filtered, 'Price') < numeric(filtered, '200D MA')).sum():,}")

st.caption(
    "Risk Score is a relative 0–100 ranking within the filtered universe. "
    "A higher score indicates more risk signals, not a forecast of loss."
)


# =========================================================
# Risk distribution and sector exposure
# =========================================================

left, right = st.columns(2)

with left:
    st.subheader("Risk-Level Distribution")
    order = ["High", "Elevated", "Moderate", "Lower", "Unrated"]
    counts = filtered["Risk Level"].value_counts().reindex(order, fill_value=0).reset_index()
    counts.columns = ["Risk Level", "Stocks"]
    fig = px.bar(
        counts,
        x="Risk Level",
        y="Stocks",
        color="Risk Level",
        color_discrete_map={label: risk_color(label) for label in order},
        text="Stocks",
    )
    fig.update_layout(showlegend=False, height=400, margin=dict(l=20, r=20, t=20, b=20))
    fig.update_traces(textposition="outside", hovertemplate="%{x}: %{y} stocks<extra></extra>")
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Median Risk by Sector")
    sector_risk = (
        filtered.groupby(sector_column, as_index=False)
        .agg(Median_Risk=("Risk Score", "median"), Stocks=("Ticker", "count"))
        .sort_values("Median_Risk", ascending=True)
    )
    fig = px.bar(
        sector_risk,
        x="Median_Risk",
        y=sector_column,
        orientation="h",
        color="Median_Risk",
        color_continuous_scale="RdYlGn_r",
        text="Median_Risk",
        hover_data={"Stocks": True},
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(
        height=400,
        xaxis_title="Median Risk Score",
        yaxis_title=None,
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)


# =========================================================
# Risk-return map
# =========================================================

st.divider()
st.subheader("Risk vs. Return")

return_column = first_available(filtered, ["12M Return", "6M Return"])
if return_column:
    chart_data = filtered.copy()
    chart_data["Return Percent"] = numeric(chart_data, return_column) * 100
    chart_data["Bubble Size"] = numeric(chart_data, "Market Cap").clip(lower=0)
    if chart_data["Bubble Size"].notna().sum() == 0:
        chart_data["Bubble Size"] = 1

    fig = px.scatter(
        chart_data,
        x="Risk Score",
        y="Return Percent",
        size="Bubble Size",
        size_max=45,
        color="Risk Level",
        color_discrete_map={level: risk_color(level) for level in risk_levels},
        hover_name="Ticker",
        hover_data={
            company_column: True,
            sector_column: True,
            "Risk Score": ":.1f",
            "Return Percent": ":+.1f",
            "Bubble Size": False,
        },
    )
    fig.add_hline(y=0, line_dash="dot", line_color="gray")
    fig.update_layout(
        height=520,
        xaxis_title="Relative Risk Score",
        yaxis_title=f"{return_column.replace(' Return', '')} Return (%)",
        legend_title="Risk Level",
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Return data is unavailable for the risk-return chart.")


# =========================================================
# Risk factor panels
# =========================================================

st.divider()
st.subheader("Risk Signals")

tab_valuation, tab_momentum, tab_balance, tab_coverage = st.tabs(
    ["Valuation", "Momentum", "Balance Sheet", "Data Coverage"]
)

with tab_valuation:
    valuation_columns = [column for column in ["Ticker", company_column, "Forward PE", "PEG", "Price/Sales", "Valuation Score", "Risk Score"] if column in filtered.columns]
    valuation = filtered[valuation_columns].copy()
    valuation = valuation.sort_values("Risk Score", ascending=False)
    st.dataframe(
        valuation.style.format({
            "Forward PE": "{:.1f}",
            "PEG": "{:.2f}",
            "Price/Sales": "{:.2f}",
            "Valuation Score": "{:.1f}",
            "Risk Score": "{:.1f}",
        }, na_rep="N/A"),
        use_container_width=True,
        hide_index=True,
    )

with tab_momentum:
    momentum_columns = [column for column in ["Ticker", company_column, "Price", "6M Return", "12M Return", "50D MA", "200D MA", "Momentum Score", "Risk Score"] if column in filtered.columns]
    momentum = filtered[momentum_columns].copy().sort_values("Risk Score", ascending=False)
    formats = {
        "Price": "${:,.2f}",
        "6M Return": "{:+.1%}",
        "12M Return": "{:+.1%}",
        "50D MA": "${:,.2f}",
        "200D MA": "${:,.2f}",
        "Momentum Score": "{:.1f}",
        "Risk Score": "{:.1f}",
    }
    st.dataframe(momentum.style.format(formats, na_rep="N/A"), use_container_width=True, hide_index=True)

with tab_balance:
    balance_columns = [column for column in ["Ticker", company_column, "Market Cap", "Total Debt", "Total Cash", "Free Cash Flow", "ROE", "Operating Margin", "Quality Score", "Risk Score"] if column in filtered.columns]
    balance = filtered[balance_columns].copy().sort_values("Risk Score", ascending=False)
    formats = {
        "Market Cap": fmt_market_cap,
        "Total Debt": fmt_market_cap,
        "Total Cash": fmt_market_cap,
        "Free Cash Flow": fmt_market_cap,
        "ROE": "{:.1%}",
        "Operating Margin": "{:.1%}",
        "Quality Score": "{:.1f}",
        "Risk Score": "{:.1f}",
    }
    st.dataframe(balance.style.format(formats, na_rep="N/A"), use_container_width=True, hide_index=True)

with tab_coverage:
    important_fields = [
        column for column in [
            "Revenue Growth", "Earnings Growth", "Forward EPS Growth", "ROE",
            "Operating Margin", "Forward PE", "PEG", "Price/Sales",
            "6M Return", "12M Return", "50D MA", "200D MA",
        ] if column in filtered.columns
    ]

    coverage = filtered[["Ticker", company_column]].copy()
    coverage["Available Fields"] = filtered[important_fields].notna().sum(axis=1) if important_fields else 0
    coverage["Possible Fields"] = len(important_fields)
    coverage["Coverage"] = coverage["Available Fields"] / max(len(important_fields), 1)
    coverage = coverage.sort_values(["Coverage", "Ticker"])

    st.dataframe(
        coverage.style.format({"Coverage": "{:.0%}"}),
        use_container_width=True,
        hide_index=True,
    )


# =========================================================
# Highest-risk watch table
# =========================================================

st.divider()
st.subheader("Highest Relative Risk")

display_columns = [
    column for column in [
        "Ticker", company_column, sector_column, "Risk Score", "Risk Level",
        "Overall Score", "Forward PE", "PEG", "12M Return", "Market Cap",
        "Risk Inputs",
    ] if column in filtered.columns
]

risk_table = filtered[display_columns].sort_values("Risk Score", ascending=False).head(25)
formatters = {
    "Risk Score": "{:.1f}",
    "Overall Score": "{:.1f}",
    "Forward PE": "{:.1f}",
    "PEG": "{:.2f}",
    "12M Return": "{:+.1%}",
    "Market Cap": fmt_market_cap,
}

st.dataframe(
    risk_table.style.format(formatters, na_rep="N/A"),
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download Risk Dashboard CSV",
    data=filtered.sort_values("Risk Score", ascending=False).to_csv(index=False).encode("utf-8"),
    file_name="marketscope_growth_risk_dashboard.csv",
    mime="text/csv",
    type="secondary",
)

st.caption(
    "MarketScope Growth is a research tool. Relative risk rankings depend on available cached data "
    "and should not be treated as personalized investment advice or a prediction of future performance."
)

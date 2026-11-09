from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import DEFAULT_NUMBER_OF_HOLDINGS, DEFAULT_PORTFOLIO_VALUE, MAX_PORTFOLIO_HOLDINGS
from market_data import get_market_data


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def safe_num(value, default=0.0) -> float:
    try:
        value = float(value)
        return value if np.isfinite(value) else default
    except (TypeError, ValueError):
        return default


def weighted_average(frame: pd.DataFrame, column: str) -> float:
    if frame.empty or column not in frame.columns:
        return np.nan
    values = pd.to_numeric(frame[column], errors="coerce")
    weights = pd.to_numeric(frame["Weight"], errors="coerce") / 100
    valid = values.notna() & weights.notna()
    if not valid.any() or weights[valid].sum() == 0:
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def pct(value) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.2%}"


def yield_pct(value) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):.2f}%"


def num(value, digits=1) -> str:
    return "N/A" if pd.isna(value) else f"{float(value):,.{digits}f}"


# ---------------------------------------------------------
# Header and data
# ---------------------------------------------------------

st.header("🧺 Dividend Portfolio Builder")
st.caption(
    "Build a Dividend Aristocrat portfolio and estimate allocation, dividend income, "
    "sector exposure, portfolio yield, risk, and MarketScope scores."
)

try:
    data = get_market_data(show_progress=False)
except Exception as exc:
    st.error(f"Unable to load MarketScope Dividend data: {exc}")
    st.stop()


df = data.get("dividend_df", pd.DataFrame()).copy()

if df.empty:
    st.warning("No Dividend Aristocrat data is currently available.")
    st.stop()


df = df.sort_values(["Overall Score", "Ticker"], ascending=[False, True]).reset_index(drop=True)
tickers = df["Ticker"].dropna().astype(str).tolist()


# ---------------------------------------------------------
# Portfolio setup
# ---------------------------------------------------------

st.subheader("Portfolio Setup")

setup_1, setup_2 = st.columns([1, 2])

with setup_1:
    portfolio_value = st.number_input(
        "Portfolio value ($)",
        min_value=100.0,
        value=float(DEFAULT_PORTFOLIO_VALUE),
        step=1000.0,
        format="%.2f",
    )

with setup_2:
    default_count = min(DEFAULT_NUMBER_OF_HOLDINGS, len(tickers))
    default_tickers = tickers[:default_count]
    selected = st.multiselect(
        "Select Dividend Aristocrats",
        options=sorted(tickers),
        default=default_tickers,
        max_selections=MAX_PORTFOLIO_HOLDINGS,
    )

if not selected:
    st.info("Select at least one Dividend Aristocrat to build a portfolio.")
    st.stop()


# ---------------------------------------------------------
# Editable weights
# ---------------------------------------------------------

portfolio = (
    df[df["Ticker"].isin(selected)]
    .set_index("Ticker")
    .reindex(selected)
    .reset_index()
)

equal_weight = 100.0 / len(portfolio)

weight_input = portfolio[["Ticker", "Company", "Sector"]].copy()
weight_input["Weight"] = equal_weight

st.subheader("Portfolio Weights")
st.caption(
    "Edit the Weight column if you want a custom allocation. Weights should total 100%."
)

edited = st.data_editor(
    weight_input,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    disabled=["Ticker", "Company", "Sector"],
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", pinned=True),
        "Company": st.column_config.TextColumn("Company", width="medium"),
        "Sector": st.column_config.TextColumn("Sector", width="medium"),
        "Weight": st.column_config.NumberColumn(
            "Weight (%)",
            min_value=0.0,
            max_value=100.0,
            step=0.5,
            format="%.2f",
            required=True,
        ),
    },
    key="dividend_portfolio_weights",
)

portfolio["Weight"] = pd.to_numeric(edited["Weight"], errors="coerce").fillna(0.0)
weight_total = float(portfolio["Weight"].sum())

if abs(weight_total - 100.0) > 0.01:
    st.warning(f"Portfolio weights currently total {weight_total:.2f}%. Adjust them to 100% for a fully allocated portfolio.")


# ---------------------------------------------------------
# Position calculations
# ---------------------------------------------------------

portfolio["Price"] = pd.to_numeric(portfolio["Price"], errors="coerce")
portfolio["Dividend Yield"] = pd.to_numeric(portfolio["Dividend Yield"], errors="coerce")
portfolio["Dividend Rate"] = pd.to_numeric(portfolio["Dividend Rate"], errors="coerce")
portfolio["Allocation"] = portfolio_value * portfolio["Weight"] / 100
portfolio["Estimated Shares"] = np.where(
    portfolio["Price"] > 0,
    portfolio["Allocation"] / portfolio["Price"],
    np.nan,
)
portfolio["Estimated Annual Income"] = (
    portfolio["Allocation"] * (portfolio["Dividend Yield"].fillna(0) / 100)
)
portfolio["Estimated Monthly Income"] = portfolio["Estimated Annual Income"] / 12

portfolio_yield = weighted_average(portfolio, "Dividend Yield")
annual_income = float(portfolio["Estimated Annual Income"].sum())
monthly_income = annual_income / 12
weighted_growth = weighted_average(portfolio, "Dividend Growth 5Y")
weighted_payout = weighted_average(portfolio, "Payout Ratio")
weighted_beta = weighted_average(portfolio, "Beta")
weighted_score = weighted_average(portfolio, "Overall Score")


# ---------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------

st.divider()
st.subheader("Portfolio Summary")

m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Portfolio Value", f"${portfolio_value:,.0f}")
m2.metric("Holdings", len(portfolio))
m3.metric("Portfolio Yield", yield_pct(portfolio_yield))
m4.metric("Annual Income", f"${annual_income:,.2f}")
m5.metric("Monthly Income", f"${monthly_income:,.2f}")
m6.metric("Overall Score", num(weighted_score))

m7, m8, m9 = st.columns(3)
m7.metric("Weighted 5Y Div Growth", pct(weighted_growth))
m8.metric("Weighted Payout Ratio", pct(weighted_payout))
m9.metric("Weighted Beta", num(weighted_beta, 2))


# ---------------------------------------------------------
# Allocation charts
# ---------------------------------------------------------

st.divider()
st.subheader("Allocation")

chart_1, chart_2 = st.columns(2)

with chart_1:
    holding_fig = px.pie(
        portfolio,
        names="Ticker",
        values="Weight",
        hole=0.45,
        title="Holdings Allocation",
    )
    holding_fig.update_traces(textposition="inside", textinfo="label+percent")
    holding_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), legend_title=None)
    st.plotly_chart(holding_fig, use_container_width=True, config={"displaylogo": False})

with chart_2:
    sector_allocation = (
        portfolio.groupby("Sector", as_index=False)["Weight"]
        .sum()
        .sort_values("Weight", ascending=False)
    )
    sector_fig = px.pie(
        sector_allocation,
        names="Sector",
        values="Weight",
        hole=0.45,
        title="Sector Allocation",
    )
    sector_fig.update_traces(textposition="inside", textinfo="label+percent")
    sector_fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), legend_title=None)
    st.plotly_chart(sector_fig, use_container_width=True, config={"displaylogo": False})


# ---------------------------------------------------------
# Income contribution
# ---------------------------------------------------------

st.divider()
st.subheader("Estimated Dividend Income by Holding")

income_fig = px.bar(
    portfolio.sort_values("Estimated Annual Income", ascending=False),
    x="Ticker",
    y="Estimated Annual Income",
    color="Sector",
    text="Estimated Annual Income",
)
income_fig.update_traces(texttemplate="$%{text:.0f}", textposition="outside")
income_fig.update_layout(
    height=460,
    xaxis_title=None,
    yaxis_title="Estimated Annual Income ($)",
    legend_title=None,
    margin=dict(l=10, r=10, t=10, b=10),
)
st.plotly_chart(income_fig, use_container_width=True, config={"displaylogo": False})


# ---------------------------------------------------------
# Portfolio score profile
# ---------------------------------------------------------

st.divider()
st.subheader("Portfolio MarketScope Profile")

score_names = [
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
    "Overall Score",
]
score_values = [weighted_average(portfolio, score) for score in score_names]

radar_fig = go.Figure()
radar_fig.add_trace(
    go.Scatterpolar(
        r=score_values + [score_values[0]],
        theta=[name.replace(" Score", "") for name in score_names] + ["Dividend"],
        fill="toself",
        name="Portfolio",
    )
)
radar_fig.update_layout(
    height=500,
    polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
    showlegend=False,
    margin=dict(l=30, r=30, t=30, b=30),
)
st.plotly_chart(radar_fig, use_container_width=True, config={"displaylogo": False})


# ---------------------------------------------------------
# Holdings detail
# ---------------------------------------------------------

st.divider()
st.subheader("Holdings Detail")

display_columns = [
    "Ticker",
    "Company",
    "Sector",
    "Weight",
    "Price",
    "Allocation",
    "Estimated Shares",
    "Dividend Yield",
    "Dividend Growth 5Y",
    "Payout Ratio",
    "Estimated Annual Income",
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Overall Score",
]
display_columns = [c for c in display_columns if c in portfolio.columns]

st.dataframe(
    portfolio[display_columns],
    hide_index=True,
    use_container_width=True,
    column_config={
        "Weight": st.column_config.NumberColumn("Weight", format="%.2f%%"),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Allocation": st.column_config.NumberColumn("Allocation", format="$%.2f"),
        "Estimated Shares": st.column_config.NumberColumn("Est. Shares", format="%.2f"),
        "Dividend Yield": st.column_config.NumberColumn("Yield", format="%.2f%%"),
        "Dividend Growth 5Y": st.column_config.NumberColumn("5Y Growth", format="%.2f%%"),
        "Payout Ratio": st.column_config.NumberColumn("Payout", format="%.2f%%"),
        "Estimated Annual Income": st.column_config.NumberColumn("Annual Income", format="$%.2f"),
        "Dividend Score": st.column_config.ProgressColumn("Dividend", min_value=0, max_value=100, format="%.1f"),
        "Quality Score": st.column_config.ProgressColumn("Quality", min_value=0, max_value=100, format="%.1f"),
        "Value Score": st.column_config.ProgressColumn("Value", min_value=0, max_value=100, format="%.1f"),
        "Overall Score": st.column_config.ProgressColumn("Overall", min_value=0, max_value=100, format="%.1f"),
    },
)


# ---------------------------------------------------------
# Export
# ---------------------------------------------------------

st.divider()
export_df = portfolio.copy()
export_df["Portfolio Value"] = portfolio_value
export_df["Portfolio Yield"] = portfolio_yield
export_df["Portfolio Annual Income"] = annual_income

st.download_button(
    "⬇️ Download Portfolio (CSV)",
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name="marketscope_dividend_portfolio.csv",
    mime="text/csv",
    type="secondary",
)

st.caption(
    "Income estimates use the current dividend yield in the MarketScope dataset and assume the selected allocation amounts. "
    "Fractional-share estimates are used for analysis. Dividends are not guaranteed and can change."
)

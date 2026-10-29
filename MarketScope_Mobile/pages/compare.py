"""MarketScope Mobile - comparison page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

COMPARE_UNIVERSE = (
    "AAPL", "ABBV", "AFL", "AMD", "AMZN", "AVGO", "BLK", "BRK-B", "CRM", "CVX",
    "GOOG", "JNJ", "JPM", "KO", "META", "MSFT", "NVDA", "PEP", "PG", "TXN",
    "SPY", "QQQ", "VTI", "SCHD", "VIG", "VYM", "BND", "VXUS", "XLK", "XLF",
)


def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan

def normalize_yield(value: object) -> float:
    value = number(value)

    if not np.isfinite(value):
        return np.nan

    if value > 1:
        value /= 100

    return value

def fmt(value: object, pattern: str) -> str:
    numeric = number(value)
    return pattern.format(numeric) if np.isfinite(numeric) else "N/A"


@st.cache_data(ttl=3600, show_spinner=False)
def load_comparison(tickers: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    histories: list[pd.DataFrame] = []

    for ticker in tickers:
        try:
            security = yf.Ticker(ticker)
            info = security.info or {}
            history = security.history(period="1y", auto_adjust=True)
            closes = pd.Series(dtype=float)
            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()

            price = float(closes.iloc[-1]) if not closes.empty else number(info.get("currentPrice"))
            ret_3m = closes.iloc[-1] / closes.iloc[-64] - 1 if len(closes) > 63 else np.nan
            ret_6m = closes.iloc[-1] / closes.iloc[-127] - 1 if len(closes) > 126 else np.nan
            ret_12m = closes.iloc[-1] / closes.iloc[-252] - 1 if len(closes) > 251 else np.nan
            volatility = float(closes.pct_change().dropna().std() * np.sqrt(252)) if len(closes) > 20 else np.nan

            rows.append({
                "Ticker": ticker,
                "Name": info.get("shortName") or ticker,
                "Type": info.get("quoteType") or "Unknown",
                "Sector": info.get("sector") or "Fund / Other",
                "Price": price,
                "Market Cap / Assets": number(info.get("marketCap")) if info.get("quoteType") != "ETF" else number(info.get("totalAssets")),
                "Forward PE": number(info.get("forwardPE")),
                "Price/Book": number(info.get("priceToBook")),
                "Dividend Yield": normalize_yield(info.get("dividendYield")),
                "Revenue Growth": number(info.get("revenueGrowth")),
                "Earnings Growth": number(info.get("earningsGrowth")),
                "ROE": number(info.get("returnOnEquity")),
                "3M Return": ret_3m,
                "6M Return": ret_6m,
                "12M Return": ret_12m,
                "Volatility": volatility,
            })

            if not closes.empty:
                indexed = closes / closes.iloc[0] * 100
                histories.append(pd.DataFrame({
                    "Date": indexed.index,
                    "Indexed Value": indexed.values,
                    "Ticker": ticker,
                }))
        except Exception:
            continue

    summary = pd.DataFrame(rows)
    performance = pd.concat(histories, ignore_index=True) if histories else pd.DataFrame()
    return summary, performance


def metric_rows(data: pd.DataFrame) -> list[tuple[str, str]]:
    return [
        ("Price", "${:,.2f}"),
        ("Forward PE", "{:.1f}"),
        ("Price/Book", "{:.2f}"),
        ("Dividend Yield", "{:.2%}"),
        ("Revenue Growth", "{:.1%}"),
        ("Earnings Growth", "{:.1%}"),
        ("ROE", "{:.1%}"),
        ("3M Return", "{:.1%}"),
        ("6M Return", "{:.1%}"),
        ("12M Return", "{:.1%}"),
        ("Volatility", "{:.1%}"),
    ]


st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"] {display:none;}
<<<<<<< HEAD
.block-container {max-width:520px;padding:1rem 1rem 5rem 1rem;}
=======
.block-container {max-width:520px;padding:3rem 1rem 5rem 1rem;}
>>>>>>> 697fedb (Heading spacing)
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.compare-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.85rem;background:rgba(128,128,128,.05);}
.compare-ticker {font-size:1.2rem;font-weight:800;}
.compare-name {font-size:.78rem;color:#9aa3b2;min-height:38px;}
.metric-label {font-size:.78rem;color:#9aa3b2;margin-top:.45rem;}
.metric-value {font-size:1rem;font-weight:700;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">⚖️ Compare</div>', unsafe_allow_html=True)
st.markdown('<div class="module-subtitle">Compare two or three stocks or ETFs using return, valuation, income, growth, quality, and risk metrics.</div>', unsafe_allow_html=True)

home_col, watch_col = st.columns(2)
with home_col:
    st.page_link("mobile_home.py", label="Home", icon="🏠", width="stretch")
with watch_col:
    st.page_link("pages/watchlist.py", label="Watchlist", icon="⭐", width="stretch")

watchlist = [str(t).upper() for t in st.session_state.get("mobile_watchlist", [])]
options = list(dict.fromkeys(watchlist + list(COMPARE_UNIVERSE)))
defaults = watchlist[:3] if len(watchlist) >= 2 else ["MSFT", "GOOG"]
defaults = [ticker for ticker in defaults if ticker in options][:3]

selected = st.multiselect(
    "Choose 2 or 3 symbols",
    options=options,
    default=defaults,
    max_selections=3,
    placeholder="Select symbols...",
)
custom = st.text_input(
    "Add a symbol",
    placeholder="Enter ticker, then press Enter",
    label_visibility="collapsed",
).strip().upper()
if custom and custom not in selected:
    selected = (selected + [custom])[:3]

if len(selected) < 2:
    st.info("Select at least two symbols to compare.")
    st.stop()

refresh = st.button("🔄 Refresh comparison", use_container_width=True)
if refresh:
    load_comparison.clear()

with st.spinner("Loading comparison..."):
    data, performance = load_comparison(tuple(selected))

if data.empty or len(data) < 2:
    st.warning("Comparison data is unavailable for one or more selected symbols.")
    st.stop()

data["Ticker"] = pd.Categorical(data["Ticker"], categories=selected, ordered=True)
data = data.sort_values("Ticker").reset_index(drop=True)
data["Ticker"] = data["Ticker"].astype(str)

st.markdown('<div class="section-label">SUMMARY</div>', unsafe_allow_html=True)
columns = st.columns(len(data))
for container, (_, row) in zip(columns, data.iterrows()):
    with container:
        st.markdown(
            f'<div class="compare-card"><div class="compare-ticker">{row["Ticker"]}</div>'
            f'<div class="compare-name">{row["Name"]}</div>'
            f'<div class="metric-label">Price</div><div class="metric-value">{fmt(row["Price"], "${:,.2f}")}</div>'
            f'<div class="metric-label">12M Return</div><div class="metric-value">{fmt(row["12M Return"], "{:.1%}")}</div>'
            f'<div class="metric-label">Yield</div><div class="metric-value">{fmt(row["Dividend Yield"], "{:.2%}")}</div></div>',
            unsafe_allow_html=True,
        )

st.divider()
st.markdown('<div class="section-label">METRIC COMPARISON</div>', unsafe_allow_html=True)
for metric, pattern in metric_rows(data):
    with st.expander(metric, expanded=metric in {"12M Return", "Forward PE"}):
        metric_cols = st.columns(len(data))
        for container, (_, row) in zip(metric_cols, data.iterrows()):
            container.metric(str(row["Ticker"]), fmt(row.get(metric), pattern))

st.divider()
st.markdown('<div class="section-label">GROWTH OF $100</div>', unsafe_allow_html=True)
if not performance.empty:
    fig = px.line(performance, x="Date", y="Indexed Value", color="Ticker")
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.update_layout(
        height=360,
        margin=dict(l=5, r=5, t=10, b=5),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=.5),
        xaxis_title="",
        yaxis_title="Value",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown('<div class="section-label">RETURN VS RISK</div>', unsafe_allow_html=True)
chart = data.dropna(subset=["12M Return", "Volatility"]).copy()
if not chart.empty:
    fig = px.scatter(
        chart,
        x="Volatility",
        y="12M Return",
        text="Ticker",
        color="Ticker",
        hover_name="Name",
        hover_data={"Forward PE": ":.1f", "Dividend Yield": ":.2%"},
    )
    fig.update_traces(textposition="top center", marker_size=16)
    fig.update_xaxes(tickformat=".0%", title="Volatility")
    fig.update_yaxes(tickformat=".0%", title="12M Return")
    fig.update_layout(height=340, margin=dict(l=5, r=5, t=10, b=5), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.caption("Comparison metrics are informational research inputs and are not investment recommendations.")

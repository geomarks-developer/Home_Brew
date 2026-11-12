"""stockchoice - universal stock and ETF details page."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf
from app_utils import apply_card_density, cache_ttl, initialize_settings

# Make the stockchoice_Mobile project root importable when this file is in pages/.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from database import add_to_watchlist, load_watchlist


initialize_settings()
def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def fmt_number(value: object, pattern: str) -> str:
    value = number(value)
    return pattern.format(value) if np.isfinite(value) else "N/A"


def normalize_yield(value: object) -> float:
    value = number(value)
    if not np.isfinite(value) or value < 0:
        return np.nan
    if value > 0.20:
        value /= 100
    return value


def fmt_large(value: object) -> str:
    value = number(value)
    if not np.isfinite(value):
        return "N/A"
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= divisor:
            return f"${value / divisor:,.2f}{suffix}"
    return f"${value:,.0f}"


def calculate_rsi(closes: pd.Series, period: int = 14) -> float:
    if len(closes) <= period:
        return np.nan
    delta = closes.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = -delta.clip(upper=0).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return number(rsi.iloc[-1])


@st.cache_data(ttl=cache_ttl(), show_spinner=False)
def load_details(symbol: str) -> tuple[dict, pd.DataFrame]:
    ticker = yf.Ticker(symbol)
    info = ticker.info or {}
    history = ticker.history(period="5y", auto_adjust=True)
    if history is None:
        history = pd.DataFrame()
    return info, history


def metric(label: str, value: str) -> None:
    st.metric(label, value)


apply_card_density()
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {display:none;}
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"] {display:none !important; visibility:hidden !important;}
    .block-container {max-width:520px;padding:2.75rem 1rem 5rem 1rem;}
    .detail-symbol {font-size:2.15rem;font-weight:850;line-height:1.05;margin-top:.4rem;}
    .detail-name {font-size:.95rem;color:#9aa3b2;margin-top:.25rem;margin-bottom:.9rem;}
    .section-label {font-size:.80rem;color:#9aa3b2;font-weight:700;margin-top:1.15rem;margin-bottom:.35rem;letter-spacing:.02em;}
    .description {border:1px solid rgba(128,128,128,.22);border-radius:14px;padding:.9rem 1rem;background:rgba(128,128,128,.04);font-size:.90rem;line-height:1.5;}
    </style>
    """,
    unsafe_allow_html=True,
)

symbol = str(
    st.session_state.get("mobile_selected_ticker")
    or st.session_state.get("mobile_search")
    or ""
).strip().upper()

nav_left, nav_right = st.columns(2)
with nav_left:
    if st.button("← Watchlist", use_container_width=True):
        st.switch_page("pages/watchlist.py")
with nav_right:
    if st.button("🏠 Home", use_container_width=True):
        st.switch_page("app.py")

if not symbol:
    st.warning("No security is selected. Return to the watchlist and choose Details.")
    st.stop()

with st.spinner(f"Loading {symbol}..."):
    try:
        info, history = load_details(symbol)
    except Exception as exc:
        st.error(f"Unable to load {symbol}: {exc}")
        st.stop()

name = str(info.get("longName") or info.get("shortName") or symbol)
quote_type = str(info.get("quoteType") or "Unknown").upper()
category = str(info.get("category") or "")

st.markdown(f'<div class="detail-symbol">{symbol}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="detail-name">{name}</div>', unsafe_allow_html=True)

closes = pd.Series(dtype=float)
if not history.empty and "Close" in history.columns:
    closes = pd.to_numeric(history["Close"], errors="coerce").dropna()

price = float(closes.iloc[-1]) if not closes.empty else number(info.get("currentPrice") or info.get("regularMarketPrice"))
prev = float(closes.iloc[-2]) if len(closes) >= 2 else number(info.get("previousClose"))
day_change = (price / prev - 1) if np.isfinite(price) and np.isfinite(prev) and prev else np.nan

p1, p2 = st.columns(2)
with p1:
    metric("Price", fmt_number(price, "${:,.2f}"))
with p2:
    metric("1D Change", fmt_number(day_change, "{:+.2%}"))

st.markdown('<div class="section-label">OVERVIEW</div>', unsafe_allow_html=True)
a, b = st.columns(2)
with a:
    metric("52W High", fmt_number(info.get("fiftyTwoWeekHigh"), "${:,.2f}"))
    metric("Forward P/E", fmt_number(info.get("forwardPE"), "{:.2f}"))
with b:
    metric("52W Low", fmt_number(info.get("fiftyTwoWeekLow"), "${:,.2f}"))
    metric("Dividend Yield", fmt_number(normalize_yield(info.get("dividendYield")), "{:.2%}"))

if quote_type == "ETF":
    a, b = st.columns(2)
    with a:
        metric("Net Assets", fmt_large(info.get("totalAssets") or info.get("netAssets")))
    with b:
        metric("Expense Ratio", fmt_number(info.get("annualReportExpenseRatio"), "{:.2%}"))
    if category:
        st.caption(f"Category: {category}")
else:
    a, b = st.columns(2)
    with a:
        metric("Market Cap", fmt_large(info.get("marketCap")))
        metric("Price / Book", fmt_number(info.get("priceToBook"), "{:.2f}"))
    with b:
        metric("Trailing P/E", fmt_number(info.get("trailingPE"), "{:.2f}"))
        metric("ROE", fmt_number(info.get("returnOnEquity"), "{:.1%}"))

st.markdown('<div class="section-label">PERFORMANCE</div>', unsafe_allow_html=True)

def trailing_return(days: int) -> float:
    if len(closes) <= days:
        return np.nan
    return float(closes.iloc[-1] / closes.iloc[-days - 1] - 1)

r1, r2 = st.columns(2)
with r1:
    metric("1M", fmt_number(trailing_return(21), "{:+.1%}"))
    metric("6M", fmt_number(trailing_return(126), "{:+.1%}"))
with r2:
    metric("3M", fmt_number(trailing_return(63), "{:+.1%}"))
    metric("1Y", fmt_number(trailing_return(252), "{:+.1%}"))

if st.session_state.get("mobile_show_charts", True):
    st.markdown('<div class="section-label">PRICE HISTORY</div>', unsafe_allow_html=True)
    period = st.segmented_control("Range", ["1M", "3M", "6M", "1Y", "2Y", "5Y"], default="1Y", label_visibility="collapsed")
    period_days = {"1M": 31, "3M": 93, "6M": 186, "1Y": 366, "2Y": 732, "5Y": 1830}
    chart_data = history.copy()
    # Calculate moving averages using the full history
    chart_data["SMA50"] = chart_data["Close"].rolling(window=50).mean()
    chart_data["SMA200"] = chart_data["Close"].rolling(window=200).mean()

    if not chart_data.empty:
        cutoff = pd.Timestamp.now(tz=chart_data.index.tz) - pd.Timedelta(days=period_days.get(period, 366))
        chart_data = chart_data.loc[chart_data.index >= cutoff]
        fig = go.Figure()

        # Price
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["Close"],
                mode="lines",
                name=symbol,
                line=dict(width=2),
            )
        )

        # 50-day moving average
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["SMA50"],
                mode="lines",
                name="50 Day MA",
                line=dict(color="#f5a623", width=1.5),
            )
        )

        # 200-day moving average
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["SMA200"],
                mode="lines",
                name="200 Day MA",
                line=dict(color="#9b59b6", width=1.5),
            )
        )
        fig.update_layout(
            height=315,
            margin=dict(l=5, r=5, t=35, b=5),
            xaxis_title="",
            yaxis_title="Price",
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="left",
                x=0,
                itemclick="toggleothers",
                itemdoubleclick="toggle",
            ),
            hovermode="x unified",
        )
        fig.update_yaxes(tickprefix="$", tickformat=",.2f")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Price history is unavailable.")

st.markdown('<div class="section-label">TECHNICAL</div>', unsafe_allow_html=True)
sma50 = closes.tail(50).mean() if len(closes) >= 50 else np.nan
sma200 = closes.tail(200).mean() if len(closes) >= 200 else np.nan
rsi = calculate_rsi(closes)
volatility = closes.pct_change().dropna().tail(252).std() * np.sqrt(252) if len(closes) > 20 else np.nan

tech1, tech2 = st.columns(2)
with tech1:
    metric("SMA 50", fmt_number(sma50, "${:,.2f}"))
    metric("RSI 14", fmt_number(rsi, "{:.1f}"))
with tech2:
    metric("SMA 200", fmt_number(sma200, "${:,.2f}"))
    metric("Volatility", fmt_number(volatility, "{:.1%}"))

if quote_type != "ETF":
    st.markdown('<div class="section-label">FUNDAMENTALS</div>', unsafe_allow_html=True)
    f1, f2 = st.columns(2)
    with f1:
        metric("Profit Margin", fmt_number(info.get("profitMargins"), "{:.1%}"))
        metric("Revenue Growth", fmt_number(info.get("revenueGrowth"), "{:.1%}"))
    with f2:
        metric("Earnings Growth", fmt_number(info.get("earningsGrowth"), "{:.1%}"))
        metric("Debt / Equity", fmt_number(info.get("debtToEquity"), "{:.1f}"))

summary = info.get("longBusinessSummary")
if summary:
    st.markdown('<div class="section-label">ABOUT</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="description">{summary}</div>', unsafe_allow_html=True)

st.divider()
left, right = st.columns(2)

saved_symbols = load_watchlist()
st.session_state["mobile_watchlist"] = saved_symbols
is_watched = symbol in {str(s).upper() for s in saved_symbols}
with left:
    if is_watched:
        if st.button("✓ Watching", use_container_width=True, disabled=True):
            pass
    else:
        if st.button("⭐ Add to Watchlist", use_container_width=True):
            add_to_watchlist(symbol)
            st.session_state["mobile_watchlist"] = load_watchlist()
            st.rerun()

with right:
    if st.button("⚖️ Compare", use_container_width=True):
        st.session_state["mobile_selected_ticker"] = symbol
        st.session_state["mobile_search"] = symbol
        st.switch_page("pages/compare.py")

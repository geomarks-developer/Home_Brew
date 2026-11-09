"""MarketScope Mobile - shared session watchlist."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

DEFAULT_SYMBOLS = ("MSFT", "GOOG", "AAPL", "NVDA", "SCHD", "SPY")


def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan

def normalize_yield(value: object) -> float:
    value = number(value)

    if not np.isfinite(value) or value < 0:
        return np.nan

    # Yahoo may return 0.74 to represent 0.74%.
    # Convert percentage-point values to decimal form.
    if value > 0.20:
        value /= 100

    return value

def fmt(value: object, pattern: str) -> str:
    value = number(value)
    return pattern.format(value) if np.isfinite(value) else "N/A"


@st.cache_data(ttl=3600, show_spinner=False)
def load_watchlist_data(symbols: tuple[str, ...]) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows: list[dict[str, object]] = []
    histories: list[pd.DataFrame] = []

    for symbol in symbols:
        try:
            security = yf.Ticker(symbol)
            info = security.info or {}
            history = security.history(period="2y", auto_adjust=True)
            closes = pd.Series(dtype=float)
            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()

            price = float(closes.iloc[-1]) if not closes.empty else number(info.get("currentPrice"))
            ret_1m = closes.iloc[-1] / closes.iloc[-22] - 1 if len(closes) > 21 else np.nan
            ret_6m = closes.iloc[-1] / closes.iloc[-127] - 1 if len(closes) > 126 else np.nan
            ret_12m = closes.iloc[-1] / closes.iloc[-252] - 1 if len(closes) > 251 else np.nan
            volatility = float(closes.pct_change().dropna().std() * np.sqrt(252)) if len(closes) > 20 else np.nan

            quote_type = str(info.get("quoteType") or "Unknown")
            rows.append({
                "Symbol": symbol,
                "Name": info.get("shortName") or symbol,
                "Type": quote_type,
                "Price": price,
                "Dividend Yield": normalize_yield(info.get("dividendYield")),
                "Forward PE": number(info.get("forwardPE")),
                "1M Return": ret_1m,
                "6M Return": ret_6m,
                "12M Return": ret_12m,
                "Volatility": volatility,
            })

            if not closes.empty:
                indexed = closes / closes.iloc[0] * 100
                histories.append(pd.DataFrame({
                    "Date": indexed.index,
                    "Indexed Value": indexed.values,
                    "Symbol": symbol,
                }))
        except Exception:
            continue

    summary = pd.DataFrame(rows)
    performance = pd.concat(histories, ignore_index=True) if histories else pd.DataFrame()
    return summary, performance


def remove_symbol(symbol: str) -> None:
    current = st.session_state.setdefault("mobile_watchlist", [])
    st.session_state["mobile_watchlist"] = [s for s in current if str(s).upper() != symbol.upper()]


def watch_card(row: pd.Series) -> None:
    symbol = str(row["Symbol"])
    st.markdown(f"""
<div class="watch-card">
 <div class="watch-row">
  <div><div class="symbol">{symbol}</div><div class="name">{row.get('Name', symbol)}</div></div>
  <div class="price">{fmt(row.get('Price'), '${:,.2f}')}</div>
 </div>
 <div class="mini-row">
  <span>1M <b>{fmt(row.get('1M Return'), '{:.1%}')}</b></span>
  <span>6M <b>{fmt(row.get('6M Return'), '{:.1%}')}</b></span>
  <span>12M <b>{fmt(row.get('12M Return'), '{:.1%}')}</b></span>
  <span>Yield <b>{fmt(row.get('Dividend Yield'), '{:.2%}')}</b></span>
 </div>
</div>
""", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        if st.button("🔎 Details", key=f"watch_detail_{symbol}", use_container_width=True):
            st.session_state["mobile_selected_ticker"] = symbol
            st.session_state["mobile_search"] = symbol
            st.toast(f"{symbol} selected")
    with right:
        if st.button("🗑️ Remove", key=f"watch_remove_{symbol}", use_container_width=True):
            remove_symbol(symbol)
            st.rerun()


st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"] {display:none;}
.block-container {max-width:520px;padding:2.5rem 1rem 5rem 1rem;}
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.watch-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.9rem 1rem .8rem;background:rgba(128,128,128,.05);margin-top:.75rem;}
.watch-row {display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;}
.symbol {font-size:1.25rem;font-weight:800;}
.name {font-size:.82rem;color:#9aa3b2;margin-top:.12rem;}
.price {font-size:1.05rem;font-weight:800;}
.mini-row {display:grid;grid-template-columns:1fr 1fr;gap:.35rem .8rem;margin-top:.8rem;font-size:.82rem;color:#9aa3b2;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">⭐ Watchlist</div>', unsafe_allow_html=True)
st.markdown('<div class="module-subtitle">One shared mobile watchlist for stocks and ETFs across Growth, Value, Dividend, and ETF research.</div>', unsafe_allow_html=True)

home_col, compare_col = st.columns(2)
with home_col:
    st.page_link("mobile_home.py", label="Home", icon="🏠", width="stretch")
with compare_col:
    st.page_link("pages/compare.py", label="Compare", icon="⚖️", width="stretch")

watchlist = st.session_state.setdefault("mobile_watchlist", [])
watchlist = list(dict.fromkeys(str(symbol).upper() for symbol in watchlist))
st.session_state["mobile_watchlist"] = watchlist

new_symbol = st.text_input(
    "Add symbol",
    placeholder="Add ticker or ETF, e.g. MSFT or SPY",
    label_visibility="collapsed",
).strip().upper()

if new_symbol:
    if new_symbol not in watchlist:
        st.session_state["mobile_watchlist"].append(new_symbol)
        load_watchlist_data.clear()
        st.rerun()

button1, button2 = st.columns(2)
with button1:
    if st.button("Add starter list", use_container_width=True):
        st.session_state["mobile_watchlist"] = list(dict.fromkeys(watchlist + list(DEFAULT_SYMBOLS)))
        load_watchlist_data.clear()
        st.rerun()
with button2:
    if st.button("Clear all", use_container_width=True):
        st.session_state["mobile_watchlist"] = []
        st.rerun()

watchlist = st.session_state["mobile_watchlist"]
if not watchlist:
    st.info("Your mobile watchlist is empty. Add a ticker above or use the Watch buttons in the research modules.")
    st.stop()

refresh = st.button("🔄 Refresh watchlist", use_container_width=True)
if refresh:
    load_watchlist_data.clear()

with st.spinner("Loading watchlist..."):
    data, performance = load_watchlist_data(tuple(watchlist))

if data.empty:
    st.warning("Watchlist market data is currently unavailable.")
    st.stop()

st.markdown('<div class="section-label">WATCHLIST SNAPSHOT</div>', unsafe_allow_html=True)
a, b = st.columns(2)
a.metric("Symbols", len(data))
b.metric("Positive 12M", int((pd.to_numeric(data["12M Return"], errors="coerce") > 0).sum()))
c, d = st.columns(2)
c.metric("Median 12M", fmt(data["12M Return"].median(), "{:.1%}"))
d.metric("Median Yield", fmt(data["Dividend Yield"].median(), "{:.2%}"))

st.markdown('<div class="section-label">YOUR SYMBOLS</div>', unsafe_allow_html=True)
order = {symbol: index for index, symbol in enumerate(watchlist)}
data["_order"] = data["Symbol"].map(order)
data = data.sort_values("_order")
for _, row in data.iterrows():
    watch_card(row)

st.divider()
st.markdown('<div class="section-label">WATCHLIST PERFORMANCE</div>', unsafe_allow_html=True)
if not performance.empty:
    fig = px.line(performance, x="Date", y="Indexed Value", color="Symbol")
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.update_layout(
        height=360,
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis_title="",
        yaxis_title="Growth of $100",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=.5),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("The watchlist is stored in the current Streamlit session. Persistent storage can be added later.")

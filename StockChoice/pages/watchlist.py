"""stockchoice - persistent SQLite watchlist."""
from __future__ import annotations

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf
from app_utils import apply_card_density, cache_ttl, initialize_settings

from securities import format_security_option, get_security_options
from database import (
    add_many_to_watchlist,
    add_to_watchlist,
    clear_watchlist,
    init_database,
    load_watchlist,
    remove_from_watchlist,
)


initialize_settings()
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
    if value > 0.20:
        value /= 100
    return value

def linear(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan

    if high == low:
        return 50.0

    return float(
        np.clip(
            (value - low) / (high - low) * 100,
            0,
            100,
        )
    )


def inverse(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan

    return float(
        np.clip(
            (high - value) / (high - low) * 100,
            0,
            100,
        )
    )


def mean_available(values: list[float]) -> float:
    usable = [
        value
        for value in values
        if np.isfinite(value)
    ]

    return float(np.mean(usable)) if usable else np.nan


def watchlist_score(
    forward_pe: float,
    dividend_yield: float,
    ret_6m: float,
    ret_12m: float,
    volatility: float,
) -> float:
    """
    Compact stockchoice Watchlist score.

    Uses only metrics already collected by the Watchlist so
    displaying the score does not require another Yahoo request.
    """

    valuation = inverse(
        forward_pe,
        10,
        40,
    )

    momentum = mean_available(
        [
            linear(ret_6m, -0.20, 0.35),
            linear(ret_12m, -0.30, 0.50),
        ]
    )

    risk = inverse(
        volatility,
        0.10,
        0.45,
    )

    income = linear(
        dividend_yield,
        0.00,
        0.05,
    )

    components = [
        (valuation, 0.30),
        (momentum, 0.40),
        (risk, 0.20),
        (income, 0.10),
    ]

    usable = [
        (value, weight)
        for value, weight in components
        if np.isfinite(value)
    ]

    if not usable:
        return np.nan

    return (
        sum(value * weight for value, weight in usable)
        / sum(weight for _, weight in usable)
    )

def fmt(value: object, pattern: str) -> str:
    value = number(value)
    return pattern.format(value) if np.isfinite(value) else "N/A"


@st.cache_data(ttl=cache_ttl(), show_spinner=False)
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

            dividend_yield = normalize_yield(
                info.get("dividendYield")
            )

            forward_pe = number(
                info.get("forwardPE")
            )

            score = watchlist_score(
                forward_pe=forward_pe,
                dividend_yield=dividend_yield,
                ret_6m=ret_6m,
                ret_12m=ret_12m,
                volatility=volatility,
            )

            rows.append({
                "Symbol": symbol,
                "Name": info.get("shortName") or symbol,
                "Type": quote_type,
                "Price": price,
                "Score": score,
                "Dividend Yield": dividend_yield,
                "Forward PE": forward_pe,
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


def sync_watchlist_from_database() -> list[str]:
    symbols = load_watchlist()
    st.session_state["mobile_watchlist"] = symbols
    return symbols


def remove_symbol(symbol: str) -> None:
    remove_from_watchlist(symbol)
    sync_watchlist_from_database()


def watch_card(row: pd.Series) -> None:
    symbol = str(row["Symbol"])
    score = number(row.get("Score"))

    st.markdown(
        f"""
<div class="watch-card">
 <div class="watch-row">
  <div>
   <div class="symbol">{symbol}</div>
   <div class="name">{row.get('Name', symbol)}</div>
  </div>
  <div class="score">{fmt(score, '{:.0f}')}</div>
 </div>

 <div class="mini-row">
  <span>Price <b>{fmt(row.get('Price'), '${:,.2f}')}</b></span>
  <span>1M <b>{fmt(row.get('1M Return'), '{:.1%}')}</b></span>
  <span>6M <b>{fmt(row.get('6M Return'), '{:.1%}')}</b></span>
  <span>12M <b>{fmt(row.get('12M Return'), '{:.1%}')}</b></span>
  <span>Yield <b>{fmt(row.get('Dividend Yield'), '{:.2%}')}</b></span>
  <span>P/E <b>{fmt(row.get('Forward PE'), '{:.1f}')}</b></span>
 </div>
</div>
""",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        if st.button(
            "🔎 Details",
            key=f"watch_detail_{symbol}",
            use_container_width=True,
        ):
            st.session_state["mobile_selected_ticker"] = symbol
            st.session_state["mobile_search"] = symbol
            st.switch_page("pages/details.py")

    with right:
        if st.button(
            "🗑️ Remove",
            key=f"watch_remove_{symbol}",
            use_container_width=True,
        ):
            remove_symbol(symbol)
            load_watchlist_data.clear()
            st.rerun()


apply_card_density()
st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {display:none !important; visibility:hidden !important;}
.block-container {max-width:520px;padding:2.5rem 1rem 5rem 1rem;}
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.watch-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.9rem 1rem .8rem;background:rgba(128,128,128,.05);margin-top:.75rem;}
.watch-row {display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;}
.symbol {font-size:1.25rem;font-weight:800;}
.name {font-size:.82rem;color:#9aa3b2;margin-top:.12rem;}
.score {
    min-width:46px;
    text-align:center;
    border-radius:12px;
    padding:.35rem .45rem;
    background:#1877f2;
    color:white;
    font-weight:800;
    font-size:1.05rem;
}
.mini-row {display:grid;grid-template-columns:1fr 1fr;gap:.35rem .8rem;margin-top:.8rem;font-size:.82rem;color:#9aa3b2;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">⭐ Watchlist</div>', unsafe_allow_html=True)
st.markdown('<div class="module-subtitle">One shared mobile watchlist for stocks and ETFs across Growth, Value, Dividend, and ETF research.</div>', unsafe_allow_html=True)

home_col, compare_col = st.columns(2)
with home_col:
    st.page_link("app.py", label="Home", icon="🏠", width="stretch")
with compare_col:
    st.page_link("pages/compare.py", label="Compare", icon="⚖️", width="stretch")

init_database()
if not st.session_state.get("mobile_watchlist_db_loaded", False):
    sync_watchlist_from_database()
    st.session_state["mobile_watchlist_db_loaded"] = True

watchlist = st.session_state.setdefault("mobile_watchlist", [])
watchlist = list(dict.fromkeys(str(symbol).strip().upper() for symbol in watchlist if str(symbol).strip()))
st.session_state["mobile_watchlist"] = watchlist

available_symbols = get_security_options(exclude=watchlist)
selected_symbol = st.selectbox(
    "Add from securities",
    options=[""] + available_symbols,
    format_func=lambda symbol: "Select a stock or ETF..." if not symbol else format_security_option(symbol),
    label_visibility="collapsed",
)
if selected_symbol and add_to_watchlist(selected_symbol):
    sync_watchlist_from_database()
    load_watchlist_data.clear()
    st.rerun()
button1, button2 = st.columns(2)
with button1:
    if st.button("Add starter list", use_container_width=True):
        add_many_to_watchlist(DEFAULT_SYMBOLS)
        sync_watchlist_from_database()
        load_watchlist_data.clear()
        st.rerun()
with button2:
    if st.button("Clear all", use_container_width=True):
        clear_watchlist()
        sync_watchlist_from_database()
        load_watchlist_data.clear()
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

data = data.sort_values(
    by="Score",
    ascending=False,
    na_position="last",
).reset_index(drop=True)

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
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=.5,itemclick="toggleothers",itemdoubleclick="toggle",),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Watchlist changes are saved automatically to the local Stockchoice SQLite database.")

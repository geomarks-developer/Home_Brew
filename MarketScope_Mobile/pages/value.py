"""MarketScope Mobile - Value module."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

VALUE_TICKERS = (
    "AFL", "BLK", "BRK-B", "C", "CMCSA", "COP", "CVS", "CVX", "DHR", "EMR",
    "GM", "GOOG", "GS", "JPM", "MDT", "MET", "NEM", "PFE", "TROW", "TXN",
)


def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def linear(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan
    return float(np.clip((value - low) / (high - low) * 100, 0, 100))


def inverse(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan
    return float(np.clip((high - value) / (high - low) * 100, 0, 100))


def mean_available(values: list[float]) -> float:
    usable = [v for v in values if np.isfinite(v)]
    return float(np.mean(usable)) if usable else np.nan


def value_scores(info: dict, history: pd.DataFrame) -> dict[str, float]:
    market_cap = number(info.get("marketCap"))
    fcf = number(info.get("freeCashflow"))
    forward_pe = number(info.get("forwardPE"))
    price_book = number(info.get("priceToBook"))
    ev_ebitda = number(info.get("enterpriseToEbitda"))
    roe = number(info.get("returnOnEquity"))
    margin = number(info.get("operatingMargins"))
    debt_equity = number(info.get("debtToEquity"))
    revenue_growth = number(info.get("revenueGrowth"))
    earnings_growth = number(info.get("earningsGrowth"))

    fcf_yield = fcf / market_cap if np.isfinite(fcf) and np.isfinite(market_cap) and market_cap > 0 else np.nan

    closes = pd.Series(dtype=float)
    if history is not None and not history.empty and "Close" in history.columns:
        closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
    ret12 = closes.iloc[-1] / closes.iloc[-252] - 1 if len(closes) > 251 else np.nan
    above200 = closes.iloc[-1] / closes.tail(200).mean() - 1 if len(closes) >= 200 else np.nan

    valuation = mean_available([
        inverse(forward_pe, 8, 30),
        inverse(price_book, 1, 6),
        inverse(ev_ebitda, 5, 20),
        linear(fcf_yield, 0.00, 0.10),
    ])
    quality = mean_available([
        linear(roe, 0.00, 0.30),
        linear(margin, 0.00, 0.25),
        100.0 if np.isfinite(fcf) and fcf > 0 else 0.0 if np.isfinite(fcf) else np.nan,
    ])
    strength = inverse(debt_equity, 25, 250) if np.isfinite(debt_equity) else np.nan
    momentum = mean_available([
        linear(ret12, -0.30, 0.35),
        linear(above200, -0.20, 0.20),
    ])

    deterioration = mean_available([
        inverse(revenue_growth, -0.20, 0.20),
        inverse(earnings_growth, -0.30, 0.30),
    ])
    trap = mean_available([
        deterioration,
        100.0 if np.isfinite(fcf) and fcf < 0 else 0.0 if np.isfinite(fcf) else np.nan,
        inverse(quality, 35, 75) if np.isfinite(quality) else np.nan,
        inverse(momentum, 30, 70) if np.isfinite(momentum) else np.nan,
    ])

    components = [(valuation, .45), (quality, .25), (strength, .15), (momentum, .15)]
    usable = [(v, w) for v, w in components if np.isfinite(v)]
    overall = sum(v*w for v, w in usable) / sum(w for _, w in usable) if usable else np.nan

    return {
        "FCF Yield": fcf_yield,
        "Revenue Growth": revenue_growth,
        "Earnings Growth": earnings_growth,
        "12M Return": ret12,
        "Valuation Score": valuation,
        "Quality Score": quality,
        "Financial Strength Score": strength,
        "Momentum Score": momentum,
        "Overall Score": overall,
        "Value Trap Risk": trap,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_value_data(tickers: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        try:
            security = yf.Ticker(ticker)
            info = security.info or {}
            history = security.history(period="1y", auto_adjust=True)
            scores = value_scores(info, history)
            price = np.nan
            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
                if not closes.empty:
                    price = float(closes.iloc[-1])
            rows.append({
                "Ticker": ticker,
                "Company": info.get("shortName") or ticker,
                "Sector": info.get("sector") or "Unknown",
                "Price": price,
                "Market Cap": number(info.get("marketCap")),
                "Forward PE": number(info.get("forwardPE")),
                **scores,
            })
        except Exception:
            continue
    data = pd.DataFrame(rows)
    if not data.empty:
        data = data.sort_values("Overall Score", ascending=False, na_position="last")
    return data.reset_index(drop=True)


def add_watchlist(ticker: str) -> None:
    watchlist = st.session_state.setdefault("mobile_watchlist", [])
    if ticker not in watchlist:
        watchlist.append(ticker)


def fmt(value: float, pattern: str) -> str:
    return pattern.format(value) if np.isfinite(value) else "N/A"


def stock_card(row: pd.Series) -> None:
    ticker = str(row["Ticker"])
    score = number(row.get("Overall Score"))
    trap = number(row.get("Value Trap Risk"))
    st.markdown(
        f"""
<div class="stock-card">
 <div class="stock-row">
  <div><div class="ticker">{ticker}</div><div class="company">{row.get('Company', ticker)}</div></div>
  <div class="score">{fmt(score, '{:.0f}')}</div>
 </div>
 <div class="mini-row">
  <span>Price <b>{fmt(number(row.get('Price')), '${:,.2f}')}</b></span>
  <span>Valuation <b>{fmt(number(row.get('Valuation Score')), '{:.0f}')}</b></span>
  <span>FCF Yield <b>{fmt(number(row.get('FCF Yield')), '{:.1%}')}</b></span>
  <span>Trap Risk <b>{fmt(trap, '{:.0f}')}</b></span>
 </div>
</div>
""",
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("⭐ Watch", key=f"value_watch_{ticker}", use_container_width=True):
            add_watchlist(ticker)
            st.toast(f"{ticker} added to Watchlist")
    with c2:
        if st.button("🔎 Details", key=f"value_detail_{ticker}", use_container_width=True):
            st.session_state["mobile_selected_ticker"] = ticker
            st.session_state["mobile_search"] = ticker
            st.toast(f"{ticker} selected for Stock Detail")


st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"] {display:none;}
<<<<<<< HEAD
.block-container {max-width:520px; padding:1rem 1rem 5rem 1rem;}
=======
.block-container {max-width:520px; padding:3rem 1rem 5rem 1rem;}
>>>>>>> 697fedb (Heading spacing)
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.stock-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.9rem 1rem .8rem;background:rgba(128,128,128,.05);margin-top:.75rem;}
.stock-row {display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;}
.ticker {font-size:1.25rem;font-weight:800;}
.company {font-size:.82rem;color:#9aa3b2;margin-top:.12rem;}
.score {min-width:46px;text-align:center;border-radius:12px;padding:.35rem .45rem;background:#7c3aed;color:white;font-weight:800;font-size:1.05rem;}
.mini-row {display:grid;grid-template-columns:1fr 1fr;gap:.35rem .8rem;margin-top:.8rem;font-size:.82rem;color:#9aa3b2;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">💎 Value</div>', unsafe_allow_html=True)
st.markdown('<div class="module-subtitle">Valuation, business quality, financial strength, momentum, and value-trap awareness for quick mobile research.</div>', unsafe_allow_html=True)

home_col, refresh_col = st.columns(2)
with home_col:
    st.page_link("mobile_home.py", label="Home", icon="🏠", width="stretch")
with refresh_col:
    refresh = st.button("🔄 Refresh", use_container_width=True)
if refresh:
    load_value_data.clear()

with st.spinner("Loading Value research..."):
    data = load_value_data(VALUE_TICKERS)
if data.empty:
    st.warning("Value data is currently unavailable.")
    st.stop()

search = st.text_input(
    "Search Value",
    value=st.session_state.get("mobile_search", ""),
    placeholder="Ticker or company...",
    label_visibility="collapsed",
).strip()
sector_options = ["All"] + sorted(data["Sector"].dropna().astype(str).unique().tolist())
sector = st.selectbox("Sector", sector_options, label_visibility="collapsed")

filtered = data.copy()
if search:
    mask = filtered["Ticker"].astype(str).str.contains(search, case=False, regex=False) | filtered["Company"].astype(str).str.contains(search, case=False, regex=False)
    filtered = filtered[mask]
if sector != "All":
    filtered = filtered[filtered["Sector"] == sector]

st.markdown('<div class="section-label">VALUE SNAPSHOT</div>', unsafe_allow_html=True)
a, b = st.columns(2)
a.metric("Stocks", len(filtered))
b.metric("Median Valuation", fmt(number(filtered["Valuation Score"].median()) if not filtered.empty else np.nan, "{:.0f}"))
c, d = st.columns(2)
c.metric("Median FCF Yield", fmt(number(filtered["FCF Yield"].median()) if not filtered.empty else np.nan, "{:.1%}"))
d.metric("Median Trap Risk", fmt(number(filtered["Value Trap Risk"].median()) if not filtered.empty else np.nan, "{:.0f}"))

if filtered.empty:
    st.info("No Value stocks match the current search and sector filter.")
    st.stop()

st.markdown('<div class="section-label">TOP VALUE CANDIDATES</div>', unsafe_allow_html=True)
show_count = st.select_slider("Show", options=[5, 10, 15, 20], value=10, label_visibility="collapsed")
leaders = filtered.sort_values(["Overall Score", "Value Trap Risk"], ascending=[False, True]).head(show_count)
for _, row in leaders.iterrows():
    stock_card(row)

st.divider()
st.markdown('<div class="section-label">VALUATION VS TRAP RISK</div>', unsafe_allow_html=True)
chart = filtered.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()
if not chart.empty:
    chart["Bubble Size"] = pd.to_numeric(chart["Market Cap"], errors="coerce").clip(lower=1)
    fig = px.scatter(
        chart,
        x="Valuation Score",
        y="Value Trap Risk",
        size="Bubble Size",
        size_max=25,
        color="Sector",
        hover_name="Ticker",
        hover_data={
            "Company": True,
            "Overall Score": ":.1f",
            "Quality Score": ":.1f",
            "Forward PE": ":.1f",
            "FCF Yield": ":.1%",
            "12M Return": ":.1%",
            "Bubble Size": False,
        },
    )
    fig.add_vline(x=65, line_dash="dot", line_color="gray")
    fig.add_hline(y=50, line_dash="dot", line_color="gray")
    fig.update_xaxes(range=[0, 100], title="Valuation →")
    fig.update_yaxes(range=[100, 0], title="Trap Risk ↓")
    fig.update_layout(height=390, margin=dict(l=5, r=5, t=10, b=5), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.caption("Mobile Value scores are compact research signals, not investment recommendations.")

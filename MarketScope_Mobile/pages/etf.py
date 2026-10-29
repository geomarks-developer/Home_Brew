"""MarketScope Mobile - ETF module."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

ETF_UNIVERSE = {
    "Broad Market": ("SPY", "IVV", "VOO", "VTI", "DIA", "QQQ"),
    "Growth": ("VUG", "IWF", "SCHG", "QQQM"),
    "Value": ("VTV", "IWD", "SCHV"),
    "Dividend": ("SCHD", "VIG", "VYM", "DGRO"),
    "International": ("VXUS", "VEA", "VWO", "IXUS"),
    "Bonds": ("BND", "AGG", "TLT", "IEF", "VCSH"),
    "Sectors": ("XLK", "XLF", "XLV", "XLI", "XLE", "XLP", "XLY", "XLU", "XLB", "XLRE", "XLC"),
}


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

    # Handle sources returning percentage points instead of decimals.
    if value > 1:
        value /= 100

    return value

def calculate_trailing_yield(
    security: yf.Ticker,
    price: float,
) -> float:
    if not np.isfinite(price) or price <= 0:
        return np.nan

    try:
        dividends = security.dividends

        if dividends is None or dividends.empty:
            return np.nan

        dividends = pd.to_numeric(
            dividends,
            errors="coerce",
        ).dropna()

        if dividends.empty:
            return np.nan

        cutoff = dividends.index.max() - pd.Timedelta(days=365)
        annual_dividends = dividends[
            dividends.index > cutoff
        ].sum()

        if annual_dividends <= 0:
            return np.nan

        return float(annual_dividends / price)

    except Exception:
        return np.nan
    
def linear(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan
    return float(np.clip((value-low)/(high-low)*100, 0, 100))


def inverse(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan
    return float(np.clip((high-value)/(high-low)*100, 0, 100))


def mean_available(values: list[float]) -> float:
    usable = [v for v in values if np.isfinite(v)]
    return float(np.mean(usable)) if usable else np.nan


def all_tickers() -> tuple[str, ...]:
    return tuple(dict.fromkeys(t for group in ETF_UNIVERSE.values() for t in group))


def category_for(ticker: str) -> str:
    for category, tickers in ETF_UNIVERSE.items():
        if ticker in tickers:
            return category
    return "Other"


def expense_ratio_from_funds_data(security: yf.Ticker) -> float:
    try:
        operations = security.funds_data.fund_operations
        if operations is None or operations.empty:
            return np.nan
        # yfinance currently exposes Annual Report Expense Ratio in fund_operations.
        for label in operations.index:
            if "expense ratio" in str(label).lower():
                row = operations.loc[label]
                if isinstance(row, pd.Series):
                    for value in row.tolist():
                        numeric = number(value)
                        if np.isfinite(numeric):
                            return numeric
                return number(row)
    except Exception:
        pass
    return np.nan


def etf_metrics(
    security: yf.Ticker,
    info: dict,
    history: pd.DataFrame,
    expense_ratio: float,
    price: float,
) -> dict[str, float]:
    
    closes = pd.Series(dtype=float)
    if history is not None and not history.empty and "Close" in history.columns:
        closes = pd.to_numeric(history["Close"], errors="coerce").dropna()

    ret_3m = closes.iloc[-1]/closes.iloc[-64]-1 if len(closes) > 63 else np.nan
    ret_6m = closes.iloc[-1]/closes.iloc[-127]-1 if len(closes) > 126 else np.nan
    ret_12m = closes.iloc[-1]/closes.iloc[-252]-1 if len(closes) > 251 else np.nan
    above_200 = closes.iloc[-1]/closes.tail(200).mean()-1 if len(closes) >= 200 else np.nan

    daily = closes.pct_change().dropna()
    volatility = float(daily.std()*np.sqrt(252)) if len(daily) > 20 else np.nan
    dividend_yield = calculate_trailing_yield(security,price,)

    performance = mean_available([
        linear(ret_3m, -0.12, 0.18),
        linear(ret_6m, -0.18, 0.30),
        linear(ret_12m, -0.25, 0.45),
    ])
    momentum = linear(above_200, -0.18, 0.18)
    risk = inverse(volatility, 0.10, 0.40)
    cost = inverse(expense_ratio, 0.0002, 0.0075)
    income = linear(dividend_yield, 0.00, 0.045)

    parts = [(performance,.40),(momentum,.20),(risk,.15),(cost,.15),(income,.10)]
    usable = [(v,w) for v,w in parts if np.isfinite(v)]
    overall = sum(v*w for v,w in usable)/sum(w for _,w in usable) if usable else np.nan

    return {
        "3M Return": ret_3m,
        "6M Return": ret_6m,
        "12M Return": ret_12m,
        "Volatility": volatility,
        "Dividend Yield": dividend_yield,
        "Expense Ratio": expense_ratio,
        "Performance Score": performance,
        "Momentum Score": momentum,
        "Risk Score": risk,
        "Cost Score": cost,
        "Income Score": income,
        "Overall Score": overall,
    }


@st.cache_data(ttl=3600, show_spinner=False)
def load_etf_data(tickers: tuple[str, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker in tickers:
        try:
            security = yf.Ticker(ticker)
            info = security.info or {}
            history = security.history(period="1y", auto_adjust=True)

            price = np.nan

            if (
                history is not None
                and not history.empty
                and "Close" in history.columns
            ):
                closes = pd.to_numeric(
                    history["Close"],
                    errors="coerce",
                ).dropna()

                if not closes.empty:
                    price = float(closes.iloc[-1])

            expense = expense_ratio_from_funds_data(security)

            metrics = etf_metrics(
                security,
                info,
                history,
                expense,
                price,
            )

            rows.append({
                "Ticker": ticker,
                "Fund": info.get("shortName") or ticker,
                "Category": category_for(ticker),
                "Price": price,
                "Net Assets": number(info.get("totalAssets")),
                **metrics,
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


def etf_card(row: pd.Series) -> None:
    ticker = str(row["Ticker"])
    score = number(row.get("Overall Score"))
    st.markdown(f"""
<div class="fund-card">
 <div class="fund-row">
  <div><div class="ticker">{ticker}</div><div class="fund">{row.get('Fund', ticker)}</div></div>
  <div class="score">{fmt(score, '{:.0f}')}</div>
 </div>
 <div class="mini-row">
  <span>Price <b>{fmt(number(row.get('Price')), '${:,.2f}')}</b></span>
  <span>12M <b>{fmt(number(row.get('12M Return')), '{:.1%}')}</b></span>
  <span>Expense <b>{fmt(number(row.get('Expense Ratio')), '{:.2%}')}</b></span>
  <span>Yield <b>{fmt(number(row.get('Dividend Yield')), '{:.2%}')}</b></span>
 </div>
</div>""", unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        if st.button("⭐ Watch", key=f"etf_watch_{ticker}", use_container_width=True):
            add_watchlist(ticker)
            st.toast(f"{ticker} added to Watchlist")
    with right:
        if st.button("🔎 Details", key=f"etf_detail_{ticker}", use_container_width=True):
            st.session_state["mobile_selected_ticker"] = ticker
            st.session_state["mobile_search"] = ticker
            st.toast(f"{ticker} selected for Fund Detail")


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
.fund-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.9rem 1rem .8rem;background:rgba(128,128,128,.05);margin-top:.75rem;}
.fund-row {display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;}
.ticker {font-size:1.25rem;font-weight:800;}
.fund {font-size:.82rem;color:#9aa3b2;margin-top:.12rem;}
.score {min-width:46px;text-align:center;border-radius:12px;padding:.35rem .45rem;background:#0891b2;color:white;font-weight:800;font-size:1.05rem;}
.mini-row {display:grid;grid-template-columns:1fr 1fr;gap:.35rem .8rem;margin-top:.8rem;font-size:.82rem;color:#9aa3b2;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">🌐 ETF</div>', unsafe_allow_html=True)
st.markdown('<div class="module-subtitle">ETF performance, cost, risk, income, and category context in a mobile-first research view.</div>', unsafe_allow_html=True)

home_col, refresh_col = st.columns(2)
with home_col:
    st.page_link("mobile_home.py", label="Home", icon="🏠", width="stretch")
with refresh_col:
    refresh = st.button("🔄 Refresh", use_container_width=True)
if refresh:
    load_etf_data.clear()

with st.spinner("Loading ETF research..."):
    data = load_etf_data(all_tickers())
if data.empty:
    st.warning("ETF data is currently unavailable.")
    st.stop()

search = st.text_input(
    "Search ETF",
    value=st.session_state.get("mobile_search", ""),
    placeholder="ETF ticker or fund name...",
    label_visibility="collapsed",
).strip()
category_options = ["All"] + list(ETF_UNIVERSE.keys())
category = st.selectbox("Category", category_options, label_visibility="collapsed")

filtered = data.copy()
if search:
    mask = filtered["Ticker"].astype(str).str.contains(search, case=False, regex=False) | filtered["Fund"].astype(str).str.contains(search, case=False, regex=False)
    filtered = filtered[mask]
if category != "All":
    filtered = filtered[filtered["Category"] == category]

st.markdown('<div class="section-label">ETF SNAPSHOT</div>', unsafe_allow_html=True)
a, b = st.columns(2)
a.metric("ETFs", len(filtered))
b.metric("Median 12M", fmt(number(filtered["12M Return"].median()) if not filtered.empty else np.nan, "{:.1%}"))
c, d = st.columns(2)
c.metric("Median Expense", fmt(number(filtered["Expense Ratio"].median()) if not filtered.empty else np.nan, "{:.2%}"))
d.metric("Median Yield", fmt(number(filtered["Dividend Yield"].median()) if not filtered.empty else np.nan, "{:.2%}"))

if filtered.empty:
    st.info("No ETFs match the current search and category filter.")
    st.stop()

st.markdown('<div class="section-label">TOP ETF CANDIDATES</div>', unsafe_allow_html=True)
show_count = st.select_slider("Show", options=[5,10,15,20], value=10, label_visibility="collapsed")
leaders = filtered.sort_values("Overall Score", ascending=False, na_position="last").head(show_count)
for _, row in leaders.iterrows():
    etf_card(row)

st.divider()
st.markdown('<div class="section-label">RETURN VS RISK</div>', unsafe_allow_html=True)
chart = filtered.dropna(subset=["12M Return", "Volatility"]).copy()
if not chart.empty:
    chart["Bubble Size"] = pd.to_numeric(chart["Net Assets"], errors="coerce").clip(lower=1)
    fig = px.scatter(
        chart,
        x="Volatility",
        y="12M Return",
        size="Bubble Size",
        size_max=25,
        color="Category",
        hover_name="Ticker",
        hover_data={
            "Fund": True,
            "Overall Score": ":.1f",
            "Expense Ratio": ":.2%",
            "Dividend Yield": ":.2%",
            "Bubble Size": False,
        },
    )
    fig.update_xaxes(tickformat=".0%", title="Volatility")
    fig.update_yaxes(tickformat=".0%", title="12M Return")
    fig.update_layout(height=390, margin=dict(l=5,r=5,t=10,b=5), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

st.caption("Mobile ETF scores are compact research signals, not investment recommendations.")

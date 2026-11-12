"""stockchoice - Dividend module."""
from __future__ import annotations

FALLBACK_VERSION = "2026-10-31-v4"

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
from database import add_to_watchlist, load_watchlist
from securities import format_security_option

initialize_settings()
DIVIDEND_TICKERS = (
    "ABBV", "AFL", "ADP", "APD", "CINF", "CL", "CVX", "ED", "EMR", "GD",
    "IBM", "JNJ", "KO", "LOW", "MCD", "MDT", "NEE", "PEP", "PG", "TROW",
)


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

    # Some Yahoo Finance responses provide dividend yield as
    # percentage points, such as 0.74 meaning 0.74%.
    # Convert those values to decimal form for {:.2%} formatting.
    if value > 0.20:
        value /= 100

    return value


def trailing_dividend_yield(security: yf.Ticker, price: float) -> float:
    """Fallback when Yahoo info omits dividendYield."""
    if not np.isfinite(price) or price <= 0:
        return np.nan
    try:
        dividends = pd.to_numeric(security.dividends, errors="coerce").dropna()
        if dividends.empty:
            return np.nan
        cutoff = dividends.index.max() - pd.Timedelta(days=365)
        trailing = float(dividends[dividends.index > cutoff].sum())
        return trailing / price if trailing > 0 else np.nan
    except Exception as exc:
        print(f"Dividend yield fallback error for {security.ticker}: {type(exc).__name__}: {exc}")
        return np.nan

def payout_ratio_fallback(
    security: yf.Ticker,
    history: pd.DataFrame,
) -> float:
    """Calculate payout ratio from trailing dividends and EPS."""
    try:
        if history is None or history.empty or "Dividends" not in history.columns:
            return np.nan

        dividends = pd.to_numeric(
            history["Dividends"],
            errors="coerce",
        ).dropna()

        if dividends.empty:
            return np.nan

        # Sum dividends paid during the most recent 365 days.
        cutoff = dividends.index.max() - pd.Timedelta(days=365)
        annual_dividend = float(
            dividends[dividends.index > cutoff].sum()
        )

        if annual_dividend <= 0:
            return np.nan

        # Prefer annual EPS so dividend and earnings periods are comparable.
        statement = security.income_stmt

        if statement is None or statement.empty:
            return np.nan

        for row_name in ("Diluted EPS", "Basic EPS"):
            if row_name not in statement.index:
                continue

            eps_values = pd.to_numeric(
                statement.loc[row_name],
                errors="coerce",
            ).dropna()

            if eps_values.empty:
                continue

            eps = number(eps_values.iloc[0])

            if np.isfinite(eps) and eps > 0:
                return float(annual_dividend / eps)

        return np.nan

    except Exception as exc:
        print(
            f"Dividend payout fallback error for "
            f"{security.ticker}: "
            f"{type(exc).__name__}: {exc}"
        )
        return np.nan

def statement_growth_fallback(security: yf.Ticker) -> float:
    """Fallback when Yahoo info omits earningsGrowth."""
    for statement_name in ("quarterly_income_stmt", "income_stmt"):
        try:
            statement = getattr(security, statement_name)
            if statement is None or statement.empty:
                continue
            for row_name in ("Net Income", "Net Income Common Stockholders", "Diluted EPS", "Basic EPS"):
                if row_name not in statement.index:
                    continue
                values = pd.to_numeric(statement.loc[row_name], errors="coerce").dropna()
                if len(values) >= 2:
                    newest = number(values.iloc[0]); previous = number(values.iloc[1])
                    if np.isfinite(newest) and np.isfinite(previous) and previous > 0:
                        return float(newest / previous - 1)
        except Exception as exc:
            print(f"Dividend growth fallback error for {security.ticker}: {type(exc).__name__}: {exc}")
    return np.nan


def linear(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan
    return float(np.clip((value - low) / (high - low) * 100, 0, 100))


def inverse(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan
    return float(np.clip((high - value) / (high - low) * 100, 0, 100))


def mean_available(values: list[float]) -> float:
    usable = [value for value in values if np.isfinite(value)]
    return float(np.mean(usable)) if usable else np.nan


def dividend_scores(security: yf.Ticker, info: dict, history: pd.DataFrame, price: float) -> dict[str, float]:
    dividend_yield = normalize_yield(info.get("dividendYield"))
    if not np.isfinite(dividend_yield):
        dividend_yield = trailing_dividend_yield(security, price)
    payout_ratio = number(info.get("payoutRatio"))
    if not np.isfinite(payout_ratio):
        payout_ratio = payout_ratio_fallback(
            security,
            history,
        )
    five_year_yield = number(info.get("fiveYearAvgDividendYield"))
    roe = number(info.get("returnOnEquity"))
    margin = number(info.get("operatingMargins"))
    debt_equity = number(info.get("debtToEquity"))
    fcf = number(info.get("freeCashflow"))
    earnings_growth = number(info.get("earningsGrowth"))
    if not np.isfinite(earnings_growth):
        earnings_growth = statement_growth_fallback(security)

    closes = pd.Series(dtype=float)
    if history is not None and not history.empty and "Close" in history.columns:
        closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
    ret12 = closes.iloc[-1] / closes.iloc[-252] - 1 if len(closes) > 251 else np.nan

    income = linear(dividend_yield, 0.01, 0.06)
    sustainability = mean_available([
        inverse(payout_ratio, 0.35, 0.90),
        100.0 if np.isfinite(fcf) and fcf > 0 else 0.0 if np.isfinite(fcf) else np.nan,
        linear(earnings_growth, -0.10, 0.15),
    ])
    quality = mean_available([
        linear(roe, 0.05, 0.30),
        linear(margin, 0.05, 0.25),
    ])
    balance_sheet = inverse(debt_equity, 25, 250) if np.isfinite(debt_equity) else np.nan
    momentum = linear(ret12, -0.25, 0.35)

    weights = [
        (income, .30),
        (sustainability, .30),
        (quality, .20),
        (balance_sheet, .10),
        (momentum, .10),
    ]
    usable = [(value, weight) for value, weight in weights if np.isfinite(value)]
    overall = sum(value * weight for value, weight in usable) / sum(weight for _, weight in usable) if usable else np.nan

    return {
        "Dividend Yield": dividend_yield,
        "5Y Avg Yield": five_year_yield / 100 if np.isfinite(five_year_yield) and five_year_yield > 1 else five_year_yield,
        "Payout Ratio": payout_ratio,
        "Earnings Growth": earnings_growth,
        "12M Return": ret12,
        "Income Score": income,
        "Sustainability Score": sustainability,
        "Quality Score": quality,
        "Balance Sheet Score": balance_sheet,
        "Momentum Score": momentum,
        "Overall Score": overall,
    }


@st.cache_data(ttl=cache_ttl(), show_spinner=False)
def load_dividend_data(tickers: tuple[str, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for ticker in tickers:
        try:
            security = yf.Ticker(ticker)

            try:
                info = security.info or {}
            except Exception as exc:
                print(
                    f"Dividend info unavailable for {ticker}: "
                    f"{type(exc).__name__}: {exc}"
                )
                info = {}

            history = security.history(
                period="2y",
                auto_adjust=True,
                actions=True,
            )

            price = np.nan
            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
                if not closes.empty:
                    price = float(closes.iloc[-1])

            scores = dividend_scores(security, info, history, price)

            rows.append({
                "Ticker": ticker,
                "Company": info.get("shortName") or ticker,
                "Sector": info.get("sector") or "Unknown",
                "Price": price,
                "Market Cap": number(info.get("marketCap")),
                "Forward PE": number(info.get("forwardPE")),
                **scores,
            })
        except Exception as exc:
            print(f"Dividend data error for {ticker}: {type(exc).__name__}: {exc}")
            continue

    data = pd.DataFrame(rows)
    if not data.empty:
        data = data.sort_values("Overall Score", ascending=False, na_position="last")
    return data.reset_index(drop=True)


def add_watchlist(ticker: str) -> bool:
    added = add_to_watchlist(ticker)
    st.session_state["mobile_watchlist"] = load_watchlist()
    return added
def fmt(value: float, pattern: str) -> str:
    return pattern.format(value) if np.isfinite(value) else "N/A"


def stock_card(row: pd.Series) -> None:
    ticker = str(row["Ticker"])
    score = number(row.get("Overall Score"))
    st.markdown(
        f"""
<div class="stock-card">
 <div class="stock-row">
  <div><div class="ticker">{ticker}</div><div class="company">{row.get('Company', ticker)}</div></div>
  <div class="score">{fmt(score, '{:.0f}')}</div>
 </div>
 <div class="mini-row">
  <span>Price <b>{fmt(number(row.get('Price')), '${:,.2f}')}</b></span>
  <span>Yield <b>{fmt(number(row.get('Dividend Yield')), '{:.2%}')}</b></span>
  <span>Payout <b>{fmt(number(row.get('Payout Ratio')), '{:.0%}')}</b></span>
  <span>Safety <b>{fmt(number(row.get('Sustainability Score')), '{:.0f}')}</b></span>
 </div>
</div>
""",
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)
    with left:
        if st.button("⭐ Watch", key=f"div_watch_{ticker}", use_container_width=True):
            add_watchlist(ticker)
            st.toast(f"{ticker} added to Watchlist")
    with right:
        if st.button("🔎 Details", key=f"div_detail_{ticker}", use_container_width=True):
            st.session_state["mobile_selected_ticker"] = ticker
            st.session_state["mobile_search"] = ticker
            st.switch_page("pages/details.py")


apply_card_density()
st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {display:none !important; visibility:hidden !important;}
.block-container {max-width:520px;padding:2rem 1rem 5rem 1rem;}
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.stock-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.9rem 1rem .8rem;background:rgba(128,128,128,.05);margin-top:.75rem;}
.stock-row {display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;}
.ticker {font-size:1.25rem;font-weight:800;}
.company {font-size:.82rem;color:#9aa3b2;margin-top:.12rem;}
.score {min-width:46px;text-align:center;border-radius:12px;padding:.35rem .45rem;background:#16a34a;color:white;font-weight:800;font-size:1.05rem;}
.mini-row {display:grid;grid-template-columns:1fr 1fr;gap:.35rem .8rem;margin-top:.8rem;font-size:.82rem;color:#9aa3b2;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">💰 Dividend</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="module-subtitle">Income, payout sustainability, quality, balance-sheet strength, and momentum in a mobile-first view.</div>',
    unsafe_allow_html=True,
)

home_col, refresh_col = st.columns(2)
with home_col:
    st.page_link("app.py", label="Home", icon="🏠", width="stretch")
with refresh_col:
    refresh = st.button("🔄 Refresh", use_container_width=True)
if refresh:
    load_dividend_data.clear()

with st.spinner("Loading Dividend research..."):
    data = load_dividend_data(DIVIDEND_TICKERS)
if data.empty:
    st.warning("Dividend data is currently unavailable.")
    st.stop()

search = st.selectbox(
    "Search Dividend",
    options=list(DIVIDEND_TICKERS),
    index=None,
    placeholder="Search a ticker or company...",
    format_func=format_security_option,
    key="dividend_search",
    label_visibility="collapsed",
)

sector_options = ["All"] + sorted(data["Sector"].dropna().astype(str).unique().tolist())
sector = st.selectbox("Sector", sector_options, label_visibility="collapsed")

filtered = data.copy()
filtered = data.copy()

if search:
    filtered = filtered[
        filtered["Ticker"].astype(str).str.upper() == search.upper()
    ]
if sector != "All":
    filtered = filtered[filtered["Sector"] == sector]

st.markdown('<div class="section-label">DIVIDEND SNAPSHOT</div>', unsafe_allow_html=True)
a, b = st.columns(2)
a.metric("Stocks", len(filtered))
b.metric("Median Yield", fmt(number(filtered["Dividend Yield"].median()) if not filtered.empty else np.nan, "{:.2%}"))
c, d = st.columns(2)
c.metric("Median Payout", fmt(number(filtered["Payout Ratio"].median()) if not filtered.empty else np.nan, "{:.0%}"))
d.metric("Median Safety", fmt(number(filtered["Sustainability Score"].median()) if not filtered.empty else np.nan, "{:.0f}"))

if filtered.empty:
    st.info("No Dividend stocks match the current search and sector filter.")
    st.stop()

st.markdown('<div class="section-label">TOP DIVIDEND CANDIDATES</div>', unsafe_allow_html=True)
show_count = st.select_slider("Show", options=[5, 10, 15, 20], value=st.session_state.get("mobile_default_result_count", 10), label_visibility="collapsed")
leaders = filtered.sort_values(["Overall Score", "Sustainability Score"], ascending=[False, False]).head(show_count)
for _, row in leaders.iterrows():
    stock_card(row)

if st.session_state.get("mobile_show_charts", True):
    st.divider()
    st.markdown('<div class="section-label">YIELD VS SUSTAINABILITY</div>', unsafe_allow_html=True)
    chart = filtered.dropna(subset=["Dividend Yield", "Sustainability Score"]).copy()
    if not chart.empty:
        chart["Bubble Size"] = pd.to_numeric(chart["Market Cap"], errors="coerce").clip(lower=1)
        fig = px.scatter(
            chart,
            x="Dividend Yield",
            y="Sustainability Score",
            size="Bubble Size",
            size_max=25,
            color="Sector",
            hover_name="Ticker",
            hover_data={
                "Company": True,
                "Overall Score": ":.1f",
                "Payout Ratio": ":.0%",
                "Quality Score": ":.1f",
                "12M Return": ":.1%",
                "Bubble Size": False,
            },
        )
        fig.update_xaxes(
            tickformat=".1%",
            title="Dividend Yield"
        )

        fig.update_yaxes(
            range=[-5, 105],
            title="Sustainability"
        )

        fig.update_layout(
            height=410,
            margin=dict(
                l=35,
                r=35,
                t=50,
                b=35,
            ),
            showlegend=False,
        )

        st.plotly_chart(
            fig,
            width="content",
            height="content",
        )

if st.session_state.get("mobile_show_disclaimer", True):
    st.caption("Mobile Dividend scores are compact research signals, not investment recommendations.")

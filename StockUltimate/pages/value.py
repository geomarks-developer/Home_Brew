"""stockchoice - Value module."""
from __future__ import annotations

FALLBACK_VERSION = "2026-10-31-v2"

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



def statement_row(statement: pd.DataFrame, names: tuple[str, ...]) -> pd.Series:
    for name in names:
        if name in statement.index:
            return pd.to_numeric(statement.loc[name], errors="coerce").dropna()
    return pd.Series(dtype=float)


def period_growth(values: pd.Series) -> float:
    if len(values) < 2:
        return np.nan
    newest = number(values.iloc[0])
    previous = number(values.iloc[1])
    if not np.isfinite(newest) or not np.isfinite(previous) or previous <= 0:
        return np.nan
    return float(newest / previous - 1)


def statement_value_fallbacks(security: yf.Ticker) -> dict[str, float]:
    result = {
        "Revenue Growth": np.nan,
        "Earnings Growth": np.nan,
        "Free Cash Flow": np.nan,
        "EPS": np.nan,
        "Book Equity": np.nan,
        "Shares Outstanding": np.nan,
        "EBITDA": np.nan,
        "Total Debt": np.nan,
        "Cash": np.nan,
    }
    for statement_name in ("quarterly_income_stmt", "income_stmt"):
        try:
            statement = getattr(security, statement_name)
        except Exception as exc:
            print(f"Value fallback error for {security.ticker} ({statement_name}): {type(exc).__name__}: {exc}")
            continue
        if statement is None or statement.empty:
            continue
        if not np.isfinite(result["Revenue Growth"]):
            result["Revenue Growth"] = period_growth(statement_row(statement, ("Total Revenue", "Operating Revenue")))
        if not np.isfinite(result["Earnings Growth"]):
            result["Earnings Growth"] = period_growth(statement_row(statement, ("Net Income", "Net Income Common Stockholders", "Diluted EPS", "Basic EPS")))
        if statement_name == "income_stmt":
            eps_values = statement_row(statement, ("Diluted EPS", "Basic EPS"))
            if not eps_values.empty:
                result["EPS"] = number(eps_values.iloc[0])
            ebitda_values = statement_row(statement, ("Normalized EBITDA", "EBITDA"))
            if not ebitda_values.empty:
                result["EBITDA"] = number(ebitda_values.iloc[0])
    for balance_name in ("quarterly_balance_sheet", "balance_sheet"):
        try:
            balance = getattr(security, balance_name)
        except Exception as exc:
            print(f"Value balance-sheet fallback error for {security.ticker} ({balance_name}): {type(exc).__name__}: {exc}")
            continue
        if balance is None or balance.empty:
            continue
        equity = statement_row(balance, ("Stockholders Equity", "Total Stockholder Equity", "Common Stock Equity"))
        shares = statement_row(balance, ("Ordinary Shares Number", "Share Issued"))
        debt = statement_row(balance, ("Total Debt",))
        cash = statement_row(balance, ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents"))
        if not equity.empty:
            result["Book Equity"] = number(equity.iloc[0])
        if not shares.empty:
            result["Shares Outstanding"] = number(shares.iloc[0])
        if not debt.empty:
            result["Total Debt"] = number(debt.iloc[0])
        if not cash.empty:
            result["Cash"] = number(cash.iloc[0])
        break

    for cash_name in ("quarterly_cashflow", "cashflow"):
        try:
            cashflow = getattr(security, cash_name)
        except Exception as exc:
            print(f"Value cash-flow fallback error for {security.ticker} ({cash_name}): {type(exc).__name__}: {exc}")
            continue
        if cashflow is None or cashflow.empty:
            continue
        values = statement_row(cashflow, ("Free Cash Flow",))
        if not values.empty:
            periods = min(4, len(values)) if cash_name.startswith("quarterly") else 1
            result["Free Cash Flow"] = float(values.iloc[:periods].sum())
            break
        operating = statement_row(cashflow, ("Operating Cash Flow", "Total Cash From Operating Activities"))
        capex = statement_row(cashflow, ("Capital Expenditure", "Capital Expenditures"))
        if not operating.empty and not capex.empty:
            periods = min(4, len(operating), len(capex)) if cash_name.startswith("quarterly") else 1
            result["Free Cash Flow"] = float(operating.iloc[:periods].sum() + capex.iloc[:periods].sum())
            break
    return result

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


def value_scores(
    security: yf.Ticker,
    info: dict,
    history: pd.DataFrame,
    price: float,
) -> dict[str, float]:
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

    fallback = statement_value_fallbacks(security)
    if not np.isfinite(revenue_growth):
        revenue_growth = fallback["Revenue Growth"]
    if not np.isfinite(earnings_growth):
        earnings_growth = fallback["Earnings Growth"]

    if not np.isfinite(fcf):
        fcf = fallback["Free Cash Flow"]

    # ---------------------------------------------------------
    # Valuation fallbacks
    # ---------------------------------------------------------

    shares = fallback["Shares Outstanding"]

    # Market Cap = Price × Shares Outstanding
    if (
        not np.isfinite(market_cap)
        and np.isfinite(price)
        and np.isfinite(shares)
        and shares > 0
    ):
        market_cap = price * shares


    # P/E fallback using annual EPS
    eps = fallback["EPS"]

    if (
        not np.isfinite(forward_pe)
        and np.isfinite(price)
        and np.isfinite(eps)
        and eps > 0
    ):
        forward_pe = price / eps


    # Price / Book fallback
    book_equity = fallback["Book Equity"]

    if (
        not np.isfinite(price_book)
        and np.isfinite(market_cap)
        and np.isfinite(book_equity)
        and book_equity > 0
    ):
        price_book = market_cap / book_equity


    # EV / EBITDA fallback
    ebitda = fallback["EBITDA"]
    total_debt = fallback["Total Debt"]
    cash = fallback["Cash"]

    if (
        not np.isfinite(ev_ebitda)
        and np.isfinite(market_cap)
        and np.isfinite(ebitda)
        and ebitda > 0
    ):
        enterprise_value = market_cap

        if np.isfinite(total_debt):
            enterprise_value += total_debt

        if np.isfinite(cash):
            enterprise_value -= cash

        if enterprise_value > 0:
            ev_ebitda = enterprise_value / ebitda


    # Free Cash Flow Yield fallback
    if (
        np.isfinite(fcf)
        and np.isfinite(market_cap)
        and market_cap > 0
    ):
        fcf_yield = fcf / market_cap
    else:
        fcf_yield = np.nan

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
        "Market Cap": market_cap,
        "Forward PE": forward_pe,
        "Price to Book": price_book,
        "EV/EBITDA": ev_ebitda,
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


@st.cache_data(ttl=cache_ttl(), show_spinner=False)
def load_value_data(tickers: tuple[str, ...]) -> pd.DataFrame:
    rows = []
    for ticker in tickers:
        try:
            security = yf.Ticker(ticker)
            try:
                info = security.info or {}
            except Exception as exc:
                print(f"Value info unavailable for {ticker}: {type(exc).__name__}: {exc}")
                info = {}

            history = security.history(period="2y", auto_adjust=True)
            price = np.nan
            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
                if not closes.empty:
                    price = float(closes.iloc[-1])

            scores = value_scores(security, info, history, price)

            rows.append({
                "Ticker": ticker,
                "Company": info.get("shortName") or ticker,
                "Sector": info.get("sector") or "Unknown",
                "Price": price,
                **scores,
            })
        except Exception as exc:
            print(f"Value data error for {ticker}: {type(exc).__name__}: {exc}")
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
            st.switch_page("pages/details.py")


apply_card_density()
st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {display:none !important; visibility:hidden !important;}
.block-container {max-width:520px; padding:2.5rem 1rem 5rem 1rem;}
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
    st.page_link("app.py", label="Home", icon="🏠", width="stretch")
with refresh_col:
    refresh = st.button("🔄 Refresh", use_container_width=True)
if refresh:
    load_value_data.clear()

with st.spinner("Loading Value research..."):
    data = load_value_data(VALUE_TICKERS)
if data.empty:
    st.warning("Value data is currently unavailable.")
    st.stop()

# ---------------------------------------------------------
# Search / filter
# ---------------------------------------------------------
search = st.selectbox(
    "Search Value",
    options=list(VALUE_TICKERS),
    index=None,
    placeholder="Search a ticker or company...",
    format_func=format_security_option,
    key="value_search",
    label_visibility="collapsed",
)

sector_options = (
    ["All"]
    + sorted(
        data["Sector"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
)

sector = st.selectbox(
    "Sector",
    sector_options,
    label_visibility="collapsed",
)

filtered = data.copy()

if search:
    filtered = filtered[
        filtered["Ticker"].astype(str).str.upper() == search.upper()
    ]

if sector != "All":
    filtered = filtered[
        filtered["Sector"] == sector
    ]


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
show_count = st.select_slider("Show", options=[5, 10, 15, 20], value=st.session_state.get("mobile_default_result_count", 10), label_visibility="collapsed")
leaders = filtered.sort_values(["Overall Score", "Value Trap Risk"], ascending=[False, True]).head(show_count)
for _, row in leaders.iterrows():
    stock_card(row)

if st.session_state.get("mobile_show_charts", True):
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
        fig.update_xaxes(range=[-5, 105], title="Valuation →")
        fig.update_yaxes(range=[105, -5], title="Trap Risk ↓")
        fig.update_layout(height=390, margin=dict(l=35, r=35, t=35, b=35), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

if st.session_state.get("mobile_show_disclaimer", True):
    st.caption("Mobile Value scores are compact research signals, not investment recommendations.")

"""MarketScope Mobile - markets dashboard."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

MARKET_SYMBOLS = {
    "S&P 500": "^GSPC",
    "Nasdaq": "^IXIC",
    "Dow": "^DJI",
    "Russell 2000": "^RUT",
    "VIX": "^VIX",
    "10Y Treasury": "^TNX",
}

SECTOR_ETFS = {
    "Technology": "XLK",
    "Financials": "XLF",
    "Health Care": "XLV",
    "Industrials": "XLI",
    "Consumer Disc.": "XLY",
    "Communication": "XLC",
    "Energy": "XLE",
    "Consumer Staples": "XLP",
    "Utilities": "XLU",
    "Materials": "XLB",
    "Real Estate": "XLRE",
}

ASSET_ETFS = {
    "US Stocks": "SPY",
    "International": "VXUS",
    "Bonds": "BND",
    "Gold": "GLD",
    "Oil": "USO",
}


def number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan
    return result if np.isfinite(result) else np.nan


def fmt(value: object, pattern: str) -> str:
    value = number(value)
    return pattern.format(value) if np.isfinite(value) else "N/A"


@st.cache_data(ttl=900, show_spinner=False)
def load_market_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    symbols = tuple(dict.fromkeys(
        list(MARKET_SYMBOLS.values()) + list(SECTOR_ETFS.values()) + list(ASSET_ETFS.values())
    ))
    histories: dict[str, pd.Series] = {}

    for symbol in symbols:
        try:
            history = yf.Ticker(symbol).history(period="2y", auto_adjust=True)
            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
                if not closes.empty:
                    histories[symbol] = closes
        except Exception:
            continue

    def metrics(name: str, symbol: str) -> dict[str, object]:
        closes = histories.get(symbol, pd.Series(dtype=float))
        price = float(closes.iloc[-1]) if not closes.empty else np.nan
        day = closes.iloc[-1] / closes.iloc[-2] - 1 if len(closes) > 1 else np.nan
        week = closes.iloc[-1] / closes.iloc[-6] - 1 if len(closes) > 5 else np.nan
        month = closes.iloc[-1] / closes.iloc[-22] - 1 if len(closes) > 21 else np.nan
        three_month = closes.iloc[-1] / closes.iloc[-64] - 1 if len(closes) > 63 else np.nan
        six_month = closes.iloc[-1] / closes.iloc[-127] - 1 if len(closes) > 126 else np.nan
        twelve_month = closes.iloc[-1] / closes.iloc[-252] - 1 if len(closes) > 251 else np.nan
        return {
            "Name": name,
            "Symbol": symbol,
            "Price": price,
            "1D": day,
            "1W": week,
            "1M": month,
            "3M": three_month,
            "6M": six_month,
            "12M": twelve_month,
        }

    indices = pd.DataFrame([metrics(name, symbol) for name, symbol in MARKET_SYMBOLS.items()])
    sectors = pd.DataFrame([metrics(name, symbol) for name, symbol in SECTOR_ETFS.items()])
    assets = pd.DataFrame([metrics(name, symbol) for name, symbol in ASSET_ETFS.items()])

    performance_frames = []
    for name, symbol in {**ASSET_ETFS, "Nasdaq 100": "QQQ"}.items():
        closes = histories.get(symbol)
        if closes is None or closes.empty:
            try:
                history = yf.Ticker(symbol).history(period="2y", auto_adjust=True)
                closes = pd.to_numeric(history["Close"], errors="coerce").dropna()
            except Exception:
                continue
        if closes is not None and not closes.empty:
            indexed = closes / closes.iloc[0] * 100
            performance_frames.append(pd.DataFrame({
                "Date": indexed.index,
                "Indexed Value": indexed.values,
                "Asset": name,
            }))

    performance = pd.concat(performance_frames, ignore_index=True) if performance_frames else pd.DataFrame()
    return indices, sectors, assets, performance


def market_card(row: pd.Series) -> None:
    change = number(row.get("1D"))
    change_class = "positive" if np.isfinite(change) and change >= 0 else "negative"
    st.markdown(f"""
<div class="market-card">
 <div class="market-row">
  <div><div class="market-name">{row['Name']}</div><div class="market-symbol">{row['Symbol']}</div></div>
  <div class="market-price">{fmt(row.get('Price'), '{:,.2f}')}</div>
 </div>
 <div class="returns">
  <span class="{change_class}">1D <b>{fmt(row.get('1D'), '{:+.2%}')}</b></span>
  <span>1M <b>{fmt(row.get('1M'), '{:+.1%}')}</b></span>
  <span>12M <b>{fmt(row.get('12M'), '{:+.1%}')}</b></span>
 </div>
</div>
""", unsafe_allow_html=True)


st.markdown("""
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"] {display:none;}
.block-container {max-width:520px;padding:2.5rem 1rem 5rem 1rem;}
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.market-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.85rem 1rem;background:rgba(128,128,128,.05);margin-top:.65rem;}
.market-row {display:flex;align-items:flex-start;justify-content:space-between;gap:.8rem;}
.market-name {font-size:1.05rem;font-weight:760;}
.market-symbol {font-size:.78rem;color:#9aa3b2;margin-top:.1rem;}
.market-price {font-size:1rem;font-weight:800;}
.returns {display:grid;grid-template-columns:1fr 1fr 1fr;gap:.3rem;margin-top:.7rem;font-size:.78rem;color:#9aa3b2;}
.positive {color:#16a34a;}
.negative {color:#dc2626;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:650;margin-top:.7rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="module-title">🌐 Markets</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="module-subtitle">A compact market pulse covering major indexes, sectors, bonds, commodities, and global assets.</div>',
    unsafe_allow_html=True,
)

home_col, refresh_col = st.columns(2)
with home_col:
    st.page_link("mobile_home.py", label="Home", icon="🏠", width="stretch")
with refresh_col:
    refresh = st.button("🔄 Refresh", use_container_width=True)
if refresh:
    load_market_data.clear()

with st.spinner("Loading market dashboard..."):
    indices, sectors, assets, performance = load_market_data()

if indices.empty and sectors.empty and assets.empty:
    st.warning("Market data is currently unavailable.")
    st.stop()

st.markdown('<div class="section-label">MARKET PULSE</div>', unsafe_allow_html=True)
for _, row in indices.iterrows():
    market_card(row)

st.divider()
st.markdown('<div class="section-label">SECTOR LEADERSHIP</div>', unsafe_allow_html=True)
period = st.segmented_control(
    "Sector period",
    options=["1D", "1W", "1M", "3M", "6M", "12M"],
    default="1M",
    label_visibility="collapsed",
)
period = period or "1M"
sector_chart = sectors.dropna(subset=[period]).sort_values(period)
if not sector_chart.empty:
    fig = px.bar(
        sector_chart,
        x=period,
        y="Name",
        orientation="h",
        color=period,
        color_continuous_scale="RdYlGn",
        text=period,
        hover_data={"Symbol": True},
    )
    fig.update_traces(texttemplate="%{text:+.1%}", textposition="outside")
    fig.update_xaxes(tickformat=".0%", title="Return")
    fig.update_layout(height=430, margin=dict(l=5, r=5, t=10, b=5), coloraxis_showscale=False, yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

st.divider()
st.markdown('<div class="section-label">CROSS-ASSET SNAPSHOT</div>', unsafe_allow_html=True)
asset_cols = st.columns(2)
for index, (_, row) in enumerate(assets.iterrows()):
    container = asset_cols[index % 2]
    container.metric(
        str(row["Name"]),
        fmt(row.get("Price"), "{:,.2f}"),
        fmt(row.get("1M"), "{:+.1%}"),
    )

st.divider()
st.markdown('<div class="section-label">GROWTH OF $100</div>', unsafe_allow_html=True)
if not performance.empty:
    fig = px.line(performance, x="Date", y="Indexed Value", color="Asset")
    fig.add_hline(y=100, line_dash="dot", line_color="gray")
    fig.update_layout(
        height=370,
        margin=dict(l=5, r=5, t=10, b=5),
        xaxis_title="",
        yaxis_title="Value",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=.5),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

st.caption("Market information is delayed or subject to source availability and is provided for research use.")

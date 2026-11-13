from pathlib import Path

import pandas as pd
import streamlit as st

from screener_engine import (
    WORKBOOK_NAME,
    SECTOR_ETFS,
    create_treemap,
    download_history,
    heatmap_rows,
    read_tickers,
    sector_heatmap_rows,
)

BASE_DIR = Path(__file__).resolve().parent.parent
if not (BASE_DIR / WORKBOOK_NAME).exists():
    BASE_DIR = Path(__file__).resolve().parent

WORKBOOK_PATH = BASE_DIR / WORKBOOK_NAME
CACHE_FILE = BASE_DIR / "screener_cache.pkl"


def load_cache():
    if not CACHE_FILE.exists():
        return {}, {}, {}
    with open(CACHE_FILE, "rb") as file:
        data = pickle.load(file)
    return (
        data.get("histories", {}),
        data.get("cache", {}),
        data.get("fund_cache", {}),
    )


def save_cache(histories, info_cache, fund_cache):
    with open(CACHE_FILE, "wb") as file:
        pickle.dump(
            {
                "histories": histories,
                "cache": info_cache,
                "fund_cache": fund_cache,
            },
            file,
        )


def make_frame(rows):
    return pd.DataFrame(rows)


def render_map(fig, key):
    if fig is None:
        st.info("No heatmap data is available.")
        return
    fig.update_layout(height=720)
    st.plotly_chart(
        fig,
        width="stretch",
        key=key,
        config={
            "displayModeBar": True,
            "displaylogo": False,
        },
    )


shared_data = st.session_state.get("market_data")
if shared_data is None:
    st.error("Shared MarketScope data is not loaded. Return to Summary or restart the app.")
    st.stop()

sp100 = shared_data["sp100_heatmap_df"].copy()
dividends = shared_data["dividend_heatmap_df"].copy()
etfs = shared_data["etf_heatmap_df"].copy()
sectors = shared_data["sector_heatmap_df"].copy()

if all(frame.empty for frame in [sp100, dividends, etfs, sectors]):
    st.warning("No heatmap data is currently available.")
    st.stop()

# Quick market snapshot
s1, s2, s3, s4 = st.columns(4)

def avg_change(frame):
    if frame.empty or "1 Month Change %" not in frame:
        return None
    return pd.to_numeric(frame["1 Month Change %"], errors="coerce").mean()

for column, label, frame in [
    (s1, "S&P 100 Avg 1M", sp100),
    (s2, "Dividend Avg 1M", dividends),
    (s3, "ETF Avg 1M", etfs),
    (s4, "Sector Avg 1M", sectors),
]:
    value = avg_change(frame)
    column.metric(label, f"{value:+.2%}" if pd.notna(value) else "N/A")

st.divider()

sp_tab, dividend_tab, etf_tab, sector_tab = st.tabs(
    ["🏛️ S&P 100", "💵 Dividends", "📊 ETFs", "🧭 Sectors"]
)

with sp_tab:
    st.subheader("S&P 100 One-Month Heatmap")
    st.caption("Tile size reflects market capitalization; color reflects one-month price change.")
    render_map(
        create_treemap(sp100, "S&P 100 One-Month Heatmap"),
        "sp100_heatmap",
    )

with dividend_tab:
    st.subheader("Dividend Stock One-Month Heatmap")
    st.caption("Hover over a tile for price, trend, yield, and payout details when available.")
    render_map(
        create_treemap(dividends, "Dividend Stock One-Month Heatmap"),
        "dividend_heatmap",
    )

with etf_tab:
    st.subheader("ETF One-Month Heatmap")
    st.caption("Tile size reflects fund assets when available; color reflects one-month price change.")
    render_map(
        create_treemap(etfs, "ETF One-Month Heatmap"),
        "etf_heatmap",
    )

with sector_tab:
    st.subheader("U.S. Sector ETF One-Month Heatmap")
    st.caption("Each sector is represented by the sector ETF used in your screener engine.")
    render_map(
        create_treemap(sectors, "U.S. Sector ETF One-Month Heatmap", True),
        "sector_heatmap",
    )

from datetime import date, datetime
from pathlib import Path

import streamlit as st

from market_data import clear_market_data_cache, get_market_data

st.set_page_config(
    page_title="MarketScope",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Overview": [
        st.Page("pages/summary.py", title="Summary", icon="🏠", default=True),
    ],
    "Screeners": [
        st.Page("pages/stock.py", title="Stock Screener", icon="📈"),
        st.Page("pages/dividends.py", title="Dividend Screener", icon="💵"),
        st.Page("pages/etfs.py", title="ETF Screener", icon="📊"),
    ],
    "Market": [
        st.Page("pages/heatmaps.py", title="Market Heatmaps", icon="🗺️"),
    ],
    "Research": [
        st.Page("pages/methodology.py", title="Methodology", icon="📖"),
    ],
}

page = st.navigation(pages, position="sidebar", expanded=True)

st.sidebar.markdown("### 📈 MarketScope")
st.sidebar.caption("Investment Research")
st.sidebar.divider()

refresh_all = st.sidebar.button(
    "🔄 Refresh All Market Data",
    type="primary",
     width="stretch",
)

try:
    today_string = date.today().isoformat()
    existing_data = st.session_state.get("market_data")

    # IMPORTANT: Only session data that already has a date can be stale.
    # The older market_data.py did not return data_date. Treating a missing
    # data_date as stale caused a forced yfinance refresh on every rerun.
    stale_session_data = (
        existing_data is not None
        and existing_data.get("data_date") is not None
        and existing_data.get("data_date") != today_string
    )

    if refresh_all or stale_session_data:
        clear_market_data_cache()
        shared_data = get_market_data(
            force_refresh=True,
            show_progress=True,
        )
        shared_data["data_date"] = today_string
        st.session_state["market_data"] = shared_data

    elif existing_data is None:
        # New browser session. Use the pickle when it was written today;
        # otherwise force one daily refresh.
        root_dir = Path(__file__).resolve().parent
        cache_file = root_dir / "screener_cache.pkl"

        cache_is_today = False
        if cache_file.exists():
            cache_date = datetime.fromtimestamp(
                cache_file.stat().st_mtime
            ).date()
            cache_is_today = cache_date == date.today()

        shared_data = get_market_data(
            force_refresh=not cache_is_today,
            show_progress=True,
        )
        shared_data["data_date"] = today_string
        st.session_state["market_data"] = shared_data

    else:
        # Page changes, filters, and row selections come through here.
        # No cache load. No screener rebuild. No yfinance.
        shared_data = existing_data

    st.sidebar.caption(
        f"Loaded {shared_data['ticker_count']:,} tickers"
    )
    st.sidebar.caption(
        f"Market data date: {shared_data.get('data_date', today_string)}"
    )
    st.sidebar.caption(
        f"Session loaded: {shared_data['loaded_at']}"
    )

    if refresh_all:
        st.sidebar.success("Manual refresh completed.")
    elif stale_session_data:
        st.sidebar.success("Daily cache refresh completed.")

except Exception as error:
    st.error(f"MarketScope could not load market data: {error}")
    st.stop()

with st.sidebar.container(border=True):
    st.markdown("#### ⚠️ Risk Notice")
    st.caption(
        "For informational and research purposes only. "
        "Not investment, financial, tax, or legal advice. "
        "Investing involves risk, including possible loss of principal. "
        "Past performance does not guarantee future results."
    )
    st.page_link(
        "pages/methodology.py",
        label="Read methodology and disclosures",
        icon="📖",
    )

page.run()

"""
TickerTrends Screener
=====================

Mobile-first stock screener.

Architecture rule:

    Streamlit pages read SQLite.
    The scanner talks to market-data providers.

This page does not call yfinance or calculate scores.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from st_aggrid import AgGrid, GridOptionsBuilder

from core.database import get_all_ticker_states


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Screener | TickerTrends",
    page_icon="🔎",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ============================================================
# CONSTANTS
# ============================================================

TREND_ORDER = [
    "Strong Bullish",
    "Bullish",
    "Accumulation",
    "Extended",
    "Weakening",
    "Bearish",
]

TREND_ICONS = {
    "Strong Bullish": "🟢",
    "Bullish": "🟢",
    "Accumulation": "🔵",
    "Extended": "🟡",
    "Weakening": "🟠",
    "Bearish": "🔴",
}

UNIVERSE_OPTIONS = [
    "All",
    "NASDAQ-100",
    "S&P 100",
    "Dividend Aristocrats",
]


# ============================================================
# CACHED SQLITE READ
# ============================================================

@st.cache_data(ttl=300)
def load_screener_data() -> pd.DataFrame:
    """
    Load current TickerTrends results from SQLite.

    No market-data requests are performed.
    """

    rows = get_all_ticker_states()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


# ============================================================
# DISPLAY HELPERS
# ============================================================

def trend_display(
    state: str | None,
) -> str:
    """
    Return compact trend display text.
    """

    if not state:
        return "⚪ Unknown"

    icon = TREND_ICONS.get(
        state,
        "⚪",
    )

    return f"{icon} {state}"


# ============================================================
# FILTERING
# ============================================================

def apply_filters(
    df: pd.DataFrame,
    selected_ticker: str | None,
    selected_trends: list[str],
    minimum_score: int,
    universe: str,
    complete_scores_only: bool,
) -> pd.DataFrame:
    """
    Apply all Screener filters.
    """
    filtered = df.copy()

    # --------------------------------------------------------
    # STOCK
    # --------------------------------------------------------
    if selected_ticker:
        filtered = filtered[
            filtered["ticker"].astype(str) == selected_ticker
        ]

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------
    if selected_trends:
        filtered = filtered[
            filtered["trend_state"].isin(selected_trends)
        ]

    # --------------------------------------------------------
    # COMPLETE SCORES
    # --------------------------------------------------------
    if complete_scores_only:
        filtered = filtered[
            filtered["total_score"].notna()
        ]

    # --------------------------------------------------------
    # MINIMUM SCORE
    # --------------------------------------------------------
    if minimum_score > 0:
        filtered = filtered[
            filtered["total_score"].fillna(-1) >= minimum_score
        ]

    # --------------------------------------------------------
    # UNIVERSE
    # --------------------------------------------------------
    if universe == "NASDAQ-100":
        filtered = filtered[filtered["in_nasdaq100"] == 1]
    elif universe == "S&P 100":
        filtered = filtered[filtered["in_sp100"] == 1]
    elif universe == "Dividend Aristocrats":
        filtered = filtered[filtered["in_aristocrats"] == 1]

    # --------------------------------------------------------
    # DEFAULT SORT
    # --------------------------------------------------------
    filtered = filtered.sort_values(
        by=["total_score", "ticker"],
        ascending=[False, True],
        na_position="last",
    )
    return filtered

# ============================================================
# NAVIGATION
# ============================================================

if st.button(
    "🏠 Home",
    key="home_button",
    use_container_width=False,
):
    st.switch_page("Summary.py")


# ============================================================
# HEADER
# ============================================================

st.title("🔎 Screener")

st.caption(
    "Trend first. Fundamentals second."
)


# ============================================================
# LOAD DATA
# ============================================================

df = load_screener_data()

if df.empty:

    st.info(
        "No TickerTrends scan data is available."
    )

    st.stop()


# ============================================================
# PRIMARY FILTERS
# ============================================================

stock_options = [None] + (
    df[["ticker", "company_name"]]
    .drop_duplicates(subset=["ticker"])
    .sort_values("ticker")
    .apply(
        lambda row: (
            str(row["ticker"]),
            (
                str(row["company_name"])
                if pd.notna(row["company_name"])
                and str(row["company_name"]).strip()
                else str(row["ticker"])
            ),
        ),
        axis=1,
    )
    .tolist()
)

selected_stock = st.selectbox(
    "Stock",
    options=stock_options,
    index=0,
    format_func=lambda option: (
        "All Stocks"
        if option is None
        else f"{option[0]} — {option[1]}"
    ),
    placeholder="Choose a stock",
)

selected_ticker = (
    selected_stock[0]
    if selected_stock is not None
    else None
)


selected_trends = st.multiselect(
    "Trend",
    TREND_ORDER,
    default=[],
    placeholder="All trend states",
)


# ============================================================
# SECONDARY FILTERS
# ============================================================

with st.expander(
    "⚙️ More Filters",
    expanded=False,
):

    universe = st.selectbox(
        "Universe",
        UNIVERSE_OPTIONS,
        index=0,
    )

    minimum_score = st.slider(
        "Minimum Score",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )

    complete_scores_only = st.toggle(
        "Complete scores only",
        value=True,
    )


# ============================================================
# APPLY FILTERS
# ============================================================

filtered = apply_filters(
    df=df,
    selected_ticker=selected_ticker,
    selected_trends=selected_trends,
    minimum_score=minimum_score,
    universe=universe,
    complete_scores_only=complete_scores_only,
)


# ============================================================
# RESULT COUNT
# ============================================================

if len(filtered) == 1:

    st.caption(
        "1 stock"
    )

else:

    st.caption(
        f"{len(filtered)} stocks"
    )


# ============================================================
# NO RESULTS
# ============================================================

if filtered.empty:

    st.info(
        "No stocks match the current filters."
    )

    st.stop()


# ============================================================
# BUILD MOBILE DISPLAY
# ============================================================

display = filtered[
    [
        "ticker",
        "company_name",
        "trend_state",
        "total_score",
    ]
].copy()

# Clean up missing company names.
display["company_name"] = (
    display["company_name"]
    .fillna("")
)

display["trend_state"] = (
    display["trend_state"]
    .apply(
        trend_display
    )
)

display["total_score"] = (
    pd.to_numeric(
        display["total_score"],
        errors="coerce",
    )
    .round(1)
)

display.rename(
    columns={
        "ticker": "Ticker",
        "company_name": "Company",
        "trend_state": "Trend",
        "total_score": "Score",
    },
    inplace=True,
)

display.reset_index(
    drop=True,
    inplace=True,
)

# ============================================================
# CLICKABLE SCREENER TABLE
# ============================================================

grid_builder = GridOptionsBuilder.from_dataframe(display)

grid_builder.configure_default_column(
    sortable=True,
    filterable=False,
    resizable=True,
    editable=False,
)

grid_builder.configure_column(
    "Ticker",
    width=105,
    minWidth=90,
)

grid_builder.configure_column(
    "Company",
    width=220,
    minWidth=145,
)

grid_builder.configure_column(
    "Trend",
    width=180,
    minWidth=140,
)

grid_builder.configure_column(
    "Score",
    width=85,
    minWidth=70,
    type=["numericColumn"],
    valueFormatter="x == null ? '' : x.toFixed(1)",
)

# Select a stock by clicking anywhere on its row.
# No checkbox column is displayed.
grid_builder.configure_selection(
    selection_mode="single",
    use_checkbox=False,
)

grid_options = grid_builder.build()
grid_options["suppressRowClickSelection"] = False

grid_response = AgGrid(
    display,
    gridOptions=grid_options,
    height=560,
    fit_columns_on_grid_load=True,
    allow_unsafe_jscode=False,
    update_on=["selectionChanged"],
    key="tickertrends_screener_clickable",
)

# ============================================================
# OPEN DETAILS WHEN A ROW IS CLICKED
# ============================================================

selected_rows = grid_response.get("selected_rows")
selected_row = None

if isinstance(selected_rows, pd.DataFrame):
    if not selected_rows.empty:
        selected_row = selected_rows.iloc[0]
elif isinstance(selected_rows, list):
    if selected_rows:
        selected_row = selected_rows[0]

if selected_row is not None:
    if isinstance(selected_row, pd.Series):
        clicked_ticker = selected_row.get("Ticker")
    else:
        clicked_ticker = selected_row.get("Ticker")

    if clicked_ticker:
        st.session_state["selected_ticker"] = str(clicked_ticker)
        st.switch_page("pages/5_Details.py")

# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Results are loaded from the latest TickerTrends "
    "scan stored in SQLite."
)
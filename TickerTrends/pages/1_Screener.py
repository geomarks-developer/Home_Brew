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

from core.database import get_all_ticker_states


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Screener | TickerTrends",
    page_icon="🔎",
    layout="wide",
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
    search: str,
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
    # SEARCH
    # --------------------------------------------------------

    search = search.strip()

    if search:

        ticker_match = (
            filtered["ticker"]
            .fillna("")
            .str.contains(
                search,
                case=False,
                regex=False,
            )
        )

        company_match = (
            filtered["company_name"]
            .fillna("")
            .str.contains(
                search,
                case=False,
                regex=False,
            )
        )

        filtered = filtered[
            ticker_match
            | company_match
        ]

    # --------------------------------------------------------
    # TREND
    # --------------------------------------------------------

    if selected_trends:

        filtered = filtered[
            filtered[
                "trend_state"
            ].isin(
                selected_trends
            )
        ]

    # --------------------------------------------------------
    # COMPLETE SCORES
    # --------------------------------------------------------

    if complete_scores_only:

        filtered = filtered[
            filtered[
                "total_score"
            ].notna()
        ]

    # --------------------------------------------------------
    # MINIMUM SCORE
    # --------------------------------------------------------

    if minimum_score > 0:

        filtered = filtered[
            filtered[
                "total_score"
            ].fillna(-1)
            >= minimum_score
        ]

    # --------------------------------------------------------
    # UNIVERSE
    # --------------------------------------------------------

    if universe == "NASDAQ-100":

        filtered = filtered[
            filtered[
                "in_nasdaq100"
            ]
            == 1
        ]

    elif universe == "S&P 100":

        filtered = filtered[
            filtered[
                "in_sp100"
            ]
            == 1
        ]

    elif universe == "Dividend Aristocrats":

        filtered = filtered[
            filtered[
                "in_aristocrats"
            ]
            == 1
        ]

    # --------------------------------------------------------
    # DEFAULT SORT
    # --------------------------------------------------------

    filtered = filtered.sort_values(
        by=[
            "total_score",
            "ticker",
        ],
        ascending=[
            False,
            True,
        ],
        na_position="last",
    )

    return filtered


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

search = st.text_input(
    "Search",
    placeholder="Ticker or company",
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
    search=search,
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
        "trend_state",
        "total_score",
        "rsi_14",
    ]
].copy()


display["trend_state"] = (
    display["trend_state"]
    .apply(
        trend_display
    )
)


display["total_score"] = (
    pd.to_numeric(
        display[
            "total_score"
        ],
        errors="coerce",
    )
    .round(1)
)


display["rsi_14"] = (
    pd.to_numeric(
        display[
            "rsi_14"
        ],
        errors="coerce",
    )
    .round(1)
)


# Preserve ticker order for row-selection lookup.
ticker_lookup = (
    display["ticker"]
    .reset_index(
        drop=True
    )
)


display.rename(
    columns={
        "ticker": "Ticker",
        "trend_state": "Trend",
        "total_score": "Score",
        "rsi_14": "RSI",
    },
    inplace=True,
)


display.reset_index(
    drop=True,
    inplace=True,
)


# ============================================================
# SCREENER TABLE
# ============================================================

selection = st.dataframe(
    display,
    hide_index=True,
    width="stretch",
    height=560,
    on_select="rerun",
    selection_mode="single-row",
    key="tickertrends_screener",
    column_order=[
        "Ticker",
        "Trend",
        "Score",
        "RSI",
    ],
    column_config={
        "Ticker": st.column_config.TextColumn(
            "Ticker",
            width="small",
        ),

        "Trend": st.column_config.TextColumn(
            "Trend",
            width="medium",
        ),

        "Score": st.column_config.NumberColumn(
            "Score",
            min_value=0,
            max_value=100,
            format="%.1f",
            width="small",
        ),

        "RSI": st.column_config.NumberColumn(
            "RSI",
            min_value=0,
            max_value=100,
            format="%.1f",
            width="small",
        ),
    },
)


# ============================================================
# SELECTED TICKER
# ============================================================

selected_rows = (
    selection.selection.rows
    if selection
    else []
)


if selected_rows:

    selected_index = (
        selected_rows[0]
    )

    selected_ticker = (
        ticker_lookup.iloc[
            selected_index
        ]
    )

    selected_record = (
        filtered[
            filtered["ticker"]
            == selected_ticker
        ]
        .iloc[0]
    )


    # Store selection for Details.
    st.session_state[
        "selected_ticker"
    ] = selected_ticker


    # --------------------------------------------------------
    # QUICK VIEW
    # --------------------------------------------------------

    st.divider()

    st.subheader(
        selected_ticker
    )


    company_name = (
        selected_record.get(
            "company_name"
        )
        or selected_ticker
    )


    st.caption(
        company_name
    )


    st.write(
        trend_display(
            selected_record[
                "trend_state"
            ]
        )
    )


    # --------------------------------------------------------
    # SCORE / RSI
    # --------------------------------------------------------

    score = (
        selected_record.get(
            "total_score"
        )
    )

    rsi = (
        selected_record.get(
            "rsi_14"
        )
    )


    metric_col1, metric_col2 = (
        st.columns(2)
    )


    with metric_col1:

        st.metric(
            "Score",
            (
                f"{score:.1f}"
                if pd.notna(score)
                else "N/A"
            ),
        )


    with metric_col2:

        st.metric(
            "RSI",
            (
                f"{rsi:.1f}"
                if pd.notna(rsi)
                else "N/A"
            ),
        )


    # --------------------------------------------------------
    # DETAILS LINK
    # --------------------------------------------------------

    st.page_link(
        "pages/5_Details.py",
        label=(
            f"View {selected_ticker} Details"
        ),
        icon="📈",
        use_container_width=True,
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Results are loaded from the latest TickerTrends "
    "scan stored in SQLite."
)
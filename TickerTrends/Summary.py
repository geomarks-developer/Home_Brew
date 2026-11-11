"""
TickerTrends
============

Mobile-friendly Summary / Home dashboard.

Architecture rule:

    Summary reads SQLite only.

Opening this page does NOT:
    - call yfinance
    - calculate technical indicators
    - calculate fundamentals
    - run the universe scanner

Market-data refreshes are handled separately by core.scanner.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd
import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder
from core.scanner import scan_universe

from core.database import (
    get_all_ticker_states,
    get_last_completed_scan,
    get_latest_data_timestamp,
    get_unacknowledged_changes,
    get_watchlist,
    initialize_database,
)


# ============================================================
# DATABASE INITIALIZATION
# ============================================================

initialize_database()

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="TickerTrends",
    page_icon="📈",
    layout="centered",
    #layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONSTANTS
# ============================================================

TREND_ICONS = {
    "Strong Bullish": "🟢",
    "Bullish": "🟢",
    "Accumulation": "🔵",
    "Extended": "🟡",
    "Weakening": "🟠",
    "Bearish": "🔴",
}

TREND_ORDER = [
    "Strong Bullish",
    "Bullish",
    "Accumulation",
    "Extended",
    "Weakening",
    "Bearish",
]


# ============================================================
# CACHED SQLITE READS
# ============================================================

@st.cache_data(ttl=300)
def load_market_data() -> pd.DataFrame:
    """
    Load calculated ticker states from SQLite.
    """

    rows = get_all_ticker_states()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_freshness() -> dict[str, Any]:
    """
    Load full-scan freshness information.
    """

    return {
        "scan": get_last_completed_scan(
            scan_type="full"
        ),

        "latest_ticker_update": (
            get_latest_data_timestamp()
        ),
    }


@st.cache_data(ttl=60)
def load_watchlist_data() -> pd.DataFrame:
    """
    Load the current Watchlist.
    """

    rows = get_watchlist()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


@st.cache_data(ttl=30)
def load_watchlist_changes() -> pd.DataFrame:
    """
    Load unacknowledged Watchlist state changes.
    """

    rows = get_unacknowledged_changes(
        watchlist_only=True
    )

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


# ============================================================
# CACHE CONTROL
# ============================================================
def clear_summary_caches() -> None:
    """Clear Summary reads after a completed market refresh."""
    load_market_data.clear()
    load_freshness.clear()
    load_watchlist_data.clear()
    load_watchlist_changes.clear()


# ============================================================
# FORMATTERS
# ============================================================

def parse_timestamp(
    value: str | None,
) -> datetime | None:
    """
    Parse an ISO database timestamp.
    """

    if not value:
        return None

    try:
        return datetime.fromisoformat(
            value
        )

    except ValueError:
        return None


def format_timestamp(
    value: str | None,
) -> str:
    """
    Format a timestamp for display.
    """

    parsed = parse_timestamp(
        value
    )

    if parsed is None:
        return "Not available"

    return parsed.strftime(
        "%b %d • %I:%M %p"
    )


def format_score(
    value,
) -> str:
    """
    Format TickerTrends score.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{float(value):.1f}"


def format_rsi(
    value,
) -> str:
    """
    Format RSI.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{float(value):.1f}"


def trend_display(
    state: str | None,
) -> str:
    """
    Display icon and trend name.
    """

    if not state:
        return "⚪ Unknown"

    icon = TREND_ICONS.get(
        state,
        "⚪",
    )

    return f"{icon} {state}"


# ============================================================
# FRESHNESS
# ============================================================

def full_scan_is_current(
    scan: dict[str, Any] | None,
) -> bool:
    """
    A completed full scan is current when its completion
    date matches today's date.
    """

    if not scan:
        return False

    completed_at = parse_timestamp(
        scan.get(
            "completed_at"
        )
    )

    if completed_at is None:
        return False

    now = datetime.now(
        completed_at.tzinfo
    )

    return (
        completed_at.date()
        == now.date()
    )


# ============================================================
# STOCK TABLE HELPER
# ============================================================

def display_stock_table(
    source_df: pd.DataFrame,
    key: str,
    height: int = 260,
) -> None:
    """
    Display a compact clickable stock grid.
    Clicking anywhere on a row opens Details for that ticker.
    """
    if source_df.empty:
        return

    table = source_df[
        [
            "ticker",
            "company_name",
            "trend_state",
            "total_score",
        ]
    ].copy()

    table["trend_state"] = (
        table["trend_state"]
        .apply(trend_display)
    )
    table["total_score"] = (
        pd.to_numeric(
            table["total_score"],
            errors="coerce",
        )
        .round(1)
    )

    table.rename(
        columns={
            "ticker": "Ticker",
            "company_name": "Company",
            "trend_state": "Trend",
            "total_score": "Score",
        },
        inplace=True,
    )
    table.reset_index(drop=True, inplace=True)

    grid_builder = GridOptionsBuilder.from_dataframe(table)
    grid_builder.configure_default_column(
        sortable=True,
        filterable=False,
        resizable=True,
        editable=False,
    )
    grid_builder.configure_column(
        "Ticker",
        width=95,
        minWidth=85,
    )
    grid_builder.configure_column(
        "Company",
        width=220,
        minWidth=160,
    )
    grid_builder.configure_column(
        "Trend",
        width=180,
        minWidth=145,
    )
    grid_builder.configure_column(
        "Score",
        width=95,
        minWidth=75,
        type=["numericColumn"],
    )

    grid_builder.configure_selection(
        selection_mode="single",
        use_checkbox=False,
    )

    grid_options = grid_builder.build()
    grid_options["suppressRowClickSelection"] = False

    grid_response = AgGrid(
        table,
        gridOptions=grid_options,
        height=height,
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=False,
        update_on=["selectionChanged"],
        key=key,
    )

    selected_rows = grid_response.get("selected_rows")
    selected_row = None

    if isinstance(selected_rows, pd.DataFrame):
        if not selected_rows.empty:
            selected_row = selected_rows.iloc[0]
    elif isinstance(selected_rows, list):
        if selected_rows:
            selected_row = selected_rows[0]

    if selected_row is None:
        return

    if isinstance(selected_row, pd.Series):
        selected_ticker = selected_row.get("Ticker")
    else:
        selected_ticker = selected_row.get("Ticker")

    if selected_ticker:
        st.session_state["selected_ticker"] = str(selected_ticker)
        st.switch_page("pages/5_Details.py")

# ============================================================
# LOAD DATA
# ============================================================

df = load_market_data()

freshness = load_freshness()

watchlist_df = (
    load_watchlist_data()
)

changes_df = (
    load_watchlist_changes()
)


# ============================================================
# HEADER
# ============================================================

st.title("📈 TickerTrends")

st.caption(
    "Follow the trend. Know when it changes."
)


# ============================================================
# TOP SCORES
# ============================================================

st.divider()

st.subheader(
    "Top Scores"
)


top_scores = (
    df[
        df[
            "total_score"
        ]
        .notna()
    ]
    .sort_values(
        by=[
            "total_score",
            "ticker",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .head(
        8
    )
)


display_stock_table(
    top_scores,
    key="summary_top_scores",
    height=300,
)


st.page_link(
    "pages/1_Screener.py",
    label="Open Screener",
    icon="🔎",
    use_container_width=True,
)


# ============================================================
# ACCUMULATION
# ============================================================

st.divider()

st.subheader(
    "🔵 Accumulation"
)

st.caption(
    "Strong long-term trends where momentum has cooled "
    "near the 50-day moving average."
)


accumulation_df = (
    df[
        (
            df[
                "trend_state"
            ]
            == "Accumulation"
        )
        & (
            df[
                "total_score"
            ]
            .notna()
        )
    ]
    .sort_values(
        by=[
            "total_score",
            "ticker",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .head(
        8
    )
)


if accumulation_df.empty:

    st.caption(
        "No Accumulation stocks are currently available."
    )

else:

    display_stock_table(
        accumulation_df,
        key="summary_accumulation",
        height=300,
    )


# ============================================================
# WEAKENING / BEARISH
# ============================================================

st.divider()

st.subheader(
    "⚠️ Trend Caution"
)

st.caption(
    "Highest-scoring stocks currently classified as "
    "Weakening or Bearish."
)


caution_df = (
    df[
        (
            df[
                "trend_state"
            ]
            .isin(
                [
                    "Weakening",
                    "Bearish",
                ]
            )
        )
        & (
            df[
                "total_score"
            ]
            .notna()
        )
    ]
    .sort_values(
        by=[
            "total_score",
            "ticker",
        ],
        ascending=[
            False,
            True,
        ],
    )
    .head(
        8
    )
)


if caution_df.empty:

    st.caption(
        "No Weakening or Bearish stocks are currently "
        "available."
    )

else:

    display_stock_table(
        caution_df,
        key="summary_caution",
        height=300,
    )


# ============================================================
# WATCHLIST ALERTS
# ============================================================

if not changes_df.empty:

    st.divider()

    st.subheader(
        f"🔔 Watchlist Changes ({len(changes_df)})"
    )


    for _, change in (
        changes_df.head(
            3
        )
        .iterrows()
    ):

        ticker = str(
            change[
                "ticker"
            ]
        )

        old_state = (
            change.get(
                "old_state"
            )
            or "Unknown"
        )

        new_state = (
            change.get(
                "new_state"
            )
            or "Unknown"
        )


        with st.container(
            border=True
        ):

            st.markdown(
                f"**{ticker}**"
            )

            st.write(
                f"{trend_display(old_state)} "
                f"→ {trend_display(new_state)}"
            )


    st.page_link(
        "pages/3_Watchlist.py",
        label="View Watchlist Changes",
        icon="⭐",
        use_container_width=True,
    )



# ============================================================
# WATCHLIST SUMMARY
# ============================================================

st.divider()

st.subheader(
    "⭐ Watchlist"
)


if watchlist_df.empty:

    st.caption(
        "No stocks are currently on the Watchlist."
    )

    st.page_link(
        "pages/1_Screener.py",
        label="Find Stocks",
        icon="🔎",
        use_container_width=True,
    )

else:

    watchlist_sorted = (
        watchlist_df
        .sort_values(
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
        .head(
            6
        )
    )


    display_stock_table(
        watchlist_sorted,
        key="summary_watchlist",
        height=255,
    )


    st.page_link(
        "pages/3_Watchlist.py",
        label="Open Watchlist",
        icon="⭐",
        use_container_width=True,
    )


# ============================================================
# QUICK NAVIGATION
# ============================================================

st.divider()

st.subheader(
    "Explore"
)


st.page_link(
    "pages/1_Screener.py",
    label="Screener",
    icon="🔎",
    use_container_width=True,
)


st.page_link(
    "pages/2_Markets.py",
    label="Markets",
    icon="🌎",
    use_container_width=True,
)


st.page_link(
    "pages/4_Compare.py",
    label="Compare",
    icon="⚖️",
    use_container_width=True,
)


st.page_link(
    "pages/6_Score_Guide.py",
    label="Score Guide",
    icon="📖",
    use_container_width=True,
)


# ============================================================
# FRESHNESS INDICATOR
# ============================================================

st.divider()

with st.expander(
    "Scan Status",
    expanded=False,
):

    last_scan = freshness[
        "scan"
    ]

    if last_scan:

        current = full_scan_is_current(
            last_scan
        )

        if current:

            st.success(
                "✓ Market data is current"
            )

        else:

            st.warning(
                "Market data has not been fully "
                "refreshed today."
            )


        freshness_col1, freshness_col2 = (
            st.columns(2)
        )


        with freshness_col1:

            st.metric(
                "Last Full Scan",
                format_timestamp(
                    last_scan.get(
                        "completed_at"
                    )
                ),
            )


        with freshness_col2:

            successful = (
                last_scan.get(
                    "successful",
                    0,
                )
            )

            requested = (
                last_scan.get(
                    "requested",
                    0,
                )
            )

            st.metric(
                "Updated",
                f"{successful} / {requested}",
            )


        failed = last_scan.get(
            "failed",
            0,
        )


        if failed:

            st.caption(
                f"{failed} securities could not be updated "
                f"during the last full scan."
            )


    else:

        st.warning(
            "No completed full-universe scan has been "
            "recorded yet."
        )

        latest = freshness.get(
            "latest_ticker_update"
        )

        if latest:

            st.caption(
                "Latest stored ticker update: "
                f"{format_timestamp(latest)}"
            )


    st.divider()
    st.caption(
        "A full refresh downloads current market data and recalculates "
        "technicals, fundamentals, trend states, and scores."
    )

    if st.button(
        "🔄 Refresh Market Data",
        type="primary",
        use_container_width=True,
        key="refresh_market_data",
    ):
        try:
            with st.spinner(
                "Refreshing the full TickerTrends universe. "
                "This may take several minutes..."
            ):
                refresh_result = scan_universe(
                    delay=0.50,
                    retries=1,
                    retry_delay=3.0,
                    sync_before_scan=True,
                )

            clear_summary_caches()
            st.session_state["market_refresh_message"] = (
                f"Refresh complete: {refresh_result.successful} of "
                f"{refresh_result.requested} updated; "
                f"{refresh_result.failed} failed."
            )
            st.rerun()
        except Exception as exc:
            st.error(
                "Market refresh failed: "
                f"{type(exc).__name__}: {exc}"
            )

    refresh_message = st.session_state.pop(
        "market_refresh_message",
        None,
    )
    if refresh_message:
        st.success(refresh_message)

    # ============================================================
    # NO MARKET DATA
    # ============================================================

    if df.empty:

        st.info(
            "No calculated TickerTrends data is available."
        )

        st.caption(
            "Run the universe scanner to populate "
            "tickertrends.db."
        )

        st.stop()


# ============================================================
# MARKET SNAPSHOT
# ============================================================

with st.expander(
    "Market Snapshot",
    expanded=False,
):

    total_stocks = len(
        df
    )


    complete_scores = int(
        df[
            "total_score"
        ]
        .notna()
        .sum()
    )


    strong_bullish = int(
        (
            df[
                "trend_state"
            ]
            == "Strong Bullish"
        )
        .sum()
    )


    bearish = int(
        (
            df[
                "trend_state"
            ]
            == "Bearish"
        )
        .sum()
    )


    snapshot_col1, snapshot_col2 = (
        st.columns(2)
    )


    with snapshot_col1:

        st.metric(
            "Stocks",
            total_stocks,
        )

        st.metric(
            "Strong Bullish",
            strong_bullish,
        )


    with snapshot_col2:

        st.metric(
            "Complete Scores",
            complete_scores,
        )

        st.metric(
            "Bearish",
            bearish,
        )


# ============================================================
# TREND DISTRIBUTION
# ============================================================

with st.expander(
    "Trend Distribution",
    expanded=False,
):

    trend_rows = []


    for state in TREND_ORDER:

        count = int(
            (
                df[
                    "trend_state"
                ]
                == state
            )
            .sum()
        )

        trend_rows.append(
            {
                "Trend": (
                    trend_display(
                        state
                    )
                ),

                "Stocks": count,
            }
        )


    trend_df = pd.DataFrame(
        trend_rows
    )


    st.dataframe(
        trend_df,
        hide_index=True,
        width="stretch",
        column_config={
            "Trend": (
                st.column_config.TextColumn(
                    "Trend",
                    width="medium",
                )
            ),

            "Stocks": (
                st.column_config.NumberColumn(
                    "Stocks",
                    width="small",
                )
            ),
        },
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "TickerTrends displays the latest calculated results "
    "stored in SQLite. Opening, filtering, or navigating "
    "the app does not rerun the 214-stock universe scanner."
)
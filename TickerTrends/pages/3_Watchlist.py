"""
TickerTrends Watchlist
======================

Mobile-friendly watchlist and trend-change monitor.

Architecture rule:

    This page reads SQLite only.

It does NOT:
    - call yfinance
    - calculate indicators
    - calculate scores
    - run the scanner

Trend changes are created by core.database.save_ticker_state()
when the universe scanner detects a category change.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from core.database import (
    acknowledge_all_changes,
    acknowledge_change,
    get_state_history,
    get_unacknowledged_changes,
    get_watchlist,
    remove_from_watchlist,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Watchlist | TickerTrends",
    page_icon="⭐",
    layout="wide",
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


# ============================================================
# CACHED SQLITE READS
# ============================================================

@st.cache_data(ttl=60)
def load_watchlist() -> pd.DataFrame:
    """
    Load current Watchlist data from SQLite.
    """

    rows = get_watchlist()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


@st.cache_data(ttl=30)
def load_changes() -> pd.DataFrame:
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
# HELPERS
# ============================================================

def trend_display(
    state: str | None,
) -> str:
    """
    Return compact trend text.
    """

    if not state:
        return "⚪ Unknown"

    return (
        f"{TREND_ICONS.get(state, '⚪')} "
        f"{state}"
    )


def format_score(
    value,
) -> str:
    """
    Format score values.
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
    Format RSI values.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{float(value):.1f}"


def format_timestamp(
    value: str | None,
) -> str:
    """
    Format an ISO timestamp for compact display.
    """

    if not value:
        return ""

    try:
        parsed = datetime.fromisoformat(
            value
        )

        return parsed.strftime(
            "%b %d • %I:%M %p"
        )

    except ValueError:
        return value


def change_icon(
    old_state: str | None,
    new_state: str | None,
) -> str:
    """
    Return an attention icon based on the new state.

    Red is reserved for a move into Bearish.
    Blue highlights Accumulation.
    Green highlights Strong Bullish/Bullish.
    Yellow/orange highlights Extended/Weakening.
    """

    if new_state == "Bearish":
        return "🔴"

    if new_state == "Weakening":
        return "🟠"

    if new_state == "Extended":
        return "🟡"

    if new_state == "Accumulation":
        return "🔵"

    if new_state in {
        "Strong Bullish",
        "Bullish",
    }:
        return "🟢"

    return "🔔"


def clear_watchlist_caches() -> None:
    """
    Clear Watchlist-related cached database reads.
    """

    load_watchlist.clear()
    load_changes.clear()


# ============================================================
# HEADER
# ============================================================

st.title("⭐ Watchlist")

st.caption(
    "Monitor the stocks that matter and see when "
    "their trend changes."
)


# ============================================================
# LOAD DATA
# ============================================================

watchlist_df = load_watchlist()
changes_df = load_changes()


# ============================================================
# EMPTY WATCHLIST
# ============================================================

if watchlist_df.empty:

    st.info(
        "Your Watchlist is empty."
    )

    st.caption(
        "Add stocks from the Details page to begin "
        "monitoring trend-state changes."
    )

    st.page_link(
        "pages/1_Screener.py",
        label="Browse Screener",
        icon="🔎",
        use_container_width=True,
    )

    st.stop()


# ============================================================
# CHANGE ALERTS
# ============================================================

if not changes_df.empty:

    st.subheader(
        f"🔔 New Changes ({len(changes_df)})"
    )

    st.caption(
        "These changes have occurred since the last "
        "time the alert was acknowledged."
    )

    # Global acknowledge control.
    if st.button(
        "✓ Mark All Changes Seen",
        use_container_width=True,
    ):

        acknowledge_all_changes()

        clear_watchlist_caches()

        st.rerun()


    # --------------------------------------------------------
    # CHANGE CARDS
    # --------------------------------------------------------

    for _, change in changes_df.iterrows():

        change_id = int(
            change[
                "id"
            ]
        )

        ticker = str(
            change[
                "ticker"
            ]
        )

        old_state = (
            change.get(
                "old_state"
            )
        )

        new_state = (
            change.get(
                "new_state"
            )
        )

        icon = change_icon(
            old_state,
            new_state,
        )

        changed_at = (
            format_timestamp(
                change.get(
                    "changed_at"
                )
            )
        )

        company_name = (
            change.get(
                "company_name"
            )
            or ticker
        )

        with st.container(
            border=True
        ):

            st.markdown(
                f"### {icon} {ticker}"
            )

            if company_name != ticker:

                st.caption(
                    company_name
                )

            st.markdown(
                f"**{old_state or 'Unknown'} "
                f"→ {new_state or 'Unknown'}**"
            )

            if changed_at:

                st.caption(
                    changed_at
                )

            button_col1, button_col2 = (
                st.columns(2)
            )

            with button_col1:

                if st.button(
                    "View Details",
                    key=(
                        f"change_details_"
                        f"{change_id}"
                    ),
                    use_container_width=True,
                ):

                    st.session_state[
                        "selected_ticker"
                    ] = ticker

                    st.switch_page(
                        "pages/5_Details.py"
                    )

            with button_col2:

                if st.button(
                    "✓ Seen",
                    key=(
                        f"ack_change_"
                        f"{change_id}"
                    ),
                    use_container_width=True,
                ):

                    acknowledge_change(
                        change_id
                    )

                    clear_watchlist_caches()

                    st.rerun()


    st.divider()


# ============================================================
# WATCHLIST SUMMARY
# ============================================================

st.subheader(
    "My Stocks"
)


watchlist_count = len(
    watchlist_df
)


change_count = (
    len(changes_df)
    if not changes_df.empty
    else 0
)


summary_col1, summary_col2 = (
    st.columns(2)
)


with summary_col1:

    st.metric(
        "Watchlist",
        watchlist_count,
    )


with summary_col2:

    st.metric(
        "New Changes",
        change_count,
    )


# ============================================================
# PREPARE WATCHLIST TABLE
# ============================================================

display = watchlist_df.copy()


display["trend_display"] = (
    display[
        "trend_state"
    ].apply(
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


# ------------------------------------------------------------
# FLAG TICKERS WITH UNSEEN CHANGES
# ------------------------------------------------------------

if changes_df.empty:

    changed_tickers: set[str] = set()

else:

    changed_tickers = set(
        changes_df[
            "ticker"
        ]
        .dropna()
        .astype(str)
        .tolist()
    )


def ticker_with_alert(
    ticker: str,
) -> str:
    """
    Add an alert indicator for a ticker with an
    unacknowledged state change.
    """

    if ticker in changed_tickers:
        return f"🔔 {ticker}"

    return ticker


display["ticker_display"] = (
    display[
        "ticker"
    ].apply(
        ticker_with_alert
    )
)


# ------------------------------------------------------------
# SORT SCORE DESCENDING
# ------------------------------------------------------------

display = display.sort_values(
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


# Preserve ticker order before renaming.
ticker_lookup = (
    display[
        "ticker"
    ]
    .reset_index(
        drop=True
    )
)


# ------------------------------------------------------------
# MOBILE TABLE
# ------------------------------------------------------------

display = display[
    [
        "ticker_display",
        "trend_display",
        "total_score",
        "rsi_14",
    ]
].copy()


display.rename(
    columns={
        "ticker_display": "Ticker",
        "trend_display": "Trend",
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
# WATCHLIST TABLE
# ============================================================

selection = st.dataframe(
    display,
    hide_index=True,
    width="stretch",
    height=480,
    on_select="rerun",
    selection_mode="single-row",
    key="tickertrends_watchlist",
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
# SELECTED STOCK
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
        watchlist_df[
            watchlist_df[
                "ticker"
            ]
            == selected_ticker
        ]
        .iloc[0]
    )


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
            selected_record.get(
                "trend_state"
            )
        )
    )


    score = selected_record.get(
        "total_score"
    )

    rsi = selected_record.get(
        "rsi_14"
    )


    metric_col1, metric_col2 = (
        st.columns(2)
    )


    with metric_col1:

        st.metric(
            "Score",
            format_score(
                score
            ),
        )


    with metric_col2:

        st.metric(
            "RSI",
            format_rsi(
                rsi
            ),
        )


    # --------------------------------------------------------
    # ACTIONS
    # --------------------------------------------------------

    detail_col, remove_col = (
        st.columns(2)
    )


    with detail_col:

        if st.button(
            "View Details",
            key=(
                f"watchlist_details_"
                f"{selected_ticker}"
            ),
            type="primary",
            use_container_width=True,
        ):

            st.switch_page(
                "pages/5_Details.py"
            )


    with remove_col:

        if st.button(
            "Remove",
            key=(
                f"watchlist_remove_"
                f"{selected_ticker}"
            ),
            use_container_width=True,
        ):

            remove_from_watchlist(
                selected_ticker
            )

            clear_watchlist_caches()

            st.rerun()


# ============================================================
# CHANGE HISTORY
# ============================================================

with st.expander(
    "Recent Trend History",
    expanded=False,
):

    history = get_state_history(
        limit=25
    )


    if not history:

        st.caption(
            "No trend-state changes have been "
            "recorded yet."
        )

    else:

        # Only display Watchlist symbols.
        watchlist_tickers = set(
            watchlist_df[
                "ticker"
            ]
            .astype(str)
            .tolist()
        )


        history_rows = [
            row
            for row in history
            if row.get(
                "ticker"
            )
            in watchlist_tickers
        ]


        if not history_rows:

            st.caption(
                "No trend-state changes have been "
                "recorded for current Watchlist stocks."
            )

        else:

            history_df = (
                pd.DataFrame(
                    history_rows
                )
            )


            history_df[
                "Change"
            ] = (
                history_df[
                    "old_state"
                ].fillna(
                    "Unknown"
                )
                + " → "
                + history_df[
                    "new_state"
                ].fillna(
                    "Unknown"
                )
            )


            history_df[
                "When"
            ] = (
                history_df[
                    "changed_at"
                ]
                .apply(
                    format_timestamp
                )
            )


            history_display = (
                history_df[
                    [
                        "ticker",
                        "Change",
                        "When",
                    ]
                ]
                .rename(
                    columns={
                        "ticker": "Ticker",
                    }
                )
            )


            st.dataframe(
                history_display,
                hide_index=True,
                width="stretch",
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Watchlist alerts are created when the TickerTrends "
    "scanner detects a change in trend state. Opening this "
    "page does not download market data."
)
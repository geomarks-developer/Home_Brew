"""
TickerTrends Compare
====================

Mobile-friendly comparison page for 2 or 3 stocks.

Architecture rule:

    Compare reads existing calculated results from SQLite.

It does NOT:
    - call yfinance
    - recalculate technicals
    - recalculate fundamentals
    - run the universe scanner

Comparison focuses only on the metrics that define
TickerTrends:

    Overall Score
    Trend State

    Technical
        Technical Score
        RSI
        Price vs 50D
        Price vs 200D
        200D slope

    Fundamental
        Fundamental Score
        P/E
        PEG
        FCF Margin
        Relative Performance
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from core.database import (
    get_all_ticker_states,
)
from core.scoring import (
    calculate_fundamental_score,
    calculate_technical_score,
    get_score_label,
)
from core.trend_state import format_state


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Compare | TickerTrends",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# ============================================================
# CONSTANTS
# ============================================================

STATE_COLORS = {
    "Strong Bullish": "#22c55e",
    "Bullish": "#4ade80",
    "Accumulation": "#3b82f6",
    "Extended": "#eab308",
    "Weakening": "#f97316",
    "Bearish": "#ef4444",
}


# ============================================================
# CACHED SQLITE DATA
# ============================================================

@st.cache_data(ttl=300)
def load_compare_data() -> pd.DataFrame:
    """
    Load current TickerTrends results from SQLite.

    No external market-data requests are made.
    """

    rows = get_all_ticker_states()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        rows
    )


# ============================================================
# FORMATTERS
# ============================================================

def format_number(
    value,
    decimals: int = 1,
) -> str:
    """
    Format general numeric data.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return (
        f"{float(value):.{decimals}f}"
    )


def format_score(
    value,
    maximum: int | None = None,
) -> str:
    """
    Format a score.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    if maximum is None:

        return (
            f"{float(value):.1f}"
        )

    return (
        f"{float(value):.1f} / {maximum}"
    )


def format_percent(
    value,
    decimals: int = 1,
) -> str:
    """
    Format signed percentage data.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return (
        f"{float(value):+.{decimals}f}%"
    )


def format_money(
    value,
) -> str:
    """
    Format a stock price.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return (
        f"${float(value):,.2f}"
    )


# ============================================================
# SNAPSHOT HELPERS
# ============================================================

def row_to_technicals(
    row: pd.Series,
) -> dict[str, Any]:
    """
    Convert one database row into the technical dictionary
    expected by scoring.py.
    """

    return {
        "ticker": row.get(
            "ticker"
        ),

        "price": row.get(
            "price"
        ),

        "sma_50": row.get(
            "sma_50"
        ),

        "sma_200": row.get(
            "sma_200"
        ),

        "sma_200_slope": row.get(
            "sma_200_slope"
        ),

        "pct_from_sma50": row.get(
            "pct_from_sma50"
        ),

        "pct_from_sma200": row.get(
            "pct_from_sma200"
        ),

        "rsi_14": row.get(
            "rsi_14"
        ),
    }


def row_to_fundamentals(
    row: pd.Series,
) -> dict[str, Any]:
    """
    Convert one database row into the fundamental
    dictionary expected by scoring.py.
    """

    return {
        "ticker": row.get(
            "ticker"
        ),

        "pe_ratio": row.get(
            "pe_ratio"
        ),

        "peg_ratio": row.get(
            "peg_ratio"
        ),

        "fcf_margin": row.get(
            "fcf_metric"
        ),

        "relative_performance": (
            row.get(
                "relative_performance"
            )
        ),
    }


# ============================================================
# LOAD DATA
# ============================================================

df = load_compare_data()


if df.empty:

    st.info(
        "No TickerTrends scan data is available."
    )

    st.stop()


# Compare only tickers with calculated states.

available_tickers = sorted(
    df[
        "ticker"
    ]
    .dropna()
    .astype(str)
    .unique()
    .tolist()
)


if len(
    available_tickers
) < 2:

    st.warning(
        "At least two calculated stocks are required "
        "for comparison."
    )

    st.stop()


# ============================================================
# DEFAULT TICKERS
# ============================================================

def choose_default(
    preferred: str,
    fallback_index: int,
) -> str:
    """
    Use a familiar preferred symbol when available.
    """

    if preferred in available_tickers:
        return preferred

    fallback_index = min(
        fallback_index,
        len(
            available_tickers
        ) - 1,
    )

    return available_tickers[
        fallback_index
    ]


default_1 = choose_default(
    "MSFT",
    0,
)

default_2 = choose_default(
    "AAPL",
    1,
)

default_3 = choose_default(
    "NVDA",
    2,
)


# ============================================================
# HEADER
# ============================================================

st.title(
    "⚖️ Compare"
)

st.caption(
    "Compare trend, technical condition, "
    "fundamentals, and score."
)


# ============================================================
# STOCK SELECTION
# ============================================================

ticker_1 = st.selectbox(
    "Stock 1",
    available_tickers,
    index=available_tickers.index(
        default_1
    ),
)


ticker_2_options = [
    ticker
    for ticker in available_tickers
    if ticker != ticker_1
]


if (
    default_2
    not in ticker_2_options
):

    default_2 = ticker_2_options[
        0
    ]


ticker_2 = st.selectbox(
    "Stock 2",
    ticker_2_options,
    index=ticker_2_options.index(
        default_2
    ),
)


add_third = st.toggle(
    "Compare a third stock",
    value=False,
)


ticker_3 = None


if add_third:

    ticker_3_options = [
        ticker
        for ticker in available_tickers
        if ticker
        not in {
            ticker_1,
            ticker_2,
        }
    ]


    if ticker_3_options:

        if (
            default_3
            not in ticker_3_options
        ):

            default_3 = (
                ticker_3_options[
                    0
                ]
            )


        ticker_3 = st.selectbox(
            "Stock 3",
            ticker_3_options,
            index=ticker_3_options.index(
                default_3
            ),
        )


selected_tickers = [
    ticker_1,
    ticker_2,
]


if ticker_3:

    selected_tickers.append(
        ticker_3
    )


# ============================================================
# SELECT RECORDS
# ============================================================

records: dict[
    str,
    pd.Series,
] = {}


for ticker in selected_tickers:

    matching = df[
        df[
            "ticker"
        ]
        == ticker
    ]

    if matching.empty:
        continue

    records[
        ticker
    ] = matching.iloc[
        0
    ]


if len(
    records
) < 2:

    st.warning(
        "Unable to load enough stocks for comparison."
    )

    st.stop()


# ============================================================
# STOCK SUMMARY CARDS
# ============================================================

st.subheader(
    "Overview"
)


for ticker in selected_tickers:

    row = records[
        ticker
    ]

    company = (
        row.get(
            "company_name"
        )
        or ticker
    )

    state = row.get(
        "trend_state"
    )

    color = STATE_COLORS.get(
        state,
        "#94a3b8",
    )

    total_score = (
        row.get(
            "total_score"
        )
    )

    grade, label = (
        get_score_label(
            total_score
        )
    )


    with st.container(
        border=True
    ):

        header_col1, header_col2 = (
            st.columns(2)
        )


        with header_col1:

            st.markdown(
                f"### {ticker}"
            )

            st.caption(
                company
            )


        with header_col2:

            st.metric(
                "Score",
                format_score(
                    total_score
                ),
            )


        trend_text = (
            format_state(
                state
            )
            if state
            else "⚪ Unknown"
        )


        st.markdown(
            f"""
            <div style="
                border-left: 4px solid {color};
                padding: 0.55rem 0.75rem;
                border-radius: 0.30rem;
                background: rgba(128,128,128,0.07);
                margin-bottom: 0.5rem;
                font-weight: 600;
            ">
                {trend_text}
            </div>
            """,
            unsafe_allow_html=True,
        )


        metric_col1, metric_col2 = (
            st.columns(2)
        )


        with metric_col1:

            st.metric(
                "Technical",
                format_score(
                    row.get(
                        "technical_score"
                    ),
                    60,
                ),
            )


        with metric_col2:

            st.metric(
                "Fundamental",
                format_score(
                    row.get(
                        "fundamental_score"
                    ),
                    40,
                ),
            )


        st.caption(
            (
                f"{grade} • {label}"
                if total_score
                is not None
                else
                "Insufficient Data"
            )
        )


        if st.button(
            "View Details",
            key=(
                f"compare_details_"
                f"{ticker}"
            ),
            use_container_width=True,
        ):

            st.session_state[
                "selected_ticker"
            ] = ticker

            st.switch_page(
                "pages/5_Details.py"
            )


# ============================================================
# TECHNICAL COMPARISON
# ============================================================

st.subheader(
    "Technical Comparison"
)


technical_rows: list[
    dict[str, Any]
] = []


for ticker in selected_tickers:

    row = records[
        ticker
    ]

    technical_rows.append(
        {
            "Metric": ticker,

            "Price": (
                row.get(
                    "price"
                )
            ),

            "RSI": (
                row.get(
                    "rsi_14"
                )
            ),

            "vs 50D": (
                row.get(
                    "pct_from_sma50"
                )
            ),

            "vs 200D": (
                row.get(
                    "pct_from_sma200"
                )
            ),

            "200D Slope": (
                row.get(
                    "sma_200_slope"
                )
            ),

            "Technical": (
                row.get(
                    "technical_score"
                )
            ),
        }
    )


technical_df = (
    pd.DataFrame(
        technical_rows
    )
)


st.dataframe(
    technical_df,
    hide_index=True,
    width="stretch",
    column_config={
        "Metric": st.column_config.TextColumn(
            "Ticker",
            width="small",
        ),

        "Price": st.column_config.NumberColumn(
            "Price",
            format="$%.2f",
            width="small",
        ),

        "RSI": st.column_config.NumberColumn(
            "RSI",
            format="%.1f",
            width="small",
        ),

        "vs 50D": st.column_config.NumberColumn(
            "vs 50D",
            format="%+.1f%%",
            width="small",
        ),

        "vs 200D": st.column_config.NumberColumn(
            "vs 200D",
            format="%+.1f%%",
            width="small",
        ),

        "200D Slope": st.column_config.NumberColumn(
            "200D Slope",
            format="%+.2f%%",
            width="small",
        ),

        "Technical": st.column_config.NumberColumn(
            "Technical",
            format="%.1f",
            width="small",
        ),
    },
)


# ============================================================
# FUNDAMENTAL COMPARISON
# ============================================================

st.subheader(
    "Fundamental Comparison"
)


fundamental_rows: list[
    dict[str, Any]
] = []


for ticker in selected_tickers:

    row = records[
        ticker
    ]

    fundamental_rows.append(
        {
            "Metric": ticker,

            "P/E": (
                row.get(
                    "pe_ratio"
                )
            ),

            "PEG": (
                row.get(
                    "peg_ratio"
                )
            ),

            "FCF Margin": (
                row.get(
                    "fcf_metric"
                )
            ),

            "Relative Perf": (
                row.get(
                    "relative_performance"
                )
            ),

            "Fundamental": (
                row.get(
                    "fundamental_score"
                )
            ),
        }
    )


fundamental_df = (
    pd.DataFrame(
        fundamental_rows
    )
)


st.dataframe(
    fundamental_df,
    hide_index=True,
    width="stretch",
    column_config={
        "Metric": st.column_config.TextColumn(
            "Ticker",
            width="small",
        ),

        "P/E": st.column_config.NumberColumn(
            "P/E",
            format="%.2f",
            width="small",
        ),

        "PEG": st.column_config.NumberColumn(
            "PEG",
            format="%.2f",
            width="small",
        ),

        "FCF Margin": st.column_config.NumberColumn(
            "FCF Margin",
            format="%+.1f%%",
            width="small",
        ),

        "Relative Perf": st.column_config.NumberColumn(
            "Relative",
            format="%+.1f%%",
            width="small",
        ),

        "Fundamental": st.column_config.NumberColumn(
            "Fundamental",
            format="%.1f",
            width="small",
        ),
    },
)


# ============================================================
# COMPONENT SCORE COMPARISON
# ============================================================

with st.expander(
    "Score Components",
    expanded=False,
):

    for ticker in selected_tickers:

        row = records[
            ticker
        ]


        technical_snapshot = (
            row_to_technicals(
                row
            )
        )


        fundamental_snapshot = (
            row_to_fundamentals(
                row
            )
        )


        technical_result = (
            calculate_technical_score(
                technical_snapshot
            )
        )


        fundamental_result = (
            calculate_fundamental_score(
                fundamental_snapshot
            )
        )


        st.markdown(
            f"### {ticker}"
        )


        st.markdown(
            "**Technical**"
        )


        for component in technical_result[
            "components"
        ]:

            points = (
                f"{component.points:.1f}"
                if component.points
                is not None
                else "N/A"
            )

            st.caption(
                f"{component.name}: "
                f"{points} / "
                f"{component.max_points:.0f} "
                f"• {component.label}"
            )


        st.markdown(
            "**Fundamentals**"
        )


        for component in fundamental_result[
            "components"
        ]:

            points = (
                f"{component.points:.1f}"
                if component.points
                is not None
                else "N/A"
            )

            st.caption(
                f"{component.name}: "
                f"{points} / "
                f"{component.max_points:.0f} "
                f"• {component.label}"
            )


        st.divider()



# ============================================================
# QUICK TAKE
# ============================================================

st.subheader(
    "At a Glance"
)


# ------------------------------------------------------------
# BUILD COMPARISON RECORDS
# ------------------------------------------------------------

scored_records = []

technical_records = []

fundamental_records = []


for ticker in selected_tickers:

    row = records[
        ticker
    ]

    total_score = row.get(
        "total_score"
    )

    technical_score = row.get(
        "technical_score"
    )

    fundamental_score = row.get(
        "fundamental_score"
    )


    if (
        total_score is not None
        and not pd.isna(total_score)
    ):

        scored_records.append(
            (
                ticker,
                float(total_score),
            )
        )


    if (
        technical_score is not None
        and not pd.isna(technical_score)
    ):

        technical_records.append(
            (
                ticker,
                float(technical_score),
            )
        )


    if (
        fundamental_score is not None
        and not pd.isna(fundamental_score)
    ):

        fundamental_records.append(
            (
                ticker,
                float(fundamental_score),
            )
        )


# ------------------------------------------------------------
# HIGHEST OVERALL SCORE
# ------------------------------------------------------------

if scored_records:

    highest_total = max(
        scored_records,
        key=lambda item: item[1],
    )

    st.write(
        f"**Highest overall score:** "
        f"{highest_total[0]} "
        f"({highest_total[1]:.1f})"
    )


# ------------------------------------------------------------
# STRONGEST TECHNICAL SCORE
# ------------------------------------------------------------

if technical_records:

    strongest_technical = max(
        technical_records,
        key=lambda item: item[1],
    )

    st.write(
        f"**Strongest technical score:** "
        f"{strongest_technical[00]} "
        f"({strongest_technical[1]:.1f}/60)"
    )


# ------------------------------------------------------------
# STRONGEST FUNDAMENTAL SCORE
# ------------------------------------------------------------

if fundamental_records:

    strongest_fundamental = max(
        fundamental_records,
        key=lambda item: item[1],
    )

    st.write(
        f"**Strongest fundamental score:** "
        f"{strongest_fundamental[0]} "
        f"({strongest_fundamental[1]:.1f}/40)"
    )
# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Compare uses the most recent TickerTrends results "
    "stored in SQLite. Changing stocks does not download "
    "market data or rerun the universe scanner."
)
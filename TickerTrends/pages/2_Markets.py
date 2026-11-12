"""
TickerTrends Markets
====================

Simple market-trend dashboard.

Markets tracked:
    - S&P 500
    - NASDAQ-100
    - Dow 30
    - Russell 2000

Purpose:
    Show the broader market environment using the same
    technical philosophy as TickerTrends:

        50-day SMA
        200-day SMA
        200-day slope
        RSI-14
        Trend state

Market data is cached to avoid repeated downloads.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from core.technicals import (
    calculate_technicals_from_history,
    get_chart_data,
)
from core.trend_state import (
    determine_trend_state,
    format_state,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Markets | TickerTrends",
    page_icon="🌎",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ============================================================
# MARKET DEFINITIONS
# ============================================================

MARKETS = {
    "S&P 500": {
        "ticker": "^GSPC",
        "short": "S&P 500",
    },

    "NASDAQ-100": {
        "ticker": "^NDX",
        "short": "NASDAQ-100",
    },

    "Dow 30": {
        "ticker": "^DJI",
        "short": "Dow 30",
    },

    "Russell 2000": {
        "ticker": "^RUT",
        "short": "Russell 2000",
    },
}


STATE_ICONS = {
    "Strong Bullish": "🟢",
    "Bullish": "🟢",
    "Accumulation": "🔵",
    "Extended": "🟡",
    "Weakening": "🟠",
    "Bearish": "🔴",
}


STATE_COLORS = {
    "Strong Bullish": "#22c55e",
    "Bullish": "#4ade80",
    "Accumulation": "#3b82f6",
    "Extended": "#eab308",
    "Weakening": "#f97316",
    "Bearish": "#ef4444",
}


# ============================================================
# CACHED MARKET DATA
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def load_market_history(
    ticker: str,
    period: str = "2y",
) -> pd.DataFrame:
    """
    Load market history with TickerTrends indicators.

    Cached for 30 minutes.
    """

    return get_chart_data(
        ticker=ticker,
        period=period,
    )


@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def load_market_snapshot(
    ticker: str,
) -> dict[str, Any] | None:
    """
    Calculate the current technical snapshot for one
    market index.

    Cached for 30 minutes.
    """

    history = load_market_history(
        ticker=ticker,
        period="2y",
    )

    if history.empty:
        return None

    return calculate_technicals_from_history(
        ticker=ticker,
        data=history,
    )


# ============================================================
# FORMATTERS
# ============================================================

def format_number(
    value,
    decimals: int = 1,
) -> str:
    """
    Format numeric values.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{value:.{decimals}f}"


def format_percent(
    value,
    decimals: int = 1,
) -> str:
    """
    Format signed percentage values.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return (
        f"{value:+.{decimals}f}%"
    )


def format_price(
    value,
) -> str:
    """
    Format index level.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{value:,.2f}"


# ============================================================
# LOAD ALL MARKET SNAPSHOTS
# ============================================================

def get_market_rows() -> list[dict[str, Any]]:
    """
    Build the four-market summary.
    """

    results: list[
        dict[str, Any]
    ] = []

    for name, info in MARKETS.items():

        ticker = info[
            "ticker"
        ]

        snapshot = (
            load_market_snapshot(
                ticker
            )
        )

        if snapshot is None:

            results.append(
                {
                    "Market": name,
                    "ticker": ticker,
                    "Trend": "⚪ Unavailable",
                    "trend_state": None,
                    "RSI": None,
                    "50D": None,
                    "200D": None,
                    "price": None,
                    "pct_from_sma50": None,
                    "pct_from_sma200": None,
                    "sma_200_slope": None,
                }
            )

            continue

        trend = determine_trend_state(
            snapshot
        )

        state = (
            trend.state
            if trend
            else None
        )

        results.append(
            {
                "Market": name,

                "ticker": ticker,

                "Trend": (
                    format_state(state)
                    if state
                    else "⚪ Unknown"
                ),

                "trend_state": state,

                "RSI": snapshot.get(
                    "rsi_14"
                ),

                "50D": snapshot.get(
                    "sma_50"
                ),

                "200D": snapshot.get(
                    "sma_200"
                ),

                "price": snapshot.get(
                    "price"
                ),

                "pct_from_sma50": (
                    snapshot.get(
                        "pct_from_sma50"
                    )
                ),

                "pct_from_sma200": (
                    snapshot.get(
                        "pct_from_sma200"
                    )
                ),

                "sma_200_slope": (
                    snapshot.get(
                        "sma_200_slope"
                    )
                ),
            }
        )

    return results


# ============================================================
# CHART
# ============================================================

def create_market_chart(
    market_name: str,
    history: pd.DataFrame,
) -> go.Figure:
    """
    Build a compact price / 50D / 200D market chart.
    """

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=history.index,
            y=history["Close"],
            name="Price",
            mode="lines",
            line={
                "color": "#60a5fa",
                "width": 2.2,
            },
            hovertemplate=(
                "%{x|%b %d, %Y}"
                "<br>Price: %{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )

    if "SMA_50" in history.columns:

        figure.add_trace(
            go.Scatter(
                x=history.index,
                y=history["SMA_50"],
                name="50D",
                mode="lines",
                line={
                    "color": "#f59e0b",
                    "width": 1.6,
                },
                hovertemplate=(
                    "%{x|%b %d, %Y}"
                    "<br>50D: %{y:,.2f}"
                    "<extra></extra>"
                ),
            )
        )

    if "SMA_200" in history.columns:

        figure.add_trace(
            go.Scatter(
                x=history.index,
                y=history["SMA_200"],
                name="200D",
                mode="lines",
                line={
                    "color": "#ef4444",
                    "width": 1.8,
                },
                hovertemplate=(
                    "%{x|%b %d, %Y}"
                    "<br>200D: %{y:,.2f}"
                    "<extra></extra>"
                ),
            )
        )

    figure.update_layout(
        title={
            "text": market_name,
            "x": 0.01,
            "xanchor": "left",
        },

        height=430,

        margin={
            "l": 8,
            "r": 8,
            "t": 60,
            "b": 10,
        },

        hovermode="x unified",

        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.02,
            "xanchor": "left",
            "x": 0,
        },

        template="plotly_dark",
    )

    figure.update_xaxes(
        rangeslider_visible=False
    )

    return figure

# ============================================================
# NAVIGATION
# ============================================================

if st.button(
    "🏠 Home",
    key="home_button",
    use_container_width=False,
):
    st.switch_page("summary.py")


# ============================================================
# HEADER
# ============================================================

st.title("🌎 Markets")

st.caption(
    "The broader trend environment for TickerTrends."
)


# ============================================================
# LOAD DATA
# ============================================================

with st.spinner(
    "Loading market trends..."
):

    market_rows = get_market_rows()


market_df = pd.DataFrame(
    market_rows
)


# ============================================================
# MARKET SUMMARY
# ============================================================

st.subheader(
    "Market Overview"
)


# Create one stacked block per market rather than four
# permanent columns so the layout remains easy to use
# on narrow screens.

for _, row in market_df.iterrows():

    state = row[
        "trend_state"
    ]

    color = STATE_COLORS.get(
        state,
        "#94a3b8",
    )

    with st.container(
        border=True
    ):

        header_col1, header_col2 = (
            st.columns(2)
        )

        with header_col1:

            st.markdown(
                f"### {row['Market']}"
            )

            st.write(
                row[
                    "Trend"
                ]
            )

        with header_col2:

            st.metric(
                "RSI",
                format_number(
                    row[
                        "RSI"
                    ],
                    1,
                ),
            )

        metric_col1, metric_col2 = (
            st.columns(2)
        )

        with metric_col1:

            st.metric(
                "vs 50D",
                format_percent(
                    row[
                        "pct_from_sma50"
                    ],
                    1,
                ),
            )

        with metric_col2:

            st.metric(
                "vs 200D",
                format_percent(
                    row[
                        "pct_from_sma200"
                    ],
                    1,
                ),
            )

        if state:

            st.markdown(
                f"""
                <div style="
                    height: 4px;
                    background: {color};
                    border-radius: 2px;
                    margin-top: 0.25rem;
                "></div>
                """,
                unsafe_allow_html=True,
            )


# ============================================================
# SELECT MARKET
# ============================================================

st.subheader(
    "Market Detail"
)


selected_market = st.selectbox(
    "Market",
    options=list(
        MARKETS.keys()
    ),
)


selected_info = MARKETS[
    selected_market
]


selected_ticker = (
    selected_info[
        "ticker"
    ]
)


selected_row = (
    market_df[
        market_df[
            "Market"
        ]
        == selected_market
    ]
    .iloc[0]
)


# ============================================================
# SELECTED MARKET CONDITION
# ============================================================

state = selected_row[
    "trend_state"
]


state_color = (
    STATE_COLORS.get(
        state,
        "#94a3b8",
    )
)


st.markdown(
    f"""
    <div style="
        border-left: 5px solid {state_color};
        padding: 0.70rem 0.90rem;
        margin: 0.25rem 0 0.75rem 0;
        border-radius: 0.35rem;
        background: rgba(128, 128, 128, 0.08);
        font-weight: 600;
    ">
        {selected_row['Trend']}
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# KEY METRICS
# ============================================================

metric_col1, metric_col2 = (
    st.columns(2)
)


with metric_col1:

    st.metric(
        "Index",
        format_price(
            selected_row[
                "price"
            ]
        ),
    )

    st.metric(
        "50-Day SMA",
        format_price(
            selected_row[
                "50D"
            ]
        ),
        delta=format_percent(
            selected_row[
                "pct_from_sma50"
            ],
            1,
        ),
    )


with metric_col2:

    st.metric(
        "RSI-14",
        format_number(
            selected_row[
                "RSI"
            ],
            1,
        ),
    )

    st.metric(
        "200-Day SMA",
        format_price(
            selected_row[
                "200D"
            ]
        ),
        delta=format_percent(
            selected_row[
                "pct_from_sma200"
            ],
            1,
        ),
    )


st.caption(
    "200D slope: "
    f"{format_percent(selected_row['sma_200_slope'], 2)}"
)


# ============================================================
# CHART RANGE
# ============================================================

chart_period = st.segmented_control(
    "Chart Range",
    options=[
        "6mo",
        "1y",
        "2y",
    ],
    default="1y",
    selection_mode="single",
)


if chart_period is None:

    chart_period = "1y"


# ============================================================
# MARKET CHART
# ============================================================

with st.spinner(
    f"Loading {selected_market} chart..."
):

    history = load_market_history(
        ticker=selected_ticker,
        period=chart_period,
    )


if history.empty:

    st.info(
        "Market chart data is currently unavailable."
    )

else:

    figure = create_market_chart(
        market_name=selected_market,
        history=history,
    )

    st.plotly_chart(
        figure,
        width="stretch",
        config={
            "displaylogo": False,
            "responsive": True,
        },
    )


# ============================================================
# TREND EXPLANATION
# ============================================================

snapshot = load_market_snapshot(
    selected_ticker
)


if snapshot:

    trend = determine_trend_state(
        snapshot
    )

    if trend:

        with st.expander(
            "Why this trend?",
            expanded=False,
        ):

            st.write(
                trend.reason
            )

            st.write(
                "**Price above 50D:** "
                + (
                    "Yes"
                    if trend.price_above_50
                    else "No"
                )
            )

            st.write(
                "**Price above 200D:** "
                + (
                    "Yes"
                    if trend.price_above_200
                    else "No"
                )
            )

            st.write(
                "**50D above 200D:** "
                + (
                    "Yes"
                    if trend.sma50_above_200
                    else "No"
                )
            )

            st.write(
                "**200D rising:** "
                + (
                    "Yes"
                    if trend.sma200_rising
                    else "No"
                )
            )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Market index data is cached for 30 minutes. "
    "Opening or filtering this page does not rerun "
    "the 214-stock TickerTrends scanner."
)
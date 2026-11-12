"""
TickerTrends Details
====================

Mobile-friendly detail page for one ticker.

Architecture:

    SQLite
        -> current indicators
        -> current scores
        -> trend state
        -> company information

    Cached historical download
        -> price chart
        -> 50-day SMA
        -> 200-day SMA
        -> RSI chart

Opening this page does not rescan the full universe.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from core.database import (
    add_to_watchlist,
    get_all_ticker_states,
    get_ticker_state,
    get_ticker,
    is_in_watchlist,
    remove_from_watchlist,
)
from core.scoring import (
    calculate_fundamental_score,
    calculate_technical_score,
    get_score_label,
)
from core.technicals import get_chart_data
from core.trend_state import (
    determine_trend_state,
    format_state,
)
from core.universe import get_memberships


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Details | TickerTrends",
    page_icon="📈",
    layout="centered",
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
# CACHED SQLITE READS
# ============================================================

@st.cache_data(ttl=300)
def load_ticker_states() -> pd.DataFrame:
    """
    Load all currently calculated ticker states.

    This reads SQLite only.
    """

    rows = get_all_ticker_states()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def load_ticker_snapshot(
    ticker: str,
) -> dict[str, Any] | None:
    """
    Load one calculated ticker state from SQLite.
    """

    return get_ticker_state(
        ticker
    )


@st.cache_data(ttl=300)
def load_ticker_master(
    ticker: str,
) -> dict[str, Any] | None:
    """
    Load company and universe information from SQLite.
    """

    return get_ticker(
        ticker
    )


# ============================================================
# CACHED CHART DATA
# ============================================================

@st.cache_data(
    ttl=1800,
    show_spinner=False,
)
def load_chart_data(
    ticker: str,
    period: str,
) -> pd.DataFrame:
    """
    Download and calculate historical chart data.

    This is the only external market-data request on
    the Details page.

    Results are cached for 30 minutes.
    """

    return get_chart_data(
        ticker=ticker,
        period=period,
    )


# ============================================================
# NUMBER FORMATTERS
# ============================================================

def format_money(
    value: float | None,
) -> str:
    """
    Format a price or monetary value.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"${value:,.2f}"


def format_large_money(
    value: float | None,
) -> str:
    """
    Format large monetary values.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    absolute = abs(
        value
    )

    if absolute >= 1_000_000_000_000:
        return (
            f"${value / 1_000_000_000_000:.2f}T"
        )

    if absolute >= 1_000_000_000:
        return (
            f"${value / 1_000_000_000:.2f}B"
        )

    if absolute >= 1_000_000:
        return (
            f"${value / 1_000_000:.2f}M"
        )

    return f"${value:,.0f}"


def format_number(
    value: float | None,
    decimals: int = 1,
) -> str:
    """
    Format a general number.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return f"{value:.{decimals}f}"


def format_percent(
    value: float | None,
    decimals: int = 1,
) -> str:
    """
    Format a signed percentage.
    """

    if value is None:
        return "N/A"

    if pd.isna(value):
        return "N/A"

    return (
        f"{value:+.{decimals}f}%"
    )


# ============================================================
# FUNDAMENTAL STATUS
# ============================================================

def fundamental_color(
    points: float | None,
    max_points: float,
) -> str:
    """
    Return a visual status color based on component points.
    """

    if points is None:
        return "#94a3b8"

    ratio = (
        points / max_points
        if max_points
        else 0
    )

    if ratio >= 0.75:
        return "#22c55e"

    if ratio >= 0.50:
        return "#eab308"

    return "#ef4444"


def status_icon(
    points: float | None,
    max_points: float,
) -> str:
    """
    Return a compact score-status icon.
    """

    if points is None:
        return "⚪"

    ratio = (
        points / max_points
        if max_points
        else 0
    )

    if ratio >= 0.75:
        return "🟢"

    if ratio >= 0.50:
        return "🟡"

    return "🔴"


# ============================================================
# SNAPSHOT CONVERSION
# ============================================================

def build_technical_snapshot(
    row: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert the SQLite row into the dictionary expected
    by scoring.py and trend_state.py.
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


def build_fundamental_snapshot(
    row: dict[str, Any],
) -> dict[str, Any]:
    """
    Convert the SQLite row into the dictionary expected
    by scoring.py.
    """

    return {
        "ticker": row.get(
            "ticker"
        ),

        "pe_ratio": row.get(
            "pe_ratio"
        ),

        # The current database schema doesn't store whether
        # P/E came from trailing or forward data.
        "pe_source": None,

        "peg_ratio": row.get(
            "peg_ratio"
        ),

        "free_cash_flow": row.get(
            "free_cash_flow"
        ),

        # TickerTrends stores FCF margin in fcf_metric.
        "fcf_margin": row.get(
            "fcf_metric"
        ),

        "relative_performance": row.get(
            "relative_performance"
        ),
    }


# ============================================================
# CHART CREATION
# ============================================================

def create_price_chart(
    ticker: str,
    chart_data: pd.DataFrame,
) -> go.Figure:
    """
    Build a mobile-friendly price, moving-average,
    and RSI chart.
    """

    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.08,
        row_heights=[
            0.72,
            0.28,
        ],
    )

    # --------------------------------------------------------
    # PRICE
    # --------------------------------------------------------

    figure.add_trace(
        go.Scatter(
            x=chart_data.index,
            y=chart_data["Close"],
            name="Price",
            mode="lines",
            line={
                "color": "#60a5fa",
                "width": 2.2,
            },
            hovertemplate=(
                "%{x|%b %d, %Y}"
                "<br>Price: $%{y:,.2f}"
                "<extra></extra>"
            ),
          ),
        row=1,
        col=1,
    )

    # ------------------------------------------------------
    # 50-DAY SMA
    # --------------------------------------------------------

    if "SMA_50" in chart_data.columns:

        figure.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["SMA_50"],
                name="50D",
                mode="lines",
                line={
                    "color": "#f59e0b",
                    "width": 1.7,
                },
                hovertemplate=(
                    "%{x|%b %d, %Y}"
                    "<br>50D: $%{y:,.2f}"
                    "<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

    # --------------------------------------------------------
    # 200-DAY SMA
    # --------------------------------------------------------

    if "SMA_200" in chart_data.columns:

        figure.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["SMA_200"],
                name="200D",
                mode="lines",
                line={
                    "color": "#ef4444",
                    "width": 1.8,
                },
                hovertemplate=(
                    "%{x|%b %d, %Y}"
                    "<br>200D: $%{y:,.2f}"
                    "<extra></extra>"
                ),
            ),
            row=1,
            col=1,
        )

    # --------------------------------------------------------
    # RSI
    # --------------------------------------------------------

    if "RSI_14" in chart_data.columns:

        figure.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data["RSI_14"],
                name="RSI",
                mode="lines",
                line={
                    "color": "#a78bfa",
                    "width": 1.8,
                },
                hovertemplate=(
                    "%{x|%b %d, %Y}"
                    "<br>RSI: %{y:.1f}"
                    "<extra></extra>"
                ),
            ),
            row=2,
            col=1,
        )

    # --------------------------------------------------------
    # RSI REFERENCE LINES
    # --------------------------------------------------------

    for level, color in [
        (70, "#ef4444"),
        (50, "#64748b"),
        (30, "#22c55e"),
    ]:

        figure.add_hline(
            y=level,
            line_width=1,
            line_dash="dot",
            line_color=color,
            row=2,
            col=1,
        )

    # --------------------------------------------------------
    # LAYOUT
    # --------------------------------------------------------

    figure.update_layout(
        title={
            "text": f"{ticker} Trend",
            "x": 0.01,
            "xanchor": "left",
        },
        height=540,
        margin={
            "l": 8,
            "r": 8,
            "t": 55,
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

    figure.update_yaxes(
        title_text="Price",
        tickprefix="$",
        row=1,
        col=1,
    )

    figure.update_yaxes(
        title_text="RSI",
        range=[
            0,
            100,
        ],
        row=2,
        col=1,
    )

    figure.update_xaxes(
        rangeslider_visible=False
    )

    return figure


# ============================================================
# TICKER SELECTION
# ============================================================

states_df = load_ticker_states()

if states_df.empty:

    st.info(
        "No TickerTrends scan data is available."
    )

    st.stop()


available_tickers = sorted(
    states_df[
        "ticker"
    ]
    .dropna()
    .unique()
    .tolist()
)


selected_from_screener = (
    st.session_state.get(
        "selected_ticker"
    )
)


if (
    selected_from_screener
    not in available_tickers
):

    selected_from_screener = (
        available_tickers[0]
    )


default_index = (
    available_tickers.index(
        selected_from_screener
    )
)


ticker = st.selectbox(
    "Ticker",
    available_tickers,
    index=default_index,
)


# Keep Screener and Details synchronized.
st.session_state[
    "selected_ticker"
] = ticker


# ============================================================
# LOAD CURRENT SNAPSHOT
# ============================================================

snapshot = load_ticker_snapshot(
    ticker
)

master = load_ticker_master(
    ticker
)


if snapshot is None:

    st.warning(
        f"No calculated TickerTrends data "
        f"is available for {ticker}."
    )

    st.stop()


technical_snapshot = (
    build_technical_snapshot(
        snapshot
    )
)


fundamental_snapshot = (
    build_fundamental_snapshot(
        snapshot
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


trend_result = (
    determine_trend_state(
        technical_snapshot
    )
)


# ============================================================
# COMPANY INFORMATION
# ============================================================

company_name = (
    master.get("company_name")
    if master
    else None
) or ticker


sector = (
    master.get("sector")
    if master
    else None
)


industry = (
    master.get("industry")
    if master
    else None
)


memberships = get_memberships(
    ticker
)


trend_state = (
    snapshot.get(
        "trend_state"
    )
)


trend_text = (
    format_state(
        trend_state
    )
    if trend_state
    else "⚪ Unknown"
)


trend_color = STATE_COLORS.get(
    trend_state,
    "#94a3b8",
)


total_score = snapshot.get(
    "total_score"
)


grade, score_label = (
    get_score_label(
        total_score
    )
)

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

st.title(
    f"📈 {ticker}"
)

st.caption(
    company_name
)


header_col1, header_col2 = (
    st.columns(2)
)


with header_col1:

    st.metric(
        "TickerTrends Score",
        (
            f"{total_score:.1f}"
            if total_score is not None
            else "N/A"
        ),
        help=(
            "Technical score plus fundamental score."
        ),
    )


with header_col2:

    st.metric(
        "Rating",
        (
            f"{grade} • {score_label}"
            if total_score is not None
            else "Insufficient Data"
        ),
    )


st.markdown(
    f"""
    <div style="
        border-left: 5px solid {trend_color};
        padding: 0.70rem 0.90rem;
        margin: 0.25rem 0 0.75rem 0;
        border-radius: 0.35rem;
        background: rgba(128, 128, 128, 0.08);
        font-size: 1.05rem;
        font-weight: 600;
    ">
        {trend_text}
    </div>
    """,
    unsafe_allow_html=True,
)


if trend_result:

    st.caption(
        trend_result.reason
    )


# ============================================================
# WATCHLIST
# ============================================================

watchlisted = is_in_watchlist(
    ticker
)


if watchlisted:

    if st.button(
        "★ Remove from Watchlist",
        use_container_width=True,
    ):

        remove_from_watchlist(
            ticker
        )

        st.cache_data.clear()

        st.success(
            f"{ticker} was removed from the Watchlist."
        )

        st.rerun()

else:

    if st.button(
        "☆ Add to Watchlist",
        type="primary",
        use_container_width=True,
    ):

        add_to_watchlist(
            ticker
        )

        st.cache_data.clear()

        st.success(
            f"{ticker} was added to the Watchlist."
        )

        st.rerun()


# ============================================================
# COMPANY CONTEXT
# ============================================================

context_parts: list[str] = []


if sector:
    context_parts.append(
        sector
    )


if industry:
    context_parts.append(
        industry
    )


if memberships:
    context_parts.append(
        " • ".join(
            memberships
        )
    )


if context_parts:

    st.caption(
        " | ".join(
            context_parts
        )
    )


# ============================================================
# KEY METRICS
# ============================================================

st.subheader(
    "Current Condition"
)


metric_col1, metric_col2 = (
    st.columns(2)
)


with metric_col1:

    st.metric(
        "Price",
        format_money(
            snapshot.get(
                "price"
            )
        ),
    )

    st.metric(
        "50-Day SMA",
        format_money(
            snapshot.get(
                "sma_50"
            )
        ),
        delta=format_percent(
            snapshot.get(
                "pct_from_sma50"
            )
        ),
        help=(
            "Delta shows price distance from the 50-day SMA."
        ),
    )


with metric_col2:

    st.metric(
        "RSI-14",
        format_number(
            snapshot.get(
                "rsi_14"
            ),
            1,
        ),
    )

    st.metric(
        "200-Day SMA",
        format_money(
            snapshot.get(
                "sma_200"
            )
        ),
        delta=format_percent(
            snapshot.get(
                "pct_from_sma200"
            )
        ),
        help=(
            "Delta shows price distance from the 200-day SMA."
        ),
    )


st.caption(
    "200D slope: "
    f"{format_percent(snapshot.get('sma_200_slope'), 2)}"
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
# PRICE / RSI CHART
# ============================================================

with st.spinner(
    f"Loading {ticker} chart..."
):

    chart_data = load_chart_data(
        ticker=ticker,
        period=chart_period,
    )


if chart_data.empty:

    st.info(
        "Historical chart data is currently unavailable."
    )

else:

    chart = create_price_chart(
        ticker=ticker,
        chart_data=chart_data,
    )

    st.plotly_chart(
        chart,
        width="stretch",
        config={
            "displaylogo": False,
            "responsive": True,
        },
    )


st.caption(
    "Historical chart data is cached for 30 minutes. "
    "Opening this page does not rerun the universe scanner."
)


# ============================================================
# SCORE BREAKDOWN
# ============================================================

st.subheader(
    "Score Breakdown"
)


score_col1, score_col2 = (
    st.columns(2)
)


with score_col1:

    st.metric(
        "Technical",
        (
            f"{snapshot['technical_score']:.1f} / 60"
            if snapshot.get(
                "technical_score"
            )
            is not None
            else "N/A"
        ),
    )


with score_col2:

    st.metric(
        "Fundamental",
        (
            f"{snapshot['fundamental_score']:.1f} / 40"
            if snapshot.get(
                "fundamental_score"
            )
            is not None
            else "N/A"
        ),
    )


# ============================================================
# TECHNICAL COMPONENTS
# ============================================================

with st.expander(
    "Technical Score",
    expanded=True,
):

    for component in technical_result[
        "components"
    ]:

        points = component.points

        point_text = (
            f"{points:.1f} / {component.max_points:.0f}"
            if points is not None
            else "N/A"
        )

        st.markdown(
            f"**{component.name}**"
        )

        st.caption(
            f"{point_text} • {component.label}"
        )

        st.progress(
            (
                points / component.max_points
                if points is not None
                and component.max_points
                else 0
            )
        )

        st.caption(
            component.reason
        )


# ============================================================
# FUNDAMENTAL COMPONENTS
# ============================================================

st.subheader(
    "Fundamentals"
)


for component in fundamental_result[
    "components"
]:

    color = fundamental_color(
        component.points,
        component.max_points,
    )

    icon = status_icon(
        component.points,
        component.max_points,
    )

    point_text = (
        f"{component.points:.1f} / "
        f"{component.max_points:.0f}"
        if component.points is not None
        else "N/A"
    )

    st.markdown(
        f"""
        <div style="
            border-left: 4px solid {color};
            padding: 0.65rem 0.80rem;
            margin-bottom: 0.55rem;
            border-radius: 0.30rem;
            background: rgba(128, 128, 128, 0.07);
        ">
            <div style="font-weight: 650;">
                {icon} {component.name}
            </div>
            <div style="font-size: 1.02rem;">
                {component.label}
            </div>
            <div style="
                opacity: 0.80;
                font-size: 0.88rem;
            ">
                {point_text} • {component.reason}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# FUNDAMENTAL VALUES
# ============================================================

with st.expander(
    "Fundamental Values",
    expanded=True,
):

    st.write(
        f"**P/E:** "
        f"{format_number(snapshot.get('pe_ratio'), 2)}"
    )

    st.write(
        f"**PEG:** "
        f"{format_number(snapshot.get('peg_ratio'), 2)}"
    )

    st.write(
        f"**Free Cash Flow:** "
        f"{format_large_money(snapshot.get('free_cash_flow'))}"
    )

    st.write(
        f"**FCF Margin:** "
        f"{format_percent(snapshot.get('fcf_metric'), 2)}"
    )

    st.write(
        f"**6M Relative Performance:** "
        f"{format_percent(snapshot.get('relative_performance'), 2)}"
    )


# ============================================================
# DATA INFORMATION
# ============================================================

with st.expander(
    "Data Information",
    expanded=False,
):

    st.write(
        "**Last calculated:** "
        f"{snapshot.get('calculated_at') or 'N/A'}"
    )

    st.write(
        "**Technical coverage:** "
        f"{technical_result['coverage']:.0f}%"
    )

    st.write(
        "**Fundamental coverage:** "
        f"{fundamental_result['coverage']:.0f}%"
    )

    st.caption(
        "The current score and indicator values come from "
        "SQLite. Only the historical chart uses cached "
        "market-data retrieval."
    )
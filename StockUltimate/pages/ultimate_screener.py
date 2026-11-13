"""
StockUltimate - Ultimate Screener
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf

from app_utils import cache_ttl, initialize_settings
from database import add_to_watchlist, load_watchlist
from securities import STOCKS, format_security_option

initialize_settings()

UNIVERSE = tuple(STOCKS.keys())


# ---------------------------------------------------------
# Data Loader
# ---------------------------------------------------------

@st.cache_data(ttl=cache_ttl(), show_spinner=False)
def load_ultimate_data(
    tickers: tuple[str, ...],
) -> pd.DataFrame:

    rows = []

    for ticker in tickers:

        try:

            security = yf.Ticker(ticker)

            info = security.info or {}

            revenue_growth = _number(
                info.get("revenueGrowth")
            )

            earnings_growth = _number(
                info.get("earningsGrowth")
            )

            dividend_yield = _number(
                info.get("dividendYield")
            )

            print(ticker, dividend_yield)


            roe = _number(
                info.get("returnOnEquity")
            )

            operating_margin = _number(
                info.get("operatingMargins")
            )

            forward_pe = _number(
                info.get("forwardPE")
            )

            pb = _number(
                info.get("priceToBook")
            )

            market_cap = _number(
                info.get("marketCap")
            )

            growth_score = _growth_score(
                revenue_growth,
                earnings_growth,
            )

            value_score = _value_score(
                forward_pe,
                pb,
            )

            dividend_score = _dividend_score(
                dividend_yield,
            )

            quality_score = _quality_score(
                roe,
                operating_margin,
            )

            overall_score = (
                growth_score * 0.30
                + value_score * 0.30
                + dividend_score * 0.20
                + quality_score * 0.20
            )

            rows.append(
                {
                    "ticker": ticker,
                    "company": info.get("shortName") or ticker,
                    "sector": info.get("sector") or "Unknown",
                    "market_cap": market_cap,
                    "growth_score": growth_score,
                    "value_score": value_score,
                    "dividend_score": dividend_score,
                    "quality_score": quality_score,
                    "overall_score": overall_score,
                    "profile": classify_profile(
                        growth_score,
                        value_score,
                        dividend_score,
                    ),
                }
            )

        except Exception:
            continue

    df = pd.DataFrame(rows)

    if not df.empty:
        df = df.sort_values(
            "overall_score",
            ascending=False,
        )

    return df.reset_index(drop=True)


# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def _number(value):

    try:
        return float(value)
    except Exception:
        return np.nan


def _linear(
    value,
    low,
    high,
):

    if not np.isfinite(value):
        return 50.0

    return float(
        np.clip(
            (value - low)
            / (high - low)
            * 100,
            0,
            100,
        )
    )


def _growth_score(
    revenue_growth,
    earnings_growth,
):

    scores = [
        _linear(
            revenue_growth,
            -0.05,
            0.35,
        ),
        _linear(
            earnings_growth,
            -0.10,
            0.40,
        ),
    ]

    return float(np.mean(scores))


def _value_score(
    pe,
    pb,
):

    pe_score = 50

    if np.isfinite(pe) and pe > 0:
        pe_score = np.clip(
            (40 - pe)
            / 30
            * 100,
            0,
            100,
        )

    pb_score = 50

    if np.isfinite(pb) and pb > 0:
        pb_score = np.clip(
            (8 - pb)
            / 6
            * 100,
            0,
            100,
        )

    return float(
        np.mean(
            [
                pe_score,
                pb_score,
            ]
        )
    )


def _dividend_score(dividend_yield):

    if not np.isfinite(dividend_yield):
        return 0

    if dividend_yield <= 0:
        return 0

    return float(
        np.clip(
            dividend_yield / 5.0 * 100,
            0,
            100,
        )
    )


def _quality_score(
    roe,
    margin,
):

    return float(
        np.mean(
            [
                _linear(
                    roe,
                    0,
                    0.35,
                ),
                _linear(
                    margin,
                    0,
                    0.30,
                ),
            ]
        )
    )


def classify_profile(
    growth,
    value,
    dividend,
):

    if (
        growth >= 80
        and value >= 80
        and dividend >= 80
    ):
        return "Elite Compounder"

    if (
        growth >= 80
        and value >= 80
    ):
        return "GARP"

    if (
        value >= 80
        and dividend >= 80
    ):
        return "Dividend Value"

    if growth >= 85:
        return "High Growth"

    if dividend >= 85:
        return "Income"

    return "Balanced"


# ---------------------------------------------------------
# Page Header
# ---------------------------------------------------------

st.markdown(
    """
<style>

[data-testid="stSidebar"] {
    display:none;
}

[data-testid="collapsedControl"] {
    display:none;
}

.block-container {
    max-width:540px;
}

</style>
""",
    unsafe_allow_html=True,
)


st.title("🏆 Ultimate Screener",
)

home_col, caption_col = st.columns(2)

with caption_col:
    st.caption(
        "Growth + Value + Dividend + Quality"
    )

with home_col:
    st.page_link(
        "app.py",
        label="Home",
        icon="🏠",
        width="stretch",
        )

# ---------------------------------------------------------
# Load Data
# ---------------------------------------------------------

with st.spinner(
    "Loading securities..."
):
    df = load_ultimate_data(
        UNIVERSE
    )

if df.empty:

    st.warning(
        "No data available."
    )

    st.stop()

# ---------------------------------------------------------
# Filters
# ---------------------------------------------------------

search = st.selectbox(
    "Select Security",
    options=list(UNIVERSE),
    index=None,
    placeholder="Search...",
    format_func=format_security_option,
)

minimum_score = st.slider(
    "Minimum Overall Score",
    0,
    100,
    60,
)

filtered = df[
    df["overall_score"]
    >= minimum_score
]

if search:

    filtered = filtered[
        filtered["ticker"]
        == search
    ]

# ---------------------------------------------------------
# Metrics
# ---------------------------------------------------------

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Stocks",
    len(filtered),
)

c2.metric(
    "Average",
    round(
        filtered["overall_score"].mean(),
        1,
    ),
)

c3.metric(
    "Top Score",
    round(
        filtered["overall_score"].max(),
        1,
    ),
)

c4.metric(
    "Elite",
    len(
        filtered[
            filtered["overall_score"]
            >= 85
        ]
    ),
)

# ---------------------------------------------------------
# Rank Table
# ---------------------------------------------------------

st.subheader(
    "Top Ranked Stocks"
)

display_df = (
    filtered[
        [
            "ticker",
            "company",
            "overall_score",
            "profile",
        ]
    ]
    .sort_values(
        "overall_score",
        ascending=False,
    )
)

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "ticker": st.column_config.TextColumn(
            "Ticker",
        ),
        "company": st.column_config.TextColumn(
            "Company",
            width="medium",
        ),
        "overall_score": st.column_config.NumberColumn(
            "Overall Score",
            format="%.1f",
        ),
            "profile": st.column_config.TextColumn(
            "Profile",
            width="small",
        ),
    },
)

# ---------------------------------------------------------
# Bubble Chart
# ---------------------------------------------------------

st.subheader(
    "Growth vs Value"
)

fig = px.scatter(
    filtered,
    x="growth_score",
    y="value_score",
    size="market_cap",
    color="overall_score",
    text="ticker",
    custom_data=[
        "ticker",
        "company",
        "overall_score",
        "growth_score",
        "value_score",
        "dividend_score",
        "quality_score",
        "profile",
    ],
    color_continuous_scale=[
        [0.00, "#ef4444"],
        [0.40, "#f59e0b"],
        [0.70, "#22c55e"],
        [1.00, "#38bdf8"],
    ],
    size_max=38,
)

fig.update_traces(
    textposition="top center",
    textfont=dict(
        size=11,
        color="#e5e7eb",
    ),
    marker=dict(
        opacity=0.85,
        line=dict(
            width=1,
            color="rgba(255,255,255,0.35)",
        ),
    ),
    hovertemplate=(
        "<b>%{customdata[0]} - %{customdata[1]}</b><br>"
        "<br>"
        "Overall Score: %{customdata[2]:.1f}<br>"
        "Growth Score: %{customdata[3]:.1f}<br>"
        "Value Score: %{customdata[4]:.1f}<br>"
        "Dividend Score: %{customdata[5]:.1f}<br>"
        "Quality Score: %{customdata[6]:.1f}<br>"
        "Profile: %{customdata[7]}"
        "<extra></extra>"
    ),
)

fig.update_layout(
    height=520,
    margin=dict(
        l=20,
        r=50,
        t=20,
        b=10,
    ),
    xaxis_title="Growth Score",
    yaxis_title="Value Score",
    coloraxis_colorbar=dict(
        title="Overall<br>Score",
        tickformat=".1f",
        thickness=12,
    ),
    hoverlabel=dict(
        bgcolor="#111827",
        font_size=13,
        font_color="white",
    ),
)

fig.update_xaxes(
    range=[50, 105],
    tick0=0,
    dtick=20,
    showgrid=True,
    gridcolor="rgba(255,255,255,0.10)",
    zeroline=False,
)

fig.update_yaxes(
    range=[20, 105],
    tick0=0,
    dtick=20,
    showgrid=True,
    gridcolor="rgba(255,255,255,0.10)",
    zeroline=False,
)

st.plotly_chart(
    fig,
    use_container_width=True,
)

# ---------------------------------------------------------
# Profile Breakdown
# ---------------------------------------------------------

st.subheader("Investment Profiles")

profile_counts = (
    filtered["profile"]
    .value_counts()
    .reset_index()
)

profile_counts.columns = [
    "profile",
    "count",
]

# Sort largest to smallest
profile_counts = profile_counts.sort_values(
    "count",
    ascending=False,
)

fig2 = px.bar(
    profile_counts,
    x="profile",
    y="count",
    text="count",
    custom_data=[
        "profile",
        "count",
    ],
)

fig2.update_traces(
    marker_color="#4da3ff",
    marker_line_color="rgba(255,255,255,0.25)",
    marker_line_width=1,
    texttemplate="%{text}",
    textposition="outside",
    cliponaxis=False,
    hovertemplate=(
        "<b>%{customdata[0]}</b><br>"
        "Stocks: %{customdata[1]}"
        "<extra></extra>"
    ),
)

fig2.update_layout(
    height=420,
    margin=dict(
        l=10,
        r=10,
        t=25,
        b=20,
    ),
    xaxis_title="Profile",
    yaxis_title="Tickers",
    showlegend=False,
    hoverlabel=dict(
        bgcolor="#111827",
        font_size=13,
        font_color="white",
    ),
)

fig2.update_xaxes(
    showgrid=False,
    tickangle=0,
)

fig2.update_yaxes(
    rangemode="tozero",
    dtick=1,
    showgrid=True,
    gridcolor="rgba(255,255,255,0.10)",
    zeroline=False,
)

st.plotly_chart(
    fig2,
    use_container_width=True,
)
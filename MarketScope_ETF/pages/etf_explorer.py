import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_data import get_price_history


# =========================================================
# PAGE HEADER
# =========================================================

st.title("📈 ETF Explorer")

st.caption(
    "Explore individual ETFs using price trends, "
    "momentum, relative strength, risk, and technical indicators."
)


# =========================================================
# LOAD SHARED DATA
# =========================================================

market_data = st.session_state.get("market_data")

if market_data is None:
    st.error(
        "Shared MarketScope ETF data is not loaded. "
        "Restart the application."
    )
    st.stop()


etf_df = market_data.get(
    "etf_df",
    pd.DataFrame(),
).copy()


if etf_df.empty:
    st.warning(
        "ETF analysis data is currently unavailable."
    )
    st.stop()


# =========================================================
# ETF SELECTOR
# =========================================================

available_etfs = (
    etf_df["Ticker"]
    .dropna()
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)


selected_ticker = st.selectbox(
    "Select ETF",
    options=available_etfs,
    index=0,
    key="etf_explorer_ticker",
    width="stretch",
)


# =========================================================
# SELECT ETF ROW
# =========================================================

ticker_rows = etf_df[
    etf_df["Ticker"] == selected_ticker
]


if ticker_rows.empty:
    st.warning(
        f"No analysis data is available for {selected_ticker}."
    )
    st.stop()


etf = ticker_rows.iloc[0]


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def safe_number(value):
    """
    Convert a value to float when possible.
    """

    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except (TypeError, ValueError):
        pass

    return np.nan


def format_number(
    value,
    decimals=2,
    prefix="",
    suffix="",
):
    """
    Format a numeric value for display.
    """

    value = safe_number(value)

    if pd.isna(value):
        return "N/A"

    return (
        f"{prefix}"
        f"{value:,.{decimals}f}"
        f"{suffix}"
    )


def format_large_number(value):
    """
    Format large fund values such as assets.
    """

    value = safe_number(value)

    if pd.isna(value):
        return "N/A"

    if abs(value) >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.2f}T"

    if abs(value) >= 1_000_000_000:
        return f"${value / 1_000_000_000:.2f}B"

    if abs(value) >= 1_000_000:
        return f"${value / 1_000_000:.2f}M"

    return f"${value:,.0f}"


# =========================================================
# ETF TITLE
# =========================================================

etf_name = str(
    etf.get(
        "Name",
        selected_ticker,
    )
)

categories = str(
    etf.get(
        "Categories",
        "Unclassified",
    )
)


st.markdown(
    f"## {selected_ticker}"
)

if (
    etf_name
    and etf_name != selected_ticker
):
    st.write(etf_name)

st.caption(categories)


# =========================================================
# PRIMARY METRICS
# =========================================================

price = etf.get("Price")
etf_score = etf.get("ETF Score")
trend = etf.get("Trend", "N/A")
rsi = etf.get("RSI 14")


metric1, metric2, metric3, metric4 = st.columns(4)


with metric1:

    st.metric(
        "Price",
        format_number(
            price,
            decimals=2,
            prefix="$",
        ),
    )


with metric2:

    st.metric(
        "ETF Score",
        format_number(
            etf_score,
            decimals=1,
        ),
    )


with metric3:

    st.metric(
        "Trend",
        str(trend),
    )


with metric4:

    st.metric(
        "RSI",
        format_number(
            rsi,
            decimals=1,
        ),
    )


# =========================================================
# PRICE HISTORY
# =========================================================

st.markdown("---")

st.markdown("## Price History")


history = get_price_history(
    market_data,
    selected_ticker,
)


if history.empty:

    st.info(
        "Price history is not available "
        "for this ETF."
    )

else:

    chart_data = history.copy()

    chart_data["SMA 50"] = (
        chart_data["Close"]
        .rolling(50)
        .mean()
    )

    chart_data["SMA 200"] = (
        chart_data["Close"]
        .rolling(200)
        .mean()
    )


    chart_range = st.radio(
        "Chart Range",
        options=[
            "3M",
            "6M",
            "1Y",
            "2Y",
        ],
        index=2,
        horizontal=True,
        key="etf_explorer_chart_range",
    )


    range_days = {
        "3M": 90,
        "6M": 180,
        "1Y": 365,
        "2Y": 730,
    }


    if isinstance(
        chart_data.index,
        pd.DatetimeIndex,
    ):

        latest_date = (
            chart_data.index.max()
        )

        cutoff_date = (
            latest_date
            - pd.Timedelta(
                days=range_days[
                    chart_range
                ]
            )
        )

        display_history = (
            chart_data[
                chart_data.index
                >= cutoff_date
            ]
            .copy()
        )

    else:

        display_history = (
            chart_data.copy()
        )


    fig = go.Figure()


    fig.add_trace(
        go.Scatter(
            x=display_history.index,
            y=display_history["Close"],
            mode="lines",
            name=selected_ticker,
            line=dict(
                width=2.5,
                color="#1f77b4",
            ),
        )
    )


    fig.add_trace(
        go.Scatter(
            x=display_history.index,
            y=display_history["SMA 50"],
            mode="lines",
            name="SMA 50",
            line=dict(
                width=1.5,
                color="#ff9900",
            ),
        )
    )


    fig.add_trace(
        go.Scatter(
            x=display_history.index,
            y=display_history["SMA 200"],
            mode="lines",
            name="SMA 200",
            line=dict(
                width=1.5,
                color="#d62728",
            ),
        )
    )


    fig.update_layout(
        height=520,
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        xaxis_title=None,
        yaxis_title="Price ($)",
    )


    fig.update_xaxes(
        showgrid=False,
    )


    st.plotly_chart(
        fig,
        width="stretch",
        key="etf_explorer_price_chart",
    )


# =========================================================
# PERFORMANCE
# =========================================================

st.markdown("---")

st.markdown("## Performance")


performance_metrics = [
    ("1D", "Return 1D %"),
    ("1W", "Return 1W %"),
    ("1M", "Return 1M %"),
    ("3M", "Return 3M %"),
    ("6M", "Return 6M %"),
    ("YTD", "Return YTD %"),
    ("1Y", "Return 1Y %"),
]


performance_columns = st.columns(
    len(performance_metrics)
)


for column, (
    label,
    field,
) in zip(
    performance_columns,
    performance_metrics,
):

    value = safe_number(
        etf.get(field)
    )

    with column:

        st.metric(
            label,
            format_number(
                value,
                decimals=2,
                suffix="%",
            ),
        )


# =========================================================
# TECHNICAL ANALYSIS
# =========================================================

st.markdown("---")

st.markdown("## Technical Analysis")


technical1, technical2, technical3, technical4 = (
    st.columns(4)
)


with technical1:

    st.metric(
        "SMA 50",
        format_number(
            etf.get("SMA 50"),
            decimals=2,
            prefix="$",
        ),
    )


with technical2:

    st.metric(
        "SMA 200",
        format_number(
            etf.get("SMA 200"),
            decimals=2,
            prefix="$",
        ),
    )


with technical3:

    st.metric(
        "52W High Distance",
        format_number(
            etf.get(
                "52W High Distance %"
            ),
            decimals=2,
            suffix="%",
        ),
    )


with technical4:

    st.metric(
        "Momentum Score",
        format_number(
            etf.get(
                "Momentum Score"
            ),
            decimals=1,
        ),
    )


# =========================================================
# SCORE BREAKDOWN
# =========================================================

st.markdown("---")

st.markdown("## MarketScope Score Breakdown")


score_data = pd.DataFrame(
    {
        "Component": [
            "Momentum",
            "Trend",
            "Risk",
            "Liquidity",
            "Cost",
            "Dividend",
        ],

        "Score": [
            safe_number(
                etf.get(
                    "Momentum Score"
                )
            ),
            safe_number(
                etf.get(
                    "Trend Score"
                )
            ),
            safe_number(
                etf.get(
                    "Risk Score"
                )
            ),
            safe_number(
                etf.get(
                    "Liquidity Score"
                )
            ),
            safe_number(
                etf.get(
                    "Cost Score"
                )
            ),
            safe_number(
                etf.get(
                    "Dividend Score"
                )
            ),
        ],
    }
)


score_data = score_data.dropna(
    subset=["Score"]
)


if score_data.empty:

    st.info(
        "Score-component data is "
        "not currently available."
    )

else:

    score_fig = go.Figure()


    score_fig.add_trace(
        go.Bar(
            x=score_data["Score"],
            y=score_data["Component"],
            orientation="h",
            marker=dict(
                color=score_data["Score"],
                colorscale=[
                    [0.0, "#d73027"],
                    [0.5, "#fee08b"],
                    [1.0, "#1a9850"],
                ],
                cmin=0,
                cmax=100,
            ),
            text=score_data["Score"].map(
                lambda value:
                    f"{value:.1f}"
            ),
            textposition="outside",
        )
    )


    score_fig.update_layout(
        height=380,
        xaxis=dict(
            range=[0, 105],
            title="Score",
        ),
        yaxis=dict(
            title=None,
            autorange="reversed",
        ),
        margin=dict(
            l=10,
            r=20,
            t=10,
            b=10,
        ),
        showlegend=False,
    )


    st.plotly_chart(
        score_fig,
        width="stretch",
        key="etf_explorer_scores",
    )


# =========================================================
# RISK AND RELATIVE STRENGTH
# =========================================================

st.markdown("---")

left_column, right_column = st.columns(2)


with left_column:

    st.markdown("### Risk")

    risk1, risk2 = st.columns(2)

    with risk1:

        st.metric(
            "Volatility",
            format_number(
                etf.get(
                    "Volatility %"
                ),
                decimals=2,
                suffix="%",
            ),
        )

    with risk2:

        st.metric(
            "Max Drawdown",
            format_number(
                etf.get(
                    "Max Drawdown %"
                ),
                decimals=2,
                suffix="%",
            ),
        )


with right_column:

    st.markdown(
        "### Relative Strength vs SPY"
    )

    rs1, rs2, rs3 = st.columns(3)

    with rs1:

        st.metric(
            "3M",
            format_number(
                etf.get(
                    "Relative Strength 3M %"
                ),
                decimals=2,
                suffix="%",
            ),
        )

    with rs2:

        st.metric(
            "6M",
            format_number(
                etf.get(
                    "Relative Strength 6M %"
                ),
                decimals=2,
                suffix="%",
            ),
        )

    with rs3:

        st.metric(
            "1Y",
            format_number(
                etf.get(
                    "Relative Strength 1Y %"
                ),
                decimals=2,
                suffix="%",
            ),
        )


# =========================================================
# FUND INFORMATION
# =========================================================

st.markdown("---")

st.markdown("## Fund Information")


fund1, fund2, fund3, fund4 = st.columns(4)


with fund1:

    st.metric(
        "Expense Ratio",
        format_number(
            etf.get(
                "Expense Ratio %"
            ),
            decimals=3,
            suffix="%",
        ),
    )


with fund2:

    st.metric(
        "Dividend Yield",
        format_number(
            etf.get(
                "Dividend Yield %"
            ),
            decimals=2,
            suffix="%",
        ),
    )


with fund3:

    st.metric(
        "Total Assets",
        format_large_number(
            etf.get(
                "Total Assets"
            )
        ),
    )


with fund4:

    volume = safe_number(
        etf.get(
            "Average Volume"
        )
    )

    if pd.isna(volume):
        volume_display = "N/A"
    else:
        volume_display = (
            f"{volume:,.0f}"
        )

    st.metric(
        "Average Volume",
        volume_display,
    )


# =========================================================
# TREND DETAILS
# =========================================================

with st.expander(
    "🔍 Trend Details"
):

    above_sma_50 = bool(
        etf.get(
            "Above SMA 50",
            False,
        )
    )

    above_sma_200 = bool(
        etf.get(
            "Above SMA 200",
            False,
        )
    )

    golden_cross = bool(
        etf.get(
            "SMA 50 Above SMA 200",
            False,
        )
    )


    if above_sma_50:
        st.success(
            "Price is above its 50-day moving average."
        )
    else:
        st.warning(
            "Price is below its 50-day moving average."
        )


    if above_sma_200:
        st.success(
            "Price is above its 200-day moving average."
        )
    else:
        st.warning(
            "Price is below its 200-day moving average."
        )


    if golden_cross:
        st.success(
            "The 50-day moving average is above "
            "the 200-day moving average."
        )
    else:
        st.warning(
            "The 50-day moving average is not above "
            "the 200-day moving average."
        )


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.caption(
    "MarketScope ETF is provided for informational and "
    "educational purposes only. Historical performance, "
    "rankings, technical indicators, and MarketScope scores "
    "are not investment advice."
)
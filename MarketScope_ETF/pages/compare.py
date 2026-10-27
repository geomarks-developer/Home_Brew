import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from market_data import get_price_history


# =========================================================
# PAGE HEADER
# =========================================================

st.title("⚖️ Compare ETFs")

st.caption(
    "Compare ETF performance, risk, trends, relative strength, "
    "and MarketScope scores side by side."
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
# HELPERS
# =========================================================

def safe_number(value):
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
    suffix="",
):
    value = safe_number(value)

    if pd.isna(value):
        return "N/A"

    return f"{value:,.{decimals}f}{suffix}"


# =========================================================
# ETF SELECTION
# =========================================================

available_etfs = (
    etf_df["Ticker"]
    .dropna()
    .astype(str)
    .sort_values()
    .unique()
    .tolist()
)


preferred_defaults = [
    "VOO",
    "QQQ",
    "SCHD",
]


default_etfs = [
    ticker
    for ticker in preferred_defaults
    if ticker in available_etfs
]


selected_etfs = st.multiselect(
    "Select ETFs to compare",
    options=available_etfs,
    default=default_etfs,
    max_selections=4,
    placeholder="Select 2 to 4 ETFs",
    key="compare_etfs",
    width="stretch",
)


if len(selected_etfs) < 2:
    st.info(
        "Select at least two ETFs to begin the comparison."
    )
    st.stop()


# =========================================================
# CHART SETTINGS
# =========================================================

chart_col1, chart_col2 = st.columns(
    [1, 1]
)


with chart_col1:

    chart_range = st.radio(
        "Comparison Period",
        options=[
            "3M",
            "6M",
            "1Y",
            "2Y",
        ],
        index=2,
        horizontal=True,
        key="compare_chart_range",
    )


with chart_col2:

    starting_value = st.selectbox(
        "Starting Investment",
        options=[
            1000,
            5000,
            10000,
            25000,
            50000,
        ],
        index=2,
        format_func=lambda value:
            f"${value:,.0f}",
        key="compare_starting_value",
        width="stretch",
    )


range_days = {
    "3M": 90,
    "6M": 180,
    "1Y": 365,
    "2Y": 730,
}


# =========================================================
# NORMALIZED PERFORMANCE
# =========================================================

st.markdown("---")

st.markdown(
    f"## Growth of ${starting_value:,.0f}"
)


comparison_history = {}


for ticker in selected_etfs:

    history = get_price_history(
        market_data,
        ticker,
    )

    if history.empty:
        continue

    if "Close" not in history.columns:
        continue

    history = history.copy()

    if not isinstance(
        history.index,
        pd.DatetimeIndex,
    ):
        continue

    latest_date = history.index.max()

    cutoff_date = (
        latest_date
        - pd.Timedelta(
            days=range_days[
                chart_range
            ]
        )
    )

    history = history[
        history.index >= cutoff_date
    ].copy()

    history["Close"] = pd.to_numeric(
        history["Close"],
        errors="coerce",
    )

    history = history.dropna(
        subset=["Close"]
    )

    if history.empty:
        continue

    first_price = safe_number(
        history["Close"].iloc[0]
    )

    if (
        pd.isna(first_price)
        or first_price == 0
    ):
        continue

    history["Portfolio Value"] = (
        history["Close"]
        / first_price
        * starting_value
    )

    comparison_history[
        ticker
    ] = history


if len(comparison_history) < 2:

    st.warning(
        "There is not enough price history available "
        "to compare the selected ETFs."
    )

else:

    fig = go.Figure()


    for ticker, history in (
        comparison_history.items()
    ):

        fig.add_trace(
            go.Scatter(
                x=history.index,
                y=history[
                    "Portfolio Value"
                ],
                mode="lines",
                name=ticker,
                line=dict(
                    width=2.5,
                ),
                hovertemplate=(
                    "%{x|%b %d, %Y}"
                    "<br>"
                    "$%{y:,.2f}"
                    "<extra>"
                    + ticker
                    + "</extra>"
                ),
            )
        )


    fig.add_hline(
        y=starting_value,
        line_dash="dot",
        line_color="gray",
        opacity=0.6,
    )


    fig.update_layout(
        height=525,
        hovermode="x unified",
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        xaxis_title=None,
        yaxis_title="Portfolio Value ($)",
    )


    fig.update_xaxes(
        showgrid=False,
    )


    st.plotly_chart(
        fig,
        width="stretch",
        key="compare_growth_chart",
    )


# =========================================================
# ENDING VALUE
# =========================================================

if comparison_history:

    st.markdown("### Ending Value")


    ending_columns = st.columns(
        len(comparison_history)
    )


    for column, (
        ticker,
        history,
    ) in zip(
        ending_columns,
        comparison_history.items(),
    ):

        ending_value = safe_number(
            history[
                "Portfolio Value"
            ].iloc[-1]
        )

        gain_loss = (
            ending_value
            - starting_value
        )

        gain_loss_pct = (
            (
                ending_value
                / starting_value
            )
            - 1
        ) * 100


        with column:

            st.metric(
                ticker,
                (
                    f"${ending_value:,.2f}"
                    if pd.notna(
                        ending_value
                    )
                    else "N/A"
                ),
                delta=(
                    f"{gain_loss_pct:+.2f}%"
                    if pd.notna(
                        gain_loss_pct
                    )
                    else None
                ),
            )


# =========================================================
# PERFORMANCE COMPARISON
# =========================================================

st.markdown("---")

st.markdown("## Performance")


comparison_rows = etf_df[
    etf_df["Ticker"].isin(
        selected_etfs
    )
].copy()


comparison_rows = (
    comparison_rows
    .set_index("Ticker")
    .reindex(selected_etfs)
    .reset_index()
)


performance_fields = {
    "1 Day": "Return 1D %",
    "1 Week": "Return 1W %",
    "1 Month": "Return 1M %",
    "3 Months": "Return 3M %",
    "6 Months": "Return 6M %",
    "YTD": "Return YTD %",
    "1 Year": "Return 1Y %",
}


performance_table = pd.DataFrame(
    {
        "Period":
            list(
                performance_fields.keys()
            )
    }
)


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue

    row = ticker_row.iloc[0]


    performance_table[
        ticker
    ] = [
        safe_number(
            row.get(field)
        )
        for field in (
            performance_fields.values()
        )
    ]


column_config = {
    ticker:
        st.column_config.NumberColumn(
            ticker,
            format="%.2f%%",
        )
    for ticker in selected_etfs
}


st.dataframe(
    performance_table,
    width="stretch",
    hide_index=True,
    column_config=column_config,
)


# =========================================================
# SCORE COMPARISON
# =========================================================

st.markdown("---")

st.markdown("## MarketScope Scores")


score_fields = {
    "ETF Score":
        "ETF Score",

    "Momentum":
        "Momentum Score",

    "Trend":
        "Trend Score",

    "Risk":
        "Risk Score",

    "Liquidity":
        "Liquidity Score",

    "Cost":
        "Cost Score",

    "Dividend":
        "Dividend Score",
}


score_table = pd.DataFrame(
    {
        "Score":
            list(
                score_fields.keys()
            )
    }
)


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue


    row = ticker_row.iloc[0]


    score_table[
        ticker
    ] = [
        safe_number(
            row.get(field)
        )
        for field in (
            score_fields.values()
        )
    ]


score_column_config = {
    ticker:
        st.column_config.NumberColumn(
            ticker,
            format="%.1f",
        )
    for ticker in selected_etfs
}


st.dataframe(
    score_table,
    width="stretch",
    hide_index=True,
    column_config=score_column_config,
)


# =========================================================
# SCORE BAR CHART
# =========================================================

score_chart_data = []


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue


    row = ticker_row.iloc[0]


    for label, field in (
        score_fields.items()
    ):

        value = safe_number(
            row.get(field)
        )

        if pd.isna(value):
            continue


        score_chart_data.append(
            {
                "Ticker": ticker,
                "Component": label,
                "Score": value,
            }
        )


score_chart_df = pd.DataFrame(
    score_chart_data
)


if not score_chart_df.empty:

    score_fig = go.Figure()


    for ticker in selected_etfs:

        ticker_scores = (
            score_chart_df[
                score_chart_df[
                    "Ticker"
                ]
                == ticker
            ]
        )


        score_fig.add_trace(
            go.Bar(
                name=ticker,
                x=ticker_scores[
                    "Component"
                ],
                y=ticker_scores[
                    "Score"
                ],
            )
        )


    score_fig.update_layout(
        barmode="group",
        height=430,
        yaxis=dict(
            title="Score",
            range=[0, 105],
        ),
        xaxis=dict(
            title=None,
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0,
        ),
        margin=dict(
            l=10,
            r=10,
            t=20,
            b=10,
        ),
    )


    st.plotly_chart(
        score_fig,
        width="stretch",
        key="compare_scores_chart",
    )


# =========================================================
# RISK COMPARISON
# =========================================================

st.markdown("---")

st.markdown("## Risk")


risk_fields = {
    "Annualized Volatility":
        "Volatility %",

    "Maximum Drawdown":
        "Max Drawdown %",

    "52-Week High Distance":
        "52W High Distance %",
}


risk_table = pd.DataFrame(
    {
        "Metric":
            list(
                risk_fields.keys()
            )
    }
)


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue


    row = ticker_row.iloc[0]


    risk_table[
        ticker
    ] = [
        safe_number(
            row.get(field)
        )
        for field in (
            risk_fields.values()
        )
    ]


risk_column_config = {
    ticker:
        st.column_config.NumberColumn(
            ticker,
            format="%.2f%%",
        )
    for ticker in selected_etfs
}


st.dataframe(
    risk_table,
    width="stretch",
    hide_index=True,
    column_config=risk_column_config,
)


# =========================================================
# TECHNICAL COMPARISON
# =========================================================

st.markdown("---")

st.markdown("## Technical Comparison")


technical_table = []


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue


    row = ticker_row.iloc[0]


    technical_table.append(
        {
            "Ticker":
                ticker,

            "Price":
                safe_number(
                    row.get("Price")
                ),

            "SMA 50":
                safe_number(
                    row.get("SMA 50")
                ),

            "SMA 200":
                safe_number(
                    row.get("SMA 200")
                ),

            "RSI":
                safe_number(
                    row.get("RSI 14")
                ),

            "Trend":
                str(
                    row.get(
                        "Trend",
                        "N/A",
                    )
                ),
        }
    )


technical_df = pd.DataFrame(
    technical_table
)


st.dataframe(
    technical_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Price":
            st.column_config.NumberColumn(
                "Price",
                format="$%.2f",
            ),

        "SMA 50":
            st.column_config.NumberColumn(
                "SMA 50",
                format="$%.2f",
            ),

        "SMA 200":
            st.column_config.NumberColumn(
                "SMA 200",
                format="$%.2f",
            ),

        "RSI":
            st.column_config.NumberColumn(
                "RSI",
                format="%.1f",
            ),
    },
)


# =========================================================
# RELATIVE STRENGTH
# =========================================================

st.markdown("---")

st.markdown(
    "## Relative Strength vs SPY"
)


relative_strength_fields = {
    "3 Months":
        "Relative Strength 3M %",

    "6 Months":
        "Relative Strength 6M %",

    "1 Year":
        "Relative Strength 1Y %",
}


relative_strength_table = pd.DataFrame(
    {
        "Period":
            list(
                relative_strength_fields.keys()
            )
    }
)


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue


    row = ticker_row.iloc[0]


    relative_strength_table[
        ticker
    ] = [
        safe_number(
            row.get(field)
        )
        for field in (
            relative_strength_fields.values()
        )
    ]


relative_strength_config = {
    ticker:
        st.column_config.NumberColumn(
            ticker,
            format="%.2f%%",
        )
    for ticker in selected_etfs
}


st.dataframe(
    relative_strength_table,
    width="stretch",
    hide_index=True,
    column_config=(
        relative_strength_config
    ),
)


# =========================================================
# FUND DETAILS
# =========================================================

st.markdown("---")

st.markdown("## Fund Details")


fund_table = []


for ticker in selected_etfs:

    ticker_row = comparison_rows[
        comparison_rows["Ticker"]
        == ticker
    ]

    if ticker_row.empty:
        continue


    row = ticker_row.iloc[0]


    fund_table.append(
        {
            "Ticker":
                ticker,

            "Categories":
                str(
                    row.get(
                        "Categories",
                        "",
                    )
                ),

            "Expense Ratio":
                safe_number(
                    row.get(
                        "Expense Ratio %"
                    )
                ),

            "Dividend Yield":
                safe_number(
                    row.get(
                        "Dividend Yield %"
                    )
                ),

            "Average Volume":
                safe_number(
                    row.get(
                        "Average Volume"
                    )
                ),
        }
    )


fund_df = pd.DataFrame(
    fund_table
)


st.dataframe(
    fund_df,
    width="stretch",
    hide_index=True,
    column_config={
        "Expense Ratio":
            st.column_config.NumberColumn(
                "Expense Ratio",
                format="%.3f%%",
            ),

        "Dividend Yield":
            st.column_config.NumberColumn(
                "Dividend Yield",
                format="%.2f%%",
            ),

        "Average Volume":
            st.column_config.NumberColumn(
                "Average Volume",
                format="%,.0f",
            ),
    },
)


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.caption(
    "MarketScope ETF comparisons are provided for "
    "informational and educational purposes only. "
    "Historical performance, MarketScope scores, "
    "technical indicators, and hypothetical portfolio "
    "values are not investment advice."
)
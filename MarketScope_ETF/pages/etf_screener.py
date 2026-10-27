import pandas as pd
import streamlit as st


# =========================================================
# PAGE HEADER
# =========================================================

st.title("🔎 ETF Screener")

st.caption(
    "Screen the MarketScope ETF universe using category, "
    "score, momentum, trend, performance, and risk."
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
# PREPARE DATA
# =========================================================

numeric_columns = [
    "Price",
    "ETF Score",
    "Momentum Score",
    "Trend Score",
    "Risk Score",
    "Liquidity Score",
    "Cost Score",
    "Dividend Score",
    "Return 1D %",
    "Return 1W %",
    "Return 1M %",
    "Return 3M %",
    "Return 6M %",
    "Return YTD %",
    "Return 1Y %",
    "Relative Strength 3M %",
    "Relative Strength 6M %",
    "Relative Strength 1Y %",
    "RSI 14",
    "52W High Distance %",
    "Volatility %",
    "Max Drawdown %",
    "Dividend Yield %",
    "Expense Ratio %",
    "Average Volume",
    "Total Assets",
]


for column in numeric_columns:

    if column in etf_df.columns:

        etf_df[column] = pd.to_numeric(
            etf_df[column],
            errors="coerce",
        )


# =========================================================
# FILTER PANEL
# =========================================================

st.markdown("## Filters")


filter_row_1 = st.columns(
    [
        1.4,
        1.2,
        1.2,
        1.2,
    ]
)


# ---------------------------------------------------------
# Category
# ---------------------------------------------------------

with filter_row_1[0]:

    categories = sorted(
        {
            category.strip()
            for value in etf_df.get(
                "Categories",
                pd.Series(dtype=str),
            ).dropna()
            for category in str(value).split(",")
            if category.strip()
        }
    )

    selected_categories = st.multiselect(
        "ETF Category",
        options=categories,
        placeholder="All categories",
    )


# ---------------------------------------------------------
# Trend
# ---------------------------------------------------------

with filter_row_1[1]:

    trend_order = [
        "Strong Uptrend",
        "Uptrend",
        "Neutral",
        "Downtrend",
        "Strong Downtrend",
    ]

    available_trends = []

    if "Trend" in etf_df.columns:

        existing_trends = set(
            etf_df["Trend"]
            .dropna()
            .astype(str)
        )

        available_trends = [
            trend
            for trend in trend_order
            if trend in existing_trends
        ]

    selected_trends = st.multiselect(
        "Trend",
        options=available_trends,
        placeholder="All trends",
    )


# ---------------------------------------------------------
# Minimum ETF Score
# ---------------------------------------------------------

with filter_row_1[2]:

    minimum_score = st.slider(
        "Minimum ETF Score",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )


# ---------------------------------------------------------
# Minimum Momentum
# ---------------------------------------------------------

with filter_row_1[3]:

    minimum_momentum = st.slider(
        "Minimum Momentum",
        min_value=0,
        max_value=100,
        value=0,
        step=5,
    )


# =========================================================
# PERFORMANCE FILTERS
# =========================================================

with st.expander(
    "📈 Performance & Technical Filters"
):

    performance_row_1 = st.columns(4)


    with performance_row_1[0]:

        min_1m = st.number_input(
            "Minimum 1M Return %",
            value=-100.0,
            step=1.0,
        )


    with performance_row_1[1]:

        min_3m = st.number_input(
            "Minimum 3M Return %",
            value=-100.0,
            step=1.0,
        )


    with performance_row_1[2]:

        min_6m = st.number_input(
            "Minimum 6M Return %",
            value=-100.0,
            step=1.0,
        )


    with performance_row_1[3]:

        min_1y = st.number_input(
            "Minimum 1Y Return %",
            value=-100.0,
            step=1.0,
        )


    st.markdown("#### Technical Trend")


    technical_row = st.columns(3)


    with technical_row[0]:

        require_above_sma50 = st.checkbox(
            "Price above SMA 50"
        )


    with technical_row[1]:

        require_above_sma200 = st.checkbox(
            "Price above SMA 200"
        )


    with technical_row[2]:

        require_golden_trend = st.checkbox(
            "SMA 50 above SMA 200"
        )


    st.markdown("#### RSI")


    rsi_range = st.slider(
        "RSI Range",
        min_value=0,
        max_value=100,
        value=(0, 100),
        step=1,
    )


# =========================================================
# RISK FILTERS
# =========================================================

with st.expander(
    "⚖️ Risk Filters"
):

    risk_col1, risk_col2 = st.columns(2)


    with risk_col1:

        max_volatility = st.slider(
            "Maximum Annualized Volatility %",
            min_value=5,
            max_value=100,
            value=100,
            step=5,
        )


    with risk_col2:

        max_drawdown = st.slider(
            "Maximum Drawdown %",
            min_value=5,
            max_value=100,
            value=100,
            step=5,
            help=(
                "Example: selecting 25 excludes ETFs whose "
                "historical maximum drawdown exceeded 25%."
            ),
        )


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_df = etf_df.copy()


# ---------------------------------------------------------
# Category filter
# ---------------------------------------------------------

if selected_categories:

    def category_match(value):

        if pd.isna(value):
            return False

        ticker_categories = {
            category.strip()
            for category in str(value).split(",")
        }

        return bool(
            ticker_categories.intersection(
                selected_categories
            )
        )


    filtered_df = filtered_df[
        filtered_df["Categories"].apply(
            category_match
        )
    ]


# ---------------------------------------------------------
# Trend filter
# ---------------------------------------------------------

if selected_trends:

    filtered_df = filtered_df[
        filtered_df["Trend"].isin(
            selected_trends
        )
    ]


# ---------------------------------------------------------
# ETF score
# ---------------------------------------------------------

if "ETF Score" in filtered_df.columns:

    filtered_df = filtered_df[
        filtered_df["ETF Score"].fillna(-1)
        >= minimum_score
    ]


# ---------------------------------------------------------
# Momentum
# ---------------------------------------------------------

if "Momentum Score" in filtered_df.columns:

    filtered_df = filtered_df[
        filtered_df[
            "Momentum Score"
        ].fillna(-1)
        >= minimum_momentum
    ]


# ---------------------------------------------------------
# Performance
# ---------------------------------------------------------

performance_filters = {
    "Return 1M %": min_1m,
    "Return 3M %": min_3m,
    "Return 6M %": min_6m,
    "Return 1Y %": min_1y,
}


for column, minimum in (
    performance_filters.items()
):

    if column in filtered_df.columns:

        filtered_df = filtered_df[
            filtered_df[column].fillna(
                float("-inf")
            )
            >= minimum
        ]


# ---------------------------------------------------------
# Moving averages
# ---------------------------------------------------------

if (
    require_above_sma50
    and "Above SMA 50" in filtered_df.columns
):

    filtered_df = filtered_df[
        filtered_df["Above SMA 50"]
    ]


if (
    require_above_sma200
    and "Above SMA 200" in filtered_df.columns
):

    filtered_df = filtered_df[
        filtered_df["Above SMA 200"]
    ]


if (
    require_golden_trend
    and "SMA 50 Above SMA 200"
    in filtered_df.columns
):

    filtered_df = filtered_df[
        filtered_df[
            "SMA 50 Above SMA 200"
        ]
    ]


# ---------------------------------------------------------
# RSI
# ---------------------------------------------------------

if "RSI 14" in filtered_df.columns:

    filtered_df = filtered_df[
        filtered_df["RSI 14"].between(
            rsi_range[0],
            rsi_range[1],
            inclusive="both",
        )
    ]


# ---------------------------------------------------------
# Volatility
# ---------------------------------------------------------

if "Volatility %" in filtered_df.columns:

    filtered_df = filtered_df[
        filtered_df[
            "Volatility %"
        ].fillna(float("inf"))
        <= max_volatility
    ]


# ---------------------------------------------------------
# Drawdown
# ---------------------------------------------------------

if "Max Drawdown %" in filtered_df.columns:

    drawdown_magnitude = (
        filtered_df[
            "Max Drawdown %"
        ]
        .abs()
    )

    #filtered_df = filtered============================
# SORTING
# =========================================================

st.markdown("---")


sort_options = [
    column
    for column in [
        "ETF Score",
        "Momentum Score",
        "Trend Score",
        "Risk Score",
        "Return 1M %",
        "Return 3M %",
        "Return 6M %",
        "Return YTD %",
        "Return 1Y %",
        "Relative Strength 3M %",
        "Volatility %",
        "Dividend Yield %",
    ]
    if column in filtered_df.columns
]


sort_col1, sort_col2 = st.columns(
    [
        2,
        1,
    ]
)


with sort_col1:

    sort_by = st.selectbox(
        "Rank ETFs By",
        options=sort_options,
        index=(
            sort_options.index(
                "ETF Score"
            )
            if "ETF Score"
            in sort_options
            else 0
        ),
    )


with sort_col2:

    sort_direction = st.radio(
        "Direction",
        options=[
            "Highest First",
            "Lowest First",
        ],
        horizontal=True,
    )


ascending = (
    sort_direction
    == "Lowest First"
)


if sort_by:

    filtered_df = (
        filtered_df
        .sort_values(
            sort_by,
            ascending=ascending,
            na_position="last",
        )
        .reset_index(drop=True)
    )


# =========================================================
# RESULTS SUMMARY
# =========================================================

result_count = len(filtered_df)

universe_count = len(etf_df)


metric_col1, metric_col2, metric_col3 = (
    st.columns(3)
)


with metric_col1:

    st.metric(
        "Matching ETFs",
        result_count,
    )


with metric_col2:

    st.metric(
        "ETF Universe",
        universe_count,
    )


with metric_col3:

    if (
        result_count > 0
        and "ETF Score"
        in filtered_df.columns
    ):

        top_score = filtered_df[
            "ETF Score"
        ].max()

        if pd.notna(top_score):

            st.metric(
                "Highest ETF Score",
                f"{top_score:.1f}",
            )

        else:

            st.metric(
                "Highest ETF Score",
                "N/A",
            )

    else:

        st.metric(
            "Highest ETF Score",
            "N/A",
        )


# =========================================================
# SCREENER RESULTS
# =========================================================

st.markdown("## ETF Rankings")


if filtered_df.empty:

    st.warning(
        "No ETFs match the current filters. "
        "Try relaxing one or more screening criteria."
    )

else:

    display_columns = [
        "Ticker",
        "Name",
        "Categories",
        "Price",
        "ETF Score",
        "Trend",
        "Momentum Score",
        "Trend Score",
        "Risk Score",
        "Return 1M %",
        "Return 3M %",
        "Return 6M %",
        "Return YTD %",
        "Return 1Y %",
        "Relative Strength 3M %",
        "RSI 14",
        "52W High Distance %",
        "Volatility %",
        "Max Drawdown %",
        "Average Volume",
    ]


    display_columns = [
        column
        for column in display_columns
        if column in filtered_df.columns
    ]


    display_df = filtered_df[
        display_columns
    ].copy()


    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=650,
        column_config={

            "Ticker":
                st.column_config.TextColumn(
                    "Ticker",
                    width="small",
                ),

            "Name":
                st.column_config.TextColumn(
                    "ETF",
                    width="medium",
                ),

            "Categories":
                st.column_config.TextColumn(
                    "Category",
                    width="medium",
                ),

            "Price":
                st.column_config.NumberColumn(
                    "Price",
                    format="$%.2f",
                ),

            "ETF Score":
                st.column_config.NumberColumn(
                    "Score",
                    format="%.1f",
                ),

            "Momentum Score":
                st.column_config.NumberColumn(
                    "Momentum",
                    format="%.1f",
                ),

            "Trend Score":
                st.column_config.NumberColumn(
                    "Trend Score",
                    format="%.1f",
                ),

            "Risk Score":
                st.column_config.NumberColumn(
                    "Risk",
                    format="%.1f",
                ),

            "Return 1M %":
                st.column_config.NumberColumn(
                    "1M",
                    format="%.2f%%",
                ),

            "Return 3M %":
                st.column_config.NumberColumn(
                    "3M",
                    format="%.2f%%",
                ),

            "Return 6M %":
                st.column_config.NumberColumn(
                    "6M",
                    format="%.2f%%",
                ),

            "Return YTD %":
                st.column_config.NumberColumn(
                    "YTD",
                    format="%.2f%%",
                ),

            "Return 1Y %":
                st.column_config.NumberColumn(
                    "1Y",
                    format="%.2f%%",
                ),

            "Relative Strength 3M %":
                st.column_config.NumberColumn(
                    "RS 3M",
                    format="%.2f%%",
                ),

            "RSI 14":
                st.column_config.NumberColumn(
                    "RSI",
                    format="%.1f",
                ),

            "52W High Distance %":
                st.column_config.NumberColumn(
                    "From 52W High",
                    format="%.2f%%",
                ),

            "Volatility %":
                st.column_config.NumberColumn(
                    "Volatility",
                    format="%.2f%%",
                ),

            "Max Drawdown %":
                st.column_config.NumberColumn(
                    "Max Drawdown",
                    format="%.2f%%",
                ),

            "Average Volume":
                st.column_config.NumberColumn(
                    "Avg Volume",
                    format="%.0f",
                ),
        },
    )


# =========================================================
# TOP 10 SNAPSHOT
# =========================================================

if not filtered_df.empty:

    st.markdown("---")

    st.markdown(
        f"## 🏆 Top ETFs by {sort_by}"
    )


    top_snapshot = (
        filtered_df
        .head(10)
        .copy()
    )


    snapshot_columns = [
        "Ticker",
        "ETF Score",
        "Trend",
        "Momentum Score",
        "Return 3M %",
        "Return 1Y %",
    ]


    snapshot_columns = [
        column
        for column in snapshot_columns
        if column in top_snapshot.columns
    ]


    st.dataframe(
        top_snapshot[
            snapshot_columns
        ],
        use_container_width=True,
        hide_index=True,
        column_config={

            "ETF Score":
                st.column_config.NumberColumn(
                    "Score",
                    format="%.1f",
                ),

            "Momentum Score":
                st.column_config.NumberColumn(
                    "Momentum",
                    format="%.1f",
                ),

            "Return 3M %":
                st.column_config.NumberColumn(
                    "3M",
                    format="%.2f%%",
                ),

            "Return 1Y %":
                st.column_config.NumberColumn(
                    "1Y",
                    format="%.2f%%",
                ),
        },
    )


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.caption(
    "MarketScope ETF rankings are quantitative screening "
    "tools for informational and educational purposes only. "
    "They are not investment recommendations."
)
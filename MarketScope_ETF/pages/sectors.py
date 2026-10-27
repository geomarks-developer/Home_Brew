import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from sector_engine import analyze_sectors


# =========================================================
# PAGE HEADER
# =========================================================

st.title("🌎 Market & Sectors")

st.caption(
    "Track sector leadership, momentum, relative performance, "
    "and market rotation across the 11 major U.S. sectors."
)


# =========================================================
# LOAD SHARED MARKET DATA
# =========================================================

market_data = st.session_state.get("market_data")

if market_data is None:
    st.error(
        "Shared MarketScope ETF data is not loaded. "
        "Restart the application."
    )
    st.stop()


sector_df = market_data.get(
    "sector_df",
    pd.DataFrame(),
).copy()


if sector_df.empty:
    st.warning(
        "Sector analysis data is currently unavailable."
    )
    st.stop()


# =========================================================
# RUN SECTOR ANALYSIS
# =========================================================

sector_data = analyze_sectors(
    sector_df
)

rankings = sector_data["rankings"]

summary = sector_data["summary"]


if rankings.empty:
    st.warning(
        "Sector rankings could not be calculated."
    )
    st.stop()


# =========================================================
# SUMMARY METRICS
# =========================================================

top_sector = summary.get(
    "top_sector",
    "N/A",
)

top_sector_ticker = summary.get(
    "top_sector_ticker",
    "",
)

top_sector_score = summary.get(
    "top_sector_score",
)

bottom_sector = summary.get(
    "bottom_sector",
    "N/A",
)

bottom_sector_ticker = summary.get(
    "bottom_sector_ticker",
    "",
)

average_score = summary.get(
    "average_score",
)


# Count improving sectors

improving_count = 0

if "Rotation" in rankings.columns:
    improving_count = (
        rankings["Rotation"]
        .eq("Improving")
        .sum()
    )


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "Leading Sector",
        top_sector,
        top_sector_ticker,
    )


with col2:

    if pd.notna(top_sector_score):

        st.metric(
            "Leader Score",
            f"{top_sector_score:.1f}",
        )

    else:

        st.metric(
            "Leader Score",
            "N/A",
        )


with col3:

    st.metric(
        "Improving Sectors",
        f"{improving_count}",
    )


with col4:

    st.metric(
        "Weakest Sector",
        bottom_sector,
        bottom_sector_ticker,
    )


# =========================================================
# SECTOR LEADERSHIP CHART
# =========================================================

st.markdown("---")

st.markdown("## Sector Leadership")


chart_df = rankings.copy()

chart_df["Sector Score"] = pd.to_numeric(
    chart_df["Sector Score"],
    errors="coerce",
)

chart_df = chart_df.dropna(
    subset=[
        "Sector Score",
    ]
)


if not chart_df.empty:

    chart_df = chart_df.sort_values(
        "Sector Score",
        ascending=True,
    )


    fig = px.bar(
        chart_df,
        x="Sector Score",
        y="Sector",
        orientation="h",
        color="Sector Score",
        color_continuous_scale=[
            [0.00, "#b91c1c"],
            [0.35, "#ef4444"],
            [0.50, "#f59e0b"],
            [0.65, "#84cc16"],
            [1.00, "#15803d"],
        ],
        hover_data={
            "Ticker": True,
            "Sector Score": ":.2f",
            "Rotation": True,
        },
    )


    fig.update_layout(
        height=520,
        showlegend=False,
        coloraxis_showscale=False,
        xaxis_title="Sector Score",
        yaxis_title="",
        margin=dict(
            l=10,
            r=20,
            t=10,
            b=30,
        ),
    )


    fig.update_traces(
        texttemplate="%{x:.1f}",
        textposition="outside",
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# =========================================================
# PERFORMANCE PERIOD SELECTOR
# =========================================================

st.markdown("---")

st.markdown("## Sector Performance")


period_options = {
    "1 Day": "Return 1D %",
    "1 Week": "Return 1W %",
    "1 Month": "Return 1M %",
    "3 Months": "Return 3M %",
    "6 Months": "Return 6M %",
    "YTD": "Return YTD %",
    "1 Year": "Return 1Y %",
}


available_periods = {
    label: column
    for label, column in period_options.items()
    if column in rankings.columns
}


if available_periods:

    period_label = st.radio(
        "Performance Period",
        options=list(
            available_periods.keys()
        ),
        index=2 if len(available_periods) > 2 else 0,
        horizontal=True,
    )


    period_column = available_periods[
        period_label
    ]


    performance_df = rankings[
        [
            "Sector",
            "Ticker",
            period_column,
        ]
    ].copy()


    performance_df[
        period_column
    ] = pd.to_numeric(
        performance_df[
            period_column
        ],
        errors="coerce",
    )


    performance_df = performance_df.dropna(
        subset=[
            period_column,
        ]
    )


    performance_df = (
        performance_df
        .sort_values(
            period_column,
            ascending=True,
        )
    )


    if not performance_df.empty:

        performance_df["Direction"] = (
            performance_df[
                period_column
            ]
            .apply(
                lambda value:
                "Positive"
                if value >= 0
                else "Negative"
            )
        )


        fig = px.bar(
            performance_df,
            x=period_column,
            y="Sector",
            orientation="h",
            color="Direction",
            color_discrete_map={
                "Positive": "#16a34a",
                "Negative": "#dc2626",
            },
            hover_data={
                "Ticker": True,
                period_column: ":.2f",
                "Direction": False,
            },
        )


        fig.update_layout(
            height=500,
            showlegend=False,
            xaxis_title=(
                f"{period_label} Return (%)"
            ),
            yaxis_title="",
            margin=dict(
                l=10,
                r=20,
                t=10,
                b=30,
            ),
        )


        fig.add_vline(
            x=0,
            line_width=1,
            line_color="gray",
        )


        fig.update_traces(
            texttemplate="%{x:.2f}%",
            textposition="outside",
        )


        st.plotly_chart(
            fig,
            use_container_width=True,
        )


else:

    st.info(
        "Sector performance history is unavailable."
    )


# =========================================================
# ROTATION MAP
# =========================================================

st.markdown("---")

st.markdown("## 🔄 Sector Rotation Map")

st.caption(
    "Compare recent sector performance with intermediate-term "
    "performance to help identify improving and weakening trends."
)


rotation_required = [
    "Return 1M %",
    "Return 3M %",
]


if all(
    column in rankings.columns
    for column in rotation_required
):

    rotation_df = rankings.copy()


    rotation_df["Return 1M %"] = (
        pd.to_numeric(
            rotation_df["Return 1M %"],
            errors="coerce",
        )
    )


    rotation_df["Return 3M %"] = (
        pd.to_numeric(
            rotation_df["Return 3M %"],
            errors="coerce",
        )
    )


    rotation_df = rotation_df.dropna(
        subset=[
            "Return 1M %",
            "Return 3M %",
        ]
    )


    if not rotation_df.empty:

        fig = px.scatter(
            rotation_df,
            x="Return 3M %",
            y="Return 1M %",
            text="Sector",
            color="Rotation",
            hover_name="Ticker",
            hover_data={
                "Sector Score": ":.2f",
                "Return 3M %": ":.2f",
                "Return 1M %": ":.2f",
            },
            color_discrete_map={
                "Improving": "#16a34a",
                "Stable": "#2563eb",
                "Cooling": "#f59e0b",
                "Weakening": "#dc2626",
                "Unknown": "#6b7280",
            },
        )


        fig.update_traces(
            textposition="top center",
            marker=dict(
                size=15,
                line=dict(
                    width=1,
                    color="white",
                ),
            ),
        )


        fig.add_hline(
            y=0,
            line_width=1,
            line_dash="dot",
            line_color="gray",
        )


        fig.add_vline(
            x=0,
            line_width=1,
            line_dash="dot",
            line_color="gray",
        )


        fig.update_layout(
            height=600,
            xaxis_title="3-Month Return (%)",
            yaxis_title="1-Month Return (%)",
            margin=dict(
                l=20,
                r=20,
                t=20,
                b=20,
            ),
        )


        st.plotly_chart(
            fig,
            use_container_width=True,
        )


# =========================================================
# MOMENTUM COMPARISON
# =========================================================

st.markdown("---")

st.markdown("## 📈 Sector Momentum")


momentum_columns = [
    "Sector",
    "Return 1M %",
    "Return 3M %",
    "Return 6M %",
]


available_momentum_columns = [
    column
    for column in momentum_columns
    if column in rankings.columns
]


if len(available_momentum_columns) > 1:

    momentum_df = rankings[
        available_momentum_columns
    ].copy()


    value_columns = [
        column
        for column in available_momentum_columns
        if column != "Sector"
    ]


    for column in value_columns:

        momentum_df[column] = (
            pd.to_numeric(
                momentum_df[column],
                errors="coerce",
            )
        )


    momentum_long = momentum_df.melt(
        id_vars="Sector",
        value_vars=value_columns,
        var_name="Period",
        value_name="Return",
    )


    momentum_long["Period"] = (
        momentum_long["Period"]
        .str.replace(
            "Return ",
            "",
            regex=False,
        )
        .str.replace(
            " %",
            "",
            regex=False,
        )
    )


    fig = px.bar(
        momentum_long,
        x="Sector",
        y="Return",
        color="Period",
        barmode="group",
        labels={
            "Return": "Return (%)",
            "Sector": "",
        },
    )


    fig.update_layout(
        height=500,
        legend_title_text="Period",
        xaxis_tickangle=-40,
        margin=dict(
            l=20,
            r=20,
            t=20,
            b=80,
        ),
    )


    fig.add_hline(
        y=0,
        line_width=1,
        line_color="gray",
    )


    st.plotly_chart(
        fig,
        use_container_width=True,
    )


# =========================================================
# SECTOR RANKING TABLE
# =========================================================

st.markdown("---")

st.markdown("## 📋 Sector Rankings")


ranking_columns = [
    "Rank",
    "Sector",
    "Ticker",
    "Sector Score",
    "Sector Strength",
    "Rotation",
    "Trend",
    "Return 1M %",
    "Return 3M %",
    "Return 6M %",
    "Return YTD %",
    "Return 1Y %",
    "RSI 14",
]


ranking_columns = [
    column
    for column in ranking_columns
    if column in rankings.columns
]


display_df = rankings[
    ranking_columns
].copy()


st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank":
            st.column_config.NumberColumn(
                "Rank",
                format="%d",
            ),

        "Sector Score":
            st.column_config.NumberColumn(
                "Score",
                format="%.2f",
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

        "RSI 14":
            st.column_config.NumberColumn(
                "RSI",
                format="%.1f",
            ),
    },
)


# =========================================================
# LEADERS / LAGGARDS
# =========================================================

st.markdown("---")

left_column, right_column = st.columns(2)


with left_column:

    st.markdown(
        "### 🟢 Sector Leaders"
    )


    leaders = (
        rankings
        .head(3)
        .copy()
    )


    for _, row in leaders.iterrows():

        sector = row.get(
            "Sector",
            ""
        )

        ticker = row.get(
            "Ticker",
            ""
        )

        score = row.get(
            "Sector Score",
        )

        rotation = row.get(
            "Rotation",
            ""
        )


        if pd.notna(score):

            st.success(
                f"**{sector} ({ticker})**  \n"
                f"Sector Score: {score:.1f}  \n"
                f"Rotation: {rotation}"
            )


with right_column:

    st.markdown(
        "### 🔴 Sector Laggards"
    )


    laggards = (
        rankings
        .tail(3)
        .sort_values(
            "Sector Score",
            ascending=True,
        )
        .copy()
    )


    for _, row in laggards.iterrows():

        sector = row.get(
            "Sector",
            ""
        )

        ticker = row.get(
            "Ticker",
            ""
        )

        score = row.get(
            "Sector Score",
        )

        rotation = row.get(
            "Rotation",
            ""
        )


        if pd.notna(score):

            st.error(
                f"**{sector} ({ticker})**  \n"
                f"Sector Score: {score:.1f}  \n"
                f"Rotation: {rotation}"
            )


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.caption(
    "Sector rankings and rotation classifications are "
    "quantitative MarketScope indicators derived from historical "
    "ETF price data. They are provided for informational and "
    "educational purposes and are not investment advice."
)
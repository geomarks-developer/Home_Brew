import pandas as pd
import plotly.express as px
import streamlit as st

from sector_engine import analyze_sectors


# =========================================================
# PAGE HEADER
# =========================================================

st.title("📊 MarketScope ETF")

st.subheader("ETF & Sector Market Dashboard")

st.caption(
    "Identify ETF momentum, sector leadership, market trends, "
    "and relative strength across the MarketScope ETF universe."
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


etf_df = market_data.get(
    "etf_df",
    pd.DataFrame(),
).copy()

sector_df = market_data.get(
    "sector_df",
    pd.DataFrame(),
).copy()

metadata = market_data.get(
    "metadata",
    {},
)


if etf_df.empty:
    st.warning(
        "ETF analysis data is currently unavailable."
    )
    st.stop()


# =========================================================
# SECTOR ANALYSIS
# =========================================================

sector_data = analyze_sectors(
    sector_df
)

sector_rankings = sector_data[
    "rankings"
]

sector_summary = sector_data[
    "summary"
]


# =========================================================
# MARKET OVERVIEW
# =========================================================

st.markdown("## Market Overview")

total_etfs = len(etf_df)

uptrend_count = 0
strong_uptrend_count = 0

if "Trend" in etf_df.columns:

    uptrend_count = (
        etf_df["Trend"]
        .isin(
            [
                "Uptrend",
                "Strong Uptrend",
            ]
        )
        .sum()
    )

    strong_uptrend_count = (
        etf_df["Trend"]
        .eq("Strong Uptrend")
        .sum()
    )


average_score = None

if "ETF Score" in etf_df.columns:

    average_score = pd.to_numeric(
        etf_df["ETF Score"],
        errors="coerce",
    ).mean()


top_sector = sector_summary.get(
    "top_sector"
)


col1, col2, col3, col4 = st.columns(4)


with col1:

    st.metric(
        "ETF Universe",
        f"{total_etfs}",
    )


with col2:

    st.metric(
        "ETFs in Uptrend",
        f"{uptrend_count}",
    )


with col3:

    if pd.notna(average_score):

        st.metric(
            "Average ETF Score",
            f"{average_score:.1f}",
        )

    else:

        st.metric(
            "Average ETF Score",
            "N/A",
        )


with col4:

    st.metric(
        "Leading Sector",
        (
            top_sector
            if top_sector
            else "N/A"
        ),
    )


# =========================================================
# MARKET BREADTH
# =========================================================

st.markdown("---")

st.markdown("## Market Breadth")


if total_etfs > 0:

    uptrend_pct = (
        uptrend_count
        / total_etfs
        * 100
    )

    strong_uptrend_pct = (
        strong_uptrend_count
        / total_etfs
        * 100
    )

else:

    uptrend_pct = 0
    strong_uptrend_pct = 0


breadth_col1, breadth_col2 = st.columns(2)


with breadth_col1:

    st.metric(
        "ETF Universe in Uptrend",
        f"{uptrend_pct:.1f}%",
    )

    st.progress(
        min(
            max(
                uptrend_pct / 100,
                0,
            ),
            1,
        )
    )


with breadth_col2:

    st.metric(
        "Strong Uptrends",
        f"{strong_uptrend_pct:.1f}%",
    )

    st.progress(
        min(
            max(
                strong_uptrend_pct / 100,
                0,
            ),
            1,
        )
    )


# =========================================================
# TOP ETFs
# =========================================================

st.markdown("---")

st.markdown("## 🏆 Top ETFs")


if "ETF Score" in etf_df.columns:

    top_etfs = (
        etf_df
        .dropna(
            subset=[
                "ETF Score",
            ]
        )
        .sort_values(
            "ETF Score",
            ascending=False,
        )
        .head(10)
        .copy()
    )

else:

    top_etfs = pd.DataFrame()


if top_etfs.empty:

    st.info(
        "ETF rankings are not currently available."
    )

else:

    display_columns = [
        "Ticker",
        "Name",
        "Categories",
        "ETF Score",
        "Trend",
        "Return 1M %",
        "Return 3M %",
        "Return 6M %",
        "Return 1Y %",
        "RSI 14",
    ]

    display_columns = [
        column
        for column in display_columns
        if column in top_etfs.columns
    ]


    st.dataframe(
        top_etfs[
            display_columns
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "ETF Score": st.column_config.NumberColumn(
                "ETF Score",
                format="%.1f",
            ),
            "Return 1M %": st.column_config.NumberColumn(
                "1M",
                format="%.2f%%",
            ),
            "Return 3M %": st.column_config.NumberColumn(
                "3M",
                format="%.2f%%",
            ),
            "Return 6M %": st.column_config.NumberColumn(
                "6M",
                format="%.2f%%",
            ),
            "Return 1Y %": st.column_config.NumberColumn(
                "1Y",
                format="%.2f%%",
            ),
            "RSI 14": st.column_config.NumberColumn(
                "RSI",
                format="%.1f",
            ),
        },
    )


# =========================================================
# SECTOR LEADERSHIP
# =========================================================

st.markdown("---")

st.markdown("## 🌎 Sector Leadership")


if sector_rankings.empty:

    st.info(
        "Sector rankings are not currently available."
    )

else:

    chart_data = sector_rankings.copy()

    chart_data["Sector Score"] = pd.to_numeric(
        chart_data["Sector Score"],
        errors="coerce",
    )


    chart_data = chart_data.dropna(
        subset=[
            "Sector Score",
        ]
    )


    if not chart_data.empty:

        fig = px.bar(
            chart_data.sort_values(
                "Sector Score",
                ascending=True,
            ),
            x="Sector Score",
            y="Sector",
            orientation="h",
            color="Sector Score",
            color_continuous_scale=[
                "#d73027",
                "#fee08b",
                "#1a9850",
            ],
            labels={
                "Sector Score":
                    "Sector Score",
            },
        )


        fig.update_layout(
            height=500,
            showlegend=False,
            coloraxis_showscale=False,
            margin=dict(
                l=10,
                r=10,
                t=10,
                b=10,
            ),
        )


        st.plotly_chart(
            fig,
            width="stretch",
        )


# =========================================================
# SECTOR LEADERS AND LAGGARDS
# =========================================================

if not sector_rankings.empty:

    leader_col, laggard_col = (
        st.columns(2)
    )


    with leader_col:

        st.markdown(
            "### 🟢 Leading Sectors"
        )

        leaders = (
            sector_rankings
            .head(5)
            .copy()
        )


        leader_columns = [
            "Rank",
            "Sector",
            "Ticker",
            "Sector Score",
            "Rotation",
        ]


        leader_columns = [
            column
            for column in leader_columns
            if column in leaders.columns
        ]


        st.dataframe(
            leaders[
                leader_columns
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Sector Score":
                    st.column_config.NumberColumn(
                        "Score",
                        format="%.2f",
                    ),
            },
        )


    with laggard_col:

        st.markdown(
            "### 🔴 Lagging Sectors"
        )


        laggards = (
            sector_rankings
            .tail(5)
            .sort_values(
                "Sector Score",
                ascending=True,
            )
            .copy()
        )


        laggard_columns = [
            "Rank",
            "Sector",
            "Ticker",
            "Sector Score",
            "Rotation",
        ]


        laggard_columns = [
            column
            for column in laggard_columns
            if column in laggards.columns
        ]


        st.dataframe(
            laggards[
                laggard_columns
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Sector Score":
                    st.column_config.NumberColumn(
                        "Score",
                        format="%.2f",
                    ),
            },
        )


# =========================================================
# ETF MOMENTUM LEADERS
# =========================================================

st.markdown("---")

st.markdown("## 🚀 ETF Momentum Leaders")


if "Momentum Score" in etf_df.columns:

    momentum_df = (
        etf_df
        .dropna(
            subset=[
                "Momentum Score",
            ]
        )
        .sort_values(
            "Momentum Score",
            ascending=False,
        )
        .head(10)
        .copy()
    )


    momentum_columns = [
        "Ticker",
        "Name",
        "Categories",
        "Momentum Score",
        "Trend",
        "Return 1M %",
        "Return 3M %",
        "Return 6M %",
    ]


    momentum_columns = [
        column
        for column in momentum_columns
        if column in momentum_df.columns
    ]


    st.dataframe(
        momentum_df[
            momentum_columns
        ],
        width="stretch",
        hide_index=True,
        column_config={
            "Momentum Score":
                st.column_config.NumberColumn(
                    "Momentum",
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
        },
    )


# =========================================================
# DATA STATUS
# =========================================================

st.markdown("---")

with st.expander("📡 MarketScope Data Status"):

    last_refresh = metadata.get("last_refresh")
    source = metadata.get("loaded_from", "Unknown")
    available = metadata.get(
        "available_ticker_count",
        len(etf_df),
    )
    missing = metadata.get(
        "missing_ticker_count",
        0,
    )
    disk_cache_saved = metadata.get(
        "disk_cache_saved",
        "Unknown",
    )

    if isinstance(last_refresh, pd.Timestamp):
        last_refresh_display = last_refresh.strftime(
            "%B %d, %Y at %I:%M %p"
        )
    elif hasattr(last_refresh, "strftime"):
        last_refresh_display = last_refresh.strftime(
            "%B %d, %Y at %I:%M %p"
        )
    elif last_refresh:
        last_refresh_display = str(last_refresh)
    else:
        last_refresh_display = "Unknown"

    source_display = str(source).replace("_", " ").title()
    available_display = str(available)
    missing_display = str(missing)
    cache_display = str(disk_cache_saved)

    status_col1, status_col2 = st.columns(2)

    with status_col1:
        st.markdown(
            f"""
            **Data source:** {source_display}

            **ETFs available:** {available_display}

            **Missing ETFs:** {missing_display}
            """
        )

    with status_col2:
        st.markdown(
            f"""
            **Last refresh:** {last_refresh_display}

            **Disk cache saved:** {cache_display}
            """
        )


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.caption(
    "MarketScope ETF is provided for informational and "
    "educational purposes only. Rankings, trends, scores, "
    "and other indicators are not investment advice."
)
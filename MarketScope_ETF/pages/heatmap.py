import pandas as pd
import plotly.express as px
import streamlit as st
from sector_engine import analyze_sectors
from config import ETF_CATEGORIES


# =========================================================
# PAGE HEADER
# =========================================================

st.title("🔥 ETF Heatmap")

st.caption(
    "Visualize ETF and sector performance across multiple "
    "time periods using the shared MarketScope ETF dataset."
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

sector_df = market_data.get(
    "sector_df",
    pd.DataFrame(),
).copy()


sector_df = market_data.get(
    "sector_df",
    pd.DataFrame(),
).copy()

sector_data = analyze_sectors(sector_df)

sector_rankings = sector_data["rankings"]


if etf_df.empty:
    st.warning(
        "ETF analysis data is currently unavailable."
    )
    st.stop()


# =========================================================
# PERFORMANCE PERIODS
# =========================================================

PERIOD_COLUMNS = {
    "1 Day": "Return 1D %",
    "1 Week": "Return 1W %",
    "1 Month": "Return 1M %",
    "3 Months": "Return 3M %",
    "6 Months": "Return 6M %",
    "YTD": "Return YTD %",
    "1 Year": "Return 1Y %",
}


# =========================================================
# CATEGORY HELPERS
# =========================================================

ASSET_CLASS_CATEGORIES = [
    "Broad Market",
    "International",
    "Bonds",
    "Real Estate",
    "Commodities",
]


STYLE_CATEGORIES = [
    "Growth",
    "Value",
    "Dividend",
    "Factor / Quality",
    "Thematic / Industry",
]


def get_tickers_for_categories(
    categories: list[str],
) -> list[str]:
    """
    Return unique ETF tickers belonging to the selected
    MarketScope categories.
    """

    tickers = []

    for category in categories:

        category_tickers = ETF_CATEGORIES.get(
            category,
            [],
        )

        tickers.extend(
            category_tickers
        )

    return list(
        dict.fromkeys(tickers)
    )


# =========================================================
# TREEMAP HELPER
# =========================================================

def create_heatmap(
    data: pd.DataFrame,
    performance_column: str,
    title: str,
    path: list[str],
):
    """
    Build a Plotly treemap using ETF performance
    as the color scale.
    """

    if data.empty:
        return None

    if performance_column not in data.columns:
        return None

    chart_data = data.copy()

    chart_data[performance_column] = pd.to_numeric(
        chart_data[performance_column],
        errors="coerce",
    )

    chart_data = chart_data.dropna(
        subset=[
            performance_column,
        ]
    )

    if chart_data.empty:
        return None


    # -----------------------------------------------------
    # Equal tile weighting
    # -----------------------------------------------------
    #
    # Later we can replace this with AUM weighting when
    # fund metadata is added.
    #

    chart_data["Tile Size"] = 1


    # -----------------------------------------------------
    # Determine symmetrical color range
    # -----------------------------------------------------

    largest_move = (
        chart_data[
            performance_column
        ]
        .abs()
        .max()
    )


    if (
        pd.isna(largest_move)
        or largest_move == 0
    ):
        largest_move = 1


    # Prevent one extreme ETF from making everything else
    # appear nearly white.
    color_limit = min(
        largest_move,
        15,
    )


    fig = px.treemap(
        chart_data,
        path=path,
        values="Tile Size",
        color=performance_column,
        color_continuous_scale=[
            "#b91c1c",
            "#ef4444",
            "#fca5a5",
            "#f3f4f6",
            "#86efac",
            "#22c55e",
            "#15803d",
        ],
        color_continuous_midpoint=0,
        range_color=[
            -color_limit,
            color_limit,
        ],
        custom_data=[
            performance_column,
            "ETF Score"
            if "ETF Score" in chart_data.columns
            else performance_column,
            "Trend"
            if "Trend" in chart_data.columns
            else performance_column,
        ],
    )


    fig.update_traces(
        texttemplate=(
            "<b>%{label}</b>"
            "<br>"
            "%{customdata[0]:+.2f}%"
        ),
        hovertemplate=(
            "<b>%{label}</b>"
            "<br>"
            f"{title}: "
            "%{customdata[0]:+.2f}%"
            "<extra></extra>"
        ),
        marker=dict(
            line=dict(
                color="white",
                width=2,
            )
        ),
    )


    fig.update_layout(
        height=700,
        margin=dict(
            l=5,
            r=5,
            t=30,
            b=5,
        ),
        coloraxis_colorbar=dict(
            title="Return %",
            ticksuffix="%",
        ),
    )

    return fig


# =========================================================
# CONTROLS
# =========================================================

control_col1, control_col2 = st.columns(
    [1, 3]
)


with control_col1:

    selected_period = st.selectbox(
        "Performance Period",
        options=list(
            PERIOD_COLUMNS.keys()
        ),
        index=2,
    )


performance_column = PERIOD_COLUMNS[
    selected_period
]


with control_col2:

    if performance_column in etf_df.columns:

        valid_returns = pd.to_numeric(
            etf_df[
                performance_column
            ],
            errors="coerce",
        ).dropna()


        if not valid_returns.empty:

            positive_count = (
                valid_returns > 0
            ).sum()

            negative_count = (
                valid_returns < 0
            ).sum()

            average_return = (
                valid_returns.mean()
            )


            metric1, metric2, metric3 = (
                st.columns(3)
            )


            metric1.metric(
                "Positive ETFs",
                int(positive_count),
            )


            metric2.metric(
                "Negative ETFs",
                int(negative_count),
            )


            metric3.metric(
                "Average Return",
                f"{average_return:+.2f}%",
            )


# =========================================================
# CHECK PERIOD AVAILABILITY
# =========================================================

if performance_column not in etf_df.columns:

    st.warning(
        f"{selected_period} performance data is not "
        "currently available."
    )

    st.stop()


# =========================================================
# TABS
# =========================================================

all_tab, sector_tab, asset_tab, style_tab = st.tabs(
    [
        "🌐 All ETFs",
        "🏭 Sectors",
        "🧭 Asset Classes",
        "🎯 Style & Strategy",
    ]
)


# =========================================================
# ALL ETF HEATMAP
# =========================================================

with all_tab:

    st.markdown(
        f"### All ETFs · {selected_period}"
    )


    all_heatmap_data = (
        etf_df
        .copy()
    )


    fig = create_heatmap(
        data=all_heatmap_data,
        performance_column=performance_column,
        title=selected_period,
        path=[
            "Categories",
            "Ticker",
        ],
    )


    if fig is None:

        st.info(
            "No ETF performance data is available "
            "for this period."
        )

    else:

        st.plotly_chart(
            fig,
            width="stretch",
            key="all_etf_heatmap",
        )


# =========================================================
# SECTOR HEATMAP
# =========================================================

with sector_tab:

    st.markdown(
        f"### Sector Performance · {selected_period}"
    )


    if sector_df.empty:

        st.info(
            "Sector data is currently unavailable."
        )

    else:

        fig = create_heatmap(
            data=sector_df,
            performance_column=performance_column,
            title=selected_period,
            path=[
                "Sector",
                "Ticker",
            ],
        )


        if fig is None:

            st.info(
                "No sector performance data is "
                "available for this period."
            )

        else:

            st.plotly_chart(
                fig,
                width="stretch",
                key="sector_heatmap",
            )


# =========================================================
# ASSET CLASS HEATMAP
# =========================================================

with asset_tab:

    st.markdown(
        f"### Asset Classes · {selected_period}"
    )


    asset_tickers = (
        get_tickers_for_categories(
            ASSET_CLASS_CATEGORIES
        )
    )


    asset_df = etf_df[
        etf_df[
            "Ticker"
        ].isin(asset_tickers)
    ].copy()


    # Build a cleaner primary display category.
    def find_asset_category(
        ticker: str,
    ) -> str:

        for category in (
            ASSET_CLASS_CATEGORIES
        ):

            if ticker in ETF_CATEGORIES.get(
                category,
                [],
            ):
                return category

        return "Other"


    asset_df[
        "Heatmap Category"
    ] = asset_df[
        "Ticker"
    ].apply(
        find_asset_category
    )


    fig = create_heatmap(
        data=asset_df,
        performance_column=performance_column,
        title=selected_period,
        path=[
            "Heatmap Category",
            "Ticker",
        ],
    )


    if fig is None:

        st.info(
            "No asset-class performance data is "
            "available for this period."
        )

    else:

        st.plotly_chart(
            fig,
            width="stretch",
            key="asset_heatmap",
        )


# =========================================================
# STYLE / STRATEGY HEATMAP
# =========================================================

with style_tab:

    st.markdown(
        f"### ETF Style & Strategy · {selected_period}"
    )


    style_tickers = (
        get_tickers_for_categories(
            STYLE_CATEGORIES
        )
    )


    style_df = etf_df[
        etf_df[
            "Ticker"
        ].isin(style_tickers)
    ].copy()


    def find_style_category(
        ticker: str,
    ) -> str:

        for category in STYLE_CATEGORIES:

            if ticker in ETF_CATEGORIES.get(
                category,
                [],
            ):
                return category

        return "Other"


    style_df[
        "Heatmap Category"
    ] = style_df[
        "Ticker"
    ].apply(
        find_style_category
    )


    fig = create_heatmap(
        data=style_df,
        performance_column=performance_column,
        title=selected_period,
        path=[
            "Heatmap Category",
            "Ticker",
        ],
    )


    if fig is None:

        st.info(
            "No style or strategy performance "
            "data is available for this period."
        )

    else:

        st.plotly_chart(
            fig,
            width="stretch",
            key="style_heatmap",
        )


# =========================================================
# PERFORMANCE LEADERS / LAGGARDS
# =========================================================

st.markdown("---")

st.markdown(
    f"## {selected_period} Leaders & Laggards"
)


ranking_df = etf_df.copy()


ranking_df[
    performance_column
] = pd.to_numeric(
    ranking_df[
        performance_column
    ],
    errors="coerce",
)


ranking_df = ranking_df.dropna(
    subset=[
        performance_column
    ]
)


leader_col, laggard_col = st.columns(2)


with leader_col:

    st.markdown(
        "### 🟢 Leaders"
    )


    leaders = (
        ranking_df
        .sort_values(
            performance_column,
            ascending=False,
        )
        .head(10)
        .copy()
    )


    leader_columns = [
        "Ticker",
        "Categories",
        performance_column,
        "ETF Score",
        "Trend",
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
            performance_column:
                st.column_config.NumberColumn(
                    selected_period,
                    format="%.2f%%",
                ),

            "ETF Score":
                st.column_config.NumberColumn(
                    "ETF Score",
                    format="%.1f",
                ),
        },
    )


with laggard_col:

    st.markdown("### 🔴 Laggards")

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
        "Ticker",
        "Categories",
        performance_column,
        "ETF Score",
        "Trend",
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
            performance_column:
                st.column_config.NumberColumn(
                    selected_period,
                    format="%.2f%%",
                ),

            "ETF Score":
                st.column_config.NumberColumn(
                    "ETF Score",
                    format="%.1f",
                ),
        },
    )


# =========================================================
# LEGEND / EXPLANATION
# =========================================================

st.markdown("---")

st.caption(
    "Green indicates positive performance and red indicates "
    "negative performance for the selected period. ETF tiles "
    "are currently equally weighted. MarketScope ETF rankings "
    "and performance measures are provided for informational "
    "and educational purposes only."
)
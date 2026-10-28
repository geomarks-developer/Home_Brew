from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from market_data import get_market_data


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _percent(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.2%}"


def _score(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"{float(value):.1f}"


def _money(value) -> str:
    if pd.isna(value):
        return "N/A"
    return f"${float(value):,.2f}"


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.header("📊 Dividend Aristocrat Summary")

st.caption(
    "A high-level view of the Dividend Aristocrat universe, including "
    "income, growth, quality, valuation, momentum, and MarketScope rankings."
)


# ---------------------------------------------------------
# Refresh controls
# ---------------------------------------------------------

refresh_col, status_col = st.columns([1, 3])

with refresh_col:
    refresh = st.button(
        "🔄 Refresh All Market Data",
        type="secondary",
        use_container_width=True,
    )


# ---------------------------------------------------------
# Load shared market data
# ---------------------------------------------------------

try:
    data = get_market_data(
        force_refresh=refresh,
        show_progress=True,
    )
except Exception as exc:
    st.error(f"Unable to load MarketScope Dividend data: {exc}")
    st.stop()


df = data.get("dividend_df", pd.DataFrame()).copy()

if df.empty:
    st.warning("No Dividend Aristocrat data is currently available.")
    st.stop()


with status_col:
    loaded_at = data.get("loaded_at", "Unknown")
    ticker_count = data.get("ticker_count", len(df))
    successful_count = data.get("successful_history_count", len(df))

    st.caption(
        f"Loaded: {loaded_at}  |  "
        f"Universe: {ticker_count} stocks  |  "
        f"Price histories: {successful_count}/{ticker_count}"
    )


# ---------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------

median_yield = pd.to_numeric(
    df.get("Dividend Yield")/100, errors="coerce"
).median()


median_growth = pd.to_numeric(
    df.get("Dividend Growth 5Y"), errors="coerce"
).median()

median_score = pd.to_numeric(
    df.get("Overall Score"), errors="coerce"
).median()

median_payout = pd.to_numeric(
    df.get("Payout Ratio"), errors="coerce"
).median()

metric1, metric2, metric3, metric4, metric5 = st.columns(5)

metric1.metric(
    "Aristocrats",
    f"{len(df)}",
)

metric2.metric(
    "Median Yield",
    _percent(median_yield),
)

metric3.metric(
    "Median 5Y Div Growth",
    _percent(median_growth),
)

metric4.metric(
    "Median Payout Ratio",
    _percent(median_payout),
)

metric5.metric(
    "Median Overall Score",
    _score(median_score),
)

st.divider()


# ---------------------------------------------------------
# Top-ranked stocks
# ---------------------------------------------------------

st.subheader("🏆 Top-Ranked Dividend Aristocrats")

rank_columns = [
    "Rank",
    "Ticker",
    "Company",
    "Sector",
    "Price",
    "Dividend Yield",
    "Dividend Growth 5Y",
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Overall Score",
    "Rating",
]


rank_columns = [
    column for column in rank_columns
    if column in df.columns
]

top_ranked = (
    df.sort_values("Overall Score", ascending=False)
    .head(10)[rank_columns]
    .copy()
)

st.dataframe(
    top_ranked,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Price": st.column_config.NumberColumn(
            "Price",
            format="$%.2f",
        ),
        "Dividend Yield": st.column_config.NumberColumn(
            "Dividend Yield",
            format="%.2f%%",
        ),
        "Dividend Growth 5Y": st.column_config.NumberColumn(
            "5Y Div Growth",
            format="%.2f%%",
        ),
        "Dividend Score": st.column_config.NumberColumn(
            "Dividend",
            format="%.1f",
        ),
        "Quality Score": st.column_config.NumberColumn(
            "Quality",
            format="%.1f",
        ),
        "Value Score": st.column_config.NumberColumn(
            "Value",
            format="%.1f",
        ),
        "Overall Score": st.column_config.ProgressColumn(
            "Overall Score",
            min_value=0,
            max_value=100,
            format="%.1f",
        ),
    },
)

top_ranked["Dividend Yield"] = (
    top_ranked["Dividend Yield"] * 100
)

top_ranked["Dividend Growth 5Y"] = (
    top_ranked["Dividend Growth 5Y"] * 100
)

st.divider()


# ---------------------------------------------------------
# Yield and score leaders
# ---------------------------------------------------------

left, right = st.columns(2)

with left:
    st.subheader("💵 Highest Dividend Yields")

    yield_columns = [
        "Ticker",
        "Company",
        "Sector",
        "Dividend Yield",
        "Payout Ratio",
        "Dividend Growth 5Y",
        "Overall Score",
    ]

    

    yield_columns = [
        column for column in yield_columns
        if column in df.columns
    ]

    yield_leaders = (
        df.sort_values("Dividend Yield", ascending=False)
        .head(10)[yield_columns]
        .copy()
    )

    st.dataframe(
        yield_leaders,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Dividend Yield": st.column_config.NumberColumn(
                "Yield",
                format="%.2f%%",
            ),
            "Payout Ratio": st.column_config.NumberColumn(
                "Payout",
                format="%.2f%%",
            ),
            "Dividend Growth 5Y": st.column_config.NumberColumn(
                "5Y Growth",
                format="%.2f%%",
            ),
            "Overall Score": st.column_config.NumberColumn(
                "Score",
                format="%.1f",
            ),
        },
    )

    yield_leaders["Dividend Yield"] = (
        yield_leaders["Dividend Yield"] * 100
    )

    yield_leaders["Payout Ratio"] = (
        yield_leaders["Payout Ratio"] * 100
    )

    yield_leaders["Dividend Growth 5Y"] = (
        yield_leaders["Dividend Growth 5Y"] * 100
    )

with right:
    st.subheader("📈 Best Dividend Scores")

    dividend_columns = [
        "Ticker",
        "Company",
        "Dividend Yield",
        "Dividend Growth 5Y",
        "Dividend Consistency",
        "Dividend Score",
        "Overall Score",
    ]

    dividend_columns = [
        column for column in dividend_columns
        if column in df.columns
    ]

    dividend_leaders = (
        df.sort_values("Dividend Score", ascending=False)
        .head(10)[dividend_columns]
        .copy()
    )

    st.dataframe(
        dividend_leaders,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Dividend Yield": st.column_config.NumberColumn(
                "Yield",
                format="%.2f%%",
            ),
            "Dividend Growth 5Y": st.column_config.NumberColumn(
                "5Y Growth",
                format="%.2f%%",
            ),
            "Dividend Consistency": st.column_config.NumberColumn(
                "Consistency",
                format="%.0f%%",
            ),
            "Dividend Score": st.column_config.ProgressColumn(
                "Dividend Score",
                min_value=0,
                max_value=100,
                format="%.1f",
            ),
            "Overall Score": st.column_config.NumberColumn(
                "Overall",
                format="%.1f",
            ),
        },
    )

dividend_leaders["Dividend Yield"] = (
    dividend_leaders["Dividend Yield"] * 100
)

dividend_leaders["Dividend Growth 5Y"] = (
    dividend_leaders["Dividend Growth 5Y"] * 100
)

dividend_leaders["Dividend Consistency"] = (
    dividend_leaders["Dividend Consistency"] * 100
)

st.divider()


# ---------------------------------------------------------
# Sector overview
# ---------------------------------------------------------

st.subheader("🏭 Dividend Aristocrats by Sector")

sector_source = df.copy()
sector_source["Sector"] = sector_source["Sector"].fillna("Unknown")

sector_summary = (
    sector_source.groupby("Sector", as_index=False)
    .agg(
        Stocks=("Ticker", "count"),
        Median_Yield=("Dividend Yield", "median"),
        Median_Score=("Overall Score", "median"),
    )
    .sort_values("Stocks", ascending=False)
)

chart_col, table_col = st.columns([1.4, 1])

with chart_col:
    sector_chart = px.bar(
        sector_summary,
        x="Sector",
        y="Stocks",
        color="Median_Score",
        color_continuous_scale="Blues",
        labels={
            "Stocks": "Number of Stocks",
            "Median_Score": "Median Score",
        },
        title="Dividend Aristocrat Sector Representation",
    )

    sector_summary["Median_Yield"] = (
        sector_summary["Median_Yield"] 
    )

    sector_chart.update_layout(
        xaxis_title=None,
        yaxis_title="Stocks",
        coloraxis_colorbar_title="Score",
        margin=dict(l=10, r=10, t=55, b=10),
    )

    st.plotly_chart(
        sector_chart,
        use_container_width=True,
    )


with table_col:
    sector_table = sector_summary.rename(
        columns={
            "Median_Yield": "Median Yield",
            "Median_Score": "Median Score",
        }
    )

    st.dataframe(
        sector_table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Median Yield": st.column_config.NumberColumn(
                "Median Yield",
                format="%.2f%%",
            ),
            "Median Score": st.column_config.NumberColumn(
                "Median Score",
                format="%.1f",
            ),
        },
    )

st.divider()


# ---------------------------------------------------------
# Score leaders by category
# ---------------------------------------------------------

st.subheader("🎯 MarketScope Category Leaders")

categories = [
    ("Dividend Score", "Dividend"),
    ("Quality Score", "Quality"),
    ("Value Score", "Value"),
    ("Momentum Score", "Momentum"),
    ("Risk Score", "Risk"),
]

leader_columns = st.columns(len(categories))

for column, (score_column, label) in zip(leader_columns, categories):
    if score_column not in df.columns:
        continue

    valid_scores = pd.to_numeric(
        df[score_column], errors="coerce"
    )

    if valid_scores.notna().any():
        leader_index = valid_scores.idxmax()
        leader = df.loc[leader_index]

        with column:
            st.metric(
                label,
                str(leader["Ticker"]),
                f'{float(leader[score_column]):.1f} score',
            )


# ---------------------------------------------------------
# Footer
# ---------------------------------------------------------

st.caption(
    "MarketScope Dividend scores are research indicators, not investment "
    "recommendations. Dividend payments and market data can change."
)

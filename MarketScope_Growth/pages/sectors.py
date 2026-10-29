"""MarketScope Growth sector analysis page."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from config import SECTOR_COLORS
from market_data import load_market_data


SCORE_COLUMNS = [
    "Growth Score",
    "Quality Score",
    "Valuation Score",
    "Momentum Score",
    "Overall Score",
]


@st.cache_data(ttl=900, show_spinner=False)
def get_sector_data() -> pd.DataFrame:
    """Load the scored MarketScope Growth dataset."""
    return load_market_data()


def numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    """Return a numeric column or an aligned NaN Series."""
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def build_sector_summary(data: pd.DataFrame) -> pd.DataFrame:
    """Aggregate company scores and key metrics by sector."""
    if "Sector" not in data.columns:
        return pd.DataFrame()

    working = data.copy()
    working["Sector"] = working["Sector"].fillna("Unknown").replace("", "Unknown")

    numeric_columns = [
        "Market Cap",
        "Revenue Growth",
        "Earnings Growth",
        "Forward EPS Growth",
        "6M Return",
        "12M Return",
        *SCORE_COLUMNS,
    ]
    for column in numeric_columns:
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")

    aggregations: dict[str, tuple[str, str]] = {
        "Stocks": ("Ticker", "count"),
    }

    for column in SCORE_COLUMNS:
        if column in working.columns:
            aggregations[column] = (column, "mean")

    optional_metrics = {
        "Median Market Cap": ("Market Cap", "median"),
        "Revenue Growth": ("Revenue Growth", "median"),
        "Earnings Growth": ("Earnings Growth", "median"),
        "Forward EPS Growth": ("Forward EPS Growth", "median"),
        "6M Return": ("6M Return", "mean"),
        "12M Return": ("12M Return", "mean"),
    }
    for label, aggregation in optional_metrics.items():
        if aggregation[0] in working.columns:
            aggregations[label] = aggregation

    summary = (
        working.groupby("Sector", as_index=False)
        .agg(**aggregations)
        .sort_values("Overall Score", ascending=False, na_position="last")
        .reset_index(drop=True)
    )

    summary.insert(0, "Rank", range(1, len(summary) + 1))
    return summary


def sector_table_config() -> dict:
    """Return Streamlit formatting for the sector summary table."""

    config = {
        "Rank": st.column_config.NumberColumn(
            "Rank",
            format="%d",
        ),
        "Stocks": st.column_config.NumberColumn(
            "Stocks",
            format="%d",
        ),
        "Median Market Cap": st.column_config.NumberColumn(
            "Median Market Cap",
            format="compact",
        ),
    }

    # Score columns
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )

    # Decimal values displayed as percentages
    for column in (
        "Revenue Growth",
        "Earnings Growth",
        "Forward EPS Growth",
        "6M Return",
        "12M Return",
    ):
        config[column] = st.column_config.NumberColumn(
            column,
            format="percent",
        )

    return config


def make_score_bar(summary: pd.DataFrame, score_column: str) -> go.Figure:
    """Create a consistently colored horizontal sector ranking chart."""
    chart = summary.dropna(subset=[score_column]).sort_values(score_column)
    colors = [SECTOR_COLORS.get(sector, SECTOR_COLORS.get("Unknown", "#bdbdbd"))
              for sector in chart["Sector"]]

    figure = go.Figure(
        go.Bar(
            x=chart[score_column],
            y=chart["Sector"],
            orientation="h",
            marker_color=colors,
            text=chart[score_column].map(lambda value: f"{value:.1f}"),
            textposition="outside",
            customdata=chart[["Stocks"]],
            hovertemplate=(
                "<b>%{y}</b><br>"
                + score_column
                + ": %{x:.1f}<br>Stocks: %{customdata[0]}<extra></extra>"
            ),
        )
    )
    figure.update_xaxes(range=[0, 105], title=score_column)
    figure.update_yaxes(title="")
    figure.update_layout(
        height=max(420, 42 * len(chart)),
        showlegend=False,
        margin=dict(l=10, r=45, t=10, b=10),
    )
    return figure


def make_score_heatmap(summary: pd.DataFrame) -> go.Figure:
    """Create a sector-by-category score heatmap."""
    score_columns = [column for column in SCORE_COLUMNS if column in summary.columns]
    heatmap_data = summary.set_index("Sector")[score_columns]

    figure = px.imshow(
        heatmap_data,
        text_auto=".1f",
        aspect="auto",
        color_continuous_scale=[
            [0.00, "#c62828"],
            [0.40, "#ef6c00"],
            [0.55, "#fbc02d"],
            [0.70, "#66bb6a"],
            [1.00, "#1b5e20"],
        ],
        zmin=0,
        zmax=100,
    )
    figure.update_layout(
        height=max(440, 45 * len(heatmap_data)),
        margin=dict(l=10, r=10, t=10, b=10),
        coloraxis_colorbar_title="Score",
    )
    figure.update_xaxes(title="")
    figure.update_yaxes(title="")
    return figure


def make_radar_chart(row: pd.Series) -> go.Figure:
    """Create a radar chart for the selected sector's category scores."""
    columns = [column for column in SCORE_COLUMNS if column in row.index]
    labels = [column.replace(" Score", "") for column in columns]
    values = [float(row[column]) if pd.notna(row[column]) else 0.0 for column in columns]

    if values:
        labels.append(labels[0])
        values.append(values[0])

    color = SECTOR_COLORS.get(row["Sector"], SECTOR_COLORS.get("Unknown", "#bdbdbd"))
    figure = go.Figure(
        go.Scatterpolar(
            r=values,
            theta=labels,
            fill="toself",
            line_color=color,
            fillcolor=color,
            opacity=0.65,
            hovertemplate="%{theta}: %{r:.1f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=430,
        showlegend=False,
        polar=dict(radialaxis=dict(visible=True, range=[0, 100])),
        margin=dict(l=35, r=35, t=25, b=25),
    )
    return figure


def show() -> None:
    """Render the Growth by Sector page."""
    st.title("🏭 Growth by Sector")
    st.caption(
        "Compare sector-level Growth, Quality, Valuation, Momentum, and Overall "
        "scores across the MarketScope Growth universe."
    )

    try:
        with st.spinner("Loading sector analysis..."):
            data = get_sector_data()
    except Exception as exc:
        st.error("Sector analysis could not load market data.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No growth-stock data is currently available.")
        return

    summary = build_sector_summary(data)
    if summary.empty:
        st.warning("Sector information is not available in the current dataset.")
        return

    leader = summary.iloc[0]
    largest = summary.sort_values("Stocks", ascending=False).iloc[0]
    growth_leader = summary.sort_values(
        "Growth Score", ascending=False, na_position="last"
    ).iloc[0]
    value_leader = summary.sort_values(
        "Valuation Score", ascending=False, na_position="last"
    ).iloc[0]

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric(
        "Top Overall Sector",
        leader["Sector"],
        f'{leader["Overall Score"]:.1f} score',
    )
    metric2.metric(
        "Top Growth Sector",
        growth_leader["Sector"],
        f'{growth_leader["Growth Score"]:.1f} score',
    )
    metric3.metric(
        "Top Valuation Sector",
        value_leader["Sector"],
        f'{value_leader["Valuation Score"]:.1f} score',
    )
    metric4.metric(
        "Largest Coverage",
        largest["Sector"],
        f'{int(largest["Stocks"])} stocks',
    )

    st.divider()

    score_options = [column for column in SCORE_COLUMNS if column in summary.columns]
    selected_score = st.selectbox(
        "Rank sectors by",
        options=score_options,
        index=score_options.index("Overall Score") if "Overall Score" in score_options else 0,
    )

    left, right = st.columns([1.1, 1])
    with left:
        st.subheader("Sector Rankings")
        st.plotly_chart(
            make_score_bar(summary, selected_score),
            use_container_width=True,
        )

    with right:
        st.subheader("Score Heatmap")
        st.plotly_chart(
            make_score_heatmap(summary),
            use_container_width=True,
        )

    st.divider()
    st.subheader("Sector Scorecard")
    st.dataframe(
        summary,
        use_container_width=True,
        hide_index=True,
        column_config=sector_table_config(),
    )

    st.divider()
    st.subheader("Sector Detail")

    selected_sector = st.selectbox(
        "Select a sector",
        options=summary["Sector"].tolist(),
    )
    sector_row = summary.loc[summary["Sector"] == selected_sector].iloc[0]
    sector_stocks = data.loc[
        data["Sector"].fillna("Unknown") == selected_sector
    ].copy()

    detail_left, detail_right = st.columns([1, 1.4])
    with detail_left:
        st.plotly_chart(make_radar_chart(sector_row), use_container_width=True)

    with detail_right:
        st.markdown(f"### {selected_sector} Leaders")
        sort_column = st.selectbox(
            "Rank stocks by",
            options=[column for column in SCORE_COLUMNS if column in sector_stocks.columns],
            key="sector_stock_sort",
        )
        sector_stocks = sector_stocks.sort_values(
            sort_column, ascending=False, na_position="last"
        )

        leader_columns = [
            column for column in (
                "Ticker",
                "Company",
                "Growth Score",
                "Quality Score",
                "Valuation Score",
                "Momentum Score",
                "Overall Score",
                "Rating",
            )
            if column in sector_stocks.columns
        ]
        st.dataframe(
            sector_stocks[leader_columns].head(15),
            use_container_width=True,
            hide_index=True,
            column_config=sector_table_config(),
        )

    st.caption(
        "Sector scores are averages of the companies included in the configured "
        "MarketScope Growth universe, not averages for every publicly traded company."
    )
# =========================================================
# Run page
# =========================================================
show()
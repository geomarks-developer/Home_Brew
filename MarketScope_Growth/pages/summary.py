import pandas as pd
import plotly.express as px
import streamlit as st

from config import DEFAULT_TOP_N, SECTOR_COLORS
from market_data import cache_age_hours, load_market_data


def score_color(score):
    if pd.isna(score):
        return "#9e9e9e"
    if score >= 80:
        return "#1b5e20"
    if score >= 70:
        return "#2e7d32"
    if score >= 60:
        return "#66bb6a"
    if score >= 50:
        return "#fbc02d"
    if score >= 40:
        return "#ef6c00"
    return "#c62828"


def safe_mean(data, column):
    if column not in data.columns:
        return None
    values = pd.to_numeric(data[column], errors="coerce")
    return None if values.dropna().empty else values.mean()


@st.cache_data(ttl=900, show_spinner=False)
def get_summary_data():
    return load_market_data()


def show():
    st.title("🚀 Growth Summary")
    st.caption(
        "MarketScope Growth evaluates companies across Growth, Quality, Valuation, and Momentum."
    )

    with st.sidebar:
        st.markdown("### Growth Dashboard")
        refresh = st.button("🔄 Refresh Market Data", type="secondary", use_container_width=True)
        if refresh:
            st.cache_data.clear()
            with st.spinner("Refreshing MarketScope Growth data..."):
                load_market_data(force_refresh=True)
            st.rerun()

        age = cache_age_hours()
        if age is not None:
            st.caption(
                f"Data cache age: {age * 60:.0f} minutes" if age < 1 else f"Data cache age: {age:.1f} hours"
            )

    try:
        with st.spinner("Loading MarketScope Growth..."):
            data = get_summary_data()
    except Exception as exc:
        st.error("MarketScope Growth could not load market data.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No growth-stock data is currently available.")
        return

    overall_average = safe_mean(data, "Overall Score")
    growth_average = safe_mean(data, "Growth Score")
    quality_average = safe_mean(data, "Quality Score")
    momentum_average = safe_mean(data, "Momentum Score")

    metrics = st.columns(5)
    metrics[0].metric("Stocks Analyzed", f"{len(data):,}")
    metrics[1].metric("Overall Score", f"{overall_average:.1f}" if overall_average is not None else "N/A")
    metrics[2].metric("Growth", f"{growth_average:.1f}" if growth_average is not None else "N/A")
    metrics[3].metric("Quality", f"{quality_average:.1f}" if quality_average is not None else "N/A")
    metrics[4].metric("Momentum", f"{momentum_average:.1f}" if momentum_average is not None else "N/A")

    st.divider()
    st.subheader("🏆 Growth Leaders")

    leader_count = min(DEFAULT_TOP_N, len(data))
    top_stocks = data.sort_values("Overall Score", ascending=False, na_position="last").head(leader_count)

    display_columns = [
        "Ticker", "Company", "Sector", "Price", "Market Cap",
        "Revenue Growth", "Earnings Growth", "Forward EPS Growth",
        "Growth Score", "Quality Score", "Valuation Score",
        "Momentum Score", "Overall Score", "Rating",
    ]
    display_columns = [c for c in display_columns if c in top_stocks.columns]
    leader_table = top_stocks[display_columns].copy()

    for column in ["Revenue Growth", "Earnings Growth", "Forward EPS Growth"]:
        if column in leader_table.columns:
            leader_table[column] = pd.to_numeric(leader_table[column], errors="coerce") * 100

    st.dataframe(
        leader_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Market Cap": st.column_config.NumberColumn("Market Cap", format="$%.0f"),
            "Revenue Growth": st.column_config.NumberColumn("Revenue Growth", format="%.1f%%"),
            "Earnings Growth": st.column_config.NumberColumn("Earnings Growth", format="%.1f%%"),
            "Forward EPS Growth": st.column_config.NumberColumn("Forward EPS Growth", format="%.1f%%"),
            "Growth Score": st.column_config.ProgressColumn("Growth", min_value=0, max_value=100, format="%.1f"),
            "Quality Score": st.column_config.ProgressColumn("Quality", min_value=0, max_value=100, format="%.1f"),
            "Valuation Score": st.column_config.ProgressColumn("Valuation", min_value=0, max_value=100, format="%.1f"),
            "Momentum Score": st.column_config.ProgressColumn("Momentum", min_value=0, max_value=100, format="%.1f"),
            "Overall Score": st.column_config.ProgressColumn("Overall", min_value=0, max_value=100, format="%.1f"),
        },
    )

    st.divider()
    st.subheader("⭐ Category Leaders")
    category_columns = st.columns(4)
    categories = [
        (category_columns[0], "Growth", "Growth Score"),
        (category_columns[1], "Quality", "Quality Score"),
        (category_columns[2], "Valuation", "Valuation Score"),
        (category_columns[3], "Momentum", "Momentum Score"),
    ]

    for container, title, score_column in categories:
        with container:
            st.markdown(f"**{title} Leaders**")
            if score_column not in data.columns:
                st.caption("No data available.")
                continue
            leaders = (
                data[["Ticker", score_column]]
                .dropna(subset=[score_column])
                .sort_values(score_column, ascending=False)
                .head(5)
            )
            for _, row in leaders.iterrows():
                ticker = row["Ticker"]
                score = row[score_column]
                st.markdown(
                    f'<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 0;">'
                    f'<strong>{ticker}</strong><span style="color:{score_color(score)};font-weight:700;">{score:.1f}</span></div>',
                    unsafe_allow_html=True,
                )

    st.divider()
    st.subheader("🏭 Growth Leadership by Sector")

    if {"Sector", "Overall Score", "Growth Score", "Ticker"}.issubset(data.columns):
        sector_data = (
            data.dropna(subset=["Sector", "Overall Score"])
            .groupby("Sector", as_index=False)
            .agg(
                Overall_Score=("Overall Score", "mean"),
                Growth_Score=("Growth Score", "mean"),
                Stocks=("Ticker", "count"),
            )
            .sort_values("Overall_Score", ascending=True)
        )

        fig = px.bar(
            sector_data,
            x="Overall_Score",
            y="Sector",
            orientation="h",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            custom_data=["Growth_Score", "Stocks"],
        )
        fig.update_traces(
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Overall Score: %{x:.1f}<br>"
                "Growth Score: %{customdata[0]:.1f}<br>"
                "Stocks: %{customdata[1]}<extra></extra>"
            )
        )
        fig.update_layout(
            height=450,
            showlegend=False,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Average Overall Score",
            yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sector scoring data is not available.")

    st.divider()
    chart1, chart2 = st.columns(2)

    with chart1:
        st.subheader("📊 Overall Ratings")
        if "Rating" in data.columns:
            ratings = data["Rating"].fillna("Unrated").value_counts().rename_axis("Rating").reset_index(name="Stocks")
            fig = px.bar(ratings, x="Rating", y="Stocks", text="Stocks")
            fig.update_layout(showlegend=False, height=350, xaxis_title="", yaxis_title="Number of Stocks", margin=dict(l=10, r=10, t=10, b=10))
            fig.update_traces(textposition="outside")
            st.plotly_chart(fig, use_container_width=True)

    with chart2:
        st.subheader("🚀 Growth Ratings")
        if "Growth Rating" in data.columns:
            growth_ratings = data["Growth Rating"].fillna("Unrated").value_counts().rename_axis("Rating").reset_index(name="Stocks")
            fig = px.pie(growth_ratings, names="Rating", values="Stocks", hole=0.45)
            fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("🔥 Highest Growth Scores")

    if "Growth Score" in data.columns:
        growth_leaders = data.dropna(subset=["Growth Score"]).sort_values("Growth Score", ascending=False).head(15)
        chart_args = dict(
            data_frame=growth_leaders.sort_values("Growth Score"),
            x="Growth Score",
            y="Ticker",
            orientation="h",
            hover_data=[c for c in ["Company", "Rating"] if c in growth_leaders.columns],
        )
        if "Sector" in growth_leaders.columns:
            chart_args["color"] = "Sector"
            chart_args["color_discrete_map"] = SECTOR_COLORS

        fig = px.bar(**chart_args)
        fig.update_layout(height=500, margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Growth Score", yaxis_title="", legend_title="Sector")
        fig.update_xaxes(range=[0, 100])
        st.plotly_chart(fig, use_container_width=True)

    st.caption(
        "MarketScope Growth scores are quantitative research tools and are not investment recommendations."
    )


# Required when this file is executed through st.Page/st.navigation.
show()

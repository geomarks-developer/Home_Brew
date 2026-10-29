"""Interactive MarketScope Value screener."""
from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from config import DEFAULT_FILTERS, SECTOR_COLORS
from market_data import load_market_data


PERCENT_COLUMNS = [
    "FCF Yield",
    "Earnings Yield",
    "Revenue Growth",
    "Earnings Growth",
    "EPS Growth",
    "Forward EPS Growth",
    "ROE",
    "Operating Margin",
    "Profit Margin",
    "6M Return",
    "12M Return",
    "Overall Coverage",
    "Valuation Coverage",
    "Quality Coverage",
    "Financial Strength Coverage",
    "Growth Coverage",
    "Momentum Coverage",
    "Value Trap Coverage",
]

SCORE_COLUMNS = [
    "Valuation Score",
    "Quality Score",
    "Financial Strength Score",
    "Growth Score",
    "Momentum Score",
    "Overall Score",
]


# =========================================================
# Helpers
# =========================================================

def numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def available_range(
    data: pd.DataFrame,
    column: str,
    default_min: float,
    default_max: float,
) -> tuple[float, float]:
    values = numeric_series(data, column).dropna()
    if values.empty:
        return default_min, default_max
    return float(values.min()), float(values.max())


def column_configuration() -> dict:
    """Return Streamlit DataFrame formatting settings."""
    config = {
        "Rank": st.column_config.NumberColumn("#", format="%d"),
        "Ticker": st.column_config.TextColumn("Ticker", pinned=True),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Enterprise Value": st.column_config.NumberColumn("Enterprise Value", format="compact"),
        "Trailing PE": st.column_config.NumberColumn("Trailing P/E", format="%.1f"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "Price/Sales": st.column_config.NumberColumn("P/S", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "PEG": st.column_config.NumberColumn("PEG", format="%.2f"),
        "Debt/Equity": st.column_config.NumberColumn("Debt/Equity", format="%.1f"),
        "Current Ratio": st.column_config.NumberColumn("Current Ratio", format="%.2f"),
        "Net Debt/Market Cap": st.column_config.NumberColumn(
            "Net Debt / Market Cap",
            format="percent",
        ),
        "Cash/Debt": st.column_config.NumberColumn("Cash / Debt", format="%.2f"),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk",
            min_value=0,
            max_value=100,
            format="%.1f",
        ),
    }

    for column in PERCENT_COLUMNS:
        config[column] = st.column_config.NumberColumn(
            column,
            format="percent",
        )

    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )

    return config


def selected_columns() -> list[str]:
    return [
        "Rank",
        "Ticker",
        "Company",
        "Sector",
        "Price",
        "Market Cap",
        "Forward PE",
        "Price/Book",
        "Price/Sales",
        "EV/EBITDA",
        "FCF Yield",
        "Earnings Yield",
        "ROE",
        "Revenue Growth",
        "Earnings Growth",
        "6M Return",
        "12M Return",
        "Valuation Score",
        "Quality Score",
        "Financial Strength Score",
        "Growth Score",
        "Momentum Score",
        "Overall Score",
        "Rating",
        "Value Trap Risk",
        "Value Trap Rating",
        "Overall Coverage",
    ]


# =========================================================
# Page
# =========================================================

def show() -> None:
    st.title("💎 Value Screener")
    st.caption(
        "Screen for attractively valued companies while balancing business quality, "
        "financial strength, growth, momentum, and potential value-trap risk."
    )

    try:
        with st.spinner("Loading MarketScope Value data..."):
            data = load_market_data()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No MarketScope Value data is currently available.")
        return

    data = data.copy()
    if "Sector" not in data.columns:
        data["Sector"] = "Unknown"
    data["Sector"] = data["Sector"].fillna("Unknown").replace("", "Unknown")

    # -----------------------------------------------------
    # Sidebar filters
    # -----------------------------------------------------
    with st.sidebar:
        st.markdown("### Value Screener Filters")

        sectors = sorted(data["Sector"].astype(str).unique())
        chosen_sectors = st.multiselect(
            "Sectors",
            sectors,
            default=sectors,
        )

        minimum_market_cap_billions = st.number_input(
            "Minimum market cap ($B)",
            min_value=0.0,
            value=float(DEFAULT_FILTERS["minimum_market_cap"]) / 1_000_000_000,
            step=1.0,
        )

        st.markdown("#### Score Requirements")
        minimum_overall = st.slider(
            "Minimum Overall Score",
            0.0,
            100.0,
            float(DEFAULT_FILTERS["minimum_overall_score"]),
            1.0,
        )
        minimum_valuation = st.slider(
            "Minimum Valuation Score",
            0.0,
            100.0,
            float(DEFAULT_FILTERS["minimum_valuation_score"]),
            1.0,
        )
        minimum_quality = st.slider(
            "Minimum Quality Score",
            0.0,
            100.0,
            float(DEFAULT_FILTERS["minimum_quality_score"]),
            1.0,
        )
        minimum_strength = st.slider(
            "Minimum Financial Strength",
            0.0,
            100.0,
            0.0,
            1.0,
        )
        maximum_trap_risk = st.slider(
            "Maximum Value-Trap Risk",
            0.0,
            100.0,
            float(DEFAULT_FILTERS["maximum_value_trap_risk"]),
            1.0,
        )

        st.markdown("#### Valuation Limits")
        use_forward_pe = st.checkbox("Limit Forward P/E", value=False)
        maximum_forward_pe = st.number_input(
            "Maximum Forward P/E",
            min_value=0.0,
            value=20.0,
            step=1.0,
            disabled=not use_forward_pe,
        )

        use_ev_ebitda = st.checkbox("Limit EV/EBITDA", value=False)
        maximum_ev_ebitda = st.number_input(
            "Maximum EV/EBITDA",
            min_value=0.0,
            value=15.0,
            step=1.0,
            disabled=not use_ev_ebitda,
        )

        use_fcf_yield = st.checkbox("Require FCF Yield", value=False)
        minimum_fcf_yield_pct = st.number_input(
            "Minimum FCF Yield (%)",
            min_value=-50.0,
            max_value=100.0,
            value=5.0,
            step=0.5,
            disabled=not use_fcf_yield,
        )

        st.markdown("#### Additional Requirements")
        require_positive_fcf = st.checkbox("Positive free cash flow", value=False)
        require_positive_growth = st.checkbox(
            "Positive revenue or earnings growth",
            value=False,
        )
        require_above_200dma = st.checkbox("Price above 200-day average", value=False)

    # -----------------------------------------------------
    # Apply filters
    # -----------------------------------------------------
    filtered = data[data["Sector"].astype(str).isin(chosen_sectors)].copy()
    filtered = filtered[
        numeric_series(filtered, "Market Cap").fillna(0)
        >= minimum_market_cap_billions * 1_000_000_000
    ]
    filtered = filtered[numeric_series(filtered, "Overall Score") >= minimum_overall]
    filtered = filtered[numeric_series(filtered, "Valuation Score") >= minimum_valuation]
    filtered = filtered[numeric_series(filtered, "Quality Score") >= minimum_quality]
    filtered = filtered[
        numeric_series(filtered, "Financial Strength Score") >= minimum_strength
    ]
    filtered = filtered[numeric_series(filtered, "Value Trap Risk") <= maximum_trap_risk]

    if use_forward_pe:
        forward_pe = numeric_series(filtered, "Forward PE")
        filtered = filtered[(forward_pe > 0) & (forward_pe <= maximum_forward_pe)]

    if use_ev_ebitda:
        ev_ebitda = numeric_series(filtered, "EV/EBITDA")
        filtered = filtered[(ev_ebitda > 0) & (ev_ebitda <= maximum_ev_ebitda)]

    if use_fcf_yield:
        filtered = filtered[
            numeric_series(filtered, "FCF Yield") >= minimum_fcf_yield_pct / 100
        ]

    if require_positive_fcf:
        filtered = filtered[numeric_series(filtered, "Free Cash Flow") > 0]

    if require_positive_growth:
        revenue_growth = numeric_series(filtered, "Revenue Growth")
        earnings_growth = numeric_series(filtered, "Earnings Growth")
        filtered = filtered[(revenue_growth > 0) | (earnings_growth > 0)]

    if require_above_200dma:
        filtered = filtered[
            numeric_series(filtered, "Price") > numeric_series(filtered, "200D MA")
        ]

    # -----------------------------------------------------
    # Results summary
    # -----------------------------------------------------
    result_metrics = st.columns(5)
    result_metrics[0].metric("Matches", f"{len(filtered):,}", f"of {len(data):,}")
    result_metrics[1].metric(
        "Median Overall",
        f"{numeric_series(filtered, 'Overall Score').median():.1f}"
        if not filtered.empty
        else "N/A",
    )
    result_metrics[2].metric(
        "Median Valuation",
        f"{numeric_series(filtered, 'Valuation Score').median():.1f}"
        if not filtered.empty
        else "N/A",
    )
    result_metrics[3].metric(
        "Median FCF Yield",
        f"{numeric_series(filtered, 'FCF Yield').median():.1%}"
        if not filtered.empty
        else "N/A",
    )
    result_metrics[4].metric(
        "Median Trap Risk",
        f"{numeric_series(filtered, 'Value Trap Risk').median():.1f}"
        if not filtered.empty
        else "N/A",
    )

    if filtered.empty:
        st.info("No stocks match the selected value-screening criteria.")
        return

    # -----------------------------------------------------
    # Sort and table controls
    # -----------------------------------------------------
    control_col1, control_col2 = st.columns([1, 1])
    with control_col1:
        sort_options = [
            column
            for column in (
                "Overall Score",
                "Valuation Score",
                "Quality Score",
                "Financial Strength Score",
                "Value Trap Risk",
                "FCF Yield",
                "Earnings Yield",
                "Forward PE",
                "Market Cap",
            )
            if column in filtered.columns
        ]
        sort_column = st.selectbox("Sort results by", sort_options, index=0)

    with control_col2:
        ascending_default = sort_column in {
            "Value Trap Risk",
            "Forward PE",
        }
        ascending = st.toggle("Lowest first", value=ascending_default)

    filtered = filtered.sort_values(
        sort_column,
        ascending=ascending,
        na_position="last",
    ).copy()
    filtered["Screen Rank"] = range(1, len(filtered) + 1)

    st.divider()
    st.subheader("Value Screener Results")

    display_columns = [column for column in selected_columns() if column in filtered.columns]
    result_table = filtered[display_columns].copy()
    if "Rank" in result_table.columns:
        result_table["Rank"] = filtered["Screen Rank"].values

    st.dataframe(
        result_table,
        use_container_width=True,
        hide_index=True,
        column_config=column_configuration(),
    )

    st.download_button(
        "Download Screener Results CSV",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="marketscope_value_screener.csv",
        mime="text/csv",
        type="secondary",
    )

    # -----------------------------------------------------
    # Visual results
    # -----------------------------------------------------
    st.divider()
    chart_data = filtered.dropna(
        subset=["Valuation Score", "Value Trap Risk"]
    ).copy()

    if not chart_data.empty:
        st.subheader("Valuation vs. Value-Trap Risk")
        st.caption(
            "The preferred area is toward the right and lower portion of the chart: "
            "stronger valuation with less evidence of a value trap."
        )

        chart_data["Market Cap ($B)"] = (
            numeric_series(chart_data, "Market Cap") / 1_000_000_000
        )
        chart_data["Bubble Size"] = numeric_series(
            chart_data,
            "Market Cap",
        ).clip(lower=1)

        hover_data = {
            "Valuation Score": ":.1f",
            "Value Trap Risk": ":.1f",
            "Overall Score": ":.1f",
            "Quality Score": ":.1f",
            "Financial Strength Score": ":.1f",
            "Market Cap ($B)": ":$.1f",
            "FCF Yield": ":.1%",
            "Forward PE": ":.1f",
            "Bubble Size": False,
        }

        for optional in (
            "Company",
            "Sector",
            "Rating",
            "Value Trap Rating",
        ):
            if optional in chart_data.columns:
                hover_data[optional] = True

        figure = px.scatter(
            chart_data,
            x="Valuation Score",
            y="Value Trap Risk",
            color="Sector" if "Sector" in chart_data.columns else None,
            color_discrete_map=SECTOR_COLORS,
            size="Bubble Size",
            size_max=44,
            hover_name="Ticker" if "Ticker" in chart_data.columns else None,
            hover_data=hover_data,
        )
        figure.add_vline(x=65, line_dash="dot", line_color="gray")
        figure.add_hline(y=50, line_dash="dot", line_color="gray")
        figure.update_xaxes(
            range=[0, 100],
            title="Valuation Score → more attractive",
        )
        figure.update_yaxes(
            range=[100, 0],
            title="Value-Trap Risk → lower is better",
        )
        figure.update_layout(
            height=580,
            margin=dict(l=10, r=10, t=20, b=10),
            legend_title="Sector",
        )
        st.plotly_chart(figure, use_container_width=True)

    # -----------------------------------------------------
    # Category comparison
    # -----------------------------------------------------
    st.divider()
    st.subheader("Top Candidates by Category")

    tabs = st.tabs(
        [
            "Overall",
            "Valuation",
            "Quality",
            "Financial Strength",
            "Lowest Trap Risk",
        ]
    )
    categories = [
        (tabs[0], "Overall Score", False),
        (tabs[1], "Valuation Score", False),
        (tabs[2], "Quality Score", False),
        (tabs[3], "Financial Strength Score", False),
        (tabs[4], "Value Trap Risk", True),
    ]

    category_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Sector",
            "Forward PE",
            "FCF Yield",
            "Valuation Score",
            "Quality Score",
            "Financial Strength Score",
            "Overall Score",
            "Value Trap Risk",
        )
        if column in filtered.columns
    ]

    for tab, score_column, lowest_first in categories:
        with tab:
            leaders = filtered.sort_values(
                score_column,
                ascending=lowest_first,
                na_position="last",
            ).head(10)
            st.dataframe(
                leaders[category_columns],
                use_container_width=True,
                hide_index=True,
                column_config=column_configuration(),
            )

    st.caption(
        "MarketScope Value is a research and screening tool. Low valuation multiples can reflect "
        "business deterioration, leverage, cyclicality, accounting effects, or other risks. "
        "Use the Value Trap score and company-specific research alongside the valuation results."
    )


show()

"""MarketScope Growth interactive stock screener page."""

from __future__ import annotations

import io

import pandas as pd
import plotly.express as px
import streamlit as st

from config import DEFAULT_TOP_N, PRESET_SCREENS, SECTOR_COLORS
from market_data import load_market_data


# =========================================================
# Data and formatting helpers
# =========================================================

@st.cache_data(ttl=900, show_spinner=False)
def get_screener_data() -> pd.DataFrame:
    """Load the scored MarketScope Growth dataset."""
    return load_market_data()


def numeric_series(data: pd.DataFrame, column: str) -> pd.Series:
    """Return a numeric column or an aligned all-NaN Series."""
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def available_range(data: pd.DataFrame, column: str, default=(0.0, 100.0)):
    """Return a safe numeric min/max tuple for a filter widget."""
    values = numeric_series(data, column).dropna()
    if values.empty:
        return default

    low = float(values.min())
    high = float(values.max())
    if low == high:
        high = low + 1.0
    return low, high


def apply_preset(data: pd.DataFrame, preset_name: str) -> pd.DataFrame:
    """Apply a preset definition from config.PRESET_SCREENS."""
    rules = PRESET_SCREENS.get(preset_name, {})
    filtered = data.copy()

    rule_columns = {
        "min_overall_score": "Overall Score",
        "min_growth_score": "Growth Score",
        "min_quality_score": "Quality Score",
        "min_valuation_score": "Valuation Score",
        "min_momentum_score": "Momentum Score",
    }

    for rule, column in rule_columns.items():
        minimum = rules.get(rule)
        if minimum is not None and column in filtered.columns:
            values = numeric_series(filtered, column)
            filtered = filtered.loc[values >= float(minimum)]

    return filtered


def to_csv_bytes(data: pd.DataFrame) -> bytes:
    """Convert a DataFrame to UTF-8 CSV bytes."""
    return data.to_csv(index=False).encode("utf-8")


def to_excel_bytes(data: pd.DataFrame) -> bytes | None:
    """Convert a DataFrame to an in-memory Excel workbook."""
    try:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            data.to_excel(writer, sheet_name="Growth Screener", index=False)
            worksheet = writer.book["Growth Screener"]
            worksheet.freeze_panes = "A2"
            worksheet.auto_filter.ref = worksheet.dimensions

            for column_cells in worksheet.columns:
                width = min(
                    max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells) + 2,
                    28,
                )
                worksheet.column_dimensions[column_cells[0].column_letter].width = width

        output.seek(0)
        return output.getvalue()
    except (ImportError, ModuleNotFoundError):
        return None


def prepare_display_table(data: pd.DataFrame) -> pd.DataFrame:
    """Select and order the primary screener columns."""
    preferred = [
        "Ticker",
        "Company",
        "Sector",
        "Industry",
        "Price",
        "Market Cap",
        "Revenue Growth",
        "Earnings Growth",
        "EPS Growth",
        "Forward EPS Growth",
        "ROE",
        "Operating Margin",
        "Profit Margin",
        "Forward PE",
        "PEG",
        "Price/Sales",
        "6M Return",
        "12M Return",
        "Growth Score",
        "Quality Score",
        "Valuation Score",
        "Momentum Score",
        "Overall Score",
        "Overall Coverage",
        "Rating",
    ]
    columns = [column for column in preferred if column in data.columns]
    return data.loc[:, columns].copy()


def column_configuration() -> dict:
    """Return Streamlit DataFrame formatting settings."""
    percent_columns = [
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
    ]

    config = {
        "Ticker": st.column_config.TextColumn("Ticker", pinned=True),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="$%.0f"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "PEG": st.column_config.NumberColumn("PEG", format="%.2f"),
        "Price/Sales": st.column_config.NumberColumn("Price/Sales", format="%.1f"),
    }

    for column in percent_columns:
        config[column] = st.column_config.NumberColumn(column, format="percent")

    for column, label in (
        ("Growth Score", "Growth"),
        ("Quality Score", "Quality"),
        ("Valuation Score", "Valuation"),
        ("Momentum Score", "Momentum"),
        ("Overall Score", "Overall"),
    ):
        config[column] = st.column_config.ProgressColumn(
            label,
            min_value=0,
            max_value=100,
            format="%.1f",
        )

    return config


# =========================================================
# Page
# =========================================================

def show() -> None:
    st.title("🔎 Growth Stock Screener")
    st.caption(
        "Screen the MarketScope Growth universe by growth, quality, valuation, "
        "momentum, company size, sector, and quantitative rating."
    )

    try:
        with st.spinner("Loading growth-stock data..."):
            data = get_screener_data()
    except Exception as exc:
        st.error("The growth screener could not load market data.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No growth-stock data is currently available.")
        return

    data = data.copy()

    # -----------------------------------------------------
    # Preset and global filters
    # -----------------------------------------------------
    preset_names = list(PRESET_SCREENS.keys())
    preset = st.selectbox(
        "Preset screen",
        options=preset_names,
        index=0,
        help="Presets apply the score thresholds defined in config.py.",
    )
    filtered = apply_preset(data, preset)

    with st.expander("Advanced filters", expanded=True):
        row1 = st.columns(4)

        sectors = sorted(
            value for value in data.get("Sector", pd.Series(dtype=str)).dropna().unique()
            if str(value).strip()
        )
        selected_sectors = row1[0].multiselect(
            "Sectors",
            options=sectors,
            default=[],
            placeholder="All sectors",
        )

        ratings = sorted(
            value for value in data.get("Rating", pd.Series(dtype=str)).dropna().unique()
            if str(value).strip()
        )
        selected_ratings = row1[1].multiselect(
            "Ratings",
            options=ratings,
            default=[],
            placeholder="All ratings",
        )

        ticker_search = row1[2].text_input(
            "Ticker or company",
            placeholder="Example: NVDA or Nvidia",
        ).strip()

        market_cap_options = [
            "All sizes",
            "Mega Cap ($200B+)",
            "Large Cap ($10B-$200B)",
            "Mid Cap ($2B-$10B)",
        ]
        market_cap_filter = row1[3].selectbox("Market cap", market_cap_options)

        row2 = st.columns(5)
        min_growth = row2[0].slider("Min growth", 0, 100, 0)
        min_quality = row2[1].slider("Min quality", 0, 100, 0)
        min_valuation = row2[2].slider("Min valuation", 0, 100, 0)
        min_momentum = row2[3].slider("Min momentum", 0, 100, 0)
        min_overall = row2[4].slider("Min overall", 0, 100, 0)

        row3 = st.columns(4)
        revenue_low, revenue_high = available_range(data, "Revenue Growth", (-1.0, 1.0))
        minimum_revenue_growth = row3[0].number_input(
            "Min revenue growth (%)",
            min_value=-100.0,
            max_value=500.0,
            value=float(max(-100.0, revenue_low * 100.0)),
            step=1.0,
        ) / 100.0

        earnings_low, _ = available_range(data, "Earnings Growth", (-1.0, 1.0))
        minimum_earnings_growth = row3[1].number_input(
            "Min earnings growth (%)",
            min_value=-100.0,
            max_value=1000.0,
            value=float(max(-100.0, earnings_low * 100.0)),
            step=1.0,
        ) / 100.0

        maximum_forward_pe = row3[2].number_input(
            "Max forward P/E",
            min_value=0.0,
            max_value=500.0,
            value=500.0,
            step=1.0,
        )

        maximum_peg = row3[3].number_input(
            "Max PEG",
            min_value=0.0,
            max_value=25.0,
            value=25.0,
            step=0.1,
        )

    # -----------------------------------------------------
    # Apply advanced filters
    # -----------------------------------------------------
    if selected_sectors and "Sector" in filtered.columns:
        filtered = filtered.loc[filtered["Sector"].isin(selected_sectors)]

    if selected_ratings and "Rating" in filtered.columns:
        filtered = filtered.loc[filtered["Rating"].isin(selected_ratings)]

    if ticker_search:
        ticker_match = filtered.get("Ticker", pd.Series("", index=filtered.index)).astype(str)
        company_match = filtered.get("Company", pd.Series("", index=filtered.index)).astype(str)
        search_mask = (
            ticker_match.str.contains(ticker_search, case=False, na=False, regex=False)
            | company_match.str.contains(ticker_search, case=False, na=False, regex=False)
        )
        filtered = filtered.loc[search_mask]

    if "Market Cap" in filtered.columns:
        caps = numeric_series(filtered, "Market Cap")
        if market_cap_filter == "Mega Cap ($200B+)":
            filtered = filtered.loc[caps >= 200_000_000_000]
        elif market_cap_filter == "Large Cap ($10B-$200B)":
            filtered = filtered.loc[(caps >= 10_000_000_000) & (caps < 200_000_000_000)]
        elif market_cap_filter == "Mid Cap ($2B-$10B)":
            filtered = filtered.loc[(caps >= 2_000_000_000) & (caps < 10_000_000_000)]

    score_filters = {
        "Growth Score": min_growth,
        "Quality Score": min_quality,
        "Valuation Score": min_valuation,
        "Momentum Score": min_momentum,
        "Overall Score": min_overall,
    }
    for column, minimum in score_filters.items():
        if column in filtered.columns:
            filtered = filtered.loc[numeric_series(filtered, column) >= minimum]

    if "Revenue Growth" in filtered.columns:
        values = numeric_series(filtered, "Revenue Growth")
        filtered = filtered.loc[values.isna() | (values >= minimum_revenue_growth)]

    if "Earnings Growth" in filtered.columns:
        values = numeric_series(filtered, "Earnings Growth")
        filtered = filtered.loc[values.isna() | (values >= minimum_earnings_growth)]

    if "Forward PE" in filtered.columns and maximum_forward_pe < 500:
        values = numeric_series(filtered, "Forward PE")
        filtered = filtered.loc[values.isna() | ((values > 0) & (values <= maximum_forward_pe))]

    if "PEG" in filtered.columns and maximum_peg < 25:
        values = numeric_series(filtered, "PEG")
        filtered = filtered.loc[values.isna() | ((values > 0) & (values <= maximum_peg))]

    # -----------------------------------------------------
    # Sorting and result limit
    # -----------------------------------------------------
    toolbar = st.columns([2, 1, 1])
    sort_options = [
        column for column in (
            "Overall Score",
            "Growth Score",
            "Quality Score",
            "Valuation Score",
            "Momentum Score",
            "Revenue Growth",
            "12M Return",
            "Market Cap",
        )
        if column in filtered.columns
    ]
    sort_column = toolbar[0].selectbox("Sort results by", sort_options)
    ascending = toolbar[1].selectbox("Order", ["Highest first", "Lowest first"]) == "Lowest first"
    result_limit = toolbar[2].selectbox(
        "Rows",
        options=[10, 25, 50, 100, "All"],
        index=1 if DEFAULT_TOP_N == 25 else 0,
    )

    if sort_column:
        filtered = filtered.sort_values(sort_column, ascending=ascending, na_position="last")

    total_matches = len(filtered)
    displayed = filtered if result_limit == "All" else filtered.head(int(result_limit))

    # -----------------------------------------------------
    # Summary metrics
    # -----------------------------------------------------
    metrics = st.columns(5)
    metrics[0].metric("Matching Stocks", f"{total_matches:,}")

    metric_fields = [
        ("Average Overall", "Overall Score"),
        ("Average Growth", "Growth Score"),
        ("Average Quality", "Quality Score"),
        ("Average Momentum", "Momentum Score"),
    ]
    for container, (label, column) in zip(metrics[1:], metric_fields):
        values = numeric_series(filtered, column).dropna()
        container.metric(label, f"{values.mean():.1f}" if not values.empty else "N/A")

    if filtered.empty:
        st.info("No stocks match the current combination of filters.")
        return

    # -----------------------------------------------------
    # Results table
    # -----------------------------------------------------
    table = prepare_display_table(displayed)
    st.dataframe(
        table,
        use_container_width=True,
        hide_index=True,
        column_config=column_configuration(),
        height=min(800, 90 + 35 * len(table)),
    )

    # -----------------------------------------------------
    # Downloads
    # -----------------------------------------------------
    download1, download2, spacer = st.columns([1, 1, 3])
    download_data = prepare_display_table(filtered)

    download1.download_button(
        "Download CSV",
        data=to_csv_bytes(download_data),
        file_name="marketscope_growth_screener.csv",
        mime="text/csv",
        use_container_width=True,
    )

    excel_data = to_excel_bytes(download_data)
    if excel_data is not None:
        download2.download_button(
            "Download Excel",
            data=excel_data,
            file_name="marketscope_growth_screener.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    else:
        download2.caption("Install openpyxl to enable Excel export.")

    st.divider()

    # -----------------------------------------------------
    # Visual results
    # -----------------------------------------------------
    chart_data = filtered.dropna(
        subset=["Growth Score", "Overall Score"]
    ).copy()

    if not chart_data.empty:
        st.subheader("Growth vs. Overall Score")

        # -------------------------------------------------
        # Display-only fields for hover
        # -------------------------------------------------
        if "Revenue Growth" in chart_data.columns:
            chart_data["Revenue Growth %"] = (
                pd.to_numeric(
                    chart_data["Revenue Growth"],
                    errors="coerce",
                )
                * 100
            )

        if "Earnings Growth" in chart_data.columns:
            chart_data["Earnings Growth %"] = (
                pd.to_numeric(
                    chart_data["Earnings Growth"],
                    errors="coerce",
                )
                * 100
            )

        # -------------------------------------------------
        # Hover configuration
        # -------------------------------------------------
        hover_data = {}

        if "Company" in chart_data.columns:
            hover_data["Company"] = True

        if "Sector" in chart_data.columns:
            hover_data["Sector"] = True

        if "Revenue Growth %" in chart_data.columns:
            hover_data["Revenue Growth %"] = ":.1f"

        if "Earnings Growth %" in chart_data.columns:
            hover_data["Earnings Growth %"] = ":.1f"

        if "Forward PE" in chart_data.columns:
            hover_data["Forward PE"] = ":.1f"

        if "PEG" in chart_data.columns:
            hover_data["PEG"] = ":.2f"

        if "Rating" in chart_data.columns:
            hover_data["Rating"] = True

        # -------------------------------------------------
        # Scatter configuration
        # -------------------------------------------------
        scatter_args = {
            "data_frame": chart_data,
            "x": "Growth Score",
            "y": "Overall Score",
            "color": (
                "Sector"
                if "Sector" in chart_data.columns
                else None
            ),
            "color_discrete_map": SECTOR_COLORS,
            "hover_name": (
                "Ticker"
                if "Ticker" in chart_data.columns
                else None
            ),
        }

        # -------------------------------------------------
        # Market cap controls bubble size and hover display
        # -------------------------------------------------
        if "Market Cap" in chart_data.columns:
            positive_caps = numeric_series(
                chart_data,
                "Market Cap",
            ).clip(lower=1)

            chart_data["Chart Market Cap"] = positive_caps
            chart_data["Market Cap ($B)"] = (
                positive_caps / 1_000_000_000
            )

            scatter_args["size"] = "Chart Market Cap"
            scatter_args["size_max"] = 40

            hover_data["Market Cap ($B)"] = ":$.1f"

            # Hide raw bubble-size field from hover
            hover_data["Chart Market Cap"] = False

        scatter_args["hover_data"] = hover_data

        # -------------------------------------------------
        # Build chart
        # -------------------------------------------------
        figure = px.scatter(**scatter_args)

        figure.update_xaxes(
            range=[0, 100],
            title="Growth Score",
        )

        figure.update_yaxes(
            range=[0, 100],
            title="Overall Score",
        )

        figure.update_layout(
            height=560,
            margin=dict(
                l=10,
                r=10,
                t=20,
                b=10,
            ),
            legend_title="Sector",
        )

        st.plotly_chart(
            figure,
            use_container_width=True,
        )

    st.caption(
        "Scores are quantitative research tools. Missing metrics are excluded "
        "and the remaining available components are reweighted by the scoring engine."
    )
# =========================================================
# Run page
# =========================================================
show()
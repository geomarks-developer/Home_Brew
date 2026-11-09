from __future__ import annotations

import pandas as pd
import streamlit as st

from market_data import get_market_data


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.header("💵 Dividend Aristocrat Screener")
st.caption(
    "Filter and rank Dividend Aristocrats by income, dividend growth, "
    "valuation, quality, momentum, risk, and the overall MarketScope score."
)


# ---------------------------------------------------------
# Load shared data
# ---------------------------------------------------------

try:
    data = get_market_data(show_progress=False)
except Exception as exc:
    st.error(f"Unable to load MarketScope Dividend data: {exc}")
    st.stop()


df = data.get("dividend_df", pd.DataFrame()).copy()

if df.empty:
    st.warning("No Dividend Aristocrat data is currently available.")
    st.stop()


# ---------------------------------------------------------
# Numeric preparation
# ---------------------------------------------------------

numeric_columns = [
    "Price",
    "Dividend Yield",
    "Payout Ratio",
    "Dividend Growth 5Y",
    "P/E",
    "Forward P/E",
    "PEG",
    "ROE",
    "Debt to Equity",
    "Return 1Y",
    "RSI",
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
    "Overall Score",
]

for column in numeric_columns:
    if column in df.columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")


# ---------------------------------------------------------
# Filters
# ---------------------------------------------------------

st.subheader("Filters")

sectors = sorted(
    value for value in df["Sector"].dropna().astype(str).unique()
    if value
)

filter_row_1 = st.columns([1.5, 1, 1, 1])

with filter_row_1[0]:
    selected_sectors = st.multiselect(
        "Sector",
        options=sectors,
        default=sectors,
    )

with filter_row_1[1]:
    min_yield = st.number_input(
        "Minimum dividend yield (%)",
        min_value=0.0,
        max_value=20.0,
        value=0.0,
        step=0.25,
    ) / 100

with filter_row_1[2]:
    min_growth = st.number_input(
        "Minimum 5Y dividend growth (%)",
        min_value=-25.0,
        max_value=50.0,
        value=0.0,
        step=0.5,
    ) / 100

with filter_row_1[3]:
    min_score = st.number_input(
        "Minimum overall score",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
    )

filter_row_2 = st.columns(4)

with filter_row_2[0]:
    max_payout = st.number_input(
        "Maximum payout ratio (%)",
        min_value=0.0,
        max_value=300.0,
        value=100.0,
        step=5.0,
    ) / 100

with filter_row_2[1]:
    max_pe = st.number_input(
        "Maximum P/E",
        min_value=0.0,
        max_value=200.0,
        value=50.0,
        step=1.0,
    )

with filter_row_2[2]:
    min_quality = st.number_input(
        "Minimum quality score",
        min_value=0.0,
        max_value=100.0,
        value=0.0,
        step=5.0,
    )

with filter_row_2[3]:
    positive_momentum = st.checkbox(
        "Require price above 200-day SMA",
        value=False,
    )


# ---------------------------------------------------------
# Apply filters
# ---------------------------------------------------------

filtered = df.copy()

if selected_sectors:
    filtered = filtered[filtered["Sector"].isin(selected_sectors)]
else:
    filtered = filtered.iloc[0:0]

if "Dividend Yield" in filtered.columns:
    filtered = filtered[
        filtered["Dividend Yield"].fillna(-1) >= min_yield
    ]

if "Dividend Growth 5Y" in filtered.columns:
    filtered = filtered[
        filtered["Dividend Growth 5Y"].fillna(-999) >= min_growth
    ]

if "Overall Score" in filtered.columns:
    filtered = filtered[
        filtered["Overall Score"].fillna(-1) >= min_score
    ]

if "Payout Ratio" in filtered.columns:
    filtered = filtered[
        filtered["Payout Ratio"].isna()
        | (filtered["Payout Ratio"] <= max_payout)
    ]

if "P/E" in filtered.columns:
    filtered = filtered[
        filtered["P/E"].isna()
        | (
            (filtered["P/E"] > 0)
            & (filtered["P/E"] <= max_pe)
        )
    ]

if "Quality Score" in filtered.columns:
    filtered = filtered[
        filtered["Quality Score"].fillna(-1) >= min_quality
    ]

if positive_momentum and "Price vs SMA 200" in filtered.columns:
    filtered = filtered[
        pd.to_numeric(
            filtered["Price vs SMA 200"], errors="coerce"
        ).fillna(-1) > 0
    ]


# ---------------------------------------------------------
# Sorting controls
# ---------------------------------------------------------

sort_options = [
    column
    for column in [
        "Overall Score",
        "Dividend Score",
        "Quality Score",
        "Value Score",
        "Momentum Score",
        "Risk Score",
        "Dividend Yield",
        "Dividend Growth 5Y",
        "P/E",
        "Return 1Y",
    ]
    if column in filtered.columns
]

sort_col, direction_col, count_col = st.columns([1.3, 1, 2])

with sort_col:
    sort_by = st.selectbox(
        "Rank results by",
        sort_options,
        index=0,
    )

with direction_col:
    highest_first = st.selectbox(
        "Order",
        ["Highest first", "Lowest first"],
        index=0,
    ) == "Highest first"

filtered = filtered.sort_values(
    sort_by,
    ascending=not highest_first,
    na_position="last",
).reset_index(drop=True)

with count_col:
    st.metric(
        "Stocks matching filters",
        f"{len(filtered)} of {len(df)}",
    )


# ---------------------------------------------------------
# Screener table
# ---------------------------------------------------------

st.divider()
st.subheader("Screener Results")

display_columns = [
    "Rank",
    "Ticker",
    "Company",
    "Sector",
    "Price",
    "Dividend Yield",
    "Payout Ratio",
    "Dividend Growth 5Y",
    "P/E",
    "Forward P/E",
    "PEG",
    "ROE",
    "Debt to Equity",
    "Return 1Y",
    "RSI",
    "Dividend Score",
    "Quality Score",
    "Value Score",
    "Momentum Score",
    "Risk Score",
    "Overall Score",
    "Rating",
]

display_columns = [
    column for column in display_columns
    if column in filtered.columns
]

if filtered.empty:
    st.info("No stocks match the current filter settings.")
else:
    table = filtered[display_columns].copy()

    st.dataframe(
        table,
        hide_index=True,
        use_container_width=True,
        height=650,
        column_config={
            "Rank": st.column_config.NumberColumn(
                "Rank", format="%d", width="small"
            ),
            "Ticker": st.column_config.TextColumn(
                "Ticker", width="small", pinned=True
            ),
            "Company": st.column_config.TextColumn(
                "Company", width="medium"
            ),
            "Sector": st.column_config.TextColumn(
                "Sector", width="medium"
            ),
            "Price": st.column_config.NumberColumn(
                "Price", format="$%.2f"
            ),
            "Dividend Yield": st.column_config.NumberColumn(
                "Yield", format="%.2f%%"
            ),
            "Payout Ratio": st.column_config.NumberColumn(
                "Payout", format="%.1f%%"
            ),
            "Dividend Growth 5Y": st.column_config.NumberColumn(
                "5Y Div Growth", format="%.2f%%"
            ),
            "P/E": st.column_config.NumberColumn(
                "P/E", format="%.1f"
            ),
            "Forward P/E": st.column_config.NumberColumn(
                "Fwd P/E", format="%.1f"
            ),
            "PEG": st.column_config.NumberColumn(
                "PEG", format="%.2f"
            ),
            "ROE": st.column_config.NumberColumn(
                "ROE", format="%.1f%%"
            ),
            "Debt to Equity": st.column_config.NumberColumn(
                "Debt/Equity", format="%.1f"
            ),
            "Return 1Y": st.column_config.NumberColumn(
                "1Y Return", format="%.2f%%"
            ),
            "RSI": st.column_config.NumberColumn(
                "RSI", format="%.1f"
            ),
            "Dividend Score": st.column_config.ProgressColumn(
                "Dividend", min_value=0, max_value=100, format="%.1f"
            ),
            "Quality Score": st.column_config.ProgressColumn(
                "Quality", min_value=0, max_value=100, format="%.1f"
            ),
            "Value Score": st.column_config.ProgressColumn(
                "Value", min_value=0, max_value=100, format="%.1f"
            ),
            "Momentum Score": st.column_config.ProgressColumn(
                "Momentum", min_value=0, max_value=100, format="%.1f"
            ),
            "Risk Score": st.column_config.ProgressColumn(
                "Risk", min_value=0, max_value=100, format="%.1f"
            ),
            "Overall Score": st.column_config.ProgressColumn(
                "Overall", min_value=0, max_value=100, format="%.1f"
            ),
        },
    )


# ---------------------------------------------------------
# Quick leaders
# ---------------------------------------------------------

if not filtered.empty:
    st.divider()
    st.subheader("Quick View")

    metric_columns = st.columns(5)

    leader_metrics = [
        ("Highest Overall", "Overall Score"),
        ("Best Dividend", "Dividend Score"),
        ("Best Quality", "Quality Score"),
        ("Best Value", "Value Score"),
        ("Highest Yield", "Dividend Yield"),
    ]

    for container, (label, metric) in zip(metric_columns, leader_metrics):
        if metric not in filtered.columns:
            continue

        numeric = pd.to_numeric(filtered[metric], errors="coerce")
        if not numeric.notna().any():
            continue

        row = filtered.loc[numeric.idxmax()]

        if metric == "Dividend Yield":
            detail = f'{float(row[metric]):.2%}'
        else:
            detail = f'{float(row[metric]):.1f}'

        with container:
            st.metric(label, str(row["Ticker"]), detail)


# ---------------------------------------------------------
# Download filtered results
# ---------------------------------------------------------

st.divider()

csv_data = filtered.to_csv(index=False).encode("utf-8")

st.download_button(
    "⬇️ Download Filtered Results (CSV)",
    data=csv_data,
    file_name="marketscope_dividend_screener.csv",
    mime="text/csv",
    type="secondary",
)

st.caption(
    "MarketScope Dividend scores are research indicators, not investment "
    "recommendations. Dividend payments, fundamentals, and prices can change."
)

"""MarketScope Value side-by-side stock comparison page."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from market_data import load_market_bundle


SCORE_COLUMNS = [
    "Valuation Score",
    "Quality Score",
    "Financial Strength Score",
    "Growth Score",
    "Momentum Score",
    "Overall Score",
]

PERCENT_COLUMNS = [
    "FCF Yield",
    "Earnings Yield",
    "Revenue Growth",
    "Earnings Growth",
    "EPS Growth",
    "Forward EPS Growth",
    "ROE",
    "ROA",
    "Gross Margin",
    "Operating Margin",
    "Profit Margin",
    "6M Return",
    "12M Return",
    "Net Debt/Market Cap",
    "Overall Coverage",
]


def numeric(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def close_series(history: pd.DataFrame | None) -> pd.Series:
    if history is None or history.empty:
        return pd.Series(dtype=float)
    column = "Adj Close" if "Adj Close" in history.columns else "Close"
    if column not in history.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(history[column], errors="coerce").dropna().sort_index()


def comparison_config() -> dict:
    config = {
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Enterprise Value": st.column_config.NumberColumn("Enterprise Value", format="compact"),
        "Free Cash Flow": st.column_config.NumberColumn("Free Cash Flow", format="compact"),
        "Operating Cash Flow": st.column_config.NumberColumn("Operating Cash Flow", format="compact"),
        "Total Cash": st.column_config.NumberColumn("Total Cash", format="compact"),
        "Total Debt": st.column_config.NumberColumn("Total Debt", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Trailing PE": st.column_config.NumberColumn("Trailing P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "Price/Sales": st.column_config.NumberColumn("P/S", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "PEG": st.column_config.NumberColumn("PEG", format="%.2f"),
        "Debt/Equity": st.column_config.NumberColumn("Debt/Equity", format="%.1f"),
        "Current Ratio": st.column_config.NumberColumn("Current Ratio", format="%.2f"),
        "Quick Ratio": st.column_config.NumberColumn("Quick Ratio", format="%.2f"),
        "Cash/Debt": st.column_config.NumberColumn("Cash/Debt", format="%.2f"),
        "Value Trap Risk": st.column_config.ProgressColumn(
            "Trap Risk", min_value=0, max_value=100, format="%.1f"
        ),
    }
    for column in PERCENT_COLUMNS:
        config[column] = st.column_config.NumberColumn(column, format="percent")
    for column in SCORE_COLUMNS:
        config[column] = st.column_config.ProgressColumn(
            column.replace(" Score", ""),
            min_value=0,
            max_value=100,
            format="%.1f",
        )
    return config


def metric_comparison(data: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    available = [column for column in columns if column in data.columns]
    if not available:
        return pd.DataFrame()
    table = data.set_index("Ticker")[available].T
    table.index.name = "Metric"
    return table


def normalized_history(histories: dict[str, pd.DataFrame], tickers: list[str]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for ticker in tickers:
        prices = close_series(histories.get(ticker))
        if prices.empty:
            continue
        normalized = prices / prices.iloc[0] * 100
        frames.append(
            pd.DataFrame(
                {
                    "Date": normalized.index,
                    "Indexed Value": normalized.values,
                    "Ticker": ticker,
                }
            )
        )
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def show() -> None:
    st.title("⚖️ Compare Value Stocks")
    st.caption(
        "Compare valuation, quality, financial strength, growth, momentum, price performance, "
        "and value-trap risk side by side."
    )

    try:
        with st.spinner("Loading MarketScope Value comparison data..."):
            bundle = load_market_bundle()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    data = bundle.get("data", pd.DataFrame()).copy()
    histories = bundle.get("histories", {})
    if data.empty or "Ticker" not in data.columns:
        st.warning("No stock-comparison data is currently available.")
        return

    data["Ticker"] = data["Ticker"].astype(str).str.upper()
    data = data.drop_duplicates(subset="Ticker", keep="first")
    tickers = data["Ticker"].sort_values().tolist()
    defaults = tickers[: min(3, len(tickers))]

    selected = st.multiselect(
        "Choose 2 to 5 stocks",
        tickers,
        default=defaults,
        max_selections=5,
    )

    if len(selected) < 2:
        st.info("Choose at least two stocks to begin the comparison.")
        return

    compared = data[data["Ticker"].isin(selected)].copy()
    compared["Ticker"] = pd.Categorical(compared["Ticker"], categories=selected, ordered=True)
    compared = compared.sort_values("Ticker").reset_index(drop=True)
    compared["Ticker"] = compared["Ticker"].astype(str)

    # -----------------------------------------------------
    # Headline cards
    # -----------------------------------------------------
    cards = st.columns(len(compared))
    for container, (_, record) in zip(cards, compared.iterrows()):
        ticker = record["Ticker"]
        company = str(record.get("Company") or ticker)
        overall = record.get("Overall Score")
        trap = record.get("Value Trap Risk")
        with container:
            st.markdown(f"### {ticker}")
            st.caption(company)
            st.metric("Overall Score", f"{overall:.1f}" if pd.notna(overall) else "N/A")
            st.metric("Valuation Score", f"{record.get('Valuation Score'):.1f}" if pd.notna(record.get("Valuation Score")) else "N/A")
            st.metric("Value-Trap Risk", f"{trap:.1f}" if pd.notna(trap) else "N/A")
            st.caption(str(record.get("Rating") or "Insufficient Data"))

    st.divider()

    # -----------------------------------------------------
    # Score comparison
    # -----------------------------------------------------
    st.subheader("Score Comparison")
    score_long = compared.melt(
        id_vars="Ticker",
        value_vars=[column for column in SCORE_COLUMNS if column in compared.columns],
        var_name="Category",
        value_name="Score",
    ).dropna(subset=["Score"])
    score_long["Category"] = score_long["Category"].str.replace(" Score", "", regex=False)

    if not score_long.empty:
        fig = px.bar(
            score_long,
            x="Category",
            y="Score",
            color="Ticker",
            barmode="group",
            text="Score",
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_yaxes(range=[0, 110], title="Score")
        fig.update_layout(height=480, xaxis_title="", legend_title="Stock")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Price performance
    # -----------------------------------------------------
    st.divider()
    st.subheader("Indexed Price Performance")
    performance = normalized_history(histories, selected)
    if performance.empty:
        st.info("Price history is unavailable for the selected stocks.")
    else:
        fig = px.line(
            performance,
            x="Date",
            y="Indexed Value",
            color="Ticker",
            hover_data={"Indexed Value": ":.1f"},
        )
        fig.add_hline(y=100, line_dash="dot", line_color="gray")
        fig.update_layout(
            height=500,
            xaxis_title="",
            yaxis_title="Growth of $100",
            legend_title="Stock",
            hovermode="x unified",
        )
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Valuation vs. trap-risk comparison
    # -----------------------------------------------------
    st.divider()
    st.subheader("Valuation vs. Value-Trap Risk")
    scatter = compared.dropna(subset=["Valuation Score", "Value Trap Risk"]).copy()
    if not scatter.empty:
        scatter["Market Cap ($B)"] = numeric(scatter, "Market Cap") / 1_000_000_000
        scatter["Bubble Size"] = numeric(scatter, "Market Cap").clip(lower=1)
        fig = px.scatter(
            scatter,
            x="Valuation Score",
            y="Value Trap Risk",
            color="Ticker",
            size="Bubble Size",
            size_max=55,
            text="Ticker",
            hover_name="Company" if "Company" in scatter.columns else "Ticker",
            hover_data={
                "Overall Score": ":.1f",
                "Quality Score": ":.1f",
                "Financial Strength Score": ":.1f",
                "FCF Yield": ":.1%",
                "Forward PE": ":.1f",
                "Market Cap ($B)": ":$.1f",
                "Bubble Size": False,
            },
        )
        fig.update_traces(textposition="top center")
        fig.add_vline(x=65, line_dash="dot", line_color="gray")
        fig.add_hline(y=50, line_dash="dot", line_color="gray")
        fig.update_xaxes(range=[0, 100], title="Valuation Score → more attractive")
        fig.update_yaxes(range=[100, 0], title="Value-Trap Risk → lower is better")
        fig.update_layout(height=540, legend_title="Stock")
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Comparison tables
    # -----------------------------------------------------
    st.divider()
    valuation_tab, quality_tab, strength_tab, growth_tab, momentum_tab = st.tabs(
        ["Valuation", "Quality", "Financial Strength", "Growth", "Momentum"]
    )

    table_sets = [
        (
            valuation_tab,
            [
                "Price",
                "Market Cap",
                "Enterprise Value",
                "Forward PE",
                "Trailing PE",
                "Price/Book",
                "Price/Sales",
                "EV/EBITDA",
                "PEG",
                "FCF Yield",
                "Earnings Yield",
                "Valuation Score",
            ],
        ),
        (
            quality_tab,
            [
                "ROE",
                "ROA",
                "Gross Margin",
                "Operating Margin",
                "Profit Margin",
                "Free Cash Flow",
                "Operating Cash Flow",
                "Quality Score",
            ],
        ),
        (
            strength_tab,
            [
                "Total Cash",
                "Total Debt",
                "Net Debt/Market Cap",
                "Cash/Debt",
                "Debt/Equity",
                "Current Ratio",
                "Quick Ratio",
                "Financial Strength Score",
            ],
        ),
        (
            growth_tab,
            [
                "Revenue Growth",
                "Earnings Growth",
                "EPS Growth",
                "Forward EPS Growth",
                "Growth Score",
            ],
        ),
        (
            momentum_tab,
            [
                "6M Return",
                "12M Return",
                "50D MA",
                "200D MA",
                "52W High",
                "52W Low",
                "Momentum Score",
                "Value Trap Risk",
            ],
        ),
    ]

    for tab, metrics in table_sets:
        with tab:
            table = metric_comparison(compared, metrics)
            if table.empty:
                st.info("No comparison data is available for this category.")
            else:
                st.dataframe(table, use_container_width=True)

    # -----------------------------------------------------
    # Full rows and export
    # -----------------------------------------------------
    st.divider()
    st.subheader("Full Comparison")
    display_columns = [
        column
        for column in (
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
            "Revenue Growth",
            "Earnings Growth",
            "ROE",
            "Debt/Equity",
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
        )
        if column in compared.columns
    ]

    st.dataframe(
        compared[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=comparison_config(),
    )

    st.download_button(
        "Download Comparison CSV",
        data=compared[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_value_comparison.csv",
        mime="text/csv",
        type="secondary",
    )

    st.caption(
        "Comparisons are most meaningful among businesses with similar economics and accounting characteristics. "
        "A lower multiple is not automatically superior when profitability, leverage, cyclicality, or growth differ."
    )


show()

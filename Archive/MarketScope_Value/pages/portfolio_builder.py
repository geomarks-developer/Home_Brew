"""MarketScope Value portfolio builder."""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import SECTOR_COLORS
from market_data import load_market_data


SCORE_COLUMNS = [
    "Valuation Score",
    "Quality Score",
    "Financial Strength Score",
    "Growth Score",
    "Momentum Score",
    "Overall Score",
]

PERCENT_COLUMNS = [
    "Weight",
    "FCF Yield",
    "Revenue Growth",
    "Earnings Growth",
    "6M Return",
    "12M Return",
]


def numeric(data: pd.DataFrame, column: str) -> pd.Series:
    if column not in data.columns:
        return pd.Series(float("nan"), index=data.index, dtype=float)
    return pd.to_numeric(data[column], errors="coerce")


def weighted_average(data: pd.DataFrame, column: str) -> float:
    values = numeric(data, column)
    weights = numeric(data, "Weight")
    valid = values.notna() & weights.notna() & (weights > 0)
    if not valid.any():
        return np.nan
    return float(np.average(values[valid], weights=weights[valid]))


def portfolio_config() -> dict:
    config = {
        "Ticker": st.column_config.TextColumn("Ticker", pinned=True),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Market Cap": st.column_config.NumberColumn("Market Cap", format="compact"),
        "Forward PE": st.column_config.NumberColumn("Forward P/E", format="%.1f"),
        "Price/Book": st.column_config.NumberColumn("P/B", format="%.2f"),
        "EV/EBITDA": st.column_config.NumberColumn("EV/EBITDA", format="%.1f"),
        "Allocation": st.column_config.NumberColumn("Allocation", format="$%.2f"),
        "Shares": st.column_config.NumberColumn("Shares", format="%.3f"),
        "Whole Shares": st.column_config.NumberColumn("Whole Shares", format="%d"),
        "Whole Share Cost": st.column_config.NumberColumn("Whole Share Cost", format="$%.2f"),
        "Cash Remaining": st.column_config.NumberColumn("Cash Remaining", format="$%.2f"),
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


def prepare_candidates(data: pd.DataFrame) -> pd.DataFrame:
    candidates = data.copy()
    candidates = candidates.dropna(subset=["Ticker", "Price", "Overall Score"])
    candidates = candidates[numeric(candidates, "Price") > 0]
    candidates["Sector"] = candidates.get("Sector", "Unknown")
    candidates["Sector"] = candidates["Sector"].fillna("Unknown").replace("", "Unknown")
    return candidates


def choose_model_weights(
    candidates: pd.DataFrame,
    model: str,
    stock_count: int,
    maximum_sector_weight: float,
) -> pd.DataFrame:
    work = candidates.copy()

    if model == "Deep Value":
        work["Model Score"] = (
            numeric(work, "Valuation Score") * 0.60
            + numeric(work, "Quality Score") * 0.15
            + numeric(work, "Financial Strength Score") * 0.10
            + numeric(work, "Momentum Score") * 0.05
            + (100 - numeric(work, "Value Trap Risk")) * 0.10
        )
    elif model == "Quality Value":
        work["Model Score"] = (
            numeric(work, "Valuation Score") * 0.35
            + numeric(work, "Quality Score") * 0.30
            + numeric(work, "Financial Strength Score") * 0.20
            + numeric(work, "Growth Score") * 0.05
            + (100 - numeric(work, "Value Trap Risk")) * 0.10
        )
    elif model == "Low Trap Risk":
        work["Model Score"] = (
            numeric(work, "Valuation Score") * 0.30
            + numeric(work, "Quality Score") * 0.20
            + numeric(work, "Financial Strength Score") * 0.15
            + numeric(work, "Momentum Score") * 0.10
            + (100 - numeric(work, "Value Trap Risk")) * 0.25
        )
    else:
        work["Model Score"] = (
            numeric(work, "Overall Score") * 0.70
            + (100 - numeric(work, "Value Trap Risk")) * 0.30
        )

    work = work.sort_values("Model Score", ascending=False, na_position="last")

    selected_rows: list[pd.Series] = []
    sector_counts: dict[str, int] = {}
    maximum_sector_positions = max(1, int(np.floor(stock_count * maximum_sector_weight)))

    for _, row in work.iterrows():
        sector = str(row.get("Sector") or "Unknown")
        if sector_counts.get(sector, 0) >= maximum_sector_positions:
            continue
        selected_rows.append(row)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        if len(selected_rows) >= stock_count:
            break

    # If the sector cap prevents a full portfolio, fill remaining slots by score.
    chosen_tickers = {str(row["Ticker"]) for row in selected_rows}
    if len(selected_rows) < stock_count:
        for _, row in work.iterrows():
            ticker = str(row["Ticker"])
            if ticker in chosen_tickers:
                continue
            selected_rows.append(row)
            chosen_tickers.add(ticker)
            if len(selected_rows) >= stock_count:
                break

    portfolio = pd.DataFrame(selected_rows).reset_index(drop=True)
    if portfolio.empty:
        return portfolio

    if model == "Equal Weight":
        portfolio["Weight"] = 1.0 / len(portfolio)
    else:
        raw = numeric(portfolio, "Model Score").clip(lower=1)
        portfolio["Weight"] = raw / raw.sum()

    return portfolio


def calculate_allocations(portfolio: pd.DataFrame, portfolio_value: float) -> pd.DataFrame:
    result = portfolio.copy()
    result["Allocation"] = numeric(result, "Weight") * portfolio_value
    result["Shares"] = result["Allocation"] / numeric(result, "Price")
    result["Whole Shares"] = np.floor(result["Shares"]).fillna(0).astype(int)
    result["Whole Share Cost"] = result["Whole Shares"] * numeric(result, "Price")
    result["Cash Remaining"] = result["Allocation"] - result["Whole Share Cost"]
    return result


def show() -> None:
    st.title("🧺 Value Portfolio Builder")
    st.caption(
        "Build a model value portfolio using valuation, quality, financial strength, "
        "momentum, diversification, and value-trap controls."
    )

    try:
        with st.spinner("Loading MarketScope Value portfolio data..."):
            data = load_market_data()
    except Exception as exc:
        st.error("MarketScope Value data could not be loaded.")
        st.exception(exc)
        return

    if data is None or data.empty:
        st.warning("No portfolio data is currently available.")
        return

    candidates = prepare_candidates(data)
    if candidates.empty:
        st.warning("No stocks have sufficient price and score data for portfolio construction.")
        return

    # -----------------------------------------------------
    # Portfolio controls
    # -----------------------------------------------------
    st.subheader("Portfolio Settings")
    row1 = st.columns(4)
    with row1[0]:
        portfolio_value = st.number_input(
            "Portfolio value",
            min_value=1_000.0,
            value=25_000.0,
            step=1_000.0,
            format="%.0f",
        )
    with row1[1]:
        model = st.selectbox(
            "Portfolio model",
            ["Balanced Value", "Deep Value", "Quality Value", "Low Trap Risk", "Equal Weight"],
        )
    with row1[2]:
        stock_count = st.slider("Number of stocks", 5, min(30, len(candidates)), 12)
    with row1[3]:
        maximum_sector_weight_pct = st.slider(
            "Maximum sector weight",
            10,
            50,
            25,
            5,
            format="%d%%",
        )

    row2 = st.columns(4)
    with row2[0]:
        minimum_overall = st.slider("Minimum Overall Score", 0.0, 100.0, 55.0, 1.0)
    with row2[1]:
        minimum_valuation = st.slider("Minimum Valuation Score", 0.0, 100.0, 60.0, 1.0)
    with row2[2]:
        minimum_quality = st.slider("Minimum Quality Score", 0.0, 100.0, 45.0, 1.0)
    with row2[3]:
        maximum_trap_risk = st.slider("Maximum Value-Trap Risk", 0.0, 100.0, 55.0, 1.0)

    sectors = sorted(candidates["Sector"].astype(str).unique())
    selected_sectors = st.multiselect("Eligible sectors", sectors, default=sectors)

    eligible = candidates[candidates["Sector"].astype(str).isin(selected_sectors)].copy()
    eligible = eligible[
        (numeric(eligible, "Overall Score") >= minimum_overall)
        & (numeric(eligible, "Valuation Score") >= minimum_valuation)
        & (numeric(eligible, "Quality Score") >= minimum_quality)
        & (numeric(eligible, "Value Trap Risk") <= maximum_trap_risk)
    ]

    if len(eligible) < stock_count:
        st.warning(
            f"Only {len(eligible)} stocks meet the selected requirements. "
            "The portfolio will use all available matches unless the filters are relaxed."
        )
        stock_count = min(stock_count, len(eligible))

    if stock_count == 0:
        st.info("No stocks meet the current portfolio requirements.")
        return

    portfolio = choose_model_weights(
        eligible,
        model=model,
        stock_count=stock_count,
        maximum_sector_weight=maximum_sector_weight_pct / 100,
    )
    portfolio = calculate_allocations(portfolio, portfolio_value)

    # -----------------------------------------------------
    # Portfolio summary
    # -----------------------------------------------------
    st.divider()
    st.subheader("Portfolio Summary")
    summary = st.columns(6)
    summary[0].metric("Stocks", f"{len(portfolio)}")
    summary[1].metric("Sectors", f"{portfolio['Sector'].nunique()}")
    summary[2].metric("Overall Score", f"{weighted_average(portfolio, 'Overall Score'):.1f}")
    summary[3].metric("Valuation Score", f"{weighted_average(portfolio, 'Valuation Score'):.1f}")
    summary[4].metric("FCF Yield", f"{weighted_average(portfolio, 'FCF Yield'):.1%}")
    summary[5].metric("Trap Risk", f"{weighted_average(portfolio, 'Value Trap Risk'):.1f}")

    # -----------------------------------------------------
    # Holdings table
    # -----------------------------------------------------
    st.subheader("Model Holdings")
    display_columns = [
        column
        for column in (
            "Ticker",
            "Company",
            "Sector",
            "Price",
            "Weight",
            "Allocation",
            "Shares",
            "Whole Shares",
            "Whole Share Cost",
            "Cash Remaining",
            "Forward PE",
            "FCF Yield",
            "Valuation Score",
            "Quality Score",
            "Financial Strength Score",
            "Growth Score",
            "Momentum Score",
            "Overall Score",
            "Value Trap Risk",
            "Value Trap Rating",
        )
        if column in portfolio.columns
    ]

    st.dataframe(
        portfolio[display_columns],
        use_container_width=True,
        hide_index=True,
        column_config=portfolio_config(),
    )

    st.download_button(
        "Download Portfolio CSV",
        data=portfolio[display_columns].to_csv(index=False).encode("utf-8"),
        file_name="marketscope_value_portfolio.csv",
        mime="text/csv",
        type="secondary",
    )

    # -----------------------------------------------------
    # Allocation charts
    # -----------------------------------------------------
    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("Stock Allocation")
        fig = px.pie(
            portfolio,
            names="Ticker",
            values="Weight",
            hover_data={
                "Company": True if "Company" in portfolio.columns else False,
                "Sector": True,
                "Allocation": ":$,.2f",
                "Overall Score": ":.1f",
                "Value Trap Risk": ":.1f",
            },
        )
        fig.update_traces(textposition="inside", textinfo="label+percent")
        fig.update_layout(height=480, legend_title="Stock")
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.subheader("Sector Allocation")
        sector_allocation = (
            portfolio.groupby("Sector", as_index=False)["Weight"].sum().sort_values("Weight", ascending=False)
        )
        fig = px.bar(
            sector_allocation,
            x="Sector",
            y="Weight",
            color="Sector",
            color_discrete_map=SECTOR_COLORS,
            text="Weight",
        )
        fig.update_traces(texttemplate="%{text:.1%}", textposition="outside")
        fig.update_yaxes(tickformat=".0%", title="Portfolio Weight")
        fig.update_layout(height=480, showlegend=False, xaxis_tickangle=-35)
        st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Portfolio score profile
    # -----------------------------------------------------
    st.divider()
    st.subheader("Portfolio Score Profile")
    profile = pd.DataFrame(
        {
            "Category": [column.replace(" Score", "") for column in SCORE_COLUMNS],
            "Score": [weighted_average(portfolio, column) for column in SCORE_COLUMNS],
        }
    ).dropna()

    fig = px.bar(
        profile.sort_values("Score"),
        x="Score",
        y="Category",
        orientation="h",
        color="Score",
        color_continuous_scale="RdYlGn",
        text="Score",
    )
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_xaxes(range=[0, 100])
    fig.update_layout(
        height=430,
        coloraxis_showscale=False,
        xaxis_title="Weighted Portfolio Score",
        yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

    # -----------------------------------------------------
    # Risk review
    # -----------------------------------------------------
    st.divider()
    st.subheader("Portfolio Risk Review")
    high_trap = portfolio[numeric(portfolio, "Value Trap Risk") >= 50]
    concentration = portfolio.groupby("Sector")["Weight"].sum().sort_values(ascending=False)
    largest_sector = concentration.index[0] if not concentration.empty else "N/A"
    largest_sector_weight = concentration.iloc[0] if not concentration.empty else np.nan
    largest_position = portfolio.sort_values("Weight", ascending=False).iloc[0]

    review = st.columns(4)
    review[0].metric("Positions with Trap Risk ≥ 50", f"{len(high_trap)}")
    review[1].metric(
        "Largest Position",
        str(largest_position["Ticker"]),
        f"{largest_position['Weight']:.1%}",
    )
    review[2].metric(
        "Largest Sector",
        str(largest_sector),
        f"{largest_sector_weight:.1%}" if pd.notna(largest_sector_weight) else None,
    )
    review[3].metric(
        "Whole-Share Cash Left",
        f"${portfolio['Cash Remaining'].sum():,.2f}",
    )

    if not high_trap.empty:
        st.warning(
            "The model portfolio includes one or more positions with elevated Value-Trap Risk. "
            "Review those companies individually before using the allocation."
        )

    st.caption(
        "This page creates a quantitative model portfolio, not a personalized investment recommendation. "
        "It does not account for taxes, transaction costs, liquidity needs, existing holdings, or individual risk tolerance."
    )


show()

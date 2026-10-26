import pandas as pd
import plotly.express as px
import streamlit as st

from screener_engine import build_sample_portfolio


# ---------------------------------------------------------
# Page header
# ---------------------------------------------------------

st.title("💼 Sample Portfolio")

st.caption(
    "A hypothetical $10,000 portfolio built from the highest-ranked "
    "Stock, Dividend, and ETF screener results while attempting to "
    "minimize sector overlap."
)


# ---------------------------------------------------------
# Get shared MarketScope data
# ---------------------------------------------------------

shared_data = st.session_state.get("market_data")

if shared_data is None:
    st.error(
        "Shared MarketScope data is not loaded. "
        "Restart the app to initialize market data."
    )
    st.stop()


# ---------------------------------------------------------
# Get screener DataFrames
# ---------------------------------------------------------

stocks = shared_data["stock_df"].copy()
dividends = shared_data["dividend_df"].copy()
etfs = shared_data["etf_df"].copy()


if stocks.empty:
    st.warning("The stock screener did not return any results.")
    st.stop()

if dividends.empty:
    st.warning("The dividend screener did not return any results.")
    st.stop()

if etfs.empty:
    st.warning("The ETF screener did not return any results.")
    st.stop()


# ---------------------------------------------------------
# Sort strongest candidates first
# ---------------------------------------------------------

stocks = stocks.sort_values(
    ["Passes Screen", "Score"],
    ascending=[False, False],
    na_position="last",
).reset_index(drop=True)

dividends = dividends.sort_values(
    ["Passes Screen", "Score", "Dividend Yield"],
    ascending=[False, False, False],
    na_position="last",
).reset_index(drop=True)

etfs = etfs.sort_values(
    ["Passes Screen", "Score"],
    ascending=[False, False],
    na_position="last",
).reset_index(drop=True)


# ---------------------------------------------------------
# Portfolio settings
# ---------------------------------------------------------

portfolio_value = 10_000


# ---------------------------------------------------------
# Build sample portfolio
# ---------------------------------------------------------

portfolio = build_sample_portfolio(
    stock_df=stocks,
    dividend_df=dividends,
    etf_df=etfs,
    portfolio_value=portfolio_value,
)

if portfolio.empty:
    st.warning(
        "A sample portfolio could not be created from the "
        "current screener results."
    )
    st.stop()


# ---------------------------------------------------------
# Portfolio summary
# ---------------------------------------------------------

total_invested = pd.to_numeric(
    portfolio["Invested Amount"],
    errors="coerce",
).sum()

cash_remaining = portfolio_value - total_invested

number_holdings = len(portfolio)

sector_count = (
    portfolio["Sector"]
    .dropna()
    .astype(str)
    .replace("Unclassified", pd.NA)
    .dropna()
    .nunique()
)


m1, m2, m3, m4 = st.columns(4)

m1.metric(
    "Starting Portfolio",
    f"${portfolio_value:,.0f}",
)

m2.metric(
    "Amount Invested",
    f"${total_invested:,.2f}",
)

m3.metric(
    "Cash Remaining",
    f"${cash_remaining:,.2f}",
)

m4.metric(
    "Sectors Represented",
    f"{sector_count}",
)


# ---------------------------------------------------------
# Portfolio construction
# ---------------------------------------------------------

st.divider()

st.subheader("Portfolio Construction")

c1, c2, c3 = st.columns(3)

with c1:
    with st.container(border=True):
        st.markdown("### 📈 Stocks")
        st.metric("Target Positions", "3")
        st.metric("Target Allocation", "$3,000")
        st.caption("30% of portfolio")

with c2:
    with st.container(border=True):
        st.markdown("### 💵 Dividend Stocks")
        st.metric("Target Positions", "4")
        st.metric("Target Allocation", "$4,000")
        st.caption("40% of portfolio")

with c3:
    with st.container(border=True):
        st.markdown("### 📊 ETFs")
        st.metric("Target Positions", "3")
        st.metric("Target Allocation", "$3,000")
        st.caption("30% of portfolio")


# ---------------------------------------------------------
# Portfolio holdings table
# ---------------------------------------------------------

st.divider()

st.subheader("Portfolio Holdings")

st.caption(
    "Positions are selected from the highest-ranked screener results. "
    "Sector diversification is prioritized, and individual position "
    "sizes are weighted using screener scores."
)


display_columns = [
    "Type",
    "Ticker",
    "Sector",
    "Score",
    "Price",
    "Shares",
    "Target Allocation",
    "Invested Amount",
    "Cash Remaining",
    "Actual Weight",
]

display_columns = [
    column
    for column in display_columns
    if column in portfolio.columns
]

display_df = portfolio[display_columns].copy()


# Convert portfolio weights to percentages for display.

if "Actual Weight" in display_df.columns:
    display_df["Actual Weight"] = pd.to_numeric(
        display_df["Actual Weight"],
        errors="coerce",
    ) * 100


st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
    height=450,
    column_config={
        "Type": st.column_config.TextColumn(
            "Investment Type",
            width=140,
        ),
        "Ticker": st.column_config.TextColumn(
            "Ticker",
            width=90,
            pinned=True,
        ),
        "Sector": st.column_config.TextColumn(
            "Sector",
            width=180,
        ),
        "Score": st.column_config.NumberColumn(
            "Score",
            format="%.1f",
        ),
        "Price": st.column_config.NumberColumn(
            "Price",
            format="$%.2f",
        ),
        "Shares": st.column_config.NumberColumn(
            "Shares",
            format="%d",
        ),
        "Target Allocation": st.column_config.NumberColumn(
            "Target",
            format="$%.2f",
        ),
        "Invested Amount": st.column_config.NumberColumn(
            "Invested",
            format="$%.2f",
        ),
        "Cash Remaining": st.column_config.NumberColumn(
            "Unused",
            format="$%.2f",
        ),
        "Actual Weight": st.column_config.NumberColumn(
            "Portfolio %",
            format="%.1f%%",
        ),
    },
)


# ---------------------------------------------------------
# Allocation charts
# ---------------------------------------------------------

st.divider()

st.subheader("Portfolio Allocation")

chart1, chart2 = st.columns(2)


# ---------------------------------------------------------
# Holding allocation
# ---------------------------------------------------------

with chart1:

    allocation_chart = px.pie(
        portfolio,
        names="Ticker",
        values="Invested Amount",
        color="Type",
        hole=0.45,
        title="Allocation by Holding",
    )

    allocation_chart.update_traces(
        textposition="inside",
        textinfo="label+percent",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Allocation: $%{value:,.2f}<br>"
            "Weight: %{percent}"
            "<extra></extra>"
        ),
    )

    allocation_chart.update_layout(
        height=500,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),
        legend_title_text="Investment Type",
    )

    st.plotly_chart(
        allocation_chart,
        width="stretch",
        key="portfolio_allocation_chart",
        config={
            "displayModeBar": True,
            "displaylogo": False,
        },
    )


# ---------------------------------------------------------
# Sector allocation
# ---------------------------------------------------------

with chart2:

    sector_totals = (
        portfolio.groupby(
            "Sector",
            as_index=False,
            observed=True,
        )["Invested Amount"]
        .sum()
        .sort_values(
            "Invested Amount",
            ascending=False,
        )
    )

    sector_chart = px.bar(
        sector_totals,
        x="Sector",
        y="Invested Amount",
        title="Allocation by Sector",
        text_auto=".2s",
        color="Sector",
    )

    sector_chart.update_layout(
        height=500,
        margin=dict(
            l=20,
            r=20,
            t=60,
            b=80,
        ),
        showlegend=False,
        xaxis_title=None,
        yaxis_title="Invested Amount",
        yaxis_tickprefix="$",
        yaxis_tickformat=",",
    )

    sector_chart.update_xaxes(
        tickangle=-35,
    )

    st.plotly_chart(
        sector_chart,
        width="stretch",
        key="portfolio_sector_chart",
        config={
            "displayModeBar": True,
            "displaylogo": False,
        },
    )


# ---------------------------------------------------------
# Allocation by investment type
# ---------------------------------------------------------

st.subheader("Allocation by Investment Type")

type_totals = (
    portfolio.groupby(
        "Type",
        as_index=False,
        observed=True,
    )["Invested Amount"]
    .sum()
)

type_chart = px.bar(
    type_totals,
    x="Type",
    y="Invested Amount",
    color="Type",
    text="Invested Amount",
)

type_chart.update_traces(
    texttemplate="$%{text:,.0f}",
    textposition="outside",
)

type_chart.update_layout(
    height=400,
    margin=dict(
        l=20,
        r=20,
        t=20,
        b=20,
    ),
    showlegend=False,
    xaxis_title=None,
    yaxis_title="Invested Amount",
    yaxis_tickprefix="$",
    yaxis_tickformat=",",
)

st.plotly_chart(
    type_chart,
    width="stretch",
    key="portfolio_type_chart",
    config={
        "displayModeBar": True,
        "displaylogo": False,
    },
)


# ---------------------------------------------------------
# Diversification summary
# ---------------------------------------------------------

st.divider()

st.subheader("Diversification Summary")

unique_tickers = portfolio["Ticker"].nunique()

duplicate_sector_count = (
    portfolio["Sector"]
    .replace("Unclassified", pd.NA)
    .dropna()
    .value_counts()
    .gt(1)
    .sum()
)


d1, d2, d3, d4 = st.columns(4)

d1.metric(
    "Total Holdings",
    unique_tickers,
)

d2.metric(
    "Unique Sectors",
    sector_count,
)

d3.metric(
    "Repeated Sectors",
    int(duplicate_sector_count),
)

d4.metric(
    "Cash %",
    f"{cash_remaining / portfolio_value:.1%}",
)


# ---------------------------------------------------------
# Methodology
# ---------------------------------------------------------

with st.expander("ℹ️ Portfolio Methodology"):

    st.markdown(
        """
        ### Sample Portfolio Methodology

        The sample portfolio starts with **$10,000** and selects
        investments from the current MarketScope screener results.

        **Target construction**

        - **3 Stocks**
        - **4 Dividend Stocks**
        - **3 ETFs**
        - **10 total positions**
        - **30% Stocks**
        - **40% Dividend Stocks**
        - **30% ETFs**

        Individual positions within each category are weighted based
        on their MarketScope screener score. Higher-scoring investments
        receive slightly larger target allocations while preserving the
        overall 30% / 40% / 30% portfolio structure.

        **Selection process**

        Candidates are evaluated in their current screener ranking.

        The portfolio attempts to:

        1. Select the highest-ranked qualifying candidates.
        2. Avoid using the same ticker more than once.
        3. Select investments from different sectors whenever possible.
        4. Reduce sector concentration across stocks, dividend stocks,
           and ETFs.
        5. Use screener scores to determine position sizes within each
           investment category.
        6. Use whole shares when calculating the hypothetical investment.

        If there are not enough qualifying investments from unique
        sectors, the next highest-ranked candidate may be selected even
        if its sector is already represented.

        Cash remaining because of whole-share rounding is left
        uninvested.

        **This portfolio is hypothetical and is intended for research
        and demonstration purposes only. It is not investment advice.**
        """
    )
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path


# ---------------------------------------------------------
# Page configuration
# ---------------------------------------------------------

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    page_icon="📈",
    layout="wide"
)


# ---------------------------------------------------------
# Title
# ---------------------------------------------------------

st.title("📈 Stock Analysis Dashboard")

st.caption(
    "Stock, dividend, and ETF screening results"
)

st.divider()


# ---------------------------------------------------------
# Temporary sample data
#
# We'll replace this with your actual screener DataFrames
# once the basic page is running.
# ---------------------------------------------------------

stock_data = pd.DataFrame({
    "Ticker": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN"],
    "Score": [92, 90, 88, 84, 82],
    "Price": [250.00, 520.00, 195.00, 310.00, 225.00],
    "Upside %": [12.4, 10.8, 8.7, 15.2, 11.6],
    "RSI": [55.2, 58.1, 62.3, 49.8, 53.7]
})


dividend_data = pd.DataFrame({
    "Ticker": ["JNJ", "KO", "PG", "PEP", "XOM"],
    "Score": [91, 89, 87, 85, 83],
    "Dividend Yield": [0.028, 0.029, 0.024, 0.036, 0.032],
    "Payout Ratio": [0.48, 0.62, 0.58, 0.71, 0.45]
})


etf_data = pd.DataFrame({
    "Ticker": ["SPY", "QQQ", "SCHD", "VTI", "VOO"],
    "Score": [94, 92, 90, 88, 86],
    "Expense Ratio": [0.0009, 0.0020, 0.0006, 0.0003, 0.0003]
})


# ---------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------

st.subheader("Market Dashboard")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Top Stock",
        stock_data.iloc[0]["Ticker"],
        f'Score {stock_data.iloc[0]["Score"]}'
    )

with col2:
    st.metric(
        "Top Dividend Stock",
        dividend_data.iloc[0]["Ticker"],
        f'Score {dividend_data.iloc[0]["Score"]}'
    )

with col3:
    st.metric(
        "Top ETF",
        etf_data.iloc[0]["Ticker"],
        f'Score {etf_data.iloc[0]["Score"]}'
    )


st.divider()


# ---------------------------------------------------------
# Tabs
# ---------------------------------------------------------

tab1, tab2, tab3 = st.tabs([
    "🏆 Top Stocks",
    "💰 Dividend Stocks",
    "📊 ETFs"
])


# ---------------------------------------------------------
# Stocks
# ---------------------------------------------------------

with tab1:

    st.subheader("Top Stocks")

    st.dataframe(
        stock_data,
        width="stretch",
        hide_index=True
    )


# ---------------------------------------------------------
# Dividend stocks
# ---------------------------------------------------------

with tab2:

    st.subheader("Top Dividend Stocks")

    display_dividends = dividend_data.copy()

    st.dataframe(
        display_dividends,
        width="stretch",
        hide_index=True,
        column_config={
            "Dividend Yield": st.column_config.NumberColumn(
                "Dividend Yield",
                format="percent"
            ),
            "Payout Ratio": st.column_config.NumberColumn(
                "Payout Ratio",
                format="percent"
            )
        }
    )


# ---------------------------------------------------------
# ETFs
# ---------------------------------------------------------

with tab3:

    st.subheader("Top ETFs")

    st.dataframe(
        etf_data,
        width="stretch",
        hide_index=True,
        column_config={
            "Expense Ratio": st.column_config.NumberColumn(
                "Expense Ratio",
                format="percent"
            )
        }
    )


st.divider()

st.caption(
    "Stock Analysis Dashboard • For informational purposes only"
)

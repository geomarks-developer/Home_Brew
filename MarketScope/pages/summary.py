from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from screener_engine import (
    WORKBOOK_NAME,
    dividend_rows,
    etf_rows,
    read_tickers,
    stock_rows,
)

BASE_DIR = Path(__file__).resolve().parent.parent
if not (BASE_DIR / WORKBOOK_NAME).exists():
    BASE_DIR = Path(__file__).resolve().parent

WORKBOOK_PATH = BASE_DIR / WORKBOOK_NAME
CACHE_FILE = BASE_DIR / "screener_cache.pkl"
TOP_COUNT = 5


def safe_number(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def percent_text(value, decimals=1, signed=False):
    value = safe_number(value)
    if value is None:
        return "N/A"
    sign = "+" if signed else ""
    return f"{value:{sign}.{decimals}%}"


def money_text(value):
    value = safe_number(value)
    return f"${value:,.2f}" if value is not None else "N/A"


def load_cache():
    if not CACHE_FILE.exists():
        return {}, {}, {}
    with open(CACHE_FILE, "rb") as file:
        data = pickle.load(file)
    return (
        data.get("histories", {}),
        data.get("cache", {}),
        data.get("fund_cache", {}),
    )


def top_results(rows, secondary=None):
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame

    sort_columns = ["Passes Screen", "Score"]
    ascending = [False, False]
    if secondary and secondary in frame.columns:
        sort_columns.append(secondary)
        ascending.append(False)
    sort_columns.append("Ticker")
    ascending.append(True)

    return (
        frame.sort_values(
            sort_columns,
            ascending=ascending,
            na_position="last",
        )
        .head(TOP_COUNT)
        .reset_index(drop=True)
    )


def normalized_performance(top_frame, histories):
    if top_frame.empty:
        return pd.DataFrame()

    series_list = []
    for ticker in top_frame["Ticker"].dropna().astype(str):
        ticker = ticker.strip().upper()
        history = histories.get(ticker)
        if history is None or history.empty:
            continue

        column = "Adj Close" if "Adj Close" in history.columns else "Close"
        if column not in history.columns:
            continue

        prices = pd.to_numeric(history[column], errors="coerce").dropna()
        if prices.empty:
            continue

        if not isinstance(prices.index, pd.DatetimeIndex):
            prices.index = pd.to_datetime(prices.index, errors="coerce")
        prices = prices[~prices.index.isna()].sort_index()
        if prices.empty:
            continue

        latest = prices.index.max()
        prices = prices[prices.index >= latest - pd.DateOffset(years=1)]
        prices = prices.resample("W-FRI").last().dropna()
        if prices.empty or prices.iloc[0] == 0:
            continue

        performance = prices / prices.iloc[0] - 1
        performance.name = ticker
        series_list.append(performance)

    if not series_list:
        return pd.DataFrame()

    return pd.concat(series_list, axis=1).sort_index().ffill()


def performance_chart(frame, title):
    if frame.empty:
        return None

    fig = go.Figure()
    for ticker in frame.columns:
        values = pd.to_numeric(frame[ticker], errors="coerce").dropna()
        if values.empty:
            continue
        fig.add_trace(
            go.Scatter(
                x=values.index,
                y=values,
                mode="lines",
                name=str(ticker),
                line=dict(width=2),
                hovertemplate=(
                    "<b>%{x|%b %d, %Y}</b><br>"
                    "%{y:+.1%}<extra>%{fullData.name}</extra>"
                ),
            )
        )

    fig.add_hline(y=0, line_dash="dash", line_color="#808080", line_width=1)
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left"),
        height=390,
        margin=dict(l=15, r=15, t=55, b=15),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="Performance", tickformat="+.0%", showgrid=True),
    )
    return fig


def show_top_table(frame, kind):
    if frame.empty:
        st.info("No results available.")
        return

    table = frame.copy()
    table.insert(0, "Rank", range(1, len(table) + 1))

    if kind == "stocks":
        columns = ["Rank", "Ticker", "Name", "Price", "Score", "Upside %"]
        config = {
            "Rank": st.column_config.NumberColumn("#", format="%d", width=45),
            "Ticker": st.column_config.TextColumn("Ticker", width=75),
            "Name": st.column_config.TextColumn("Company", width=180),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
            "Upside %": st.column_config.NumberColumn("Upside", format="%.1f%%"),
        }
        table["Upside %"] = pd.to_numeric(table["Upside %"], errors="coerce") * 100
    elif kind == "dividends":
        columns = ["Rank", "Ticker", "Name", "Price", "Score", "Dividend Yield"]
        config = {
            "Rank": st.column_config.NumberColumn("#", format="%d", width=45),
            "Ticker": st.column_config.TextColumn("Ticker", width=75),
            "Name": st.column_config.TextColumn("Company", width=180),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
            "Dividend Yield": st.column_config.NumberColumn("Yield", format="%.2f%%"),
        }
        table["Dividend Yield"] = pd.to_numeric(
            table["Dividend Yield"], errors="coerce"
        ) * 100
    else:
        columns = ["Rank", "Ticker", "Name", "Price", "Score", "Expense Ratio"]
        config = {
            "Rank": st.column_config.NumberColumn("#", format="%d", width=45),
            "Ticker": st.column_config.TextColumn("Ticker", width=75),
            "Name": st.column_config.TextColumn("Fund", width=180),
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "Score": st.column_config.NumberColumn("Score", format="%d"),
            "Expense Ratio": st.column_config.NumberColumn("Expense", format="%.2f%%"),
        }
        table["Expense Ratio"] = pd.to_numeric(
            table["Expense Ratio"], errors="coerce"
        ) * 100

    columns = [column for column in columns if column in table.columns]
    st.dataframe(
        table[columns],
        width="stretch",
        hide_index=True,
        height=250,
        column_config=config,
    )


shared_data = st.session_state.get("market_data")
if shared_data is None:
    st.error("Shared MarketScope data is not loaded. Restart the app to initialize market data.")
    st.stop()

lists = shared_data["ticker_lists"]
histories = shared_data["histories"]
stock_data = shared_data["stock_rows"]
dividend_data = shared_data["dividend_rows"]
etf_data = shared_data["etf_rows"]

stocks = shared_data["stock_df"].copy()
dividends = shared_data["dividend_df"].copy()
etfs = shared_data["etf_df"].copy()

top_stocks = top_results(stock_data, "Upside %")
top_dividends = top_results(dividend_data, "Dividend Yield")
top_etfs = top_results(etf_data)

st.title("🏠 MarketScope Summary")
st.caption("High-level view of stock, dividend, and ETF screening results")

stock_passes = int(stocks.get("Passes Screen", pd.Series(dtype=bool)).fillna(False).sum())
dividend_passes = int(dividends.get("Passes Screen", pd.Series(dtype=bool)).fillna(False).sum())
etf_passes = int(etfs.get("Passes Screen", pd.Series(dtype=bool)).fillna(False).sum())

m1, m2, m3, m4 = st.columns(4)
m1.metric("Securities Analyzed", f"{len(stocks) + len(dividends) + len(etfs):,}")
m2.metric("Stocks Passing", f"{stock_passes:,}", f"of {len(stocks):,}")
m3.metric("Dividend Stocks Passing", f"{dividend_passes:,}", f"of {len(dividends):,}")
m4.metric("ETFs Passing", f"{etf_passes:,}", f"of {len(etfs):,}")

st.divider()
st.subheader("Top 5 Screening Results")

stock_tab, dividend_tab, etf_tab = st.tabs(
    ["📈 Top Stocks", "💵 Top Dividend Stocks", "📊 Top ETFs"]
)

with stock_tab:
    left, right = st.columns([1, 1.65])
    with left:
        show_top_table(top_stocks, "stocks")
    with right:
        fig = performance_chart(
            normalized_performance(top_stocks, histories),
            "Top Stocks: 1-Year Performance",
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="summary_stock_chart")
        else:
            st.info("No stock performance history is available.")

with dividend_tab:
    left, right = st.columns([1, 1.65])
    with left:
        show_top_table(top_dividends, "dividends")
    with right:
        fig = performance_chart(
            normalized_performance(top_dividends, histories),
            "Top Dividend Stocks: 1-Year Performance",
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="summary_dividend_chart")
        else:
            st.info("No dividend-stock performance history is available.")

with etf_tab:
    left, right = st.columns([1, 1.65])
    with left:
        show_top_table(top_etfs, "etfs")
    with right:
        fig = performance_chart(
            normalized_performance(top_etfs, histories),
            "Top ETFs: 1-Year Performance",
        )
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="summary_etf_chart")
        else:
            st.info("No ETF performance history is available.")

st.divider()
st.subheader("Screening Snapshot")

s1, s2, s3 = st.columns(3)
with s1:
    with st.container(border=True):
        st.markdown("### 📈 Stocks")
        avg_score = pd.to_numeric(stocks.get("Score %"), errors="coerce").mean()
        avg_change = pd.to_numeric(stocks.get("1 Month Change %"), errors="coerce").mean()
        st.metric("Average Score", percent_text(avg_score))
        st.metric("Average 1-Month Change", percent_text(avg_change, signed=True))
        st.metric("Pass Rate", percent_text(stock_passes / len(stocks) if len(stocks) else None))

with s2:
    with st.container(border=True):
        st.markdown("### 💵 Dividends")
        avg_yield = pd.to_numeric(dividends.get("Dividend Yield"), errors="coerce").mean()
        avg_payout = pd.to_numeric(dividends.get("Payout Ratio"), errors="coerce").mean()
        st.metric("Average Yield", percent_text(avg_yield, 2))
        st.metric("Average Payout Ratio", percent_text(avg_payout))
        st.metric("Pass Rate", percent_text(dividend_passes / len(dividends) if len(dividends) else None))

with s3:
    with st.container(border=True):
        st.markdown("### 📊 ETFs")
        avg_expense = pd.to_numeric(etfs.get("Expense Ratio"), errors="coerce").mean()
        avg_return = pd.to_numeric(etfs.get("1 Month Change %"), errors="coerce").mean()
        st.metric("Average Expense Ratio", percent_text(avg_expense, 2))
        st.metric("Average 1-Month Change", percent_text(avg_return, signed=True))
        st.metric("Pass Rate", percent_text(etf_passes / len(etfs) if len(etfs) else None))

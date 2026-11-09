from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from screener_engine import (
    WORKBOOK_NAME,
    download_history,
    etf_rows,
    read_tickers,
)


BASE_DIR = Path(__file__).resolve().parent.parent
if not (BASE_DIR / WORKBOOK_NAME).exists():
    BASE_DIR = Path(__file__).resolve().parent

WORKBOOK_PATH = BASE_DIR / WORKBOOK_NAME
CACHE_FILE = BASE_DIR / "screener_cache.pkl"


def safe_number(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def metric_value(value, kind="number", decimals=1):
    value = safe_number(value)
    if value is None:
        return "N/A"
    if kind == "percent":
        return f"{value * 100:.{decimals}f}%"
    if kind == "currency":
        return f"${value:,.2f}"
    if kind == "large_currency":
        if abs(value) >= 1_000_000_000:
            return f"${value / 1_000_000_000:,.2f}B"
        if abs(value) >= 1_000_000:
            return f"${value / 1_000_000:,.2f}M"
        return f"${value:,.0f}"
    return f"{value:,.{decimals}f}"


def test_result(value):
    if value is True or value == True:
        return "✅ PASS"
    if value is False or value == False:
        return "❌ FAIL"
    return "➖ N/A"


def prepare_display_percentages(df):
    result = df.copy()
    columns = [
        "Daily Change %",
        "1 Month Change %",
        "% From 52W High",
        "Expense Ratio",
        "Yield",
        "3Y Average Return",
        "5Y Average Return",
        "Score %",
    ]
    for column in columns:
        if column in result.columns:
            result[column] = pd.to_numeric(result[column], errors="coerce") * 100
    return result


def build_etf_dataframe(rows):
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    return frame.sort_values(
        ["Passes Screen", "Score", "Ticker"],
        ascending=[False, False, True],
        na_position="last",
    ).reset_index(drop=True)


def build_etf_chart(ticker, history):
    if history is None or history.empty:
        return None

    chart_data = history.copy()
    price_column = "Adj Close" if "Adj Close" in chart_data.columns else "Close"
    if price_column not in chart_data.columns:
        return None

    chart_data[price_column] = pd.to_numeric(chart_data[price_column], errors="coerce")
    chart_data = chart_data.dropna(subset=[price_column])
    if chart_data.empty:
        return None

    if not isinstance(chart_data.index, pd.DatetimeIndex):
        chart_data.index = pd.to_datetime(chart_data.index, errors="coerce")
    chart_data = chart_data[~chart_data.index.isna()].sort_index()
    if chart_data.empty:
        return None

    chart_data["SMA 50"] = chart_data[price_column].rolling(50).mean()
    chart_data["SMA 200"] = chart_data[price_column].rolling(200).mean()
    latest_date = chart_data.index.max()
    chart_data = chart_data[
        chart_data.index >= latest_date - pd.DateOffset(years=1)
    ].copy()
    if chart_data.empty:
        return None

    fig = go.Figure()
    for column, label, color, width in [
        (price_column, "Price", "#1f77b4", 2.5),
        ("SMA 50", "SMA 50", "#ff9800", 2),
        ("SMA 200", "SMA 200", "#d62728", 2),
    ]:
        fig.add_trace(
            go.Scatter(
                x=chart_data.index,
                y=chart_data[column],
                mode="lines",
                name=label,
                line=dict(color=color, width=width),
                hovertemplate=(
                    "<b>%{x|%b %d, %Y}</b><br>"
                    f"{label}: $%{{y:,.2f}}<extra></extra>"
                ),
            )
        )

    fig.update_layout(
        title=dict(text=f"{ticker} - 1 Year Price History", x=0.01, xanchor="left"),
        height=520,
        margin=dict(l=20, r=20, t=60, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1
        ),
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(title="Price", tickprefix="$", tickformat=",.2f", showgrid=True),
    )
    return fig


@st.cache_data(show_spinner=False)
def load_ticker_lists(workbook_path_string):
    return read_tickers(Path(workbook_path_string))


@st.cache_data(show_spinner=False)
def load_pickle_cache(cache_file_string, modified_time):
    cache_path = Path(cache_file_string)
    if not cache_path.exists():
        return {}, {}, {}
    with open(cache_path, "rb") as file:
        data = pickle.load(file)
    return (
        data.get("histories", {}),
        data.get("cache", {}),
        data.get("fund_cache", {}),
    )


def save_pickle_cache(histories, info_cache, fund_cache):
    with open(CACHE_FILE, "wb") as file:
        pickle.dump(
            {
                "histories": histories,
                "cache": info_cache,
                "fund_cache": fund_cache,
            },
            file,
        )


shared_data = st.session_state.get("market_data")
if shared_data is None:
    st.error("Shared MarketScope data is not loaded. Return to Summary or restart the app.")
    st.stop()

etf_tickers = shared_data["ticker_lists"].get("etfs", [])
histories = shared_data["histories"]
info_cache = shared_data["info_cache"]
fund_cache = shared_data["fund_cache"]
rows = shared_data["etf_rows"]

etf_df = build_etf_dataframe(rows)
if etf_df.empty:
    st.warning("The ETF screener did not return any results.")
    st.stop()

st.title("📊 ETF Screener")
st.caption("Expense ratio, assets under management, performance, and trend analysis")

total = len(etf_df)
passing = int(etf_df["Passes Screen"].fillna(False).sum())
average_expense = pd.to_numeric(etf_df.get("Expense Ratio"), errors="coerce").mean()
average_assets = pd.to_numeric(etf_df.get("Total Assets"), errors="coerce").mean()

m1, m2, m3, m4 = st.columns(4)
m1.metric("ETFs Analyzed", f"{total:,}")
m2.metric("Passing Screen", f"{passing:,}")
m3.metric(
    "Average Expense Ratio",
    f"{average_expense:.2%}" if pd.notna(average_expense) else "N/A",
)
m4.metric(
    "Average AUM",
    metric_value(average_assets, "large_currency") if pd.notna(average_assets) else "N/A",
)

st.divider()
st.subheader("Filters")
f1, f2, f3, f4, f5 = st.columns([1.1, 1.4, 1, 1.1, 1.5])
screen_filter = f1.selectbox("Screen Result", ["All", "Passing Only", "Failing Only"])
categories = sorted(
    str(value)
    for value in etf_df.get("Category", pd.Series(dtype=str)).dropna().unique()
)
selected_category = f2.selectbox("Category", ["All"] + categories)
maximum_score = int(pd.to_numeric(etf_df["Score"], errors="coerce").max())
minimum_score = f3.number_input(
    "Minimum Score", min_value=0, max_value=maximum_score, value=0, step=1
)
maximum_expense_percent = f4.number_input(
    "Max Expense %",
    min_value=0.0,
    max_value=5.0,
    value=5.0,
    step=0.05,
)
search_text = f5.text_input("Ticker or Fund", placeholder="VOO, SPY, Vanguard...")

filtered_df = etf_df.copy()
if screen_filter == "Passing Only":
    filtered_df = filtered_df[filtered_df["Passes Screen"] == True]
elif screen_filter == "Failing Only":
    filtered_df = filtered_df[filtered_df["Passes Screen"] == False]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]
filtered_df = filtered_df[
    pd.to_numeric(filtered_df["Score"], errors="coerce") >= minimum_score
]
filtered_df = filtered_df[
    pd.to_numeric(filtered_df["Expense Ratio"], errors="coerce")
    <= maximum_expense_percent / 100
]
if search_text.strip():
    query = search_text.strip()
    ticker_match = filtered_df["Ticker"].astype(str).str.contains(query, case=False, na=False)
    name_match = filtered_df["Name"].astype(str).str.contains(query, case=False, na=False)
    filtered_df = filtered_df[ticker_match | name_match]
filtered_df = filtered_df.reset_index(drop=True)

st.subheader("ETF Screening Results")
st.caption(f"Displaying {len(filtered_df):,} of {len(etf_df):,} ETFs")
if filtered_df.empty:
    st.info("No ETFs match the current filters.")
    st.stop()

preferred_columns = [
    "Ticker", "Name", "Category", "Price", "Daily Change %", "1 Month Change %",
    "Expense Ratio", "Total Assets", "Yield", "3Y Average Return", "5Y Average Return",
    "Score", "Max Score", "Passes Screen", "RSI", "MACD", "MACD Signal",
    "SMA 50", "SMA 200", "Bullish Alignment", "Failed Tests",
]
display_columns = [column for column in preferred_columns if column in filtered_df]
display_df = prepare_display_percentages(
    filtered_df[display_columns].copy()
).reset_index(drop=True)

selection = st.dataframe(
    display_df,
    width="stretch",
    hide_index=True,
    height=650,
    key="etf_screener_table",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Ticker": st.column_config.TextColumn("Ticker", width=90, pinned=True),
        "Name": st.column_config.TextColumn("Fund", width=220, pinned=True),
        "Category": st.column_config.TextColumn("Category", width=180),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Daily Change %": st.column_config.NumberColumn("Daily %", format="%.2f%%"),
        "1 Month Change %": st.column_config.NumberColumn("1 Month %", format="%.2f%%"),
        "Expense Ratio": st.column_config.NumberColumn("Expense Ratio", format="%.2f%%"),
        "Total Assets": st.column_config.NumberColumn("AUM", format="$%.0f"),
        "Yield": st.column_config.NumberColumn("Yield", format="%.2f%%"),
        "3Y Average Return": st.column_config.NumberColumn("3Y Avg Return", format="%.1f%%"),
        "5Y Average Return": st.column_config.NumberColumn("5Y Avg Return", format="%.1f%%"),
        "Score": st.column_config.NumberColumn("Score", format="%d"),
        "Max Score": st.column_config.NumberColumn("Max", format="%d"),
        "Passes Screen": st.column_config.CheckboxColumn("Pass"),
        "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
        "MACD": st.column_config.NumberColumn("MACD", format="%.2f"),
        "MACD Signal": st.column_config.NumberColumn("Signal", format="%.2f"),
        "SMA 50": st.column_config.NumberColumn("SMA 50", format="$%.2f"),
        "SMA 200": st.column_config.NumberColumn("SMA 200", format="$%.2f"),
        "Bullish Alignment": st.column_config.CheckboxColumn("Bullish"),
        "Failed Tests": st.column_config.TextColumn("Failed Tests", width=350),
    },
)

selected_positions = list(selection.selection.rows)
selected_position = selected_positions[0] if selected_positions else 0
etf = filtered_df.iloc[selected_position]
selected_ticker = str(etf.get("Ticker", "")).strip().upper()
fund_name = etf.get("Name", "")

st.divider()
st.subheader("ETF Details")
st.markdown(f"## {selected_ticker} {fund_name or ''}")
category = etf.get("Category")
if category and not pd.isna(category):
    st.caption(str(category))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Price", metric_value(etf.get("Price"), "currency"))
c2.metric("Expense Ratio", metric_value(etf.get("Expense Ratio"), "percent", 2))
c3.metric("AUM", metric_value(etf.get("Total Assets"), "large_currency"))
c4.metric("Screen", "PASS" if bool(etf.get("Passes Screen", False)) else "FAIL")

failed_tests = etf.get("Failed Tests")
if bool(etf.get("Passes Screen", False)):
    st.success("This ETF currently passes the screener.")
elif failed_tests and not pd.isna(failed_tests):
    st.warning(f"Failed tests: {failed_tests}")
else:
    st.warning("This ETF currently does not pass the screener.")

chart = build_etf_chart(selected_ticker, histories.get(selected_ticker))
if chart is not None:
    st.plotly_chart(
        chart,
        width="stretch",
        key=f"etf_chart_{selected_ticker}",
        config={"displayModeBar": True, "displaylogo": False, "scrollZoom": True},
    )
else:
    st.info(f"No price history is available for {selected_ticker}.")

st.subheader("ETF Analysis")
cost_col, fund_col, returns_col, trend_col = st.columns(4)

with cost_col:
    with st.container(border=True):
        st.markdown("### 💲 Cost")
        st.metric("Expense Ratio", metric_value(etf.get("Expense Ratio"), "percent", 2))
        st.caption(test_result(etf.get("Expense Test")))
        st.metric("Price", metric_value(etf.get("Price"), "currency"))
        st.metric("Yield", metric_value(etf.get("Yield"), "percent", 2))

with fund_col:
    with st.container(border=True):
        st.markdown("### 🏦 Fund Size")
        st.metric("Assets Under Management", metric_value(etf.get("Total Assets"), "large_currency"))
        st.caption(test_result(etf.get("AUM Test")))
        st.metric("Category", str(etf.get("Category") or "N/A"))
        st.metric("Screener Score", f"{int(etf.get('Score', 0))} / {int(etf.get('Max Score', 0))}")

with returns_col:
    with st.container(border=True):
        st.markdown("### 📈 Returns")
        st.metric("Daily Change", metric_value(etf.get("Daily Change %"), "percent", 2))
        st.metric("1-Month Change", metric_value(etf.get("1 Month Change %"), "percent", 2))
        st.metric("3-Year Avg Return", metric_value(etf.get("3Y Average Return"), "percent", 1))
        st.metric("5-Year Avg Return", metric_value(etf.get("5Y Average Return"), "percent", 1))

with trend_col:
    with st.container(border=True):
        st.markdown("### 🧭 Trend")
        st.metric("50-Day SMA", metric_value(etf.get("SMA 50"), "currency"))
        st.metric("200-Day SMA", metric_value(etf.get("SMA 200"), "currency"))
        bullish = bool(etf.get("Bullish Alignment", False))
        st.metric("Bullish Alignment", "BULLISH" if bullish else "BEARISH")
        st.caption(test_result(etf.get("Trend Test")))

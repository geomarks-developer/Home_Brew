from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from screener_engine import (
    WORKBOOK_NAME,
    dividend_rows,
    download_history,
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


def metric_value(value, format_type="number", decimals=1):
    value = safe_number(value)
    if value is None:
        return "N/A"
    if format_type == "percent":
        return f"{value * 100:.{decimals}f}%"
    if format_type == "currency":
        return f"${value:,.2f}"
    if format_type == "large_currency":
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
    percentage_columns = [
        "Daily Change %",
        "1 Month Change %",
        "% From 52W High",
        "Dividend Yield",
        "5Y Avg Dividend Yield",
        "Payout Ratio",
        "Score %",
    ]
    for column in percentage_columns:
        if column in result.columns:
            result[column] = pd.to_numeric(
                result[column], errors="coerce"
            ) * 100
    return result


def build_dividend_dataframe(rows):
    if not rows:
        return pd.DataFrame()
    frame = pd.DataFrame(rows)
    return frame.sort_values(
        ["Passes Screen", "Score", "Dividend Yield", "Ticker"],
        ascending=[False, False, False, True],
        na_position="last",
    ).reset_index(drop=True)


def build_dividend_chart(ticker, history):
    if history is None or history.empty:
        return None

    chart_data = history.copy()
    price_column = "Adj Close" if "Adj Close" in chart_data.columns else "Close"
    if price_column not in chart_data.columns:
        return None

    chart_data[price_column] = pd.to_numeric(
        chart_data[price_column], errors="coerce"
    )
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

    figure = go.Figure()
    traces = [
        (price_column, "Price", "#1f77b4", 2.5),
        ("SMA 50", "SMA 50", "#ff9800", 2),
        ("SMA 200", "SMA 200", "#d62728", 2),
    ]
    for column, label, color, width in traces:
        figure.add_trace(
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

    figure.update_layout(
        title=dict(
            text=f"{ticker} - 1 Year Price History",
            x=0.01,
            xanchor="left",
        ),
        height=520,
        margin=dict(l=20, r=20, t=60, b=20),
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),
        xaxis=dict(title=None, showgrid=False),
        yaxis=dict(
            title="Price",
            tickprefix="$",
            tickformat=",.2f",
            showgrid=True,
        ),
    )
    return figure


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

dividend_tickers = shared_data["ticker_lists"].get("dividends", [])
histories = shared_data["histories"]
info_cache = shared_data["info_cache"]
fund_cache = shared_data["fund_cache"]
rows = shared_data["dividend_rows"]

dividend_df = build_dividend_dataframe(rows)
if dividend_df.empty:
    st.warning("The dividend screener did not return any results.")
    st.stop()

st.title("💵 Dividend Screener")
st.caption("Dividend income, payout sustainability, cash flow, trend, and momentum")

total = len(dividend_df)
passing = int(dividend_df["Passes Screen"].fillna(False).sum())
average_yield = pd.to_numeric(
    dividend_df.get("Dividend Yield"), errors="coerce"
).mean()
average_score = pd.to_numeric(
    dividend_df.get("Score %"), errors="coerce"
).mean()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Stocks Analyzed", f"{total:,}")
m2.metric("Passing Screen", f"{passing:,}")
m3.metric(
    "Average Dividend Yield",
    f"{average_yield:.2%}" if pd.notna(average_yield) else "N/A",
)
m4.metric(
    "Average Score",
    f"{average_score:.1%}" if pd.notna(average_score) else "N/A",
)

st.divider()
st.subheader("Filters")
f1, f2, f3, f4, f5 = st.columns([1.1, 1.3, 1, 1, 1.5])

screen_filter = f1.selectbox(
    "Screen Result",
    ["All", "Passing Only", "Failing Only"],
)
sectors = sorted(
    str(value)
    for value in dividend_df.get("Sector", pd.Series(dtype=str)).dropna().unique()
)
selected_sector = f2.selectbox("Sector", ["All"] + sectors)
maximum_score = int(
    pd.to_numeric(dividend_df["Score"], errors="coerce").max()
)
minimum_score = f3.number_input(
    "Minimum Score",
    min_value=0,
    max_value=maximum_score,
    value=0,
    step=1,
)
minimum_yield_percent = f4.number_input(
    "Minimum Yield %",
    min_value=0.0,
    max_value=25.0,
    value=0.0,
    step=0.25,
)
search_text = f5.text_input(
    "Ticker or Company",
    placeholder="KO, Coca-Cola, JNJ...",
)

filtered_df = dividend_df.copy()
if screen_filter == "Passing Only":
    filtered_df = filtered_df[filtered_df["Passes Screen"] == True]
elif screen_filter == "Failing Only":
    filtered_df = filtered_df[filtered_df["Passes Screen"] == False]
if selected_sector != "All":
    filtered_df = filtered_df[filtered_df["Sector"] == selected_sector]
filtered_df = filtered_df[
    pd.to_numeric(filtered_df["Score"], errors="coerce") >= minimum_score
]
filtered_df = filtered_df[
    pd.to_numeric(filtered_df["Dividend Yield"], errors="coerce")
    >= minimum_yield_percent / 100
]
if search_text.strip():
    query = search_text.strip()
    ticker_match = filtered_df["Ticker"].astype(str).str.contains(
        query, case=False, na=False
    )
    name_match = filtered_df["Name"].astype(str).str.contains(
        query, case=False, na=False
    )
    filtered_df = filtered_df[ticker_match | name_match]
filtered_df = filtered_df.reset_index(drop=True)

st.subheader("Dividend Screening Results")
st.caption(f"Displaying {len(filtered_df):,} of {len(dividend_df):,} stocks")
if filtered_df.empty:
    st.info("No dividend stocks match the current filters.")
    st.stop()

preferred_columns = [
    "Ticker",
    "Name",
    "Sector",
    "Price",
    "Daily Change %",
    "1 Month Change %",
    "Dividend Yield",
    "5Y Avg Dividend Yield",
    "Payout Ratio",
    "Free Cash Flow",
    "Debt To Equity",
    "Score",
    "Max Score",
    "Score %",
    "Passes Screen",
    "RSI",
    "MACD",
    "MACD Signal",
    "SMA 50",
    "SMA 200",
    "Bullish Alignment",
    "Failed Tests",
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
    key="dividend_screener_table",
    on_select="rerun",
    selection_mode="single-row",
    column_config={
        "Ticker": st.column_config.TextColumn(
            "Ticker", width=90, pinned=True
        ),
        "Name": st.column_config.TextColumn(
            "Company", width=220, pinned=True
        ),
        "Sector": st.column_config.TextColumn("Sector", width=170),
        "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
        "Daily Change %": st.column_config.NumberColumn(
            "Daily %", format="%.2f%%"
        ),
        "1 Month Change %": st.column_config.NumberColumn(
            "1 Month %", format="%.2f%%"
        ),
        "Dividend Yield": st.column_config.NumberColumn(
            "Dividend Yield", format="%.2f%%"
        ),
        "5Y Avg Dividend Yield": st.column_config.NumberColumn(
            "5Y Avg Yield", format="%.2f%%"
        ),
        "Payout Ratio": st.column_config.NumberColumn(
            "Payout Ratio", format="%.1f%%"
        ),
        "Free Cash Flow": st.column_config.NumberColumn(
            "Free Cash Flow", format="$%.0f"
        ),
        "Debt To Equity": st.column_config.NumberColumn(
            "Debt/Equity", format="%.1f"
        ),
        "Score": st.column_config.NumberColumn("Score", format="%d"),
        "Max Score": st.column_config.NumberColumn("Max", format="%d"),
        "Score %": st.column_config.ProgressColumn(
            "Score %", min_value=0, max_value=100, format="%.0f%%"
        ),
        "Passes Screen": st.column_config.CheckboxColumn("Pass"),
        "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
        "MACD": st.column_config.NumberColumn("MACD", format="%.2f"),
        "MACD Signal": st.column_config.NumberColumn("Signal", format="%.2f"),
        "SMA 50": st.column_config.NumberColumn("SMA 50", format="$%.2f"),
        "SMA 200": st.column_config.NumberColumn("SMA 200", format="$%.2f"),
        "Bullish Alignment": st.column_config.CheckboxColumn("Bullish"),
        "Failed Tests": st.column_config.TextColumn(
            "Failed Tests", width=350
        ),
    },
)

selected_positions = list(selection.selection.rows)
selected_position = selected_positions[0] if selected_positions else 0
stock = filtered_df.iloc[selected_position]
selected_ticker = str(stock.get("Ticker", "")).strip().upper()
company_name = stock.get("Name", "")

st.divider()
st.subheader("Dividend Stock Details")
st.markdown(f"## {selected_ticker} {company_name or ''}")
sector = stock.get("Sector")
if sector and not pd.isna(sector):
    st.caption(str(sector))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Price", metric_value(stock.get("Price"), "currency"))
c2.metric("Dividend Yield", metric_value(stock.get("Dividend Yield"), "percent", 2))
c3.metric(
    "Payout Ratio", metric_value(stock.get("Payout Ratio"), "percent", 1)
)
c4.metric("Screen", "PASS" if bool(stock.get("Passes Screen", False)) else "FAIL")

failed_tests = stock.get("Failed Tests")
if bool(stock.get("Passes Screen", False)):
    st.success("This stock currently passes the dividend screener.")
elif failed_tests and not pd.isna(failed_tests):
    st.warning(f"Failed tests: {failed_tests}")
else:
    st.warning("This stock currently does not pass the dividend screener.")

chart = build_dividend_chart(selected_ticker, histories.get(selected_ticker))
if chart is not None:
    st.plotly_chart(
        chart,
        width="stretch",
        key=f"dividend_chart_{selected_ticker}",
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "scrollZoom": True,
        },
    )
else:
    st.info(f"No price history is available for {selected_ticker}.")

st.subheader("Dividend Analysis")
income_col, sustainability_col, momentum_col, trend_col = st.columns(4)

with income_col:
    with st.container(border=True):
        st.markdown("### 💵 Income")
        st.metric(
            "Dividend Yield",
            metric_value(stock.get("Dividend Yield"), "percent", 2),
        )
        st.caption(test_result(stock.get("Dividend Yield Test")))
        st.metric(
            "5-Year Average Yield",
            metric_value(stock.get("5Y Avg Dividend Yield"), "percent", 2),
        )
        current_yield = safe_number(stock.get("Dividend Yield"))
        average_five_year_yield = safe_number(stock.get("5Y Avg Dividend Yield"))
        if current_yield is not None and average_five_year_yield is not None:
            spread = current_yield - average_five_year_yield
            st.metric("Yield vs 5Y Average", f"{spread:+.2%}")
        else:
            st.metric("Yield vs 5Y Average", "N/A")

with sustainability_col:
    with st.container(border=True):
        st.markdown("### 🛡️ Sustainability")
        st.metric(
            "Payout Ratio",
            metric_value(stock.get("Payout Ratio"), "percent", 1),
        )
        st.caption(test_result(stock.get("Payout Ratio Test")))
        st.metric(
            "Free Cash Flow",
            metric_value(stock.get("Free Cash Flow"), "large_currency"),
        )
        st.caption(test_result(stock.get("Free Cash Flow Test")))
        st.metric(
            "Debt / Equity",
            metric_value(stock.get("Debt To Equity"), "number", 1),
        )
        st.caption(test_result(stock.get("Debt To Equity Test")))

with momentum_col:
    with st.container(border=True):
        st.markdown("### ⚡ Momentum")
        st.metric("RSI", metric_value(stock.get("RSI"), "number", 1))
        st.caption(test_result(stock.get("RSI Range Test")))
        st.metric("MACD", metric_value(stock.get("MACD"), "number", 2))
        st.metric(
            "MACD Signal",
            metric_value(stock.get("MACD Signal"), "number", 2),
        )
        st.caption(test_result(stock.get("MACD Above Signal Test")))
        momentum_score = safe_number(stock.get("Momentum Score"))
        st.metric(
            "Momentum Score",
            f"{momentum_score:.0f} / 3" if momentum_score is not None else "N/A",
        )

with trend_col:
    with st.container(border=True):
        st.markdown("### 📈 Trend")
        st.metric("50-Day SMA", metric_value(stock.get("SMA 50"), "currency"))
        st.caption(test_result(stock.get("Above SMA 50 Test")))
        st.metric("200-Day SMA", metric_value(stock.get("SMA 200"), "currency"))
        st.caption(test_result(stock.get("Above SMA 200 Test")))
        bullish = bool(stock.get("Bullish Alignment", False))
        st.metric("Bullish Alignment", "BULLISH" if bullish else "BEARISH")
        st.caption(test_result(stock.get("Trend Test")))

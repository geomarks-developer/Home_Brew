from pathlib import Path
import pickle
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

# ---------------------------------------------------------
# Import the existing screener engine
# ---------------------------------------------------------
#
# For the very first version, rename:
#
#     Combo_Analysis v16.py
#
# to:
#
#     screener_engine.py
#
# This lets Streamlit import the existing functions directly.
#
from screener_engine import (
    WORKBOOK_NAME,
    download_history,
    read_tickers,
    stock_rows,
)


# =========================================================
# Streamlit configuration
# =========================================================

st.set_page_config(
    page_title="Stock Screener",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# =========================================================
# Paths
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

WORKBOOK_PATH = BASE_DIR / WORKBOOK_NAME
CACHE_FILE = BASE_DIR / "screener_cache.pkl"


# =========================================================
# Formatting helpers
# =========================================================

def safe_number(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def build_stock_dataframe(rows):
    """
    Convert stock_rows() output into a DataFrame and sort using
    the same general priority as the Excel version.
    """

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    sort_columns = [
        column
        for column in ["Passes Screen", "Score", "Ticker"]
        if column in df.columns
    ]

    if sort_columns:
        ascending_map = {
            "Passes Screen": False,
            "Score": False,
            "Ticker": True,
        }

        df = df.sort_values(
            by=sort_columns,
            ascending=[
                ascending_map[column]
                for column in sort_columns
            ],
            na_position="last",
        )

    return df.reset_index(drop=True)

def prepare_display_percentages(df):
    """
    Convert decimal percentage values to 0-100 values
    for display in Streamlit.

    This does NOT modify the screener calculation data.
    """

    result = df.copy()

    percentage_columns = [
        "Daily Change %",
        "1 Month Change %",
        "% From 52W High",
        "Score %",
        "Return On Equity",
        "Profit Margin",
        "Revenue Growth",
        "Earnings Growth",
        "Upside %",
        "Dividend Yield",
        "5Y Avg Dividend Yield",
        "Payout Ratio",
        "Expense Ratio",
        "Yield",
        "3Y Average Return",
        "5Y Average Return",
    ]

    for column in percentage_columns:
        if column in result.columns:
            result[column] = (
                pd.to_numeric(
                    result[column],
                    errors="coerce"
                ) * 100
            )

    return result
def build_stock_chart(ticker, history):
    """
    Build a 1-year interactive price chart showing:
        - Closing Price
        - 50-day SMA
        - 200-day SMA

    Moving averages are calculated before limiting the
    displayed data to one year so the SMA 200 is available
    throughout as much of the chart as possible.
    """

    if history is None or history.empty:
        return None

    chart_data = history.copy()

    # -----------------------------------------------------
    # Determine price column
    # -----------------------------------------------------

    price_column = (
        "Adj Close"
        if "Adj Close" in chart_data.columns
        else "Close"
    )

    if price_column not in chart_data.columns:
        return None

    chart_data[price_column] = pd.to_numeric(
        chart_data[price_column],
        errors="coerce"
    )

    chart_data = chart_data.dropna(
        subset=[price_column]
    )

    if chart_data.empty:
        return None

    # -----------------------------------------------------
    # Make sure index is datetime
    # -----------------------------------------------------

    if not isinstance(
        chart_data.index,
        pd.DatetimeIndex
    ):
        chart_data.index = pd.to_datetime(
            chart_data.index,
            errors="coerce"
        )

    chart_data = chart_data[
        ~chart_data.index.isna()
    ]

    chart_data = chart_data.sort_index()

    if chart_data.empty:
        return None

    # -----------------------------------------------------
    # Calculate moving averages BEFORE limiting to 1 year
    # -----------------------------------------------------

    chart_data["SMA 50"] = (
        chart_data[price_column]
        .rolling(50)
        .mean()
    )

    chart_data["SMA 200"] = (
        chart_data[price_column]
        .rolling(200)
        .mean()
    )

    # -----------------------------------------------------
    # Limit displayed chart to most recent year
    # -----------------------------------------------------

    latest_date = chart_data.index.max()

    one_year_ago = (
        latest_date
        - pd.DateOffset(years=1)
    )

    chart_data = chart_data[
        chart_data.index >= one_year_ago
    ].copy()

    if chart_data.empty:
        return None

    # -----------------------------------------------------
    # Create Plotly figure
    # -----------------------------------------------------

    fig = go.Figure()

    # Closing Price
    fig.add_trace(
        go.Scatter(
            x=chart_data.index,
            y=chart_data[price_column],
            mode="lines",
            name="Price",
            line=dict(
                width=2.5,
                color="#1f77b4"
            ),
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "Price: $%{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )

    # SMA 50
    fig.add_trace(
        go.Scatter(
            x=chart_data.index,
            y=chart_data["SMA 50"],
            mode="lines",
            name="SMA 50",
            line=dict(
                width=2,
                color="#ff9800"
            ),
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "SMA 50: $%{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )

    # SMA 200
    fig.add_trace(
        go.Scatter(
            x=chart_data.index,
            y=chart_data["SMA 200"],
            mode="lines",
            name="SMA 200",
            line=dict(
                width=2,
                color="#d62728"
            ),
            hovertemplate=(
                "<b>%{x|%b %d, %Y}</b><br>"
                "SMA 200: $%{y:,.2f}"
                "<extra></extra>"
            ),
        )
    )

    # -----------------------------------------------------
    # Layout
    # -----------------------------------------------------

    fig.update_layout(
        title=dict(
            text=f"{ticker} - 1 Year Price History",
            x=0.01,
            xanchor="left",
        ),

        height=520,

        margin=dict(
            l=20,
            r=20,
            t=60,
            b=20,
        ),

        hovermode="x unified",

        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ),

        xaxis=dict(
            title=None,
            showgrid=False,
            rangeslider=dict(
                visible=False
            ),
        ),

        yaxis=dict(
            title="Price",
            tickprefix="$",
            tickformat=",.2f",
            showgrid=True,
        ),
    )

    return fig
# =========================================================
# Data loading
# =========================================================

@st.cache_data(show_spinner=False)
def load_ticker_lists(workbook_path_string):
    """
    Read ticker lists from Combo_Analysis.xlsx.
    """

    return read_tickers(
        Path(workbook_path_string)
    )


@st.cache_data(show_spinner=False)
def load_pickle_cache(
    cache_file_string,
    modified_time,
):
    """
    Load the existing screener pickle cache.

    modified_time is included so Streamlit invalidates its
    cache when the pickle file changes.
    """

    cache_path = Path(cache_file_string)

    if not cache_path.exists():
        return {}, {}, {}

    with open(cache_path, "rb") as file:
        cached_data = pickle.load(file)

    histories = cached_data.get(
        "histories",
        {},
    )

    info_cache = cached_data.get(
        "cache",
        {},
    )

    fund_cache = cached_data.get(
        "fund_cache",
        {},
    )

    return (
        histories,
        info_cache,
        fund_cache,
    )


# =========================================================
# Yahoo refresh
# =========================================================

def refresh_stock_data(tickers):
    """
    Download fresh price history and rebuild stock information.
    """

    histories = download_history(tickers)

    info_cache = {}

    rows = stock_rows(
        tickers,
        histories,
        info_cache,
    )

    return (
        histories,
        info_cache,
        rows,
    )


# =========================================================
# Load application data
# =========================================================

if not WORKBOOK_PATH.exists():

    st.error(
        f"Workbook not found: {WORKBOOK_PATH}"
    )

    st.info(
        "Place Combo_Analysis.xlsx in the same folder as app.py."
    )

    st.stop()


ticker_lists = load_ticker_lists(
    str(WORKBOOK_PATH)
)

stock_tickers = ticker_lists.get(
    "stocks",
    [],
)

if not stock_tickers:

    st.warning(
        "No stock tickers were found in the Stock column "
        "of the Tickers worksheet."
    )

    st.stop()


# =========================================================
# Sidebar
# =========================================================

st.sidebar.title("Stock Screener")

st.sidebar.caption(
    "Market screening and analysis"
)

st.sidebar.divider()

st.sidebar.subheader("Data")

cache_exists = CACHE_FILE.exists()

use_cache = st.sidebar.toggle(
    "Use cached data",
    value=cache_exists,
)

refresh_button = st.sidebar.button(
    "Refresh Market Data",
    type="primary",
    use_container_width=True,
)

st.sidebar.caption(
    f"{len(stock_tickers):,} stock tickers configured"
)


# =========================================================
# Get screener data
# =========================================================

histories = {}
info_cache = {}
stock_data_rows = []


if refresh_button:

    with st.spinner(
        "Downloading market data and running stock screener..."
    ):

        (
            histories,
            info_cache,
            stock_data_rows,
        ) = refresh_stock_data(
            stock_tickers
        )

        # Save data using the same cache structure
        # as Combo_Analysis v16.

        cached_data = {
            "histories": histories,
            "cache": info_cache,
            "fund_cache": {},
        }

        with open(
            CACHE_FILE,
            "wb",
        ) as file:

            pickle.dump(
                cached_data,
                file,
            )

        st.cache_data.clear()

    st.success(
        "Market data refreshed."
    )


elif use_cache and cache_exists:

    modified_time = CACHE_FILE.stat().st_mtime

    (
        histories,
        info_cache,
        fund_cache,
    ) = load_pickle_cache(
        str(CACHE_FILE),
        modified_time,
    )

    with st.spinner(
        "Running stock screener from cached data..."
    ):

        stock_data_rows = stock_rows(
            stock_tickers,
            histories,
            info_cache,
        )


else:

    st.info(
        "Select **Use cached data** or click "
        "**Refresh Market Data** to run the screener."
    )

    st.stop()


# =========================================================
# Build DataFrame
# =========================================================

stock_df = build_stock_dataframe(
    stock_data_rows
)

if stock_df.empty:

    st.warning(
        "The stock screener did not return any results."
    )

    st.stop()


# =========================================================
# Page heading
# =========================================================

st.title("📈 Stock Screener")

st.caption(
    "Fundamental, valuation, trend, and momentum screening"
)


# =========================================================
# Top summary metrics
# =========================================================

total_stocks = len(
    stock_df
)

passing_stocks = int(
    stock_df["Passes Screen"]
    .fillna(False)
    .sum()
)

if "Score %" in stock_df.columns:

    average_score = (
        pd.to_numeric(
            stock_df["Score %"],
            errors="coerce",
        )
        .mean()
    )

else:

    average_score = None


if "Daily Change %" in stock_df.columns:

    average_daily_change = (
        pd.to_numeric(
            stock_df["Daily Change %"],
            errors="coerce",
        )
        .mean()
    )

else:

    average_daily_change = None


metric1, metric2, metric3, metric4 = st.columns(4)


metric1.metric(
    "Stocks Analyzed",
    f"{total_stocks:,}",
)


metric2.metric(
    "Passing Screen",
    f"{passing_stocks:,}",
)


if average_score is not None:

    metric3.metric(
        "Average Score",
        f"{average_score:.1%}",
    )

else:

    metric3.metric(
        "Average Score",
        "N/A",
    )


if average_daily_change is not None:

    metric4.metric(
        "Average Daily Change",
        f"{average_daily_change:+.2%}",
    )

else:

    metric4.metric(
        "Average Daily Change",
        "N/A",
    )


st.divider()


# =========================================================
# Filters
# =========================================================

st.subheader("Filters")

filter1, filter2, filter3, filter4 = st.columns(
    [1.1, 1.4, 1.1, 1.5]
)


# ---------------------------------------------------------
# Pass / Fail
# ---------------------------------------------------------

screen_filter = filter1.selectbox(
    "Screen Result",
    [
        "All",
        "Passing Only",
        "Failing Only",
    ],
)


# ---------------------------------------------------------
# Sector
# ---------------------------------------------------------

if "Sector" in stock_df.columns:

    sectors = sorted(
        [
            str(value)
            for value
            in stock_df["Sector"]
            .dropna()
            .unique()
        ]
    )

else:

    sectors = []


selected_sector = filter2.selectbox(
    "Sector",
    ["All"] + sectors,
)


# ---------------------------------------------------------
# Score
# ---------------------------------------------------------

if "Score" in stock_df.columns:

    maximum_score = int(
        pd.to_numeric(
            stock_df["Score"],
            errors="coerce",
        )
        .max()
    )

else:

    maximum_score = 14


minimum_score = filter3.number_input(
    "Minimum Score",
    min_value=0,
    max_value=maximum_score,
    value=0,
    step=1,
)


# ---------------------------------------------------------
# Ticker / company search
# ---------------------------------------------------------

search_text = filter4.text_input(
    "Ticker or Company",
    placeholder="AAPL, Microsoft, Nvidia...",
)


# =========================================================
# Apply filters
# =========================================================

filtered_df = stock_df.copy()


if screen_filter == "Passing Only":

    filtered_df = filtered_df[
        filtered_df["Passes Screen"] == True
    ]


elif screen_filter == "Failing Only":

    filtered_df = filtered_df[
        filtered_df["Passes Screen"] == False
    ]


if (
    selected_sector != "All"
    and "Sector" in filtered_df.columns
):

    filtered_df = filtered_df[
        filtered_df["Sector"]
        == selected_sector
    ]


if "Score" in filtered_df.columns:

    filtered_df = filtered_df[
        pd.to_numeric(
            filtered_df["Score"],
            errors="coerce",
        )
        >= minimum_score
    ]


if search_text:

    search_text = search_text.strip()

    ticker_match = (
        filtered_df["Ticker"]
        .astype(str)
        .str.contains(
            search_text,
            case=False,
            na=False,
        )
    )

    if "Name" in filtered_df.columns:

        company_match = (
            filtered_df["Name"]
            .astype(str)
            .str.contains(
                search_text,
                case=False,
                na=False,
            )
        )

        filtered_df = filtered_df[
            ticker_match | company_match
        ]

    else:

        filtered_df = filtered_df[
            ticker_match
        ]


# =========================================================
# Results heading
# =========================================================

st.subheader("Stock Screening Results")

st.caption(
    f"Displaying {len(filtered_df):,} "
    f"of {len(stock_df):,} stocks"
)


# =========================================================
# Columns to display
# =========================================================

preferred_columns = [
    "Ticker",
    "Name",
    "Sector",
    "Price",
    "Daily Change %",
    "1 Month Change %",
    "Score",
    "Max Score",
    "Score %",
    "Passes Screen",
    "PEG",
    "Forward PE",
    "Return On Equity",
    "Profit Margin",
    "Revenue Growth",
    "Earnings Growth",
    "Debt To Equity",
    "Upside %",
    "RSI",
    "MACD",
    "MACD Signal",
    "SMA 50",
    "SMA 200",
    "Bullish Alignment",
    "Failed Tests",
]


display_columns = [
    column
    for column in preferred_columns
    if column in filtered_df.columns
]


display_df = filtered_df[
    display_columns
].copy()

display_df = prepare_display_percentages(
    display_df
)


# =========================================================
# Stock table
# =========================================================

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    height=650,

    column_config={

        "Ticker": st.column_config.TextColumn(
            "Ticker",
            width=90,
            pinned=True,
        ),

        "Name": st.column_config.TextColumn(
            "Company",
            width="medium",
        ),

        "Sector": st.column_config.TextColumn(
            "Sector",
            width="medium",
        ),

        "Price": st.column_config.NumberColumn(
            "Price",
            format="$%.2f",
        ),

        "Daily Change %":
            st.column_config.NumberColumn(
                "Daily %",
                format="%.2f%%",
            ),

        "1 Month Change %":
            st.column_config.NumberColumn(
                "1 Month %",
                format="%.2f%%",
            ),

        "Score":
            st.column_config.NumberColumn(
                "Score",
                format="%d",
            ),

        "Max Score":
            st.column_config.NumberColumn(
                "Max",
                format="%d",
            ),

        "Score %":
            st.column_config.ProgressColumn(
                "Score %",
                min_value=0,
                max_value=100,
                format="%.0f%%",
            ),

        "Passes Screen":
            st.column_config.CheckboxColumn(
                "Pass",
            ),

        "PEG":
            st.column_config.NumberColumn(
                "PEG",
                format="%.2f",
            ),

        "Forward PE":
            st.column_config.NumberColumn(
                "Forward P/E",
                format="%.2f",
            ),

        "Return On Equity":
            st.column_config.NumberColumn(
                "ROE",
                format="%.1f%%",
            ),

        "Profit Margin":
            st.column_config.NumberColumn(
                "Margin",
                format="%.1f%%",
            ),

        "Revenue Growth":
            st.column_config.NumberColumn(
                "Revenue Growth",
                format="%.1f%%",
            ),

        "Earnings Growth":
            st.column_config.NumberColumn(
                "Earnings Growth",
                format="%.1f%%",
            ),

        "Debt To Equity":
            st.column_config.NumberColumn(
                "Debt/Equity",
                format="%.1f",
            ),

        "Upside %":
            st.column_config.NumberColumn(
                "Upside",
                format="%.1f%%",
            ),

        "RSI":
            st.column_config.NumberColumn(
                "RSI",
                format="%.1f",
            ),

        "MACD":
            st.column_config.NumberColumn(
                "MACD",
                format="%.2f",
            ),

        "MACD Signal":
            st.column_config.NumberColumn(
                "Signal",
                format="%.2f",
            ),

        "SMA 50":
            st.column_config.NumberColumn(
                "SMA 50",
                format="$%.2f",
            ),

        "SMA 200":
            st.column_config.NumberColumn(
                "SMA 200",
                format="$%.2f",
            ),

        "Bullish Alignment":
            st.column_config.CheckboxColumn(
                "Bullish",
            ),

        "Failed Tests":
            st.column_config.TextColumn(
                "Failed Tests",
                width="large",
            ),
    },
)


# =========================================================
# Selected stock
# =========================================================

st.divider()

st.subheader("Stock Details")


if not filtered_df.empty:

    ticker_options = (
        filtered_df["Ticker"]
        .dropna()
        .astype(str)
        .tolist()
    )

    selected_ticker = st.selectbox(
        "Select a stock",
        ticker_options,
    )


    selected_rows = filtered_df[
        filtered_df["Ticker"]
        == selected_ticker
    ]


    if not selected_rows.empty:

        stock = selected_rows.iloc[0]

        company_name = stock.get(
            "Name",
            "",
        )

        st.markdown(
            f"### {selected_ticker} "
            f"{company_name or ''}"
        )


        detail1, detail2, detail3, detail4 = (
            st.columns(4)
        )


        price = safe_number(
            stock.get("Price")
        )

        score = safe_number(
            stock.get("Score")
        )

        max_score = safe_number(
            stock.get("Max Score")
        )

        upside = safe_number(
            stock.get("Upside %")
        )


        detail1.metric(
            "Price",
            f"${price:,.2f}"
            if price is not None
            else "N/A",
        )


        detail2.metric(
            "Score",
            (
                f"{score:.0f} / {max_score:.0f}"
                if score is not None
                and max_score is not None
                else "N/A"
            ),
        )


        detail3.metric(
            "Upside",
            (
                f"{upside:+.1%}"
                if upside is not None
                else "N/A"
            ),
        )


        passes = bool(
            stock.get(
                "Passes Screen",
                False,
            )
        )


        detail4.metric(
            "Screen",
            "PASS" if passes else "FAIL",
        )


        failed_tests = stock.get(
            "Failed Tests"
        )


        if passes:

            st.success(
                "This stock currently passes "
                "the screener."
            )

        elif failed_tests:

            st.warning(
                f"Failed tests: {failed_tests}"
            )
# =========================================================
# Stock price chart
# =========================================================

history = histories.get(
    selected_ticker
)

stock_chart = build_stock_chart(
    selected_ticker,
    history
)

if stock_chart is not None:

    st.plotly_chart(
        stock_chart,
        width="stretch",
        config={
            "displayModeBar": True,
            "displaylogo": False,
            "scrollZoom": True,
        },
    )

else:

    st.info(
        f"No price history is available for "
        f"{selected_ticker}."
    )

def prepare_display_percentages(df):
    """
    Convert decimal percentage values to 0-100 values
    for display in Streamlit.

    This does NOT modify the screener calculation data.
    """

    result = df.copy()

    percentage_columns = [
        "Daily Change %",
        "1 Month Change %",
        "% From 52W High",
        "Score %",
        "Return On Equity",
        "Profit Margin",
        "Revenue Growth",
        "Earnings Growth",
        "Upside %",
        "Dividend Yield",
        "5Y Avg Dividend Yield",
        "Payout Ratio",
        "Expense Ratio",
        "Yield",
        "3Y Average Return",
        "5Y Average Return",
    ]

    for column in percentage_columns:
        if column in result.columns:
            result[column] = (
                pd.to_numeric(
                    result[column],
                    errors="coerce"
                ) * 100
            )

    return result
"""Combined investment workbook with 1-month Excel and HTML heatmaps.

Workbook expected in the same folder: StockAnalysis.xlsx
Tickers sheet columns:
    A = stocks
    B = dividend stocks
    C = ETFs
    D = S&P 500 stocks

Install:
    pip install yfinance pandas openpyxl pillow plotly kaleido

Kaleido 1.x uses Chrome for PNG export. If needed:
    kaleido_get_chrome
"""

from __future__ import annotations

import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import yfinance as yf
from openpyxl import Workbook, load_workbook
from openpyxl.drawing.image import Image as XLImage
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


# -----------------------------------------------------------------------------
# SETTINGS
# -----------------------------------------------------------------------------
WORKBOOK_NAME = "Combo_Analysis.xlsx"
TICKERS_SHEET = "Tickers"
HTML_DASHBOARD_NAME = "investment_dashboard.html"
SP500_IMAGE_NAME = "sp500_heatmap.png"
ETF_IMAGE_NAME = "etf_heatmap.png"

# Approximately one trading month. The change compares the newest close with
# the close 21 trading sessions earlier, requiring at least 22 observations.
MONTH_LOOKBACK_SESSIONS = 21

# Stock screening thresholds
MAX_PEG = 2.5
MAX_FORWARD_PE = 30.0
MIN_ROE = 0.05
MIN_PROFIT_MARGIN = 0.05
MIN_REVENUE_GROWTH = 0.00
MIN_EARNINGS_GROWTH = 0.00
MAX_DEBT_TO_EQUITY = 150.0
MIN_UPSIDE_PCT = 0.00

# Dividend screening thresholds
MIN_DIVIDEND_YIELD = 0.02
MAX_PAYOUT_RATIO = 0.70

# ETF screening thresholds
MAX_EXPENSE_RATIO = 0.005
MIN_AUM = 500_000_000

REQUEST_PAUSE_SECONDS = 0.05


# -----------------------------------------------------------------------------
# GENERAL HELPERS
# -----------------------------------------------------------------------------
def clean_number(value: Any) -> float | None:
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def safe_compare(value: float | None, operator: str, threshold: float) -> bool:
    if value is None:
        return False
    if operator == "lt":
        return value < threshold
    if operator == "gt":
        return value > threshold
    raise ValueError(f"Unsupported operator: {operator}")


def normalize_ticker(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    ticker = str(value).strip().upper().replace(".", "-")
    if not ticker or ticker in {"TICKER", "SYMBOL", "NAN", "NONE"}:
        return None
    return ticker


def unique_ordered(values: list[str | None]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))


# -----------------------------------------------------------------------------
# WORKBOOK INPUT
# -----------------------------------------------------------------------------
def create_starter_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = TICKERS_SHEET
    sheet.append(["Stock", "Dividend", "ETF", "S&P 500"])
    sheet.freeze_panes = "A2"

    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)

    for column in range(1, 5):
        sheet.column_dimensions[get_column_letter(column)].width = 18

    workbook.save(path)


def read_ticker_lists(path: Path) -> dict[str, list[str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    if TICKERS_SHEET not in workbook.sheetnames:
        raise KeyError(f'The workbook needs a sheet named "{TICKERS_SHEET}".')

    sheet = workbook[TICKERS_SHEET]
    columns = {"stocks": 1, "dividends": 2, "etfs": 3, "sp500": 4}
    ticker_lists: dict[str, list[str]] = {}

    for name, column in columns.items():
        values = [
            normalize_ticker(sheet.cell(row=row, column=column).value)
            for row in range(2, sheet.max_row + 1)
        ]
        ticker_lists[name] = unique_ordered(values)

    workbook.close()
    return ticker_lists


# -----------------------------------------------------------------------------
# YFINANCE DATA
# -----------------------------------------------------------------------------
def download_history(tickers: list[str]) -> dict[str, pd.DataFrame]:
    if not tickers:
        return {}

    data = yf.download(
        tickers=tickers,
        period="1y",
        interval="1d",
        auto_adjust=False,
        actions=False,
        group_by="ticker",
        threads=True,
        progress=False,
    )

    if len(tickers) == 1:
        frame = data.dropna(how="all")
        return {tickers[0]: frame} if not frame.empty else {}

    histories: dict[str, pd.DataFrame] = {}
    for ticker in tickers:
        try:
            frame = data[ticker].copy().dropna(how="all")
            if not frame.empty:
                histories[ticker] = frame
        except (KeyError, TypeError):
            continue

    return histories


def price_metrics(history: pd.DataFrame | None) -> dict[str, Any]:
    blank = {
        "Price": None,
        "Previous Close": None,
        "Daily Change %": None,
        "1 Month Change %": None,
        "SMA 50": None,
        "SMA 200": None,
        "Above SMA 50": False,
        "Above SMA 200": False,
        "SMA 50 > SMA 200": False,
        "Bullish Alignment": False,
        "52 Week High": None,
        "% From 52W High": None,
    }

    if history is None or history.empty:
        return blank

    price_column = "Adj Close" if "Adj Close" in history.columns else "Close"
    close = pd.to_numeric(history[price_column], errors="coerce").dropna()
    if close.empty:
        return blank

    price = clean_number(close.iloc[-1])
    previous_close = clean_number(close.iloc[-2]) if len(close) >= 2 else None

    month_reference = None
    required_rows = MONTH_LOOKBACK_SESSIONS + 1
    if len(close) >= required_rows:
        month_reference = clean_number(close.iloc[-required_rows])

    daily_change = (
        price / previous_close - 1
        if price is not None and previous_close not in (None, 0)
        else None
    )
    month_change = (
        price / month_reference - 1
        if price is not None and month_reference not in (None, 0)
        else None
    )

    sma50 = (
        clean_number(close.rolling(50).mean().iloc[-1])
        if len(close) >= 50
        else None
    )
    sma200 = (
        clean_number(close.rolling(200).mean().iloc[-1])
        if len(close) >= 200
        else None
    )
    high52 = clean_number(close.max())

    above50 = price is not None and sma50 is not None and price > sma50
    above200 = price is not None and sma200 is not None and price > sma200
    golden_alignment = sma50 is not None and sma200 is not None and sma50 > sma200

    return {
        "Price": price,
        "Previous Close": previous_close,
        "Daily Change %": daily_change,
        "1 Month Change %": month_change,
        "SMA 50": sma50,
        "SMA 200": sma200,
        "Above SMA 50": above50,
        "Above SMA 200": above200,
        "SMA 50 > SMA 200": golden_alignment,
        "Bullish Alignment": above50 and above200 and golden_alignment,
        "52 Week High": high52,
        "% From 52W High": (
            price / high52 - 1
            if price is not None and high52 not in (None, 0)
            else None
        ),
    }


def get_info(ticker: str, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if ticker in cache:
        return cache[ticker]

    try:
        cache[ticker] = yf.Ticker(ticker).get_info() or {}
    except Exception as exc:
        print(f"  Warning: information unavailable for {ticker}: {exc}")
        cache[ticker] = {}

    time.sleep(REQUEST_PAUSE_SECONDS)
    return cache[ticker]


# -----------------------------------------------------------------------------
# SCREENER DATA
# -----------------------------------------------------------------------------
def build_stock_rows(
    tickers: list[str],
    histories: dict[str, pd.DataFrame],
    info_cache: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []

    for number, ticker in enumerate(tickers, start=1):
        print(f"Stock {number}/{len(tickers)}: {ticker}")
        info = get_info(ticker, info_cache)
        prices = price_metrics(histories.get(ticker))

        target_price = clean_number(info.get("targetMeanPrice"))
        current_price = prices["Price"] or clean_number(info.get("currentPrice"))
        upside = (
            target_price / current_price - 1
            if target_price is not None and current_price not in (None, 0)
            else None
        )

        peg = clean_number(info.get("pegRatio") or info.get("trailingPegRatio"))
        forward_pe = clean_number(info.get("forwardPE"))
        roe = clean_number(info.get("returnOnEquity"))
        margin = clean_number(info.get("profitMargins"))
        revenue_growth = clean_number(info.get("revenueGrowth"))
        earnings_growth = clean_number(info.get("earningsGrowth"))
        debt_to_equity = clean_number(info.get("debtToEquity"))

        tests = [
            safe_compare(peg, "lt", MAX_PEG),
            safe_compare(forward_pe, "lt", MAX_FORWARD_PE),
            safe_compare(roe, "gt", MIN_ROE),
            safe_compare(margin, "gt", MIN_PROFIT_MARGIN),
            safe_compare(revenue_growth, "gt", MIN_REVENUE_GROWTH),
            safe_compare(earnings_growth, "gt", MIN_EARNINGS_GROWTH),
            safe_compare(debt_to_equity, "lt", MAX_DEBT_TO_EQUITY),
            safe_compare(upside, "gt", MIN_UPSIDE_PCT),
            prices["Above SMA 50"],
            prices["Above SMA 200"],
            prices["SMA 50 > SMA 200"],
        ]

        rows.append(
            {
                "Ticker": ticker,
                "Name": info.get("shortName") or info.get("longName"),
                "Sector": info.get("sector"),
                "Industry": info.get("industry"),
                **prices,
                "Target Price": target_price,
                "Upside %": upside,
                "PEG": peg,
                "Forward PE": forward_pe,
                "Return On Equity": roe,
                "Profit Margin": margin,
                "Revenue Growth": revenue_growth,
                "Earnings Growth": earnings_growth,
                "Debt To Equity": debt_to_equity,
                "Free Cash Flow": clean_number(info.get("freeCashflow")),
                "Score": sum(tests),
                "Max Score": len(tests),
                "Passes Screen": all(tests[:8]) and prices["Above SMA 200"],
                "Error": None if info else "Data unavailable",
            }
        )

    return rows


def build_dividend_rows(
    tickers: list[str],
    histories: dict[str, pd.DataFrame],
    info_cache: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []

    for number, ticker in enumerate(tickers, start=1):
        print(f"Dividend {number}/{len(tickers)}: {ticker}")
        info = get_info(ticker, info_cache)
        prices = price_metrics(histories.get(ticker))

        dividend_yield = clean_number(info.get("dividendYield"))
        payout_ratio = clean_number(info.get("payoutRatio"))
        free_cash_flow = clean_number(info.get("freeCashflow"))
        debt_to_equity = clean_number(info.get("debtToEquity"))
        five_year_average = clean_number(info.get("fiveYearAvgDividendYield"))

        tests = [
            safe_compare(dividend_yield, "gt", MIN_DIVIDEND_YIELD),
            safe_compare(payout_ratio, "lt", MAX_PAYOUT_RATIO),
            free_cash_flow is not None and free_cash_flow > 0,
            safe_compare(debt_to_equity, "lt", MAX_DEBT_TO_EQUITY),
            prices["Above SMA 50"],
            prices["Above SMA 200"],
            prices["SMA 50 > SMA 200"],
        ]

        rows.append(
            {
                "Ticker": ticker,
                "Name": info.get("shortName") or info.get("longName"),
                "Sector": info.get("sector"),
                **prices,
                "Dividend Yield": dividend_yield,
                "5Y Avg Dividend Yield": (
                    five_year_average / 100
                    if five_year_average is not None
                    else None
                ),
                "Payout Ratio": payout_ratio,
                "Free Cash Flow": free_cash_flow,
                "Debt To Equity": debt_to_equity,
                "Score": sum(tests),
                "Max Score": len(tests),
                "Passes Screen": all(tests[:4]) and prices["Above SMA 200"],
                "Error": None if info else "Data unavailable",
            }
        )

    return rows


def build_etf_rows(
    tickers: list[str],
    histories: dict[str, pd.DataFrame],
    info_cache: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []

    for number, ticker in enumerate(tickers, start=1):
        print(f"ETF {number}/{len(tickers)}: {ticker}")
        info = get_info(ticker, info_cache)
        prices = price_metrics(histories.get(ticker))

        expense_ratio = clean_number(
            info.get("annualReportExpenseRatio") or info.get("netExpenseRatio")
        )
        total_assets = clean_number(info.get("totalAssets"))

        tests = [
            safe_compare(expense_ratio, "lt", MAX_EXPENSE_RATIO),
            safe_compare(total_assets, "gt", MIN_AUM),
            prices["Above SMA 50"],
            prices["Above SMA 200"],
            prices["SMA 50 > SMA 200"],
        ]

        rows.append(
            {
                "Ticker": ticker,
                "Name": info.get("shortName") or info.get("longName"),
                "Category": info.get("category"),
                **prices,
                "Expense Ratio": expense_ratio,
                "Total Assets": total_assets,
                "Yield": clean_number(info.get("yield")),
                "3Y Average Return": clean_number(info.get("threeYearAverageReturn")),
                "5Y Average Return": clean_number(info.get("fiveYearAverageReturn")),
                "Score": sum(tests),
                "Max Score": len(tests),
                "Passes Screen": tests[0] and tests[1] and prices["Above SMA 200"],
                "Error": None if info else "Data unavailable",
            }
        )

    return rows


def build_heatmap_rows(
    tickers: list[str],
    histories: dict[str, pd.DataFrame],
    info_cache: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = []

    for ticker in tickers:
        info = get_info(ticker, info_cache)
        prices = price_metrics(histories.get(ticker))
        size_value = clean_number(info.get("marketCap") or info.get("totalAssets"))

        rows.append(
            {
                "Ticker": ticker,
                "Name": info.get("shortName") or info.get("longName"),
                "Group": info.get("sector") or info.get("category") or "Unclassified",
                "Market Cap / Assets": size_value or 1,
                "Price": prices["Price"],
                "Daily Change %": prices["Daily Change %"],
                "1 Month Change %": prices["1 Month Change %"],
                "SMA 50": prices["SMA 50"],
                "SMA 200": prices["SMA 200"],
                "Above SMA 50": prices["Above SMA 50"],
                "Above SMA 200": prices["Above SMA 200"],
                "Bullish Alignment": prices["Bullish Alignment"],
            }
        )

    return rows


def sorted_frame(
    rows: list[dict[str, Any]],
    columns: list[str],
    ascending: list[bool],
) -> pd.DataFrame:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values(
        columns,
        ascending=ascending,
        na_position="last",
    ).reset_index(drop=True)


# -----------------------------------------------------------------------------
# PLOTLY HEATMAPS
# -----------------------------------------------------------------------------
def create_treemap(frame: pd.DataFrame, title: str):
    if frame.empty:
        return None

    chart = frame.copy()
    chart["Market Cap / Assets"] = (
        pd.to_numeric(chart["Market Cap / Assets"], errors="coerce")
        .fillna(1)
        .clip(lower=1)
    )
    chart["1 Month Change %"] = pd.to_numeric(
        chart["1 Month Change %"], errors="coerce"
    )

    # Rows without enough history are excluded instead of displayed as nan%.
    chart = chart.dropna(subset=["1 Month Change %"])
    if chart.empty:
        return None

    chart["Group"] = chart["Group"].fillna("Unclassified")
    chart["Name"] = chart["Name"].fillna(chart["Ticker"])

    figure = px.treemap(
        chart,
        path=[px.Constant("Market"), "Group", "Ticker"],
        values="Market Cap / Assets",
        color="1 Month Change %",
        color_continuous_scale=[
            [0.00, "#8B0000"],
            [0.25, "#D73027"],
            [0.45, "#F4A6A6"],
            [0.50, "#D9D9D9"],
            [0.55, "#A7DCA7"],
            [0.75, "#1A9850"],
            [1.00, "#006400"],
        ],
        color_continuous_midpoint=0,
        custom_data=[
            "Name",
            "Price",
            "SMA 50",
            "SMA 200",
            "Bullish Alignment",
        ],
        title=title,
    )

    # Plotly creates parent rectangles for market and sector/category levels.
    # Some parent color values may not be finite. Preformatted text prevents nan%.
    safe_change_labels = []
    for value in figure.data[0].marker.colors:
        number = clean_number(value)
        safe_change_labels.append(f"{number:+.2%}" if number is not None else "")

    figure.update_traces(
        text=safe_change_labels,
        texttemplate="<b>%{label}</b><br>%{text}",
        marker=dict(line=dict(width=1, color="#202020")),
        root_color="#101820",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "%{customdata[0]}<br>"
            "1 Month Change: %{color:+.2%}<br>"
            "Price: $%{customdata[1]:,.2f}<br>"
            "SMA 50: $%{customdata[2]:,.2f}<br>"
            "SMA 200: $%{customdata[3]:,.2f}<br>"
            "Bullish Alignment: %{customdata[4]}"
            "<extra></extra>"
        ),
    )

    figure.update_layout(
        template="plotly_dark",
        paper_bgcolor="#101820",
        plot_bgcolor="#101820",
        font=dict(color="white"),
        margin=dict(t=55, l=8, r=8, b=8),
        coloraxis_colorbar=dict(title="1 Month Change", tickformat="+.1%"),
    )

    return figure


def create_html_dashboard(
    path: Path,
    frames: dict[str, pd.DataFrame],
    stock_figure,
    etf_figure,
) -> None:
    def count_true(frame: pd.DataFrame, column: str) -> int:
        if frame.empty or column not in frame.columns:
            return 0
        return int(frame[column].fillna(False).sum())

    stocks = frames["Stock Screener"]
    dividends = frames["Dividend Screener"]
    etfs = frames["ETF Screener"]

    cards = [
        ("Stocks Screened", len(stocks)),
        ("Stocks Passing", count_true(stocks, "Passes Screen")),
        ("Dividend Stocks Passing", count_true(dividends, "Passes Screen")),
        ("ETFs Passing", count_true(etfs, "Passes Screen")),
        ("Stock Bullish Alignments", count_true(stocks, "Bullish Alignment")),
        ("ETF Bullish Alignments", count_true(etfs, "Bullish Alignment")),
    ]

    cards_html = "".join(
        f'<div class="card"><div class="value">{value:,}</div>'
        f'<div class="label">{label}</div></div>'
        for label, value in cards
    )

    stock_html = (
        stock_figure.to_html(full_html=False, include_plotlyjs="inline")
        if stock_figure is not None
        else "<p>No S&P 500 heatmap data was available.</p>"
    )
    etf_html = (
        etf_figure.to_html(full_html=False, include_plotlyjs=False)
        if etf_figure is not None
        else "<p>No ETF heatmap data was available.</p>"
    )

    refreshed = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")

    html = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Investment Dashboard</title>
<style>
body {{ margin:0; background:#0b1220; color:#fff; font-family:Segoe UI,Arial,sans-serif; }}
header {{ padding:24px 32px; background:#13233d; }}
h1 {{ margin:0 0 6px; }}
.sub {{ color:#aebbd0; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:14px; padding:22px 32px; }}
.card {{ background:#172941; border-radius:14px; padding:18px; box-shadow:0 4px 14px #0005; }}
.value {{ font-size:30px; font-weight:700; color:#7fd1ff; }}
.label {{ margin-top:5px; color:#c8d3e3; }}
.chart {{ margin:0 22px 24px; background:#101820; border-radius:14px; overflow:hidden; }}
</style>
</head>
<body>
<header>
<h1>Investment Dashboard</h1>
<div class="sub">One-month heatmaps, updated {refreshed}</div>
</header>
<section class="cards">{cards_html}</section>
<section class="chart">{stock_html}</section>
<section class="chart">{etf_html}</section>
</body>
</html>"""

    path.write_text(html, encoding="utf-8")


def export_heatmap_assets(
    output_dir: Path,
    frames: dict[str, pd.DataFrame],
) -> dict[str, Path]:
    stock_figure = create_treemap(
        frames["Stock Heatmap Data"],
        "S&P 500 One-Month Market Heatmap",
    )
    etf_figure = create_treemap(
        frames["ETF Heatmap Data"],
        "ETF One-Month Market Heatmap",
    )

    images: dict[str, Path] = {}
    exports = [
        ("S&P 500 Map", stock_figure, SP500_IMAGE_NAME),
        ("ETF Map", etf_figure, ETF_IMAGE_NAME),
    ]

    for sheet_name, figure, filename in exports:
        if figure is None:
            continue
        image_path = output_dir / filename
        try:
            figure.write_image(image_path, width=1800, height=1000, scale=1)
            images[sheet_name] = image_path
        except Exception as exc:
            print(f"Warning: PNG export failed for {sheet_name}: {exc}")
            print("The interactive HTML dashboard will still be created.")

    create_html_dashboard(
        output_dir / HTML_DASHBOARD_NAME,
        frames,
        stock_figure,
        etf_figure,
    )
    return images


# -----------------------------------------------------------------------------
# EXCEL OUTPUT
# -----------------------------------------------------------------------------
def write_dataframe_sheet(
    workbook,
    sheet_name: str,
    frame: pd.DataFrame,
) -> None:
    if sheet_name in workbook.sheetnames:
        del workbook[sheet_name]

    sheet = workbook.create_sheet(sheet_name)
    sheet.sheet_view.showGridLines = False
    sheet.freeze_panes = "A2"

    if frame.empty:
        sheet["A1"] = "No results"
        sheet["A1"].font = Font(bold=True)
        return

    sheet.append(list(frame.columns))
    for row in frame.itertuples(index=False, name=None):
        sheet.append(list(row))

    for cell in sheet[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")

    sheet.auto_filter.ref = sheet.dimensions
    headers = {cell.value: cell.column for cell in sheet[1]}

    percentage_headers = {
        "Daily Change %",
        "1 Month Change %",
        "% From 52W High",
        "Upside %",
        "Return On Equity",
        "Profit Margin",
        "Revenue Growth",
        "Earnings Growth",
        "Dividend Yield",
        "5Y Avg Dividend Yield",
        "Payout Ratio",
        "Expense Ratio",
        "Yield",
        "3Y Average Return",
        "5Y Average Return",
    }
    currency_headers = {
        "Price",
        "Previous Close",
        "SMA 50",
        "SMA 200",
        "52 Week High",
        "Target Price",
    }
    integer_headers = {
        "Free Cash Flow",
        "Total Assets",
        "Market Cap / Assets",
    }

    for header, column in headers.items():
        if header in percentage_headers:
            number_format = "0.0%;[Red](0.0%);-"
        elif header in currency_headers:
            number_format = "$#,##0.00;[Red]($#,##0.00);-"
        elif header in integer_headers:
            number_format = "#,##0;[Red](#,##0);-"
        else:
            continue

        for row_cells in sheet.iter_cols(
            min_col=column,
            max_col=column,
            min_row=2,
        ):
            for cell in row_cells:
                cell.number_format = number_format

    if "1 Month Change %" in headers and sheet.max_row >= 2:
        column_letter = get_column_letter(headers["1 Month Change %"])
        sheet.conditional_formatting.add(
            f"{column_letter}2:{column_letter}{sheet.max_row}",
            ColorScaleRule(
                start_type="min",
                start_color="F8696B",
                mid_type="num",
                mid_value=0,
                mid_color="FFEB84",
                end_type="max",
                end_color="63BE7B",
            ),
        )

    for column_cells in sheet.columns:
        values = [
            str(cell.value) if cell.value is not None else ""
            for cell in column_cells[:200]
        ]
        width = min(max(max((len(value) for value in values), default=0) + 2, 11), 32)
        sheet.column_dimensions[get_column_letter(column_cells[0].column)].width = width


def insert_heatmap_sheet(
    workbook,
    sheet_name: str,
    image_path: Path | None,
    html_path: Path,
) -> None:
    if sheet_name in workbook.sheetnames:
        del workbook[sheet_name]

    sheet = workbook.create_sheet(sheet_name)
    sheet.sheet_view.showGridLines = False
    sheet["A1"] = sheet_name
    sheet["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="17365D")
    sheet.merge_cells("A1:H1")

    sheet["A2"] = "Open interactive dashboard"
    sheet["A2"].hyperlink = html_path.resolve().as_uri()
    sheet["A2"].style = "Hyperlink"

    if image_path is not None and image_path.exists():
        image = XLImage(str(image_path))
        image.width = 1350
        image.height = 750
        sheet.add_image(image, "A4")
    else:
        sheet["A4"] = (
            "Static image unavailable. Use the interactive dashboard link above."
        )

    for column in range(1, 20):
        sheet.column_dimensions[get_column_letter(column)].width = 12


def build_dashboard(
    workbook,
    frames: dict[str, pd.DataFrame],
    html_path: Path,
) -> None:
    if "Dashboard" in workbook.sheetnames:
        del workbook["Dashboard"]

    sheet = workbook.create_sheet("Dashboard", 0)
    sheet.sheet_view.showGridLines = False
    sheet["A1"] = "Investment Screening Dashboard"
    sheet["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="17365D")
    sheet.merge_cells("A1:D1")

    sheet.append(
        [
            "Last Refresh",
            datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z"),
        ]
    )
    sheet.append([])
    sheet.append(["Section", "Tickers", "Passing", "Strong Uptrends"])

    sections = [
        ("Stocks", frames["Stock Screener"]),
        ("Dividends", frames["Dividend Screener"]),
        ("ETFs", frames["ETF Screener"]),
    ]

    for label, frame in sections:
        passing = (
            int(frame["Passes Screen"].fillna(False).sum())
            if not frame.empty and "Passes Screen" in frame.columns
            else 0
        )
        bullish = (
            int(frame["Bullish Alignment"].fillna(False).sum())
            if not frame.empty and "Bullish Alignment" in frame.columns
            else 0
        )
        sheet.append([label, len(frame), passing, bullish])

    sheet["A9"] = "Open interactive one-month dashboard"
    sheet["A9"].hyperlink = html_path.resolve().as_uri()
    sheet["A9"].style = "Hyperlink"

    sheet["A11"] = "Heatmap Period"
    sheet["B11"] = f"Approximately {MONTH_LOOKBACK_SESSIONS} trading sessions"

    for cell in sheet[4]:
        cell.fill = PatternFill("solid", fgColor="5B9BD5")
        cell.font = Font(color="FFFFFF", bold=True)

    for column, width in {"A": 35, "B": 24, "C": 18, "D": 20}.items():
        sheet.column_dimensions[column].width = width


def save_results(
    workbook_path: Path,
    frames: dict[str, pd.DataFrame],
    images: dict[str, Path],
) -> None:
    workbook = load_workbook(workbook_path)

    data_sheets = [
        "Stock Screener",
        "Dividend Screener",
        "ETF Screener",
        "Stock Heatmap Data",
        "ETF Heatmap Data",
    ]
    for sheet_name in data_sheets:
        write_dataframe_sheet(workbook, sheet_name, frames[sheet_name])

    html_path = workbook_path.parent / HTML_DASHBOARD_NAME
    insert_heatmap_sheet(
        workbook,
        "S&P 500 Map",
        images.get("S&P 500 Map"),
        html_path,
    )
    insert_heatmap_sheet(
        workbook,
        "ETF Map",
        images.get("ETF Map"),
        html_path,
    )
    build_dashboard(workbook, frames, html_path)

    workbook.calculation.fullCalcOnLoad = True
    workbook.calculation.forceFullCalc = True
    workbook.save(workbook_path)


# -----------------------------------------------------------------------------
# MAIN
# -----------------------------------------------------------------------------
def main() -> None:
    script_directory = Path(__file__).resolve().parent
    workbook_path = script_directory / WORKBOOK_NAME

    if not workbook_path.exists():
        create_starter_workbook(workbook_path)
        print(f"Created starter workbook: {workbook_path}")
        print("Add tickers to the Tickers sheet, save the workbook, and run again.")
        return

    ticker_lists = read_ticker_lists(workbook_path)
    all_tickers = unique_ordered(
        ticker_lists["stocks"]
        + ticker_lists["dividends"]
        + ticker_lists["etfs"]
        + ticker_lists["sp500"]
    )

    if not all_tickers:
        print("No tickers were found on the Tickers sheet.")
        return

    print(f"Downloading one year of history for {len(all_tickers)} tickers...")
    histories = download_history(all_tickers)
    info_cache: dict[str, dict[str, Any]] = {}

    stock_frame = sorted_frame(
        build_stock_rows(ticker_lists["stocks"], histories, info_cache),
        ["Passes Screen", "Score", "Ticker"],
        [False, False, True],
    )
    dividend_frame = sorted_frame(
        build_dividend_rows(ticker_lists["dividends"], histories, info_cache),
        ["Passes Screen", "Score", "Dividend Yield"],
        [False, False, False],
    )
    etf_frame = sorted_frame(
        build_etf_rows(ticker_lists["etfs"], histories, info_cache),
        ["Passes Screen", "Score", "Ticker"],
        [False, False, True],
    )
    stock_heatmap_frame = sorted_frame(
        build_heatmap_rows(ticker_lists["sp500"], histories, info_cache),
        ["Group", "1 Month Change %"],
        [True, False],
    )
    etf_heatmap_frame = sorted_frame(
        build_heatmap_rows(ticker_lists["etfs"], histories, info_cache),
        ["Group", "1 Month Change %"],
        [True, False],
    )

    frames = {
        "Stock Screener": stock_frame,
        "Dividend Screener": dividend_frame,
        "ETF Screener": etf_frame,
        "Stock Heatmap Data": stock_heatmap_frame,
        "ETF Heatmap Data": etf_heatmap_frame,
    }

    images = export_heatmap_assets(script_directory, frames)
    save_results(workbook_path, frames, images)

    print(f"Updated workbook: {workbook_path}")
    print(f"Interactive dashboard: {script_directory / HTML_DASHBOARD_NAME}")


if __name__ == "__main__":
    main()

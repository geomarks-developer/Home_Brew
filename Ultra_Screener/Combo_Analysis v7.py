# Combined stock, dividend, and ETF screeners with stock, dividend, ETF,
# and sector ETF heatmaps.
#
# Expected workbook: Combo_Analysis.xlsx in the same folder as this script.
# Tickers sheet: A=stocks, B=dividend stocks, C=ETFs, D=S&P 100 stocks.
#
# Install:
#     pip install yfinance pandas openpyxl pillow plotly kaleido
# If Kaleido requires Chrome:
#     kaleido_get_chrome

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

WORKBOOK_NAME = "Combo_Analysis.xlsx"
TICKERS_SHEET = "Tickers"
HTML_NAME = "investment_dashboard.html"
MONTH_LOOKBACK = 21
MAX_PEG, MAX_FORWARD_PE = 2.5, 30.0
MIN_ROE, MIN_MARGIN = 0.05, 0.05
MAX_DEBT_EQUITY, MIN_UPSIDE = 150.0, 0.0
MIN_DIVIDEND_YIELD, MAX_PAYOUT = 0.02, 0.70
MAX_EXPENSE_RATIO, MIN_AUM = 0.005, 500_000_000
PAUSE = 0.05

SECTOR_ETFS = {
    "Communication Services": {"Ticker": "XLC", "Weight": 1},
    "Consumer Discretionary": {"Ticker": "XLY", "Weight": 1},
    "Consumer Staples": {"Ticker": "XLP", "Weight": 1},
    "Energy": {"Ticker": "XLE", "Weight": 1},
    "Financials": {"Ticker": "XLF", "Weight": 1},
    "Health Care": {"Ticker": "XLV", "Weight": 1},
    "Industrials": {"Ticker": "XLI", "Weight": 1},
    "Materials": {"Ticker": "XLB", "Weight": 1},
    "Real Estate": {"Ticker": "XLRE", "Weight": 1},
    "Technology": {"Ticker": "XLK", "Weight": 1},
    "Utilities": {"Ticker": "XLU", "Weight": 1},
}


def number(value: Any) -> float | None:
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def compare(value, operation, limit):
    if value is None:
        return False
    return value < limit if operation == "lt" else value > limit


def normalize_ticker(value):
    if value is None or pd.isna(value):
        return None
    value = str(value).strip().upper().replace(".", "-")
    return None if not value or value in {"TICKER", "SYMBOL", "NAN", "NONE"} else value


def create_starter(path):
    wb = Workbook()
    ws = wb.active
    ws.title = TICKERS_SHEET
    ws.append(["Stock", "Dividend", "ETF", "S&P 100"])
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
    for col in range(1, 5):
        ws.column_dimensions[get_column_letter(col)].width = 18
    wb.save(path)


def read_tickers(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    if TICKERS_SHEET not in wb.sheetnames:
        raise KeyError('The workbook needs a sheet named "Tickers".')
    ws = wb[TICKERS_SHEET]
    result = {}
    for name, col in {"stocks": 1, "dividends": 2, "etfs": 3, "sp100": 4}.items():
        values = [normalize_ticker(ws.cell(row, col).value) for row in range(2, ws.max_row + 1)]
        result[name] = list(dict.fromkeys(value for value in values if value))
    wb.close()
    return result


def download_history(tickers):
    if not tickers:
        return {}
    data = yf.download(
        tickers, period="1y", interval="1d", auto_adjust=False,
        actions=False, group_by="ticker", threads=True, progress=False,
    )
    if len(tickers) == 1:
        frame = data.dropna(how="all")
        return {tickers[0]: frame} if not frame.empty else {}
    result = {}
    for ticker in tickers:
        try:
            frame = data[ticker].copy().dropna(how="all")
            if not frame.empty:
                result[ticker] = frame
        except (KeyError, TypeError):
            pass
    return result


def price_metrics(history):
    blank = {
        "Price": None, "Previous Close": None, "Daily Change %": None,
        "1 Month Change %": None, "SMA 50": None, "SMA 200": None,
        "Above SMA 50": False, "Above SMA 200": False,
        "SMA 50 > SMA 200": False, "Bullish Alignment": False,
        "52 Week High": None, "% From 52W High": None,
    }
    if history is None or history.empty:
        return blank
    column = "Adj Close" if "Adj Close" in history.columns else "Close"
    close = pd.to_numeric(history[column], errors="coerce").dropna()
    if close.empty:
        return blank
    price = number(close.iloc[-1])
    previous = number(close.iloc[-2]) if len(close) >= 2 else None
    month_base = number(close.iloc[-(MONTH_LOOKBACK + 1)]) if len(close) >= MONTH_LOOKBACK + 1 else None
    sma50 = number(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma200 = number(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    high = number(close.max())
    above50 = price is not None and sma50 is not None and price > sma50
    above200 = price is not None and sma200 is not None and price > sma200
    cross = sma50 is not None and sma200 is not None and sma50 > sma200
    return {
        "Price": price, "Previous Close": previous,
        "Daily Change %": price / previous - 1 if price and previous else None,
        "1 Month Change %": price / month_base - 1 if price and month_base else None,
        "SMA 50": sma50, "SMA 200": sma200, "Above SMA 50": above50,
        "Above SMA 200": above200, "SMA 50 > SMA 200": cross,
        "Bullish Alignment": above50 and above200 and cross,
        "52 Week High": high, "% From 52W High": price / high - 1 if price and high else None,
    }


def get_info(ticker, cache):
    if ticker in cache:
        return cache[ticker]
    try:
        cache[ticker] = yf.Ticker(ticker).get_info() or {}
    except Exception as exc:
        print(f"  Warning: information unavailable for {ticker}: {exc}")
        cache[ticker] = {}
    time.sleep(PAUSE)
    return cache[ticker]


def normalized_dividend_values(info):
    dividend_yield = number(info.get("dividendYield"))
    if dividend_yield is not None and dividend_yield > 1:
        dividend_yield /= 100
    payout_ratio = number(info.get("payoutRatio"))
    if payout_ratio is not None and payout_ratio > 1:
        payout_ratio /= 100
    return dividend_yield, payout_ratio


def stock_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"Stock {n}/{len(tickers)}: {ticker}")
        info = get_info(ticker, cache)
        p = price_metrics(histories.get(ticker))
        target = number(info.get("targetMeanPrice"))
        current = p["Price"] or number(info.get("currentPrice"))
        upside = target / current - 1 if target and current else None
        peg = number(info.get("pegRatio") or info.get("trailingPegRatio"))
        pe = number(info.get("forwardPE"))
        roe = number(info.get("returnOnEquity"))
        margin = number(info.get("profitMargins"))
        revenue = number(info.get("revenueGrowth"))
        earnings = number(info.get("earningsGrowth"))
        debt = number(info.get("debtToEquity"))

        peg_test = compare(peg, "lt", MAX_PEG)
        pe_test = compare(pe, "lt", MAX_FORWARD_PE)
        roe_test = compare(roe, "gt", MIN_ROE)
        margin_test = compare(margin, "gt", MIN_MARGIN)
        revenue_test = compare(revenue, "gt", 0)
        earnings_test = compare(earnings, "gt", 0)
        debt_test = compare(debt, "lt", MAX_DEBT_EQUITY)
        upside_test = compare(upside, "gt", MIN_UPSIDE)
        above_50_test = p["Above SMA 50"]
        above_200_test = p["Above SMA 200"]
        golden_cross_test = p["SMA 50 > SMA 200"]
        trend_test = above_50_test and above_200_test and golden_cross_test

        tests = [peg_test, pe_test, roe_test, margin_test, revenue_test, earnings_test,
                 debt_test, upside_test, above_50_test, above_200_test, golden_cross_test]

        failed_tests = []
        for value, passed, unavailable, failed in [
            (peg, peg_test, "PEG unavailable", "PEG too high"),
            (pe, pe_test, "Forward PE unavailable", "Forward PE too high"),
            (roe, roe_test, "ROE unavailable", "ROE too low"),
            (margin, margin_test, "Profit margin unavailable", "Profit margin too low"),
            (revenue, revenue_test, "Revenue growth unavailable", "Revenue growth not positive"),
            (earnings, earnings_test, "Earnings growth unavailable", "Earnings growth not positive"),
            (debt, debt_test, "Debt to equity unavailable", "Debt to equity too high"),
            (upside, upside_test, "Target upside unavailable", "Target upside not positive"),
        ]:
            if value is None:
                failed_tests.append(unavailable)
            elif not passed:
                failed_tests.append(failed)
        if not above_50_test: failed_tests.append("Below SMA 50")
        if not above_200_test: failed_tests.append("Below SMA 200")
        if not golden_cross_test: failed_tests.append("SMA 50 not above SMA 200")

        rows.append({
            "Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
            "Sector": info.get("sector"), "Industry": info.get("industry"), **p,
            "Target Price": target, "Upside %": upside, "PEG": peg, "Forward PE": pe,
            "Return On Equity": roe, "Profit Margin": margin, "Revenue Growth": revenue,
            "Earnings Growth": earnings, "Debt To Equity": debt,
            "Free Cash Flow": number(info.get("freeCashflow")),
            "PEG Test": peg_test, "Forward PE Test": pe_test, "ROE Test": roe_test,
            "Profit Margin Test": margin_test, "Revenue Growth Test": revenue_test,
            "Earnings Growth Test": earnings_test, "Debt To Equity Test": debt_test,
            "Upside Test": upside_test, "Above SMA 50 Test": above_50_test,
            "Above SMA 200 Test": above_200_test, "Golden Cross Test": golden_cross_test,
            "Trend Test": trend_test, "Failed Tests": ", ".join(failed_tests) if failed_tests else None,
            "Score": sum(tests), "Max Score": len(tests),
            "Passes Screen": all(tests[:8]) and above_200_test,
            "Error": None if info else "Data unavailable",
        })
    return rows


def dividend_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"Dividend {n}/{len(tickers)}: {ticker}")
        info = get_info(ticker, cache)
        p = price_metrics(histories.get(ticker))
        dividend_yield, payout_ratio = normalized_dividend_values(info)
        if dividend_yield is not None and dividend_yield > 0.25:
            continue
        cash_flow = number(info.get("freeCashflow"))
        debt = number(info.get("debtToEquity"))
        average_yield = number(info.get("fiveYearAvgDividendYield"))

        yield_test = compare(dividend_yield, "gt", MIN_DIVIDEND_YIELD)
        payout_test = compare(payout_ratio, "lt", MAX_PAYOUT)
        cash_flow_test = cash_flow is not None and cash_flow > 0
        debt_test = compare(debt, "lt", MAX_DEBT_EQUITY)
        above_50_test = p["Above SMA 50"]
        above_200_test = p["Above SMA 200"]
        golden_cross_test = p["SMA 50 > SMA 200"]
        trend_test = above_50_test and above_200_test and golden_cross_test
        tests = [yield_test, payout_test, cash_flow_test, debt_test,
                 above_50_test, above_200_test, golden_cross_test]

        failed_tests = []
        checks = [
            (dividend_yield, yield_test, "Dividend yield unavailable", "Dividend yield below minimum"),
            (payout_ratio, payout_test, "Payout ratio unavailable", "Payout ratio too high"),
            (cash_flow, cash_flow_test, "Free cash flow unavailable", "Free cash flow not positive"),
            (debt, debt_test, "Debt to equity unavailable", "Debt to equity too high"),
        ]
        for value, passed, unavailable, failed in checks:
            if value is None: failed_tests.append(unavailable)
            elif not passed: failed_tests.append(failed)
        if not above_50_test: failed_tests.append("Below SMA 50")
        if not above_200_test: failed_tests.append("Below SMA 200")
        if not golden_cross_test: failed_tests.append("SMA 50 not above SMA 200")

        rows.append({
            "Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
            "Sector": info.get("sector"), **p, "Dividend Yield": dividend_yield,
            "5Y Avg Dividend Yield": average_yield / 100 if average_yield is not None else None,
            "Payout Ratio": payout_ratio, "Free Cash Flow": cash_flow, "Debt To Equity": debt,
            "Dividend Yield Test": yield_test, "Payout Ratio Test": payout_test,
            "Free Cash Flow Test": cash_flow_test, "Debt To Equity Test": debt_test,
            "Above SMA 50 Test": above_50_test, "Above SMA 200 Test": above_200_test,
            "Golden Cross Test": golden_cross_test, "Trend Test": trend_test,
            "Failed Tests": ", ".join(failed_tests) if failed_tests else None,
            "Score": sum(tests), "Max Score": len(tests),
            "Passes Screen": all(tests[:4]) and above_200_test,
            "Error": None if info else "Data unavailable",
        })
    return rows

def fund_operation_value(operations, row_names, ticker):
    """Read a numeric ETF metric from yfinance funds_data.fund_operations."""
    if operations is None or not isinstance(operations, pd.DataFrame) or operations.empty:
        return None

    normalized_rows = {str(index).strip().lower(): index for index in operations.index}
    normalized_columns = {str(column).strip().lower(): column for column in operations.columns}

    for row_name in row_names:
        row_key = str(row_name).strip().lower()
        if row_key not in normalized_rows:
            continue

        actual_row = normalized_rows[row_key]
        preferred_columns = [ticker.lower(), "fund", "value"]

        for column_name in preferred_columns:
            if column_name in normalized_columns:
                value = number(operations.loc[actual_row, normalized_columns[column_name]])
                if value is not None:
                    return value

        row = operations.loc[actual_row]
        if isinstance(row, pd.Series):
            for raw_value in row.tolist():
                value = number(raw_value)
                if value is not None:
                    return value
        else:
            value = number(row)
            if value is not None:
                return value

    return None


def get_etf_fund_metrics(ticker, info, fund_cache):
    """Get expense ratio and net assets, preferring ETF-specific fund data."""
    if ticker in fund_cache:
        return fund_cache[ticker]

    expense = number(info.get("annualReportExpenseRatio") or info.get("netExpenseRatio"))
    assets = number(info.get("totalAssets"))
    expense_source = "Ticker info" if expense is not None else None
    assets_source = "Ticker info" if assets is not None else None

    try:
        fund_data = yf.Ticker(ticker).funds_data
        operations = fund_data.fund_operations

        fund_expense = fund_operation_value(
            operations,
            ["Annual Report Expense Ratio", "Net Expense Ratio", "Expense Ratio"],
            ticker,
        )
        if fund_expense is not None:
            # fund_operations reports expense ratios as percentage values.
            # Example: 0.08 means 0.08%, so convert to decimal form (0.0008)
            # for screening and Excel percentage formatting.
            if fund_expense >= 0.01:
                fund_expense /= 100
            expense = fund_expense
            expense_source = "Funds data"

        fund_assets = fund_operation_value(
            operations,
            ["Total Net Assets", "Net Assets", "Total Assets"],
            ticker,
        )
        if assets is None and fund_assets is not None:
            # fund_operations may report net assets in millions.
            assets = fund_assets * 1_000_000 if fund_assets < 10_000_000 else fund_assets
            assets_source = "Funds data"

    except Exception as exc:
        print(f"  Warning: ETF fund data unavailable for {ticker}: {exc}")

    result = {
        "Expense Ratio": expense,
        "Total Assets": assets,
        "Expense Source": expense_source or "Unavailable",
        "Assets Source": assets_source or "Unavailable",
    }
    fund_cache[ticker] = result
    return result


def etf_rows(tickers, histories, cache, fund_cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"ETF {n}/{len(tickers)}: {ticker}")
        info = get_info(ticker, cache)
        p = price_metrics(histories.get(ticker))
        fund = get_etf_fund_metrics(ticker, info, fund_cache)
        expense = fund["Expense Ratio"]
        assets = fund["Total Assets"]

        expense_test = compare(expense, "lt", MAX_EXPENSE_RATIO)
        aum_test = compare(assets, "gt", MIN_AUM)
        above_50_test = p["Above SMA 50"]
        above_200_test = p["Above SMA 200"]
        golden_cross_test = p["SMA 50 > SMA 200"]
        data_complete = expense is not None and assets is not None
        trend_test = above_50_test and above_200_test and golden_cross_test
        passes = data_complete and expense_test and aum_test and trend_test

        tests = [expense_test, aum_test, above_50_test, above_200_test, golden_cross_test]
        failed_tests = []
        if expense is None:
            failed_tests.append("Expense ratio unavailable")
        elif not expense_test:
            failed_tests.append("Expense ratio too high")
        if assets is None:
            failed_tests.append("AUM unavailable")
        elif not aum_test:
            failed_tests.append("AUM below minimum")
        if not above_50_test:
            failed_tests.append("Below SMA 50")
        if not above_200_test:
            failed_tests.append("Below SMA 200")
        if not golden_cross_test:
            failed_tests.append("SMA 50 not above SMA 200")

        rows.append({
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName"),
            "Category": info.get("category"),
            **p,
            "Expense Ratio": expense,
            "Expense Source": fund["Expense Source"],
            "Total Assets": assets,
            "Assets Source": fund["Assets Source"],
            "Expense Test": expense_test,
            "AUM Test": aum_test,
            "Above SMA 50 Test": above_50_test,
            "Above SMA 200 Test": above_200_test,
            "Golden Cross Test": golden_cross_test,
            "Trend Test": trend_test,
            "Data Complete": data_complete,
            "Failed Tests": ", ".join(failed_tests) if failed_tests else None,
            "Yield": number(info.get("yield")),
            "3Y Average Return": number(info.get("threeYearAverageReturn")),
            "5Y Average Return": number(info.get("fiveYearAverageReturn")),
            "Score": sum(tests),
            "Max Score": len(tests),
            "Passes Screen": passes,
            "Error": None if info else "Data unavailable",
        })
    return rows


def heatmap_rows(tickers, histories, cache, dividend=False):
    rows = []
    for ticker in tickers:
        info = get_info(ticker, cache)
        p = price_metrics(histories.get(ticker))
        row = {
            "Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
            "Group": info.get("sector") or info.get("category") or "Unclassified",
            "Market Cap / Assets": number(info.get("marketCap") or info.get("totalAssets")) or 1,
            "Price": p["Price"], "Daily Change %": p["Daily Change %"],
            "1 Month Change %": p["1 Month Change %"], "SMA 50": p["SMA 50"],
            "SMA 200": p["SMA 200"], "Above SMA 50": p["Above SMA 50"],
            "Above SMA 200": p["Above SMA 200"], "Bullish Alignment": p["Bullish Alignment"],
        }
        if dividend:
            dividend_yield, payout_ratio = normalized_dividend_values(info)
            if dividend_yield is not None and dividend_yield > 0.25:
                continue
            row["Dividend Yield"] = dividend_yield
            row["Payout Ratio"] = payout_ratio
        rows.append(row)
    return rows


def sector_heatmap_rows(histories, cache):
    rows = []
    for sector, config in SECTOR_ETFS.items():
        ticker = config["Ticker"]
        print(f"Sector ETF: {ticker} ({sector})")
        info = get_info(ticker, cache)
        p = price_metrics(histories.get(ticker))
        rows.append({
            "Sector": sector, "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName") or sector,
            "Weight": config["Weight"], "Price": p["Price"],
            "Previous Close": p["Previous Close"], "Daily Change %": p["Daily Change %"],
            "1 Month Change %": p["1 Month Change %"], "SMA 50": p["SMA 50"],
            "SMA 200": p["SMA 200"], "Above SMA 50": p["Above SMA 50"],
            "Above SMA 200": p["Above SMA 200"], "Bullish Alignment": p["Bullish Alignment"],
        })
    return rows


def sort_frame(rows, columns, ascending):
    frame = pd.DataFrame(rows)
    return frame.sort_values(columns, ascending=ascending, na_position="last").reset_index(drop=True) if not frame.empty else frame


def market_colors():
    return [
        [0, "#8B0000"], [.25, "#D73027"], [.45, "#F4A6A6"],
        [.5, "#333333"], [.55, "#A7DCA7"], [.75, "#1A9850"], [1, "#006400"],
    ]


def create_treemap(frame, title, dividend=False):
    if frame.empty:
        return None
    chart = frame.copy()
    chart["Market Cap / Assets"] = pd.to_numeric(chart["Market Cap / Assets"], errors="coerce").fillna(1).clip(lower=1)
    chart["1 Month Change %"] = pd.to_numeric(chart["1 Month Change %"], errors="coerce")
    chart = chart.dropna(subset=["1 Month Change %"])
    if chart.empty:
        return None
    chart["Group"] = chart["Group"].fillna("Unclassified")
    chart["Name"] = chart["Name"].fillna(chart["Ticker"])
    hover = ["Name", "Price", "SMA 50", "SMA 200", "Bullish Alignment"]
    if dividend:
        hover += ["Dividend Yield", "Payout Ratio"]
    fig = px.treemap(
        chart, path=[px.Constant("Market"), "Group", "Ticker"], values="Market Cap / Assets",
        color="1 Month Change %", color_continuous_midpoint=0,
        color_continuous_scale=market_colors(), custom_data=hover, title=title,
    )
    labels = [f"{number(v):+.2%}" if number(v) is not None else "" for v in fig.data[0].marker.colors]
    hover_template = (
        "<b>%{label}</b><br>%{customdata[0]}<br>1 Month Change: %{color:+.2%}<br>"
        "Price: $%{customdata[1]:,.2f}<br>SMA 50: $%{customdata[2]:,.2f}<br>"
        "SMA 200: $%{customdata[3]:,.2f}<br>Bullish Alignment: %{customdata[4]}"
    )
    if dividend:
        hover_template += "<br>Dividend Yield: %{customdata[5]:.2%}<br>Payout Ratio: %{customdata[6]:.1%}"
    hover_template += "<extra></extra>"
    fig.update_traces(
        text=labels, texttemplate="<b>%{label}</b><br>%{text}", hovertemplate=hover_template,
        marker=dict(line=dict(width=1, color="#202020")), root_color="#101820",
    )
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#101820", plot_bgcolor="#101820",
        margin=dict(t=55, l=8, r=8, b=8),
        coloraxis_colorbar=dict(title="1 Month Change", tickformat="+.1%"),
    )
    return fig


def create_sector_treemap(frame):
    if frame.empty:
        return None
    chart = frame.copy()
    chart["1 Month Change %"] = pd.to_numeric(chart["1 Month Change %"], errors="coerce")
    chart["Weight"] = pd.to_numeric(chart["Weight"], errors="coerce").fillna(1).clip(lower=1)
    chart = chart.dropna(subset=["1 Month Change %"])
    if chart.empty:
        return None
    fig = px.treemap(
        chart, path=[px.Constant("U.S. Sectors"), "Sector", "Ticker"], values="Weight",
        color="1 Month Change %", color_continuous_midpoint=0,
        color_continuous_scale=market_colors(),
        custom_data=["Name", "Price", "Previous Close", "Daily Change %", "SMA 50", "SMA 200", "Bullish Alignment"],
        title="U.S. Sector ETF One-Month Heatmap",
    )
    labels = [f"{number(v):+.2%}" if number(v) is not None else "" for v in fig.data[0].marker.colors]
    fig.update_traces(
        text=labels, texttemplate="<b>%{label}</b><br>%{text}",
        hovertemplate=(
            "<b>%{label}</b><br>%{customdata[0]}<br>1 Month Change: %{color:+.2%}<br>"
            "Daily Change: %{customdata[3]:+.2%}<br>Price: $%{customdata[1]:,.2f}<br>"
            "Previous Close: $%{customdata[2]:,.2f}<br>SMA 50: $%{customdata[4]:,.2f}<br>"
            "SMA 200: $%{customdata[5]:,.2f}<br>Bullish Alignment: %{customdata[6]}<extra></extra>"
        ),
        marker=dict(line=dict(width=2, color="#202020")), root_color="#101820",
    )
    fig.update_layout(
        template="plotly_dark", paper_bgcolor="#101820", plot_bgcolor="#101820",
        margin=dict(t=55, l=8, r=8, b=8),
        coloraxis_colorbar=dict(title="1 Month Change", tickformat="+.1%"),
    )
    return fig


def create_html(path, frames, figures):
    def count(frame, column):
        return int(frame[column].fillna(False).sum()) if not frame.empty and column in frame else 0

    stocks = frames["Stock Screener"]
    dividends = frames["Dividend Screener"]
    etfs = frames["ETF Screener"]
    cards = [
        ("Stocks Screened", len(stocks)), ("Stocks Passing", count(stocks, "Passes Screen")),
        ("Dividend Stocks Passing", count(dividends, "Passes Screen")),
        ("ETFs Passing", count(etfs, "Passes Screen")),
        ("Stock Bullish Alignments", count(stocks, "Bullish Alignment")),
        ("Dividend Bullish Alignments", count(dividends, "Bullish Alignment")),
        ("ETF Bullish Alignments", count(etfs, "Bullish Alignment")),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="value">{value:,}</div><div class="label">{label}</div></div>'
        for label, value in cards
    )
    chart_html = []
    for index, (name, figure) in enumerate(figures):
        content = figure.to_html(full_html=False, include_plotlyjs="inline" if index == 0 else False) if figure else f"<p>No {name} data.</p>"
        chart_html.append(f'<section class="chart">{content}</section>')
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Investment Dashboard</title>
<style>body{{margin:0;background:#0b1220;color:#fff;font-family:Segoe UI,Arial}}header{{padding:24px 32px;background:#13233d}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;padding:22px 32px}}.card{{background:#172941;border-radius:14px;padding:18px}}.value{{font-size:30px;font-weight:700;color:#7fd1ff}}.label{{color:#c8d3e3}}.chart{{margin:0 22px 24px;background:#101820;border-radius:14px;overflow:hidden}}</style>
</head><body><header><h1>Investment Dashboard</h1><div>Market heatmaps, updated {now}</div></header><section class="cards">{cards_html}</section>{''.join(chart_html)}</body></html>"""
    path.write_text(html, encoding="utf-8")


def export_assets(folder, frames):
    figures = [
        ("S&P 100", create_treemap(frames["Stock Heatmap Data"], "S&P 100 One-Month Heatmap")),
        ("Dividend", create_treemap(frames["Dividend Heatmap Data"], "Dividend Stock One-Month Heatmap", True)),
        ("ETF", create_treemap(frames["ETF Heatmap Data"], "ETF One-Month Heatmap")),
        ("Sector ETF", create_sector_treemap(frames["Sector Heatmap Data"])),
    ]
    exports = [
        ("S&P 100 Map", figures[0][1], "sp100_heatmap.png"),
        ("Dividend Map", figures[1][1], "dividend_heatmap.png"),
        ("ETF Map", figures[2][1], "etf_heatmap.png"),
        ("Sector Map", figures[3][1], "sector_heatmap.png"),
    ]
    images = {}
    for map_name, fig, filename in exports:
        if fig:
            try:
                image_path = folder / filename
                fig.write_image(image_path, width=1800, height=1000)
                images[map_name] = image_path
            except Exception as exc:
                print(f"Warning: PNG export failed for {map_name}: {exc}")
    create_html(folder / HTML_NAME, frames, figures)
    return images


def write_dataframe(workbook, name, frame):
    if name in workbook.sheetnames:
        del workbook[name]
    ws = workbook.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"
    if frame.empty:
        ws["A1"] = "No results"
        return
    ws.append(list(frame.columns))
    for row in frame.itertuples(index=False, name=None):
        ws.append(list(row))
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")
    ws.auto_filter.ref = ws.dimensions
    headers = {cell.value: cell.column for cell in ws[1]}
    percentages = {
        "Daily Change %", "1 Month Change %", "% From 52W High", "Upside %", "Return On Equity",
        "Profit Margin", "Revenue Growth", "Earnings Growth", "Dividend Yield", "5Y Avg Dividend Yield",
        "Payout Ratio", "Expense Ratio", "Yield", "3Y Average Return", "5Y Average Return",
    }
    currencies = {"Price", "Previous Close", "SMA 50", "SMA 200", "52 Week High", "Target Price"}
    integers = {"Free Cash Flow", "Total Assets", "Market Cap / Assets"}
    for header, col in headers.items():
        fmt = "0.0%;[Red](0.0%);-" if header in percentages else "$#,##0.00;[Red]($#,##0.00);-" if header in currencies else "#,##0;[Red](#,##0);-" if header in integers else None
        if fmt:
            for cells in ws.iter_cols(min_col=col, max_col=col, min_row=2):
                for cell in cells:
                    cell.number_format = fmt
    for change_header in ("Daily Change %", "1 Month Change %"):
        if change_header in headers:
            letter = get_column_letter(headers[change_header])
            ws.conditional_formatting.add(
                f"{letter}2:{letter}{ws.max_row}",
                ColorScaleRule(start_type="min", start_color="F8696B", mid_type="num", mid_value=0,
                               mid_color="FFEB84", end_type="max", end_color="63BE7B"),
            )
    for cells in ws.columns:
        values = [str(cell.value or "") for cell in cells[:200]]
        ws.column_dimensions[get_column_letter(cells[0].column)].width = min(max(max(map(len, values), default=0) + 2, 11), 32)


def insert_map(workbook, name, image_path, html_path):
    if name in workbook.sheetnames:
        del workbook[name]
    ws = workbook.create_sheet(name)
    ws.sheet_view.showGridLines = False
    ws["A1"] = name
    ws["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="17365D")
    ws.merge_cells("A1:H1")
    ws["A2"] = "Open interactive dashboard"
    ws["A2"].hyperlink = html_path.resolve().as_uri()
    ws["A2"].style = "Hyperlink"
    if image_path and image_path.exists():
        image = XLImage(str(image_path))
        image.width = 1350
        image.height = 750
        ws.add_image(image, "A4")
    else:
        ws["A4"] = "Static image unavailable. Use the interactive dashboard link above."


def save_workbook(path, frames, images):
    wb = load_workbook(path)
    for name in [
        "Stock Screener", "Dividend Screener", "ETF Screener", "Stock Heatmap Data",
        "Dividend Heatmap Data", "ETF Heatmap Data", "Sector Heatmap Data",
    ]:
        write_dataframe(wb, name, frames[name])
    html_path = path.parent / HTML_NAME
    for name in ["S&P 100 Map", "Dividend Map", "ETF Map", "Sector Map"]:
        insert_map(wb, name, images.get(name), html_path)
    if "Dashboard" in wb.sheetnames:
        del wb["Dashboard"]
    ws = wb.create_sheet("Dashboard", 0)
    ws.sheet_view.showGridLines = False
    ws["A1"] = "Investment Screening Dashboard"
    ws["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="17365D")
    ws.merge_cells("A1:D1")
    ws.append(["Last Refresh", datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")])
    ws.append([])
    ws.append(["Section", "Tickers", "Passing", "Strong Uptrends"])
    for label, key in [("Stocks", "Stock Screener"), ("Dividends", "Dividend Screener"), ("ETFs", "ETF Screener")]:
        frame = frames[key]
        passing = int(frame["Passes Screen"].fillna(False).sum()) if not frame.empty else 0
        bullish = int(frame["Bullish Alignment"].fillna(False).sum()) if not frame.empty else 0
        ws.append([label, len(frame), passing, bullish])
    sector_frame = frames["Sector Heatmap Data"]
    sector_bullish = int(sector_frame["Bullish Alignment"].fillna(False).sum()) if not sector_frame.empty else 0
    ws.append(["Sector ETFs", len(sector_frame), "", sector_bullish])
    ws["A10"] = "Open interactive market dashboard"
    ws["A10"].hyperlink = html_path.resolve().as_uri()
    ws["A10"].style = "Hyperlink"
    for cell in ws[4]:
        cell.fill = PatternFill("solid", fgColor="5B9BD5")
        cell.font = Font(color="FFFFFF", bold=True)
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.save(path)


def main():
    folder = Path(__file__).resolve().parent
    workbook_path = folder / WORKBOOK_NAME
    if not workbook_path.exists():
        create_starter(workbook_path)
        print(f"Created {workbook_path}. Add tickers and run again.")
        return
    lists = read_tickers(workbook_path)
    sector_tickers = [config["Ticker"] for config in SECTOR_ETFS.values()]
    all_tickers = list(dict.fromkeys(
        lists["stocks"] + lists["dividends"] + lists["etfs"] + lists["sp100"] + sector_tickers
    ))
    if not all_tickers:
        print("No tickers found.")
        return
    print(f"Downloading history for {len(all_tickers)} tickers...")
    histories = download_history(all_tickers)
    cache = {}
    fund_cache = {}
    frames = {
        "Stock Screener": sort_frame(stock_rows(lists["stocks"], histories, cache), ["Passes Screen", "Score", "Ticker"], [False, False, True]),
        "Dividend Screener": sort_frame(dividend_rows(lists["dividends"], histories, cache), ["Passes Screen", "Score", "Dividend Yield"], [False, False, False]),
        "ETF Screener": sort_frame(etf_rows(lists["etfs"], histories, cache, fund_cache), ["Passes Screen", "Score", "Ticker"], [False, False, True]),
        "Stock Heatmap Data": sort_frame(heatmap_rows(lists["sp100"], histories, cache), ["Group", "1 Month Change %"], [True, False]),
        "Dividend Heatmap Data": sort_frame(heatmap_rows(lists["dividends"], histories, cache, True), ["Group", "1 Month Change %"], [True, False]),
        "ETF Heatmap Data": sort_frame(heatmap_rows(lists["etfs"], histories, cache), ["Group", "1 Month Change %"], [True, False]),
        "Sector Heatmap Data": sort_frame(sector_heatmap_rows(histories, cache), ["Daily Change %", "Sector"], [False, True]),
    }
    images = export_assets(folder, frames)
    save_workbook(workbook_path, frames, images)
    print(f"Updated workbook: {workbook_path}")
    print(f"Interactive dashboard: {folder / HTML_NAME}")


if __name__ == "__main__":
    main()

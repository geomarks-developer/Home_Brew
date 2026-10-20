from __future__ import annotations

import math
import time
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
from openpyxl.styles import PatternFill
from openpyxl.styles import Border, Side
import textwrap
import pickle

WORKBOOK_NAME = "Combo_Analysis.xlsx"
TICKERS_SHEET = "Tickers"
HTML_NAME = "investment_dashboard.html"
MONTH_LOOKBACK = 21
MAX_PEG, MAX_FORWARD_PE = 2.5, 30.0
MIN_ROE, MIN_MARGIN = 0.05, 0.05
MAX_DEBT_EQUITY, MIN_UPSIDE = 150.0, 0.0
MIN_DIVIDEND_YIELD, MAX_PAYOUT = 0.02, 0.70
MAX_EXPENSE_RATIO, MIN_AUM = 0.005, 500_000_000
MIN_RSI, MAX_RSI = 40.0, 70.0
PAUSE = 0.05

SECTOR_ETFS = {
    "Communication Services": "XLC", "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP", "Energy": "XLE", "Financials": "XLF",
    "Health Care": "XLV", "Industrials": "XLI", "Materials": "XLB",
    "Real Estate": "XLRE", "Technology": "XLK", "Utilities": "XLU",
}

# ---------------------------------------------------------
# Utility functions
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Starter workbook creation
# ---------------------------------------------------------

def create_starter(path):
    wb = Workbook()
    ws = wb.active
    ws.title = TICKERS_SHEET
    ws.append(["Stock", "Dividend", "ETF", "S&P 100", "Profiles"])
    ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
    for col in range(1, 6):
        ws.column_dimensions[get_column_letter(col)].width = 18
    wb.save(path)


# ---------------------------------------------------------
# Read tickers
# ---------------------------------------------------------

def read_tickers(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    if TICKERS_SHEET not in wb.sheetnames:
        raise KeyError('The workbook needs a sheet named "Tickers".')
    ws = wb[TICKERS_SHEET]
    result = {}
    for name, col in {"stocks": 1, "dividends": 2, "etfs": 3, "sp100": 4, "profiles": 5}.items():
        values = [normalize_ticker(ws.cell(row, col).value) for row in range(2, ws.max_row + 1)]
        result[name] = list(dict.fromkeys(v for v in values if v))
    wb.close()
    return result


# ---------------------------------------------------------
# Download history
# ---------------------------------------------------------

def download_history(tickers):
    if not tickers:
        return {}
    data = yf.download(
        tickers,
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
    result = {}
    for ticker in tickers:
        try:
            frame = data[ticker].copy().dropna(how="all")
            if not frame.empty:
                result[ticker] = frame
        except (KeyError, TypeError):
            pass
    return result


# ---------------------------------------------------------
# Price metrics
# ---------------------------------------------------------

def price_metrics(history):
    blank = {
        "Price": None, "Previous Close": None, "Daily Change %": None,
        "1 Month Change %": None, "SMA 50": None, "SMA 200": None,
        "Above SMA 50": False, "Above SMA 200": False,
        "SMA 50 > SMA 200": False, "Bullish Alignment": False,
        "52 Week High": None, "% From 52W High": None,
        "RSI": None, "MACD": None, "MACD Signal": None,
        "MACD Histogram": None, "RSI Test": False, "MACD Test": False,
    }
    if history is None or history.empty:
        return blank
    column = "Adj Close" if "Adj Close" in history.columns else "Close"
    close = pd.to_numeric(history[column], errors="coerce").dropna()
    if close.empty:
        return blank

    price = number(close.iloc[-1])
    previous = number(close.iloc[-2]) if len(close) >= 2 else None
    month_base = number(close.iloc[-(MONTH_LOOKBACK + 1)]) if len(close) > MONTH_LOOKBACK else None
    sma50 = number(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma200 = number(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    high = number(close.max())
    above50 = price is not None and sma50 is not None and price > sma50
    above200 = price is not None and sma200 is not None and price > sma200
    cross = sma50 is not None and sma200 is not None and sma50 > sma200

    rsi = None
    if len(close) >= 15:
        delta = close.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0, float("nan"))
        latest = (100 - 100 / (1 + rs)).iloc[-1]
        if pd.notna(latest):
            rsi = number(latest)
        if rsi is None:
            g, loss_value = number(avg_gain.iloc[-1]), number(avg_loss.iloc[-1])
            if g is not None and g > 0 and loss_value == 0:
                rsi = 100.0
            elif g == 0 and loss_value is not None and loss_value > 0:
                rsi = 0.0

    macd = signal = histogram = None
    if len(close) >= 34:
        ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
        macd_series = ema12 - ema26
        signal_series = macd_series.ewm(span=9, adjust=False, min_periods=9).mean()
        macd, signal = number(macd_series.iloc[-1]), number(signal_series.iloc[-1])
        histogram = number((macd_series - signal_series).iloc[-1])

    rsi_test = rsi is not None and MIN_RSI <= rsi <= MAX_RSI
    macd_test = macd is not None and signal is not None and macd > signal

    return {
        "Price": price, "Previous Close": previous,
        "Daily Change %": price / previous - 1 if price is not None and previous not in (None, 0) else None,
        "1 Month Change %": price / month_base - 1 if price is not None and month_base not in (None, 0) else None,
        "SMA 50": sma50, "SMA 200": sma200, "Above SMA 50": above50,
        "Above SMA 200": above200, "SMA 50 > SMA 200": cross,
        "Bullish Alignment": above50 and above200 and cross,
        "52 Week High": high,
        "% From 52W High": price / high - 1 if price is not None and high not in (None, 0) else None,
        "RSI": rsi, "MACD": macd, "MACD Signal": signal,
        "MACD Histogram": histogram, "RSI Test": rsi_test, "MACD Test": macd_test,
    }


# ---------------------------------------------------------
# Momentum scoring
# ---------------------------------------------------------

def momentum_scores(metrics):
    rsi, macd, signal = number(metrics.get("RSI")), number(metrics.get("MACD")), number(metrics.get("MACD Signal"))
    rsi_score = 2 if rsi is not None and 50 <= rsi <= MAX_RSI else 1 if rsi is not None and MIN_RSI <= rsi < 50 else 0
    macd_score = int(macd is not None and signal is not None and macd > signal)
    return rsi_score, macd_score, rsi_score + macd_score


# ---------------------------------------------------------
# Info caching
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# Dividend normalization
# ---------------------------------------------------------

def normalized_dividend_values(info):
    dividend_yield, payout = number(info.get("dividendYield")), number(info.get("payoutRatio"))
    if dividend_yield is not None and dividend_yield > 1:
        dividend_yield /= 100
    if payout is not None and payout > 1:
        payout /= 100
    return dividend_yield, payout


# ---------------------------------------------------------
# Momentum failure logging
# ---------------------------------------------------------

def momentum_failures(failed, p):
    if p["RSI"] is None:
        failed.append("RSI unavailable")
    elif p["RSI"] < MIN_RSI:
        failed.append(f"RSI below {MIN_RSI:g}")
    elif p["RSI"] > MAX_RSI:
        failed.append(f"RSI above {MAX_RSI:g}")
    if p["MACD"] is None or p["MACD Signal"] is None:
        failed.append("MACD unavailable")
    elif not p["MACD Test"]:
        failed.append("MACD not above signal")


# ---------------------------------------------------------
# Stock screener rows
# ---------------------------------------------------------

def stock_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"Stock {n}/{len(tickers)}: {ticker}")
        info, p = get_info(ticker, cache), price_metrics(histories.get(ticker))
        rsi_score, macd_score, momentum_score = momentum_scores(p)
        target = number(info.get("targetMeanPrice"))
        current = p["Price"] or number(info.get("currentPrice"))
        upside = target / current - 1 if target is not None and current not in (None, 0) else None
        values = {
            "PEG": number(info.get("pegRatio") or info.get("trailingPegRatio")),
            "Forward PE": number(info.get("forwardPE")),
            "Return On Equity": number(info.get("returnOnEquity")),
            "Profit Margin": number(info.get("profitMargins")),
            "Revenue Growth": number(info.get("revenueGrowth")),
            "Earnings Growth": number(info.get("earningsGrowth")),
            "Debt To Equity": number(info.get("debtToEquity")),
            "Upside %": upside,
        }
        specs = [
            ("PEG", "lt", MAX_PEG, "PEG unavailable", "PEG too high"),
            ("Forward PE", "lt", MAX_FORWARD_PE, "Forward PE unavailable", "Forward PE too high"),
            ("Return On Equity", "gt", MIN_ROE, "ROE unavailable", "ROE too low"),
            ("Profit Margin", "gt", MIN_MARGIN, "Profit margin unavailable", "Profit margin too low"),
            ("Revenue Growth", "gt", 0, "Revenue growth unavailable", "Revenue growth not positive"),
            ("Earnings Growth", "gt", 0, "Earnings growth unavailable", "Earnings growth not positive"),
            ("Debt To Equity", "lt", MAX_DEBT_EQUITY, "Debt to equity unavailable", "Debt to equity too high"),
            ("Upside %", "gt", MIN_UPSIDE, "Target upside unavailable", "Target upside not positive"),
        ]
        tests, failed = {}, []
        for key, op, limit, unavailable, message in specs:
            passed = compare(values[key], op, limit)
            tests[key] = passed
            if values[key] is None:
                failed.append(unavailable)
            elif not passed:
                failed.append(message)
        above50, above200, golden = p["Above SMA 50"], p["Above SMA 200"], p["SMA 50 > SMA 200"]
        if not above50:
            failed.append("Below SMA 50")
        if not above200:
            failed.append("Below SMA 200")
        if not golden:
            failed.append("SMA 50 not above SMA 200")
        momentum_failures(failed, p)
        base_tests = list(tests.values()) + [above50, above200, golden]
        base_score, max_score = sum(base_tests), len(base_tests) + 3
        total_score = base_score + momentum_score
        rows.append({
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName"),
            "Sector": info.get("sector"),
            "Industry": info.get("industry"),
            **p,
            "Target Price": target,
            **values,
            "Free Cash Flow": number(info.get("freeCashflow")),
            **{f"{key} Test": passed for key, passed in tests.items()},
            "Above SMA 50 Test": above50,
            "Above SMA 200 Test": above200,
            "Golden Cross Test": golden,
            "Trend Test": above50 and above200 and golden,
            "RSI Range Test": p["RSI Test"],
            "MACD Above Signal Test": p["MACD Test"],
            "Momentum Test": p["RSI Test"] and p["MACD Test"],
            "Base Score": base_score,
            "RSI Score": rsi_score,
            "MACD Score": macd_score,
            "Momentum Score": momentum_score,
            "Failed Tests": ", ".join(failed) if failed else None,
            "Score": total_score,
            "Max Score": max_score,
            "Score %": total_score / max_score if max_score else None,
            "Passes Screen": all(tests.values()) and above200 and momentum_score >= 2,
            "Error": None if info else "Data unavailable",
        })
    return rows


# ---------------------------------------------------------
# Dividend screener rows
# ---------------------------------------------------------

def dividend_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"Dividend {n}/{len(tickers)}: {ticker}")
        info, p = get_info(ticker, cache), price_metrics(histories.get(ticker))
        rsi_score, macd_score, momentum_score = momentum_scores(p)
        dividend_yield, payout = normalized_dividend_values(info)
        if dividend_yield is not None and dividend_yield > 0.25:
            continue
        cash_flow, debt = number(info.get("freeCashflow")), number(info.get("debtToEquity"))
        average_yield = number(info.get("fiveYearAvgDividendYield"))
        test_values = [
            (dividend_yield, compare(dividend_yield, "gt", MIN_DIVIDEND_YIELD), "Dividend yield unavailable", "Dividend yield below minimum"),
            (payout, compare(payout, "lt", MAX_PAYOUT), "Payout ratio unavailable", "Payout ratio too high"),
            (cash_flow, cash_flow is not None and cash_flow > 0, "Free cash flow unavailable", "Free cash flow not positive"),
            (debt, compare(debt, "lt", MAX_DEBT_EQUITY), "Debt to equity unavailable", "Debt to equity too high"),
        ]
        core_tests = [x[1] for x in test_values]
        failed = [x[2] if x[0] is None else x[3] for x in test_values if x[0] is None or not x[1]]
        above50, above200, golden = p["Above SMA 50"], p["Above SMA 200"], p["SMA 50 > SMA 200"]
        if not above50:
            failed.append("Below SMA 50")
        if not above200:
            failed.append("Below SMA 200")
        if not golden:
            failed.append("SMA 50 not above SMA 200")
        momentum_failures(failed, p)
        base_tests = core_tests + [above50, above200, golden]
        base_score, max_score = sum(base_tests), len(base_tests) + 3
        total_score = base_score + momentum_score
        rows.append({
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName"),
            "Sector": info.get("sector"),
            **p,
            "Dividend Yield": dividend_yield,
            "5Y Avg Dividend Yield": average_yield / 100 if average_yield is not None else None,
            "Payout Ratio": payout,
            "Free Cash Flow": cash_flow,
            "Debt To Equity": debt,
            "Dividend Yield Test": core_tests[0],
            "Payout Ratio Test": core_tests[1],
            "Free Cash Flow Test": core_tests[2],
            "Debt To Equity Test": core_tests[3],
            "Above SMA 50 Test": above50,
            "Above SMA 200 Test": above200,
            "Golden Cross Test": golden,
            "Trend Test": above50 and above200 and golden,
            "RSI Range Test": p["RSI Test"],
            "MACD Above Signal Test": p["MACD Test"],
            "Momentum Test": p["RSI Test"] and p["MACD Test"],
            "Base Score": base_score,
            "RSI Score": rsi_score,
            "MACD Score": macd_score,
            "Momentum Score": momentum_score,
            "Failed Tests": ", ".join(failed) if failed else None,
            "Score": total_score,
            "Max Score": max_score,
            "Score %": total_score / max_score if max_score else None,
            "Passes Screen": all(core_tests) and above200 and momentum_score >= 2,
            "Error": None if info else "Data unavailable",
        })
    return rows


# ---------------------------------------------------------
# ETF metrics and rows
# ---------------------------------------------------------

def get_etf_metrics(ticker, info, cache):
    if ticker in cache:
        return cache[ticker]
    expense = number(info.get("annualReportExpenseRatio") or info.get("netExpenseRatio"))
    if expense is not None:
        expense = expense / 100
    assets = number(info.get("totalAssets"))
    cache[ticker] = {"Expense Ratio": expense, "Total Assets": assets}
    return cache[ticker]


def etf_rows(tickers, histories, cache, fund_cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"ETF {n}/{len(tickers)}: {ticker}")
        info, p = get_info(ticker, cache), price_metrics(histories.get(ticker))
        fund = get_etf_metrics(ticker, info, fund_cache)
        expense, assets = fund["Expense Ratio"], fund["Total Assets"]
        tests = [
            compare(expense, "lt", MAX_EXPENSE_RATIO),
            compare(assets, "gt", MIN_AUM),
            p["Above SMA 50"],
            p["Above SMA 200"],
            p["SMA 50 > SMA 200"],
        ]
        failed = []
        if expense is None:
            failed.append("Expense ratio unavailable")
        elif not tests[0]:
            failed.append("Expense ratio too high")
        if assets is None:
            failed.append("AUM unavailable")
        elif not tests[1]:
            failed.append("AUM below minimum")
        if not tests[2]:
            failed.append("Below SMA 50")
        if not tests[3]:
            failed.append("Below SMA 200")
        if not tests[4]:
            failed.append("SMA 50 not above SMA 200")
        rows.append({
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName"),
            "Category": info.get("category"),
            **p,
            "Expense Ratio": expense,
            "Total Assets": assets,
            "Expense Test": tests[0],
            "AUM Test": tests[1],
            "Trend Test": all(tests[2:]),
            "Failed Tests": ", ".join(failed) if failed else None,
            "Yield": number(info.get("yield")),
            "3Y Average Return": number(info.get("threeYearAverageReturn")),
            "5Y Average Return": number(info.get("fiveYearAverageReturn")),
            "Score": sum(tests),
            "Max Score": len(tests),
            "Passes Screen": all(tests),
            "Error": None if info else "Data unavailable",
        })
    return rows


# ---------------------------------------------------------
# Heatmap rows
# ---------------------------------------------------------

def heatmap_rows(tickers, histories, cache, dividend=False):
    rows = []
    for ticker in tickers:
        info, p = get_info(ticker, cache), price_metrics(histories.get(ticker))
        row = {
            "Ticker": ticker,
            "Name": info.get("shortName") or info.get("longName"),
            "Group": info.get("sector") or info.get("category") or "Unclassified",
            "Market Cap / Assets": number(info.get("marketCap") or info.get("totalAssets")) or 1,
            "Price": p["Price"],
            "Previous Close": p["Previous Close"],
            "Daily Change %": p["Daily Change %"],
            "1 Month Change %": p["1 Month Change %"],
            "SMA 50": p["SMA 50"],
            "SMA 200": p["SMA 200"],
            "Bullish Alignment": p["Bullish Alignment"],
        }
        if dividend:
            dy, pr = normalized_dividend_values(info)
            row["Dividend Yield"], row["Payout Ratio"] = dy, pr
        rows.append(row)
    return rows


def sector_heatmap_rows(histories, cache):
    rows = []
    for sector, ticker in SECTOR_ETFS.items():
        info, p = get_info(ticker, cache), price_metrics(histories.get(ticker))
        rows.append({
            "Sector": sector,
            "Ticker": ticker,
            "Name": info.get("shortName") or sector,
            "Weight": 1,
            "Price": p["Price"],
            "Previous Close": p["Previous Close"],
            "Daily Change %": p["Daily Change %"],
            "1 Month Change %": p["1 Month Change %"],
            "SMA 50": p["SMA 50"],
            "SMA 200": p["SMA 200"],
            "Bullish Alignment": p["Bullish Alignment"],
        })
    return rows


# ---------------------------------------------------------
# Sorting helper
# ---------------------------------------------------------

def sort_frame(rows, columns, ascending):
    frame = pd.DataFrame(rows)
    return frame.sort_values(columns, ascending=ascending, na_position="last").reset_index(drop=True) if not frame.empty else frame

# ---------------------------------------------------------
# Treemap creation
# ---------------------------------------------------------

def create_treemap(frame, title, sector=False):
    if frame.empty:
        return None

    chart = frame.copy()
    value_col = "Weight" if sector else "Market Cap / Assets"
    group_col = "Sector" if sector else "Group"

    chart[value_col] = pd.to_numeric(chart[value_col], errors="coerce").fillna(1).clip(lower=1)
    chart["1 Month Change %"] = pd.to_numeric(chart["1 Month Change %"], errors="coerce")
    chart = chart.dropna(subset=["1 Month Change %"])
    if chart.empty:
        return None

    formats = {
        "Name": True,
        "Price": ":$,.2f",
        "Previous Close": ":$,.2f",
        "Daily Change %": ":+.2%",
        "1 Month Change %": ":+.2%",
        "SMA 50": ":$,.2f",
        "SMA 200": ":$,.2f",
        "Bullish Alignment": True,
        "Dividend Yield": ":.2%",
        "Payout Ratio": ":.1%",
    }
    hover_data = {k: v for k, v in formats.items() if k in chart.columns}

    fig = px.treemap(
        chart,
        path=[px.Constant("Market"), group_col, "Ticker"],
        values=value_col,
        color="1 Month Change %",
        color_continuous_midpoint=0,
        color_continuous_scale=[
            [0, "#8B0000"],
            [.25, "#D73027"],
            [.45, "#F4A6A6"],
            [.5, "#333333"],
            [.55, "#A7DCA7"],
            [.75, "#1A9850"],
            [1, "#006400"],
        ],
        hover_data=hover_data,
        title=title,
    )

    labels = [
        f"{number(v):+.2%}" if number(v) is not None else ""
        for v in fig.data[0].marker.colors
    ]

    fig.update_traces(
        text=labels,
        texttemplate="<b>%{label}</b><br>%{text}",
        marker=dict(line=dict(width=1, color="#202020")),
        root_color="#101820",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#101820",
        plot_bgcolor="#101820",
        margin=dict(t=55, l=8, r=8, b=8),
        coloraxis_colorbar=dict(title="1 Month Change", tickformat="+.1%"),
    )

    return fig


# ---------------------------------------------------------
# Export PNGs + HTML dashboard
# ---------------------------------------------------------

def export_assets(folder, frames):
    figures = [
        ("S&P 100 Map", create_treemap(frames["Stock Heatmap Data"], "S&P 100 One-Month Heatmap"), "sp100_heatmap.png"),
        ("Dividend Map", create_treemap(frames["Dividend Heatmap Data"], "Dividend Stock One-Month Heatmap"), "dividend_heatmap.png"),
        ("ETF Map", create_treemap(frames["ETF Heatmap Data"], "ETF One-Month Heatmap"), "etf_heatmap.png"),
        ("Sector Map", create_treemap(frames["Sector Heatmap Data"], "U.S. Sector ETF One-Month Heatmap", True), "sector_heatmap.png"),
    ]

    images = {}
    html_parts = []

    for index, (name, fig, filename) in enumerate(figures):
        if fig:
            html_parts.append(
                fig.to_html(
                    full_html=False,
                    include_plotlyjs="inline" if index == 0 else False
                )
            )
            try:
                image_path = folder / filename
                fig.write_image(image_path, width=1800, height=1000)
                images[name] = image_path
            except Exception as exc:
                print(f"Warning: PNG export failed for {name}: {exc}")

    html = (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Investment Dashboard</title></head>"
        "<body style='background:#101820;color:white'>"
        + "".join(html_parts)
        + "</body></html>"
    )

    (folder / HTML_NAME).write_text(html, encoding="utf-8")
    return images


# ---------------------------------------------------------
# Write DataFrame to Excel sheet
# ---------------------------------------------------------

def write_dataframe(workbook, name, frame):
    if name in workbook.sheetnames:
        del workbook[name]

    ws = workbook.create_sheet(name)
    ws.freeze_panes = "A2"
    ws.sheet_view.showGridLines = False

    if frame.empty:
        ws["A1"] = "No results"
        return

    ws.append(list(frame.columns))
    for row in frame.itertuples(index=False, name=None):
        ws.append(list(row))

    # Header formatting
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")

    ws.auto_filter.ref = ws.dimensions

    headers = {cell.value: cell.column for cell in ws[1]}

    percentages = {
        "Daily Change %", "1 Month Change %", "% From 52W High", "Upside %",
        "Return On Equity", "Profit Margin", "Revenue Growth", "Earnings Growth",
        "Dividend Yield", "5Y Avg Dividend Yield", "Payout Ratio",
        "Expense Ratio", "Yield", "3Y Average Return", "5Y Average Return",
        "Score %",
    }

    currencies = {
        "Price", "Previous Close", "SMA 50", "SMA 200",
        "52 Week High", "Target Price",
    }

    # Apply number formats
    for header, col in headers.items():
        fmt = (
            "0.0%" if header in percentages
            else "$#,##0.00" if header in currencies
            else None
        )
        if fmt:
            for cell in list(ws.columns)[col - 1][1:]:
                cell.number_format = fmt

    # Conditional formatting
    for header in ("Daily Change %", "1 Month Change %"):
        if header in headers:
            letter = get_column_letter(headers[header])
            ws.conditional_formatting.add(
                f"{letter}2:{letter}{ws.max_row}",
                ColorScaleRule(
                    start_type="min", start_color="F8696B",
                    mid_type="num", mid_value=0, mid_color="FFEB84",
                    end_type="max", end_color="63BE7B",
                ),
            )

    # Column width auto-fit
    for cells in ws.columns:
        ws.column_dimensions[get_column_letter(cells[0].column)].width = min(
            max(max(len(str(c.value or "")) for c in cells[:200]) + 2, 11),
            32,
        )


# ---------------------------------------------------------
# Insert heatmap PNG + link to HTML dashboard
# ---------------------------------------------------------

def insert_map(workbook, name, image_path, html_path):
    if name in workbook.sheetnames:
        del workbook[name]

    ws = workbook.create_sheet(name)
    ws["A1"] = name
    ws["A2"] = "Open interactive dashboard"
    ws["A2"].hyperlink = html_path.resolve().as_uri()
    ws["A2"].style = "Hyperlink"

    if image_path and image_path.exists():
        image = XLImage(str(image_path))
        image.width = 1350
        image.height = 750
        ws.add_image(image, "A4")


# ---------------------------------------------------------
# Methodology sheet
# ---------------------------------------------------------

def add_methodology_sheet(workbook):
    name = "Test Methodology"
    if name in workbook.sheetnames:
        del workbook[name]

    ws = workbook.create_sheet(name, 1)
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A5"

    ws["A1"] = "Screening Tests, Methodology & Indicator Glossary"
    ws["A1"].font = Font(size=18, bold=True, color="FFFFFF")
    ws["A1"].fill = PatternFill("solid", fgColor="17365D")
    ws.merge_cells("A1:F1")

    ws["A2"] = (
        "Reference for pass/fail rules, scoring, and the financial and technical "
        "indicators used by the workbook."
    )
    ws.merge_cells("A2:F2")

    ws.append([])
    ws.append(["Screener", "Test / Metric", "Pass Rule", "Points", "Required?", "Methodology / Notes"])

    # (Glossary content omitted for brevity — identical to v11)
    # You can paste your existing glossary rows here unchanged.

    tests=[
    ["Stock","PEG",f"PEG < {MAX_PEG}",1,"Yes","PEG valuation test; uses trailing PEG as a fallback."],["Stock","Forward PE",f"Forward PE < {MAX_FORWARD_PE}",1,"Yes","Forward valuation test."],["Stock","ROE",f"ROE > {MIN_ROE:.0%}",1,"Yes","Profitability test."],["Stock","Profit Margin",f"Profit Margin > {MIN_MARGIN:.0%}",1,"Yes","Profitability test."],["Stock","Revenue Growth","Revenue Growth > 0%",1,"Yes","Requires positive growth."],["Stock","Earnings Growth","Earnings Growth > 0%",1,"Yes","Requires positive growth."],["Stock","Debt to Equity",f"Debt to Equity < {MAX_DEBT_EQUITY:g}",1,"Yes","Leverage test."],["Stock","Target Upside",f"Target Upside > {MIN_UPSIDE:.0%}",1,"Yes","Analyst mean target above current price."],["Stock","Above SMA 50","Price > 50-day SMA",1,"No","Score/trend input."],["Stock","Above SMA 200","Price > 200-day SMA",1,"Yes","Required in final pass."],["Stock","Golden Cross","SMA 50 > SMA 200",1,"No","Score/trend input."],["Stock / Dividend","RSI",f"{MIN_RSI:g} <= RSI <= {MAX_RSI:g}","0-2","Momentum",f"2 points for RSI 50-{MAX_RSI:g}; 1 for {MIN_RSI:g}-<50; otherwise 0."],["Stock / Dividend","MACD","MACD > Signal","0-1","Momentum","MACD confirmation point."],["Stock","Final Pass","All 8 fundamentals + Above SMA 200 + Momentum >= 2","N/A","Final","Maximum score 14."],["Dividend","Dividend Yield",f"Yield > {MIN_DIVIDEND_YIELD:.1%}",1,"Yes","Minimum income yield."],["Dividend","Payout Ratio",f"Payout < {MAX_PAYOUT:.0%}",1,"Yes","Dividend sustainability test."],["Dividend","Free Cash Flow","FCF > 0",1,"Yes","Requires positive free cash flow."],["Dividend","Debt to Equity",f"Debt to Equity < {MAX_DEBT_EQUITY:g}",1,"Yes","Leverage test."],["Dividend","Above SMA 50","Price > 50-day SMA",1,"No","Score/trend input."],["Dividend","Above SMA 200","Price > 200-day SMA",1,"Yes","Required in final pass."],["Dividend","Golden Cross","SMA 50 > SMA 200",1,"No","Score/trend input."],["Dividend","Final Pass","All 4 dividend tests + Above SMA 200 + Momentum >= 2","N/A","Final","Maximum score 10."],["ETF","Expense Ratio",f"Expense Ratio < {MAX_EXPENSE_RATIO:.2%}",1,"Yes","ETF cost test."],["ETF","AUM",f"Total Assets > ${MIN_AUM:,.0f}",1,"Yes","Fund size test."],["ETF","Above SMA 50","Price > 50-day SMA",1,"Yes","Trend requirement."],["ETF","Above SMA 200","Price > 200-day SMA",1,"Yes","Trend requirement."],["ETF","Golden Cross","SMA 50 > SMA 200",1,"Yes","Trend requirement."],["ETF","Final Pass","All 5 ETF tests pass","N/A","Final","Maximum score 5."],["All","1 Month Change",f"Latest price / price {MONTH_LOOKBACK} trading days earlier - 1",0,"No","Heatmap display/color; not a pass/fail test."],["All","Bullish Alignment","Above SMA 50 + Above SMA 200 + Golden Cross",0,"No","Descriptive dashboard/heatmap indicator."],["All","Unavailable Data","Missing metric fails its individual test",0,"Depends","Shown in Failed Tests."]]
    for r in tests: ws.append(r)
    
    glossary_start=ws.max_row+3
    ws.cell(glossary_start,1,"Indicator Glossary"); ws.cell(glossary_start,1).font=Font(size=16,bold=True,color="FFFFFF"); ws.cell(glossary_start,1).fill=PatternFill("solid",fgColor="375623"); ws.merge_cells(start_row=glossary_start,start_column=1,end_row=glossary_start,end_column=6)
    gh=glossary_start+1
    for i,v in enumerate(["Indicator","Full Name","Category","What It Measures","Interpretation in This Workbook","Notes"],1): ws.cell(gh,i,v)
    glossary=[
    ["PEG","Price/Earnings-to-Growth Ratio","Valuation","P/E relative to expected earnings growth","Lower values receive preference; must be below configured limit for the stock fundamental pass.","Combines valuation and growth into one ratio."],
    ["Forward PE","Forward Price-to-Earnings Ratio","Valuation","Share price relative to forecast earnings per share","Must be below configured maximum.","Uses expected rather than trailing earnings."],
    ["ROE","Return on Equity","Profitability","Profit earned relative to shareholder equity","Higher than the configured minimum passes.","A profitability/efficiency measure."],
    ["Profit Margin","Net Profit Margin","Profitability","Profit retained from revenue","Must exceed configured minimum.","Positive/higher margins generally indicate stronger profitability."],
    ["Revenue Growth","Revenue Growth Rate","Growth","Change in company revenue","Positive growth passes.","Measures top-line growth."],
    ["Earnings Growth","Earnings Growth Rate","Growth","Change in company earnings","Positive growth passes.","Measures bottom-line growth."],
    ["Debt to Equity","Debt-to-Equity Ratio","Financial Health","Debt relative to shareholder equity","Must remain below configured maximum.","Used as the leverage test."],
    ["Target Upside","Analyst Target Price Upside","Valuation / Sentiment","Difference between analyst mean target and current price","Positive expected upside passes.","Calculated as Target Price / Current Price - 1."],
    ["Dividend Yield","Dividend Yield","Income","Annual dividend income relative to share price","Must exceed configured minimum for dividend stocks.","Displayed as a percentage."],
    ["Payout Ratio","Dividend Payout Ratio","Income / Sustainability","Share of earnings paid as dividends","Must remain below configured maximum.","Used as a dividend sustainability screen."],
    ["Free Cash Flow","Free Cash Flow (FCF)","Cash Flow","Cash remaining after operating/capital needs","Positive FCF passes the dividend test.","Can support dividends, debt reduction, buybacks, or reinvestment."],
    ["Expense Ratio","Fund Expense Ratio","ETF Cost","Annual fund operating costs as a percentage of assets","Must be below configured maximum.","Lower is generally cheaper for investors."],
    ["AUM","Assets Under Management","ETF Size","Total assets held by the fund","Must exceed configured minimum.","Used here as a fund-size screen."],
    ["SMA 50","50-Day Simple Moving Average","Trend","Average closing price across the latest 50 sessions","Price above SMA 50 indicates positive intermediate trend in this model.","Every closing price receives equal weight."],
    ["SMA 200","200-Day Simple Moving Average","Trend","Average closing price across the latest 200 sessions","Price above SMA 200 is required for Stock and Dividend passes and ETF passes.","Longer-term trend measure."],
    ["Golden Cross","50-Day SMA > 200-Day SMA","Trend","Relationship between intermediate and long-term averages","Treated as bullish trend confirmation.","Required for ETF pass; contributes to Stock/Dividend scores."],
    ["RSI","Relative Strength Index","Momentum","Speed and magnitude of recent price changes on a 0-100 scale",f"{MIN_RSI:g}-{MAX_RSI:g} is accepted; 50-{MAX_RSI:g} receives 2 points and {MIN_RSI:g}-<50 receives 1.","Workbook uses 14 periods."],
    ["MACD","Moving Average Convergence Divergence","Momentum / Trend","Difference between fast and slow exponential moving averages","One point when MACD is above its signal line.","Workbook uses EMA 12 minus EMA 26."],
    ["MACD Signal","MACD Signal Line","Momentum","Smoothed MACD used for confirmation","MACD > Signal counts as positive confirmation.","Workbook uses a 9-period EMA of MACD."],
    ["MACD Histogram","MACD Histogram","Momentum","Difference between MACD and its signal line","Positive values correspond to MACD being above Signal.","Included for diagnostic context."],
    ["Bullish Alignment","Combined Trend Confirmation","Composite","Price/SMA and SMA/SMA trend alignment","True when price is above both SMAs and SMA 50 is above SMA 200.","Descriptive; final requirements vary by screener."],
    ["Momentum Score","RSI + MACD Score","Composite","Combined momentum confirmation","Range 0-3; Stock/Dividend final pass requires at least 2.","RSI contributes up to 2 and MACD contributes up to 1."],
    ["Score %","Normalized Screener Score","Composite","Points earned divided by maximum possible points","Useful for comparing screening strength within the output.","Does not replace the explicit final-pass rules."],
    ["1 Month Change","Approx. 1-Month Price Change","Performance","Price change over the configured 21-trading-day lookback","Determines one-month heatmap color and tile percentage.","Not used for pass/fail."]]
    for r in glossary: ws.append(r)
    for c in ws[4]: c.fill=PatternFill("solid",fgColor="5B9BD5"); c.font=Font(color="FFFFFF",bold=True); c.alignment=Alignment(horizontal="center",wrap_text=True)
    for c in ws[gh]: c.fill=PatternFill("solid",fgColor="70AD47"); c.font=Font(color="FFFFFF",bold=True); c.alignment=Alignment(horizontal="center",wrap_text=True)
    for r in ws.iter_rows(min_row=5):
        for c in r: c.alignment=Alignment(vertical="top",wrap_text=True)
    for col,width in {"A":20,"B":28,"C":30,"D":48,"E":58,"F":54}.items(): ws.column_dimensions[col].width=width


    # End Glossary
# ---------------------------------------------------------
# One‑page summary tab for profiles tickers
# ---------------------------------------------------------

def fmt_pct(value, decimals=1):
    if pd.isna(value):
        return "N/A"
    return f"{value:.{decimals}f}%" 

def fmt_price(value):
    if pd.isna(value):
        return "N/A"
    return f"${value:,.0f}"

def fmt_num(value, decimals=1):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.{decimals}f}" 

def write_summary_tab(workbook, ticker, info, metrics, history, folder):

    alt_fill = PatternFill(
        fill_type="solid",
        fgColor="DCE6F1"
    )

    thin_border = Border(
        bottom=Side(style="thin", color="B4B4B4")
    )

    name = f"{ticker} Summary"
    if name in workbook.sheetnames:
        del workbook[name]

    ws = workbook.create_sheet(name)
    ws.sheet_view.showGridLines = False

    ws.column_dimensions["A"].width = 16
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 28

    # Title
    ws["A1"] = f"{ticker} — {info.get('shortName') or info.get('longName')}"
    ws["A1"].font = Font(size=18, bold=True)
    ws.merge_cells("A1:F1")

    ws.append(["Section", "Metric", "Value"])
    for cell in ws[1]:
        cell.font = Font(bold=True)

    # Bold headers in A, B, C
    ws["A2"].font = Font(bold=True)
    ws["B2"].font = Font(bold=True)
    ws["C2"].font = Font(bold=True)

    def add(section, metric, value):
        ws.append([section, metric, value])

    current_row = ws.max_row
    ws.cell(current_row, 1).font = Font(bold=True)

    # Profile   
    add("Profile", "Name", info.get("shortName"))
    add("Profile", "Sector", info.get("sector"))
    add("Profile", "Industry", info.get("industry"))
    add("Profile", "Market Cap", fmt_price(info.get("marketCap")))
    #summary = info.get("longBusinessSummary", "N/A")
    #summary = summary.split(".", 1)[0] + "." if summary != "N/A" else summary
    #add("Company", "Business Summary", summary)

    # Price
    add("Price", "Price", fmt_price(metrics.get('Price')))
    add("Price", "Previous Close", fmt_price(metrics.get("Previous Close")))
    add("Price", "Daily Change %", fmt_pct(metrics.get("Daily Change %")*100))
    add("Price", "1 Month Change %", fmt_pct(metrics.get("1 Month Change %")*100))
    add("Price", "SMA 50", fmt_price(metrics.get("SMA 50")))
    add("Price", "SMA 200", fmt_price(metrics.get("SMA 200")))
    add(
        "Price",
        "Bullish Alignment",
        "Bullish" if metrics.get("Bullish Alignment") else "Bearish"
    )

    # Profitability
    add("Profitability", "ROE", fmt_pct(metrics.get("Return On Equity")))
    add("Profitability", "Profit Margin", fmt_pct(metrics.get("Profit Margin")*100))
    add("Profitability", "Revenue Growth", fmt_pct(metrics.get("Revenue Growth")*100))
    add("Profitability", "Earnings Growth", fmt_pct(metrics.get("Earnings Growth")*100))
    fcf = metrics.get("Free Cash Flow")
    add("Profitability", "Free Cash Flow", fmt_price(fcf) if fcf is not None else "N/A"
    )

    # Value
    add("Value", "Forward PE", fmt_num(metrics.get("Forward PE")))
    add("Value", "PEG", fmt_num(metrics.get("PEG")))
    add("Value", "Debt To Equity", fmt_num(metrics.get("Debt To Equity")))
    add("Value", "Target Price", fmt_price(metrics.get("Target Price")))
    add("Value", "Upside %", fmt_pct(metrics.get("Upside %")*100))

    # Momentum
    add("Momentum", "RSI", fmt_num(metrics.get("RSI")))
    add("Momentum", "MACD", fmt_num(metrics.get("MACD")))
    add("Momentum", "MACD Signal", fmt_num(metrics.get("MACD Signal")))
    add("Momentum", "MACD Histogram", fmt_num(metrics.get("MACD Histogram")))

 
    # Price chart
    chart_data = history.copy()
    chart_data["SMA 50"] = chart_data["Close"].rolling(50).mean()
    chart_data["SMA 200"] = chart_data["Close"].rolling(200).mean()

    # Keep only the most recent year AFTER calculating SMAs
    #chart_data = chart_data.tail(252).copy()
    one_year_ago = pd.Timestamp.today() - pd.DateOffset(years=1)
    chart_data = chart_data[chart_data.index >= one_year_ago]
    chart_data = chart_data.reset_index()
    chart_path = folder / f"{ticker}_chart.png"
    
    try:
        fig = px.line(
            chart_data,
            x="Date",
            y=["Close", "SMA 50", "SMA 200"],
            title=f"{ticker} Price History"
        )
        fig.write_image(chart_path)
        img = XLImage(str(chart_path))
        img.width = 900
        img.height = 550
        ws.add_image(img, "D2")
    except Exception as exc:
        print(f"Chart failed for {ticker}: {exc}")

    #Format Profile
    for row_num in range(2, ws.max_row + 1):

        if row_num % 2 == 0:
            fill = alt_fill
        else:
            fill = PatternFill(fill_type=None)

        for cell in ws[row_num]:
            cell.fill = fill

        # Apply right border ONLY to Column A
        right_border = Border(right=Side(style="thin", color="B4B4B4"))

        for row_num in range(2, ws.max_row + 1):
            ws[f"A{row_num}"].border = right_border
                
        ws.freeze_panes = "A2"


# ---------------------------------------------------------
# Save workbook (now includes profiles summary tabs)
# ---------------------------------------------------------

def save_workbook(workbook_path, frames, images, lists, histories, cache, stock_rows_raw):
    # Load existing workbook instead of overwriting it
    workbook = load_workbook(workbook_path)

    # Remove old screener + heatmap + summary sheets if they exist
    sheets_to_remove = [
        "Stock Screener", "Dividend Screener", "ETF Screener",
        "Stock Heatmap Data", "Dividend Heatmap Data",
        "ETF Heatmap Data", "Sector Heatmap Data",
        "S&P 100 Map", "Dividend Map", "ETF Map", "Sector Map",
        "Test Methodology"
    ]

    # Remove old summary tabs
    for ticker in lists["profiles"]:
        name = f"{ticker} Summary"
        sheets_to_remove.append(name)

    for sheet in sheets_to_remove:
        if sheet in workbook.sheetnames:
            del workbook[sheet]

    # Write screener sheets
    for name, frame in frames.items():
        write_dataframe(workbook, name, frame)

    # Insert heatmaps
    folder = workbook_path.parent
    html_path = folder / HTML_NAME

    for map_name, image_path in images.items():
        insert_map(workbook, map_name, image_path, html_path)

    # Methodology sheet
    add_methodology_sheet(workbook)

    # profiles summary tabs
    profiles = lists["profiles"]
    for row in stock_rows_raw:
        ticker = row["Ticker"]
        if ticker in profiles:
            info = cache[ticker]
            history = histories.get(ticker)
            write_summary_tab(workbook, ticker, info, row, history, folder)

    workbook.save(workbook_path)



# ---------------------------------------------------------
# Main
# ---------------------------------------------------------

def main():
    folder = Path(__file__).resolve().parent
    workbook_path = folder / WORKBOOK_NAME

    if not workbook_path.exists():
        create_starter(workbook_path)
        print(f"Created {workbook_path}. Add tickers and run again.")
        return

    lists = read_tickers(workbook_path)

    all_tickers = list(dict.fromkeys(
        lists["stocks"]
        + lists["dividends"]
        + lists["etfs"]
        + lists["sp100"]
        + list(SECTOR_ETFS.values())
    ))

    if not all_tickers:
        print("No tickers found.")
        return

    print("Reached cache section")  

    #histories = download_history(all_tickers)
    cache = {}
    fund_cache = {}

    CACHE_FILE = Path(__file__).resolve().parent / "screener_cache.pkl"

    #USE_CACHE = True
    use_cache_input = input(
    "Use cached Yahoo Finance data? (Y/N): "
    ).strip().upper()
    USE_CACHE = use_cache_input == "Y"

    print(f"USE_CACHE = {USE_CACHE}")
    print(f"CACHE_FILE = {CACHE_FILE}")
    print(f"CACHE EXISTS = {CACHE_FILE.exists()}")

    if USE_CACHE and CACHE_FILE.exists():
        print("Loading cached screener data...")

        with open(CACHE_FILE, "rb") as f:
            cached_data = pickle.load(f)

        histories = cached_data.get("histories", {})
        cache = cached_data.get("cache", {})
        fund_cache = cached_data.get("fund_cache", {})

    else:
        print("Downloading fresh history...")

        histories = download_history(all_tickers)

        # These will be populated by the screener functions below
        cache = {}
        fund_cache = {}

    # Raw stock rows (needed for profiles summary tabs)
    stock_rows_raw = stock_rows(lists["stocks"], histories, cache)

    frames = {
        "Stock Screener": sort_frame(
            stock_rows_raw,
            ["Passes Screen", "Score", "Ticker"],
            [False, False, True],
        ),
        "Dividend Screener": sort_frame(
            dividend_rows(lists["dividends"], histories, cache),
            ["Passes Screen", "Score", "Dividend Yield"],
            [False, False, False],
        ),
        "ETF Screener": sort_frame(
            etf_rows(lists["etfs"], histories, cache, fund_cache),
            ["Passes Screen", "Score", "Ticker"],
            [False, False, True],
        ),
        "Stock Heatmap Data": sort_frame(
            heatmap_rows(lists["sp100"], histories, cache),
            ["Group", "1 Month Change %"],
            [True, False],
        ),
        "Dividend Heatmap Data": sort_frame(
            heatmap_rows(lists["dividends"], histories, cache, True),
            ["Group", "1 Month Change %"],
            [True, False],
        ),
        "ETF Heatmap Data": sort_frame(
            heatmap_rows(lists["etfs"], histories, cache),
            ["Group", "1 Month Change %"],
            [True, False],
        ),
        "Sector Heatmap Data": sort_frame(
            sector_heatmap_rows(histories, cache),
            ["Daily Change %", "Sector"],
            [False, True],
        ),
    }

    if not CACHE_FILE.exists():

        cached_data = {
            "histories": histories,
            "cache": cache,
            "fund_cache": fund_cache,
        }

        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cached_data, f)

        print(f"Saved cache to {CACHE_FILE}")
    
    images = export_assets(folder, frames)

    save_workbook(
        workbook_path,
        frames,
        images,
        lists,
        histories,
        cache,
        stock_rows_raw,
    )

    print(f"Updated workbook: {workbook_path}")
    print(f"Interactive dashboard: {folder / HTML_NAME}")


# ---------------------------------------------------------
# Run
# ---------------------------------------------------------

if __name__ == "__main__":
    main()
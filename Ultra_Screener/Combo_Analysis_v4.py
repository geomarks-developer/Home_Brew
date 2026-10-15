"""Combined stock, dividend, and ETF screeners with one-month heatmaps.

Expected workbook: StockAnalysis.xlsx in the same folder as this script.
Tickers sheet: A=stocks, B=dividend stocks, C=ETFs, D=S&P 500 stocks.

Install:
    pip install yfinance pandas openpyxl pillow plotly kaleido
If Kaleido requires Chrome:
    kaleido_get_chrome
"""
from __future__ import annotations
import math, time
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
    wb = Workbook(); ws = wb.active; ws.title = TICKERS_SHEET
    ws.append(["Stock", "Dividend", "ETF", "S&P 500"]); ws.freeze_panes = "A2"
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.font = Font(color="FFFFFF", bold=True)
    for col in range(1, 5): ws.column_dimensions[get_column_letter(col)].width = 18
    wb.save(path)


def read_tickers(path):
    wb = load_workbook(path, read_only=True, data_only=True)
    if TICKERS_SHEET not in wb.sheetnames:
        raise KeyError('The workbook needs a sheet named "Tickers".')
    ws = wb[TICKERS_SHEET]; result = {}
    for name, col in {"stocks": 1, "dividends": 2, "etfs": 3, "sp500": 4}.items():
        values = [normalize_ticker(ws.cell(row, col).value) for row in range(2, ws.max_row + 1)]
        result[name] = list(dict.fromkeys(value for value in values if value))
    wb.close(); return result


def download_history(tickers):
    if not tickers: return {}
    data = yf.download(tickers, period="1y", interval="1d", auto_adjust=False,
                       actions=False, group_by="ticker", threads=True, progress=False)
    if len(tickers) == 1:
        frame = data.dropna(how="all")
        return {tickers[0]: frame} if not frame.empty else {}
    result = {}
    for ticker in tickers:
        try:
            frame = data[ticker].copy().dropna(how="all")
            if not frame.empty: result[ticker] = frame
        except (KeyError, TypeError): pass
    return result


def price_metrics(history):
    blank = {"Price": None, "Previous Close": None, "Daily Change %": None,
             "1 Month Change %": None, "SMA 50": None, "SMA 200": None,
             "Above SMA 50": False, "Above SMA 200": False,
             "SMA 50 > SMA 200": False, "Bullish Alignment": False,
             "52 Week High": None, "% From 52W High": None}
    if history is None or history.empty: return blank
    column = "Adj Close" if "Adj Close" in history.columns else "Close"
    close = pd.to_numeric(history[column], errors="coerce").dropna()
    if close.empty: return blank
    price = number(close.iloc[-1]); previous = number(close.iloc[-2]) if len(close) >= 2 else None
    month_base = number(close.iloc[-(MONTH_LOOKBACK + 1)]) if len(close) >= MONTH_LOOKBACK + 1 else None
    sma50 = number(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    sma200 = number(close.rolling(200).mean().iloc[-1]) if len(close) >= 200 else None
    high = number(close.max())
    above50 = price is not None and sma50 is not None and price > sma50
    above200 = price is not None and sma200 is not None and price > sma200
    cross = sma50 is not None and sma200 is not None and sma50 > sma200
    return {"Price": price, "Previous Close": previous,
            "Daily Change %": price / previous - 1 if price and previous else None,
            "1 Month Change %": price / month_base - 1 if price and month_base else None,
            "SMA 50": sma50, "SMA 200": sma200, "Above SMA 50": above50,
            "Above SMA 200": above200, "SMA 50 > SMA 200": cross,
            "Bullish Alignment": above50 and above200 and cross,
            "52 Week High": high, "% From 52W High": price / high - 1 if price and high else None}


def get_info(ticker, cache):
    if ticker in cache: return cache[ticker]
    try: cache[ticker] = yf.Ticker(ticker).get_info() or {}
    except Exception as exc:
        print(f"  Warning: information unavailable for {ticker}: {exc}"); cache[ticker] = {}
    time.sleep(PAUSE); return cache[ticker]


def stock_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"Stock {n}/{len(tickers)}: {ticker}")
        info = get_info(ticker, cache); p = price_metrics(histories.get(ticker))
        target = number(info.get("targetMeanPrice")); current = p["Price"] or number(info.get("currentPrice"))
        upside = target / current - 1 if target and current else None
        peg = number(info.get("pegRatio") or info.get("trailingPegRatio"))
        pe = number(info.get("forwardPE")); roe = number(info.get("returnOnEquity"))
        margin = number(info.get("profitMargins")); revenue = number(info.get("revenueGrowth"))
        earnings = number(info.get("earningsGrowth")); debt = number(info.get("debtToEquity"))
        tests = [compare(peg,"lt",MAX_PEG), compare(pe,"lt",MAX_FORWARD_PE),
                 compare(roe,"gt",MIN_ROE), compare(margin,"gt",MIN_MARGIN),
                 compare(revenue,"gt",0), compare(earnings,"gt",0),
                 compare(debt,"lt",MAX_DEBT_EQUITY), compare(upside,"gt",MIN_UPSIDE),
                 p["Above SMA 50"], p["Above SMA 200"], p["SMA 50 > SMA 200"]]
        rows.append({"Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
                     "Sector": info.get("sector"), "Industry": info.get("industry"), **p,
                     "Target Price": target, "Upside %": upside, "PEG": peg, "Forward PE": pe,
                     "Return On Equity": roe, "Profit Margin": margin, "Revenue Growth": revenue,
                     "Earnings Growth": earnings, "Debt To Equity": debt,
                     "Free Cash Flow": number(info.get("freeCashflow")), "Score": sum(tests),
                     "Max Score": len(tests), "Passes Screen": all(tests[:8]) and p["Above SMA 200"],
                     "Error": None if info else "Data unavailable"})
    return rows


def dividend_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"Dividend {n}/{len(tickers)}: {ticker}")
        info = get_info(ticker, cache); p = price_metrics(histories.get(ticker))
        dividend_yield = number(info.get("dividendYield"))
        # Some sources return 0.055, others return 5.5
        if dividend_yield is not None and dividend_yield > 1:
            dividend_yield = dividend_yield / 100
  
        payout_ratio = number(info.get("payoutRatio"))
        if payout_ratio is not None and payout_ratio > 1:
            payout_ratio = payout_ratio / 100

        cash_flow = number(info.get("freeCashflow")); debt = number(info.get("debtToEquity"))
        average_yield = number(info.get("fiveYearAvgDividendYield"))
        tests = [compare(dividend_yield,"gt",MIN_DIVIDEND_YIELD), compare(payout_ratio,"lt",MAX_PAYOUT),
                 cash_flow is not None and cash_flow > 0, compare(debt,"lt",MAX_DEBT_EQUITY),
                 p["Above SMA 50"], p["Above SMA 200"], p["SMA 50 > SMA 200"]]
        rows.append({"Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
                     "Sector": info.get("sector"), **p, "Dividend Yield": dividend_yield,
                     "5Y Avg Dividend Yield": average_yield / 100 if average_yield is not None else None,
                     "Payout Ratio": payout_ratio, "Free Cash Flow": cash_flow, "Debt To Equity": debt,
                     "Score": sum(tests), "Max Score": len(tests),
                     "Passes Screen": all(tests[:4]) and p["Above SMA 200"],
                     "Error": None if info else "Data unavailable"})
    return rows


def etf_rows(tickers, histories, cache):
    rows = []
    for n, ticker in enumerate(tickers, 1):
        print(f"ETF {n}/{len(tickers)}: {ticker}")
        info = get_info(ticker, cache); p = price_metrics(histories.get(ticker))
        expense = number(info.get("annualReportExpenseRatio") or info.get("netExpenseRatio"))
        assets = number(info.get("totalAssets"))
        tests = [compare(expense,"lt",MAX_EXPENSE_RATIO), compare(assets,"gt",MIN_AUM),
                 p["Above SMA 50"], p["Above SMA 200"], p["SMA 50 > SMA 200"]]
        rows.append({"Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
                     "Category": info.get("category"), **p, "Expense Ratio": expense,
                     "Total Assets": assets, "Yield": number(info.get("yield")),
                     "3Y Average Return": number(info.get("threeYearAverageReturn")),
                     "5Y Average Return": number(info.get("fiveYearAverageReturn")),
                     "Score": sum(tests), "Max Score": len(tests),
                     "Passes Screen": tests[0] and tests[1] and p["Above SMA 200"],
                     "Error": None if info else "Data unavailable"})
    return rows


def heatmap_rows(tickers, histories, cache, dividend=False):
    rows = []
    for ticker in tickers:
        info = get_info(ticker, cache); p = price_metrics(histories.get(ticker))
        row = {"Ticker": ticker, "Name": info.get("shortName") or info.get("longName"),
               "Group": info.get("sector") or info.get("category") or "Unclassified",
               "Market Cap / Assets": number(info.get("marketCap") or info.get("totalAssets")) or 1,
               "Price": p["Price"], "Daily Change %": p["Daily Change %"],
               "1 Month Change %": p["1 Month Change %"], "SMA 50": p["SMA 50"],
               "SMA 200": p["SMA 200"], "Above SMA 50": p["Above SMA 50"],
               "Above SMA 200": p["Above SMA 200"], "Bullish Alignment": p["Bullish Alignment"]}
        if dividend:
            dividend_yield = number(info.get("dividendYield"))
            # Some sources return 0.055, others return 5.5
            if dividend_yield is not None and dividend_yield > 1:
                dividend_yield = dividend_yield / 100
            row["Dividend Yield"] = dividend_yield

            payout_ratio = number(info.get("payoutRatio"))
            if payout_ratio is not None and payout_ratio > 1:
                payout_ratio = payout_ratio / 100
            row["Payout Ratio"] = payout_ratio
        rows.append(row)
    return rows


def sort_frame(rows, columns, ascending):
    frame = pd.DataFrame(rows)
    return frame.sort_values(columns, ascending=ascending, na_position="last").reset_index(drop=True) if not frame.empty else frame


def create_treemap(frame, title, dividend=False):
    if frame.empty: return None
    chart = frame.copy()
    chart["Market Cap / Assets"] = pd.to_numeric(chart["Market Cap / Assets"], errors="coerce").fillna(1).clip(lower=1)
    chart["1 Month Change %"] = pd.to_numeric(chart["1 Month Change %"], errors="coerce")
    chart = chart.dropna(subset=["1 Month Change %"])
    if chart.empty: return None
    chart["Group"] = chart["Group"].fillna("Unclassified"); chart["Name"] = chart["Name"].fillna(chart["Ticker"])
    hover = ["Name", "Price", "SMA 50", "SMA 200", "Bullish Alignment"]
    if dividend: hover += ["Dividend Yield", "Payout Ratio"]
    fig = px.treemap(chart, path=[px.Constant("Market"), "Group", "Ticker"], values="Market Cap / Assets",
                     color="1 Month Change %", color_continuous_midpoint=0,
                     color_continuous_scale=[[0,"#8B0000"],[.25,"#D73027"],[.45,"#F4A6A6"],
                                             [.5,"#D9D9D9"],[.55,"#A7DCA7"],[.75,"#1A9850"],[1,"#006400"]],
                     custom_data=hover, title=title)
    labels = []
    for value in fig.data[0].marker.colors:
        value = number(value); labels.append(f"{value:+.2%}" if value is not None else "")
    hover_template = ("<b>%{label}</b><br>%{customdata[0]}<br>1 Month Change: %{color:+.2%}<br>"
                      "Price: $%{customdata[1]:,.2f}<br>SMA 50: $%{customdata[2]:,.2f}<br>"
                      "SMA 200: $%{customdata[3]:,.2f}<br>Bullish Alignment: %{customdata[4]}")
    if dividend:
        hover_template += "<br>Dividend Yield: %{customdata[5]:.2%}<br>Payout Ratio: %{customdata[6]:.1%}"
    hover_template += "<extra></extra>"
    fig.update_traces(text=labels, texttemplate="<b>%{label}</b><br>%{text}", hovertemplate=hover_template,
                      marker=dict(line=dict(width=1,color="#202020")), root_color="#101820")
    fig.update_layout(template="plotly_dark", paper_bgcolor="#101820", plot_bgcolor="#101820",
                      margin=dict(t=55,l=8,r=8,b=8),
                      coloraxis_colorbar=dict(title="1 Month Change", tickformat="+.1%"))
    return fig


def create_html(path, frames, figures):
    def count(frame, column): return int(frame[column].fillna(False).sum()) if not frame.empty and column in frame else 0
    stocks, dividends, etfs = frames["Stock Screener"], frames["Dividend Screener"], frames["ETF Screener"]
    cards = [("Stocks Screened",len(stocks)),("Stocks Passing",count(stocks,"Passes Screen")),
             ("Dividend Stocks Passing",count(dividends,"Passes Screen")),("ETFs Passing",count(etfs,"Passes Screen")),
             ("Stock Bullish Alignments",count(stocks,"Bullish Alignment")),
             ("Dividend Bullish Alignments",count(dividends,"Bullish Alignment")),
             ("ETF Bullish Alignments",count(etfs,"Bullish Alignment"))]
    cards_html = "".join(f'<div class="card"><div class="value">{v:,}</div><div class="label">{k}</div></div>' for k,v in cards)
    chart_html = []
    for index, (name, figure) in enumerate(figures):
        content = figure.to_html(full_html=False, include_plotlyjs="inline" if index == 0 else False) if figure else f"<p>No {name} data.</p>"
        chart_html.append(f'<section class="chart">{content}</section>')
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    path.write_text(f'''<!doctype html><html><head><meta charset="utf-8"><title>Investment Dashboard</title>
<style>body{{margin:0;background:#0b1220;color:#fff;font-family:Segoe UI,Arial}}header{{padding:24px 32px;background:#13233d}}.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;padding:22px 32px}}.card{{background:#172941;border-radius:14px;padding:18px}}.value{{font-size:30px;font-weight:700;color:#7fd1ff}}.label{{color:#c8d3e3}}.chart{{margin:0 22px 24px;background:#101820;border-radius:14px;overflow:hidden}}</style>
</head><body><header><h1>Investment Dashboard</h1><div>One-month heatmaps, updated {now}</div></header><section class="cards">{cards_html}</section>{''.join(chart_html)}</body></html>''', encoding="utf-8")


def export_assets(folder, frames):
    figures = [("S&P 500", create_treemap(frames["Stock Heatmap Data"], "S&P 500 One-Month Heatmap")),
               ("Dividend", create_treemap(frames["Dividend Heatmap Data"], "Dividend Stock One-Month Heatmap", True)),
               ("ETF", create_treemap(frames["ETF Heatmap Data"], "ETF One-Month Heatmap"))]
    images = {}
    for map_name, (_, fig), filename in zip(["S&P 500 Map","Dividend Map","ETF Map"], figures,
                                            ["sp500_heatmap.png","dividend_heatmap.png","etf_heatmap.png"]):
        if fig:
            try:
                path = folder / filename; fig.write_image(path, width=1800, height=1000); images[map_name] = path
            except Exception as exc:
                print(f"Warning: PNG export failed for {map_name}: {exc}")
    create_html(folder / HTML_NAME, frames, figures)
    return images


def write_dataframe(workbook, name, frame):
    if name in workbook.sheetnames: del workbook[name]
    ws = workbook.create_sheet(name); ws.sheet_view.showGridLines = False; ws.freeze_panes = "A2"
    if frame.empty: ws["A1"] = "No results"; return
    ws.append(list(frame.columns))
    for row in frame.itertuples(index=False, name=None): ws.append(list(row))
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="1F4E78"); cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")
    ws.auto_filter.ref = ws.dimensions; headers = {cell.value: cell.column for cell in ws[1]}
    percentages = {"Daily Change %","1 Month Change %","% From 52W High","Upside %","Return On Equity",
                   "Profit Margin","Revenue Growth","Earnings Growth","Dividend Yield","5Y Avg Dividend Yield",
                   "Payout Ratio","Expense Ratio","Yield","3Y Average Return","5Y Average Return"}
    currencies = {"Price","Previous Close","SMA 50","SMA 200","52 Week High","Target Price"}
    integers = {"Free Cash Flow","Total Assets","Market Cap / Assets"}
    for header, col in headers.items():
        fmt = "0.0%;[Red](0.0%);-" if header in percentages else "$#,##0.00;[Red]($#,##0.00);-" if header in currencies else "#,##0;[Red](#,##0);-" if header in integers else None
        if fmt:
            for cells in ws.iter_cols(min_col=col,max_col=col,min_row=2):
                for cell in cells: cell.number_format = fmt
    if "1 Month Change %" in headers:
        letter = get_column_letter(headers["1 Month Change %"])
        ws.conditional_formatting.add(f"{letter}2:{letter}{ws.max_row}", ColorScaleRule(start_type="min",start_color="F8696B",mid_type="num",mid_value=0,mid_color="FFEB84",end_type="max",end_color="63BE7B"))
    for cells in ws.columns:
        values = [str(c.value or "") for c in cells[:200]]
        ws.column_dimensions[get_column_letter(cells[0].column)].width = min(max(max(map(len,values),default=0)+2,11),32)


def insert_map(workbook, name, image_path, html_path):
    if name in workbook.sheetnames: del workbook[name]
    ws = workbook.create_sheet(name); ws.sheet_view.showGridLines = False
    ws["A1"] = name; ws["A1"].font = Font(size=18,bold=True,color="FFFFFF"); ws["A1"].fill = PatternFill("solid",fgColor="17365D"); ws.merge_cells("A1:H1")
    ws["A2"] = "Open interactive dashboard"; ws["A2"].hyperlink = html_path.resolve().as_uri(); ws["A2"].style = "Hyperlink"
    if image_path and image_path.exists():
        image = XLImage(str(image_path)); image.width = 1350; image.height = 750; ws.add_image(image,"A4")
    else: ws["A4"] = "Static image unavailable. Use the interactive dashboard link above."


def save_workbook(path, frames, images):
    wb = load_workbook(path)
    for name in ["Stock Screener","Dividend Screener","ETF Screener","Stock Heatmap Data","Dividend Heatmap Data","ETF Heatmap Data"]:
        write_dataframe(wb, name, frames[name])
    html_path = path.parent / HTML_NAME
    for name in ["S&P 500 Map","Dividend Map","ETF Map"]: insert_map(wb,name,images.get(name),html_path)
    if "Dashboard" in wb.sheetnames: del wb["Dashboard"]
    ws = wb.create_sheet("Dashboard",0); ws.sheet_view.showGridLines = False
    ws["A1"] = "Investment Screening Dashboard"; ws["A1"].font = Font(size=18,bold=True,color="FFFFFF"); ws["A1"].fill = PatternFill("solid",fgColor="17365D"); ws.merge_cells("A1:D1")
    ws.append(["Last Refresh",datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")]); ws.append([]); ws.append(["Section","Tickers","Passing","Strong Uptrends"])
    for label,key in [("Stocks","Stock Screener"),("Dividends","Dividend Screener"),("ETFs","ETF Screener")]:
        frame=frames[key]; passing=int(frame["Passes Screen"].fillna(False).sum()) if not frame.empty else 0; bullish=int(frame["Bullish Alignment"].fillna(False).sum()) if not frame.empty else 0
        ws.append([label,len(frame),passing,bullish])
    ws["A9"] = "Open interactive one-month dashboard"; ws["A9"].hyperlink = html_path.resolve().as_uri(); ws["A9"].style = "Hyperlink"
    for cell in ws[4]: cell.fill = PatternFill("solid",fgColor="5B9BD5"); cell.font = Font(color="FFFFFF",bold=True)
    wb.calculation.fullCalcOnLoad = True; wb.calculation.forceFullCalc = True; wb.save(path)


def main():
    folder = Path(__file__).resolve().parent; workbook_path = folder / WORKBOOK_NAME
    if not workbook_path.exists():
        create_starter(workbook_path); print(f"Created {workbook_path}. Add tickers and run again."); return
    lists = read_tickers(workbook_path)
    all_tickers = list(dict.fromkeys(lists["stocks"] + lists["dividends"] + lists["etfs"] + lists["sp500"]))
    if not all_tickers: print("No tickers found."); return
    print(f"Downloading history for {len(all_tickers)} tickers...")
    histories = download_history(all_tickers); cache = {}
    frames = {
        "Stock Screener": sort_frame(stock_rows(lists["stocks"],histories,cache),["Passes Screen","Score","Ticker"],[False,False,True]),
        "Dividend Screener": sort_frame(dividend_rows(lists["dividends"],histories,cache),["Passes Screen","Score","Dividend Yield"],[False,False,False]),
        "ETF Screener": sort_frame(etf_rows(lists["etfs"],histories,cache),["Passes Screen","Score","Ticker"],[False,False,True]),
        "Stock Heatmap Data": sort_frame(heatmap_rows(lists["sp500"],histories,cache),["Group","1 Month Change %"],[True,False]),
        "Dividend Heatmap Data": sort_frame(heatmap_rows(lists["dividends"],histories,cache,True),["Group","1 Month Change %"],[True,False]),
        "ETF Heatmap Data": sort_frame(heatmap_rows(lists["etfs"],histories,cache),["Group","1 Month Change %"],[True,False]),
    }
    images = export_assets(folder, frames); save_workbook(workbook_path, frames, images)
    print(f"Updated workbook: {workbook_path}")
    print(f"Interactive dashboard: {folder / HTML_NAME}")


if __name__ == "__main__":
    main()

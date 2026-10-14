import yfinance as yf
import pandas as pd
from openpyxl.workbook import Workbook
from pathlib import Path


# -----------------------------
# 1. Config
# -----------------------------
TICKERS = [
 'AOS','ABT','ABBV','AFL','APD','ALB','AMCR','ADM','ATO','ADP'
,'BDX','BRO','BF-B','CAH','CAT','CHRW','CVX','CB','CHD','CINF'
,'CTAS','CLX','KO','CL','ED','DOV','ECL','EMR','ERIE','ES','ESS'
,'EXPD','XOM','FDS','FAST','FRT','BEN','GD','GPC','HRL','ITW'
,'IBM','SJM','JNJ','KVUE','KMB','LIN','LOW','MKC','MCD','MDT'
,'NEE','NDSN','NUE','PNR','PEP','PPG','PG','O','ROP','SPGI','SHW'
,'SWK','SYY','TROW','TGT','GWW','WMT','WST'
]

MIN_YIELD = .02
MAX_YIELD = .08
MAX_PE    = 25
MAX_PB    = 3.0
MAX_PAYOUT = 0.75

WRITE_TO_EXCEL = True
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_XLSX = BASE_DIR / "dividend_value_screener.xlsx"

# -----------------------------
# 2. Fetch data and screen
# -----------------------------
results = []

for ticker in TICKERS:
    try:
        stock = yf.Ticker(ticker)
        info = stock.info

        div_yield = info.get("dividendYield")

        # Fix Yahoo Finance bad dividend data
        if div_yield is None:
            continue

        # If Yahoo reports 4.5 instead of 0.045
        if div_yield > 1:
            div_yield = div_yield / 100

        # Filter out impossible yields (>25%)
        if div_yield > 0.25:
            continue

        forward_pe = info.get("forwardPE", None)
        price_to_book = info.get("priceToBook", None)
        payout_ratio = info.get("payoutRatio", None)
        eps = info.get("trailingEps", None)
        name = info.get("shortName", ticker)
        sector = info.get("sector", "N/A")
        price = info.get("currentPrice")
        ma_50d = info.get("fiftyDayAverage")
        ma_200d = info.get("twoHundredDayAverage")

        # Basic sanity checks
        if div_yield is None or forward_pe is None or price_to_book is None:
           continue

        if eps is None or eps <= 0:
            # avoid negative/zero earnings
            continue

        # Yield filter
        if not (MIN_YIELD <= div_yield <= MAX_YIELD):
            continue

        # Valuation filters
        if forward_pe > MAX_PE:
            continue

        if price_to_book > MAX_PB:
            continue

        # Payout ratio filter (if available)
        if payout_ratio is not None:
            if not (0 < payout_ratio <= MAX_PAYOUT):
                continue

        results.append({
            "Ticker": ticker,
            "Name": name,
            "Sector": sector,
            "Price": price,
            "MA 50 Day": ma_50d,
            "MA 200 Day": ma_200d,
            "Dividend Yield %": round(div_yield * 100, 1),
            "Forward P/E": round(forward_pe, 1),
            "Price/Book": round(price_to_book, 1),
            "Payout Ratio": round(payout_ratio, 2) if payout_ratio is not None else None,
            "EPS (Trailing)": round(eps, 2),
        })

    except Exception as e:
        print(f"Error fetching {ticker}: {e}")

# -----------------------------
# 3. Build DataFrame
# -----------------------------
df = pd.DataFrame(results)

if df.empty:
    print("No stocks matched the criteria.")
else:
    # Sort by yield descending, then P/E ascending (high income, better value)
    df = df.sort_values(by=["Dividend Yield %", "Forward P/E"], ascending=[False, True])

    print("\n=== Medium–High Yield Undervalued Dividend Stocks ===\n")
    print(df.to_string(index=False))

    # Optional: write to Excel
    if WRITE_TO_EXCEL:
        df.to_excel(OUTPUT_XLSX, index=False)
        print(f"\nResults written to: {OUTPUT_XLSX}")

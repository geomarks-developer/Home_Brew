import os
import pandas as pd
import yfinance as yf
import plotly.express as px
from pathlib import Path

# Performance period
PERIOD = "1mo"

# Examples:
# "2d"  = 1 trading day change
# "5d"  = 1 week
# "1mo" = 1 month
# "3mo" = 3 months
# "6mo" = 6 months
# "1y"  = 1 year


# ------------------------------------
# File Location
# ------------------------------------

base_dir = Path(__file__).resolve().parent
excel_path = base_dir / "tickers.xlsx"

# ------------------------------------
# Read Tickers
# ------------------------------------

df = pd.read_excel(excel_path)

ticker_col = df.columns[0]

tickers = (
    df[ticker_col]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
    .tolist()
)

print(f"Found {len(tickers)} tickers")

# ------------------------------------
# Download Data
# ------------------------------------

rows = []

for ticker in tickers:

    try:

        print(f"Loading {ticker}...")

        t = yf.Ticker(ticker)

        info = t.info

        market_cap = info.get("marketCap", 0)
        sector = info.get("sector", "Unknown")

        hist = t.history(period=PERIOD)

        if len(hist) >= 2:

            start_price = hist["Close"].iloc[0]
            end_price = hist["Close"].iloc[-1]

            pct_change = (
                (end_price - start_price)
                / start_price
            ) * 100

        else:

            pct_change = 0

        rows.append(
            {
                "Sector": sector,
                "Ticker": ticker,
                "MarketCap": market_cap,
                "PctChange": pct_change
            }
        )

    except Exception as e:

        print(f"Error processing {ticker}: {e}")

# ------------------------------------
# Build DataFrame
# ------------------------------------

heatmap_df = pd.DataFrame(rows)

heatmap_df = heatmap_df[
    heatmap_df["MarketCap"] > 0
]

heatmap_df["Sector"] = (
    heatmap_df["Sector"]
    .fillna("Unknown")
    .astype(str)
)

# Create label text
heatmap_df["DisplayPct"] = (
    heatmap_df["PctChange"]
    .map(lambda x: f"{x:+.2f}%")
)

# ------------------------------------
# Create Treemap
# ------------------------------------

fig = px.treemap(
    heatmap_df,
    path=["Sector", "Ticker"],
    values="MarketCap",
    color="PctChange",
    custom_data=["PctChange"],
    color_continuous_scale=[
        [0.00, "#8B0000"],   # Dark Red
        [0.40, "#FF6B6B"],   # Light Red
        [0.50, "#FFFFFF"],   # Neutral
        [0.60, "#90EE90"],   # Light Green
        [1.00, "#006400"]    # Dark Green
    ],
    color_continuous_midpoint=0
)

# ------------------------------------
# Labels
# ------------------------------------

fig.update_traces(
    textinfo="label+text",
    text=heatmap_df["DisplayPct"]
)


# ------------------------------------
# Layout
# ------------------------------------

fig.update_layout(
    title=f"Stock Market Heatmap ({PERIOD} Performance)",
    margin=dict(t=40, l=5, r=5, b=5),
    uniformtext=dict(
        minsize=8,
        mode="hide"
    )
)

# ------------------------------------
# Save HTML
# ------------------------------------

html_file = base_dir / "stock_heatmap.html"

fig.write_html(html_file)

print(f"\nSaved to:\n{html_file}")

# ------------------------------------
# Show
# ------------------------------------

fig.show()
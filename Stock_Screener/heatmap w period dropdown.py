import os
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from pathlib import Path

# =====================================================
# CONFIGURATION
# =====================================================

BASE_DIR = Path(__file__).resolve().parent
EXCEL_FILE = BASE_DIR / "tickers.xlsx"

PERIODS = {
    "1 Day": "2d",
    "1 Week": "5d",
    "1 Month": "1mo",
    "3 Months": "3mo",
    "6 Months": "6mo",
    "1 Year": "1y"
}

# =====================================================
# READ TICKERS
# =====================================================

df = pd.read_excel(EXCEL_FILE)

ticker_col = df.columns[0]

tickers = (
    df[ticker_col]
    .dropna()
    .astype(str)
    .str.strip()
    .str.upper()
    .unique()
    .tolist()
)

print(f"Found {len(tickers)} tickers")

# =====================================================
# CACHE STATIC DATA
# =====================================================

ticker_info = {}

for ticker in tickers:

    try:

        print(f"Loading static info: {ticker}")

        t = yf.Ticker(ticker)

        info = t.info

        ticker_info[ticker] = {
            "Sector": info.get("sector", "Unknown"),
            "MarketCap": max(
                info.get("marketCap", 0),
                1
            )
        }

    except Exception as e:

        print(f"Error loading {ticker}: {e}")

# =====================================================
# BUILD DATAFRAME FOR A PERIOD
# =====================================================

def build_dataframe(period):

    rows = []

    for ticker in tickers:

        try:

            t = yf.Ticker(ticker)

            hist = t.history(period=period)

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
                    "Sector":
                        ticker_info[ticker]["Sector"],

                    "Ticker":
                        ticker,

                    "MarketCap":
                        ticker_info[ticker]["MarketCap"],

                    "PctChange":
                        pct_change
                }
            )

        except Exception as e:

            print(
                f"Error loading "
                f"{ticker} ({period}): {e}"
            )

    result = pd.DataFrame(rows)

    result["Sector"] = (
        result["Sector"]
        .fillna("Unknown")
        .astype(str)
    )

    return result

# =====================================================
# CREATE FIGURE
# =====================================================

fig = go.Figure()

period_names = list(PERIODS.keys())

for idx, (period_label, period_code) in enumerate(
    PERIODS.items()
):

    print(
        f"\nBuilding heatmap for "
        f"{period_label}"
    )

    heatmap_df = build_dataframe(
        period_code
    )

    labels = []
    parents = []
    values = []
    colors = []
    custom_text = []

    sectors = sorted(
        heatmap_df["Sector"].unique()
    )

    # ---------------------------
    # Sector Nodes
    # ---------------------------

    for sector in sectors:

        sector_df = heatmap_df[
            heatmap_df["Sector"] == sector
        ]

        labels.append(sector)
        parents.append("")
        values.append(
            sector_df["MarketCap"].sum()
        )
        colors.append(0)
        custom_text.append("")

        # -----------------------
        # Ticker Nodes
        # -----------------------

        for _, row in (
            sector_df.sort_values(
                "MarketCap",
                ascending=False
            ).iterrows()
        ):

            labels.append(
                row["Ticker"]
            )

            parents.append(
                sector
            )

            values.append(
                row["MarketCap"]
            )

            colors.append(
                row["PctChange"]
            )

            custom_text.append(
                f"{row['PctChange']:+.2f}%"
            )

    fig.add_trace(

        go.Treemap(

            visible=(idx == 0),

            labels=labels,

            parents=parents,

            values=values,

            customdata=custom_text,

            branchvalues="total",

            texttemplate=
                "%{label}<br>%{customdata}",

            textfont=dict(
                size=16
            ),

            marker=dict(
                colors=colors,
                colorscale=[
                    [0.00, "#8B0000"],
                    [0.25, "#FF4444"],
                    [0.50, "#F0F0F0"],
                    [0.75, "#6AD46A"],
                    [1.00, "#006400"]
                ],
                cmid=0,
                line=dict(
                    width=1,
                    color="white"
                )
            ),

            hovertemplate=
                "<b>%{label}</b><br>" +
                "Performance: %{customdata}" +
                "<extra></extra>"
        )

    )

# =====================================================
# DROPDOWN
# =====================================================

buttons = []

for index, period_name in enumerate(
    period_names
):

    visible = [
        False
    ] * len(period_names)

    visible[index] = True

    buttons.append(

        dict(

            label=period_name,

            method="update",

            args=[
                {
                    "visible": visible
                },
                {
                    "title":
                    f"Stock Market Heatmap ({period_name})"
                }
            ]
        )
    )

# =====================================================
# LAYOUT
# =====================================================

fig.update_layout(

    title=
        "Stock Market Heatmap (1 Day)",

    margin=dict(
        t=60,
        l=5,
        r=5,
        b=5
    ),

    uniformtext=dict(
        minsize=8,
        mode="hide"
    ),

    updatemenus=[

        dict(

            buttons=buttons,

            active=0,

            x=0.01,

            y=1.10,

            xanchor="left",

            yanchor="top"
        )

    ]
)

# =====================================================
# SAVE RESULTS
# =====================================================

html_file = BASE_DIR / "stock_heatmap.html"

fig.write_html(html_file)

print()
print("Heatmap Saved:")
print(html_file)

# =====================================================
# DISPLAY
# =====================================================

fig.show()
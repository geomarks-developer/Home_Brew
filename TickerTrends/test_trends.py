"""
TickerTrends Real-Stock Trend Test
==================================

Tests the technical and trend-state engines against
a few real stocks before we finalize scoring.
"""

from core.technicals import get_technicals
from core.trend_state import determine_trend_state
import numpy as np


TEST_TICKERS = [
    "MSFT",
    "AAPL",
    "NVDA",
]


def format_money(value):
    if value is None:
        return "N/A"

    return f"${value:,.2f}"


def format_number(value, decimals=2, suffix=""):
    if value is None:
        return "N/A"

    return f"{value:.{decimals}f}{suffix}"


def test_ticker(ticker):
    print()
    print("=" * 62)
    print(f"TickerTrends Test: {ticker}")
    print("=" * 62)

    technicals = get_technicals(ticker)

    if technicals is None:
        print("Unable to calculate technical indicators.")
        return

    trend = determine_trend_state(technicals)

    if trend is None:
        print("Unable to determine trend state.")
        return

    print()
    print("TECHNICALS")
    print("-" * 62)

    print(
        f"Price:              "
        f"{format_money(technicals.get('price'))}"
    )

    print(
        f"50-day SMA:         "
        f"{format_money(technicals.get('sma_50'))}"
    )

    print(
        f"200-day SMA:        "
        f"{format_money(technicals.get('sma_200'))}"
    )

    print(
        f"200-day slope:      "
        f"{format_number(
            technicals.get('sma_200_slope'),
            2,
            '%'
        )}"
    )

    print(
        f"From 50-day SMA:    "
        f"{format_number(
            technicals.get('pct_from_sma50'),
            2,
            '%'
        )}"
    )

    print(
        f"From 200-day SMA:   "
        f"{format_number(
            technicals.get('pct_from_sma200'),
            2,
            '%'
        )}"
    )

    print(
        f"RSI-14:             "
        f"{format_number(
            technicals.get('rsi_14'),
            1
        )}"
    )

    print()
    print("TREND")
    print("-" * 62)

    print(f"State:              {trend.display}")
    print(f"Reason:             {trend.reason}")

    print()
    print("TREND CONDITIONS")
    print("-" * 62)

    print(
        f"Price above 50D:    "
        f"{'Yes' if trend.price_above_50 else 'No'}"
    )

    print(
        f"Price above 200D:   "
        f"{'Yes' if trend.price_above_200 else 'No'}"
    )

    print(
        f"50D above 200D:     "
        f"{'Yes' if trend.sma50_above_200 else 'No'}"
    )

    print(
        f"200D rising:        "
        f"{'Yes' if trend.sma200_rising else 'No'}"
    )

    print(
        f"200D falling:       "
        f"{'Yes' if trend.sma200_falling else 'No'}"
    )


def main():
    print()
    print("TickerTrends Real-Stock Test")
    print("============================")

    for ticker in TEST_TICKERS:
        try:
            test_ticker(ticker)

        except Exception as exc:
            print()
            print(f"{ticker}: ERROR")
            print(str(exc))

    print()
    print("=" * 62)
    print("Test complete.")
    print("=" * 62)


if __name__ == "__main__":
    main()
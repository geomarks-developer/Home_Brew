import pandas as pd
import streamlit as st

from screener_engine import (
    MAX_DEBT_EQUITY,
    MAX_EXPENSE_RATIO,
    MAX_FORWARD_PE,
    MAX_PAYOUT,
    MAX_PEG,
    MAX_RSI,
    MIN_AUM,
    MIN_DIVIDEND_YIELD,
    MIN_MARGIN,
    MIN_ROE,
    MIN_RSI,
    MIN_UPSIDE,
    MONTH_LOOKBACK,
)

st.title("📖 Methodology")
st.caption(
    "Reference guide for MarketScope screening rules, scoring, trend indicators, and data interpretation."
)

st.info(
    "MarketScope is a screening and research tool. A passing result reflects the configured rules below, "
    "not a recommendation to buy or sell a security."
)

# =========================================================
# Quick reference
# =========================================================

st.subheader("Screening Models")

stock_col, dividend_col, etf_col = st.columns(3)

with stock_col:
    with st.container(border=True):
        st.markdown("### 📈 Stock Screener")
        st.metric("Maximum Score", "14")
        st.write("Fundamentals + valuation + trend + momentum")
        st.write("**Final pass:** all 8 fundamental tests, price above SMA 200, and Momentum Score ≥ 2")

with dividend_col:
    with st.container(border=True):
        st.markdown("### 💵 Dividend Screener")
        st.metric("Maximum Score", "10")
        st.write("Income + sustainability + trend + momentum")
        st.write("**Final pass:** all 4 dividend tests, price above SMA 200, and Momentum Score ≥ 2")

with etf_col:
    with st.container(border=True):
        st.markdown("### 📊 ETF Screener")
        st.metric("Maximum Score", "5")
        st.write("Fund cost + fund size + trend")
        st.write("**Final pass:** all 5 ETF tests pass")

# =========================================================
# Rules
# =========================================================

st.divider()
st.subheader("Screening Rules")

stock_tab, dividend_tab, etf_tab = st.tabs(
    ["📈 Stocks", "💵 Dividends", "📊 ETFs"]
)

with stock_tab:
    stock_rules = pd.DataFrame([
        ["PEG", f"< {MAX_PEG:g}", "1", "Yes", "Valuation relative to expected growth."],
        ["Forward P/E", f"< {MAX_FORWARD_PE:g}", "1", "Yes", "Forward valuation test."],
        ["Return on Equity", f"> {MIN_ROE:.0%}", "1", "Yes", "Profitability test."],
        ["Profit Margin", f"> {MIN_MARGIN:.0%}", "1", "Yes", "Profitability test."],
        ["Revenue Growth", "> 0%", "1", "Yes", "Requires positive revenue growth."],
        ["Earnings Growth", "> 0%", "1", "Yes", "Requires positive earnings growth."],
        ["Debt to Equity", f"< {MAX_DEBT_EQUITY:g}", "1", "Yes", "Leverage test."],
        ["Target Upside", f"> {MIN_UPSIDE:.0%}", "1", "Yes", "Analyst mean target above current price."],
        ["Above SMA 50", "Price > SMA 50", "1", "Score", "Intermediate trend input."],
        ["Above SMA 200", "Price > SMA 200", "1", "Yes", "Required in final pass."],
        ["Golden Cross", "SMA 50 > SMA 200", "1", "Score", "Trend confirmation."],
        ["RSI", f"{MIN_RSI:g} to {MAX_RSI:g}", "0–2", "Momentum", f"2 points for RSI 50–{MAX_RSI:g}; 1 point for {MIN_RSI:g}–<50."],
        ["MACD", "MACD > Signal", "0–1", "Momentum", "Momentum confirmation point."],
    ], columns=["Metric", "Pass Rule", "Points", "Role", "Notes"])
    st.dataframe(stock_rules, width="stretch", hide_index=True)

with dividend_tab:
    dividend_rules = pd.DataFrame([
        ["Dividend Yield", f"> {MIN_DIVIDEND_YIELD:.1%}", "1", "Yes", "Minimum income yield."],
        ["Payout Ratio", f"< {MAX_PAYOUT:.0%}", "1", "Yes", "Dividend sustainability test."],
        ["Free Cash Flow", "> 0", "1", "Yes", "Requires positive free cash flow."],
        ["Debt to Equity", f"< {MAX_DEBT_EQUITY:g}", "1", "Yes", "Leverage test."],
        ["Above SMA 50", "Price > SMA 50", "1", "Score", "Intermediate trend input."],
        ["Above SMA 200", "Price > SMA 200", "1", "Yes", "Required in final pass."],
        ["Golden Cross", "SMA 50 > SMA 200", "1", "Score", "Trend confirmation."],
        ["RSI", f"{MIN_RSI:g} to {MAX_RSI:g}", "0–2", "Momentum", f"2 points for RSI 50–{MAX_RSI:g}; 1 point for {MIN_RSI:g}–<50."],
        ["MACD", "MACD > Signal", "0–1", "Momentum", "Momentum confirmation point."],
    ], columns=["Metric", "Pass Rule", "Points", "Role", "Notes"])
    st.dataframe(dividend_rules, width="stretch", hide_index=True)

with etf_tab:
    etf_rules = pd.DataFrame([
        ["Expense Ratio", f"< {MAX_EXPENSE_RATIO:.2%}", "1", "Yes", "Fund cost test."],
        ["Assets Under Management", f"> ${MIN_AUM:,.0f}", "1", "Yes", "Fund size test."],
        ["Above SMA 50", "Price > SMA 50", "1", "Yes", "Trend requirement."],
        ["Above SMA 200", "Price > SMA 200", "1", "Yes", "Long-term trend requirement."],
        ["Golden Cross", "SMA 50 > SMA 200", "1", "Yes", "Trend confirmation."],
    ], columns=["Metric", "Pass Rule", "Points", "Required", "Notes"])
    st.dataframe(etf_rules, width="stretch", hide_index=True)

# =========================================================
# Momentum
# =========================================================

st.divider()
st.subheader("Momentum Scoring")

m1, m2 = st.columns(2)
with m1:
    with st.container(border=True):
        st.markdown("### RSI")
        st.write("**2 points:** RSI from 50 through the configured maximum")
        st.write(f"**1 point:** RSI from {MIN_RSI:g} up to, but not including, 50")
        st.write("**0 points:** outside those ranges or unavailable")
        st.caption("The screener calculates RSI using 14 periods.")

with m2:
    with st.container(border=True):
        st.markdown("### MACD")
        st.write("**1 point:** MACD is above the MACD signal line")
        st.write("**0 points:** MACD is not above the signal line or data is unavailable")
        st.caption("The screener uses EMA 12 minus EMA 26 and a 9-period EMA signal line.")

# =========================================================
# Glossary
# =========================================================

st.divider()
st.subheader("Indicator Glossary")

glossary = pd.DataFrame([
    ["PEG", "Valuation", "P/E relative to expected earnings growth", "Lower values receive preference under the configured maximum."],
    ["Forward P/E", "Valuation", "Share price relative to forecast earnings per share", "Must remain below the configured maximum."],
    ["ROE", "Profitability", "Profit earned relative to shareholder equity", "Higher than the configured minimum passes."],
    ["Profit Margin", "Profitability", "Profit retained from revenue", "Must exceed the configured minimum."],
    ["Revenue Growth", "Growth", "Change in company revenue", "Positive growth passes."],
    ["Earnings Growth", "Growth", "Change in company earnings", "Positive growth passes."],
    ["Debt to Equity", "Financial Health", "Debt relative to shareholder equity", "Must remain below the configured maximum."],
    ["Target Upside", "Valuation / Sentiment", "Analyst target relative to current price", "Calculated as target price / current price - 1."],
    ["Dividend Yield", "Income", "Annual dividend income relative to share price", "Compared with the configured minimum yield."],
    ["Payout Ratio", "Income / Sustainability", "Share of earnings paid as dividends", "Must remain below the configured maximum."],
    ["Free Cash Flow", "Cash Flow", "Cash remaining after operating and capital needs", "Positive FCF is required by the dividend test."],
    ["Expense Ratio", "ETF Cost", "Annual fund operating cost relative to assets", "Must remain below the configured maximum."],
    ["AUM", "ETF Size", "Assets under management", "Must exceed the configured minimum."],
    ["SMA 50", "Trend", "Average closing price across 50 sessions", "Price above SMA 50 is an intermediate trend signal."],
    ["SMA 200", "Trend", "Average closing price across 200 sessions", "Used as the long-term trend requirement."],
    ["Golden Cross", "Trend", "SMA 50 is above SMA 200", "Used as bullish trend confirmation."],
    ["RSI", "Momentum", "Speed and magnitude of recent price changes", f"Configured acceptable range is {MIN_RSI:g}–{MAX_RSI:g}."],
    ["MACD", "Momentum / Trend", "Difference between fast and slow exponential moving averages", "Positive confirmation occurs when MACD is above Signal."],
    ["MACD Signal", "Momentum", "Smoothed MACD confirmation line", "Uses a 9-period EMA of MACD."],
    ["Bullish Alignment", "Composite Trend", "Price is above both SMAs and SMA 50 is above SMA 200", "Descriptive trend confirmation."],
    ["Momentum Score", "Composite", "Combined RSI and MACD score", "Range is 0–3."],
    ["Score %", "Composite", "Points earned divided by maximum possible points", "Useful for comparing strength within a screener."],
    ["1 Month Change", "Performance", f"Price change over approximately {MONTH_LOOKBACK} trading days", "Used for heatmap color and performance context."],
], columns=["Indicator", "Category", "What It Measures", "MarketScope Interpretation"])

search = st.text_input("Search glossary", placeholder="RSI, PEG, dividend, SMA...")
if search.strip():
    query = search.strip()
    mask = glossary.astype(str).apply(
        lambda column: column.str.contains(query, case=False, na=False)
    ).any(axis=1)
    glossary = glossary[mask]

st.dataframe(
    glossary,
    width="stretch",
    hide_index=True,
    height=650,
    column_config={
        "Indicator": st.column_config.TextColumn("Indicator", width=150, pinned=True),
        "Category": st.column_config.TextColumn("Category", width=160),
        "What It Measures": st.column_config.TextColumn("What It Measures", width=330),
        "MarketScope Interpretation": st.column_config.TextColumn("MarketScope Interpretation", width=420),
    },
)

# =========================================================
# Data handling notes
# =========================================================

st.divider()
st.subheader("Data & Calculation Notes")

with st.expander("Missing data"):
    st.write(
        "When a required metric is unavailable, its individual test fails and the reason is included in Failed Tests."
    )

with st.expander("Percentage values"):
    st.write(
        "MarketScope keeps percentage metrics as decimal values in the calculation engine and converts them for human-readable display in the Streamlit pages."
    )

with st.expander("Price trend calculations"):
    st.write(
        "Price metrics include SMA 50, SMA 200, RSI, MACD, the MACD signal line, and the MACD histogram."
    )

with st.expander("Heatmaps"):
    st.write(
        f"The one-month heatmaps use the configured {MONTH_LOOKBACK}-trading-day lookback. Heatmap color reflects the one-month price change."
    )

# =========================================================
# Risk disclosures
# =========================================================

st.divider()
st.subheader("Risk Disclosures")

st.warning(
    "MarketScope is for informational, educational, and research purposes only. "
    "It does not provide personalized investment, financial, tax, or legal advice, "
    "and a security passing a screen should not be interpreted as a recommendation to buy, sell, or hold it."
)

r1, r2 = st.columns(2)

with r1:
    with st.container(border=True):
        st.markdown("### Investment Risk")
        st.write(
            "Investing involves risk, including the possible loss of principal. Stocks, dividend-paying securities, "
            "and ETFs can decline in value, and income or distributions can change."
        )
        st.write(
            "Screening scores simplify a set of selected factors. They do not capture every risk that may affect a "
            "company, fund, industry, sector, or market."
        )

    with st.container(border=True):
        st.markdown("### Past Performance")
        st.write(
            "Historical returns, price trends, moving averages, and other past performance information do not "
            "necessarily predict future results."
        )
        st.write(
            "MarketScope performance charts may not reflect every cost, tax, distribution, reinvestment assumption, "
            "or investor-specific circumstance."
        )

with r2:
    with st.container(border=True):
        st.markdown("### Data & Model Limitations")
        st.write(
            "MarketScope relies on third-party market and financial data. Data may be delayed, incomplete, unavailable, "
            "revised, or inaccurate. Always verify important figures using primary or authoritative sources before making a decision."
        )
        st.write(
            "Analyst targets, estimates, ratios, technical indicators, and screening thresholds are inputs to a research model, "
            "not guarantees of future performance."
        )

    with st.container(border=True):
        st.markdown("### Investor Circumstances")
        st.write(
            "An investment that appears attractive under MarketScope's rules may not be appropriate for a particular investor. "
            "Consider objectives, time horizon, liquidity needs, diversification, taxes, fees, financial circumstances, and risk tolerance."
        )

st.caption(
    "Before acting on MarketScope results, review current company or fund disclosures and other authoritative information. "
    "Consider consulting an appropriately qualified professional when individualized guidance is needed."
)


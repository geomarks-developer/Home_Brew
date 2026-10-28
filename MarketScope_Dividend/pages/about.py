from __future__ import annotations

import streamlit as st


st.header("ℹ️ About MarketScope Dividend")
st.caption(
    "A focused research dashboard for exploring and comparing Dividend Aristocrat stocks."
)

st.markdown(
    """
### What is MarketScope Dividend?

**MarketScope Dividend** is a dividend-focused companion to the MarketScope research project. It is designed specifically around a curated universe of Dividend Aristocrat stocks and brings dividend income, dividend growth, company quality, valuation, momentum, and risk into one consistent research workflow.

The goal is not to identify a single "best" dividend stock. Instead, MarketScope Dividend provides several ways to examine the tradeoffs between income, growth, valuation, quality, momentum, and risk.
"""
)

st.divider()

st.subheader("🔎 Research Tools")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
**Dividend Summary**  
Provides a high-level view of the Dividend Aristocrat universe, including yields, dividend growth, sector representation, rankings, and category leaders.

**Dividend Screener**  
Filters the universe using dividend, valuation, quality, momentum, and MarketScope scoring criteria.

**Dividend Heatmap**  
Provides a visual comparison of stocks and sectors using MarketScope scores, dividend metrics, and market performance.

**Stock Explorer**  
Examines an individual stock's dividend profile, fundamentals, technical indicators, price history, and MarketScope scores.
"""
    )

with col2:
    st.markdown(
        """
**Compare Stocks**  
Compares multiple Dividend Aristocrats side-by-side across dividend, valuation, quality, momentum, risk, and historical performance metrics.

**Portfolio Builder**  
Creates a custom Dividend Aristocrat portfolio, supports editable allocations, and estimates portfolio yield, dividend income, sector exposure, risk, and MarketScope characteristics.

**Methodology**  
Documents the scoring framework, component weights, technical calculations, dividend-growth calculations, and rating bands used throughout the application.
"""
    )

st.divider()

st.subheader("🎯 MarketScope Scoring Philosophy")

st.markdown(
    """
MarketScope Dividend combines five research dimensions into an overall score:

- **Dividend**: income, payout sustainability, dividend growth, and consistency
- **Quality**: profitability, cash flow, leverage, and earnings characteristics
- **Value**: relative valuation using several common valuation measures
- **Momentum**: price trend, medium-term returns, and RSI
- **Risk**: beta, volatility, drawdown, and position within the 52-week range

The individual category scores are intended to be reviewed alongside the Overall Score. Two stocks can achieve similar overall results for very different reasons.
"""
)

st.divider()

st.subheader("💵 Dividend-Focused Research")

st.markdown(
    """
Dividend investing involves more than finding the highest available yield. MarketScope Dividend therefore presents yield alongside dividend growth, payout ratio, dividend consistency, company fundamentals, valuation, and risk measures.

The Portfolio Builder extends that approach to a group of holdings by estimating income and calculating weighted portfolio characteristics. These estimates are research aids rather than forecasts or guarantees of future dividend payments.
"""
)

st.divider()

st.subheader("📊 Data and Calculations")

st.markdown(
    """
MarketScope Dividend uses market, company, and dividend information gathered by the application's data engine. The application caches shared data locally so that the Summary, Screener, Heatmap, Explorer, Comparison, and Portfolio pages can reuse the same research dataset.

Derived calculations include moving averages, historical returns, RSI, volatility, maximum drawdown, dividend growth, dividend consistency, valuation measures, category scores, overall scores, and portfolio estimates.

Available market and company data can be incomplete or change over time. A missing data point can therefore affect individual metrics or scores.
"""
)

st.divider()

st.subheader("⚙️ Designed for Exploration")

st.markdown(
    """
MarketScope Dividend is intended to support an iterative research process:

1. Start with the **Summary** to understand the current Dividend Aristocrat universe.
2. Use the **Screener** to narrow the list to stocks matching specific preferences.
3. Use the **Heatmap** to identify broader patterns and sector differences.
4. Investigate individual candidates with **Stock Explorer**.
5. Evaluate alternatives with **Compare Stocks**.
6. Combine candidates in **Portfolio Builder** to examine allocation, income, diversification, and portfolio-level characteristics.
7. Review **Methodology** to understand how MarketScope metrics and scores are constructed.
"""
)

st.divider()

st.subheader("⚠️ Important")

st.warning(
    "MarketScope Dividend is a research tool and does not provide investment, tax, "
    "legal, or financial advice. Scores, rankings, dividend estimates, and portfolio "
    "calculations should not be interpreted as recommendations to buy or sell a security."
)

st.markdown(
    "Dividend payments are not guaranteed. Companies can increase, reduce, suspend, "
    "or eliminate dividends, and investment values can rise or fall."
)

st.caption("MarketScope Dividend · Dividend Aristocrat Research")

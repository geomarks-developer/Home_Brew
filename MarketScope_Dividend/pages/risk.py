from __future__ import annotations

import streamlit as st


st.header("⚠️ MarketScope Dividend Risk Disclosure")
st.caption(
    "Important limitations and risks to consider when using MarketScope Dividend for investment research."
)

st.warning(
    "MarketScope Dividend is an informational research tool. It does not provide "
    "investment, financial, tax, accounting, or legal advice, and its scores and "
    "rankings are not recommendations to buy, hold, or sell any security."
)

st.divider()

st.subheader("📉 Market and Stock Risk")
st.markdown(
    """
Dividend Aristocrats are still individual stocks. Share prices can rise or fall, sometimes substantially, and an investor can lose money.

A company's historical dividend record does not eliminate the risks associated with its business, industry, valuation, financial condition, or the broader stock market.
"""
)

st.divider()

st.subheader("💵 Dividend Risk")
st.markdown(
    """
Dividends are **not guaranteed**. A company may increase, maintain, reduce, suspend, or eliminate its dividend.

A high dividend yield should not automatically be interpreted as a positive signal. Yield can increase because the dividend rises, because the stock price falls, or through a combination of both. MarketScope therefore evaluates dividend yield alongside payout ratio, dividend growth, consistency, quality, valuation, momentum, and risk measures.

Estimated portfolio income in Portfolio Builder is an analytical estimate based on the dividend-yield data available to the application. Actual future income can differ.
"""
)

st.divider()

st.subheader("🧮 Model and Scoring Risk")
st.markdown(
    """
MarketScope scores are quantitative research indicators created from a defined set of metrics and weights. Any scoring model simplifies reality.

Important considerations include:

- A high Overall Score does not guarantee strong investment performance.
- A low score does not mean a security will underperform.
- Changing the metrics, weighting scheme, or comparison universe can change rankings.
- Many component scores are relative to the other stocks currently in the Dividend Aristocrat universe.
- Missing data may receive neutral treatment within portions of the scoring model.
- Two stocks with similar Overall Scores may have substantially different dividend, quality, value, momentum, or risk profiles.

For these reasons, review the individual category scores and underlying financial metrics rather than relying on rank alone.
"""
)

st.divider()

st.subheader("📊 Data Risk")
st.markdown(
    """
MarketScope Dividend depends on third-party market and company data. Source information may be delayed, incomplete, revised, unavailable, or inconsistent between fields.

Calculated values are only as reliable as the underlying data. Missing or unusual source values can affect dividend calculations, valuation ratios, technical indicators, rankings, and portfolio estimates.

Refreshing the MarketScope cache updates the application's research dataset, but a refresh should not be interpreted as verification that every source value is complete or error-free.
"""
)

st.divider()

st.subheader("📈 Historical and Technical Measures")
st.markdown(
    """
Historical returns, moving averages, RSI, volatility, beta, maximum drawdown, and other technical measures describe historical or current market behavior. Historical performance does not guarantee future results.

Technical indicators can change quickly as prices change. MarketScope uses these measures as comparative research inputs rather than forecasts.
"""
)

st.divider()

st.subheader("🧺 Portfolio Builder Limitations")
st.markdown(
    """
Portfolio Builder is an analytical tool, not a brokerage or portfolio-management system.

Portfolio calculations may use fractional-share estimates and user-entered target weights. Estimated yield, dividend income, weighted scores, beta, sector exposure, and other portfolio statistics are approximations based on the data available to MarketScope.

Portfolio Builder does not by itself account for every consideration relevant to an actual portfolio, such as transaction costs, taxes, bid-ask spreads, execution prices, account restrictions, tax lots, personal cash-flow needs, or changes that occur after the dataset was loaded.
"""
)

st.divider()

st.subheader("🌐 Diversification and Concentration")
st.markdown(
    """
Owning multiple Dividend Aristocrats does not automatically create a diversified portfolio. Holdings can still be concentrated in particular sectors, industries, investment styles, or risk factors.

The MarketScope Portfolio Builder displays sector allocation to help evaluate concentration, but sector allocation is only one dimension of diversification.
"""
)

st.divider()

st.subheader("🎯 Personal Suitability")
st.markdown(
    """
MarketScope does not know an investor's complete financial situation, investment objectives, time horizon, income needs, tax circumstances, liquidity requirements, or ability to tolerate losses.

A security or portfolio that appears attractive under the MarketScope methodology may still be inappropriate for a particular investor.
"""
)

st.divider()

st.subheader("✅ Good Research Practice")
st.markdown(
    """
Before making an investment decision, consider reviewing information beyond MarketScope, including company disclosures, financial statements, dividend announcements, valuation, business risks, portfolio concentration, and other information relevant to the investment decision.

MarketScope Dividend is best used as a **screening, comparison, and research aid**, followed by independent analysis.
"""
)

st.info(
    "The Methodology page explains how MarketScope Dividend constructs its category "
    "scores, Overall Score, rankings, and derived calculations."
)

st.caption("MarketScope Dividend · For research and educational use")

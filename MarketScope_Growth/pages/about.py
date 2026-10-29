import streamlit as st


st.title("ℹ️ About MarketScope Growth")
st.caption(
    "A focused research dashboard for screening, comparing, and exploring growth stocks."
)

st.info(
    "MarketScope Growth is designed for research and screening purposes. "
    "Scores and rankings organize market data and should not be treated as predictions "
    "or personalized investment advice."
)

st.markdown("## What MarketScope Growth Does")
st.markdown(
    """
MarketScope Growth brings several stock-research workflows into one Streamlit application. 
The project is centered on evaluating growth companies from multiple perspectives rather than 
relying on a single metric.

The application organizes research around four primary categories:

- **Growth** – revenue and earnings expansion.
- **Quality** – profitability, cash generation, and balance-sheet strength.
- **Valuation** – the price investors are paying for earnings and sales.
- **Momentum** – recent price performance and longer-term price trends.

Those categories are combined into the MarketScope **Overall Score** for easier comparison 
across the configured growth-stock universe.
"""
)

st.markdown("## Research Tools")

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.markdown("### 📊 Market Analysis")
        st.markdown(
            """
- **Summary** provides a high-level view of the growth universe and score leaders.
- **Market Overview** examines breadth, momentum, scores, and sector leadership.
- **Growth Screener** helps identify stocks that rank well under the MarketScope framework.
- **Sectors** provides a sector-level view of the growth universe.
- **Market Calendar** provides a calendar-oriented market research view.
"""
        )

    with st.container(border=True):
        st.markdown("### 🔎 Stock Research")
        st.markdown(
            """
- **Stock Detail** provides a deeper look at an individual company.
- **Compare Stocks** places multiple growth stocks side by side.
- **Watchlist** provides a focused list for stocks you want to monitor.
"""
        )

with col2:
    with st.container(border=True):
        st.markdown("### 🧺 Portfolio & Risk")
        st.markdown(
            """
- **Portfolio Builder** creates model allocations and compares portfolio characteristics.
- **Risk Dashboard** highlights relative valuation, momentum, balance-sheet, and other risk signals.
"""
        )

    with st.container(border=True):
        st.markdown("### 🧮 Methodology")
        st.markdown(
            """
The **Methodology** page explains the scoring framework, including the Growth, Quality, 
Valuation, Momentum, and Overall scores.

It should be used alongside the dashboards when interpreting a company's ranking.
"""
        )

st.markdown("## How to Use the Scores")
st.markdown(
    """
MarketScope scores are intended to make different companies easier to compare on a common 
0–100 scale. A high score means a stock compares favorably under the metrics included in that 
category. It does **not** mean the stock is guaranteed to outperform.

A useful workflow is to start with the **Overall Score**, then examine the individual category 
scores to understand why a company ranks where it does. From there, the Stock Detail, Compare 
Stocks, Portfolio Builder, and Risk Dashboard pages can provide additional context.
"""
)

st.markdown("## Data and Limitations")
st.markdown(
    """
Market and fundamental data can be incomplete, delayed, revised, or unavailable for individual 
securities. MarketScope Growth is designed to tolerate missing values where possible, but data 
availability can still affect scores, rankings, charts, and comparisons.

Growth stocks can also be especially sensitive to changes in earnings expectations, valuation, 
interest rates, and market sentiment. No quantitative screen captures every factor that can 
affect an investment.
"""
)

st.markdown("## Project Purpose")
st.markdown(
    """
MarketScope Growth is a personal research project built to make growth-stock analysis more 
structured, repeatable, and visual. The emphasis is on combining fundamental growth, business 
quality, valuation discipline, momentum, portfolio construction, and risk awareness in one 
research workflow.
"""
)

st.divider()

st.warning(
    "MarketScope Growth is provided for informational and educational purposes only. "
    "Nothing in the application constitutes investment, financial, tax, or legal advice. "
    "Always perform independent research before making investment decisions."
)

st.caption("MarketScope Growth • Growth-stock research and portfolio analysis")

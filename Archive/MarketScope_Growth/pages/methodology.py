from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Methodology | MarketScope Growth",
    page_icon="📘",
    layout="wide",
)

st.title("📘 MarketScope Growth Methodology")
st.caption(
    "How MarketScope Growth evaluates growth stocks using Growth, Quality, "
    "Valuation, and Momentum."
)

st.info(
    "MarketScope Growth is a research and screening framework. Scores are designed "
    "to organize comparable market data, not to predict future returns or provide "
    "personalized investment advice."
)

# =========================================================
# Overview
# =========================================================

st.header("1. Overview")

st.markdown(
    """
MarketScope Growth evaluates each stock across four categories:

- **Growth** — how strongly the company's revenue and earnings are growing.
- **Quality** — profitability, cash generation, and balance-sheet strength.
- **Valuation** — how much investors are paying for the company's earnings and sales.
- **Momentum** — recent price performance and the stock's position relative to longer-term trends.

Each category is converted to a **0–100 score**. The category scores are then combined into an **Overall Score** using the weights configured for the MarketScope Growth model.
"""
)

# =========================================================
# Growth
# =========================================================

st.header("2. Growth Score")

st.markdown(
    """
The Growth Score focuses on fundamental business and earnings expansion. The model uses:

- **Revenue Growth**
- **Earnings Growth**
- **EPS Growth**
- **Forward EPS Growth**

Higher growth generally receives a higher component score. Each available metric is evaluated against the configured growth thresholds and converted to a 0–100 score.

The component scores are combined using the configured Growth weights. If a growth metric is unavailable, MarketScope does **not automatically score the missing value as zero**. Instead, the score is calculated from the available components and the model records how much of the configured Growth weighting was represented by available data.
"""
)

# =========================================================
# Quality
# =========================================================

st.header("3. Quality Score")

st.markdown(
    """
The Quality Score evaluates whether growth is supported by profitable operations, cash generation, and a reasonable balance sheet.

The model considers:

- **Return on Equity (ROE)**
- **Operating Margin**
- **Profit Margin**
- **Free Cash Flow**
- **Debt Control**

Higher ROE and stronger margins receive higher quality scores under the configured thresholds. Positive free cash flow is rewarded because it indicates that the business is generating cash after capital spending.

### Debt Control

Debt is evaluated relative to the size of the company rather than by raw debt alone. MarketScope compares net debt with market capitalization:

**Net Debt Ratio = (Total Debt − Total Cash) / Market Capitalization**

Companies with cash exceeding debt receive the strongest debt-control assessment. Higher net debt relative to market capitalization reduces the debt-control component score.
"""
)

# =========================================================
# Valuation
# =========================================================

st.header("4. Valuation Score")

st.markdown(
    """
The Valuation Score measures the price investors are paying for the company's expected earnings and sales.

The model evaluates:

- **Forward P/E**
- **PEG Ratio**
- **Price-to-Sales**

For these valuation measures, lower positive values generally receive stronger scores. The configured valuation thresholds determine how each metric maps to the 0–100 scale.

Valuation is treated as one part of the complete growth-stock assessment. A company can therefore have exceptional growth and quality characteristics while receiving a weaker Valuation Score when its market price reflects aggressive expectations.
"""
)

# =========================================================
# Momentum
# =========================================================

st.header("5. Momentum Score")

st.markdown(
    """
Momentum measures how the stock itself is behaving in the market. MarketScope uses:

- **6-Month Return**
- **12-Month Return**
- **Price versus the 50-Day Moving Average**
- **Price versus the 200-Day Moving Average**
- **Distance from the 52-Week High**

Positive returns and prices above important moving averages generally improve the Momentum Score. Stocks trading closer to their 52-week highs also receive stronger momentum assessments.

The objective is not simply to reward the stock with the largest recent gain. Multiple trend measurements are combined so that the Momentum Score reflects both intermediate-term performance and the stock's position within its broader price trend.
"""
)

# =========================================================
# Overall score
# =========================================================

st.header("6. Overall Score")

st.markdown(
    """
The four category scores are combined into the final **Overall Score**:

1. Growth Score
2. Quality Score
3. Valuation Score
4. Momentum Score

The relative importance of the four categories is controlled by the category weights in the MarketScope Growth configuration.

Like the category calculations, the Overall Score is designed to work with incomplete data. If one category cannot be calculated, the available category weights are rebalanced across the categories that have usable scores instead of treating the missing category as a zero.
"""
)

# =========================================================
# Coverage
# =========================================================

st.header("7. Data Coverage")

st.markdown(
    """
Market data is not equally complete for every company. MarketScope therefore tracks **coverage** alongside its scores.

Coverage represents the portion of the configured scoring weight supported by available data. The application can track coverage for:

- Growth
- Quality
- Valuation
- Momentum
- Overall Score

A high score with limited coverage should be interpreted more cautiously than a similar score supported by a more complete dataset.
"""
)

# =========================================================
# Market data
# =========================================================

st.header("8. Market Data and Price Metrics")

st.markdown(
    """
MarketScope Growth combines company fundamentals with market-price history.

The market-data pipeline calculates several price-based fields used throughout the application:

- Current Price
- 6-Month Return
- 12-Month Return
- 50-Day Moving Average
- 200-Day Moving Average
- 52-Week High

The application also retrieves company identity information, sector and industry classifications, fundamental information, and available analyst growth estimates.

Missing information is retained as unavailable data rather than automatically replaced with zero. This distinction is important because a missing fundamental value does not necessarily indicate poor company performance.
"""
)

# =========================================================
# Percentage handling
# =========================================================

st.header("9. Percentage Handling")

st.markdown(
    """
Growth rates, profitability measures, and market returns are stored internally as decimal values when provided in that form.

For example:

- `0.20` represents **20%**
- `0.075` represents **7.5%**
- `-0.10` represents **−10%**

Pages convert these decimal values to percentages for display. Keeping the underlying data in decimal form also allows the scoring engine and portfolio calculations to use the same normalized values consistently.
"""
)

# =========================================================
# Risk dashboard
# =========================================================

st.header("10. Risk Dashboard")

st.markdown(
    """
The Risk Dashboard provides a separate view of characteristics that may warrant additional investigation.

Its relative risk analysis can incorporate available signals from areas such as:

- Valuation
- Quality
- Momentum
- Profitability
- Debt
- Recent returns
- MarketScope scores

The dashboard's risk ranking is intended as a **relative research indicator within the selected stock universe**. A higher relative risk score does not mean that a stock will decline, and a lower score does not imply that a stock is safe.
"""
)

# =========================================================
# Portfolio builder
# =========================================================

st.header("11. Portfolio Builder")

st.markdown(
    """
The Portfolio Builder uses MarketScope Growth data to explore hypothetical allocations among selected stocks.

Portfolio-level views can include:

- Position weights
- Dollar allocations
- Estimated shares
- Sector concentration
- Weighted MarketScope scores
- Weighted growth metrics
- Weighted profitability metrics
- Weighted valuation metrics
- Weighted returns

These calculations describe a model allocation only. The Portfolio Builder does not execute trades and does not determine whether a portfolio is appropriate for a particular investor.
"""
)

# =========================================================
# Interpretation
# =========================================================

st.header("12. Interpreting MarketScope Scores")

st.markdown(
    """
MarketScope scores are most useful as a **comparison and research framework** rather than as standalone buy or sell signals.

A high Overall Score can help identify companies where several desirable characteristics occur together. However, investors should still examine the underlying components.

For example:

- Strong Growth + weak Valuation may indicate a rapidly growing but expensive stock.
- Strong Quality + weak Momentum may indicate sound fundamentals with weaker market performance.
- Strong Momentum + weak Quality may indicate strong price behavior that is not equally supported by fundamentals.
- Strong Overall Score + low Coverage means the ranking is based on less complete information.

The category breakdown is therefore just as important as the final Overall Score.
"""
)

# =========================================================
# Limitations
# =========================================================

st.header("13. Important Limitations")

st.markdown(
    """
No quantitative screening system captures every factor that can affect an investment.

MarketScope Growth may not fully reflect:

- Changes that occurred after the latest cached data was retrieved
- Company-specific news or qualitative developments
- Competitive advantages or management quality
- Accounting differences between industries
- Changes in analyst estimates
- Macroeconomic or interest-rate conditions
- Unexpected business, regulatory, or market events

Scores should therefore be treated as the beginning of the research process, not the conclusion.
"""
)

st.warning(
    "MarketScope Growth is provided for informational and research purposes only. "
    "Nothing in the application constitutes personalized investment, financial, tax, "
    "or legal advice."
)

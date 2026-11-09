"""MarketScope Value methodology page."""
from __future__ import annotations

import pandas as pd
import streamlit as st

from config import (
    CATEGORY_WEIGHTS,
    FINANCIAL_STRENGTH_WEIGHTS,
    GROWTH_WEIGHTS,
    MOMENTUM_WEIGHTS,
    QUALITY_WEIGHTS,
    RATING_THRESHOLDS,
    VALUATION_SCORE_RATINGS,
    VALUATION_WEIGHTS,
    VALUE_TRAP_RATINGS,
    VALUE_TRAP_WEIGHTS,
)


def weight_table(weights: dict[str, float], labels: dict[str, str] | None = None) -> pd.DataFrame:
    labels = labels or {}
    return pd.DataFrame(
        {
            "Factor": [labels.get(key, key.replace("_", " ").title()) for key in weights],
            "Weight": [value for value in weights.values()],
        }
    )


def rating_table(thresholds: dict[int, str], score_name: str) -> pd.DataFrame:
    rows = []
    for threshold in sorted(thresholds, reverse=True):
        rows.append({"Minimum Score": threshold, score_name: thresholds[threshold]})
    return pd.DataFrame(rows)


def show() -> None:
    st.title("🧮 Value Methodology")
    st.caption(
        "How MarketScope Value scores valuation, business quality, financial strength, growth, "
        "momentum, and potential value-trap risk."
    )

    st.markdown(
        """
MarketScope Value is designed to answer two separate questions:

1. **Does the stock appear attractively valued relative to its financial characteristics?**
2. **Are there warning signs that the apparent bargain may reflect deterioration or financial risk?**

The first question is represented by the **Overall Value Score**. The second is represented independently by
**Value Trap Risk**. Keeping the two measures separate allows a company to screen as inexpensive while still
showing meaningful warning signals.
"""
    )

    st.divider()
    st.header("Overall Value Score")
    st.write("The Overall Value Score is a 0–100 weighted combination of five category scores.")

    overall_labels = {
        "valuation": "Valuation",
        "quality": "Quality",
        "financial_strength": "Financial Strength",
        "growth": "Growth",
        "momentum": "Momentum",
    }
    overall = weight_table(CATEGORY_WEIGHTS, overall_labels)
    st.dataframe(
        overall,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Weight": st.column_config.NumberColumn("Weight", format="percent"),
        },
    )

    st.info(
        "Valuation receives the largest weight, but a stock cannot rely on cheap multiples alone. "
        "Quality, balance-sheet strength, growth, and momentum provide context for why a stock may be inexpensive."
    )

    st.divider()
    st.header("1. Valuation Score")
    st.write(
        "The Valuation Score favors lower positive valuation multiples and higher positive cash-flow or earnings yields."
    )

    valuation_labels = {
        "forward_pe": "Forward P/E",
        "trailing_pe": "Trailing P/E",
        "price_to_book": "Price / Book",
        "price_to_sales": "Price / Sales",
        "ev_to_ebitda": "EV / EBITDA",
        "fcf_yield": "Free-Cash-Flow Yield",
        "earnings_yield": "Earnings Yield",
    }
    st.dataframe(
        weight_table(VALUATION_WEIGHTS, valuation_labels),
        use_container_width=True,
        hide_index=True,
        column_config={"Weight": st.column_config.NumberColumn("Weight", format="percent")},
    )

    st.markdown(
        """
**Derived valuation measures**

- **FCF Yield** = Free Cash Flow ÷ Market Capitalization
- **Earnings Yield** = 1 ÷ Trailing P/E, when trailing P/E is positive
- Negative or zero valuation multiples are treated as unavailable rather than automatically cheap because the underlying earnings denominator may be negative or otherwise unsuitable for conventional multiple analysis.
"""
    )

    st.subheader("Valuation classifications")
    st.dataframe(
        rating_table(VALUATION_SCORE_RATINGS, "Valuation Classification"),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.header("2. Quality Score")
    st.write("Quality evaluates profitability and cash generation rather than valuation.")
    quality_labels = {
        "roe": "Return on Equity",
        "operating_margin": "Operating Margin",
        "profit_margin": "Profit Margin",
        "free_cash_flow": "Positive Free Cash Flow",
        "cash_conversion": "Cash Conversion",
    }
    st.dataframe(
        weight_table(QUALITY_WEIGHTS, quality_labels),
        use_container_width=True,
        hide_index=True,
        column_config={"Weight": st.column_config.NumberColumn("Weight", format="percent")},
    )
    st.markdown(
        "**Cash Conversion** is calculated as Free Cash Flow ÷ Operating Cash Flow when operating cash flow is positive."
    )

    st.divider()
    st.header("3. Financial Strength Score")
    st.write("Financial Strength focuses on leverage, liquidity, and balance-sheet flexibility.")
    strength_labels = {
        "net_debt_to_market_cap": "Net Debt / Market Cap",
        "debt_to_equity": "Debt / Equity",
        "current_ratio": "Current Ratio",
        "cash_to_debt": "Cash / Debt",
    }
    st.dataframe(
        weight_table(FINANCIAL_STRENGTH_WEIGHTS, strength_labels),
        use_container_width=True,
        hide_index=True,
        column_config={"Weight": st.column_config.NumberColumn("Weight", format="percent")},
    )
    st.markdown(
        "**Net Debt / Market Cap** = (Total Debt − Total Cash) ÷ Market Capitalization. "
        "Negative values indicate net cash when the required data is available."
    )

    st.divider()
    st.header("4. Growth Score")
    st.write(
        "Growth has a smaller role than in MarketScope Growth. In this model, growth primarily helps distinguish "
        "healthy inexpensive businesses from companies whose fundamentals are deteriorating."
    )
    growth_labels = {
        "revenue_growth": "Revenue Growth",
        "earnings_growth": "Earnings Growth",
        "eps_growth": "EPS Growth",
        "forward_eps_growth": "Forward EPS Growth",
    }
    st.dataframe(
        weight_table(GROWTH_WEIGHTS, growth_labels),
        use_container_width=True,
        hide_index=True,
        column_config={"Weight": st.column_config.NumberColumn("Weight", format="percent")},
    )

    st.divider()
    st.header("5. Momentum Score")
    st.write(
        "Momentum is used as a secondary confirmation signal. It does not determine whether a stock is cheap, "
        "but it helps identify whether price behavior remains persistently weak."
    )
    momentum_labels = {
        "return_6m": "6-Month Return",
        "return_12m": "12-Month Return",
        "above_50dma": "Price vs. 50-Day Average",
        "above_200dma": "Price vs. 200-Day Average",
        "distance_52w_high": "Distance from 52-Week High",
    }
    st.dataframe(
        weight_table(MOMENTUM_WEIGHTS, momentum_labels),
        use_container_width=True,
        hide_index=True,
        column_config={"Weight": st.column_config.NumberColumn("Weight", format="percent")},
    )

    st.divider()
    st.header("⚠️ Value Trap Risk")
    st.write(
        "Value Trap Risk is separate from the Overall Value Score. A higher number means more warning evidence; "
        "a lower number means fewer detected warning signals."
    )

    trap_labels = {
        "negative_revenue_growth": "Revenue Deterioration",
        "negative_earnings_growth": "Earnings Deterioration",
        "negative_free_cash_flow": "Negative Free Cash Flow",
        "weak_profitability": "Weak Profitability",
        "high_net_debt": "High Net Debt",
        "below_200dma": "Below 200-Day Average",
        "weak_12m_return": "Weak 12-Month Return",
        "low_quality_score": "Low Quality Score",
    }
    st.dataframe(
        weight_table(VALUE_TRAP_WEIGHTS, trap_labels),
        use_container_width=True,
        hide_index=True,
        column_config={"Weight": st.column_config.NumberColumn("Weight", format="percent")},
    )

    st.markdown(
        """
The risk model looks for several different failure modes rather than treating a low valuation multiple as a warning by itself.
A stock can therefore have both a **high Valuation Score** and a **high Value Trap Risk**.

The dashboard uses this distinction to separate:

- **Attractive / Lower Risk:** stronger valuation evidence with fewer detected warning signs.
- **Cheap but Risky:** attractive valuation evidence accompanied by elevated deterioration, leverage, profitability, cash-flow, or momentum risk.
"""
    )

    st.subheader("Value Trap classifications")
    st.dataframe(
        rating_table(VALUE_TRAP_RATINGS, "Risk Classification"),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.header("Missing Data and Score Coverage")
    st.markdown(
        """
MarketScope Value does not automatically assign a poor score when a metric is unavailable.
For each category:

1. Available component scores are multiplied by their configured weights.
2. Missing components are excluded.
3. The weights of the remaining components are normalized.
4. A **Coverage** value records how much of the configured factor weight had usable data.

A score with limited coverage should be treated with more caution than a similarly ranked company with broad factor coverage.
"""
    )

    st.divider()
    st.header("Overall Ratings")
    st.dataframe(
        rating_table(RATING_THRESHOLDS, "MarketScope Rating"),
        use_container_width=True,
        hide_index=True,
    )

    st.divider()
    st.header("How to Read MarketScope Value")
    interpretation = pd.DataFrame(
        [
            {
                "Valuation": "High",
                "Trap Risk": "Low",
                "Interpretation": "Potentially attractive value candidate for deeper research",
            },
            {
                "Valuation": "High",
                "Trap Risk": "High",
                "Interpretation": "Looks inexpensive, but the model detects significant warning signals",
            },
            {
                "Valuation": "Low",
                "Trap Risk": "Low",
                "Interpretation": "Business may appear healthier, but valuation is less compelling",
            },
            {
                "Valuation": "Low",
                "Trap Risk": "High",
                "Interpretation": "Weak combination in the current quantitative framework",
            },
        ]
    )
    st.dataframe(interpretation, use_container_width=True, hide_index=True)

    st.divider()
    st.header("Important Limitations")
    st.markdown(
        """
- Scores are quantitative screening indicators, not estimates of intrinsic value.
- Valuation norms differ across sectors, industries, business models, and economic cycles.
- Financial-company accounting can make some conventional leverage and enterprise-value measures less comparable with non-financial companies.
- Historical price momentum can reverse quickly.
- One-time accounting items can distort earnings, margins, growth, and cash flow.
- Missing or stale source data can reduce score coverage or affect classifications.
- The model does not incorporate every qualitative factor, including management quality, competitive advantages, regulatory changes, litigation, capital-allocation decisions, or future strategic developments.
"""
    )

    st.caption(
        "MarketScope Value is intended for informational and educational research. "
        "The methodology should be used as a starting point for deeper company analysis, not as investment advice."
    )


show()

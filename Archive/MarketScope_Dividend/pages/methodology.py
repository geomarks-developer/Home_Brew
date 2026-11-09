from __future__ import annotations

import pandas as pd
import streamlit as st

from config import (
    DIVIDEND_WEIGHTS,
    MOMENTUM_WEIGHTS,
    QUALITY_WEIGHTS,
    RISK_WEIGHTS,
    SCORE_WEIGHTS,
    VALUE_WEIGHTS,
)


st.header("🧮 MarketScope Dividend Methodology")
st.caption(
    "How MarketScope Dividend evaluates Dividend Aristocrats across income, "
    "quality, valuation, momentum, and risk."
)

st.info(
    "MarketScope Dividend is a research and ranking framework. Scores are designed "
    "to make stocks easier to compare within the Dividend Aristocrat universe. "
    "They are not investment recommendations or predictions of future returns."
)


# ---------------------------------------------------------
# Overall score
# ---------------------------------------------------------

st.subheader("Overall MarketScope Dividend Score")

st.markdown(
    "The **Overall Score** ranges from 0 to 100 and combines five category scores. "
    "A higher score means a stock ranks more favorably under the current MarketScope "
    "Dividend methodology."
)

overall_labels = {
    "dividend": "Dividend",
    "quality": "Quality",
    "value": "Value",
    "momentum": "Momentum",
    "risk": "Risk",
}

overall_df = pd.DataFrame(
    [
        {
            "Category": overall_labels.get(name, name.title()),
            "Weight": weight * 100,
        }
        for name, weight in SCORE_WEIGHTS.items()
    ]
)

st.dataframe(
    overall_df,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Category": st.column_config.TextColumn("Category"),
        "Weight": st.column_config.NumberColumn("Weight", format="%.0f%%"),
    },
)


# ---------------------------------------------------------
# Component tables
# ---------------------------------------------------------

st.divider()
st.subheader("Category Components")

component_labels = {
    "yield": "Dividend Yield",
    "payout_ratio": "Payout Ratio",
    "dividend_growth": "5-Year Dividend Growth",
    "dividend_consistency": "Dividend Consistency",
    "roe": "Return on Equity",
    "profit_margin": "Profit Margin",
    "free_cash_flow": "Free Cash Flow",
    "debt_to_equity": "Debt to Equity",
    "earnings_quality": "Earnings Growth",
    "pe_ratio": "Trailing P/E",
    "forward_pe": "Forward P/E",
    "peg_ratio": "PEG Ratio",
    "price_to_book": "Price to Book",
    "price_to_fcf": "Price to Free Cash Flow",
    "price_vs_sma50": "Price vs. 50-Day SMA",
    "price_vs_sma200": "Price vs. 200-Day SMA",
    "six_month_return": "6-Month Return",
    "one_year_return": "1-Year Return",
    "rsi": "RSI",
    "beta": "Beta",
    "volatility": "Annualized Volatility",
    "max_drawdown": "Maximum Drawdown",
    "52_week_position": "52-Week Position",
}


def component_table(weights: dict[str, float]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Metric": component_labels.get(name, name.replace("_", " ").title()),
                "Weight": weight * 100,
            }
            for name, weight in weights.items()
        ]
    )


def show_component_table(weights: dict[str, float]) -> None:
    st.dataframe(
        component_table(weights),
        hide_index=True,
        use_container_width=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric"),
            "Weight": st.column_config.NumberColumn("Weight", format="%.0f%%"),
        },
    )


tab_dividend, tab_quality, tab_value, tab_momentum, tab_risk = st.tabs(
    ["💵 Dividend", "🏆 Quality", "💲 Value", "📈 Momentum", "🛡️ Risk"]
)

with tab_dividend:
    st.markdown(
        "The Dividend Score emphasizes current income, payout sustainability, "
        "dividend growth, and consistency."
    )
    show_component_table(DIVIDEND_WEIGHTS)
    st.markdown(
        "**Payout Ratio:** the scoring model favors a payout ratio near 55%. "
        "The score declines as the payout ratio moves farther from that target, "
        "and payout ratios above 120% receive a payout-ratio component score of zero."
    )
    st.markdown(
        "**Dividend Consistency:** calculated from recent annual dividend changes. "
        "Years without a material dividend reduction improve the consistency result."
    )

with tab_quality:
    st.markdown(
        "The Quality Score compares profitability, cash generation, balance-sheet "
        "leverage, and earnings growth across the Dividend Aristocrat universe."
    )
    show_component_table(QUALITY_WEIGHTS)

with tab_value:
    st.markdown(
        "The Value Score rewards comparatively lower positive valuation multiples. "
        "Non-positive valuation multiples are treated as unavailable for relative ranking."
    )
    show_component_table(VALUE_WEIGHTS)

with tab_momentum:
    st.markdown(
        "The Momentum Score combines trend, medium-term performance, and RSI. "
        "Price strength relative to the 50-day and 200-day moving averages and stronger "
        "6-month and 1-year returns receive higher relative scores."
    )
    show_component_table(MOMENTUM_WEIGHTS)
    st.markdown(
        "**RSI:** MarketScope uses a target-based RSI score centered around 55 rather "
        "than simply rewarding the highest RSI reading."
    )

with tab_risk:
    st.markdown(
        "The Risk Score is constructed so that a higher score represents a more favorable "
        "risk profile under the model. It considers beta, volatility, drawdown, and the "
        "stock's position within its 52-week price range."
    )
    show_component_table(RISK_WEIGHTS)
    st.markdown(
        "**Beta:** the model uses a target-based score centered around 0.85. "
        "**Volatility:** lower values rank more favorably. "
        "**Maximum Drawdown:** less severe drawdowns rank more favorably."
    )


# ---------------------------------------------------------
# Relative scoring
# ---------------------------------------------------------

st.divider()
st.subheader("How Relative Scoring Works")

st.markdown(
    "Many MarketScope components use **percentile ranking** within the current Dividend "
    "Aristocrat universe. For a higher-is-better metric, stronger values receive higher "
    "percentile scores. For a lower-is-better metric, such as valuation multiples or "
    "volatility, lower values receive higher percentile scores."
)

st.markdown(
    "Missing values are generally assigned a neutral component score of **50** rather "
    "than automatically receiving the best or worst score. This reduces the impact of "
    "isolated missing data while still allowing the stock to receive a composite score."
)


# ---------------------------------------------------------
# Technical calculations
# ---------------------------------------------------------

st.divider()
st.subheader("Price and Technical Calculations")

technical_rows = pd.DataFrame(
    [
        ["50-Day SMA", "Average closing price over the most recent 50 trading sessions."],
        ["200-Day SMA", "Average closing price over the most recent 200 trading sessions."],
        ["RSI", "14-period relative strength calculation using exponentially weighted gains and losses."],
        ["1M Return", "Price return over approximately 21 trading sessions."],
        ["3M Return", "Price return over approximately 63 trading sessions."],
        ["6M Return", "Price return over approximately 126 trading sessions."],
        ["1Y Return", "Price return over approximately 252 trading sessions."],
        ["Volatility", "Standard deviation of daily returns annualized using the square root of 252."],
        ["Maximum Drawdown", "Largest decline from a previous running price high in the available history."],
        ["52-Week Position", "Current price position between the trailing 52-week low and high."],
    ],
    columns=["Metric", "Method"],
)

st.dataframe(
    technical_rows,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Metric": st.column_config.TextColumn("Metric", width="medium"),
        "Method": st.column_config.TextColumn("Method", width="large"),
    },
)


# ---------------------------------------------------------
# Dividend calculations
# ---------------------------------------------------------

st.divider()
st.subheader("Dividend Calculations")

st.markdown(
    "Dividend history is grouped by calendar year. MarketScope calculates dividend "
    "growth from annual dividend totals and uses the available annual history to estimate "
    "1-year, 3-year, and 5-year compound growth rates. An incomplete current calendar "
    "year may be excluded from the annual-growth calculation."
)

st.markdown(
    "Dividend Yield is maintained separately from Dividend Rate. Dividend Rate represents "
    "the annual dividend amount per share, while Dividend Yield expresses dividend income "
    "relative to the stock price."
)


# ---------------------------------------------------------
# Rating bands
# ---------------------------------------------------------

st.divider()
st.subheader("Overall Score Rating Bands")

ratings = pd.DataFrame(
    [
        ["Excellent", "Above 85"],
        ["Very Good", "Above 70 through 85"],
        ["Good", "Above 55 through 70"],
        ["Fair", "Above 40 through 55"],
        ["Weak", "40 or below"],
    ],
    columns=["Rating", "Overall Score"],
)

st.dataframe(ratings, hide_index=True, use_container_width=True)


# ---------------------------------------------------------
# Interpretation
# ---------------------------------------------------------

st.divider()
st.subheader("Using the Scores")

st.markdown(
    "MarketScope is most useful as a **comparison and screening framework**. A strong "
    "Overall Score can come from different combinations of income, quality, valuation, "
    "momentum, and risk. For that reason, the category scores should be reviewed alongside "
    "the Overall Score rather than relying on rank alone."
)

st.warning(
    "The methodology does not account for every factor that can affect an investment. "
    "Market prices, dividends, company fundamentals, and source data can change. Always "
    "perform additional research before making an investment decision."
)

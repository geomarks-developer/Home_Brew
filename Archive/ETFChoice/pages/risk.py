import streamlit as st


# =========================================================
# HEADER
# =========================================================

st.title("⚠️ Risk Disclosure")

st.caption(
    "Important information about the limitations, risks, "
    "and intended use of MarketScope ETF."
)


# =========================================================
# PRIMARY DISCLAIMER
# =========================================================

st.warning(
    """
    **MarketScope ETF is provided for informational and
    educational purposes only.**

    Nothing presented by this application should be interpreted
    as investment, financial, tax, accounting, or legal advice.

    MarketScope ETF does not make recommendations to buy, sell,
    or hold any security.
    """
)


# =========================================================
# INVESTMENT RISK
# =========================================================

st.markdown("## Investment Risk")

st.write(
    """
    Investing involves risk. The value of ETFs and other
    investments can rise or fall, and investors may lose money.

    Historical performance, technical indicators, rankings,
    relative-strength calculations, and MarketScope scores
    do not guarantee future investment results.
    """
)


# =========================================================
# ETF RISKS
# =========================================================

st.markdown("---")

st.markdown("## ETF Risks")

st.write(
    """
    ETFs can be exposed to different types and levels of risk
    depending on their investment objectives, holdings,
    strategies, and underlying markets.
    """
)

st.markdown(
    """
    Risks may include:

    - Market risk
    - Sector or industry concentration
    - Interest-rate risk
    - Credit risk
    - International-market exposure
    - Currency exposure
    - Liquidity risk
    - Commodity exposure
    - Investment-strategy risk
    """
)

st.write(
    """
    ETFs within the same MarketScope category should not be
    assumed to have identical investment objectives, holdings,
    risk characteristics, or expected behavior.
    """
)


# =========================================================
# DIVERSIFICATION
# =========================================================

st.markdown("---")

st.markdown("## Diversification")

st.write(
    """
    Holding multiple ETFs does not automatically ensure adequate
    diversification.

    ETFs can own overlapping securities, sectors, industries,
    countries, asset classes, or investment factors.

    MarketScope categories are intended to organize ETFs for
    analysis. They should not be interpreted as guarantees that
    ETFs assigned to different categories have independent
    investment exposures.
    """
)


# =========================================================
# MARKET PRICE
# =========================================================

st.markdown("---")

st.markdown("## Market Price and Fund Value")

st.write(
    """
    ETFs trade on exchanges at market prices.

    The price at which an ETF trades can differ from the value
    of the assets held by the fund. Market conditions, trading
    activity, liquidity, and other factors can affect ETF prices.
    """
)


# =========================================================
# HISTORICAL PERFORMANCE
# =========================================================

st.markdown("---")

st.markdown("## Historical Performance")

st.write(
    """
    MarketScope relies heavily on historical market information.

    Historical returns are backward-looking and do not predict
    future performance.

    ETFs that have performed strongly during the periods measured
    by MarketScope may subsequently underperform. ETFs that have
    performed poorly may subsequently outperform.
    """
)


# =========================================================
# TECHNICAL ANALYSIS
# =========================================================

st.markdown("---")

st.markdown("## Technical Indicators")

st.write(
    """
    MarketScope uses technical measures including moving averages,
    RSI, momentum, distance from 52-week highs, volatility, and
    maximum drawdown.

    Technical indicators describe historical market behavior.
    They can produce false, conflicting, or delayed signals and
    should not be relied upon as predictions of future prices.
    """
)


# =========================================================
# MARKETSCOPE SCORES
# =========================================================

st.markdown("---")

st.markdown("## MarketScope Scores and Rankings")

st.write(
    """
    MarketScope scores are quantitative research tools created
    specifically for this application.

    ETF Score, Momentum Score, Trend Score, Risk Score,
    Liquidity Score, Cost Score, Dividend Score, and Sector Score
    are not ratings issued by an ETF provider, investment adviser,
    broker, exchange, or regulatory organization.
    """
)

st.write(
    """
    A higher MarketScope score means that an ETF ranked more
    favorably under the application's current methodology.

    It does not mean that the ETF is guaranteed to outperform,
    is appropriate for a particular investor, or has less risk
    than another investment.
    """
)


# =========================================================
# RELATIVE STRENGTH
# =========================================================

st.markdown("---")

st.markdown("## Relative Strength")

st.write(
    """
    MarketScope compares selected ETF returns with SPY as its
    primary benchmark.

    Relative strength describes historical performance relative
    to that benchmark. Outperformance during a historical period
    does not imply future outperformance.
    """
)


# =========================================================
# SECTOR ANALYSIS
# =========================================================

st.markdown("---")

st.markdown("## Sector Rankings")

st.write(
    """
    Sector rankings identify relative historical strength under
    the MarketScope methodology.

    A sector identified as a leader may subsequently weaken,
    while a lagging sector may subsequently strengthen.

    Sector leadership and rotation classifications should therefore
    be interpreted as descriptions of current and historical market
    conditions rather than forecasts.
    """
)


# =========================================================
# PORTFOLIO BUILDER
# =========================================================

st.markdown("---")

st.markdown("## Portfolio Builder")

st.write(
    """
    Portfolios created by the MarketScope Portfolio Builder are
    hypothetical model portfolios.

    The portfolio models use predefined allocation percentages and
    MarketScope rankings. They are not customized for any individual
    investor.
    """
)

st.markdown(
    """
    The Portfolio Builder does **not** consider an individual's:

    - Age
    - Income
    - Net worth
    - Investment objectives
    - Time horizon
    - Tax circumstances
    - Existing investments
    - Retirement needs
    - Liquidity requirements
    - Risk tolerance
    - Other financial circumstances
    """
)

st.write(
    """
    The terms Conservative, Balanced, Growth, Income, and Aggressive
    are descriptive names used by MarketScope for its predefined
    allocation models. They should not be interpreted as an
    assessment that a particular model is appropriate for an
    individual investor.
    """
)


# =========================================================
# HYPOTHETICAL RESULTS
# =========================================================

st.markdown("---")

st.markdown("## Hypothetical Portfolio Results")

st.write(
    """
    Portfolio values and investment comparisons shown within
    MarketScope may be hypothetical.

    The Growth of Investment comparisons assume the same initial
    investment in each ETF so that historical performance can be
    compared on a common basis.

    These calculations do not represent an actual investment
    account.
    """
)


# =========================================================
# DATA RISKS
# =========================================================

st.markdown("---")

st.markdown("## Data Limitations")

st.write(
    """
    MarketScope depends on third-party market data.

    Data may occasionally be unavailable, incomplete, stale,
    delayed, inaccurate, or inconsistent.

    MarketScope calculations may also be affected by missing
    historical prices, unavailable ETF metadata, corporate actions,
    data-processing errors, or changes in third-party data services.
    """
)

st.write(
    """
    Users should independently verify important information before
    making investment decisions.
    """
)


# =========================================================
# FUND INFORMATION
# =========================================================

st.markdown("---")

st.markdown("## ETF Fund Information")

st.write(
    """
    Expense ratios, dividend yields, assets, classifications, and
    other fund characteristics may change over time.

    Information displayed by MarketScope should be verified against
    current information published by the ETF provider before making
    an investment decision.
    """
)


# =========================================================
# CACHING
# =========================================================

st.markdown("---")

st.markdown("## Cached Market Data")

st.write(
    """
    MarketScope uses cached market data to improve performance and
    reduce unnecessary repeated data requests.

    As a result, information displayed by the application may not
    represent real-time market prices.

    The application should not be used as a real-time trading system
    or order-entry platform.
    """
)


# =========================================================
# SOFTWARE LIMITATIONS
# =========================================================

st.markdown("---")

st.markdown("## Software Limitations")

st.write(
    """
    MarketScope ETF is software and may contain bugs, calculation
    errors, programming errors, configuration errors, or other
    technical issues.

    Application availability and functionality are not guaranteed.

    Results should be independently reviewed when they are being
    used to support financial decisions.
    """
)


# =========================================================
# INDEPENDENT RESEARCH
# =========================================================

st.markdown("---")

st.markdown("## Independent Research")

st.info(
    """
    Before investing in an ETF, review the ETF's current prospectus,
    investment objective, holdings, strategy, fees, risks, and other
    official fund information.

    MarketScope should be used as one research tool rather than as
    the sole basis for an investment decision.
    """
)


# =========================================================
# FINAL NOTICE
# =========================================================

st.markdown("---")

st.markdown("## Final Notice")

st.warning(
    """
    **By using MarketScope ETF, users acknowledge that investment
    decisions and their resulting gains or losses remain the
    responsibility of the investor.**

    MarketScope ETF provides analytical information and does not
    guarantee investment performance or outcomes.
    """
)
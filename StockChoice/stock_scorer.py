"""
StockChoice Stock Scorer

End-to-end stock scoring engine.

Workflow

1. Load cached data
2. Download missing data
3. Calculate factor scores
4. Calculate strategy score
5. Return StockScore object
"""

from __future__ import annotations

import yfinance as yf

from stock_engine import (
    FactorScores,
    build_stock_score,
)

from factors.growth import (
    build_growth_score_from_yfinance,
)

from factors.quality import (
    build_quality_score_from_yfinance,
)

from factors.value import (
    build_value_score_from_yfinance,
)

from factors.dividend import (
    build_dividend_score_from_yfinance,
)

from factors.momentum import (
    calculate_momentum_score,
)

from factors.risk import (
    calculate_risk_score,
)

from technical import (
    calculate_technical_metrics,
)

from cache_manager import (
    get_cached_fundamentals,
    save_fundamentals,
    get_cached_history,
    save_history,
    get_cached_score,
    save_score,
)


# ============================================================
# DATA LOADER
# ============================================================

def load_stock_data(
    ticker: str
) -> tuple[dict, object]:

    info = get_cached_fundamentals(
        ticker
    )

    history = get_cached_history(
        ticker
    )

    if info is None or history is None:

        stock = yf.Ticker(
            ticker
        )

        info = stock.info

        history = stock.history(
            period="5y",
            auto_adjust=True,
        )

        save_fundamentals(
            ticker,
            info
        )

        save_history(
            ticker,
            history
        )

    return info, history


# ============================================================
# SCORE STOCK
# ============================================================

def score_stock(
    ticker: str,
    strategy: str = "garp",
    years_of_dividend_growth: int | None = None,
):

    #
    # Score cache retrieval disabled for now.
    #
    # cached = get_cached_score(
    #     ticker,
    #     strategy,
    # )
    #
    # if cached is not None:
    #     return cached

    try:

        info, history = load_stock_data(
            ticker.upper()
        )

    except Exception as ex:

        raise Exception(
            f"Unable to load data for "
            f"{ticker}: {ex}"
        )

    #
    # Growth
    #
    growth_score, growth_details = (
        build_growth_score_from_yfinance(
            info
        )
    )

    #
    # Quality
    #
    quality_score, quality_details = (
        build_quality_score_from_yfinance(
            info
        )
    )

    #
    # Value
    #
    value_score, value_details = (
        build_value_score_from_yfinance(
            info
        )
    )

    #
    # Dividend
    #
    dividend_score, dividend_details = (
        build_dividend_score_from_yfinance(
            info,
            years_of_dividend_growth
        )
    )

    #
    # Momentum
    #
    momentum_score, momentum_details = (
        calculate_momentum_score(
            history
        )
    )

    #
    # Risk
    #
    risk_score, risk_details = (
        calculate_risk_score(
            history_df=history,
            beta=info.get("beta"),
            debt_to_equity=info.get(
                "debtToEquity"
            ),
        )
    )

    #
    # Technical Summary
    #
    technical = (
        calculate_technical_metrics(
            history
        )
    )

    #
    # Factor Scores
    #
    factor_scores = FactorScores(

        growth=growth_score,

        quality=quality_score,

        value=value_score,

        dividend=dividend_score,

        momentum=momentum_score,

        risk=risk_score,
    )

    #
    # Build Final Stock Score
    #
    stock_score = build_stock_score(

        ticker=ticker.upper(),

        strategy_key=strategy,

        factor_scores=factor_scores,

        trend_status=
            technical.trend_status,
    )

    #
    # Details Dictionary
    #
    details = {

        "growth":
            growth_details,

        "quality":
            quality_details,

        "value":
            value_details,

        "dividend":
            dividend_details,

        "momentum":
            momentum_details,

        "risk":
            risk_details,

        "technical": {

            "price":
                technical.current_price,

            "sma50":
                technical.sma50,

            "sma200":
                technical.sma200,

            "pct_above_sma50":
                technical.pct_above_sma50,

            "pct_above_sma200":
                technical.pct_above_sma200,

            "trend_status":
                technical.trend_status,
        },
    }

    #
    # Save score cache
    #
    try:

        save_score(
            ticker=ticker,
            strategy=strategy,
            stock_score=stock_score,
            details=details,
        )

    except Exception as ex:

        print(
            f"Unable to cache score for "
            f"{ticker}: {ex}"
        )

    return stock_score, details


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    score, details = score_stock(
        ticker="MSFT",
        strategy="garp"
    )

    print()
    print("Ticker:", score.ticker)
    print("Strategy:", score.strategy)
    print()

    print(
        "Strategy Score:",
        score.strategy_score
    )

    print(
        "Rating:",
        score.rating
    )

    print(
        "Trend:",
        score.trend_status
    )

    print()

    print(
        "Growth:",
        score.factor_scores.growth
    )

    print(
        "Quality:",
        score.factor_scores.quality
    )

    print(
        "Value:",
        score.factor_scores.value
    )

    print(
        "Dividend:",
        score.factor_scores.dividend
    )

    print(
        "Momentum:",
        score.factor_scores.momentum
    )

    print(
        "Risk:",
        score.factor_scores.risk
    )
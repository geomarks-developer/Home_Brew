import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    DEFAULT_PORTFOLIO_VALUE,
    ETF_CATEGORY_LOOKUP,
    PORTFOLIO_MODELS,
)


# =========================================================
# PAGE HEADER
# =========================================================

st.title("💼 ETF Portfolio Builder")

st.caption(
    "Build a diversified ETF portfolio using MarketScope "
    "rankings and predefined allocation models."
)

st.info(
    "The Portfolio Builder is a research tool. "
    "Portfolio selections are based on MarketScope ETF rankings "
    "and are not personalized investment recommendations."
)


# =========================================================
# LOAD SHARED DATA
# =========================================================

market_data = st.session_state.get("market_data")

if market_data is None:
    st.error(
        "Shared MarketScope ETF data is not loaded. "
        "Restart the application."
    )
    st.stop()


etf_df = market_data.get(
    "etf_df",
    pd.DataFrame(),
).copy()


if etf_df.empty:
    st.warning(
        "ETF analysis data is currently unavailable."
    )
    st.stop()


# =========================================================
# HELPERS
# =========================================================

def safe_number(
    value,
    default=np.nan,
):
    """
    Convert a value to float when possible.
    """

    try:
        value = float(value)

        if np.isfinite(value):
            return value

    except (TypeError, ValueError):
        pass

    return default


def ticker_has_category(
    ticker: str,
    category: str,
) -> bool:
    """
    Determine whether an ETF belongs to a MarketScope category.
    """

    categories = ETF_CATEGORY_LOOKUP.get(
        ticker,
        [],
    )

    return category in categories


def get_category_candidates(
    results: pd.DataFrame,
    category: str,
) -> pd.DataFrame:
    """
    Return ranked ETFs belonging to a particular category.
    """

    candidates = results.copy()

    candidates = candidates[
        candidates["Ticker"].apply(
            lambda ticker:
                ticker_has_category(
                    ticker,
                    category,
                )
        )
    ]


    if candidates.empty:
        return candidates


    if "Data Available" in candidates.columns:

        candidates = candidates[
            candidates["Data Available"]
            == True
        ]


    if "ETF Score" in candidates.columns:

        candidates["ETF Score"] = (
            pd.to_numeric(
                candidates["ETF Score"],
                errors="coerce",
            )
        )

        candidates = candidates.sort_values(
            "ETF Score",
            ascending=False,
            na_position="last",
        )


    return candidates.reset_index(
        drop=True
    )


def build_portfolio(
    results: pd.DataFrame,
    model_name: str,
    portfolio_value: float,
) -> pd.DataFrame:
    """
    Construct a MarketScope ETF portfolio.

    The highest-ranked available ETF from each allocation
    category is selected.

    Duplicate ETFs are avoided whenever another qualifying
    ETF is available.
    """

    allocation_model = PORTFOLIO_MODELS[
        model_name
    ]

    selected_tickers = set()

    rows = []


    for category, weight in (
        allocation_model.items()
    ):

        candidates = get_category_candidates(
            results,
            category,
        )


        if candidates.empty:
            continue


        # Prefer an ETF not already selected.
        unused_candidates = candidates[
            ~candidates["Ticker"].isin(
                selected_tickers
            )
        ]


        if not unused_candidates.empty:

            selected = (
                unused_candidates.iloc[0]
            )

        else:

            selected = candidates.iloc[0]


        ticker = str(
            selected["Ticker"]
        )

        selected_tickers.add(
            ticker
        )


        price = safe_number(
            selected.get(
                "Price"
            )
        )


        target_allocation = (
            portfolio_value
            * weight
        )


        shares = 0

        invested_amount = 0.0


        if (
            pd.notna(price)
            and price > 0
        ):

            shares = int(
                target_allocation
                // price
            )

            invested_amount = (
                shares
                * price
            )


        rows.append(
            {
                "Category":
                    category,

                "Ticker":
                    ticker,

                "Weight":
                    weight * 100,

                "ETF Score":
                    safe_number(
                        selected.get(
                            "ETF Score"
                        )
                    ),

                "Trend":
                    str(
                        selected.get(
                            "Trend",
                            "N/A",
                        )
                    ),

                "Price":
                    price,

                "Target Allocation":
                    target_allocation,

                "Shares":
                    shares,

                "Invested":
                    invested_amount,

                "Cash Remaining":
                    target_allocation
                    - invested_amount,
            }
        )


    portfolio = pd.DataFrame(
        rows
    )


    return portfolio


# =========================================================
# PORTFOLIO SETTINGS
# =========================================================

st.markdown("## Portfolio Settings")


settings_col1, settings_col2 = (
    st.columns(2)
)


with settings_col1:

    selected_model = st.selectbox(
        "Portfolio Model",
        options=list(
            PORTFOLIO_MODELS.keys()
        ),
        index=1,
        key="portfolio_model",
        width="stretch",
    )


with settings_col2:

    portfolio_value = st.number_input(
        "Portfolio Value ($)",
        min_value=1000,
        max_value=10_000_000,
        value=DEFAULT_PORTFOLIO_VALUE,
        step=1000,
        key="portfolio_value",
        width="stretch",
    )


# =========================================================
# MODEL DESCRIPTION
# =========================================================

model_descriptions = {

    "Conservative":
        (
            "Emphasizes bonds and diversified equity exposure "
            "with smaller allocations to real estate and commodities."
        ),

    "Balanced":
        (
            "Combines broad-market equities, growth, dividends, "
            "international exposure, bonds, real estate, and commodities."
        ),

    "Growth":
        (
            "Places greater emphasis on broad-market equities, "
            "growth ETFs, international markets, and leading sectors."
        ),

    "Income":
        (
            "Emphasizes dividend ETFs and bonds while maintaining "
            "broad-market, real-estate, and international exposure."
        ),

    "Aggressive":
        (
            "Emphasizes growth, sectors, thematic ETFs, "
            "and international equities with no dedicated "
            "bond allocation."
        ),
}


st.write(
    model_descriptions.get(
        selected_model,
        "",
    )
)


# =========================================================
# MODEL ALLOCATION
# =========================================================

st.markdown("---")

st.markdown("## Target Allocation")


model = PORTFOLIO_MODELS[
    selected_model
]


allocation_df = pd.DataFrame(
    {
        "Category":
            list(
                model.keys()
            ),

        "Allocation":
            [
                value * 100
                for value
                in model.values()
            ],
    }
)


allocation_col1, allocation_col2 = (
    st.columns(
        [1.3, 1]
    )
)


with allocation_col1:

    allocation_fig = px.bar(
        allocation_df.sort_values(
            "Allocation",
            ascending=True,
        ),
        x="Allocation",
        y="Category",
        orientation="h",
        text="Allocation",
        labels={
            "Allocation":
                "Allocation (%)",
        },
    )


    allocation_fig.update_traces(
        texttemplate="%{text:.0f}%",
        textposition="outside",
    )


    allocation_fig.update_layout(
        height=400,
        showlegend=False,
        margin=dict(
            l=10,
            r=30,
            t=10,
            b=10,
        ),
        xaxis=dict(
            range=[
                0,
                max(
                    allocation_df[
                        "Allocation"
                    ].max()
                    * 1.2,
                    10,
                ),
            ]
        ),
    )


    st.plotly_chart(
        allocation_fig,
        width="stretch",
        key="portfolio_allocation_chart",
    )


with allocation_col2:

    allocation_pie = px.pie(
        allocation_df,
        names="Category",
        values="Allocation",
        hole=0.45,
    )


    allocation_pie.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )


    allocation_pie.update_layout(
        height=400,
        margin=dict(
            l=10,
            r=10,
            t=10,
            b=10,
        ),
        showlegend=False,
    )


    st.plotly_chart(
        allocation_pie,
        width="stretch",
        key="portfolio_allocation_donut",
    )


# =========================================================
# BUILD PORTFOLIO
# =========================================================

portfolio = build_portfolio(
    results=etf_df,
    model_name=selected_model,
    portfolio_value=float(
        portfolio_value
    ),
)


if portfolio.empty:

    st.warning(
        "MarketScope could not build a portfolio "
        "from the currently available ETF data."
    )

    st.stop()


# =========================================================
# PORTFOLIO SUMMARY
# =========================================================

st.markdown("---")

st.markdown(
    "## MarketScope ETF Portfolio"
)


total_invested = (
    portfolio["Invested"].sum()
)

total_cash = (
    portfolio_value
    - total_invested
)


valid_scores = (
    pd.to_numeric(
        portfolio["ETF Score"],
        errors="coerce",
    )
    .dropna()
)


average_score = (
    valid_scores.mean()
    if not valid_scores.empty
    else np.nan
)


summary1, summary2, summary3, summary4 = (
    st.columns(4)
)


with summary1:

    st.metric(
        "Portfolio Value",
        f"${portfolio_value:,.0f}",
    )


with summary2:

    st.metric(
        "Invested",
        f"${total_invested:,.2f}",
    )


with summary3:

    st.metric(
        "Cash Remaining",
        f"${total_cash:,.2f}",
    )


with summary4:

    if pd.notna(
        average_score
    ):

        st.metric(
            "Average ETF Score",
            f"{average_score:.1f}",
        )

    else:

        st.metric(
            "Average ETF Score",
            "N/A",
        )


# =========================================================
# PORTFOLIO TABLE
# =========================================================

display_portfolio = (
    portfolio.copy()
)


st.dataframe(
    display_portfolio,
    width="stretch",
    hide_index=True,
    column_config={

        "Weight":
            st.column_config.NumberColumn(
                "Target Weight",
                format="%.1f%%",
            ),

        "ETF Score":
            st.column_config.NumberColumn(
                "ETF Score",
                format="%.1f",
            ),

        "Price":
            st.column_config.NumberColumn(
                "Price",
                format="$%.2f",
            ),

        "Target Allocation":
            st.column_config.NumberColumn(
                "Target $",
                format="$%.2f",
            ),

        "Shares":
            st.column_config.NumberColumn(
                "Shares",
                format="%d",
            ),

        "Invested":
            st.column_config.NumberColumn(
                "Invested",
                format="$%.2f",
            ),

        "Cash Remaining":
            st.column_config.NumberColumn(
                "Unused $",
                format="$%.2f",
            ),
    },
)


# =========================================================
# SELECTED ETF ALLOCATION
# =========================================================

st.markdown("---")

st.markdown(
    "## ETF Allocation"
)


actual_allocation = (
    portfolio[
        portfolio["Invested"] > 0
    ]
    .copy()
)


if not actual_allocation.empty:

    actual_fig = px.pie(
        actual_allocation,
        names="Ticker",
        values="Invested",
        hole=0.45,
        hover_data=[
            "Category",
            "ETF Score",
            "Trend",
        ],
    )


    actual_fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )


    actual_fig.update_layout(
        height=475,
        margin=dict(
            l=10,
            r=10,
            t=10,
            b=10,
        ),
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
        ),
    )


    st.plotly_chart(
        actual_fig,
        width="stretch",
        key="portfolio_etf_allocation",
    )


# =========================================================
# ETF SELECTION DETAILS
# =========================================================

st.markdown("---")

st.markdown(
    "## Why These ETFs?"
)


for _, row in portfolio.iterrows():

    ticker = str(
        row["Ticker"]
    )

    category = str(
        row["Category"]
    )

    score = safe_number(
        row["ETF Score"]
    )

    trend = str(
        row["Trend"]
    )


    score_display = (
        f"{score:.1f}"
        if pd.notna(score)
        else "N/A"
    )


    st.markdown(
        f"### {ticker}"
    )

    st.write(
        f"Selected as the highest-ranked available "
        f"MarketScope ETF for **{category}** that also "
        f"avoids duplicating another portfolio position when possible."
    )

    detail1, detail2, detail3 = (
        st.columns(3)
    )


    with detail1:

        st.metric(
            "Category",
            category,
        )


    with detail2:

        st.metric(
            "ETF Score",
            score_display,
        )


    with detail3:

        st.metric(
            "Trend",
            trend,
        )


# =========================================================
# MODEL COMPOSITION
# =========================================================

with st.expander(
    "📋 Portfolio Model Details"
):

    st.markdown(
        f"### {selected_model}"
    )

    st.write(
        model_descriptions.get(
            selected_model,
            "",
        )
    )


    model_details = pd.DataFrame(
        {
            "Category":
                list(
                    model.keys()
                ),

            "Target Allocation":
                [
                    value * 100
                    for value
                    in model.values()
                ],
        }
    )


    st.dataframe(
        model_details,
        width="stretch",
        hide_index=True,
        column_config={
            "Target Allocation":
                st.column_config.NumberColumn(
                    "Target Allocation",
                    format="%.1f%%",
                ),
        },
    )


# =========================================================
# METHODOLOGY NOTE
# =========================================================

st.markdown("---")

st.markdown(
    "### How the Portfolio Is Built"
)

st.write(
    """
    MarketScope examines the ETFs belonging to each category
    required by the selected portfolio model and ranks them using
    the current MarketScope ETF Score.

    The highest-ranked available ETF in each category is selected.
    When an ETF belongs to multiple categories, MarketScope attempts
    to avoid selecting the same ETF twice by choosing the next
    highest-ranked qualifying ETF.

    Target dollar allocations are based on the selected portfolio
    value. Share quantities use whole shares, so a portion of each
    target allocation may remain as cash.
    """
)


# =========================================================
# DISCLAIMER
# =========================================================

st.markdown("---")

st.caption(
    "This portfolio is hypothetical and is provided for "
    "informational and educational purposes only. MarketScope "
    "rankings and model allocations do not consider individual "
    "investment objectives, tax circumstances, liquidity needs, "
    "or risk tolerance and should not be considered investment advice."
)
"""MarketScope Mobile - Growth module."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
import yfinance as yf


# Mobile Growth universe. Keep this deliberately broad but manageable.
GROWTH_TICKERS = (
    "AAPL", "ADBE", "AMD", "AMZN", "AVGO", "CRM", "CRWD", "DDOG", "GOOG", "META",
    "MSFT", "NFLX", "NOW", "NVDA", "PANW", "PLTR", "SHOP", "SNOW", "TSLA", "UBER",
)


@st.cache_data(ttl=3600, show_spinner=False)
def load_growth_data(tickers: tuple[str, ...]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for ticker in tickers:
        try:
            security = yf.Ticker(ticker)
            info = security.info or {}

            # Use two years of price history so the 12-month calculation
            # has enough trading-day observations.
            history = security.history(period="2y", auto_adjust=True)

            price = np.nan
            ret_6m = np.nan
            ret_12m = np.nan
            above_200 = np.nan

            if history is not None and not history.empty and "Close" in history.columns:
                closes = pd.to_numeric(
                    history["Close"], errors="coerce"
                ).dropna()

                if not closes.empty:
                    price = float(closes.iloc[-1])

                    if len(closes) > 126:
                        ret_6m = float(
                            closes.iloc[-1] / closes.iloc[-127] - 1
                        )

                    if len(closes) > 251:
                        ret_12m = float(
                            closes.iloc[-1] / closes.iloc[-252] - 1
                        )

                    if len(closes) >= 200:
                        above_200 = float(
                            closes.iloc[-1] / closes.tail(200).mean() - 1
                        )

            revenue_growth = _number(info.get("revenueGrowth"))
            earnings_growth = _number(info.get("earningsGrowth"))
            roe = _number(info.get("returnOnEquity"))
            operating_margin = _number(info.get("operatingMargins"))
            forward_pe = _number(info.get("forwardPE"))

            growth_score = _growth_score(
                revenue_growth,
                earnings_growth,
            )

            quality_score = _quality_score(
                roe,
                operating_margin,
            )

            momentum_score = _momentum_score(
                ret_6m,
                ret_12m,
                above_200,
            )

            valuation_score = _valuation_score(
                forward_pe,
            )

            overall_score = _weighted_score(
                growth_score,
                quality_score,
                momentum_score,
                valuation_score,
            )

            rows.append(
                {
                    "Ticker": ticker,
                    "Company": info.get("shortName") or ticker,
                    "Sector": info.get("sector") or "Unknown",
                    "Price": (
                        price
                        if np.isfinite(price)
                        else _number(info.get("currentPrice"))
                    ),
                    "Market Cap": _number(info.get("marketCap")),
                    "Revenue Growth": revenue_growth,
                    "Earnings Growth": earnings_growth,
                    "ROE": roe,
                    "Operating Margin": operating_margin,
                    "Forward PE": forward_pe,
                    "6M Return": ret_6m,
                    "12M Return": ret_12m,
                    "Growth Score": growth_score,
                    "Quality Score": quality_score,
                    "Momentum Score": momentum_score,
                    "Valuation Score": valuation_score,
                    "Overall Score": overall_score,
                }
            )

        except Exception:
            continue

    frame = pd.DataFrame(rows)

    if not frame.empty:
        frame = frame.sort_values(
            "Overall Score",
            ascending=False,
            na_position="last",
        )

    return frame.reset_index(drop=True)


def _number(value: object) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return np.nan

    return result if np.isfinite(result) else np.nan


def _linear(value: float, low: float, high: float) -> float:
    if not np.isfinite(value):
        return np.nan

    if high == low:
        return 50.0

    return float(
        np.clip(
            (value - low) / (high - low) * 100,
            0,
            100,
        )
    )


def _mean_available(values: list[float]) -> float:
    available = [
        value
        for value in values
        if np.isfinite(value)
    ]

    return float(np.mean(available)) if available else np.nan


def _growth_score(
    revenue_growth: float,
    earnings_growth: float,
) -> float:

    return _mean_available(
        [
            _linear(revenue_growth, -0.05, 0.35),
            _linear(earnings_growth, -0.10, 0.40),
        ]
    )


def _quality_score(
    roe: float,
    operating_margin: float,
) -> float:

    return _mean_available(
        [
            _linear(roe, 0.00, 0.35),
            _linear(operating_margin, 0.00, 0.30),
        ]
    )


def _momentum_score(
    ret_6m: float,
    ret_12m: float,
    above_200: float,
) -> float:

    return _mean_available(
        [
            _linear(ret_6m, -0.20, 0.35),
            _linear(ret_12m, -0.30, 0.60),
            _linear(above_200, -0.20, 0.25),
        ]
    )


def _valuation_score(forward_pe: float) -> float:
    if not np.isfinite(forward_pe) or forward_pe <= 0:
        return np.nan

    # Growth stocks are allowed a wider valuation range;
    # lower remains better.
    return float(
        np.clip(
            (55 - forward_pe) / (55 - 15) * 100,
            0,
            100,
        )
    )


def _weighted_score(
    growth: float,
    quality: float,
    momentum: float,
    valuation: float,
) -> float:

    parts = [
        (growth, 0.40),
        (quality, 0.25),
        (momentum, 0.20),
        (valuation, 0.15),
    ]

    usable = [
        (value, weight)
        for value, weight in parts
        if np.isfinite(value)
    ]

    if not usable:
        return np.nan

    denominator = sum(
        weight
        for _, weight in usable
    )

    return (
        sum(
            value * weight
            for value, weight in usable
        )
        / denominator
    )


def add_watchlist(ticker: str) -> None:
    watchlist = st.session_state.setdefault(
        "mobile_watchlist",
        [],
    )

    if ticker not in watchlist:
        watchlist.append(ticker)


def stock_card(record: pd.Series) -> None:
    ticker = str(record["Ticker"])
    company = str(record.get("Company") or ticker)

    price = _number(record.get("Price"))
    score = _number(record.get("Overall Score"))
    growth = _number(record.get("Growth Score"))
    momentum = _number(record.get("Momentum Score"))
    ret12 = _number(record.get("12M Return"))

    score_display = f"{score:.0f}" if np.isfinite(score) else "N/A"
    growth_display = f"{growth:.0f}" if np.isfinite(growth) else "N/A"
    momentum_display = f"{momentum:.0f}" if np.isfinite(momentum) else "N/A"
    price_display = f"${price:,.2f}" if np.isfinite(price) else "N/A"
    ret12_display = f"{ret12:.1%}" if np.isfinite(ret12) else "N/A"

    card_html = (
        f'<div class="stock-card">'
        f'<div class="stock-row">'
        f'<div>'
        f'<div class="ticker">{ticker}</div>'
        f'<div class="company">{company}</div>'
        f'</div>'
        f'<div class="score">{score_display}</div>'
        f'</div>'
        f'<div class="mini-row">'
        f'<span>Price <b>{price_display}</b></span>'
        f'<span>Growth <b>{growth_display}</b></span>'
        f'<span>Momentum <b>{momentum_display}</b></span>'
        f'<span>12M <b>{ret12_display}</b></span>'
        f'</div>'
        f'</div>'
    )

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )

    left, right = st.columns([1, 1])

    with left:
        if st.button(
            "⭐ Watch",
            key=f"watch_{ticker}",
            use_container_width=True,
        ):
            add_watchlist(ticker)
            st.toast(f"{ticker} added to Watchlist")

    with right:
        if st.button(
            "🔎 Details",
            key=f"detail_{ticker}",
            use_container_width=True,
        ):
            st.session_state["mobile_selected_ticker"] = ticker
            st.session_state["mobile_search"] = ticker
            st.toast(f"{ticker} selected for Stock Detail")

# ---------------------------------------------------------
# Mobile styling
# ---------------------------------------------------------

st.markdown(
    """
<style>

[data-testid="stSidebar"] {
    display: none;
}

[data-testid="collapsedControl"] {
    display: none;
}

.block-container {
    max-width: 520px;
    padding: 2.5rem 1rem 5rem 1rem;
}

.module-title {
    font-size: 2rem;
    font-weight: 800;
    margin-bottom: .15rem;
}

.module-subtitle {
    color: #9aa3b2;
    font-size: .9rem;
    margin-bottom: 1rem;
}

.stock-card {
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 16px;
    padding: .9rem 1rem .8rem 1rem;
    background: rgba(128,128,128,.05);
    margin-top: .75rem;
}

.stock-row {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: .8rem;
}

.ticker {
    font-size: 1.25rem;
    font-weight: 800;
}

.company {
    font-size: .82rem;
    color: #9aa3b2;
    margin-top: .12rem;
}

.score {
    min-width: 46px;
    text-align: center;
    border-radius: 12px;
    padding: .35rem .45rem;
    background: #1877f2;
    color: white;
    font-weight: 800;
    font-size: 1.05rem;
}

.mini-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: .35rem .8rem;
    margin-top: .8rem;
    font-size: .82rem;
    color: #9aa3b2;
}

.section-label {
    font-size: .82rem;
    color: #9aa3b2;
    font-weight: 650;
    margin-top: .7rem;
}

</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Header
# ---------------------------------------------------------

st.markdown(
    '<div class="module-title">📈 Growth</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="module-subtitle">
    Growth, quality, momentum, and valuation context optimized
    for quick mobile research.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# Navigation
# ---------------------------------------------------------

home_col, refresh_col = st.columns(2)

with home_col:
    st.page_link(
        "mobile_home.py",
        label="Home",
        icon="🏠",
        width="stretch",
    )

with refresh_col:
    refresh = st.button(
        "🔄 Refresh",
        use_container_width=True,
    )

if refresh:
    load_growth_data.clear()


# ---------------------------------------------------------
# Load data
# ---------------------------------------------------------

with st.spinner("Loading Growth research..."):
    data = load_growth_data(GROWTH_TICKERS)

if data.empty:
    st.warning("Growth data is currently unavailable.")
    st.stop()


# ---------------------------------------------------------
# Search / filter
# ---------------------------------------------------------

search_default = st.session_state.get(
    "mobile_search",
    "",
)

search = st.text_input(
    "Search Growth",
    value=search_default,
    placeholder="Ticker or company...",
    label_visibility="collapsed",
).strip()


sector_options = (
    ["All"]
    + sorted(
        data["Sector"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )
)

sector = st.selectbox(
    "Sector",
    sector_options,
    label_visibility="collapsed",
)


filtered = data.copy()

if search:
    mask = (
        filtered["Ticker"]
        .astype(str)
        .str.contains(
            search,
            case=False,
            regex=False,
        )
        |
        filtered["Company"]
        .astype(str)
        .str.contains(
            search,
            case=False,
            regex=False,
        )
    )

    filtered = filtered[mask]


if sector != "All":
    filtered = filtered[
        filtered["Sector"] == sector
    ]


# ---------------------------------------------------------
# Growth Snapshot
# ---------------------------------------------------------

st.markdown(
    '<div class="section-label">GROWTH SNAPSHOT</div>',
    unsafe_allow_html=True,
)


median_score = filtered["Overall Score"].median()
median_rev_growth = filtered["Revenue Growth"].median()
median_12m = filtered["12M Return"].median()


m1, m2 = st.columns(2)

m1.metric(
    "Stocks",
    len(filtered),
)

m2.metric(
    "Median Score",
    f"{median_score:.0f}"
    if pd.notna(median_score)
    else "N/A",
)


m3, m4 = st.columns(2)

m3.metric(
    "Median Rev Growth",
    f"{median_rev_growth:.1%}"
    if pd.notna(median_rev_growth)
    else "N/A",
)

m4.metric(
    "Median 12M",
    f"{median_12m:.1%}"
    if pd.notna(median_12m)
    else "N/A",
)


if filtered.empty:
    st.info(
        "No Growth stocks match the current search and sector filter."
    )
    st.stop()


# ---------------------------------------------------------
# Top Growth Candidates
# ---------------------------------------------------------

st.markdown(
    '<div class="section-label">TOP GROWTH CANDIDATES</div>',
    unsafe_allow_html=True,
)

show_count = st.select_slider(
    "Show",
    options=[5, 10, 15, 20],
    value=10,
    label_visibility="collapsed",
)


leaders = (
    filtered
    .sort_values(
        "Overall Score",
        ascending=False,
        na_position="last",
    )
    .head(show_count)
)


for _, record in leaders.iterrows():
    stock_card(record)


# ---------------------------------------------------------
# Growth vs Momentum
# ---------------------------------------------------------

st.divider()

st.markdown(
    '<div class="section-label">GROWTH VS MOMENTUM</div>',
    unsafe_allow_html=True,
)


chart = filtered.dropna(
    subset=[
        "Growth Score",
        "Momentum Score",
    ]
).copy()


if not chart.empty:

    chart["Bubble Size"] = (
        pd.to_numeric(
            chart["Market Cap"],
            errors="coerce",
        )
        .clip(lower=1)
    )

    fig = px.scatter(
        chart,
        x="Growth Score",
        y="Momentum Score",
        size="Bubble Size",
        size_max=24,
        color="Sector",
        hover_name="Ticker",
        hover_data={
            "Company": True,
            "Overall Score": ":.1f",
            "Revenue Growth": ":.1%",
            "Earnings Growth": ":.1%",
            "Forward PE": ":.1f",
            "Bubble Size": False,
        },
    )

    fig.update_xaxes(
        range=[0, 100]
    )

    fig.update_yaxes(
        range=[0, 100]
    )

    fig.update_layout(
        height=390,
        margin=dict(
            l=5,
            r=5,
            t=10,
            b=5,
        ),
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )


st.caption(
    "Mobile Growth scores are compact screening signals "
    "for research, not investment recommendations."
)
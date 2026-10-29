"""MarketScope Hub - front door for the MarketScope research apps."""
from __future__ import annotations

import streamlit as st


st.set_page_config(
    page_title="MarketScope Hub",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Replace these with the deployed Streamlit URLs for each MarketScope app.
APP_URLS = {
    "Growth": "https://marketscopegrowth.streamlit.app",
    "Value": "https://marketscopevalue.streamlit.app",
    "Dividend": "https://marketscopedividend.streamlit.app",
    "ETF": "https://marketscopeetf.streamlit.app",
}


st.markdown(
    """
<style>
    .block-container {
        max-width: 1180px;
        padding-top: 3rem;
        padding-bottom: 3rem;
    }
    .hub-title {
        font-size: 3.4rem;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: .4rem;
    }
    .hub-subtitle {
        font-size: 1.13rem;
        color: #8f98a8;
        margin-bottom: 2rem;
    }
    .app-card {
        border: 1px solid rgba(128, 128, 128, .28);
        border-radius: 18px;
        padding: 1.35rem 1.45rem .75rem 1.45rem;
        min-height: 225px;
        background: rgba(128, 128, 128, .045);
    }
    .app-icon {
        font-size: 2rem;
        margin-bottom: .25rem;
    }
    .app-name {
        font-size: 1.65rem;
        font-weight: 750;
        margin-bottom: .5rem;
    }
    .app-description {
        color: #9ca3af;
        min-height: 72px;
        line-height: 1.55;
    }
    .section-label {
        margin-top: 1.75rem;
        font-size: 1.05rem;
        font-weight: 650;
        color: #b7beca;
    }
</style>
""",
    unsafe_allow_html=True,
)


st.markdown('<div class="hub-title">📊 MarketScope</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hub-subtitle">Choose a research approach and open the specialized MarketScope application.</div>',
    unsafe_allow_html=True,
)


def app_card(
    icon: str,
    name: str,
    description: str,
    highlights: str,
    url: str,
) -> None:
    st.markdown(
        f"""
        <div class="app-card">
            <div class="app-icon">{icon}</div>
            <div class="app-name">MarketScope {name}</div>
            <div class="app-description">{description}</div>
            <div style="margin-top:.7rem;"><strong>Focus:</strong> {highlights}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.page_link(
        url,
        label=f"Open MarketScope {name}",
        icon=icon,
        width="stretch",
    )


row1_left, row1_right = st.columns(2, gap="large")
with row1_left:
    app_card(
        "📈",
        "Growth",
        "Research companies with strong fundamental expansion and supportive market momentum.",
        "revenue and earnings expansion, quality, valuation, momentum",
        APP_URLS["Growth"],
    )

with row1_right:
    app_card(
        "💎",
        "Value",
        "Find attractively valued companies while checking business quality, financial strength, and potential value traps.",
        "valuation, quality, financial strength, value-trap risk",
        APP_URLS["Value"],
    )

st.write("")
row2_left, row2_right = st.columns(2, gap="large")
with row2_left:
    app_card(
        "💰",
        "Dividend",
        "Research dividend-focused companies with attention to income, quality, sustainability, and portfolio construction.",
        "dividend yield, dividend quality, sustainability, income",
        APP_URLS["Dividend"],
    )

with row2_right:
    app_card(
        "🌐",
        "ETF",
        "Explore ETFs and sectors using fund characteristics, performance, comparison tools, and portfolio analysis.",
        "ETFs, sectors, expenses, performance, allocation",
        APP_URLS["ETF"],
    )

st.divider()
st.markdown('<div class="section-label">MarketScope Research Suite</div>', unsafe_allow_html=True)
st.caption(
    "Each MarketScope application remains independent with its own research methodology, "
    "data cache, pages, and portfolio tools. The Hub acts only as the common launch point."
)

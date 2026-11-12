"""Stockchoice home screen."""

from __future__ import annotations

import streamlit as st

from app_utils import initialize_settings
from securities import get_security_options, format_security_option


# ---------------------------------------------------------
# INITIALIZATION
# ---------------------------------------------------------

initialize_settings()

st.set_page_config(
    page_title="StockChoice",
    page_icon="📱",
    layout="centered",
    initial_sidebar_state="collapsed",
)


# ---------------------------------------------------------
# PAGE STYLING
# ---------------------------------------------------------

st.markdown(
    """
    <style>

    /* -----------------------------------------------------
       Hide sidebar
       ----------------------------------------------------- */

    [data-testid="stSidebar"] {
        display: none;
    }

    [data-testid="collapsedControl"] {
        display: none !important;
    }


    /* -----------------------------------------------------
       Main page container
       ----------------------------------------------------- */

    .block-container {
        max-width: 520px;
        padding-top: 2.75rem;
        padding-left: 1rem;
        padding-right: 1rem;
        padding-bottom: 5rem;
    }


    /* -----------------------------------------------------
       Stockchoice branding
       ----------------------------------------------------- */

    .ms-brand {
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
        margin-bottom: .2rem;
    }

    .ms-subtitle {
        color: #9aa3b2;
        font-size: .95rem;
        line-height: 1.4;
        margin-bottom: 1.25rem;
    }


    /* -----------------------------------------------------
       Section labels
       ----------------------------------------------------- */

    .quick-label {
        font-size: .9rem;
        font-weight: 600;
        color: #9aa3b2;
        margin-top: 1rem;
        margin-bottom: .35rem;
        letter-spacing: .04rem;
    }


    /* -----------------------------------------------------
       Main research cards
       ----------------------------------------------------- */

    div[data-testid="stButton"] {
        margin-bottom: .25rem;
    }

    div[data-testid="stButton"] > button {
        width: 100%;
        min-height: 96px;

        border: 1px solid rgba(128, 128, 128, .25);
        background: rgba(128, 128, 128, .055);

        border-radius: 18px;

        padding: 1rem 1.1rem;

        text-align: left;
        justify-content: flex-start;

        transition:
            background-color 0.15s ease,
            border-color 0.15s ease,
            transform 0.10s ease;
    }


    /* -----------------------------------------------------
       Card hover
       ----------------------------------------------------- */

    div[data-testid="stButton"] > button:hover {
        border-color: #4f8cff;
        background: rgba(79, 140, 255, .08);
        transform: translateY(-1px);
    }


    /* -----------------------------------------------------
       Card pressed
       ----------------------------------------------------- */

    div[data-testid="stButton"] > button:active {
        transform: scale(.99);
    }


    /* -----------------------------------------------------
       Align icon and content
       ----------------------------------------------------- */

    div[data-testid="stButton"] > button > div {
        width: 100%;
        justify-content: flex-start;
        text-align: left;
        align-items: center;
        gap: .8rem;
    }


    /* -----------------------------------------------------
       Material icon sizing
       ----------------------------------------------------- */

    div[data-testid="stButton"] span[data-testid="stIconMaterial"] {
        flex-shrink: 0;
        font-size: 1.45rem;
    }


    /* -----------------------------------------------------
       Card text
       ----------------------------------------------------- */

    div[data-testid="stButton"] > button p {
        text-align: left;
        line-height: 1.4;
        white-space: pre-wrap;
        margin: 0;
    }


    /* -----------------------------------------------------
       Quick-access page links
       ----------------------------------------------------- */

    div[data-testid="stPageLink"] a {
        border-radius: 12px;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# HEADER
# ---------------------------------------------------------

st.markdown(
    '<div class="ms-brand">📱 Stockchoice</div>',
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="ms-subtitle">
        Stocks, ETFs, value, growth, and income research,
        from a bespoke list of quality tickers,
        in one mobile-first workspace.
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# SECURITY SEARCH
# ---------------------------------------------------------

selected_security = st.selectbox(
    "Search",
    options=get_security_options(),
    index=None,
    placeholder="Search a ticker, ETF, or company...",
    format_func=format_security_option,
    label_visibility="collapsed",
)

if selected_security:
    st.session_state["mobile_selected_ticker"] = selected_security
    st.switch_page("pages/details.py")


# ---------------------------------------------------------
# RESEARCH
# ---------------------------------------------------------

st.markdown(
    '<div class="quick-label">RESEARCH</div>',
    unsafe_allow_html=True,
)


# ---------------------------------------------------------
# RESEARCH CARDS
# ---------------------------------------------------------

cards = [
    (
        "📈",
        "Growth",
        "Find businesses with strong expansion, quality, and momentum.",
        "pages/growth.py",
    ),
    (
        "💎",
        "Value",
        "Find attractive valuations while watching quality and value-trap risk.",
        "pages/value.py",
    ),
    (
        "💵",
        "Dividend",
        "Research income, dividend quality, sustainability, and safety.",
        "pages/dividend.py",
    ),
    (
        "🌐",
        "ETF",
        "Explore ETFs, sectors, performance, expenses, and allocation ideas.",
        "pages/etf.py",
    ),
]



# ---------------------------------------------------------
# CLICKABLE RESEARCH CARDS
# ---------------------------------------------------------

for icon, title, description, page in cards:

    card_label = f"**{title}**\n\n{description}"

    if st.button(
        card_label,
        key=f"home_card_{title.lower()}",
        icon=icon,
        width="stretch",
    ):
        st.switch_page(page)


# ---------------------------------------------------------
# QUICK ACCESS
# ---------------------------------------------------------

st.markdown('<div class="quick-label">QUICK ACCESS</div>', unsafe_allow_html=True)
q1, q2 = st.columns(2)
with q1:
    st.page_link("pages/watchlist.py", label="Watchlist", icon="⭐", width="stretch")
    st.page_link("pages/compare.py", label="Compare", icon="⚖️", width="stretch")
with q2:
    st.page_link("pages/markets.py", label="Markets", icon="🌐", width="stretch")
    st.page_link("pages/settings.py", label="Settings", icon="⚙️", width="stretch")
st.page_link("pages/score_guide.py", label="Score Guide", icon="📖", width="stretch")

# ---------------------------------------------------------
# FOOTER
# ---------------------------------------------------------

st.divider()

st.caption(
    "This research tool for informational and educational use"
)
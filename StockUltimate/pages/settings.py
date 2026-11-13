"""stockchoice - settings page."""
from __future__ import annotations

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
import streamlit as st
from database import clear_watchlist, load_watchlist
from app_utils import DEFAULT_SETTINGS, initialize_settings


DEFAULTS = DEFAULT_SETTINGS


def initialize_settings() -> None:
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)
    st.session_state.setdefault("mobile_watchlist", [])


def reset_preferences() -> None:
    for key, value in DEFAULTS.items():
        st.session_state[key] = value


initialize_settings()

st.markdown(
    """
<style>
[data-testid="stSidebar"] {display:none;}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {display:none !important; visibility:hidden !important;}
.block-container {max-width:520px;padding:2.5rem 1rem 5rem 1rem;}
.module-title {font-size:2rem;font-weight:800;margin-bottom:.15rem;}
.module-subtitle {color:#9aa3b2;font-size:.9rem;margin-bottom:1rem;}
.section-label {
    font-size:.82rem;color:#9aa3b2;font-weight:650;
    margin-top:1rem;margin-bottom:.35rem;
}
.setting-card {
    border:1px solid rgba(128,128,128,.25);
    border-radius:16px;
    padding:.9rem 1rem;
    background:rgba(128,128,128,.05);
    margin:.4rem 0 .75rem 0;
}
.setting-title {font-size:1rem;font-weight:750;margin-bottom:.2rem;}
.setting-text {font-size:.82rem;color:#9aa3b2;line-height:1.4;}
.status-pill {
    display:inline-block;border-radius:999px;padding:.25rem .6rem;
    background:rgba(37,99,235,.13);color:#60a5fa;
    font-size:.78rem;font-weight:700;margin-top:.35rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown('<div class="module-title">⚙️ Settings</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="module-subtitle">Customize the stockchoice research experience and manage session data.</div>',
    unsafe_allow_html=True,
)

st.page_link("app.py", label="Home", icon="🏠", width="stretch")

st.markdown('<div class="section-label">STARTUP</div>', unsafe_allow_html=True)

st.session_state["mobile_default_module"] = st.selectbox(
    "Default research module",
    options=["Growth", "Value", "Dividend", "ETF", "Markets"],
    index=["Growth", "Value", "Dividend", "ETF", "Markets"].index(
        st.session_state["mobile_default_module"]
    ),
    help="Preferred research area for future navigation enhancements.",
)

result_options = [5, 10, 15, 20]
current_count = st.session_state["mobile_default_result_count"]
st.session_state["mobile_default_result_count"] = st.select_slider(
    "Default number of candidates",
    options=result_options,
    value=current_count if current_count in result_options else 10,
)

st.markdown('<div class="section-label">DISPLAY</div>', unsafe_allow_html=True)

st.session_state["mobile_compact_cards"] = st.toggle(
    "Compact research cards",
    value=st.session_state["mobile_compact_cards"],
    help="Preference for dense mobile stock and ETF cards.",
)

st.session_state["mobile_show_charts"] = st.toggle(
    "Show analytical charts",
    value=st.session_state["mobile_show_charts"],
    help="Preference for charts on research modules.",
)

st.session_state["mobile_show_disclaimer"] = st.toggle(
    "Show research disclaimer",
    value=st.session_state["mobile_show_disclaimer"],
)

st.markdown('<div class="section-label">DATA</div>', unsafe_allow_html=True)

cache_options = ["Fresh", "Balanced", "Data Saver"]
st.session_state["mobile_cache_preference"] = st.radio(
    "Refresh preference",
    options=cache_options,
    index=cache_options.index(st.session_state["mobile_cache_preference"]),
    horizontal=True,
)

st.markdown(
    """
<div class="setting-card">
 <div class="setting-title">Current session</div>
 <div class="setting-text">Watchlist symbols are stored in the local SQLite database. Mobile preferences are stored for the current Streamlit session.</div>
</div>
""",
    unsafe_allow_html=True,
)

saved_watchlist = load_watchlist()
st.session_state["mobile_watchlist"] = saved_watchlist
watchlist_count = len(saved_watchlist)
st.metric("Watchlist symbols", watchlist_count)

clear1, clear2 = st.columns(2)
with clear1:
    if st.button("Clear data cache", use_container_width=True):
        st.cache_data.clear()
        st.toast("Cached market data cleared")

with clear2:
    if st.button("Clear watchlist", use_container_width=True):
        clear_watchlist()
        st.session_state["mobile_watchlist"] = []
        st.toast("Watchlist cleared")
        st.rerun()

st.markdown('<div class="section-label">RESET</div>', unsafe_allow_html=True)

if st.button("Reset Mobile preferences", type="secondary", use_container_width=True):
    reset_preferences()
    st.toast("Mobile preferences reset")
    st.rerun()

st.divider()
st.markdown(
    """
<div class="setting-card">
 <div class="setting-title">📱 Stockchoice</div>
 <div class="setting-text">Mobile-first research suite for Growth, Value, Dividend, ETF, Markets, Watchlist, and Compare.</div>
 <div class="status-pill">Development build</div>
</div>
""",
    unsafe_allow_html=True,
)

st.caption(
    "Stockchoice is intended for informational and educational research and does not provide personalized investment advice."
)

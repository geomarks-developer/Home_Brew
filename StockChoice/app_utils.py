"""Shared stockchoice preference helpers."""
from __future__ import annotations
import streamlit as st
DEFAULT_SETTINGS = {
    "mobile_default_module": "Growth",
    "mobile_default_result_count": 10,
    "mobile_compact_cards": True,
    "mobile_show_charts": True,
    "mobile_show_disclaimer": True,
    "mobile_cache_preference": "Balanced",
}
def initialize_settings() -> None:
    for key, value in DEFAULT_SETTINGS.items():
        st.session_state.setdefault(key, value)
def cache_ttl() -> int:
    initialize_settings()
    return {"Fresh": 900, "Balanced": 3600, "Data Saver": 14400}.get(st.session_state.get("mobile_cache_preference"), 3600)
def apply_card_density() -> None:
    if not st.session_state.get("mobile_compact_cards", True):
        st.markdown("""<style>.stock-card,.fund-card,.watch-card,.market-card,.compare-card{padding:1.15rem!important}.mini-row,.returns{gap:.6rem 1rem!important;margin-top:1rem!important}</style>""", unsafe_allow_html=True)

"""stockchoice score guide."""
from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app_utils import apply_card_density, initialize_settings

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
.guide-card {border:1px solid rgba(128,128,128,.25);border-radius:16px;padding:.9rem 1rem;background:rgba(128,128,128,.05);margin:.6rem 0;}
.guide-title {font-size:1rem;font-weight:800;margin-bottom:.25rem;}
.guide-text {font-size:.86rem;color:#9aa3b2;line-height:1.5;}
.section-label {font-size:.82rem;color:#9aa3b2;font-weight:700;margin-top:1rem;margin-bottom:.35rem;}
</style>
""",
    unsafe_allow_html=True,
)
apply_card_density()

st.markdown('<div class="module-title">📖 Score Guide</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="module-subtitle">How Stockchoice calculates and interprets the scores shown on Growth, Value, Dividend, and ETF research cards.</div>',
    unsafe_allow_html=True,
)
st.page_link("app.py", label="Home", icon="🏠", width="stretch")

st.markdown('<div class="section-label">HOW TO READ THE SCORES</div>', unsafe_allow_html=True)
st.markdown(
    """
<div class="guide-card"><div class="guide-title">0–100 scoring</div>
<div class="guide-text">Most factor and overall scores are normalized to a 0–100 scale. Higher is generally stronger. When an input is unavailable, PulseScout calculates from the available components and reweights them proportionally.</div></div>
""",
    unsafe_allow_html=True,
)

st.write("**Suggested interpretation**")
st.write("• **80–100:** Very Strong")
st.write("• **65–79:** Strong")
st.write("• **50–64:** Moderate")
st.write("• **35–49:** Weak")
st.write("• **0–34:** Very Weak")
st.caption("These bands are an interpretation aid, not part of the underlying score formulas.")

with st.expander("📈 Growth scores", expanded=True):
    st.write("**Overall Score:** Growth 40% + Quality 25% + Momentum 20% + Valuation 15%.")
    st.write("**Growth Score:** Revenue growth and earnings growth. Higher growth produces a higher score.")
    st.write("**Quality Score:** Return on equity and operating margin.")
    st.write("**Momentum Score:** 6-month return, 12-month return, and price relative to its 200-day average.")
    st.write("**Valuation Score:** Based on forward P/E. Lower positive forward P/E values score better within the Growth model's range.")
    st.write("**Card fields:** Price, Growth Score, Momentum Score, and 12-month return. The colored badge is Overall Score.")

with st.expander("💎 Value scores"):
    st.write("**Overall Score:** Valuation 45% + Quality 25% + Financial Strength 15% + Momentum 15%.")
    st.write("**Valuation Score:** Forward P/E, price-to-book, EV/EBITDA, and free-cash-flow yield. Cheaper valuations and higher FCF yield score better.")
    st.write("**Quality Score:** Return on equity, operating margin, and positive free cash flow.")
    st.write("**Financial Strength Score:** Based on debt-to-equity, with lower leverage scoring better.")
    st.write("**Momentum Score:** 12-month return and price relative to the 200-day average.")
    st.write("**Value Trap Risk:** A separate risk score based on revenue/earnings deterioration, negative free cash flow, weak quality, and weak momentum. **Lower is better.**")
    st.write("**Card fields:** Price, Valuation Score, FCF Yield, and Value Trap Risk. The colored badge is Overall Score.")

with st.expander("💰 Dividend scores"):
    st.write("**Overall Score:** Income 30% + Sustainability 30% + Quality 20% + Balance Sheet 10% + Momentum 10%.")
    st.write("**Income Score:** Dividend yield, with higher yields scoring better within the model's range.")
    st.write("**Sustainability / Safety Score:** Payout ratio, positive free cash flow, and earnings growth. Lower payout ratios and stronger underlying cash flow/growth improve the score.")
    st.write("**Quality Score:** Return on equity and operating margin.")
    st.write("**Balance Sheet Score:** Debt-to-equity, with lower leverage scoring better.")
    st.write("**Momentum Score:** 12-month price return.")
    st.write("**Card fields:** Price, Dividend Yield, Payout Ratio, and Sustainability/Safety Score. The colored badge is Overall Score.")

with st.expander("🌐 ETF scores"):
    st.write("**Overall Score:** Performance 40% + Momentum 20% + Risk 15% + Cost 15% + Income 10%.")
    st.write("**Performance Score:** 3-month, 6-month, and 12-month returns.")
    st.write("**Momentum Score:** Price relative to its 200-day average.")
    st.write("**Risk Score:** Annualized price volatility. Lower volatility scores better.")
    st.write("**Cost Score:** Expense ratio. Lower expenses score better.")
    st.write("**Income Score:** Trailing dividend yield calculated from approximately the previous 365 days of distributions relative to price.")
    st.write("**Card fields:** Price, 12-month return, Expense Ratio, and Dividend Yield. The colored badge is Overall Score.")

st.divider()
st.info("PulseScout scores are screening and ranking signals. They are designed to organize research, not predict returns or provide personalized investment advice.")

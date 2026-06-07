"""
app.py
Thin orchestrator — loads data, runs engine, calls screen renderers.
Edit this file only to change page config, sidebar layout, or tab structure.
For logic changes: engine.py
For data changes: data.py
For constants: config.py
For styling: styles.py
For screen content: screens/screen_*.py
"""

import sys
import os

# Ensure the directory containing app.py is on sys.path so that
# sibling modules (config, data, engine, styles, screens) are importable
# regardless of where Streamlit Cloud sets the working directory.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from datetime import timedelta
import pandas as pd

# ── Page config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="All-Weather",
    page_icon="🌦",
    layout="wide",
    initial_sidebar_state="expanded",
)

from styles  import CSS
from config  import GLIDE_ASSETS, REGIME_TILTS, REGIME_META, ETF_DATA
from data    import fetch_prices, fetch_macro, fetch_forward_pe
from engine  import (
    inv_vol_weights, stop_price, compute_orders,
    score_sectors, n_tilt_slots, regime_confidence,
    transition_probability, hedge_decision,
)
import screen_hold, screen_outlook, screen_tracker

# ── Persistence helpers ───────────────────────────────────────────────────────
def qp_get(key, default):
    val = st.query_params.get(key, str(default))
    try:    return type(default)(val)
    except: return default

def qp_set(key, val):
    st.query_params[key] = str(val)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown(
        '<div style="font-family:var(--mono);font-size:.65rem;letter-spacing:.1em;'
        'text-transform:uppercase;color:var(--muted);padding:16px 0 12px">All-Weather</div>',
        unsafe_allow_html=True,
    )

    glide_choice = st.selectbox(
        "Life stage",
        options=list(GLIDE_ASSETS.keys()),
        index=qp_get("glide_idx", 0),
        key="glide_sel",
    )
    glide_idx = list(GLIDE_ASSETS.keys()).index(glide_choice)

    rebal_freq = st.selectbox(
        "Rebalance cadence",
        ["Quarterly", "Semi-annual", "Annual"],
        index=qp_get("rebal_idx", 0),
        key="rebal_sel",
    )

    if st.button("Save settings", use_container_width=True):
        qp_set("glide_idx", glide_idx)
        qp_set("rebal_idx", ["Quarterly", "Semi-annual", "Annual"].index(rebal_freq))
        st.success("Saved", icon="✓")

    st.markdown("---")
    st.markdown(
        '<div style="font-family:var(--mono);font-size:.62rem;color:var(--dim);line-height:1.8">'
        '55% Core &nbsp;·&nbsp; 35% Tilt &nbsp;·&nbsp; 10% Hedge<br>'
        f'Stage: {glide_choice.split("·")[0].strip()}<br>'
        f'Cadence: {rebal_freq}'
        '</div>',
        unsafe_allow_html=True,
    )

# ══════════════════════════════════════════════════════════════════════════════
# DATA LOADING
# ══════════════════════════════════════════════════════════════════════════════

CORE_ASSETS   = GLIDE_ASSETS[glide_choice]["assets"]
ALL_TILT_TKRS = list(dict.fromkeys(
    t for tilts in REGIME_TILTS.values() for t in tilts
))
ALL_TICKERS   = tuple(dict.fromkeys(
    CORE_ASSETS + ALL_TILT_TKRS + ["BIL", "SH", "VOO", "TLT", "SPY"]
))

with st.spinner("Loading market data…"):
    prices, highs, lows = fetch_prices(ALL_TICKERS)

macro            = fetch_macro()
pe_data, spy_pe  = fetch_forward_pe(tuple(ALL_TILT_TKRS))

# 3-month sector returns
three_mo   = prices.index[-1] - timedelta(days=90)
tilt_tkrs  = [t for t in ALL_TILT_TKRS if t in prices.columns]
sp         = prices[tilt_tkrs][prices.index >= three_mo]
ret_3m     = (
    (prices[tilt_tkrs].iloc[-1] - sp.iloc[0]) / sp.iloc[0]
    if not sp.empty else pd.Series(dtype=float)
)

# Regime
gdp_trend  = macro["gdp_trend"]
cpi_trend  = macro["cpi_trend"]
regime_key = (gdp_trend, cpi_trend)
quad_pref  = REGIME_TILTS.get(regime_key, [])

# Engine outputs
conf = regime_confidence(macro, quad_pref[:3], ret_3m, prices)
tp   = transition_probability(macro, gdp_trend, cpi_trend)

hedge_ticker, voo_px, voo_sma, crisis = hedge_decision(prices)
voo_sma_pct = (voo_px - voo_sma) / voo_sma * 100 if voo_sma else 0.0

stopped = [
    t.strip().upper()
    for t in st.query_params.get("stopped", "").split(",")
    if t.strip()
]

scored_tilts = score_sectors(prices, macro, regime_key, pe_data, stopped)
n_tilts      = n_tilt_slots(conf["score"])
sel_tilts    = scored_tilts[:n_tilts]
core_weights = inv_vol_weights(prices, CORE_ASSETS)

def get_stop(ticker):
    return stop_price(prices, highs, lows, ticker)

# ── Build target allocation map (used by tracker) ─────────────────────────────
effective_core = 0.55 + (0.35 if n_tilts == 0 else 0.0)
target_map = {}
for t in CORE_ASSETS:
    w = core_weights.get(t, 0)
    target_map[t] = {"bucket": "Core", "target_pct": round(effective_core * w * 100, 2)}
for s in sel_tilts:
    target_map[s["ticker"]] = {
        "bucket":     "Tilt",
        "target_pct": round(0.35 / max(n_tilts, 1) * 100, 2),
    }
target_map[hedge_ticker] = {"bucket": "Hedge", "target_pct": 10.0}

# ══════════════════════════════════════════════════════════════════════════════
# TOP STATUS BAR
# ══════════════════════════════════════════════════════════════════════════════

meta       = REGIME_META.get(regime_key, {})
quad_name  = meta.get("name",  "Unknown")
quad_emoji = meta.get("emoji", "❓")
quad_color = meta.get("color", "#7d8590")

gdp_c      = "#3fb950" if gdp_trend == "rising" else "#f85149"
cpi_c      = "#f85149" if cpi_trend == "rising" else "#3fb950"
bias_c     = ("#3fb950" if macro["leading_bias"] == "growth_positive" else
              "#f85149" if macro["leading_bias"] == "growth_negative" else "#d29922")
lead_label = macro["leading_bias"].replace("_", " ")

conf_score  = conf["score"]
conf_color  = conf["color"]
tp_prob     = tp["prob"]
tp_color    = tp["color"]
hedge_color = "#f85149" if crisis else "#3fb950"
hedge_label = (hedge_ticker + "  🚨") if crisis else hedge_ticker
from datetime import datetime
now_str = datetime.now().strftime("%H:%M")

st.markdown(
    f'<div class="aw-topbar" id="main" role="banner" '
    f'aria-label="Portfolio status summary">'
    f'<span class="aw-topbar-brand">All-Weather</span>'
    f'<span aria-label="Regime: {quad_name}">'
    f'<span aria-hidden="true">{quad_emoji}</span> '
    f'<b style="color:{quad_color}">{quad_name}</b></span>'
    f'<span aria-label="Confidence {conf_score} out of 100">'
    f'Confidence <b style="color:{conf_color}">{conf_score}</b></span>'
    f'<span aria-label="Transition probability {tp_prob} percent">'
    f'Transition <b style="color:{tp_color}">{tp_prob}%</b></span>'
    f'<span aria-label="GDP {gdp_trend}">'
    f'GDP <b style="color:{gdp_c}">{gdp_trend}</b></span>'
    f'<span aria-label="CPI {cpi_trend}">'
    f'CPI <b style="color:{cpi_c}">{cpi_trend}</b></span>'
    f'<span aria-label="Leading indicators {lead_label}">'
    f'Leading <b style="color:{bias_c}">{lead_label}</b></span>'
    f'<span aria-label="Hedge {hedge_ticker}">'
    f'Hedge <b style="color:{hedge_color}">{hedge_label}</b></span>'
    f'<span style="margin-left:auto;color:var(--dim)">{now_str}</span>'
    f'</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs([
    "01  WHAT TO HOLD",
    "02  REGIME OUTLOOK",
    "03  POSITION TRACKER",
])

with tab1:
    screen_hold.render(
        prices        = prices,
        macro         = macro,
        regime_key    = regime_key,
        conf          = conf,
        core_assets   = CORE_ASSETS,
        core_weights  = core_weights,
        selected_tilts= sel_tilts,
        n_tilts       = n_tilts,
        hedge_ticker  = hedge_ticker,
        voo_sma_pct   = voo_sma_pct,
        crisis        = crisis,
        stopped       = stopped,
        get_stop_fn   = get_stop,
    )

with tab2:
    screen_outlook.render(
        macro = macro,
        tp    = tp,
    )

with tab3:
    screen_tracker.render(
        target_map        = target_map,
        prices            = prices,
        highs             = highs,
        lows              = lows,
        rebal_freq        = rebal_freq,
        compute_orders_fn = compute_orders,
        get_stop_fn       = get_stop,
    )

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    f'<div style="margin-top:40px;padding-top:14px;border-top:1px solid var(--border);'
    f'font-family:var(--mono);font-size:.6rem;color:var(--dim);text-align:center">'
    f'All-Weather · Macro-driven allocation · '
    f'Data: yfinance + FRED · Not financial advice · '
    f'{datetime.now().year}</div>',
    unsafe_allow_html=True,
)

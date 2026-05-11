import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
import warnings

# ── Config & Silence yfinance ────────────────────────────────────────────────
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

st.set_page_config(page_title="Project All-Weather", page_icon="🌦", layout="wide")

# ── Persistence Logic (localStorage <-> query_params) ────────────────────────
PARAM_DEFAULTS = {"total_inv": "100000", "glide_index": "0", "core_pct": "60", "tactical_pct": "30"}

def _qp(key: str, default):
    val = st.query_params.get(key, str(default))
    try: return int(val) if isinstance(default, int) else val
    except: return default

st.components.v1.html("""
<script>
(function() {
  const KEYS = ["total_inv","glide_index","core_pct","tactical_pct"];
  const params = new URLSearchParams(window.parent.location.search);
  let needsUpdate = false;
  KEYS.forEach(k => {
    const v = localStorage.getItem("aw_" + k);
    if (v !== null && params.get(k) !== v) { params.set(k, v); needsUpdate = true; }
  });
  if (needsUpdate) { window.parent.history.replaceState(null, "", "?" + params.toString()); }
})();
</script>""", height=0)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=DM+Sans:wght@400;700&display=swap');
:root { --bg: #0a0c10; --surface: #11151c; --border: #1e2535; --accent: #3b82f6; --text: #e2e8f0; --mono: 'Space Mono', monospace; }
html, body, [class*="css"] { background-color: var(--bg) !important; color: var(--text) !important; font-family: 'DM Sans', sans-serif; }
.aw-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.aw-badge { background: var(--accent); color: white; font-family: var(--mono); font-size: 0.6rem; padding: 2px 8px; border-radius: 3px; }
.stop-badge { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #ef4444; font-family: var(--mono); font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
</style>""", unsafe_allow_html=True)

# ── Data Engine ──────────────────────────────────────────────────────────────
GLIDE_PRESETS = {
    "31–40 · Aggressive Global": {"assets": ["VOO", "VEA", "VWO", "GLD"]},
    "41–50 · Growth": {"assets": ["VOO", "VEA", "VWO", "GLD", "IEF"]},
    "51–60 · Balanced": {"assets": ["VOO", "VEA", "GLD", "IEF", "TLT"]},
    "61+ · All-Weather Classic": {"assets": ["VOO", "TLT", "IEF", "GLD", "GSG"]}
}

SECTOR_ETFS = {"XLE":"Energy","XLK":"Tech","XLV":"Health","XLF":"Financials","XLI":"Industrials","XLY":"Disc","XLP":"Staples","XLB":"Materials","XLC":"Comm","XLU":"Utils","XLRE":"Real Estate"}

@st.cache_data(ttl=3600)
def fetch_all_data(tickers):
    ticker_str = " ".join(tickers) if isinstance(tickers, list) else tickers
    try:
        data = yf.download(ticker_str, period="2y", auto_adjust=True, progress=False, group_by='ticker')
        return data
    except Exception as e:
        st.error(f"Download Error: {e}"); return pd.DataFrame()

def get_ticker_close(data, t):
    try:
        if isinstance(data.columns, pd.MultiIndex):
            return data[t]['Close'] if t in data.columns.levels[0] else data.xs('Close', axis=1, level=1)[t]
        return data[t]
    except: return pd.Series()

# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🌦 Settings")
    total_inv = st.number_input("Investment ($)", value=_qp("total_inv", 100000))
    glide_choice = st.selectbox("Life Stage", list(GLIDE_PRESETS.keys()), index=_qp("glide_index", 0))
    core_pct = st.slider("Core %", 40, 80, _qp("core_pct", 60))
    tactical_pct = st.slider("Alpha %", 10, 40, _qp("tactical_pct", 30))
    
    if st.button("💾 SAVE & REFRESH", use_container_width=True):
        st.query_params.update({"total_inv": total_inv, "glide_index": list(GLIDE_PRESETS.keys()).index(glide_choice), "core_pct": core_pct, "tactical_pct": tactical_pct})
        st.rerun()

CORE_ASSETS = GLIDE_PRESETS[glide_choice]["assets"]
ALL_TICKERS = list(set(CORE_ASSETS + list(SECTOR_ETFS.keys()) + ["VOO", "SPY"]))

# ── Main Logic ───────────────────────────────────────────────────────────────
raw_data = fetch_all_data(ALL_TICKERS)

# Conviction Scoring (60% Mom / 40% Sentiment)
def calculate_conviction(data):
    results = []
    for t in SECTOR_ETFS:
        px = get_ticker_close(data, t).dropna()
        if len(px) < 65: continue
        # Momentum (3M)
        mom = (px.iloc[-1] / px.iloc[-63]) - 1
        # Sentiment (RSI + SMA)
        rsi = 100 - (100 / (1 + (px.diff().clip(lower=0).tail(14).mean() / -px.diff().clip(upper=0).tail(14).mean())))
        sma_dist = (px.iloc[-1] / px.rolling(20).mean().iloc[-1]) - 1
        sent_score = np.clip((rsi-50) + (sma_dist*100), 0, 100)
        results.append({"Ticker": t, "Sector": SECTOR_ETFS[t], "Momentum": mom, "Sentiment": sent_score, "Price": px.iloc[-1]})
    
    df = pd.DataFrame(results)
    df['Conviction'] = (df['Momentum'].rank(pct=True)*60) + (df['Sentiment'].rank(pct=True)*40)
    return df.sort_values("Conviction", ascending=False)

tactical_df = calculate_conviction(raw_data)

# ── UI Tabs ──────────────────────────────────────────────────────────────────
st.title("PROJECT ALL-WEATHER")
tab1, tab2, tab3, tab4 = st.tabs(["Strategic Allocation", "Tactical Engine", "Correlation & Risk", "Methodology"])

with tab1:
    c1, c2 = st.columns(2)
    with c1:
        st.metric("Regime", "Stagflation Lite", "CPI Target 3.0%")
    with c2:
        spy_px = get_ticker_close(raw_data, "SPY")
        crisis = spy_px.iloc[-1] < spy_px.rolling(200).mean().iloc[-1]
        st.metric("Hedge Status", "CRISIS" if crisis else "NORMAL", "Short S&P" if crisis else "T-Bills")
    
    st.subheader("Core Risk Parity Positions")
    core_prices = pd.DataFrame({t: get_ticker_close(raw

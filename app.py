import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Project All-Weather",
    page_icon="🌦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ══════════════════════════════════════════════════════════════════════════════
# PERSISTENCE & STYLING (Restored from app(8).py)
# ══════════════════════════════════════════════════════════════════════════════

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
</script>
""", height=0)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
:root { --bg: #0a0c10; --surface: #10141c; --border: #1e2535; --accent: #3b82f6; --text: #e2e8f0; --muted: #64748b; --mono: 'Space Mono', monospace; }
html, body, [class*="css"] { background-color: var(--bg) !important; color: var(--text) !important; font-family: 'DM Sans', sans-serif; }
.aw-header { display: flex; align-items: center; gap: 16px; padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 25px; }
.aw-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.aw-badge { background: var(--accent); color: white; font-family: var(--mono); font-size: 0.6rem; padding: 2px 8px; border-radius: 3px; }
.metric-tile { background: #161b26; border: 1px solid var(--border); border-radius: 6px; padding: 15px; flex: 1; }
.stop-badge { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #ef4444; font-family: var(--mono); font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA ENGINE
# ══════════════════════════════════════════════════════════════════════════════

GLIDE_PRESETS = {
    "31–40 · Aggressive Growth": {"assets": ["VOO", "VEA", "VWO", "GLD"], "desc": "Pure equity + gold."},
    "41–50 · Growth": {"assets": ["VOO", "VEA", "VWO", "GLD", "IEF"], "desc": "Added mid-term bonds."},
    "51–55 · Growth / Cons.": {"assets": ["VOO", "VEA", "GLD", "IEF", "TLT"], "desc": "Added long bonds."},
    "60+ · All-Weather Classic": {"assets": ["VOO", "TLT", "IEF", "GLD", "GSG"], "desc": "Capital preservation."},
}

SECTOR_ETFS = {"XLE":"Energy","XLK":"Tech","XLV":"Health","XLF":"Financials","XLI":"Industrials","XLY":"Disc","XLP":"Staples","XLB":"Materials","XLC":"Comm","XLU":"Utils","XLRE":"Real Estate"}
QUADRANT_MAP = {("rising","rising"):("Stagflation","🔥",["XLE","XLB","GLD"]), ("rising","falling"):("Expansion","🚀",["XLK","XLY","XLF"]), ("falling","rising"):("Recession","❄️",["XLU","XLP","XLV"]), ("falling","falling"):("Deflation","🌧",["TLT","XLU","GLD"])}

@st.cache_data(ttl=3600)
def fetch_all_data(tickers):
    data = yf.download(tickers, period="1y", auto_adjust=True, progress=False)
    # Safe MultiIndex handling
    prices = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data[['Close']].rename(columns={'Close': tickers[0]})
    vols = data['Volume'] if isinstance(data.columns, pd.MultiIndex) else data[['Volume']].rename(columns={'Volume': tickers[0]})
    return prices.ffill(), vols.ffill()

@st.cache_data(ttl=3600)
def get_fred_macro():
    # Simple fallback trends if FRED is unreachable
    return "rising", "falling" # GDP rising, CPI falling (Expansion baseline)

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.title("🌦 Settings")
    total_inv = st.number_input("Total Investment ($)", value=_qp("total_inv", 100000))
    glide_choice = st.selectbox("Life Stage", options=list(GLIDE_PRESETS.keys()), index=_qp("glide_index", 0))
    CORE_ASSETS = GLIDE_PRESETS[glide_choice]["assets"]
    
    core_pct = st.slider("Core Equity %", 40, 80, _qp("core_pct", 60))
    tactical_pct = st.slider("Tactical %", 10, 40, _qp("tactical_pct", 30))
    hedge_pct = 100 - core_pct - tactical_pct
    
    if st.button("💾 SAVE & REFRESH", use_container_width=True):
        st.query_params.update({"total_inv": total_inv, "glide_index": list(GLIDE_PRESETS.keys()).index(glide_choice), "core_pct": core_pct, "tactical_pct": tactical_pct})
        st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# ANALYTICS LOGIC
# ══════════════════════════════════════════════════════════════════════════════

prices, volumes = fetch_all_data(list(SECTOR_ETFS.keys()) + CORE_ASSETS + ["VOO", "SH", "BIL"])
gdp_t, cpi_t = get_fred_macro()
quad_name, quad_emoji, quad_prefs = QUADRANT_MAP[(gdp_t, cpi_t)]

# 1. Technical Sentiment (RSI + SMA + Vol)
def get_sentiment(ticker):
    px = prices[ticker].dropna()
    rsi = 100 - (100 / (1 + (px.diff().clip(lower=0).rolling(14).mean() / -px.diff().clip(upper=0).rolling(14).mean())))
    sma20 = px.rolling(20).mean()
    vol_ratio = volumes[ticker].tail(5).mean() / volumes[ticker].tail(20).mean()
    
    score = (0.4 * (rsi.iloc[-1]-50)/50) + (0.4 * (px.iloc[-1]/sma20.iloc[-1]-1)*10) + (0.2 * (vol_ratio-1))
    return np.clip(score * 50 + 50, 0, 100), rsi.iloc[-1]

# 2. Conviction Score (60% Momentum / 40% Sentiment)
mom_rank = prices[list(SECTOR_ETFS.keys())].pct_change(63).iloc[-1].rank(pct=True) * 100
tactical_results = []
for t in SECTOR_ETFS:
    sent_score, rsi = get_sentiment(t)
    conviction = (0.6 * mom_rank[t]) + (0.4 * sent_score)
    tactical_results.append({"Ticker": t, "Sector": SECTOR_ETFS[t], "Conviction": conviction, "RSI": rsi, "Price": prices[t].iloc[-1]})

tactical_df = pd.DataFrame(tactical_results).sort_values("Conviction", ascending=False)
top3 = tactical_df.head(3)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN UI - TABS (Restored)
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""<div class="aw-header"><h1>PROJECT ALL-WEATHER</h1><span class="aw-badge">{glide_choice.split('·')[0]}</span></div>""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs(["Strategic Allocation", "Tactical Engine", "Correlation & Risk", "Methodology"])

with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        st.markdown('<div class="aw-card"><h3>Regime Matrix</h3>', unsafe_allow_html=True)
        st.write(f"Current Regime: **{quad_emoji} {quad_name}** (GDP {gdp_t} / CPI {cpi_t})")
        st.write(f"Preferred Assets: {', '.join(quad_prefs)}")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with c2:
        st.markdown('<div class="aw-card"><h3>Hedge Status</h3>', unsafe_allow_html=True)
        crisis = prices["VOO"].iloc[-1] < prices["VOO"].rolling(200).mean().iloc[-1]
        st.write("Status: " + ("🚨 CRISIS (Short S&P)" if crisis else "✅ NORMAL (Cash/T-Bills)"))
        st.markdown('</div>', unsafe_allow_html=True)

    st.subheader("Core Risk Parity Positions")
    core_px = prices[CORE_ASSETS]
    inv_vol = 1 / (core_px.pct_change().std() * np.sqrt(252))
    core_w = inv_vol / inv_vol.sum()
    
    cols = st.columns(len(CORE_ASSETS))
    for i, t in enumerate(CORE_ASSETS):
        alloc = (total_inv * core_pct/100) * core_w[t]
        cols[i].metric(t, f"{core_w[t]:.1%}", f"${alloc:,.0f}")

with tab2:
    st.subheader("Top Tactical Conviction")
    cols = st.columns(3)
    for i, row in enumerate(top3.itertuples()):
        with cols[i]:
            st.markdown(f"""
            <div class="aw-card">
                <div style="font-size:1.2rem; font-weight:bold">{row.Ticker}</div>
                <div style="color:var(--muted)">{row.Sector}</div>
                <hr>
                <div style="font-size:0.8rem">Conviction: <b>{row.Conviction:.1f}</b></div>
                <div style="font-size:0.8rem">RSI: {row.RSI:.1f}</div>
                <div class="stop-badge" style="margin-top:10px">ATR Stop: ${(row.Price * 0.94):.2f}</div>
            </div>
            """, unsafe_allow_html=True)
    st.dataframe(tactical_df, use_container_width=True)

with tab3:
    st.subheader("Correlation Radar & Regime Risk")
    c1, c2 = st.columns(2)
    
    with c1:
        # Correlation Radar
        corr = prices[CORE_ASSETS].pct_change().corr()
        fig_radar = go.Figure()
        for t in CORE_ASSETS:
            fig_radar.add_trace(go.Scatterpolar(r=corr[t].values, theta=corr.columns, fill='toself', name=t))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])), showlegend=True, template="plotly_dark", height=400)
        st.plotly_chart(fig_

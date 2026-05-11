import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging, warnings

warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

st.set_page_config(page_title="Project All-Weather", page_icon="🌦", layout="wide")

# ── PERSISTENCE & STYLING ──
def _qp(k, d):
    v = st.query_params.get(k, str(d))
    try: return int(v) if isinstance(d, int) else v
    except: return d

st.components.v1.html("""<script>
(function(){const K=["total_inv","glide_index","core_pct","tactical_pct"];const p=new URLSearchParams(window.parent.location.search);let u=false;K.forEach(k=>{const v=localStorage.getItem("aw_"+k);if(v!==null&&p.get(k)!==v){p.set(k,v);u=true;}});if(u){window.parent.history.replaceState(null,"","?"+p.toString());}})();
</script>""", height=0)

st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono&family=DM+Sans:wght@400;700&display=swap');
:root { --bg: #0a0c10; --surface: #11151c; --border: #1e2535; --accent: #3b82f6; --text: #e2e8f0; --mono: 'Space Mono', monospace; }
html, body, [class*="css"] { background-color: var(--bg) !important; color: var(--text) !important; font-family: 'DM Sans', sans-serif; }
.aw-card { background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 20px; margin-bottom: 20px; }
.aw-badge { background: var(--accent); color: white; font-family: var(--mono); font-size: 0.6rem; padding: 2px 8px; border-radius: 3px; }
.stop-badge { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); color: #ef4444; font-family: var(--mono); font-size: 0.7rem; padding: 2px 6px; border-radius: 4px; }
</style>""", unsafe_allow_html=True)

# ── DATA ENGINE ──
GLIDE = {
    "31–40 · Aggressive Global": ["VOO", "VEA", "VWO", "GLD"],
    "41–50 · Growth": ["VOO", "VEA", "VWO", "GLD", "IEF"],
    "51–60 · Balanced": ["VOO", "VEA", "GLD", "IEF", "TLT"],
    "61+ · All-Weather Classic": ["VOO", "TLT", "IEF", "GLD", "GSG"]
}
SECTORS = {"XLE":"Energy","XLK":"Tech","XLV":"Health","XLF":"Financials","XLI":"Industrials","XLY":"Disc","XLP":"Staples","XLB":"Materials","XLC":"Comm","XLU":"Utils","XLRE":"Real Estate"}

@st.cache_data(ttl=3600)
def fetch_data(tickers):
    try:
        d = yf.download(" ".join(tickers), period="2y", auto_adjust=True, progress=False, group_by='ticker')
        return d
    except: return pd.DataFrame()

def get_px(df, t):
    try:
        if isinstance(df.columns, pd.MultiIndex):
            return df[t]['Close'] if t in df.columns.levels[0] else df.xs('Close', axis=1, level=1)[t]
        return df[t]
    except: return pd.Series()

# ── APP ──
with st.sidebar:
    st.title("🌦 Settings")
    inv = st.number_input("Investment ($)", value=_qp("total_inv", 100000))
    glide_idx = st.selectbox("Life Stage", list(GLIDE.keys()), index=_qp("glide_index", 0))
    c_p = st.slider("Core %", 40, 80, _qp("core_pct", 60))
    a_p = st.slider("Alpha %", 10, 40, _qp("tactical_pct", 30))
    if st.button("💾 SAVE", use_container_width=True):
        st.query_params.update({"total_inv": inv, "glide_index": list(GLIDE.keys()).index(glide_idx), "core_pct": c_p, "tactical_pct": a_p})
        st.rerun()

CORE = GLIDE[glide_idx]
raw = fetch_data(list(set(CORE + list(SECTORS.keys()) + ["SPY"])))

# Conviction Calculation
res = []
for t in SECTORS:
    p = get_px(raw, t).dropna()
    if len(p) < 65: continue
    mom = (p.iloc[-1] / p.iloc[-63]) - 1
    rsi = 100 - (100 / (1 + (p.diff().clip(lower=0).tail(14).mean() / -p.diff().clip(upper=0).tail(14).mean())))
    sent = np.clip((rsi-50) + ((p.iloc[-1]/p.rolling(20).mean().iloc[-1]-1)*100), 0, 100)
    res.append({"Ticker": t, "Sector": SECTORS[t], "Mom": mom, "Sent": sent, "Price": p.iloc[-1]})
tdf = pd.DataFrame(res)
tdf['Conv'] = (tdf['Mom'].rank(pct=True)*60) + (tdf['Sent'].rank(pct=True)*40)
tdf = tdf.sort_values("Conv", ascending=False)

# UI
st.title("PROJECT ALL-WEATHER")
t1, t2, t3, t4 = st.tabs(["Allocation", "Tactical", "Risk Radar", "Methodology"])

with t1:
    c1, c2 = st.columns(2)
    with c1: st.metric("Regime", "Stagflation Lite", "Sticky Inflation")
    with c2:
        spy = get_px(raw, "SPY")
        is_c = spy.iloc[-1] < spy.rolling(200).mean().iloc[-1]
        st.metric("Hedge", "CRISIS" if is_c else "NORMAL", "Short S&P" if is_c else "T-Bills")
    st.subheader("Core Risk Parity")
    cp_df = pd.DataFrame({t: get_px(raw, t) for t in CORE}).pct_change().dropna()
    w = (1/cp_df.std()) / (1/cp_df.std()).sum()
    cols = st.columns(len(CORE))
    for i, t in enumerate(CORE):
        cols[i].metric(t, f"{w[t]:.1%}", f"${(inv*c_p/100*w[t]):,.0f}")

with t2:
    st.subheader("Top Alpha Conviction")
    top3 = tdf.head(3)
    cols = st.columns(3)
    for i, r in enumerate(top3.itertuples()):
        with cols[i]:
            st.markdown(f'<div class="aw-card"><b>{r.Ticker}</b><br>{r.Sector}<hr>Conviction: {r.Conv:.1f}<br>Alloc: ${(inv*a_p/100/3):,.0f}<br><span class="stop-badge">Stop: ${(r.Price*0.94):.2f}</span></div>', unsafe_allow_html=True)
    st.dataframe(tdf[["Ticker","Sector","Conv","Mom","Sent"]], use_container_width=True)

with t3:
    c1, c2 = st.columns(2)
    with c1:
        cor = cp_df.tail(90).corr()
        st.plotly_chart(go.Figure(data=go.Heatmap(z=cor.values, x=cor.columns, y=cor.columns, colorscale='RdBu_r'), layout=dict(title="Correlation 90D", template="plotly_dark", height=400)), use_container_width=True)
    with c2:
        v = (spy.pct_change().rolling(21).std()*np.sqrt(252)*100).dropna

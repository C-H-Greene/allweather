"""
styles.py
All CSS in one place. Edit this file to change the visual design
without touching any logic files.
"""

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

:root {
  --bg:       #080a0e;
  --bg1:      #0d1117;
  --bg2:      #131920;
  --bg3:      #1a2332;
  --border:   #1e2d3d;
  --border2:  #243447;
  --text:     #e6edf3;
  --muted:    #7d8590;
  --dim:      #3d4f63;
  --bull:     #3fb950;
  --bear:     #f85149;
  --neutral:  #d29922;
  --info:     #58a6ff;
  --purple:   #bc8cff;
  --mono:     'IBM Plex Mono', monospace;
  --sans:     'IBM Plex Sans', sans-serif;
  --radius:   6px;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, [class*="css"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: var(--sans) !important;
}
.stApp { background: var(--bg); }

/* ── 508: Skip link ── */
.skip-link {
  position: absolute; top: -40px; left: 0;
  padding: 8px 16px; background: var(--info); color: #000;
  font-family: var(--mono); font-size: .75rem;
  border-radius: 0 0 4px 0; z-index: 9999; text-decoration: none;
}
.skip-link:focus { top: 0; }

/* ── 508: Focus indicators ── */
*:focus-visible {
  outline: 2px solid var(--info) !important;
  outline-offset: 2px !important;
}

/* ── 508: Screen-reader only ── */
.sr-only {
  position: absolute; width: 1px; height: 1px;
  padding: 0; margin: -1px; overflow: hidden;
  clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}

/* ── Sidebar ── */
div[data-testid="stSidebar"] {
  background: var(--bg1) !important;
  border-right: 1px solid var(--border) !important;
}
div[data-testid="stSidebar"] * { color: var(--text) !important; }

/* ── Buttons ── */
.stButton > button {
  background: var(--bg3) !important;
  color: var(--text) !important;
  border: 1px solid var(--border2) !important;
  font-family: var(--mono) !important;
  font-size: .7rem !important;
  letter-spacing: .05em !important;
  border-radius: var(--radius) !important;
  padding: 6px 16px !important;
  transition: border-color .15s !important;
}
.stButton > button:hover { border-color: var(--info) !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  background: transparent !important;
  border-bottom: 1px solid var(--border) !important;
  gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  font-family: var(--mono) !important;
  font-size: .68rem !important;
  letter-spacing: .08em !important;
  text-transform: uppercase !important;
  padding: 10px 20px !important;
  color: var(--muted) !important;
  border-bottom: 2px solid transparent !important;
  background: transparent !important;
}
.stTabs [aria-selected="true"] {
  color: var(--text) !important;
  border-bottom-color: var(--info) !important;
}

/* ── Expanders ── */
.stExpander {
  border: 1px solid var(--border) !important;
  border-radius: var(--radius) !important;
  background: var(--bg1) !important;
}

/* ── Inputs ── */
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
  background: var(--bg2) !important;
  border-color: var(--border) !important;
  color: var(--text) !important;
  font-family: var(--mono) !important;
  font-size: .8rem !important;
}
.stDataFrame { background: var(--bg1) !important; }
.stSlider > div > div > div { background: var(--info) !important; }
hr { border-color: var(--border) !important; margin: 16px 0 !important; }

/* ══ Component classes ═══════════════════════════════════════════════════════ */

/* Top status bar */
.aw-topbar {
  display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
  padding: 10px 0 14px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
  font-family: var(--mono); font-size: .7rem; color: var(--muted);
}
.aw-topbar-brand {
  font-size: 1rem; font-weight: 600; color: var(--text);
  letter-spacing: .04em;
}

/* Regime banner */
.regime-banner {
  display: flex; align-items: center; gap: 20px;
  padding: 18px 22px;
  background: var(--bg2);
  border: 1px solid var(--border2);
  border-left: 4px solid var(--info);
  border-radius: var(--radius);
  margin-bottom: 18px;
}
.regime-emoji  { font-size: 2rem; line-height: 1; }
.regime-name   { font-family: var(--mono); font-size: 1.5rem; font-weight: 600; }
.regime-meta   { font-family: var(--mono); font-size: .65rem; color: var(--muted); margin: .3rem 0 .5rem; }
.regime-rationale { font-size: .78rem; color: var(--muted); line-height: 1.6; flex: 1; }
.regime-score  { text-align: right; white-space: nowrap; }
.regime-score-num {
  font-family: var(--mono); font-size: 2.2rem; font-weight: 600; line-height: 1;
}
.regime-score-label {
  font-family: var(--mono); font-size: .6rem; letter-spacing: .1em;
  text-transform: uppercase; color: var(--muted); margin-top: 3px;
}

/* Bucket card */
.bucket-card {
  background: var(--bg1);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 14px 18px;
  margin-bottom: 12px;
}
.bucket-header {
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 10px;
}
.bucket-name {
  font-family: var(--mono); font-size: .62rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--muted);
}
.bucket-weight { font-family: var(--mono); font-size: .95rem; font-weight: 600; }

/* Position row */
.pos-row {
  display: grid; grid-template-columns: 52px 1fr auto auto;
  align-items: start; gap: 10px;
  padding: 7px 0; border-bottom: 1px solid var(--border);
}
.pos-row:last-child { border-bottom: none; }
.pos-ticker { font-family: var(--mono); font-size: .88rem; font-weight: 600; }
.pos-name   { font-size: .74rem; color: var(--muted); }
.pos-why    { font-size: .68rem; color: var(--muted); margin-top: 1px; }
.pos-tlh    { font-family: var(--mono); font-size: .6rem; color: var(--neutral); margin-top: 1px; }
.pos-stop   { font-family: var(--mono); font-size: .6rem; color: var(--bear); margin-top: 2px; }
.pos-weight { font-family: var(--mono); font-size: .82rem; text-align: right; }
.pos-er     { font-family: var(--mono); font-size: .62rem; color: var(--dim); text-align: right; }

/* Score pills */
.pill {
  display: inline-flex; align-items: center;
  padding: 1px 6px; border-radius: 3px;
  font-family: var(--mono); font-size: .6rem; font-weight: 500;
}
.pill-regime  { background: rgba(63,185,80,.15);  color: #3fb950; }
.pill-momentum{ background: rgba(88,166,255,.12); color: #58a6ff; }
.pill-pe      { background: rgba(255,255,255,.05); }

/* Signal rows (macro detail) */
.signal-row {
  display: flex; align-items: center; gap: 10px;
  padding: 6px 0; border-bottom: 1px solid var(--border); font-size: .76rem;
}
.signal-row:last-child { border-bottom: none; }
.signal-name  { color: var(--muted); width: 150px; flex-shrink: 0; font-family: var(--mono); font-size: .68rem; }
.signal-val   { font-family: var(--mono); font-weight: 500; width: 76px; }
.signal-track { flex: 1; height: 4px; background: var(--bg3); border-radius: 2px; }
.signal-desc  { font-size: .68rem; color: var(--muted); width: 120px; text-align: right; }

/* Alert banners */
.aw-alert {
  display: flex; align-items: flex-start; gap: 10px;
  padding: 10px 14px; border-radius: var(--radius);
  margin-bottom: 12px; font-size: .76rem; line-height: 1.5;
}
.aw-alert-warn { background: rgba(210,153,34,.1);  border: 1px solid rgba(210,153,34,.3); }
.aw-alert-crit { background: rgba(248,81,73,.1);   border: 1px solid rgba(248,81,73,.3); }
.aw-alert-info { background: rgba(88,166,255,.08); border: 1px solid rgba(88,166,255,.25); }
.aw-alert-good { background: rgba(63,185,80,.08);  border: 1px solid rgba(63,185,80,.25); }

/* Probability bar */
.tp-track {
  height: 10px; background: var(--bg3); border-radius: 5px;
  overflow: hidden; margin: 8px 0;
}

/* Indicator cards (outlook screen) */
.ind-card {
  background: var(--bg1); border: 1px solid var(--border);
  border-radius: var(--radius); padding: 14px 16px; margin-bottom: 10px;
}
.ind-label {
  font-family: var(--mono); font-size: .6rem;
  letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
  margin-bottom: 5px;
}
.ind-value { font-family: var(--mono); font-size: .95rem; font-weight: 600; }
.ind-signal { font-family: var(--mono); font-size: .68rem; margin: 3px 0; }
.ind-desc   { font-size: .7rem; color: var(--muted); line-height: 1.5; }

/* Tracker table */
.tracker-header {
  display: grid;
  grid-template-columns: 52px 80px 80px 80px 80px 1fr;
  gap: 8px; padding: 6px 0 8px;
  border-bottom: 1px solid var(--border);
  font-family: var(--mono); font-size: .58rem;
  color: var(--muted); letter-spacing: .08em; text-transform: uppercase;
}
.tracker-row {
  display: grid;
  grid-template-columns: 52px 80px 80px 80px 80px 1fr;
  gap: 8px; padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: .72rem; align-items: center;
}
.tracker-row:last-child { border-bottom: none; }

/* Quadrant matrix */
.quad-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
}
.quad-cell {
  padding: 10px; border: 1px solid var(--border);
  border-radius: var(--radius); text-align: center;
  background: var(--bg2);
}
.quad-cell.active {
  background: rgba(88,166,255,.1);
  border-color: var(--info);
}
.quad-cell-emoji { font-size: 1.1rem; }
.quad-cell-name  { font-family: var(--mono); font-size: .62rem; margin-top: 2px; }
.quad-cell-now   { font-size: .55rem; color: var(--info); margin-top: 2px; }
</style>
"""

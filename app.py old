import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import math
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
# PERSISTENCE — localStorage ↔ query_params bridge
# On first load: JS reads localStorage → sets URL params → Streamlit re-runs
# On save: JS writes current sidebar values back to localStorage
# ══════════════════════════════════════════════════════════════════════════════

PARAM_DEFAULTS = {
    "total_inv":    "100000",
    "glide_index":  "0",
    "core_pct":     "60",
    "tactical_pct": "30",
}

def _qp(key: str, default):
    """Read a query param, falling back to default. Casts to int if default is int."""
    val = st.query_params.get(key, str(default))
    try:
        return int(val) if isinstance(default, int) else val
    except (ValueError, TypeError):
        return default

# Inject JS once: reads localStorage → pushes into URL params → triggers rerun
st.components.v1.html("""
<script>
(function() {
  const KEYS = ["total_inv","glide_index","core_pct","tactical_pct"];
  const stored = {};
  let needsUpdate = false;
  const params = new URLSearchParams(window.parent.location.search);

  KEYS.forEach(k => {
    const v = localStorage.getItem("aw_" + k);
    if (v !== null && params.get(k) !== v) {
      stored[k] = v;
      needsUpdate = true;
    }
  });

  if (needsUpdate) {
    KEYS.forEach(k => { if (stored[k] !== undefined) params.set(k, stored[k]); });
    // Replace URL without full reload; Streamlit picks up query_params on next interaction
    window.parent.history.replaceState(null, "", "?" + params.toString());
  }
})();
</script>
""", height=0)

# Read persisted values (or defaults) from query params
_total_inv_default    = _qp("total_inv",    100_000)
_glide_index_default  = _qp("glide_index",  0)
_core_pct_default     = _qp("core_pct",     60)
_tactical_pct_default = _qp("tactical_pct", 30)


# ── Styling ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Design tokens ─────────────────────────────────────────────────────────── */
:root {
    --bg:       #0a0c10;
    --surface:  #10141c;
    --surface2: #161b26;
    --border:   #1e2535;
    --accent:   #3b82f6;
    --accent2:  #10b981;
    --accent3:  #f59e0b;
    --accent4:  #ef4444;
    --text:     #e2e8f0;   /* contrast vs --bg: 12.6:1 — WCAG AAA */
    --muted:    #94a3b8;   /* contrast vs --bg:  5.9:1 — WCAG AA  */
    --mono:     'Space Mono', monospace;
    --sans:     'DM Sans', sans-serif;
    --focus:    #60a5fa;   /* visible focus ring color */
}

/* ── Base ──────────────────────────────────────────────────────────────────── */
html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans);
}
.stApp { background-color: var(--bg); }

/* ── Skip-to-content link (508) ────────────────────────────────────────────── */
.skip-link {
    position: absolute; top: -40px; left: 0;
    background: var(--accent); color: white;
    padding: 8px 16px; z-index: 9999;
    font-family: var(--mono); font-size: 0.8rem;
    border-radius: 0 0 4px 0;
    text-decoration: none;
}
.skip-link:focus { top: 0; }

/* ── Focus indicators (508) ────────────────────────────────────────────────── */
*:focus-visible {
    outline: 2px solid var(--focus) !important;
    outline-offset: 2px !important;
}
button:focus-visible, a:focus-visible, [tabindex]:focus-visible {
    outline: 3px solid var(--focus) !important;
    outline-offset: 3px !important;
}

/* ── Header ────────────────────────────────────────────────────────────────── */
.aw-header {
    display: flex; align-items: center; gap: 16px;
    padding: 20px 0 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 20px;
}
.aw-header h1 {
    font-family: var(--mono);
    font-size: 1.4rem;
    font-weight: 700;
    letter-spacing: -0.5px;
    color: var(--text);
    margin: 0;
}
.aw-badge {
    background: var(--accent);
    color: white;
    font-family: var(--mono);
    font-size: 0.6rem;
    padding: 2px 8px;
    border-radius: 3px;
    letter-spacing: 1px;
}

/* ── Status bar (compact top-of-page summary) ──────────────────────────────── */
.aw-status-bar {
    display: flex; gap: 16px; flex-wrap: wrap;
    padding: 10px 16px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 16px;
    align-items: center;
}
.aw-status-item {
    display: flex; align-items: center; gap: 6px;
    font-family: var(--mono); font-size: 0.7rem;
    color: var(--muted);
}
.aw-status-item b { color: var(--text); }
.aw-status-dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    flex-shrink: 0;
}

/* ── Cards ─────────────────────────────────────────────────────────────────── */
.aw-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 16px;
}
.aw-card-title {
    font-family: var(--mono);
    font-size: 0.68rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 14px;
}

/* ── Section dividers within cards ─────────────────────────────────────────── */
.aw-section-label {
    font-family: var(--mono);
    font-size: 0.6rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    padding: 10px 0 6px;
    border-top: 1px solid var(--border);
    margin-top: 14px;
}

/* ── Metric tiles ───────────────────────────────────────────────────────────── */
.metric-row { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.metric-tile {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px 16px;
    flex: 1;
    min-width: 110px;
}
.metric-tile .label {
    font-size: 0.62rem;
    font-family: var(--mono);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 5px;
}
.metric-tile .value {
    font-family: var(--mono);
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--text);
}
.metric-tile .sub { font-size: 0.72rem; color: var(--muted); margin-top: 2px; }

/* ── Regime matrix cells ────────────────────────────────────────────────────── */
.regime-cell {
    border-radius: 6px;
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    font-family: var(--mono); font-size: 0.72rem;
    letter-spacing: 1px; text-transform: uppercase;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--muted);
    transition: all 0.2s;
    text-align: center; padding: 8px;
}
.regime-cell.active {
    border-color: var(--accent);
    background: rgba(59,130,246,0.12);
    color: var(--text);
    box-shadow: 0 0 16px rgba(59,130,246,0.12);
}
.regime-cell .emoji { font-size: 1.3rem; margin-bottom: 4px; }

/* ── Allocation bars ────────────────────────────────────────────────────────── */
.alloc-bar-container { margin-bottom: 10px; }
.alloc-bar-label {
    display: flex; justify-content: space-between;
    font-family: var(--mono); font-size: 0.72rem;
    margin-bottom: 4px; color: var(--text);
}
.alloc-bar-track {
    height: 5px; background: var(--surface2);
    border-radius: 3px; overflow: hidden;
}
.alloc-bar-fill { height: 100%; border-radius: 3px; transition: width 0.5s ease; }

/* ── Status badges ─────────────────────────────────────────────────────────── */
.stop-badge {
    display: inline-flex; align-items: center; gap: 4px;
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.3);
    color: #ef4444;
    font-family: var(--mono); font-size: 0.68rem;
    padding: 2px 7px; border-radius: 4px;
}
/* Status text that pairs with color (508: color must not be sole indicator) */
.status-positive::before { content: "↑ "; }
.status-negative::before { content: "↓ "; }
.status-neutral::before  { content: "→ "; }
.status-warning::before  { content: "⚠ "; }
.status-critical::before { content: "🚨 "; }

/* ── Alert banners ──────────────────────────────────────────────────────────── */
.aw-alert {
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 14px;
    display: flex; align-items: flex-start; gap: 10px;
}
.aw-alert-icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 1px; }
.aw-alert-body { flex: 1; }
.aw-alert-title {
    font-family: var(--mono); font-weight: 700;
    font-size: 0.78rem; margin-bottom: 3px;
}
.aw-alert-text { font-size: 0.74rem; color: var(--muted); line-height: 1.5; }
.aw-alert-danger  { background: rgba(239,68,68,0.08); border: 1px solid rgba(239,68,68,0.3); }
.aw-alert-success { background: rgba(16,185,129,0.08); border: 1px solid rgba(16,185,129,0.3); }
.aw-alert-warning { background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.3); }
.aw-alert-info    { background: rgba(59,130,246,0.08); border: 1px solid rgba(59,130,246,0.3); }

/* ── Data table rows ────────────────────────────────────────────────────────── */
.aw-row {
    display: flex; align-items: center; gap: 12px;
    padding: 9px 0;
    border-bottom: 1px solid var(--border);
}
.aw-row:last-child { border-bottom: none; }

/* ── Streamlit component overrides ─────────────────────────────────────────── */
.stSlider > div > div > div { background: var(--accent) !important; }
.stDataFrame { background: var(--surface) !important; }
div[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
div[data-testid="stSidebar"] * { color: var(--text) !important; }
div[data-testid="stMetric"] {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px; padding: 12px 16px;
}
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    font-family: var(--mono) !important;
    font-size: 0.73rem !important;
    letter-spacing: 1px !important;
    border-radius: 5px !important;
    padding: 7px 18px !important;
}
.stButton > button:hover  { opacity: 0.85 !important; }
.stButton > button:focus  { outline: 3px solid var(--focus) !important; }
hr { border-color: var(--border) !important; }
.stTabs [data-baseweb="tab"] {
    font-family: var(--mono) !important;
    font-size: 0.68rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase;
}
.stTabs [aria-selected="true"] { color: var(--accent) !important; }
.stExpander { border: 1px solid var(--border) !important; border-radius: 6px !important; }

/* ── Visually hidden (508: accessible text for screen readers) ──────────────── */
.sr-only {
    position: absolute; width: 1px; height: 1px;
    padding: 0; margin: -1px; overflow: hidden;
    clip: rect(0,0,0,0); white-space: nowrap; border: 0;
}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════

# Age-adjusted core: equity-dominant, gold as inflation hedge, minimal bonds
# Glide path shifts this composition as time horizon shrinks
CORE_COLORS   = ["#3b82f6", "#10b981", "#f59e0b", "#a78bfa", "#ef4444"]

# Glide path presets — bond weight increases, equity decreases with age
GLIDE_PRESETS = {
    "31–40 · Aggressive Growth": {
        "assets": ["VOO", "VEA", "VWO", "GLD"],
        "description": "Pure equity + gold. Zero bond drag. Max compounding window.",
    },
    "41–50 · Growth": {
        "assets": ["VOO", "VEA", "VWO", "GLD", "IEF"],
        "description": "Adding mid-term bonds (~10% weight). Begin reducing sequence risk.",
    },
    "51–55 · Growth / Conservative": {
        "assets": ["VOO", "VEA", "GLD", "IEF", "TLT"],
        "description": "Reduced intl. exposure, adding long bonds (~20%). Capital preservation begins.",
    },
    "56–60 · Conservative": {
        "assets": ["VOO", "GLD", "IEF", "TLT", "GSG"],
        "description": "Transitioning to full risk parity. Drawdown protection priority.",
    },
    "60+ · All-Weather Classic": {
        "assets": ["VOO", "TLT", "IEF", "GLD", "GSG"],
        "description": "Original Bridgewater All-Weather. Designed for capital preservation.",
    },
}

SECTOR_ETFS   = {
    "XLE": "Energy",       "XLK": "Technology",    "XLV": "Health Care",
    "XLF": "Financials",   "XLI": "Industrials",   "XLY": "Cons. Disc.",
    "XLP": "Cons. Staples","XLB": "Materials",     "XLC": "Comm. Svcs.",
    "XLU": "Utilities",    "XLRE": "Real Estate",
}
HEDGE_ASSETS  = {"BIL": "Cash (T-Bills)", "SH": "Short S&P 500", "VIXY": "VIX Futures"}

QUADRANT_MAP = {
    ("rising","rising"):  ("Stagflation",    "🔥", ["XLE","XLB","GLD"]),
    ("rising","falling"): ("Expansion",      "🚀", ["XLK","XLY","XLF"]),
    ("falling","rising"): ("Recession",      "❄️", ["XLU","XLP","XLV"]),
    ("falling","falling"):("Deflation",      "🌧",  ["TLT","XLU","GLD"]),
}

DEMO_PRICES = {
    "VOO": 480.0, "VEA": 52.0,  "VWO": 43.0,  "GLD": 225.0,
    "TLT": 94.0,  "IEF": 98.0,  "GSG": 19.5,
    "XLE": 89.0,  "XLK": 222.0, "XLV": 141.0, "XLF": 44.0,  "XLI": 119.0,
    "XLY": 191.0, "XLP": 77.0,  "XLB": 88.0,  "XLC": 91.0,  "XLU": 68.0,
    "XLRE": 42.0, "BIL": 91.5,  "SH": 14.0,   "VIXY": 25.0,
}
DEMO_VOLS = {
    "VOO": 0.155, "VEA": 0.165, "VWO": 0.185, "GLD": 0.115,
    "TLT": 0.135, "IEF": 0.065, "GSG": 0.225,
}

def _make_demo_prices(tickers, n=260):
    """Synthesize realistic random-walk price series for demo mode."""
    np.random.seed(42)
    dates = pd.bdate_range(end=datetime.today(), periods=n)
    result = {}
    for t in tickers:
        base = DEMO_PRICES.get(t, 100.0)
        vol  = DEMO_VOLS.get(t, 0.18)
        daily_vol = vol / np.sqrt(252)
        returns = np.random.normal(0.0003, daily_vol, n)
        prices  = base * np.exp(np.cumsum(returns) - np.cumsum(returns)[-1])
        # walk forward from base so last price ≈ base
        result[t] = prices
    return pd.DataFrame(result, index=dates)

@st.cache_data(ttl=3600)
def fetch_ohlcv(tickers: tuple, period: str = "1y") -> tuple:
    """
    Single yf.download call returning (close_df, volume_df).
    Replaces separate fetch_price_data + fetch_volume_data calls.
    tickers is a tuple for st.cache_data hashability.
    """
    try:
        data = yf.download(list(tickers), period=period, auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            close_df  = data["Close"]
            volume_df = data["Volume"]
            high_df   = data["High"]
            low_df    = data["Low"]
        else:
            t = list(tickers)[0]
            close_df  = data[["Close"]].rename(columns={"Close": t})
            volume_df = data[["Volume"]].rename(columns={"Volume": t})
            high_df   = data[["High"]].rename(columns={"High": t})
            low_df    = data[["Low"]].rename(columns={"Low": t})

        if close_df.empty or close_df.isnull().all().all():
            raise ValueError("Empty response")

        return close_df.ffill(), volume_df.ffill(), high_df.ffill(), low_df.ffill()

    except Exception:
        st.warning("⚠ Live market data unavailable — running in **Demo Mode** with synthetic prices. "
                   "Deploy locally or on Streamlit Cloud to enable real-time data.", icon="🔌")
        prices = _make_demo_prices(list(tickers))
        np.random.seed(99)
        dates  = prices.index
        vols   = pd.DataFrame(
            {t: (np.random.lognormal(0, 0.3, len(dates)) * 20_000_000).astype(int)
             for t in tickers},
            index=dates,
        )
        # Synthetic high/low from close ±0.5%
        highs = prices * 1.005
        lows  = prices * 0.995
        return prices, vols, highs, lows

# Keep fetch_price_data as a thin wrapper for any remaining call sites
def fetch_price_data(tickers: list, period: str = "1y") -> pd.DataFrame:
    close, _, _, _ = fetch_ohlcv(tuple(tickers), period)
    return close

def fetch_volume_data(tickers: list, period: str = "3mo") -> pd.DataFrame:
    _, vol, _, _ = fetch_ohlcv(tuple(tickers), period)
    return vol


@st.cache_data(ttl=3600)
def fetch_options_pcr(tickers: tuple) -> dict:
    """
    Fetch Put/Call volume ratio for each ticker using yfinance options chains.
    Uses the nearest 2 expiration dates to get a liquid cross-section.
    Falls back to None per ticker if options data unavailable.
    """
    result = {}
    for ticker in tickers:
        try:
            t    = yf.Ticker(ticker)
            exps = t.options
            if not exps:
                result[ticker] = None
                continue
            total_put_vol  = 0
            total_call_vol = 0
            # Use nearest 2 expirations for liquidity
            for exp in exps[:2]:
                chain          = t.option_chain(exp)
                total_call_vol += chain.calls["volume"].fillna(0).sum()
                total_put_vol  += chain.puts["volume"].fillna(0).sum()
            if total_call_vol > 0:
                result[ticker] = round(total_put_vol / total_call_vol, 3)
            else:
                result[ticker] = None
        except Exception:
            result[ticker] = None
    return result

@st.cache_data(ttl=3600)
def fetch_fred_macro():
    """
    Pull macro data from FRED. Returns:
      - Coincident indicators: GDP trend/mom/streak, CPI trend/mom/streak
      - Leading indicators:    yield curve (10Y-2Y), ISM Manufacturing PMI,
                               Conference Board LEI, initial jobless claims

    All series fetched via FRED's public CSV endpoint — no API key required.

    Leading indicators lead GDP by ~6-9 months and are what sophisticated
    macro managers actually watch for regime shifts. Coincident indicators
    (GDP, CPI) confirm what leading indicators predicted.

    FRED Series IDs used:
        GDP         — Gross Domestic Product, quarterly
        CPIAUCSL    — CPI All Urban Consumers, monthly
        T10Y2Y      — 10Y minus 2Y Treasury spread (yield curve), daily → monthly avg
        MANEMP      — ISM Manufacturing PMI proxy via NAPM
        INDPRO      — Industrial Production Index (LEI component)
        ICSA        — Initial Jobless Claims, weekly → monthly avg
    """
    import urllib.request

    def fred_series(series_id: str, tail: int = 18) -> pd.Series | None:
        url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
               f"&vintage_date={datetime.today().strftime('%Y-%m-%d')}")
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                lines = r.read().decode().strip().split('\n')
            rows  = [l.split(',') for l in lines[1:] if '.' in l]
            dates = [r[0] for r in rows]
            vals  = [float(r[1]) for r in rows]
            return pd.Series(vals, index=pd.to_datetime(dates)).dropna().tail(tail)
        except Exception:
            return None

    def streak_count(series: pd.Series) -> tuple[str, int]:
        """Return (direction, consecutive_periods) for the latest trend."""
        diffs     = np.sign(series.diff().dropna())
        current_d = diffs.iloc[-1]
        direction = "rising" if current_d > 0 else "falling"
        count = 1
        for d in reversed(diffs.iloc[:-1].tolist()):
            if np.sign(d) == current_d:
                count += 1
            else:
                break
        return direction, count

    # ── Fetch all series ──────────────────────────────────────────────────
 

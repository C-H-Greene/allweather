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
# PERSISTENCE — query_params only (mobile-compatible, no JavaScript injection)
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

# Persistence: query_params only — no localStorage/JS (mobile compatible)

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
    gdp      = fred_series("GDP",      tail=12)
    cpi      = fred_series("CPIAUCSL", tail=18)
    yc_raw   = fred_series("T10Y2Y",   tail=756)   # daily, ~3 years
    ism_raw  = fred_series("MANEMP",   tail=24)    # manufacturing employment proxy
    indpro   = fred_series("INDPRO",   tail=24)    # industrial production
    claims   = fred_series("ICSA",     tail=104)   # weekly claims

    # ── Coincident: GDP ───────────────────────────────────────────────────
    gdp_trend = "rising"; gdp_mom = 0.0; gdp_streak = 1; gdp_vals = []
    if gdp is not None and len(gdp) >= 2:
        gdp_trend, gdp_streak = streak_count(gdp)
        gdp_mom    = float((gdp.iloc[-1] - gdp.iloc[-2]) / gdp.iloc[-2] * 100)
        gdp_vals   = gdp.tolist()

    # ── Coincident: CPI ───────────────────────────────────────────────────
    cpi_trend = "falling"; cpi_mom = 0.0; cpi_streak = 1; cpi_vals = []
    if cpi is not None and len(cpi) >= 2:
        lookback   = min(5, len(cpi) - 1)
        cpi_trend  = "rising" if cpi.iloc[-1] > cpi.iloc[-lookback] else "falling"
        cpi_mom    = float((cpi.iloc[-1] - cpi.iloc[-lookback]) / cpi.iloc[-lookback] * 100)
        _, cpi_streak = streak_count(cpi)
        cpi_vals   = cpi.tolist()

    # ── Leading: Yield Curve (10Y-2Y) ────────────────────────────────────
    # Positive = normal (growth-supportive); Negative = inverted (recession warning)
    # We use the 3-month average to smooth daily noise, then track direction.
    yc_current = None; yc_trend = "unknown"; yc_3m_avg = None; yc_signal = "neutral"
    if yc_raw is not None and len(yc_raw) >= 60:
        yc_monthly = yc_raw.resample("ME").mean().dropna().tail(12)
        if len(yc_monthly) >= 2:
            yc_current = round(float(yc_raw.iloc[-1]), 2)
            yc_3m_avg  = round(float(yc_raw.tail(63).mean()), 2)   # ~3 trading months
            yc_trend   = "steepening" if yc_monthly.iloc[-1] > yc_monthly.iloc[-3] else "flattening"
            # Signal classification
            if yc_current < -0.25:
                yc_signal = "inverted"      # recession warning (historically ≥12mo lead)
            elif yc_current < 0.25:
                yc_signal = "flat"          # transition zone
            elif yc_trend == "steepening":
                yc_signal = "steepening"    # growth-positive
            else:
                yc_signal = "normal"

    # ── Leading: ISM Manufacturing via Industrial Production ─────────────
    # FRED doesn't have ISM directly as a free series; we use Industrial
    # Production Index (INDPRO) as a close proxy — it correlates ~0.85 with ISM.
    # Expansion: >0 MoM; Contraction: <0 MoM. Threshold 50 equivalent: ~0% MoM.
    pmi_current = None; pmi_trend = "unknown"; pmi_signal = "neutral"; pmi_mom = 0.0
    if indpro is not None and len(indpro) >= 3:
        pmi_mom     = float((indpro.iloc[-1] - indpro.iloc[-3]) / indpro.iloc[-3] * 100)
        pmi_current = round(float(indpro.iloc[-1]), 2)
        pmi_trend   = "expanding" if pmi_mom > 0 else "contracting"
        pmi_signal  = ("expanding"   if pmi_mom >  0.5 else
                       "contracting" if pmi_mom < -0.5 else
                       "stalling")

    # ── Leading: Initial Jobless Claims ──────────────────────────────────
    # Rising claims → labor market deteriorating → GDP deceleration ahead
    # 4-week moving average smooths weekly noise.
    claims_current = None; claims_trend = "unknown"; claims_signal = "neutral"
    if claims is not None and len(claims) >= 8:
        claims_4wk     = float(claims.tail(4).mean())
        claims_prev    = float(claims.tail(8).head(4).mean())
        claims_current = round(claims_4wk / 1000, 1)   # display in thousands
        pct_chg        = (claims_4wk - claims_prev) / claims_prev * 100
        claims_trend   = "rising" if claims_4wk > claims_prev else "falling"
        claims_signal  = ("deteriorating" if pct_chg >  5 else
                          "improving"     if pct_chg < -5 else
                          "stable")

    # ── Leading indicator composite signal ───────────────────────────────
    # Summarise all leading signals into a single forward bias:
    # "growth_positive", "growth_negative", or "mixed"
    leading_signals = []
    if yc_signal in ("steepening", "normal"):
        leading_signals.append(1)
    elif yc_signal == "inverted":
        leading_signals.append(-1)
    else:
        leading_signals.append(0)

    if pmi_signal == "expanding":
        leading_signals.append(1)
    elif pmi_signal == "contracting":
        leading_signals.append(-1)
    else:
        leading_signals.append(0)

    if claims_signal == "improving":
        leading_signals.append(1)
    elif claims_signal == "deteriorating":
        leading_signals.append(-1)
    else:
        leading_signals.append(0)

    composite = sum(leading_signals)
    leading_bias = ("growth_positive" if composite >= 2  else
                    "growth_negative" if composite <= -2 else
                    "mixed")

    return {
        # Coincident
        "gdp_trend":   gdp_trend,
        "cpi_trend":   cpi_trend,
        "gdp_vals":    gdp_vals,
        "cpi_vals":    cpi_vals,
        "gdp_mom":     gdp_mom,
        "cpi_mom":     cpi_mom,
        "gdp_streak":  gdp_streak,
        "cpi_streak":  cpi_streak,
        # Leading
        "yc_current":  yc_current,
        "yc_3m_avg":   yc_3m_avg,
        "yc_trend":    yc_trend,
        "yc_signal":   yc_signal,
        "pmi_current": pmi_current,
        "pmi_mom":     round(pmi_mom, 2),
        "pmi_trend":   pmi_trend,
        "pmi_signal":  pmi_signal,
        "claims_current": claims_current,
        "claims_trend":   claims_trend,
        "claims_signal":  claims_signal,
        "leading_bias":   leading_bias,
        "leading_scores": leading_signals,
    }


@st.cache_data(ttl=3600)
def fetch_sector_pe(tickers: tuple) -> tuple:
    """
    Fetch forward P/E for each sector ETF via yfinance .info.
    Falls back to historically-calibrated estimates when data is unavailable
    (e.g. in network-restricted environments or when yfinance returns null).

    Returns (results_dict, spy_fwd_pe):
        results_dict[ticker] = {
            "fwd_pe":    float | None,   # forward 12-month P/E
            "rel_pe":    float | None,   # fwd_pe / SPY_fwd_pe (>1 = premium)
            "source":    "live" | "estimate" | "unavailable",
            "valuation": "expensive" | "fair" | "cheap" | "unknown",
            "spy_pe":    float,
        }
    """
    # Historically-calibrated sector forward P/E estimates (2024-2025 baseline)
    PE_ESTIMATES: dict = {
        "XLK":  29.5, "XLC":  20.8, "XLY":  24.1,
        "XLF":  15.2, "XLI":  21.3, "XLV":  18.4,
        "XLB":  19.6, "XLRE": 36.2, "XLE":  12.8,
        "XLP":  20.1, "XLU":  17.9,
    }
    SPY_PE_ESTIMATE = 21.5

    spy_fwd_pe = SPY_PE_ESTIMATE
    live_pes   = {}

    # Attempt live fetch — works on Streamlit Cloud, blocked in sandbox
    try:
        spy_info    = yf.Ticker("SPY").info
        spy_live_pe = spy_info.get("forwardPE") or spy_info.get("trailingPE")
        if spy_live_pe and 10 < float(spy_live_pe) < 60:
            spy_fwd_pe = float(spy_live_pe)
    except Exception:
        pass

    for ticker in tickers:
        try:
            info   = yf.Ticker(ticker).info
            fwd_pe = info.get("forwardPE")
            if fwd_pe and 5 < float(fwd_pe) < 100:
                live_pes[ticker] = float(fwd_pe)
        except Exception:
            pass

    results = {}
    for ticker in tickers:
        if ticker in live_pes:
            fwd_pe = live_pes[ticker]
            source = "live"
        elif ticker in PE_ESTIMATES:
            fwd_pe = PE_ESTIMATES[ticker]
            source = "estimate"
        else:
            results[ticker] = {
                "fwd_pe": None, "rel_pe": None,
                "source": "unavailable", "valuation": "unknown",
                "spy_pe": round(spy_fwd_pe, 1),
            }
            continue

        rel_pe = round(fwd_pe / spy_fwd_pe, 2)
        valuation = (
            "expensive" if rel_pe > 1.25 else
            "cheap"     if rel_pe < 0.80 else
            "fair"
        )
        results[ticker] = {
            "fwd_pe":   round(fwd_pe, 1),
            "rel_pe":   rel_pe,
            "source":   source,
            "valuation": valuation,
            "spy_pe":   round(spy_fwd_pe, 1),
        }

    return results, round(spy_fwd_pe, 1)


# ── Technical sentiment proxy — replaces unreliable external APIs ─────────────
# GDELT and all RSS sources return 403 from cloud/datacenter IPs (Streamlit Cloud
# runs on GCP which is blocked by all major news APIs). Instead we derive sentiment
# from price action already in memory — no network calls, always available.
#
# Signals used (each normalized 0→1, then blended):
#   RSI-14        : >60 bullish, <40 bearish
#   Price vs SMA20: above = bullish, magnitude scaled
#   Volume trend  : 5d avg vol vs 20d avg vol (rising volume confirms moves)

def compute_technical_sentiment(prices: pd.DataFrame, volumes: pd.DataFrame) -> dict:
    """
    Derive a sentiment score for each ticker purely from price + volume data.
    Returns same schema as the old fetch_gdelt_sentiment for drop-in compatibility.
    """
    results = {}

    for ticker in prices.columns:
        try:
            px  = prices[ticker].dropna()
            vol = volumes[ticker].dropna() if ticker in volumes.columns else pd.Series(dtype=float)

            if len(px) < 21:
                raise ValueError("insufficient history")

            # ── RSI-14 ────────────────────────────────────────────────────
            delta  = px.diff()
            gain   = delta.clip(lower=0).rolling(14).mean()
            loss   = (-delta.clip(upper=0)).rolling(14).mean()
            rs     = gain / loss.replace(0, np.nan)
            rsi    = (100 - 100 / (1 + rs)).iloc[-1]
            rsi_score = (float(rsi) - 50) / 50          # -1…+1, 0 = neutral

            # ── Price vs 20d SMA ──────────────────────────────────────────
            sma20     = px.tail(20).mean()
            sma_score = float((px.iloc[-1] - sma20) / sma20) * 10
            sma_score = max(-1.0, min(1.0, sma_score))

            # ── Volume trend (5d vs 20d avg) ──────────────────────────────
            vol_ratio = 1.0  # default — avoids reference-before-assignment
            if len(vol) >= 20:
                vol_5d    = vol.tail(5).mean()
                vol_20d   = vol.tail(20).mean()
                vol_ratio = float(vol_5d / vol_20d) if vol_20d > 0 else 1.0
                vol_mod   = (vol_ratio - 1.0) * np.sign(sma_score)
                vol_score = max(-1.0, min(1.0, vol_mod))
            else:
                vol_score = 0.0

            # ── Blend: RSI 40%, SMA 40%, Volume 20% ──────────────────────
            blended = 0.40 * rsi_score + 0.40 * sma_score + 0.20 * vol_score
            blended = round(max(-1.0, min(1.0, blended)), 3)

            # Convert to GDELT-compatible score (scale ×8 to match old range)
            raw_score = round(blended * 8.0, 2)

            results[ticker] = {
                "score":      raw_score,
                "norm":       blended,
                "count":      int(len(px)),          # reused as "data points"
                "tone_label": "Bullish"  if blended >  0.10
                         else "Bearish"  if blended < -0.10
                         else "Neutral",
                "headlines":  [],                    # no headlines from price data
                "source":     "technical",
                "error":      None,
                # Extra fields exposed in UI
                "rsi":        round(float(rsi), 1),
                "sma_pct":    round(float((px.iloc[-1] - sma20) / sma20 * 100), 2),
                "vol_ratio":  round(vol_ratio if len(vol) >= 20 else 1.0, 2),
            }

        except Exception as exc:
            results[ticker] = {
                "score": 0.0, "norm": 0.0, "count": 0,
                "tone_label": "N/A", "headlines": [],
                "source": "unavailable", "error": str(exc),
                "rsi": None, "sma_pct": None, "vol_ratio": None,
            }

    return results


@st.cache_data(ttl=3600)
def fetch_historical_prices(tickers: tuple, start_year: int) -> pd.DataFrame:
    """Fetch long-period close prices for historical simulation."""
    try:
        start = f"{start_year}-01-01"
        data  = yf.download(list(tickers), start=start, auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            df = data["Close"]
        else:
            df = data[["Close"]].rename(columns={"Close": list(tickers)[0]})
        return df.ffill().dropna(how="all")
    except Exception:
        return pd.DataFrame()


def run_portfolio_simulation(
    prices:         pd.DataFrame,
    weights:        dict,           # {ticker: weight}, must sum to 1.0
    start_date:     pd.Timestamp,
    end_date:       pd.Timestamp,
    rebal_freq:     str = "QE",     # pandas offset: QE=quarterly, YE=annual
    initial_value:  float = 100.0,
) -> pd.DataFrame:
    """
    Simulate a static-weight portfolio with periodic rebalancing.

    Returns a DataFrame with columns:
        date, portfolio_value, daily_return, drawdown
    """
    px = prices.loc[start_date:end_date, list(weights.keys())].copy()
    px = px.dropna(how="all").ffill()

    if px.empty or len(px) < 2:
        return pd.DataFrame()

    # Keep only tickers with full coverage
    available = {t: w for t, w in weights.items() if t in px.columns and not px[t].isna().all()}
    if not available:
        return pd.DataFrame()

    # Renormalise weights for available tickers
    total_w = sum(available.values())
    w_norm  = {t: w / total_w for t, w in available.items()}

    # Rebalance dates — quarterly or annual
    rebal_dates = set(
        pd.date_range(start=px.index[0], end=px.index[-1], freq=rebal_freq).map(
            lambda d: px.index[px.index.searchsorted(d, side="left")]
            if px.index.searchsorted(d, side="left") < len(px.index) else px.index[-1]
        )
    )
    rebal_dates.add(px.index[0])

    # Run simulation
    portfolio_value = initial_value
    shares = {t: (portfolio_value * w_norm[t]) / float(px[t].iloc[0])
              for t in w_norm}
    records = []

    prev_val = portfolio_value
    for i, date in enumerate(px.index):
        # Current portfolio value
        pv = sum(shares[t] * float(px.loc[date, t]) for t in shares if t in px.columns)

        # Rebalance
        if date in rebal_dates and i > 0:
            for t in w_norm:
                if t in px.columns:
                    shares[t] = (pv * w_norm[t]) / float(px.loc[date, t])

        daily_ret = (pv - prev_val) / prev_val if prev_val > 0 else 0.0
        records.append({"date": date, "portfolio_value": pv, "daily_return": daily_ret})
        prev_val = pv

    df = pd.DataFrame(records).set_index("date")

    # Drawdown
    rolling_max = df["portfolio_value"].cummax()
    df["drawdown"] = (df["portfolio_value"] - rolling_max) / rolling_max * 100

    return df


def compute_sim_stats(sim: pd.DataFrame, label: str) -> dict:
    """Compute annualised performance statistics from a simulation DataFrame."""
    if sim.empty:
        return {"label": label, "cagr": None, "vol": None,
                "sharpe": None, "max_dd": None, "calmar": None}

    n_years = len(sim) / 252
    total_r = sim["portfolio_value"].iloc[-1] / sim["portfolio_value"].iloc[0] - 1
    cagr    = (1 + total_r) ** (1 / n_years) - 1 if n_years > 0 else 0
    vol     = sim["daily_return"].std() * np.sqrt(252)
    rf      = 0.04   # approximate risk-free rate
    sharpe  = (cagr - rf) / vol if vol > 0 else 0
    max_dd  = sim["drawdown"].min()
    calmar  = cagr / abs(max_dd / 100) if max_dd < 0 else 0

    return {
        "label":  label,
        "cagr":   round(cagr  * 100, 2),
        "vol":    round(vol   * 100, 2),
        "sharpe": round(sharpe, 2),
        "max_dd": round(max_dd, 2),
        "calmar": round(calmar, 2),
        "start_val": round(sim["portfolio_value"].iloc[0],  2),
        "end_val":   round(sim["portfolio_value"].iloc[-1], 2),
    }


def compute_volatility_weights(prices: pd.DataFrame) -> pd.Series:
    log_ret = np.log(prices / prices.shift(1)).dropna()
    vols    = log_ret.tail(30).std() * np.sqrt(252)
    vols    = vols.replace(0, np.nan).dropna()
    inv_vol = 1 / vols
    return inv_vol / inv_vol.sum()

def compute_atr(ticker: str, highs: pd.DataFrame, lows: pd.DataFrame,
                closes: pd.DataFrame, window: int = 14) -> float:
    """Compute ATR from already-fetched OHLCV data — no extra network call."""
    try:
        if ticker not in highs.columns:
            return 0.0
        hi = highs[ticker].dropna()
        lo = lows[ticker].dropna()
        cl = closes[ticker].dropna()
        if len(hi) < window + 1:
            return 0.0
        tr = pd.concat([
            hi - lo,
            (hi - cl.shift()).abs(),
            (lo - cl.shift()).abs(),
        ], axis=1).max(axis=1)
        val = tr.rolling(window).mean().iloc[-1]
        return float(val) if pd.notna(val) else 0.0
    except Exception:
        return 0.0

def sma(prices: pd.Series, window: int) -> float:
    return prices.tail(window).mean() if len(prices) >= window else prices.mean()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("### ⚙ Parameters")

    total_inv = st.number_input(
        "Total Investment ($)",
        min_value=1000, max_value=10_000_000,
        value=_total_inv_default,
        step=1000, format="%d"
    )
    st.markdown("---")
    st.markdown("##### 🎯 Glide Path — Life Stage")

    glide_keys   = list(GLIDE_PRESETS.keys())
    glide_index  = min(_glide_index_default, len(glide_keys) - 1)
    glide_choice = st.selectbox(
        "Select your age bracket",
        options=glide_keys,
        index=glide_index,
        help="Core asset composition shifts with your time horizon."
    )
    glide_cfg   = GLIDE_PRESETS[glide_choice]
    CORE_ASSETS = glide_cfg["assets"]

    st.markdown(f"""
    <div style="background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);
                border-radius:5px;padding:10px 12px;font-size:0.75rem;color:var(--muted);
                margin-top:4px">
      {glide_cfg['description']}
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("##### Bucket Weights")

    core_pct     = st.slider("Core Equity %",        40, 80,
                              max(40, min(80, _core_pct_default     - _core_pct_default     % 5)), 5)
    tactical_pct = st.slider("Tactical Pure Alpha %", 10, 40,
                              max(10, min(40, _tactical_pct_default - _tactical_pct_default % 5)), 5)
    hedge_pct    = max(0, 100 - core_pct - tactical_pct)
    _over = core_pct + tactical_pct > 100
    if _over:
        st.warning(f"⚠ Core + Tactical = {core_pct + tactical_pct}% (over 100%). Hedge set to 0%.", icon="⚠")
    else:
        st.markdown(f"Hedge (auto) **{hedge_pct}%**")
    st.markdown("---")

    # ── Save settings to query_params ────────────────────────────────────────
    save_btn = st.button("💾  SAVE SETTINGS", use_container_width=True)
    run_btn  = st.button("🔄  REFRESH DATA",  use_container_width=True)

    if save_btn:
        new_glide_index = glide_keys.index(glide_choice)
        # Write to query params (Streamlit side)
        st.query_params["total_inv"]    = str(total_inv)
        st.query_params["glide_index"]  = str(new_glide_index)
        st.query_params["core_pct"]     = str(core_pct)
        st.query_params["tactical_pct"] = str(tactical_pct)
        # Settings saved to query_params above
        st.success("✓ Settings saved — will persist on next visit.", icon="💾")

    # Show last-saved indicator
    st.markdown(f"""
    <div style="font-family:var(--mono);font-size:0.62rem;color:var(--muted);
                margin-top:8px;text-align:center">
      Loaded from: {'💾 saved prefs' if any(
          st.query_params.get(k) for k in PARAM_DEFAULTS
      ) else '⚙ defaults'}
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

# Skip-to-content link (508 requirement)
st.markdown(
    '<a href="#main-content" class="skip-link">Skip to main content</a>',
    unsafe_allow_html=True,
)

st.markdown(f"""
<header class="aw-header" role="banner">
  <span aria-hidden="true" style="font-size:1.6rem">🌦</span>
  <div>
    <h1 id="main-content">PROJECT ALL-WEATHER</h1>
    <div style="margin-top:3px;display:flex;gap:6px;flex-wrap:wrap" role="list"
         aria-label="Portfolio bucket types">
      <span class="aw-badge" role="listitem">EQUITY CORE</span>
      <span class="aw-badge" style="background:#10b981" role="listitem">PURE ALPHA</span>
      <span class="aw-badge" style="background:#f59e0b" role="listitem">TAIL HEDGE</span>
      <span class="aw-badge" style="background:#8b5cf6" role="listitem"
            aria-label="Current life stage: {glide_choice.split('·')[0].strip()}"
      >{glide_choice.split('·')[0].strip()}</span>
    </div>
  </div>
  <div style="margin-left:auto;text-align:right;font-family:var(--mono);
              font-size:0.68rem;color:var(--muted)" aria-label="Last data refresh time">
    Last refresh<br>
    <b style="color:var(--text)">{datetime.now().strftime('%Y-%m-%d %H:%M')}</b>
  </div>
</header>
""", unsafe_allow_html=True)



# ══════════════════════════════════════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════════════════════════════════════

with st.spinner("Fetching market data…"):
    # Always fetch all possible core tickers across all glide path stages
    ALL_POSSIBLE_CORE = ["VOO", "VEA", "VWO", "GLD", "TLT", "IEF", "GSG"]
    all_tickers = ALL_POSSIBLE_CORE + list(SECTOR_ETFS.keys()) + list(HEDGE_ASSETS.keys())
    all_tickers = list(dict.fromkeys(all_tickers))

    try:
        _close, _volume, _high, _low = fetch_ohlcv(tuple(all_tickers), period="1y")
        available    = [t for t in all_tickers if t in _close.columns]
        prices_all   = _close[available]
        highs_all    = _high[[t for t in available if t in _high.columns]]
        lows_all     = _low[[t for t in available if t in _low.columns]]
        volumes_all  = _volume[[t for t in available if t in _volume.columns]]
        data_ok      = True
    except Exception as e:
        st.error(f"Data fetch failed: {e}")
        data_ok = False

    # Volume for sector ETFs is already in volumes_all from the unified fetch above
    sector_tickers_list = list(SECTOR_ETFS.keys())

    # Put/Call ratios — separate call since options chains aren't in OHLCV
    pcr_data = fetch_options_pcr(tuple(sector_tickers_list))

    # Forward P/E for all sector ETFs
    pe_data, spy_pe = fetch_sector_pe(tuple(sector_tickers_list))

    _macro     = fetch_fred_macro()
    gdp_trend  = _macro["gdp_trend"];  cpi_trend  = _macro["cpi_trend"]
    gdp_vals   = _macro["gdp_vals"];   cpi_vals   = _macro["cpi_vals"]
    gdp_mom    = _macro["gdp_mom"];    cpi_mom    = _macro["cpi_mom"]
    gdp_streak = _macro["gdp_streak"]; cpi_streak = _macro["cpi_streak"]

if not data_ok:
    st.stop()

# Technical sentiment — computed from price + volume already in memory
sector_prices_for_sent = prices_all[[t for t in SECTOR_ETFS if t in prices_all.columns]]
sentiment_data = compute_technical_sentiment(sector_prices_for_sent, volumes_all)

# Read manual sector override early so ATR computation can cover those tickers
_saved_raw    = st.query_params.get("manual_sectors", "")
_all_sectors  = list(SECTOR_ETFS.keys())
early_manual_sectors = [s for s in _saved_raw.split(",") if s in _all_sectors] \
                       if _saved_raw else []

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — CORE EQUITY (Age-Adjusted Risk Parity)
# ══════════════════════════════════════════════════════════════════════════════

core_prices   = prices_all[[t for t in CORE_ASSETS if t in prices_all.columns]]
core_weights  = compute_volatility_weights(core_prices)
core_bucket   = core_pct / 100

# Human-readable core asset labels
CORE_LABELS = {
    "VOO": "US Equities (VOO)",
    "VEA": "Intl Developed (VEA)",
    "VWO": "Emerging Markets (VWO)",
    "GLD": "Gold (GLD)",
    "TLT": "Long-Term Bonds (TLT)",
    "IEF": "Mid-Term Bonds (IEF)",
    "GSG": "Commodities (GSG)",
}

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — TACTICAL PURE ALPHA
# ══════════════════════════════════════════════════════════════════════════════

quad_key  = (gdp_trend, cpi_trend)
quad_name, quad_emoji, quad_preferred = QUADRANT_MAP.get(quad_key, ("Unknown","❓",[]))

# Opposite regime: flip both GDP and CPI trends
_flip = {"rising": "falling", "falling": "rising"}
anti_quad_key  = (_flip[gdp_trend], _flip[cpi_trend])
anti_quad_name, anti_quad_emoji, anti_preferred = QUADRANT_MAP.get(anti_quad_key, ("Unknown","❓",[]))

sector_prices = prices_all[[t for t in SECTOR_ETFS if t in prices_all.columns]]
three_mo_ago  = sector_prices.index[-1] - timedelta(days=90)
start_prices  = sector_prices[sector_prices.index >= three_mo_ago].iloc[0]
end_prices    = sector_prices.iloc[-1]
sector_returns = ((end_prices - start_prices) / start_prices).sort_values(ascending=False)

# ── Valuation-adjusted momentum score ────────────────────────────────────────
# Pure momentum can chase overvalued sectors. We apply a modest P/E adjustment:
#   cheap  (rel P/E < 0.80): +2% bonus to return score
#   fair   (rel P/E 0.80–1.25): no adjustment
#   expensive (rel P/E > 1.25): -3% penalty to return score
#
# The asymmetry (penalty > bonus) reflects that overvaluation is a clearer
# headwind than undervaluation is a tailwind in short rotation cycles.

def pe_adj_return(ticker: str, raw_return: float) -> float:
    pe = pe_data.get(ticker, {})
    valuation = pe.get("valuation", "fair")
    if valuation == "cheap":
        return raw_return + 0.02
    elif valuation == "expensive":
        return raw_return - 0.03
    return raw_return

sector_returns_adj = pd.Series(
    {t: pe_adj_return(t, float(sector_returns[t])) for t in sector_returns.index},
    name="adj_return"
).sort_values(ascending=False)

# Prefer quadrant-aligned; fill remainder with valuation-adjusted momentum leaders
preferred_available = [t for t in quad_preferred if t in sector_returns_adj.index]
top_momentum        = [t for t in sector_returns_adj.index if t not in preferred_available]
top3 = (preferred_available + top_momentum)[:3]

tactical_alloc_pct  = tactical_pct / 100
tactical_per_sector = tactical_alloc_pct / 3

# ══════════════════════════════════════════════════════════════════════════════
# REGIME CONFIDENCE ENGINE
# Blends 4 independent signals into a 0–100 confidence score.
#
# Signal 1 — Macro momentum magnitude (25%)
#   How strongly is GDP/CPI moving, not just direction.
#   Normalised against typical quarterly ranges.
#
# Signal 2 — Streak / trend age (25%)
#   Consecutive periods the regime has been in place.
#   Long streaks = established; very long = possibly mature/transitioning.
#
# Signal 3 — Sector confirmation rate (30%)
#   What % of the regime's preferred sectors are outperforming SPY 3M.
#   High agreement between price action and macro label = high confidence.
#
# Signal 4 — Equity-bond decorrelation (20%)
#   Risk parity works when equities and bonds are uncorrelated or negatively
#   correlated. Positive correlation = regime instability / stress.
# ══════════════════════════════════════════════════════════════════════════════

def compute_transition_probability(
    gdp_trend:      str,
    cpi_trend:      str,
    gdp_mom:        float,
    cpi_mom:        float,
    gdp_streak:     int,
    cpi_streak:     int,
    yc_signal:      str,
    pmi_signal:     str,
    claims_signal:  str,
    leading_scores: list,
    prices_all:     pd.DataFrame,
) -> dict:
    """
    Estimate the probability that the current macro regime will transition
    within the next 2–3 quarters, and which quadrant it is most likely to
    transition into.

    This is fundamentally different from the confidence gauge:
      Confidence  = how well confirmed is the CURRENT regime?
      Transition  = how likely is the current regime to CHANGE?

    A regime can be high-confidence (clearly Expansion) but high-transition
    (every leading indicator pointing toward Stagflation).

    Signals used:
      1. Leading indicator divergence from current regime (40%)
         How many leading indicators disagree with the current GDP/CPI trend?
      2. Rate of change of yield curve (20%)
         A rapidly flattening/inverting curve is a stronger transition signal
         than one that has been flat for a year.
      3. Streak age vs empirical regime durations (20%)
         Long streaks are statistically more likely to end.
         US regime durations (post-WWII): Expansion ~14q, Recession ~3q,
         Stagflation ~4q, Deflation ~2q.
      4. Axis pressure (20%)
         GDP and CPI momentum direction — are they decelerating even if
         still positive? Cross-axis pressure signals impending flip.

    Returns
    -------
    dict with:
        prob_transition : float 0–100  overall transition probability
        label           : str          LOW | MODERATE | ELEVATED | HIGH
        color           : str          hex
        target_probs    : dict         {quadrant: prob 0–100}  sums to ~100
        top_target      : str          most likely destination quadrant
        signals         : list of (name, score, detail) tuples
        rationale       : str          plain-English explanation
    """
    # ── Historical median regime streak lengths (quarters) ────────────────
    MEDIAN_DURATION = {
        ("rising", "falling"): 14,   # Expansion
        ("rising", "rising"):   4,   # Stagflation
        ("falling","rising"):   3,   # Recession
        ("falling","falling"):  2,   # Deflation
    }
    median_dur = MEDIAN_DURATION.get((gdp_trend, cpi_trend), 6)
    min_streak = min(gdp_streak, cpi_streak)

    # ── Signal 1: Leading indicator divergence ─────────────────────────────
    # Each leading indicator gets compared to what the current regime predicts.
    # Expansion predicts: yc positive, pmi expanding, claims improving
    # Recession predicts: yc inverted, pmi contracting, claims deteriorating
    # Stagflation predicts: yc flat/inverted, pmi mixed, claims worsening
    # Deflation predicts: yc positive (flight to bonds), pmi contracting

    expected_by_regime = {
        ("rising", "falling"):  {"yc": 1,  "pmi": 1,  "claims": 1},   # Expansion
        ("rising", "rising"):   {"yc": -1, "pmi": 0,  "claims": -1},  # Stagflation
        ("falling","rising"):   {"yc": -1, "pmi": -1, "claims": -1},  # Recession
        ("falling","falling"):  {"yc": 1,  "pmi": -1, "claims": 0},   # Deflation
    }
    expected = expected_by_regime.get((gdp_trend, cpi_trend),
                                       {"yc": 0, "pmi": 0, "claims": 0})

    actual = {
        "yc":     leading_scores[0] if len(leading_scores) > 0 else 0,
        "pmi":    leading_scores[1] if len(leading_scores) > 1 else 0,
        "claims": leading_scores[2] if len(leading_scores) > 2 else 0,
    }

    divergence_scores = []
    for key in ["yc", "pmi", "claims"]:
        exp = expected[key]
        act = actual[key]
        if exp == 0:
            # Regime has no strong expectation — any signal is mild pressure
            divergence_scores.append(abs(act) * 0.5)
        elif act == -exp:
            # Direct contradiction — strong transition signal
            divergence_scores.append(1.0)
        elif act == exp:
            # Confirms current regime
            divergence_scores.append(0.0)
        else:
            # Mixed / neutral
            divergence_scores.append(0.35)

    divergence_sig = sum(divergence_scores) / 3.0   # 0–1

    # ── Signal 2: Yield curve rate of change ──────────────────────────────
    # We approximate this from the yc_signal: inverted > flat > normal
    # A rapidly inverting curve (went from normal → inverted recently) is
    # stronger than a curve that's been inverted for years.
    yc_roc_sig = {
        "inverted":   0.85,   # strongest recession/stagflation signal
        "flat":       0.55,   # transition zone — watch closely
        "steepening": 0.15,   # growth-positive, low transition risk
        "normal":     0.10,   # stable growth, very low transition risk
        "unknown":    0.40,   # no data — moderate default
    }.get(yc_signal, 0.40)

    # ── Signal 3: Streak age vs empirical duration ─────────────────────────
    # Use a sigmoid-like function: low early, accelerating past median
    if min_streak == 0:
        streak_sig = 0.0
    elif min_streak < median_dur * 0.5:
        streak_sig = 0.1                              # young regime, very stable
    elif min_streak < median_dur:
        streak_sig = 0.3 + 0.3 * (min_streak / median_dur)  # approaching median
    elif min_streak < median_dur * 1.5:
        streak_sig = 0.65                             # past median, elevated
    else:
        streak_sig = min(0.90, 0.65 + (min_streak - median_dur * 1.5) * 0.05)

    # ── Signal 4: Axis momentum pressure ──────────────────────────────────
    # Are GDP and CPI decelerating even if still in the same direction?
    # gdp_mom > 0 but small → GDP barely growing → risk of flip
    gdp_pressure = max(0.0, min(1.0, 1.0 - abs(gdp_mom) / 1.5))
    cpi_pressure = max(0.0, min(1.0, 1.0 - abs(cpi_mom) / 1.0))
    axis_sig     = (gdp_pressure + cpi_pressure) / 2.0

    # ── Blend ─────────────────────────────────────────────────────────────
    prob_raw = (
        0.40 * divergence_sig +
        0.20 * yc_roc_sig     +
        0.20 * streak_sig     +
        0.20 * axis_sig
    )
    prob_transition = round(prob_raw * 100)

    if prob_transition >= 65:
        t_label, t_color = "HIGH",     "#ef4444"
    elif prob_transition >= 45:
        t_label, t_color = "ELEVATED", "#f59e0b"
    elif prob_transition >= 25:
        t_label, t_color = "MODERATE", "#3b82f6"
    else:
        t_label, t_color = "LOW",      "#10b981"

    # ── Target quadrant probabilities ─────────────────────────────────────
    # Which regime is it most likely transitioning INTO?
    # Each possible destination gets a base weight from:
    #   a) How much do leading indicators point toward it?
    #   b) Is it adjacent to the current regime? (single-axis flips are more likely)

    all_quads = [
        ("rising",  "falling"),   # Expansion
        ("rising",  "rising"),    # Stagflation
        ("falling", "rising"),    # Recession
        ("falling", "falling"),   # Deflation
    ]
    quad_names = {
        ("rising",  "falling"): "🚀 Expansion",
        ("rising",  "rising"):  "🔥 Stagflation",
        ("falling", "rising"):  "❄️ Recession",
        ("falling", "falling"): "🌧 Deflation",
    }

    raw_weights: dict = {}
    for q in all_quads:
        if q == (gdp_trend, cpi_trend):
            raw_weights[q] = 0.0   # can't "transition" to current
            continue

        w = 0.0
        q_gdp, q_cpi = q

        # Adjacency: single-axis flip is ~3× more likely than diagonal
        gdp_flip = q_gdp != gdp_trend
        cpi_flip = q_cpi != cpi_trend
        if gdp_flip and cpi_flip:
            w += 0.5    # diagonal — rare but possible
        else:
            w += 1.5    # single-axis flip — much more common

        # GDP axis signal
        if gdp_flip:
            # Does leading data support a GDP flip?
            if q_gdp == "falling" and actual["pmi"] <= 0 and actual["claims"] <= 0:
                w += 1.5
            elif q_gdp == "rising" and actual["pmi"] >= 0 and actual["claims"] >= 0:
                w += 1.5
            else:
                w += 0.3

        # CPI axis signal
        if cpi_flip:
            # Yield curve and claims inform inflation direction
            if q_cpi == "rising" and yc_signal in ("flat", "inverted"):
                w += 0.8   # rising inflation often accompanies tightening
            elif q_cpi == "falling" and yc_signal in ("steepening", "normal"):
                w += 0.8
            else:
                w += 0.3

        raw_weights[q] = max(0.0, w)

    total_w = sum(raw_weights.values()) or 1.0
    target_probs = {
        quad_names[q]: round(raw_weights[q] / total_w * 100)
        for q in all_quads if q != (gdp_trend, cpi_trend)
    }
    # Normalize to sum to (100 - "stay" probability)
    stay_prob    = max(0, 100 - prob_transition)
    target_total = sum(target_probs.values()) or 1
    target_probs = {k: round(v / target_total * prob_transition)
                    for k, v in target_probs.items()}

    top_target = max(target_probs, key=target_probs.get) if target_probs else "Unknown"

    # ── Rationale ─────────────────────────────────────────────────────────
    if prob_transition >= 65:
        rationale = (f"Multiple leading indicators contradict the current "
                     f"{quad_names[(gdp_trend, cpi_trend)].split()[1]} regime. "
                     f"A transition toward {top_target} appears likely "
                     f"within 2–3 quarters.")
    elif prob_transition >= 45:
        rationale = (f"Leading indicators show elevated divergence from the "
                     f"current regime. Watch for confirmation in next GDP/CPI prints. "
                     f"{top_target} is the most probable destination.")
    elif prob_transition >= 25:
        rationale = (f"Some leading indicator pressure present but current regime "
                     f"signals remain dominant. No immediate action required.")
    else:
        rationale = (f"Leading indicators broadly confirm current regime trajectory. "
                     f"Transition risk is low for the next 2–3 quarters.")

    return {
        "prob_transition": prob_transition,
        "label":           t_label,
        "color":           t_color,
        "target_probs":    target_probs,
        "top_target":      top_target,
        "stay_prob":       stay_prob,
        "signals": [
            ("Lead Divergence", round(divergence_sig * 100),
             f"{sum(1 for s in divergence_scores if s > 0.5)}/3 indicators contradict current regime"),
            ("Yield Curve",     round(yc_roc_sig * 100),
             f"Signal: {yc_signal}"),
            ("Streak Age",      round(streak_sig * 100),
             f"{min_streak} periods vs median {median_dur}q for this regime"),
            ("Axis Pressure",   round(axis_sig * 100),
             f"GDP mom {gdp_mom:+.2f}% · CPI mom {cpi_mom:+.2f}%"),
        ],
        "rationale": rationale,
    }


def compute_regime_confidence(
    gdp_mom: float, cpi_mom: float,
    gdp_streak: int, cpi_streak: int,
    quad_preferred: list, sector_returns: pd.Series,
    prices_all: pd.DataFrame,
    leading_bias: str = "mixed",
    leading_scores: list = None,
) -> dict:
    """
    Blend 5 independent signals into a 0–100 regime confidence score.

    Signal weights:
        20% Macro Momentum    — magnitude of GDP/CPI moves
        20% Trend Streak      — consecutive periods in current regime
        25% Sector Confirmation — % preferred sectors beating SPY
        15% EQ/Bond Decorr    — risk parity stability (low corr = healthy)
        20% Leading Indicators — yield curve + PMI + jobless claims composite
    """
    if leading_scores is None:
        leading_scores = [0, 0, 0]

    # ── Signal 1: Macro momentum magnitude ───────────────────────────────
    gdp_mag   = min(abs(gdp_mom) / 2.0, 1.0)
    cpi_mag   = min(abs(cpi_mom) / 1.5, 1.0)
    macro_sig = (gdp_mag + cpi_mag) / 2.0

    # ── Signal 2: Streak / trend age ─────────────────────────────────────
    min_streak = min(gdp_streak, cpi_streak)
    if min_streak <= 1:
        streak_sig = 0.25
    elif min_streak <= 3:
        streak_sig = 0.60
    elif min_streak <= 6:
        streak_sig = 0.85
    else:
        streak_sig = max(0.60, 0.85 - (min_streak - 6) * 0.05)

    # ── Signal 3: Sector price confirmation ──────────────────────────────
    spy_3m = 0.0
    if "VOO" in sector_returns.index:
        spy_3m = float(sector_returns["VOO"])
    elif "SPY" in sector_returns.index:
        spy_3m = float(sector_returns["SPY"])

    if quad_preferred:
        beats      = sum(1 for t in quad_preferred
                         if t in sector_returns.index
                         and float(sector_returns[t]) > spy_3m)
        sector_sig = beats / len(quad_preferred)
    else:
        sector_sig = 0.5

    # ── Signal 4: Equity-bond decorrelation ──────────────────────────────
    decorr_sig = 0.5
    corr_used  = 0.0
    if "VOO" in prices_all.columns and "TLT" in prices_all.columns:
        eq_ret   = prices_all["VOO"].pct_change().dropna().tail(60)
        bond_ret = prices_all["TLT"].pct_change().dropna().tail(60)
        combined = pd.concat([eq_ret, bond_ret], axis=1).dropna()
        if len(combined) >= 20:
            corr      = float(combined.iloc[:, 0].corr(combined.iloc[:, 1]))
            decorr_sig = max(0.0, min(1.0, (1.0 - corr) / 2.0))
            corr_used  = round(corr, 3)

    # ── Signal 5: Leading indicators composite ───────────────────────────
    # +1 per bullish signal, -1 per bearish, 0 = neutral; range -3 to +3
    # Map to 0–1: (-3 → 0.0, 0 → 0.5, +3 → 1.0)
    composite_raw = sum(leading_scores)
    leading_sig   = max(0.0, min(1.0, (composite_raw + 3) / 6.0))
    # When leading bias conflicts with current regime (e.g. regime=Expansion
    # but leading indicators are all negative), penalise confidence harder.
    if leading_bias == "growth_negative" and "Expansion" in str(quad_preferred):
        leading_sig = max(0.0, leading_sig - 0.2)
    elif leading_bias == "growth_positive" and "Recession" in str(quad_preferred):
        leading_sig = max(0.0, leading_sig - 0.2)

    # ── Blend ─────────────────────────────────────────────────────────────
    score = (
        0.20 * macro_sig   +
        0.20 * streak_sig  +
        0.25 * sector_sig  +
        0.15 * decorr_sig  +
        0.20 * leading_sig
    )
    score_pct = round(score * 100)

    # ── Stability label ───────────────────────────────────────────────────
    if score_pct >= 75:
        label, color, desc = "ESTABLISHED",   "#10b981", "Signals strongly aligned. High conviction."
    elif score_pct >= 55:
        label, color, desc = "CONFIRMED",     "#3b82f6", "Regime confirmed across most signals."
    elif score_pct >= 35:
        label, color, desc = "FORMING",       "#f59e0b", "Early signals present. Monitor for confirmation."
    else:
        label, color, desc = "TRANSITIONING", "#ef4444", "Weak or conflicting signals. Regime may be shifting."

    min_streak_label = (
        "New signal"      if min_streak <= 1 else
        f"{min_streak} periods" + (" — late cycle" if min_streak > 6 else "")
    )

    return {
        "score":          score_pct,
        "label":          label,
        "color":          color,
        "desc":           desc,
        "macro_sig":      round(macro_sig   * 100),
        "streak_sig":     round(streak_sig  * 100),
        "sector_sig":     round(sector_sig  * 100),
        "decorr_sig":     round(decorr_sig  * 100),
        "leading_sig":    round(leading_sig * 100),
        "streak_label":   min_streak_label,
        "gdp_mom":        round(gdp_mom, 3),
        "cpi_mom":        round(cpi_mom, 3),
        "corr_used":      corr_used,
        "leading_bias":   leading_bias,
    }


regime_confidence = compute_regime_confidence(
    gdp_mom, cpi_mom, gdp_streak, cpi_streak,
    quad_preferred, sector_returns, prices_all,
    leading_bias   = _macro["leading_bias"],
    leading_scores = _macro["leading_scores"],
)

transition_probability = compute_transition_probability(
    gdp_trend      = gdp_trend,
    cpi_trend      = cpi_trend,
    gdp_mom        = gdp_mom,
    cpi_mom        = cpi_mom,
    gdp_streak     = gdp_streak,
    cpi_streak     = cpi_streak,
    yc_signal      = _macro["yc_signal"],
    pmi_signal     = _macro["pmi_signal"],
    claims_signal  = _macro["claims_signal"],
    leading_scores = _macro["leading_scores"],
    prices_all     = prices_all,
)



voo_prices = prices_all["VOO"] if "VOO" in prices_all.columns else None
crisis_mode= False
hedge_ticker = "BIL"
hedge_name   = "Cash (T-Bills)"

if voo_prices is not None and len(voo_prices) >= 200:
    voo_sma200   = sma(voo_prices, 200)
    voo_current  = voo_prices.iloc[-1]
    crisis_mode  = float(voo_current) < float(voo_sma200)
    if crisis_mode:
        hedge_ticker = "SH"
        hedge_name   = "Short S&P 500 (SH)"
    voo_sma200_val = float(voo_sma200)
    voo_current_val= float(voo_current)
else:
    voo_sma200_val = voo_current_val = 0.0

hedge_bucket = hedge_pct / 100

# ══════════════════════════════════════════════════════════════════════════════
# ATR STOP-LOSSES for tactical positions
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def get_atrs(tickers: tuple, _prices: pd.DataFrame,
             _highs: pd.DataFrame, _lows: pd.DataFrame) -> dict:
    """_-prefixed args skip st.cache_data hashing (DataFrames aren't hashable)."""
    result = {}
    for t in tickers:
        px      = float(_prices[t].iloc[-1]) if t in _prices.columns else 0.0
        atr_val = compute_atr(t, _highs, _lows, _prices)
        result[t] = {"price": px, "atr": atr_val, "stop": px - 2 * atr_val}
    return result

atr_tickers = tuple(dict.fromkeys(top3 + early_manual_sectors))
atr_data = get_atrs(atr_tickers, prices_all, highs_all, lows_all)

# ── Correlation matrix — computed here so status bar can reference it ─────────
_corr_tickers = list(dict.fromkeys(CORE_ASSETS + ["VOO", "TLT", "GLD"]))
_corr_tickers = [t for t in _corr_tickers if t in prices_all.columns]
_rets_60d = np.log(prices_all[_corr_tickers] / prices_all[_corr_tickers].shift(1)).dropna().tail(60)
_rets_1y  = np.log(prices_all[_corr_tickers] / prices_all[_corr_tickers].shift(1)).dropna()
_corr_60d = _rets_60d.corr()
_corr_1y  = _rets_1y.corr()
_eq_bond_corr = float(_corr_60d.loc["VOO","TLT"]) \
                if ("VOO" in _corr_60d.index and "TLT" in _corr_60d.index) else 0.0
_rp_stressed  = _eq_bond_corr > 0.15

# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED SHARES CALCULATION
# ══════════════════════════════════════════════════════════════════════════════

def calc_shares(ticker, dollar_alloc):
    if ticker not in prices_all.columns:
        return 0, 0.0
    px = float(prices_all[ticker].iloc[-1])
    if px <= 0:
        return 0, px
    return int(dollar_alloc // px), px

# ══════════════════════════════════════════════════════════════════════════════
# REGIME SECTION — rendered inside Tab 1 below allocation cards
# ══════════════════════════════════════════════════════════════════════════════

# ── Compact status bar — rendered after all data computed ─────────────────────
_conf_score  = regime_confidence["score"]
_conf_color  = regime_confidence["color"]
_conf_label  = regime_confidence["label"]
_trans_score = transition_probability["prob_transition"]
_trans_color = transition_probability["color"]
_trans_label = transition_probability["label"]

_status_items = [
    (quad_emoji, f"{quad_name}",
     "var(--accent)", "Current macro regime"),
    ("📊", f"Confidence {_conf_score}",
     _conf_color, f"Regime confidence: {_conf_label}"),
    ("🔄", f"Transition {_trans_score}%",
     _trans_color, f"Transition risk: {_trans_label}"),
    ("🔗", f"EQ/Bond {_eq_bond_corr:+.2f}",
     "#10b981" if not _rp_stressed else "#ef4444",
     "Equity-bond correlation: " + ("healthy" if not _rp_stressed else "stressed")),
    ("🛡", "CRISIS MODE" if crisis_mode else "Normal hedge",
     "#ef4444" if crisis_mode else "#10b981",
     "Hedge status: " + ("crisis rotation active" if crisis_mode else "cash / T-bills")),
    ("📡", _macro["leading_bias"].replace("_"," ").title(),
     "#10b981" if _macro["leading_bias"] == "growth_positive"
     else "#ef4444" if _macro["leading_bias"] == "growth_negative" else "#f59e0b",
     "Leading indicator composite signal"),
]
_sb_parts = ['<nav class="aw-status-bar" role="navigation" aria-label="Portfolio status summary">']
for _icon, _lbl, _col, _aria in _status_items:
    _sb_parts.append(
        f'<div class="aw-status-item" title="{_aria}" aria-label="{_aria}">'
        f'<span aria-hidden="true">{_icon}</span>'
        f'<b style="color:{_col}">{_lbl}</b>'
        f'<span class="sr-only">({_aria})</span>'
        f'</div>'
    )
_sb_parts.append('</nav>')
st.markdown("".join(_sb_parts), unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊  ALLOCATION ENGINE",
    "📈  SECTOR MOMENTUM",
    "⚖  DRIFT REPORT",
    "🗺  GLIDE PATH",
    "🔭  LEADING INDICATORS",
    "📜  HISTORICAL VIEW",
])

# ─── TAB 1 — ALLOCATION ENGINE ───────────────────────────────────────────────
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="aw-card">', unsafe_allow_html=True)
        st.markdown('<div class="aw-card-title">🏛 Core Equity Bucket (Risk Parity Weighted)</div>', unsafe_allow_html=True)

        # Compute equity vs non-equity split for display
        equity_tickers = [t for t in CORE_ASSETS if t in ["VOO","VEA","VWO"]]
        equity_weight  = sum(core_weights.get(t, 0) for t in equity_tickers)

        st.markdown(f"""
        <div style="font-size:0.8rem;color:var(--muted);margin-bottom:16px">
          Inv-vol weighted · Life stage: <b style="color:#8b5cf6">{glide_choice.split('·')[0].strip()}</b>
          &nbsp;·&nbsp; Bucket: <b style="color:var(--accent)">{core_pct}%</b>
          &nbsp;·&nbsp; Equity share: <b style="color:#10b981">{equity_weight*100:.0f}%</b> of core
        </div>
        """, unsafe_allow_html=True)

        rows = []  # kept for potential future export feature
        for i, ticker in enumerate(CORE_ASSETS):
            if ticker not in core_weights.index:
                continue
            w    = core_weights[ticker]
            dollar= total_inv * core_bucket * w
            shares, px = calc_shares(ticker, dollar)
            vol   = (np.log(core_prices[ticker]/core_prices[ticker].shift(1))
                     .dropna().tail(30).std() * np.sqrt(252)) if ticker in core_prices.columns else 0
            color = CORE_COLORS[i % len(CORE_COLORS)]
            pct_of_total = core_bucket * w * 100
            label = CORE_LABELS.get(ticker, ticker)
            is_equity = ticker in ["VOO","VEA","VWO"]
            asset_type = "equity" if is_equity else ("bond" if ticker in ["TLT","IEF"] else "alt")
            type_color = {"equity": "#10b981", "bond": "#3b82f6", "alt": "#f59e0b"}[asset_type]
            st.markdown(f"""
            <div class="alloc-bar-container">
              <div class="alloc-bar-label">
                <span>
                  <b>{ticker}</b>
                  <span style="font-size:0.65rem;color:{type_color};margin-left:6px;
                               font-family:var(--mono);text-transform:uppercase">{asset_type}</span>
                </span>
                <span style="color:var(--muted)">{pct_of_total:.1f}% · ${dollar:,.0f} · {shares} shares</span>
              </div>
              <div class="alloc-bar-track">
                <div class="alloc-bar-fill" style="width:{w*100:.1f}%;background:{color}"></div>
              </div>
              <div style="font-size:0.65rem;color:var(--muted);margin-top:3px">
                {label} · 30d Vol: {vol*100:.1f}% · Inv-vol weight: {w*100:.1f}%
              </div>
            </div>
            """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="aw-card">', unsafe_allow_html=True)
        st.markdown('<div class="aw-card-title">⚡ Tactical Pure Alpha</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:0.8rem;color:var(--muted);margin-bottom:16px">
          Top-3 sectors · Regime-aligned · Bucket: <b style="color:#10b981">{tactical_pct}%</b>
        </div>
        """, unsafe_allow_html=True)

        for ticker in top3:
            dollar    = total_inv * tactical_per_sector
            shares, px = calc_shares(ticker, dollar)
            ret       = sector_returns[ticker] if ticker in sector_returns.index else 0.0
            ret_adj   = float(sector_returns_adj[ticker]) if ticker in sector_returns_adj.index else ret
            atr_info  = atr_data.get(ticker, {"atr": 0, "stop": 0, "price": px})
            aligned   = "✓ regime" if ticker in quad_preferred else "↑ momentum"
            ret_color = "#10b981" if ret >= 0 else "#ef4444"

            # P/E data for this ticker
            pe     = pe_data.get(ticker, {})
            fwd_pe = pe.get("fwd_pe")
            rel_pe = pe.get("rel_pe")
            val    = pe.get("valuation", "fair")
            pe_src = pe.get("source", "estimate")
            pe_color = (
                "#ef4444" if val == "expensive" else
                "#10b981" if val == "cheap"     else
                "var(--muted)"
            )
            pe_adj_delta = ret_adj - ret
            pe_badge_parts = []
            if fwd_pe is not None:
                pe_badge_parts.append(
                    f'<span style="background:rgba(255,255,255,0.05);'
                    f'border:1px solid {pe_color}44;color:{pe_color};'
                    f'font-family:var(--mono);font-size:0.62rem;padding:2px 7px;border-radius:3px">'
                    f'P/E {fwd_pe:.1f}x · {val}</span>'
                )
            if abs(pe_adj_delta) > 0.001:
                adj_c = "#10b981" if pe_adj_delta > 0 else "#ef4444"
                adj_txt = f'{"+" if pe_adj_delta > 0 else ""}{pe_adj_delta*100:.1f}% P/E adj'
                pe_badge_parts.append(
                    f'<span style="font-family:var(--mono);font-size:0.6rem;color:{adj_c}">'
                    f'{adj_txt}</span>'
                )

            # Build card — metric tiles stay in f-string (no HTML vars),
            # P/E badges emitted in a separate st.markdown call below
            st.markdown(f"""
            <div style="padding:14px;background:var(--surface2);border:1px solid var(--border);
                        border-radius:6px 6px 0 0;margin-bottom:0">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <div>
                  <b style="font-family:var(--mono);font-size:1rem">{ticker}</b>
                  <span style="font-size:0.75rem;color:var(--muted);margin-left:8px">{SECTOR_ETFS.get(ticker,'')}</span>
                </div>
                <div style="text-align:right">
                  <span style="font-family:var(--mono);color:{ret_color};font-size:0.9rem">{ret*100:+.1f}%</span>
                  <span style="font-family:var(--mono);font-size:0.65rem;color:var(--muted);display:block">3M raw</span>
                </div>
              </div>
              <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px">
                <div class="metric-tile" style="padding:8px 12px;min-width:80px">
                  <div class="label">$ Alloc</div>
                  <div class="value" style="font-size:1rem">${dollar:,.0f}</div>
                </div>
                <div class="metric-tile" style="padding:8px 12px;min-width:60px">
                  <div class="label">Shares</div>
                  <div class="value" style="font-size:1rem">{shares}</div>
                </div>
                <div class="metric-tile" style="padding:8px 12px;min-width:60px">
                  <div class="label">Price</div>
                  <div class="value" style="font-size:1rem">${px:.2f}</div>
                </div>
              </div>
              <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                <span class="stop-badge">🛑 Stop ${atr_info['stop']:.2f}</span>
                <span style="font-size:0.7rem;color:var(--muted)">2×ATR (${atr_info['atr']:.2f})</span>
                <span style="margin-left:auto;font-size:0.65rem;
                             color:{'var(--accent)' if aligned=='✓ regime' else 'var(--accent3)'};
                             font-family:var(--mono)">{aligned}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

            # P/E badges — separate call to avoid HTML escaping
            if pe_badge_parts:
                badge_html = (
                    '<div style="padding:6px 14px 10px;background:var(--surface2);'
                    'border:1px solid var(--border);border-top:none;border-radius:0 0 6px 6px;'
                    'display:flex;gap:8px;flex-wrap:wrap;margin-bottom:12px">'
                    + "".join(pe_badge_parts)
                    + '</div>'
                )
                st.markdown(badge_html, unsafe_allow_html=True)
            else:
                st.markdown(
                    '<div style="height:12px;background:var(--surface2);'
                    'border:1px solid var(--border);border-top:none;'
                    'border-radius:0 0 6px 6px;margin-bottom:12px"></div>',
                    unsafe_allow_html=True,
                )

        st.markdown(f"""
        <div style="padding:12px 14px;background:rgba(245,158,11,0.08);
                    border:1px solid rgba(245,158,11,0.25);border-radius:6px;
                    font-family:var(--mono);font-size:0.75rem">
          🔒 Tail Hedge: <b>{hedge_ticker}</b> · ${total_inv*hedge_bucket:,.0f}
          {'&nbsp;<span style="color:#ef4444">⚠ CRISIS ROTATION</span>' if crisis_mode else ''}
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # Portfolio summary row
    st.markdown(f"""
    <div class="aw-card">
      <div class="aw-card-title">💼 Portfolio Summary — ${total_inv:,.0f} Total Capital</div>
      <div class="metric-row">
        <div class="metric-tile">
          <div class="label">Core Bucket</div>
          <div class="value" style="color:#3b82f6">${total_inv*core_bucket:,.0f}</div>
          <div class="sub">{core_pct}% · {', '.join(CORE_ASSETS)}</div>
        </div>
        <div class="metric-tile">
          <div class="label">Tactical Bucket</div>
          <div class="value" style="color:#10b981">${total_inv*tactical_alloc_pct:,.0f}</div>
          <div class="sub">{tactical_pct}% · Pure Alpha</div>
        </div>
        <div class="metric-tile">
          <div class="label">Hedge Bucket</div>
          <div class="value" style="color:#f59e0b">${total_inv*hedge_bucket:,.0f}</div>
          <div class="sub">{hedge_pct}% · {hedge_ticker}</div>
        </div>
        <div class="metric-tile">
          <div class="label">Life Stage</div>
          <div class="value" style="color:#8b5cf6;font-size:0.85rem">{glide_choice.split('·')[0].strip()}</div>
          <div class="sub">{quad_emoji} {quad_name} regime</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


    # ── Regime Analysis ─────────────────────────────────────────────────────
    col_regime, col_hedge_info = st.columns([1.3, 1])
    
    with col_regime:
        st.markdown('<div class="aw-card">', unsafe_allow_html=True)
        st.markdown('<div class="aw-card-title">📡 Macro Regime Matrix</div>', unsafe_allow_html=True)
    
        cells = {
            ("rising","rising"):  ("Stagflation","🔥"),
            ("rising","falling"): ("Expansion","🚀"),
            ("falling","rising"): ("Recession","❄️"),
            ("falling","falling"):("Deflation","🌧"),
        }
    
        grid_html = """
        <div style="margin-bottom:8px">
          <div style="text-align:center;font-family:var(--mono);font-size:0.6rem;
                      color:var(--muted);letter-spacing:1px;text-transform:uppercase;
                      margin-bottom:6px;padding-left:28px">
            GROWTH →
          </div>
          <div style="display:grid;grid-template-columns:28px 1fr 1fr;
                      grid-template-rows:1fr 1fr 24px;gap:6px;height:190px">
            <div style="grid-row:1/3;display:flex;align-items:center;justify-content:center">
              <span style="writing-mode:vertical-rl;font-family:var(--mono);font-size:0.6rem;
                           color:var(--muted);letter-spacing:1px;text-transform:uppercase">
                INFLATION ↑
              </span>
            </div>
        """
    
        order = [("rising","falling"),("rising","rising"),("falling","falling"),("falling","rising")]
        for k in order:
            name, emoji = cells[k]
            is_active   = k == quad_key
            cls = "regime-cell active" if is_active else "regime-cell"
            badge = '<div style="font-size:0.55rem;color:var(--accent);margin-top:4px">◉ CURRENT</div>' if is_active else ""
            grid_html += f'<div class="{cls}"><div class="emoji">{emoji}</div><b>{name}</b>{badge}</div>'
    
        grid_html += """
            <div></div>
            <div style="text-align:center;font-family:var(--mono);font-size:0.6rem;
                        color:var(--muted);letter-spacing:1px;text-transform:uppercase">Rising</div>
            <div style="text-align:center;font-family:var(--mono);font-size:0.6rem;
                        color:var(--muted);letter-spacing:1px;text-transform:uppercase">Falling</div>
          </div>
        </div>
        """
    
        st.markdown(grid_html, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="margin-top:12px;padding:10px 14px;background:rgba(59,130,246,0.08);
                    border:1px solid rgba(59,130,246,0.2);border-radius:6px;
                    font-family:var(--mono);font-size:0.75rem">
          GDP: <b style="color:{'#10b981' if gdp_trend=='rising' else '#ef4444'}">{gdp_trend.upper()}</b>
          &nbsp;&nbsp;|&nbsp;&nbsp;
          CPI: <b style="color:{'#ef4444' if cpi_trend=='rising' else '#10b981'}">{cpi_trend.upper()}</b>
          &nbsp;&nbsp;|&nbsp;&nbsp;
          Regime: <b style="color:var(--accent)">{quad_emoji} {quad_name.upper()}</b>
        </div>
        """, unsafe_allow_html=True)
    
        # ── Regime Confidence Gauge ───────────────────────────────────────────
        rc   = regime_confidence
        score = rc["score"]
        color = rc["color"]
    
        # SVG arc gauge — computed from score
        # Arc runs from 210° to 330° (240° sweep) — standard semi-gauge shape
        sweep   = 240
        start_a = 210
        end_a   = start_a + sweep * (score / 100)
        r, cx, cy = 52, 70, 68
    
        # Track arc (background)
        def p(deg, rad=r):
            a = math.radians(deg)
            return f"{cx + rad * math.cos(a):.1f},{cy + rad * math.sin(a):.1f}"
    
        # Large arc flag: 1 if sweep > 180
        fill_sweep = sweep * score / 100
        large_fill = 1 if fill_sweep > 180 else 0
        large_track = 1  # full track is 240° > 180°
    
        track_path = (f"M {p(start_a)} "
                      f"A {r} {r} 0 {large_track} 1 {p(start_a + sweep)}")
        fill_path  = (f"M {p(start_a)} "
                      f"A {r} {r} 0 {large_fill} 1 {p(start_a + fill_sweep)}"
                      if fill_sweep > 0 else "")
    
        # Tick marks at 25/50/75
        ticks_svg = ""
        for pct, tick_label in [(0,""), (25,""), (50,""), (75,""), (100,"")]:
            ta = start_a + sweep * pct / 100
            x1, y1 = cx + (r-6)*math.cos(math.radians(ta)), cy + (r-6)*math.sin(math.radians(ta))
            x2, y2 = cx + (r+2)*math.cos(math.radians(ta)), cy + (r+2)*math.sin(math.radians(ta))
            ticks_svg += f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="#1e2535" stroke-width="2"/>'
    
        gauge_svg = f"""
        <svg viewBox="0 0 140 90" xmlns="http://www.w3.org/2000/svg" style="width:160px;margin:8px auto;display:block">
          <path d="{track_path}" fill="none" stroke="#1e2535" stroke-width="10" stroke-linecap="round"/>
          {"" if not fill_path else f'<path d="{fill_path}" fill="none" stroke="{color}" stroke-width="10" stroke-linecap="round" opacity="0.9"/>'}
          {ticks_svg}
          <text x="{cx}" y="{cy - 4}" text-anchor="middle" font-family="Space Mono,monospace"
                font-size="18" font-weight="700" fill="{color}">{score}</text>
          <text x="{cx}" y="{cy + 12}" text-anchor="middle" font-family="Space Mono,monospace"
                font-size="6" fill="#64748b" letter-spacing="1">CONFIDENCE</text>
          <text x="{cx}" y="{cy + 22}" text-anchor="middle" font-family="Space Mono,monospace"
                font-size="7" font-weight="700" fill="{color}" letter-spacing="1">{rc["label"]}</text>
        </svg>
        """
        st.markdown(gauge_svg, unsafe_allow_html=True)

        # Signal breakdown — collapsed by default to reduce visual noise
        with st.expander(f"Signal breakdown · {rc['label']} ({rc['score']}/100)", expanded=False):
            signals = [
                ("Macro Momentum",    rc["macro_sig"],   f"GDP {rc['gdp_mom']:+.2f}% · CPI {rc['cpi_mom']:+.2f}%"),
                ("Trend Streak",      rc["streak_sig"],  rc["streak_label"]),
                ("Sector Confirm",    rc["sector_sig"],  f"{rc['sector_sig']}% of preferred sectors beating SPY"),
                ("EQ/Bond Decorr",    rc["decorr_sig"],  f"60d corr: {rc['corr_used']:+.2f}"),
                ("Leading Indicators",rc["leading_sig"], f"Yield curve + PMI + claims → {rc['leading_bias'].replace('_',' ')}"),
            ]
            parts = ['<div style="margin-top:4px">']
            for sig_name, sig_val, sig_detail in signals:
                w    = sig_val
                scol = "#10b981" if w >= 70 else ("#f59e0b" if w >= 40 else "#ef4444")
                parts += [
                    '<div style="margin-bottom:7px">',
                    '<div style="display:flex;justify-content:space-between;'
                    'font-family:var(--mono);font-size:0.62rem;color:var(--muted);margin-bottom:3px">',
                    f'<span>{sig_name}</span>'
                    f'<span style="color:{scol}" aria-label="{sig_name}: {w} out of 100">{w}</span>',
                    '</div>',
                    f'<div style="height:4px;background:var(--surface2);border-radius:2px" '
                    f'role="meter" aria-valuenow="{w}" aria-valuemin="0" aria-valuemax="100" '
                    f'aria-label="{sig_name} score: {w}">',
                    f'<div style="height:100%;width:{w}%;background:{scol};border-radius:2px"></div>',
                    '</div>',
                    f'<div style="font-size:0.6rem;color:var(--muted);margin-top:2px">{sig_detail}</div>',
                    '</div>',
                ]
            parts.append('</div>')
            st.markdown("".join(parts), unsafe_allow_html=True)
    
        # Regime summary pill
        st.markdown(
            f'<div style="margin-top:10px;padding:8px 12px;background:rgba(59,130,246,0.08);'
            f'border:1px solid rgba(59,130,246,0.2);border-radius:6px;'
            f'font-family:var(--mono);font-size:0.72rem">'
            f'GDP: <b style="color:{"#10b981" if gdp_trend=="rising" else "#ef4444"}">{gdp_trend.upper()}</b>'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'CPI: <b style="color:{"#ef4444" if cpi_trend=="rising" else "#10b981"}">{cpi_trend.upper()}</b>'
            f'&nbsp;&nbsp;|&nbsp;&nbsp;'
            f'Regime: <b style="color:var(--accent)">{quad_emoji} {quad_name.upper()}</b>'
            f'</div>',
            unsafe_allow_html=True,
        )
    
        # ── Regime Transition Probability ─────────────────────────────────────
        tp       = transition_probability
        tp_score = tp["prob_transition"]
        tp_color = tp["color"]

        st.markdown(
            '<div style="margin-top:16px;padding-top:14px;border-top:1px solid var(--border)">',
            unsafe_allow_html=True,
        )

        # Summary line — always visible
        st.markdown(
            f'<div style="font-family:var(--mono);font-size:0.65rem;letter-spacing:1.5px;'
            f'text-transform:uppercase;color:var(--muted);margin-bottom:8px">'
            f'📈 Regime Transition Probability</div>'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
            f'<div style="flex:1;height:8px;background:var(--surface2);border-radius:4px" '
            f'role="meter" aria-valuenow="{tp_score}" aria-valuemin="0" aria-valuemax="100" '
            f'aria-label="Transition probability: {tp_score}%">'
            f'<div style="height:100%;width:{tp_score}%;background:{tp_color};border-radius:4px"></div>'
            f'</div>'
            f'<b style="font-family:var(--mono);font-size:0.95rem;color:{tp_color};'
            f'width:38px;text-align:right">{tp_score}%</b>'
            f'</div>'
            f'<div style="font-family:var(--mono);font-size:0.7rem;color:{tp_color};margin-bottom:8px">'
            f'Risk: <b>{tp["label"]}</b>'
            f'<span class="sr-only"> — {tp["rationale"]}</span>'
            f' · Stay probability: <b>{tp["stay_prob"]}%</b>'
            f' · Most likely → <b>{tp["top_target"]}</b></div>',
            unsafe_allow_html=True,
        )

        # Rationale — always visible, plain English
        st.markdown(
            f'<div style="font-size:0.7rem;color:var(--muted);padding:6px 10px;'
            f'background:rgba(255,255,255,0.02);border-radius:4px;line-height:1.5;'
            f'margin-bottom:8px" role="note" aria-label="Transition probability rationale">'
            f'{tp["rationale"]}</div>',
            unsafe_allow_html=True,
        )

        # Sub-signals + destination — collapsed by default
        with st.expander(f"Transition signal breakdown · {tp['label']}", expanded=False):
            tp_sig_parts = ['<div style="margin-bottom:10px">']
            for sig_name, sig_val, sig_detail in tp["signals"]:
                s_col = "#ef4444" if sig_val >= 60 else ("#f59e0b" if sig_val >= 35 else "#10b981")
                tp_sig_parts += [
                    '<div style="margin-bottom:5px">',
                    '<div style="display:flex;justify-content:space-between;font-family:var(--mono);'
                    'font-size:0.6rem;color:var(--muted);margin-bottom:2px">',
                    f'<span>{sig_name}</span>'
                    f'<span style="color:{s_col}" aria-label="{sig_name}: {sig_val}">{sig_val}</span>',
                    '</div>',
                    f'<div style="height:3px;background:var(--surface2);border-radius:2px" '
                    f'role="meter" aria-valuenow="{sig_val}" aria-valuemin="0" aria-valuemax="100">',
                    f'<div style="height:100%;width:{sig_val}%;background:{s_col};border-radius:2px"></div>',
                    '</div>',
                    f'<div style="font-size:0.58rem;color:var(--muted);margin-top:1px">{sig_detail}</div>',
                    '</div>',
                ]
            tp_sig_parts.append('</div>')

            st.markdown(
                '<div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);'
                'letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">'
                'If transition occurs — most likely destination:</div>',
                unsafe_allow_html=True,
            )

            tp_dest_parts = [
                '<div style="display:flex;flex-direction:column;gap:4px;margin-bottom:8px" '
                'role="list" aria-label="Transition destination probabilities">',
            ]
            for quad_label, prob in sorted(tp["target_probs"].items(), key=lambda x: -x[1]):
                is_top  = quad_label == tp["top_target"]
                d_color = tp_color if is_top else "var(--muted)"
                tp_dest_parts += [
                    f'<div style="display:flex;align-items:center;gap:8px" role="listitem" '
                    f'aria-label="{quad_label}: {prob}%{"  most likely" if is_top else ""}">',
                    f'<div style="font-family:var(--mono);font-size:0.68rem;color:{d_color};width:110px">'
                    f'{quad_label}</div>',
                    f'<div style="flex:1;height:5px;background:var(--surface2);border-radius:3px">',
                    f'<div style="height:100%;width:{prob}%;background:{d_color};'
                    f'border-radius:3px;opacity:{"1" if is_top else "0.5"}"></div>',
                    f'</div>',
                    f'<div style="font-family:var(--mono);font-size:0.65rem;color:{d_color};'
                    f'width:30px;text-align:right">{prob}%</div>',
                    f'</div>',
                ]
            tp_dest_parts.append('</div>')
            st.markdown("".join(tp_sig_parts) + "".join(tp_dest_parts), unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)   # close transition section
        st.markdown('</div>', unsafe_allow_html=True)   # close aw-card
    
    
    
    with col_hedge_info:
        st.markdown('<div class="aw-card">', unsafe_allow_html=True)
        st.markdown(
            '<div class="aw-card-title">🛡 Tail-Risk Hedge Status</div>',
            unsafe_allow_html=True,
        )

        if crisis_mode:
            st.markdown(
                f'<div class="aw-alert aw-alert-danger" role="alert" aria-live="assertive">'
                f'<div class="aw-alert-icon" aria-hidden="true">🚨</div>'
                f'<div class="aw-alert-body">'
                f'<div class="aw-alert-title" style="color:#ef4444">CRISIS MODE ACTIVE</div>'
                f'<div class="aw-alert-text">'
                f'VOO below 200-day SMA — rotating hedge to '
                f'<b style="color:#ef4444">{hedge_name}</b></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="aw-alert aw-alert-success" role="status">'
                f'<div class="aw-alert-icon" aria-hidden="true">✅</div>'
                f'<div class="aw-alert-body">'
                f'<div class="aw-alert-title" style="color:#10b981">NORMAL REGIME</div>'
                f'<div class="aw-alert-text">'
                f'VOO above 200-day SMA — hedge in '
                f'<b style="color:#10b981">{hedge_name}</b></div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )
    
        sma_pct = ((voo_current_val - voo_sma200_val) / voo_sma200_val * 100) if voo_sma200_val else 0
        color = "#10b981" if not crisis_mode else "#ef4444"
        st.markdown(f"""
        <div class="metric-row" style="margin-top:16px">
          <div class="metric-tile">
            <div class="label">VOO Price</div>
            <div class="value" style="color:{color}">${voo_current_val:.2f}</div>
          </div>
          <div class="metric-tile">
            <div class="label">200-Day SMA</div>
            <div class="value">${voo_sma200_val:.2f}</div>
          </div>
          <div class="metric-tile">
            <div class="label">SMA Distance</div>
            <div class="value" style="color:{color}">{sma_pct:+.1f}%</div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown(f"""
        <div style="padding:14px;background:var(--surface2);border:1px solid var(--border);
                    border-radius:6px;font-family:var(--mono);font-size:0.75rem;margin-top:4px">
          Active hedge: <b style="color:var(--accent3)">{hedge_ticker}</b>
          &nbsp;—&nbsp; {hedge_name}<br>
          Allocation: <b>{hedge_pct}%</b> of portfolio
          = <b>${total_inv * hedge_bucket:,.0f}</b>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # ══════════════════════════════════════════════════════════════════════════════
    # TABS
    # ══════════════════════════════════════════════════════════════════════════════
    
    # ── Correlation Matrix Panel ──────────────────────────────────────────────
    # _corr_60d, _corr_1y, _eq_bond_corr, _rp_stressed computed in data layer above
    # Always includes VOO+TLT as anchor pair regardless of glide path stage.

    # ── SVG heatmap builder ───────────────────────────────────────────────────
    def _corr_color(val: float) -> str:
        """Map correlation -1…+1 to a color.
           -1.0 → rich green  (diversification working perfectly)
            0.0 → near-neutral dark
           +1.0 → rich red    (assets moving together, RP breaks down)
        """
        if val >= 0:
            # 0 → dark surface, 1 → red
            intensity = int(val * 220)
            return f"rgb({min(239, 30 + intensity)},{max(30, 68 - intensity//3)},{max(30, 68 - intensity//2)})"
        else:
            # 0 → dark surface, -1 → green
            intensity = int(-val * 220)
            return f"rgb({max(16, 30 - intensity//3)},{min(185, 30 + intensity)},{max(80, 80 + intensity//3)})"

    def _build_corr_svg(corr_df: pd.DataFrame, size: int = 300) -> str:
        n       = len(corr_df)
        labels  = list(corr_df.columns)
        pad_l   = 46
        pad_t   = 46
        cell_w  = (size - pad_l) / n
        cell_h  = (size - pad_t) / n
        svg_w   = size + 4
        svg_h   = size + 4

        # Accessible title for screen readers
        title_id = "corr-matrix-title"
        desc_id  = "corr-matrix-desc"
        off_diag = [float(corr_df.loc[r, c])
                    for r in labels for c in labels if r != c]
        most_neg = min(off_diag) if off_diag else 0.0
        most_pos = max(off_diag) if off_diag else 0.0
        desc_str = (
            f'Heatmap of pairwise correlations for {", ".join(labels)}. '
            f'Most negative pair: {most_neg:+.2f} (green = good diversification). '
            f'Most positive pair: {most_pos:+.2f} (red = correlated, risk parity stress).'
        )

        parts = [
            f'<svg viewBox="0 0 {svg_w} {svg_h}" xmlns="http://www.w3.org/2000/svg" '
            f'role="img" aria-labelledby="{title_id} {desc_id}" '
            f'style="width:100%;max-width:{svg_w}px;font-family:Space Mono,monospace">',
            f'<title id="{title_id}">60-day rolling asset correlation matrix</title>',
            f'<desc id="{desc_id}">{desc_str}</desc>',
        ]

        # Column labels (top)
        for j, label in enumerate(labels):
            x = pad_l + j * cell_w + cell_w / 2
            parts.append(
                f'<text x="{x:.1f}" y="{pad_t - 6}" text-anchor="middle" '
                f'font-size="8" fill="#64748b" letter-spacing="0.5">{label}</text>'
            )

        # Row labels (left) + cells
        for i, row in enumerate(labels):
            y_center = pad_t + i * cell_h + cell_h / 2
            # Row label
            parts.append(
                f'<text x="{pad_l - 4}" y="{y_center + 3:.1f}" text-anchor="end" '
                f'font-size="8" fill="#64748b">{row}</text>'
            )
            for j, col in enumerate(labels):
                val   = float(corr_df.loc[row, col])
                color = _corr_color(val)
                x0    = pad_l + j * cell_w
                y0    = pad_t + i * cell_h
                # Cell background
                parts.append(
                    f'<rect x="{x0:.1f}" y="{y0:.1f}" '
                    f'width="{cell_w - 1:.1f}" height="{cell_h - 1:.1f}" '
                    f'fill="{color}" rx="2"/>'
                )
                # Value label — skip diagonal
                if i != j:
                    txt_color = "#ffffff" if abs(val) > 0.4 else "#94a3b8"
                    parts.append(
                        f'<text x="{x0 + cell_w/2:.1f}" y="{y0 + cell_h/2 + 4:.1f}" '
                        f'text-anchor="middle" font-size="9" fill="{txt_color}" '
                        f'font-weight="600">{val:+.2f}</text>'
                    )
                else:
                    # Diagonal — just the label repeated
                    parts.append(
                        f'<text x="{x0 + cell_w/2:.1f}" y="{y0 + cell_h/2 + 4:.1f}" '
                        f'text-anchor="middle" font-size="8" fill="#475569">1.00</text>'
                    )

    

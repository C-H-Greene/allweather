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

:root {
    --bg: #0a0c10;
    --surface: #10141c;
    --surface2: #161b26;
    --border: #1e2535;
    --accent: #3b82f6;
    --accent2: #10b981;
    --accent3: #f59e0b;
    --accent4: #ef4444;
    --text: #e2e8f0;
    --muted: #64748b;
    --mono: 'Space Mono', monospace;
    --sans: 'DM Sans', sans-serif;
}

html, body, [class*="css"] {
    background-color: var(--bg) !important;
    color: var(--text) !important;
    font-family: var(--sans);
}

.stApp { background-color: var(--bg); }

/* Header */
.aw-header {
    display: flex; align-items: center; gap: 16px;
    padding: 28px 0 20px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
}
.aw-header h1 {
    font-family: var(--mono);
    font-size: 1.6rem;
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

/* Cards */
.aw-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 24px;
    margin-bottom: 20px;
}
.aw-card-title {
    font-family: var(--mono);
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 16px;
}

/* Metric tiles */
.metric-row { display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }
.metric-tile {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 16px 20px;
    flex: 1;
    min-width: 120px;
}
.metric-tile .label {
    font-size: 0.65rem;
    font-family: var(--mono);
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 6px;
}
.metric-tile .value {
    font-family: var(--mono);
    font-size: 1.4rem;
    font-weight: 700;
    color: var(--text);
}
.metric-tile .sub { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }

/* Regime matrix */
.regime-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 8px;
    height: 200px;
}
.regime-cell {
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    font-family: var(--mono);
    font-size: 0.75rem;
    letter-spacing: 1px;
    text-transform: uppercase;
    border: 1px solid var(--border);
    background: var(--surface2);
    color: var(--muted);
    transition: all 0.2s;
    text-align: center;
    padding: 8px;
}
.regime-cell.active {
    border-color: var(--accent);
    background: rgba(59,130,246,0.12);
    color: var(--text);
    box-shadow: 0 0 20px rgba(59,130,246,0.15);
}
.regime-cell .emoji { font-size: 1.5rem; margin-bottom: 6px; }
.regime-axes {
    display: grid;
    grid-template-columns: 28px 1fr;
    grid-template-rows: 1fr 28px;
    gap: 8px;
}
.axis-label {
    font-family: var(--mono);
    font-size: 0.6rem;
    color: var(--muted);
    writing-mode: vertical-rl;
    text-align: center;
    letter-spacing: 1px;
    text-transform: uppercase;
}
.axis-label-h {
    font-family: var(--mono);
    font-size: 0.6rem;
    color: var(--muted);
    text-align: center;
    letter-spacing: 1px;
    text-transform: uppercase;
    grid-column: 2;
}

/* Allocation bar */
.alloc-bar-container { margin-bottom: 12px; }
.alloc-bar-label {
    display: flex; justify-content: space-between;
    font-family: var(--mono); font-size: 0.75rem;
    margin-bottom: 5px; color: var(--text);
}
.alloc-bar-track {
    height: 6px; background: var(--surface2);
    border-radius: 3px; overflow: hidden;
}
.alloc-bar-fill {
    height: 100%; border-radius: 3px;
    transition: width 0.6s ease;
}

/* Stop-loss badge */
.stop-badge {
    display: inline-block;
    background: rgba(239,68,68,0.12);
    border: 1px solid rgba(239,68,68,0.3);
    color: #ef4444;
    font-family: var(--mono);
    font-size: 0.7rem;
    padding: 3px 8px;
    border-radius: 4px;
}

/* Crisis alert */
.crisis-alert {
    background: rgba(239,68,68,0.08);
    border: 1px solid rgba(239,68,68,0.3);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.safe-alert {
    background: rgba(16,185,129,0.08);
    border: 1px solid rgba(16,185,129,0.3);
    border-radius: 8px;
    padding: 16px 20px;
    margin-bottom: 20px;
}

/* Streamlit overrides */
.stSlider > div > div > div { background: var(--accent) !important; }
div[data-testid="stMetric"] {
    background: var(--surface2);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 12px 16px;
}
.stDataFrame { background: var(--surface) !important; }
div[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
div[data-testid="stSidebar"] * { color: var(--text) !important; }
.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    font-family: var(--mono) !important;
    font-size: 0.75rem !important;
    letter-spacing: 1px !important;
    border-radius: 5px !important;
    padding: 8px 20px !important;
}
.stButton > button:hover { opacity: 0.85 !important; }
hr { border-color: var(--border) !important; }
.stTabs [data-baseweb="tab"] {
    font-family: var(--mono) !important;
    font-size: 0.7rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase;
}
.stTabs [aria-selected="true"] { color: var(--accent) !important; }
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
    Pull GDP and CPI from FRED. Returns trend, raw values, momentum magnitude,
    and consecutive-period streak — all used by the regime confidence engine.
    """
    import urllib.request

    def fred_series(series_id, tail=12):
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

    gdp = fred_series("GDP",      tail=12)
    cpi = fred_series("CPIAUCSL", tail=12)

    gdp_trend = "rising"
    cpi_trend = "falling"
    gdp_vals  = cpi_vals = []

    # ── GDP ───────────────────────────────────────────────────────────────
    gdp_mom    = 0.0   # % change, last period
    gdp_streak = 1     # consecutive quarters in current direction
    if gdp is not None and len(gdp) >= 2:
        gdp_trend  = "rising" if gdp.iloc[-1] > gdp.iloc[-2] else "falling"
        gdp_vals   = gdp.tolist()
        gdp_mom    = float((gdp.iloc[-1] - gdp.iloc[-2]) / gdp.iloc[-2] * 100)
        # Count how many consecutive periods match current trend
        direction  = np.sign(gdp.diff().dropna())
        current_d  = direction.iloc[-1]
        streak = 1
        for d in reversed(direction.iloc[:-1].tolist()):
            if np.sign(d) == current_d:
                streak += 1
            else:
                break
        gdp_streak = streak

    # ── CPI ───────────────────────────────────────────────────────────────
    cpi_mom    = 0.0
    cpi_streak = 1
    if cpi is not None and len(cpi) >= 2:
        lookback   = min(5, len(cpi) - 1)
        cpi_trend  = "rising" if cpi.iloc[-1] > cpi.iloc[-lookback] else "falling"
        cpi_vals   = cpi.tolist()
        cpi_mom    = float((cpi.iloc[-1] - cpi.iloc[-lookback]) / cpi.iloc[-lookback] * 100)
        direction  = np.sign(cpi.diff().dropna())
        current_d  = direction.iloc[-1]
        streak = 1
        for d in reversed(direction.iloc[:-1].tolist()):
            if np.sign(d) == current_d:
                streak += 1
            else:
                break
        cpi_streak = streak

    return (gdp_trend, cpi_trend, gdp_vals, cpi_vals,
            gdp_mom, cpi_mom, gdp_streak, cpi_streak)

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

    # ── Save to localStorage ───────────────────────────────────────────────
    save_btn = st.button("💾  SAVE SETTINGS", use_container_width=True)
    run_btn  = st.button("🔄  REFRESH DATA",  use_container_width=True)

    if save_btn:
        new_glide_index = glide_keys.index(glide_choice)
        # Write to query params (Streamlit side)
        st.query_params["total_inv"]    = str(total_inv)
        st.query_params["glide_index"]  = str(new_glide_index)
        st.query_params["core_pct"]     = str(core_pct)
        st.query_params["tactical_pct"] = str(tactical_pct)
        # Write to localStorage (browser side)
        st.components.v1.html(f"""
        <script>
        localStorage.setItem("aw_total_inv",    "{total_inv}");
        localStorage.setItem("aw_glide_index",  "{new_glide_index}");
        localStorage.setItem("aw_core_pct",     "{core_pct}");
        localStorage.setItem("aw_tactical_pct", "{tactical_pct}");
        </script>
        """, height=0)
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

st.markdown(f"""
<div class="aw-header">
  <span style="font-size:2rem">🌦</span>
  <div>
    <h1>PROJECT ALL-WEATHER</h1>
    <div style="margin-top:4px;display:flex;gap:8px">
      <span class="aw-badge">EQUITY CORE</span>
      <span class="aw-badge" style="background:#10b981">PURE ALPHA</span>
      <span class="aw-badge" style="background:#f59e0b">TAIL HEDGE</span>
      <span class="aw-badge" style="background:#8b5cf6">{glide_choice.split('·')[0].strip()}</span>
    </div>
  </div>
  <div style="margin-left:auto;text-align:right;font-family:var(--mono);font-size:0.7rem;color:var(--muted)">
    Last refresh<br><b style="color:var(--text)">{datetime.now().strftime('%Y-%m-%d %H:%M')}</b>
  </div>
</div>
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

    gdp_trend, cpi_trend, gdp_vals, cpi_vals, \
    gdp_mom, cpi_mom, gdp_streak, cpi_streak = fetch_fred_macro()

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

def compute_regime_confidence(
    gdp_mom: float, cpi_mom: float,
    gdp_streak: int, cpi_streak: int,
    quad_preferred: list, sector_returns: pd.Series,
    prices_all: pd.DataFrame,
) -> dict:

    # ── Signal 1: Macro momentum magnitude ───────────────────────────────
    # Typical quarterly GDP move ~0.5–1.5%, CPI move ~0.2–0.8%
    # Scale to 0–1 using expected max magnitudes
    gdp_mag   = min(abs(gdp_mom) / 2.0, 1.0)   # 2% = full confidence
    cpi_mag   = min(abs(cpi_mom) / 1.5, 1.0)   # 1.5% = full confidence
    macro_sig = (gdp_mag + cpi_mag) / 2.0

    # ── Signal 2: Streak / trend age ─────────────────────────────────────
    # 1 period = just turned, low confidence
    # 4+ periods = well established; 8+ = potentially late-cycle
    min_streak = min(gdp_streak, cpi_streak)   # both axes must agree
    if min_streak <= 1:
        streak_sig = 0.25
    elif min_streak <= 3:
        streak_sig = 0.60
    elif min_streak <= 6:
        streak_sig = 0.85
    else:
        # Very long streak — may be mature/late; confidence plateaus then fades
        streak_sig = max(0.60, 0.85 - (min_streak - 6) * 0.05)

    # ── Signal 3: Sector price confirmation ──────────────────────────────
    spy_3m = 0.0
    if "VOO" in sector_returns.index:
        spy_3m = float(sector_returns["VOO"])
    elif "SPY" in sector_returns.index:
        spy_3m = float(sector_returns["SPY"])

    if quad_preferred:
        beats = sum(
            1 for t in quad_preferred
            if t in sector_returns.index and float(sector_returns[t]) > spy_3m
        )
        sector_sig = beats / len(quad_preferred)
    else:
        sector_sig = 0.5

    # ── Signal 4: Equity-bond decorrelation ──────────────────────────────
    decorr_sig = 0.5   # neutral default
    if "VOO" in prices_all.columns and "TLT" in prices_all.columns:
        eq_ret   = prices_all["VOO"].pct_change().dropna().tail(60)
        bond_ret = prices_all["TLT"].pct_change().dropna().tail(60)
        if len(eq_ret) >= 20 and len(bond_ret) >= 20:
            combined = pd.concat([eq_ret, bond_ret], axis=1).dropna()
            if len(combined) >= 20:
                corr = float(combined.iloc[:, 0].corr(combined.iloc[:, 1]))
                # Negative corr = ideal (1.0), zero corr = neutral (0.5),
                # positive corr = stress (0.0)
                decorr_sig = max(0.0, min(1.0, (1.0 - corr) / 2.0))

    # ── Blend ─────────────────────────────────────────────────────────────
    score = (
        0.25 * macro_sig   +
        0.25 * streak_sig  +
        0.30 * sector_sig  +
        0.20 * decorr_sig
    )
    score_pct = round(score * 100)

    # ── Stability label ───────────────────────────────────────────────────
    if score_pct >= 75:
        label, color, desc = "ESTABLISHED", "#10b981", "Signals strongly aligned. High conviction."
    elif score_pct >= 55:
        label, color, desc = "CONFIRMED",   "#3b82f6", "Regime confirmed across most signals."
    elif score_pct >= 35:
        label, color, desc = "FORMING",     "#f59e0b", "Early signals present. Monitor for confirmation."
    else:
        label, color, desc = "TRANSITIONING", "#ef4444", "Weak or conflicting signals. Regime may be shifting."

    # Streak label for display
    if min_streak <= 1:
        streak_label = "New signal"
    elif min_streak <= 3:
        streak_label = f"{min_streak} periods"
    else:
        streak_label = f"{min_streak} periods" + (" — late cycle" if min_streak > 6 else "")

    return {
        "score":        score_pct,
        "label":        label,
        "color":        color,
        "desc":         desc,
        "macro_sig":    round(macro_sig * 100),
        "streak_sig":   round(streak_sig * 100),
        "sector_sig":   round(sector_sig * 100),
        "decorr_sig":   round(decorr_sig * 100),
        "streak_label": streak_label,
        "gdp_mom":      round(gdp_mom, 3),
        "cpi_mom":      round(cpi_mom, 3),
        "corr_used":    round(1.0 - decorr_sig * 2.0, 3),   # back-compute for display
    }

regime_confidence = compute_regime_confidence(
    gdp_mom, cpi_mom, gdp_streak, cpi_streak,
    quad_preferred, sector_returns, prices_all,
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
# UI — REGIME SECTION
# ══════════════════════════════════════════════════════════════════════════════

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

    # Signal breakdown bars — 4 sub-scores
    signals = [
        ("Macro Momentum",   rc["macro_sig"],  f"GDP {rc['gdp_mom']:+.2f}% · CPI {rc['cpi_mom']:+.2f}%"),
        ("Trend Streak",     rc["streak_sig"], rc["streak_label"]),
        ("Sector Confirm",   rc["sector_sig"], f"{rc['sector_sig']}% of preferred sectors beating SPY"),
        ("EQ/Bond Decorr",   rc["decorr_sig"], f"60d corr: {rc['corr_used']:+.2f}"),
    ]

    parts = ['<div style="margin-top:4px">']
    for sig_name, sig_val, sig_detail in signals:
        w    = sig_val
        scol = "#10b981" if w >= 70 else ("#f59e0b" if w >= 40 else "#ef4444")
        parts += [
            '<div style="margin-bottom:7px">',
            '<div style="display:flex;justify-content:space-between;'
            'font-family:var(--mono);font-size:0.62rem;color:var(--muted);margin-bottom:3px">',
            f'<span>{sig_name}</span><span style="color:{scol}">{w}</span>',
            '</div>',
            '<div style="height:4px;background:var(--surface2);border-radius:2px">',
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
    st.markdown('</div>', unsafe_allow_html=True)



with col_hedge_info:
    st.markdown('<div class="aw-card">', unsafe_allow_html=True)
    st.markdown('<div class="aw-card-title">🛡 Tail-Risk Hedge Status</div>', unsafe_allow_html=True)

    if crisis_mode:
        st.markdown(f"""
        <div class="crisis-alert">
          <span style="font-size:1.8rem">🚨</span>
          <div>
            <div style="font-family:var(--mono);font-weight:700;color:#ef4444;font-size:0.85rem">
              CRISIS MODE ACTIVE
            </div>
            <div style="font-size:0.8rem;color:var(--muted);margin-top:4px">
              VOO below 200-day SMA → rotating hedge to <b style="color:#ef4444">{hedge_name}</b>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="safe-alert">
          <div style="font-family:var(--mono);font-weight:700;color:#10b981;font-size:0.85rem">
            ✅ NORMAL REGIME
          </div>
          <div style="font-size:0.8rem;color:var(--muted);margin-top:4px">
            VOO above 200-day SMA → hedge parked in <b style="color:#10b981">{hedge_name}</b>
          </div>
        </div>
        """, unsafe_allow_html=True)

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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊  ALLOCATION ENGINE",
    "📈  SECTOR MOMENTUM",
    "⚖  DRIFT REPORT",
    "🗺  GLIDE PATH",
    "📰  NARRATIVE RADAR",
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

# ─── TAB 2 — SECTOR MOMENTUM ─────────────────────────────────────────────────
with tab2:
    st.markdown('<div class="aw-card">', unsafe_allow_html=True)
    st.markdown('<div class="aw-card-title">📈 S&P 500 Sector Momentum — 3M Return · Vol · P/C · Fwd P/E</div>', unsafe_allow_html=True)

    # P/E source indicator
    live_count = sum(1 for v in pe_data.values() if v.get("source") == "live")
    pe_source_label = f"{'Live' if live_count > 0 else 'Estimated'} P/E data ({live_count}/{len(pe_data)} live · SPY {spy_pe:.1f}x)"
    pe_source_color = "#10b981" if live_count > 0 else "#f59e0b"

    # Column header
    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:12px;padding:6px 0 10px;
                border-bottom:1px solid var(--border);
                font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                letter-spacing:1px;text-transform:uppercase">
      <div style="width:48px">ETF</div>
      <div style="flex:1">Sector · Current: {quad_emoji} {quad_name} / Opposite: {anti_quad_emoji} {anti_quad_name}</div>
      <div style="width:110px">3M Return</div>
      <div style="width:60px;text-align:right">3M Ret</div>
      <div style="width:68px;text-align:right">Rel Vol</div>
      <div style="width:54px;text-align:right">P/C</div>
      <div style="width:80px;text-align:right">
        <span style="color:{pe_source_color}">Fwd P/E</span>
      </div>
      <div style="width:190px;text-align:right">Badges</div>
    </div>
    """, unsafe_allow_html=True)

    for ticker in sector_returns_adj.index:
        ret      = sector_returns[ticker] if ticker in sector_returns.index else 0.0
        ret_adj  = float(sector_returns_adj[ticker])
        bar_w    = min(abs(ret) * 200, 100)
        bar_c    = "#10b981" if ret >= 0 else "#ef4444"
        is_sel   = ticker in top3
        is_reg   = ticker in quad_preferred
        is_anti  = ticker in anti_preferred and not is_reg

        # ── Volume ────────────────────────────────────────────────────────
        if ticker in volumes_all.columns and len(volumes_all[ticker].dropna()) >= 20:
            v   = volumes_all[ticker].dropna()
            rv  = float(v.tail(5).mean() / v.tail(20).mean())
            rv_str   = f"{rv:.2f}×"
            rv_color = "#10b981" if rv > 1.15 else ("#ef4444" if rv < 0.85 else "var(--muted)")
            rv_label = "↑ high" if rv > 1.15 else ("↓ low" if rv < 0.85 else "avg")
        else:
            rv_str = "—"; rv_color = "var(--muted)"; rv_label = ""

        # ── Put/Call ratio ────────────────────────────────────────────────
        pcr = pcr_data.get(ticker)
        if pcr is not None:
            pcr_str   = f"{pcr:.2f}"
            pcr_color = "#ef4444" if pcr > 1.0 else ("#10b981" if pcr < 0.7 else "var(--muted)")
            pcr_label = "bear" if pcr > 1.0 else ("bull" if pcr < 0.7 else "neut")
        else:
            pcr_str = "—"; pcr_color = "var(--muted)"; pcr_label = ""

        # ── Forward P/E ───────────────────────────────────────────────────
        pe     = pe_data.get(ticker, {})
        fwd_pe = pe.get("fwd_pe")
        rel_pe = pe.get("rel_pe")
        val    = pe.get("valuation", "fair")
        pe_src = pe.get("source", "estimate")

        if fwd_pe is not None:
            pe_str    = f"{fwd_pe:.1f}x"
            rel_str   = f"{rel_pe:+.0%}".replace("+0%", "inline").replace("-", "−") if rel_pe else ""
            pe_color  = (
                "#ef4444" if val == "expensive" else
                "#10b981" if val == "cheap" else
                "var(--muted)"
            )
            pe_label  = val
        else:
            pe_str = "—"; pe_color = "var(--muted)"; pe_label = ""; rel_str = ""

        # Show P/E adjustment indicator if it changed the adj score
        pe_adj_delta = ret_adj - ret
        adj_indicator = ""
        if abs(pe_adj_delta) > 0.001:
            adj_color = "#10b981" if pe_adj_delta > 0 else "#ef4444"
            adj_indicator = f'<span style="font-size:0.58rem;color:{adj_color}">{"▲" if pe_adj_delta > 0 else "▼"} adj</span>'

        # ── Data row ──────────────────────────────────────────────────────
        ticker_color = "var(--text)" if is_sel else "var(--muted)"
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:10px 0 4px;
                    border-bottom:{'none' if (is_sel or is_reg or is_anti) else '1px solid var(--border)'}">
          <div style="font-family:var(--mono);font-weight:700;width:48px;
                      color:{ticker_color}">{ticker}</div>
          <div style="flex:1;font-size:0.78rem;color:var(--muted)">{SECTOR_ETFS.get(ticker, ticker)}</div>
          <div style="width:110px">
            <div style="height:5px;background:var(--surface2);border-radius:2px;overflow:hidden">
              <div style="height:100%;width:{bar_w:.0f}%;background:{bar_c};border-radius:2px"></div>
            </div>
          </div>
          <div style="font-family:var(--mono);font-size:0.8rem;width:60px;text-align:right;
                      color:{bar_c}">{ret*100:+.1f}%</div>
          <div style="font-family:var(--mono);font-size:0.76rem;width:68px;text-align:right">
            <span style="color:{rv_color}">{rv_str}</span>
            <span style="font-size:0.58rem;color:var(--muted);display:block">{rv_label}</span>
          </div>
          <div style="font-family:var(--mono);font-size:0.76rem;width:54px;text-align:right">
            <span style="color:{pcr_color}">{pcr_str}</span>
            <span style="font-size:0.58rem;color:var(--muted);display:block">{pcr_label}</span>
          </div>
          <div style="font-family:var(--mono);font-size:0.76rem;width:80px;text-align:right">
            <span style="color:{pe_color}">{pe_str}</span>
            <span style="font-size:0.58rem;color:{pe_color};display:block">{pe_label} {adj_indicator}</span>
          </div>
          <div style="width:190px"></div>
        </div>
        """, unsafe_allow_html=True)

        # ── Badges — separate call so inline styles aren't escaped ────────
        if is_sel or is_reg or is_anti:
            sel_badge  = (
                '<span style="background:#3b82f6;color:white;padding:2px 6px;'
                'border-radius:3px;font-size:0.6rem;font-family:var(--mono)">SELECTED</span>'
            ) if is_sel else ""
            reg_badge  = (
                '<span style="background:rgba(167,139,250,0.2);color:#a78bfa;padding:2px 6px;'
                'border-radius:3px;font-size:0.6rem;font-family:var(--mono);'
                'border:1px solid rgba(167,139,250,0.3)">REGIME</span>'
            ) if is_reg else ""
            anti_badge = (
                f'<span style="background:rgba(239,68,68,0.12);color:#ef4444;padding:2px 6px;'
                f'border-radius:3px;font-size:0.6rem;font-family:var(--mono);'
                f'border:1px solid rgba(239,68,68,0.3)" '
                f'title="Preferred in {anti_quad_emoji} {anti_quad_name} — the opposite of current {quad_emoji} {quad_name}">'
                f'ANTI-REGIME</span>'
            ) if is_anti else ""
            st.markdown(
                f'<div style="display:flex;gap:5px;justify-content:flex-end;'
                f'padding:3px 0 10px;border-bottom:1px solid var(--border)">'
                f'{sel_badge}{reg_badge}{anti_badge}</div>',
                unsafe_allow_html=True
            )

    st.markdown(f"""
    <div style="margin-top:12px;padding:10px 14px;background:var(--surface2);
                border:1px solid var(--border);border-radius:6px;
                font-size:0.7rem;color:var(--muted);font-family:var(--mono)">
      <b style="color:var(--text)">Rel Vol</b> = 5d avg ÷ 20d avg volume.
      &gt;1.15× = above-average participation · &lt;0.85× = low conviction.
      &nbsp;&nbsp;<b style="color:var(--text)">P/C</b> = put/call volume ratio.
      &gt;1.0 = net bearish · &lt;0.7 = net bullish.
      &nbsp;&nbsp;<b style="color:var(--text)">Fwd P/E</b> = forward 12-month P/E vs SPY {spy_pe:.1f}x.
      <span style="color:#10b981">cheap</span> = &lt;0.80× SPY ·
      <span style="color:#ef4444">expensive</span> = &gt;1.25× SPY.
      P/E adjusts momentum score: cheap +2% · expensive −3%.
      &nbsp;&nbsp;<span style="color:{pe_source_color}">{pe_source_label}</span>
      &nbsp;&nbsp;<b style="color:#a78bfa">REGIME</b> = preferred in current {quad_emoji} {quad_name}.
      &nbsp;&nbsp;<b style="color:#ef4444">ANTI-REGIME</b> = preferred in opposite {anti_quad_emoji} {anti_quad_name}.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── TAB 3 — DRIFT REPORT ────────────────────────────────────────────────────
with tab3:
    st.markdown('<div class="aw-card">', unsafe_allow_html=True)
    st.markdown('<div class="aw-card-title">⚖ Drift Report — Current vs. Target Weights</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.8rem;color:var(--muted);margin-bottom:16px">
      Enter your current holdings, then hit <b>💾 Save Holdings</b>.
      Values persist in your browser — keyed by ticker so they survive
      regime rotations that change the tactical sector selection.
    </div>
    """, unsafe_allow_html=True)

    # ── Sector override — load saved selection from localStorage ──────────
    # JS: push any saved manual-sector selection from localStorage into URL params
    all_sector_list = list(SECTOR_ETFS.keys())
    st.components.v1.html("""
    <script>
    (function() {
      const v = localStorage.getItem("aw_manual_sectors");
      if (v !== null) {
        const params = new URLSearchParams(window.parent.location.search);
        if (params.get("manual_sectors") !== v) {
          params.set("manual_sectors", v);
          window.parent.history.replaceState(null, "", "?" + params.toString());
        }
      }
    })();
    </script>
    """, height=0)

    # Read saved manual sectors from query params
    saved_sectors_raw = st.query_params.get("manual_sectors", "")
    saved_sectors = [s for s in saved_sectors_raw.split(",") if s in all_sector_list] \
                    if saved_sectors_raw else []
    using_manual  = len(saved_sectors) > 0

    # ── Sector override UI ────────────────────────────────────────────────
    with st.expander(
        f"⚙ Sector Override {'— ' + ', '.join(saved_sectors) + ' (manual)' if using_manual else '— using algo selection: ' + ', '.join(top3)}",
        expanded=using_manual,
    ):
        st.markdown("""
        <div style="font-size:0.78rem;color:var(--muted);margin-bottom:12px">
          By default the drift report tracks the <b>3 algorithmically selected tactical sectors</b>.
          Use the selector below to override with your actual holdings.
          Select 1–5 sectors; target weight distributes evenly across your selection.
          Save to persist — clear the selection to revert to algo mode.
        </div>
        """, unsafe_allow_html=True)

        override_col, btn_col = st.columns([3, 1])
        with override_col:
            manual_sectors = st.multiselect(
                "Select your tactical sectors",
                options=all_sector_list,
                default=saved_sectors if using_manual else [],
                format_func=lambda t: f"{t} — {SECTOR_ETFS.get(t, t)}",
                key="sector_override_select",
                label_visibility="collapsed",
            )
        with btn_col:
            save_sectors_btn = st.button("💾 Save sectors", key="save_sectors_btn",
                                         use_container_width=True)
            clear_btn        = st.button("✕ Revert to algo", key="clear_sectors_btn",
                                         use_container_width=True)

        if save_sectors_btn and manual_sectors:
            joined = ",".join(manual_sectors)
            st.query_params["manual_sectors"] = joined
            st.components.v1.html(
                f'<script>localStorage.setItem("aw_manual_sectors", "{joined}");</script>',
                height=0,
            )
            saved_sectors  = manual_sectors
            using_manual   = True
            st.success(f"✓ Tracking: {', '.join(manual_sectors)}", icon="💾")

        if clear_btn:
            st.query_params.pop("manual_sectors", None)
            st.components.v1.html(
                '<script>localStorage.removeItem("aw_manual_sectors");</script>',
                height=0,
            )
            saved_sectors = []
            using_manual  = False
            st.success("✓ Reverted to algo sector selection.", icon="↩")

        # Show current vs algo for context
        algo_col, manual_col = st.columns(2)
        with algo_col:
            st.markdown(
                '<div style="font-family:var(--mono);font-size:0.65rem;color:var(--muted);'
                'margin-top:8px">ALGO SELECTION (regime + momentum)</div>',
                unsafe_allow_html=True,
            )
            for t in top3:
                tag = " ✓ regime" if t in quad_preferred else " ↑ momentum"
                st.markdown(
                    f'<div style="font-family:var(--mono);font-size:0.75rem;'
                    f'color:{"#10b981" if t in quad_preferred else "var(--accent3)"}">'
                    f'{t} — {SECTOR_ETFS.get(t,"")}{tag}</div>',
                    unsafe_allow_html=True,
                )
        with manual_col:
            if using_manual:
                st.markdown(
                    '<div style="font-family:var(--mono);font-size:0.65rem;color:var(--muted);'
                    'margin-top:8px">YOUR MANUAL SELECTION (active)</div>',
                    unsafe_allow_html=True,
                )
                for t in saved_sectors:
                    tag = " ✓ regime" if t in quad_preferred else (
                          " ⚠ anti-regime" if t in anti_preferred else "")
                    color = "#10b981" if t in quad_preferred else (
                            "#ef4444" if t in anti_preferred else "var(--text)")
                    st.markdown(
                        f'<div style="font-family:var(--mono);font-size:0.75rem;color:{color}">'
                        f'{t} — {SECTOR_ETFS.get(t,"")}{tag}</div>',
                        unsafe_allow_html=True,
                    )

    # Determine active tactical tickers for the drift table
    active_tactical = saved_sectors if using_manual else top3
    # Distribute tactical % evenly across however many sectors selected
    tactical_per_active = tactical_alloc_pct / max(len(active_tactical), 1)

    # ── Build target rows ──────────────────────────────────────────────────
    target_rows = []
    for ticker in CORE_ASSETS:
        if ticker not in core_weights.index:
            continue
        w = core_weights[ticker]
        target_rows.append({
            "Ticker":   ticker,
            "Bucket":   "Core",
            "Label":    CORE_LABELS.get(ticker, ticker),
            "Target %": round(core_bucket * w * 100, 2),
        })
    for ticker in active_tactical:
        target_rows.append({
            "Ticker":   ticker,
            "Bucket":   "Tactical" + (" ✏" if using_manual else ""),
            "Label":    SECTOR_ETFS.get(ticker, ticker),
            "Target %": round(tactical_per_active * 100, 2),
        })
    target_rows.append({
        "Ticker":   hedge_ticker,
        "Bucket":   "Hedge",
        "Label":    HEDGE_ASSETS.get(hedge_ticker, hedge_ticker),
        "Target %": float(hedge_pct),
    })

    target_df     = pd.DataFrame(target_rows)
    drift_tickers = target_df["Ticker"].tolist()

    # ── JS: load current %, cost basis, shares for ALL possible tickers ───
    # Use the full universe so saved values survive manual sector switches
    all_possible_drift = list(dict.fromkeys(
        [t for t in CORE_ASSETS] +
        all_sector_list +
        [hedge_ticker]
    ))
    holdings_js_keys = ", ".join(f'"{t}"' for t in all_possible_drift)
    st.components.v1.html(f"""
    <script>
    (function() {{
      const tickers = [{holdings_js_keys}];
      const params  = new URLSearchParams(window.parent.location.search);
      let changed   = false;
      tickers.forEach(t => {{
        const v  = localStorage.getItem("aw_drift_"  + t);
        const cb = localStorage.getItem("aw_cb_"     + t);
        const sh = localStorage.getItem("aw_shares_" + t);
        if (v  !== null && params.get("drift_"  + t) !== v)  {{ params.set("drift_"  + t, v);  changed = true; }}
        if (cb !== null && params.get("cb_"     + t) !== cb) {{ params.set("cb_"     + t, cb); changed = true; }}
        if (sh !== null && params.get("shares_" + t) !== sh) {{ params.set("shares_" + t, sh); changed = true; }}
      }});
      if (changed) window.parent.history.replaceState(null, "", "?" + params.toString());
    }})();
    </script>
    """, height=0)

    # ── Load saved values from query_params ────────────────────────────────
    def _load_float(key: str, default: float = 0.0) -> float:
        val = st.query_params.get(key, str(default))
        try:    return float(val)
        except: return default

    target_df["Current %"] = target_df["Ticker"].apply(
        lambda t: _load_float(f"drift_{t}", 0.0))
    target_df["Cost Basis"] = target_df["Ticker"].apply(
        lambda t: _load_float(f"cb_{t}", 0.0))
    target_df["Shares"] = target_df["Ticker"].apply(
        lambda t: _load_float(f"shares_{t}", 0.0))

    # ── Add live price and ATR stop for each ticker ────────────────────────
    def _live_price(ticker):
        if ticker in prices_all.columns:
            return float(prices_all[ticker].iloc[-1])
        return 0.0

    def _atr_stop(ticker):
        info = atr_data.get(ticker, {})
        return info.get("stop", 0.0)

    target_df["Live Price"] = target_df["Ticker"].apply(_live_price)
    target_df["ATR Stop"]   = target_df["Ticker"].apply(_atr_stop)

    # ── Editable table ─────────────────────────────────────────────────────
    drift_edit = st.data_editor(
        target_df[["Ticker", "Bucket", "Label", "Target %",
                   "Current %", "Shares", "Cost Basis"]],
        column_config={
            "Ticker":     st.column_config.TextColumn("Ticker",    disabled=True),
            "Bucket":     st.column_config.TextColumn("Bucket",    disabled=True),
            "Label":      st.column_config.TextColumn("Name",      disabled=True),
            "Target %":   st.column_config.NumberColumn("Target %", disabled=True, format="%.1f"),
            "Current %":  st.column_config.NumberColumn(
                "Current % ✏️", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"),
            "Shares":     st.column_config.NumberColumn(
                "Shares ✏️", min_value=0.0, step=0.01, format="%.2f",
                help="Shares held — fractional shares supported to 2 decimal places"),
            "Cost Basis": st.column_config.NumberColumn(
                "Cost Basis ✏️", min_value=0.0, step=0.01, format="$%.2f",
                help="Average cost per share (used for P&L and stop-loss monitoring)"),
        },
        use_container_width=True,
        hide_index=True,
        key="drift_editor",
    )

    # ── Save / status row ──────────────────────────────────────────────────
    save_col, status_col = st.columns([1, 3])
    with save_col:
        save_drift = st.button("💾  SAVE HOLDINGS", use_container_width=True, key="save_drift_btn")
    with status_col:
        has_saved = any(st.query_params.get(f"drift_{t}") for t in drift_tickers)
        if has_saved:
            st.markdown("""<div style="font-family:var(--mono);font-size:0.7rem;
                color:#10b981;padding-top:10px">💾 Showing saved holdings</div>""",
                unsafe_allow_html=True)
        else:
            st.markdown("""<div style="font-family:var(--mono);font-size:0.7rem;
                color:var(--muted);padding-top:10px">
                ⚙ No saved holdings — enter values above and save</div>""",
                unsafe_allow_html=True)

    if save_drift:
        for _, row in drift_edit.iterrows():
            t = row["Ticker"]
            st.query_params[f"drift_{t}"]  = str(row["Current %"])
            st.query_params[f"cb_{t}"]     = str(row["Cost Basis"])
            st.query_params[f"shares_{t}"] = str(row["Shares"])
        js_lines = "\n".join(
            f'localStorage.setItem("aw_drift_{r["Ticker"]}",  "{r["Current %"]}");'
            f'localStorage.setItem("aw_cb_{r["Ticker"]}",     "{r["Cost Basis"]}");'
            f'localStorage.setItem("aw_shares_{r["Ticker"]}", "{r["Shares"]}");'
            for _, r in drift_edit.iterrows()
        )
        st.components.v1.html(f"<script>{js_lines}</script>", height=0)
        st.success("✓ Holdings, shares, and cost bases saved.", icon="💾")

    # ── Drift + P&L + stop-loss calculations ──────────────────────────────
    drift_edit["Drift %"] = (drift_edit["Current %"] - drift_edit["Target %"]).round(2)
    drift_edit["Action"]  = drift_edit["Drift %"].apply(
        lambda d: "▲ BUY" if d < -1 else ("▼ SELL" if d > 1 else "✓ OK")
    )
    # Merge live price and ATR stop back in
    drift_edit["Live Price"] = target_df["Live Price"].values
    drift_edit["ATR Stop"]   = target_df["ATR Stop"].values

    # P&L per position
    def _pnl(row):
        cb    = row["Cost Basis"]
        px    = row["Live Price"]
        sh    = row["Shares"]
        if cb > 0 and px > 0 and sh > 0:
            return round((px - cb) * sh, 2)
        return None

    def _pnl_pct(row):
        cb = row["Cost Basis"]
        px = row["Live Price"]
        if cb > 0 and px > 0:
            return round((px - cb) / cb * 100, 2)
        return None

    def _stop_triggered(row):
        cb   = row["Cost Basis"]
        stop = row["ATR Stop"]
        px   = row["Live Price"]
        if cb > 0 and stop > 0 and px > 0:
            return px <= stop
        return False

    drift_edit["P&L $"]    = drift_edit.apply(_pnl, axis=1)
    drift_edit["P&L %"]    = drift_edit.apply(_pnl_pct, axis=1)
    drift_edit["Stopped"]  = drift_edit.apply(_stop_triggered, axis=1)

    # ── Stop-loss alerts (show before the detail rows) ────────────────────
    stopped_positions = drift_edit[drift_edit["Stopped"] == True]
    if not stopped_positions.empty:
        for _, sp in stopped_positions.iterrows():
            st.markdown(f"""
            <div style="background:rgba(239,68,68,0.10);border:1px solid rgba(239,68,68,0.4);
                        border-radius:8px;padding:12px 16px;margin-bottom:8px;
                        display:flex;align-items:center;gap:12px">
              <span style="font-size:1.4rem">🚨</span>
              <div>
                <div style="font-family:var(--mono);font-weight:700;color:#ef4444">
                  STOP-LOSS TRIGGERED — {sp['Ticker']}
                </div>
                <div style="font-size:0.78rem;color:var(--muted);margin-top:2px">
                  Live price <b style="color:#ef4444">${sp['Live Price']:.2f}</b>
                  has breached 2×ATR stop of
                  <b style="color:#ef4444">${sp['ATR Stop']:.2f}</b>.
                  Cost basis: ${sp['Cost Basis']:.2f} ·
                  P&L: <b style="color:#ef4444">${sp['P&L $']:,.0f}</b>
                  ({sp['P&L %']:+.1f}%)
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div style='margin-top:16px'>", unsafe_allow_html=True)
    for _, row in drift_edit.iterrows():
        drift  = row["Drift %"]
        action = row["Action"]
        col    = "#10b981" if action == "✓ OK" else ("#3b82f6" if "BUY" in action else "#ef4444")
        scale       = 40.0
        target_bar  = min(row["Target %"],  scale) / scale * 100
        current_bar = min(row["Current %"], scale) / scale * 100
        bucket_color = {"Core": "#3b82f6", "Tactical": "#10b981", "Hedge": "#f59e0b"}.get(row["Bucket"], "#64748b")

        # P&L display
        pnl_d   = row["P&L $"]
        pnl_pct = row["P&L %"]
        cb      = row["Cost Basis"]
        px      = row["Live Price"]
        stop    = row["ATR Stop"]
        stopped = row["Stopped"]

        has_cb = cb > 0 and px > 0

        st.markdown(f"""
        <div style="padding:14px 0 6px;border-bottom:{'none' if has_cb else '1px solid var(--border)'}">
          <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px">
            <b style="font-family:var(--mono);width:50px">{row['Ticker']}</b>
            <span style="font-size:0.68rem;color:{bucket_color};font-family:var(--mono);
                         background:rgba(255,255,255,0.05);padding:2px 7px;border-radius:3px;
                         border:1px solid {bucket_color}33">{row['Bucket']}</span>
            <span style="font-size:0.75rem;color:var(--muted);flex:1">{row['Label']}</span>
            <span style="font-family:var(--mono);font-size:0.8rem;font-weight:700;color:{col}">{action}</span>
            <span style="font-family:var(--mono);font-size:0.8rem;color:{col};
                         width:52px;text-align:right">{drift:+.1f}%</span>
          </div>
          <div style="display:flex;gap:10px;align-items:center;
                      font-size:0.68rem;color:var(--muted);margin-bottom:4px">
            <span style="width:52px;text-align:right">Target</span>
            <div style="flex:1;height:5px;background:var(--surface2);border-radius:3px">
              <div style="height:100%;width:{target_bar:.0f}%;background:#3b82f6;border-radius:3px"></div>
            </div>
            <span style="width:38px;text-align:right">{row['Target %']:.1f}%</span>
          </div>
          <div style="display:flex;gap:10px;align-items:center;font-size:0.68rem;color:var(--muted)">
            <span style="width:52px;text-align:right">Current</span>
            <div style="flex:1;height:5px;background:var(--surface2);border-radius:3px">
              <div style="height:100%;width:{current_bar:.0f}%;background:{col};border-radius:3px"></div>
            </div>
            <span style="width:38px;text-align:right">{row['Current %']:.1f}%</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # P&L strip — built entirely via Python string concat, NOT f-string interpolation
        # of HTML fragments. Any variable containing HTML tags must not be injected via {}.
        if has_cb:
            pnl_color  = "#10b981" if (pnl_d or 0) >= 0 else "#ef4444"
            stop_color = "#ef4444" if stopped else "var(--muted)"
            px_color   = "#10b981" if px >= cb else "#ef4444"

            parts = [
                '<div style="padding:6px 10px 14px;border-bottom:1px solid var(--border);'
                'display:flex;gap:16px;flex-wrap:wrap;align-items:center;'
                'font-family:var(--mono);font-size:0.7rem;'
                'background:rgba(255,255,255,0.02);border-radius:0 0 4px 4px">',
            ]
            if stopped:
                parts.append(
                    '<span style="background:rgba(239,68,68,0.15);color:#ef4444;'
                    'font-family:var(--mono);font-size:0.6rem;padding:1px 6px;'
                    'border-radius:3px;border:1px solid rgba(239,68,68,0.3)">🚨 STOPPED</span>'
                )
            parts += [
                f'<span style="color:var(--muted)">Cost: <b style="color:var(--text)">${cb:.2f}</b></span>',
                f'<span style="color:var(--muted)">Price: <b style="color:{px_color}">${px:.2f}</b></span>',
                f'<span style="color:var(--muted)">P&amp;L: <b style="color:{pnl_color}">${pnl_d:,.0f} ({pnl_pct:+.1f}%)</b></span>',
                f'<span style="color:{stop_color}">Stop: ${stop:.2f}</span>',
                '</div>',
            ]
            st.markdown("".join(parts), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ── Summary footer ─────────────────────────────────────────────────────
    total_drift = drift_edit["Drift %"].abs().sum()
    buys  = drift_edit[drift_edit["Action"] == "▲ BUY"]["Ticker"].tolist()
    sells = drift_edit[drift_edit["Action"] == "▼ SELL"]["Ticker"].tolist()
    drift_color = "#10b981" if total_drift < 5 else "#f59e0b" if total_drift < 15 else "#ef4444"
    drift_msg   = "✓ Within tolerance" if total_drift < 5 else "⚠ Rebalance recommended" if total_drift < 15 else "🚨 Immediate rebalance required"
    buys_html  = " ".join(f'<span style="background:rgba(59,130,246,0.15);color:#3b82f6;font-family:var(--mono);font-size:0.65rem;padding:2px 7px;border-radius:3px">{t}</span>' for t in buys)  or "—"
    sells_html = " ".join(f'<span style="background:rgba(239,68,68,0.12);color:#ef4444;font-family:var(--mono);font-size:0.65rem;padding:2px 7px;border-radius:3px">{t}</span>' for t in sells) or "—"
    st.markdown(f"""
    <div style="margin-top:20px;padding:16px 20px;background:var(--surface2);
                border:1px solid var(--border);border-radius:8px;">
      <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center">
        <div>
          <div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                      letter-spacing:1px;margin-bottom:4px">TOTAL DRIFT</div>
          <div style="font-family:var(--mono);font-size:1.3rem;font-weight:700;
                      color:{drift_color}">{total_drift:.1f}%</div>
          <div style="font-size:0.75rem;color:{drift_color};margin-top:2px">{drift_msg}</div>
        </div>
        <div style="flex:1;min-width:160px">
          <div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                      letter-spacing:1px;margin-bottom:6px">▲ BUY</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">{buys_html}</div>
        </div>
        <div style="flex:1;min-width:160px">
          <div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                      letter-spacing:1px;margin-bottom:6px">▼ SELL</div>
          <div style="display:flex;gap:4px;flex-wrap:wrap">{sells_html}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ─── TAB 4 — GLIDE PATH ──────────────────────────────────────────────────────
with tab4:
    st.markdown('<div class="aw-card">', unsafe_allow_html=True)
    st.markdown('<div class="aw-card-title">🗺 Glide Path — Asset Composition by Life Stage</div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="font-size:0.8rem;color:var(--muted);margin-bottom:24px">
      As your time horizon shrinks, shift the core bucket composition rightward.
      The tactical and hedge buckets remain unchanged throughout. Your current stage is highlighted.
    </div>
    """, unsafe_allow_html=True)

    # Bug fix: pre-define rgba values per stage — hex-to-rgb conversion was failing silently
    stage_colors = ["#10b981", "#3b82f6", "#f59e0b", "#f97316", "#ef4444"]
    stage_bgs    = [
        "rgba(16,185,129,0.10)",
        "rgba(59,130,246,0.10)",
        "rgba(245,158,11,0.10)",
        "rgba(249,115,22,0.10)",
        "rgba(239,68,68,0.10)",
    ]

    for i, (stage, cfg) in enumerate(GLIDE_PRESETS.items()):
        is_current = stage == glide_choice
        border_col = stage_colors[i]
        bg         = stage_bgs[i] if is_current else "var(--surface2)"
        border     = border_col   if is_current else "var(--border)"
        assets     = cfg["assets"]

        equity_a = [a for a in assets if a in ["VOO", "VEA", "VWO"]]
        bond_a   = [a for a in assets if a in ["TLT", "IEF"]]
        alt_a    = [a for a in assets if a in ["GLD", "GSG"]]
        n        = len(assets)
        eq_w     = len(equity_a) / n * 100
        bond_w   = len(bond_a)   / n * 100
        alt_w    = len(alt_a)    / n * 100
        label_color = "var(--text)" if is_current else "var(--muted)"
        assets_str  = "→".join(assets)

        # ── Card open + header row ─────────────────────────────────────────
        st.markdown(f"""
        <div style="padding:18px 20px 10px;background:{bg};border:1px solid {border};
                    border-radius:8px 8px 0 0;margin-bottom:0">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
            <div style="display:flex;align-items:center;gap:8px">
              <b style="font-family:var(--mono);font-size:0.85rem;color:{label_color}">{stage}</b>
              {"" if not is_current else f'<span style="background:{border_col};color:white;font-family:var(--mono);font-size:0.6rem;padding:2px 8px;border-radius:3px;letter-spacing:1px">CURRENT</span>'}
            </div>
            <div style="font-size:0.75rem;color:var(--muted)">{assets_str}</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Bar + legend row — separate call so ■ color spans render cleanly ─
        st.markdown(f"""
        <div style="padding:0 20px 16px;background:{bg};border:1px solid {border};
                    border-top:none;border-radius:0 0 8px 8px;margin-bottom:12px">
          <div style="height:10px;border-radius:5px;overflow:hidden;display:flex;margin-bottom:10px">
            <div style="width:{eq_w:.1f}%;background:#10b981"></div>
            <div style="width:{bond_w:.1f}%;background:#3b82f6"></div>
            <div style="width:{alt_w:.1f}%;background:#f59e0b"></div>
          </div>
          <div style="display:flex;gap:16px;font-size:0.7rem;color:var(--muted);font-family:var(--mono);flex-wrap:wrap">
            <span><span style="color:#10b981">■</span> Equity {eq_w:.0f}%</span>
            <span><span style="color:#3b82f6">■</span> Bonds {bond_w:.0f}%</span>
            <span><span style="color:#f59e0b">■</span> Alts {alt_w:.0f}%</span>
            <span style="margin-left:auto;font-style:italic;color:var(--muted)">{cfg['description']}</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:20px;padding:16px 20px;background:rgba(139,92,246,0.08);
                border:1px solid rgba(139,92,246,0.25);border-radius:8px;
                font-size:0.8rem;color:var(--muted)">
      <b style="color:#8b5cf6;font-family:var(--mono)">HOW TO USE THIS</b><br><br>
      The glide path is a manual decision — there is no automatic trigger. Revisit your life stage
      selection every 5–10 years, or after major life events (marriage, dependents, income change).
      The tactical and hedge buckets <b style="color:var(--text)">stay at 30% / 10%</b> regardless of
      life stage — only the core composition changes. When you shift stages, rebalance the core
      bucket gradually over 2–3 quarters to avoid large tax events from selling positions at once.
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


with tab5:
    st.markdown('<div class="aw-card">', unsafe_allow_html=True)
    st.markdown('<div class="aw-card-title">📡 Technical Sentiment Radar — RSI · SMA · Volume</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.8rem;color:var(--muted);margin-bottom:16px">
      Sentiment derived from <b>price action and volume</b> — no external API dependency.
      Signals: RSI-14 (40%), price vs 20d SMA (40%), volume trend 5d/20d (20%).
      Scored against current tactical tilts: <b style="color:#10b981">{', '.join(top3)}</b>.
    </div>
    <div style="display:inline-flex;align-items:center;gap:8px;margin-bottom:20px;
                padding:6px 12px;background:rgba(16,185,129,0.08);
                border:1px solid rgba(16,185,129,0.2);border-radius:5px">
      <span style="color:#10b981;font-family:var(--mono);font-size:0.65rem;letter-spacing:1px">
        ● TECHNICAL SIGNALS
      </span>
      <span style="font-size:0.68rem;color:var(--muted)">computed from yfinance price + volume · refreshes hourly</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Conviction score: blend momentum rank + technical sentiment ────────
    momentum_rank = {t: i for i, t in enumerate(sector_returns.index)}
    n_sectors     = len(momentum_rank)
    all_sector_tickers = list(SECTOR_ETFS.keys())

    conviction = {}
    for ticker in all_sector_tickers:
        mom_score  = 1.0 - (momentum_rank.get(ticker, n_sectors) / n_sectors)
        sent       = sentiment_data.get(ticker, {})
        sent_norm  = sent.get("norm", 0.0)
        sent_score = (sent_norm + 1) / 2                  # rescale -1…+1 → 0…1
        combined   = round(0.60 * mom_score + 0.40 * sent_score, 3)
        conviction[ticker] = {
            "momentum_score":  round(mom_score,  3),
            "sentiment_score": round(sent_score, 3),
            "combined":        combined,
            "recommendation":  "STRONG HOLD" if combined > 0.70
                               else "HOLD"    if combined > 0.55
                               else "MONITOR" if combined > 0.40
                               else "REDUCE",
        }

    badge_map = {
        "technical":   ("TECHNICAL", "#10b981"),
        "unavailable": ("NO DATA",   "#ef4444"),
    }

    # ── Detailed cards for current tactical positions ──────────────────────
    st.markdown("""
    <div style="font-family:var(--mono);font-size:0.65rem;letter-spacing:2px;
                text-transform:uppercase;color:var(--muted);margin-bottom:12px">
      Current Tactical Position Conviction
    </div>
    """, unsafe_allow_html=True)

    for ticker in top3:
        g   = sentiment_data.get(ticker, {})
        c   = conviction[ticker]
        rec = c["recommendation"]
        rec_color = {
            "STRONG HOLD": "#10b981", "HOLD": "#3b82f6",
            "MONITOR": "#f59e0b",     "REDUCE": "#ef4444",
        }.get(rec, "#64748b")

        norm       = g.get("norm", 0.0)
        tone_color = "#10b981" if norm > 0.1 else ("#ef4444" if norm < -0.1 else "#64748b")
        bar_w      = int(c["combined"] * 100)
        mom_bar    = int(c["momentum_score"] * 100)
        sent_bar   = int(c["sentiment_score"] * 100)
        aligned    = "✓ regime" if ticker in quad_preferred else "↑ momentum"
        aligned_c  = "var(--accent)" if ticker in quad_preferred else "var(--accent3)"

        rsi      = g.get("rsi")
        sma_pct  = g.get("sma_pct")
        vol_ratio= g.get("vol_ratio")
        rsi_str     = f"{rsi:.1f}" if rsi is not None else "—"
        sma_str     = f"{sma_pct:+.2f}%" if sma_pct is not None else "—"
        vol_str     = f"{vol_ratio:.2f}×" if vol_ratio is not None else "—"
        rsi_c    = "#10b981" if (rsi or 50) > 60 else ("#ef4444" if (rsi or 50) < 40 else "#64748b")
        sma_c    = "#10b981" if (sma_pct or 0) > 0 else "#ef4444"
        vol_c    = "#10b981" if (vol_ratio or 1) > 1.1 else ("#ef4444" if (vol_ratio or 1) < 0.9 else "#64748b")

        # PCR for this ticker
        pcr = pcr_data.get(ticker)
        pcr_str   = f"{pcr:.2f}" if pcr is not None else "—"
        pcr_color = "#ef4444" if (pcr or 0) > 1.0 else ("#10b981" if (pcr or 0) < 0.7 else "#64748b")

        src_label, src_color = badge_map.get(g.get("source", "unavailable"), ("N/A", "#64748b"))

        st.markdown(f"""
        <div style="padding:18px 20px;background:var(--surface2);border:1px solid var(--border);
                    border-left:3px solid {rec_color};border-radius:8px;margin-bottom:12px">
          <div style="display:flex;align-items:flex-start;justify-content:space-between;
                      margin-bottom:14px;gap:12px;flex-wrap:wrap">
            <div>
              <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
                <b style="font-family:var(--mono);font-size:1.05rem">{ticker}</b>
                <span style="font-size:0.75rem;color:var(--muted)">{SECTOR_ETFS.get(ticker,'')}</span>
                <span style="font-size:0.65rem;color:{aligned_c};font-family:var(--mono)">{aligned}</span>
              </div>
              <div style="display:flex;gap:16px;font-size:0.72rem;flex-wrap:wrap">
                <span>RSI-14: <b style="color:{rsi_c}">{rsi_str}</b></span>
                <span>vs SMA20: <b style="color:{sma_c}">{sma_str}</b></span>
                <span>Rel Vol: <b style="color:{vol_c}">{vol_str}</b></span>
                <span>P/C: <b style="color:{pcr_color}">{pcr_str}</b></span>
                <span style="color:{src_color};font-family:var(--mono);font-size:0.62rem">{src_label}</span>
              </div>
            </div>
            <div style="text-align:right">
              <div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                          letter-spacing:1px;margin-bottom:4px">CONVICTION</div>
              <div style="font-family:var(--mono);font-size:1.4rem;font-weight:700;
                          color:{rec_color}">{bar_w}</div>
              <div style="font-family:var(--mono);font-size:0.65rem;color:{rec_color};
                          letter-spacing:1px">{rec}</div>
            </div>
          </div>

          <div style="margin-bottom:6px">
            <div style="display:flex;justify-content:space-between;font-size:0.65rem;
                        color:var(--muted);font-family:var(--mono);margin-bottom:3px">
              <span>Combined conviction</span><span>{bar_w}/100</span>
            </div>
            <div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px">
              <div style="height:100%;width:{bar_w}%;background:{rec_color};border-radius:3px"></div>
            </div>
          </div>
          <div style="display:flex;gap:12px">
            <div style="flex:1">
              <div style="display:flex;justify-content:space-between;font-size:0.62rem;
                          color:var(--muted);font-family:var(--mono);margin-bottom:3px">
                <span>Momentum (60%)</span><span>{mom_bar}</span>
              </div>
              <div style="height:4px;background:rgba(255,255,255,0.05);border-radius:2px">
                <div style="height:100%;width:{mom_bar}%;background:#3b82f6;border-radius:2px"></div>
              </div>
            </div>
            <div style="flex:1">
              <div style="display:flex;justify-content:space-between;font-size:0.62rem;
                          color:var(--muted);font-family:var(--mono);margin-bottom:3px">
                <span>Technical (40%)</span><span>{sent_bar}</span>
              </div>
              <div style="height:4px;background:rgba(255,255,255,0.05);border-radius:2px">
                <div style="height:100%;width:{sent_bar}%;background:{tone_color};border-radius:2px"></div>
              </div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)

    # ── Full sector scan ───────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family:var(--mono);font-size:0.65rem;letter-spacing:2px;
                text-transform:uppercase;color:var(--muted);margin:24px 0 8px">
      Full Sector Scan
    </div>
    <div style="display:flex;gap:16px;padding:6px 0 8px;border-bottom:1px solid var(--border);
                font-family:var(--mono);font-size:0.58rem;color:var(--muted);
                letter-spacing:1px;text-transform:uppercase">
      <div style="width:46px">ETF</div>
      <div style="width:110px">Sector</div>
      <div style="flex:1">Conviction bar</div>
      <div style="width:34px;text-align:right">Score</div>
      <div style="width:52px;text-align:right">3M Ret</div>
      <div style="width:52px;text-align:right">RSI</div>
      <div style="width:52px;text-align:right">Rel Vol</div>
      <div style="width:60px;text-align:right">P/C</div>
      <div style="width:76px;text-align:right">Signal</div>
    </div>
    """, unsafe_allow_html=True)

    sorted_sectors = sorted(all_sector_tickers,
                            key=lambda t: conviction[t]["combined"], reverse=True)

    for ticker in sorted_sectors:
        g   = sentiment_data.get(ticker, {})
        c   = conviction[ticker]
        rec = c["recommendation"]
        is_selected = ticker in top3
        rec_color = {
            "STRONG HOLD": "#10b981", "HOLD": "#3b82f6",
            "MONITOR": "#f59e0b",     "REDUCE": "#ef4444",
        }.get(rec, "#64748b")

        norm      = g.get("norm", 0.0)
        tone_color= "#10b981" if norm > 0.1 else ("#ef4444" if norm < -0.1 else "#64748b")
        ret       = sector_returns[ticker] if ticker in sector_returns.index else 0.0
        ret_c     = "#10b981" if ret >= 0 else "#ef4444"
        bar_w     = int(c["combined"] * 100)
        rsi       = g.get("rsi")
        vol_ratio = g.get("vol_ratio")
        pcr       = pcr_data.get(ticker)

        rsi_str = f"{rsi:.0f}" if rsi is not None else "—"
        rsi_c   = "#10b981" if (rsi or 50) > 60 else ("#ef4444" if (rsi or 50) < 40 else "var(--muted)")
        vr_str  = f"{vol_ratio:.2f}×" if vol_ratio is not None else "—"
        vr_c    = "#10b981" if (vol_ratio or 1) > 1.1 else ("#ef4444" if (vol_ratio or 1) < 0.9 else "var(--muted)")
        pcr_str = f"{pcr:.2f}" if pcr is not None else "—"
        pcr_c   = "#ef4444" if (pcr or 0) > 1.0 else ("#10b981" if (pcr or 0) < 0.7 else "var(--muted)")

        sel_badge = ('<span style="background:#10b981;color:#0a0c10;font-family:var(--mono);'
                     'font-size:0.58rem;padding:1px 6px;border-radius:3px;'
                     'font-weight:700;margin-left:4px">TAC</span>') if is_selected else ""

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:16px;padding:9px 0;
                    border-bottom:1px solid var(--border)">
          <div style="width:46px;font-family:var(--mono);font-size:0.82rem;
                      font-weight:700;color:{'var(--text)' if is_selected else 'var(--muted)'}">{ticker}</div>
          <div style="width:110px;font-size:0.7rem;color:var(--muted)">
            {SECTOR_ETFS.get(ticker,'')} {sel_badge}
          </div>
          <div style="flex:1;height:5px;background:var(--surface2);border-radius:3px">
            <div style="height:100%;width:{bar_w}%;background:{rec_color};border-radius:3px;
                        opacity:{'1' if is_selected else '0.55'}"></div>
          </div>
          <div style="width:34px;text-align:right;font-family:var(--mono);font-size:0.75rem;
                      color:{rec_color}">{bar_w}</div>
          <div style="width:52px;text-align:right;font-family:var(--mono);font-size:0.72rem;
                      color:{ret_c}">{ret*100:+.1f}%</div>
          <div style="width:52px;text-align:right;font-family:var(--mono);font-size:0.72rem;
                      color:{rsi_c}">{rsi_str}</div>
          <div style="width:52px;text-align:right;font-family:var(--mono);font-size:0.72rem;
                      color:{vr_c}">{vr_str}</div>
          <div style="width:60px;text-align:right;font-family:var(--mono);font-size:0.72rem;
                      color:{pcr_c}">{pcr_str}</div>
          <div style="width:76px;text-align:right;font-family:var(--mono);font-size:0.65rem;
                      color:{rec_color};letter-spacing:0.5px">{rec}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div style="margin-top:20px;padding:16px 20px;background:rgba(59,130,246,0.06);
                border:1px solid rgba(59,130,246,0.15);border-radius:8px;
                font-size:0.77rem;color:var(--muted);line-height:1.6">
      <b style="color:#3b82f6;font-family:var(--mono)">METHODOLOGY</b><br><br>
      <b style="color:var(--text)">Conviction</b> = 60% 3-month momentum rank + 40% technical sentiment.
      <b style="color:var(--text)">Technical sentiment</b> = 40% RSI-14 + 40% price vs 20d SMA + 20% relative volume (5d/20d).
      All signals computed from price/volume data already fetched — no external API calls.
      <b style="color:var(--text)">P/C ratio</b> from yfinance options chains (nearest 2 expirations); shown as context only, not included in conviction score.
      <br><br>
      <b style="color:var(--text)">Thresholds:</b>
      STRONG HOLD ≥ 70 · HOLD 55–70 · MONITOR 40–55 · REDUCE &lt; 40
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


st.markdown(f"""
<div style="margin-top:40px;padding-top:20px;border-top:1px solid var(--border);
            text-align:center;font-family:var(--mono);font-size:0.65rem;color:var(--muted)">
  PROJECT ALL-WEATHER · Risk Parity + Pure Alpha Framework ·
  Data via yfinance & FRED · Not financial advice ·
  {datetime.now().strftime('%Y')}
</div>
""", unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
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
def fetch_price_data(tickers: list, period: str = "1y") -> pd.DataFrame:
    try:
        data = yf.download(tickers, period=period, auto_adjust=True, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            df = data["Close"]
        else:
            df = data[["Close"]].rename(columns={"Close": tickers[0]})
        if df.empty or df.isnull().all().all():
            raise ValueError("Empty response")
        return df
    except Exception:
        st.warning("⚠ Live market data unavailable — running in **Demo Mode** with synthetic prices. "
                   "Deploy locally or on Streamlit Cloud to enable real-time data.", icon="🔌")
        return _make_demo_prices(tickers)

@st.cache_data(ttl=3600)
def fetch_fred_macro():
    """Pull GDP and CPI trend from FRED via direct HTTP (no API key required for these series)."""
    import urllib.request, json
    
    def fred_series(series_id):
        url = (f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
               f"&vintage_date={datetime.today().strftime('%Y-%m-%d')}")
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                lines = r.read().decode().strip().split('\n')
            rows = [l.split(',') for l in lines[1:] if '.' in l]
            dates = [r[0] for r in rows]
            vals  = [float(r[1]) for r in rows]
            return pd.Series(vals, index=pd.to_datetime(dates)).dropna().tail(8)
        except Exception:
            return None

    gdp = fred_series("GDP")
    cpi = fred_series("CPIAUCSL")

    gdp_trend = "rising"   # safe defaults (expansion is more common baseline)
    cpi_trend = "falling"
    gdp_vals  = cpi_vals  = []

    if gdp is not None and len(gdp) >= 2:
        gdp_trend = "rising" if gdp.iloc[-1] > gdp.iloc[-2] else "falling"
        gdp_vals  = gdp.tolist()
    if cpi is not None and len(cpi) >= 2:
        lookback = min(5, len(cpi) - 1)
        cpi_trend = "rising" if cpi.iloc[-1] > cpi.iloc[-lookback] else "falling"
        cpi_vals  = cpi.tolist()

    return gdp_trend, cpi_trend, gdp_vals, cpi_vals

# Sector → search keywords for GDELT headline matching
SECTOR_KEYWORDS = {
    "XLE":  ["energy", "oil", "gas", "petroleum", "OPEC", "crude"],
    "XLK":  ["technology", "semiconductor", "AI", "software", "chip", "tech"],
    "XLV":  ["healthcare", "pharma", "biotech", "drug", "FDA", "hospital"],
    "XLF":  ["bank", "finance", "interest rate", "Fed", "credit", "lending"],
    "XLI":  ["industrial", "manufacturing", "defense", "aerospace", "infrastructure"],
    "XLY":  ["consumer", "retail", "spending", "discretionary", "e-commerce"],
    "XLP":  ["staples", "grocery", "food", "beverage", "household", "consumer goods"],
    "XLB":  ["materials", "mining", "steel", "copper", "chemical", "commodity"],
    "XLC":  ["media", "telecom", "streaming", "advertising", "social", "communication"],
    "XLU":  ["utility", "electricity", "power grid", "renewable", "water"],
    "XLRE": ["real estate", "REIT", "housing", "mortgage", "property"],
}

@st.cache_data(ttl=1800)
def fetch_gdelt_sentiment(tickers: tuple) -> dict:
    """
    Pull news sentiment for each sector using two approaches in order:

    1. GDELT GKG Timeline API  (/api/v2/tv/tv  mode=timelinetone)
       — Returns pre-aggregated avg tone over a time window; not IP-blocked.
    2. RSS headline scrape via Google News (fallback)
       — Counts positive/negative financial keywords in titles.

    Returns: {ticker: {score, norm, count, tone_label, headlines, error, source}}
    Tone: negative = bearish, positive = bullish. Typical range ±8.
    norm: rescaled to -1…+1 for bar display.
    """
    import urllib.request, urllib.parse, json, re
    from datetime import datetime, timedelta

    # ── Positive / negative keyword lexicon for RSS fallback ──────────────
    POS_WORDS = {"surges","rises","gains","record","beat","strong","growth",
                 "rally","upgrade","outperform","boom","breakthrough","positive",
                 "profit","expands","climbs","bullish","advances","soars"}
    NEG_WORDS = {"falls","drops","decline","miss","weak","loss","cut","downgrade",
                 "risk","concern","slowdown","crisis","bearish","plunges","crash",
                 "warning","threat","lower","contraction","disappoints","deficit"}

    def _gdelt_timeline(query: str) -> float | None:
        """
        Hit the GDELT GKG 2.0 timeline tone endpoint.
        Returns avg tone float or None on failure.
        """
        params = urllib.parse.urlencode({
            "query":    query,
            "mode":     "timelineTone",
            "format":   "json",
            "timespan": "7d",
            "sourcelang": "english",
        })
        url = f"https://api.gdeltproject.org/api/v2/doc/doc?{params}"
        req = urllib.request.Request(url, headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://gdeltproject.org/",
        })
        with urllib.request.urlopen(req, timeout=12) as r:
            data = json.loads(r.read().decode("utf-8", errors="ignore"))

        # Response shape: {"timeline":[{"data":[{"value": float}, ...]}]}
        timeline = data.get("timeline", [])
        if not timeline:
            return None
        tone_series = timeline[0].get("data", [])
        values = [pt["value"] for pt in tone_series if pt.get("value") is not None]
        if not values:
            return None
        return sum(values) / len(values)

    def _rss_fallback(keywords: list) -> tuple[float, list]:
        """
        Fetch Google News RSS for the top keyword, score headlines via lexicon.
        Returns (avg_tone_estimate, headlines_list).
        Tone is estimated: +1 per positive word, -1 per negative word, averaged.
        Scaled to GDELT-like range by multiplying by 3.
        """
        kw = urllib.parse.quote(keywords[0])
        url = f"https://news.google.com/rss/search?q={kw}+stock+market&hl=en-US&gl=US&ceid=US:en"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; RSS reader)"
        })
        with urllib.request.urlopen(req, timeout=10) as r:
            xml = r.read().decode("utf-8", errors="ignore")

        # Extract titles with simple regex — no lxml needed
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", xml)
        if not titles:
            titles = re.findall(r"<title>(.*?)</title>", xml)
        titles = [t for t in titles if len(t) > 15][:15]  # skip feed-level title

        scores = []
        for title in titles:
            words  = set(title.lower().split())
            score  = sum(1 for w in words if w in POS_WORDS) \
                   - sum(1 for w in words if w in NEG_WORDS)
            scores.append(score)

        avg = (sum(scores) / len(scores) * 3.0) if scores else 0.0
        headlines = [{"title": t, "url": ""} for t in titles[:5]]
        return avg, headlines

    results = {}

    for ticker in tickers:
        keywords = SECTOR_KEYWORDS.get(ticker, [ticker])
        # Primary query: top two keywords joined with OR
        query = " OR ".join(f'"{k}"' for k in keywords[:2])
        score     = None
        headlines = []
        source    = "gdelt"
        error     = None

        # ── Attempt 1: GDELT timeline tone ────────────────────────────────
        try:
            score = _gdelt_timeline(query)
            if score is None:
                raise ValueError("empty timeline")
            source = "gdelt"
        except Exception as e1:
            error = f"GDELT: {e1}"
            # ── Attempt 2: RSS keyword fallback ───────────────────────────
            try:
                score, headlines = _rss_fallback(keywords)
                source = "rss"
                error  = None
            except Exception as e2:
                score  = 0.0
                source = "unavailable"
                error  = f"GDELT: {e1} | RSS: {e2}"

        score = score or 0.0
        norm  = round(max(-1.0, min(1.0, score / 8.0)), 3)

        results[ticker] = {
            "score":      round(float(score), 2),
            "norm":       norm,
            "count":      len(headlines) if headlines else (1 if source == "gdelt" else 0),
            "tone_label": "Bullish" if norm > 0.1 else ("Bearish" if norm < -0.1 else "Neutral"),
            "headlines":  headlines[:5],
            "source":     source,
            "error":      error,
        }

    return results

def compute_volatility_weights(prices: pd.DataFrame) -> pd.Series:
    log_ret = np.log(prices / prices.shift(1)).dropna()
    vols    = log_ret.tail(30).std() * np.sqrt(252)
    vols    = vols.replace(0, np.nan).dropna()
    inv_vol = 1 / vols
    return inv_vol / inv_vol.sum()

def compute_atr(prices: pd.DataFrame, ticker: str, window: int = 14) -> float:
    try:
        raw = yf.download(ticker, period="3mo", auto_adjust=True, progress=False)
        if raw.empty:
            return 0.0
        hi = raw["High"].squeeze()
        lo = raw["Low"].squeeze()
        cl = raw["Close"].squeeze()
        tr = pd.concat([hi - lo,
                        (hi - cl.shift()).abs(),
                        (lo - cl.shift()).abs()], axis=1).max(axis=1)
        return tr.rolling(window).mean().iloc[-1]
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

    core_pct     = st.slider("Core Equity %",        40, 80, _core_pct_default,     5)
    tactical_pct = st.slider("Tactical Pure Alpha %", 10, 40, _tactical_pct_default, 5)
    hedge_pct    = 100 - core_pct - tactical_pct
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
        prices_all = fetch_price_data(all_tickers, period="1y")
        # ensure all expected columns present
        available   = [t for t in all_tickers if t in prices_all.columns]
        prices_all  = prices_all[available].ffill()
        data_ok     = True
    except Exception as e:
        st.error(f"Data fetch failed: {e}")
        data_ok = False

    gdp_trend, cpi_trend, gdp_vals, cpi_vals = fetch_fred_macro()

if not data_ok:
    st.stop()

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

sector_prices = prices_all[[t for t in SECTOR_ETFS if t in prices_all.columns]]
three_mo_ago  = sector_prices.index[-1] - timedelta(days=90)
start_prices  = sector_prices[sector_prices.index >= three_mo_ago].iloc[0]
end_prices    = sector_prices.iloc[-1]
sector_returns= ((end_prices - start_prices) / start_prices).sort_values(ascending=False)

# Prefer quadrant-aligned; fill remainder with momentum leaders
preferred_available = [t for t in quad_preferred if t in sector_returns.index]
top_momentum        = [t for t in sector_returns.index if t not in preferred_available]
top3 = (preferred_available + top_momentum)[:3]

tactical_alloc_pct  = tactical_pct / 100
tactical_per_sector = tactical_alloc_pct / 3

# ══════════════════════════════════════════════════════════════════════════════
# PART 3 — TAIL RISK HEDGE
# ══════════════════════════════════════════════════════════════════════════════

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
def get_atrs(tickers, _prices: pd.DataFrame):
    """_prices prefixed with _ so st.cache_data skips hashing the DataFrame."""
    result = {}
    for t in tickers:
        px      = _prices[t].iloc[-1] if t in _prices.columns else 0
        atr_val = compute_atr(_prices, t)
        stop    = float(px) - 2 * float(atr_val)
        result[t] = {"price": float(px), "atr": float(atr_val), "stop": stop}
    return result

atr_data = get_atrs(tuple(top3), prices_all)

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

        rows = []
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
            rows.append({"Ticker": ticker, "Weight": f"{w*100:.1f}%",
                         "$ Alloc": f"${dollar:,.0f}", "Shares": shares,
                         "Price": f"${px:.2f}", "30d Vol": f"{vol*100:.1f}%"})
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
            dollar = total_inv * tactical_per_sector
            shares, px = calc_shares(ticker, dollar)
            ret    = sector_returns[ticker] if ticker in sector_returns.index else 0.0
            atr_info = atr_data.get(ticker, {"atr": 0, "stop": 0, "price": px})
            aligned  = "✓ regime" if ticker in quad_preferred else "↑ momentum"
            ret_color = "#10b981" if ret >= 0 else "#ef4444"

            st.markdown(f"""
            <div style="padding:14px;background:var(--surface2);border:1px solid var(--border);
                        border-radius:6px;margin-bottom:12px">
              <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                <div>
                  <b style="font-family:var(--mono);font-size:1rem">{ticker}</b>
                  <span style="font-size:0.75rem;color:var(--muted);margin-left:8px">{SECTOR_ETFS.get(ticker,'')}</span>
                </div>
                <span style="font-family:var(--mono);color:{ret_color};font-size:0.9rem">
                  {ret*100:+.1f}%
                </span>
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
                <span style="font-size:0.7rem;color:var(--muted)">
                  2×ATR (${atr_info['atr']:.2f})
                </span>
                <span style="margin-left:auto;font-size:0.65rem;
                             color:{'var(--accent)' if aligned=='✓ regime' else 'var(--accent3)'};
                             font-family:var(--mono)">{aligned}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

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
    st.markdown('<div class="aw-card-title">📈 S&P 500 Sector 3-Month Momentum Ranking</div>', unsafe_allow_html=True)

    momentum_df = pd.DataFrame({
        "Ticker": sector_returns.index,
        "Sector": [SECTOR_ETFS.get(t, t) for t in sector_returns.index],
        "3M Return": sector_returns.values,
        "Selected": ["✓" if t in top3 else "" for t in sector_returns.index],
        "Regime Aligned": ["✓" if t in quad_preferred else "" for t in sector_returns.index],
    })

    for _, row in momentum_df.iterrows():
        ret   = row["3M Return"]
        bar_w = min(abs(ret) * 200, 100)
        bar_c = "#10b981" if ret >= 0 else "#ef4444"
        sel_badge = '<span style="background:#3b82f6;color:white;padding:2px 7px;border-radius:3px;font-size:0.65rem;font-family:var(--mono)">SELECTED</span>' if row["Selected"] else ""
        ra_badge  = '<span style="background:rgba(167,139,250,0.2);color:#a78bfa;padding:2px 7px;border-radius:3px;font-size:0.65rem;font-family:var(--mono);border:1px solid rgba(167,139,250,0.3)">REGIME</span>' if row["Regime Aligned"] else ""

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:16px;padding:10px 0;
                    border-bottom:1px solid var(--border)">
          <div style="font-family:var(--mono);font-weight:700;width:48px;color:var(--text)">{row['Ticker']}</div>
          <div style="flex:1;font-size:0.8rem;color:var(--muted)">{row['Sector']}</div>
          <div style="width:160px">
            <div style="height:5px;background:var(--surface2);border-radius:2px;overflow:hidden">
              <div style="height:100%;width:{bar_w}%;background:{bar_c};border-radius:2px"></div>
            </div>
          </div>
          <div style="font-family:var(--mono);font-size:0.85rem;width:60px;text-align:right;
                      color:{bar_c}">{ret*100:+.1f}%</div>
          <div style="width:140px;display:flex;gap:6px;justify-content:flex-end">
            {sel_badge}{ra_badge}
          </div>
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
    for ticker in top3:
        target_rows.append({
            "Ticker":   ticker,
            "Bucket":   "Tactical",
            "Label":    SECTOR_ETFS.get(ticker, ticker),
            "Target %": round(tactical_per_sector * 100, 2),
        })
    target_rows.append({
        "Ticker":   hedge_ticker,
        "Bucket":   "Hedge",
        "Label":    HEDGE_ASSETS.get(hedge_ticker, hedge_ticker),
        "Target %": float(hedge_pct),
    })

    target_df     = pd.DataFrame(target_rows)
    drift_tickers = target_df["Ticker"].tolist()

    # ── JS: on page load push any saved localStorage values into URL params ─
    holdings_js_keys = ", ".join(f'"{t}"' for t in drift_tickers)
    st.components.v1.html(f"""
    <script>
    (function() {{
      const tickers = [{holdings_js_keys}];
      const params  = new URLSearchParams(window.parent.location.search);
      let changed   = false;
      tickers.forEach(t => {{
        const v = localStorage.getItem("aw_drift_" + t);
        if (v !== null && params.get("drift_" + t) !== v) {{
          params.set("drift_" + t, v);
          changed = true;
        }}
      }});
      if (changed) {{
        window.parent.history.replaceState(null, "", "?" + params.toString());
      }}
    }})();
    </script>
    """, height=0)

    # ── Load saved Current % from query_params ─────────────────────────────
    def _load_holding(ticker: str) -> float:
        val = st.query_params.get(f"drift_{ticker}", "0.0")
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    target_df["Current %"] = target_df["Ticker"].apply(_load_holding)

    # ── Editable table ─────────────────────────────────────────────────────
    drift_edit = st.data_editor(
        target_df[["Ticker", "Bucket", "Label", "Target %", "Current %"]],
        column_config={
            "Ticker":    st.column_config.TextColumn("Ticker",   disabled=True),
            "Bucket":    st.column_config.TextColumn("Bucket",   disabled=True),
            "Label":     st.column_config.TextColumn("Name",     disabled=True),
            "Target %":  st.column_config.NumberColumn("Target %", disabled=True, format="%.1f"),
            "Current %": st.column_config.NumberColumn(
                "Current % ✏️", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"
            ),
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
            st.query_params[f"drift_{row['Ticker']}"] = str(row["Current %"])
        js_lines = "\n".join(
            f'localStorage.setItem("aw_drift_{row["Ticker"]}", "{row["Current %"]}");'
            for _, row in drift_edit.iterrows()
        )
        st.components.v1.html(f"<script>{js_lines}</script>", height=0)
        st.success("✓ Holdings saved — will reload automatically on your next visit.", icon="💾")

    # ── Drift calculations ─────────────────────────────────────────────────
    drift_edit["Drift %"] = (drift_edit["Current %"] - drift_edit["Target %"]).round(2)
    drift_edit["Action"]  = drift_edit["Drift %"].apply(
        lambda d: "▲ BUY" if d < -1 else ("▼ SELL" if d > 1 else "✓ OK")
    )

    st.markdown("<div style='margin-top:24px'>", unsafe_allow_html=True)
    for _, row in drift_edit.iterrows():
        drift  = row["Drift %"]
        action = row["Action"]
        col    = "#10b981" if action == "✓ OK" else ("#3b82f6" if "BUY" in action else "#ef4444")
        scale       = 40.0
        target_bar  = min(row["Target %"],  scale) / scale * 100
        current_bar = min(row["Current %"], scale) / scale * 100
        bucket_color = {"Core": "#3b82f6", "Tactical": "#10b981", "Hedge": "#f59e0b"}.get(row["Bucket"], "#64748b")
        st.markdown(f"""
        <div style="padding:14px 0;border-bottom:1px solid var(--border)">
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

        current_badge = (
            f'<span style="background:{border_col};color:white;font-family:var(--mono);'
            f'font-size:0.6rem;padding:2px 8px;border-radius:3px;'
            f'letter-spacing:1px;margin-left:10px">CURRENT</span>'
        ) if is_current else ""

        label_color = "var(--text)" if is_current else "var(--muted)"

        st.markdown(f"""
        <div style="padding:18px 20px;background:{bg};border:1px solid {border};
                    border-radius:8px;margin-bottom:12px">
          <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
            <div>
              <b style="font-family:var(--mono);font-size:0.85rem;color:{label_color}">{stage}</b>
              {current_badge}
            </div>
            <div style="font-size:0.75rem;color:var(--muted)">
              {'→'.join(assets)}
            </div>
          </div>
          <div style="height:10px;border-radius:5px;overflow:hidden;display:flex;margin-bottom:10px">
            <div style="width:{eq_w:.1f}%;background:#10b981"></div>
            <div style="width:{bond_w:.1f}%;background:#3b82f6"></div>
            <div style="width:{alt_w:.1f}%;background:#f59e0b"></div>
          </div>
          <div style="display:flex;gap:16px;font-size:0.7rem;color:var(--muted);font-family:var(--mono)">
            <span><span style="color:#10b981">■</span> Equity {eq_w:.0f}%</span>
            <span><span style="color:#3b82f6">■</span> Bonds {bond_w:.0f}%</span>
            <span><span style="color:#f59e0b">■</span> Alts {alt_w:.0f}%</span>
            <span style="margin-left:auto;font-style:italic">{cfg['description']}</span>
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
    st.markdown('<div class="aw-card-title">📰 Narrative Radar — GDELT Sentiment × Sector Tilt</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div style="font-size:0.8rem;color:var(--muted);margin-bottom:20px">
      News sentiment from the <b>GDELT Global Knowledge Graph</b> (7-day window, English sources)
      scored against your current tactical tilts: <b style="color:#10b981">{', '.join(top3)}</b>.
      Sentiment tone adjusts conviction — strong narrative tailwinds reinforce holds;
      headwinds flag positions for closer monitoring.
    </div>
    """, unsafe_allow_html=True)

    # Fetch GDELT for all 11 sectors so we can show the full radar, not just top3
    all_sector_tickers = list(SECTOR_ETFS.keys())

    with st.spinner("Fetching GDELT sentiment data (7-day window)…"):
        gdelt_data = fetch_gdelt_sentiment(tuple(all_sector_tickers))

    # ── Conviction score: blend momentum rank + sentiment norm ────────────
    # momentum_rank: 1 (best) to 11 (worst), inverted to 0–1
    momentum_rank = {t: i for i, t in enumerate(sector_returns.index)}
    n_sectors     = len(momentum_rank)

    conviction = {}
    for ticker in all_sector_tickers:
        mom_score  = 1.0 - (momentum_rank.get(ticker, n_sectors) / n_sectors)  # 0–1
        sent_norm  = gdelt_data[ticker]["norm"]                                  # -1 to +1
        sent_score = (sent_norm + 1) / 2                                         # rescale to 0–1
        # 60% momentum, 40% sentiment — momentum remains primary signal
        combined   = round(0.60 * mom_score + 0.40 * sent_score, 3)
        conviction[ticker] = {
            "momentum_score": round(mom_score,  3),
            "sentiment_score": round(sent_score, 3),
            "combined":        combined,
            "recommendation":  "STRONG HOLD" if combined > 0.70
                               else "HOLD"    if combined > 0.55
                               else "MONITOR" if combined > 0.40
                               else "REDUCE",
        }

    # ── Data source summary ────────────────────────────────────────────────
    source_counts = {}
    for v in gdelt_data.values():
        s = v.get("source", "unavailable")
        source_counts[s] = source_counts.get(s, 0) + 1

    source_badges = []
    badge_map = {
        "gdelt":       ("GDELT LIVE",   "#10b981"),
        "rss":         ("RSS FALLBACK", "#f59e0b"),
        "unavailable": ("NO DATA",      "#ef4444"),
    }
    for src, count in source_counts.items():
        label, color = badge_map.get(src, (src.upper(), "#64748b"))
        source_badges.append(
            f'<span style="background:rgba(255,255,255,0.05);border:1px solid {color}33;'
            f'color:{color};font-family:var(--mono);font-size:0.62rem;'
            f'padding:3px 8px;border-radius:3px">'
            f'{label} ({count})</span>'
        )

    st.markdown(f"""
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:20px;flex-wrap:wrap">
      <span style="font-size:0.72rem;color:var(--muted)">Data sources:</span>
      {"".join(source_badges)}
      <span style="font-size:0.68rem;color:var(--muted);margin-left:4px">· refreshes every 30 min</span>
    </div>
    """, unsafe_allow_html=True)

    # ── Top-level summary: conviction for current tactical positions ───────
    st.markdown("""
    <div style="font-family:var(--mono);font-size:0.65rem;letter-spacing:2px;
                text-transform:uppercase;color:var(--muted);margin-bottom:12px">
      Current Tactical Position Conviction
    </div>
    """, unsafe_allow_html=True)

    for ticker in top3:
        g    = gdelt_data[ticker]
        c    = conviction[ticker]
        rec  = c["recommendation"]
        rec_color = {
            "STRONG HOLD": "#10b981",
            "HOLD":        "#3b82f6",
            "MONITOR":     "#f59e0b",
            "REDUCE":      "#ef4444",
        }.get(rec, "#64748b")

        tone_color = "#10b981" if g["norm"] > 0.1 else ("#ef4444" if g["norm"] < -0.1 else "#64748b")
        bar_w      = int(c["combined"] * 100)
        mom_bar    = int(c["momentum_score"] * 100)
        sent_bar   = int(c["sentiment_score"] * 100)
        aligned    = "✓ regime" if ticker in quad_preferred else "↑ momentum"
        aligned_c  = "var(--accent)" if ticker in quad_preferred else "var(--accent3)"

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
              <div style="font-size:0.75rem;color:var(--muted)">
                GDELT articles (7d): <b style="color:var(--text)">{g['count']}</b>
                &nbsp;·&nbsp; Avg tone: <b style="color:{tone_color}">{g['score']:+.2f}</b>
                &nbsp;·&nbsp; Signal: <b style="color:{tone_color}">{g['tone_label']}</b>
                &nbsp;·&nbsp;
                <span style="font-family:var(--mono);font-size:0.65rem;
                  color:{badge_map.get(g.get('source','unavailable'),('','#64748b'))[1]}">
                  {badge_map.get(g.get('source','unavailable'),('N/A','#64748b'))[0]}
                </span>
              </div>
            </div>
            <div style="text-align:right">
              <div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                          letter-spacing:1px;margin-bottom:4px">CONVICTION</div>
              <div style="font-family:var(--mono);font-size:1.4rem;font-weight:700;
                          color:{rec_color}">{int(c['combined']*100)}</div>
              <div style="font-family:var(--mono);font-size:0.65rem;color:{rec_color};
                          letter-spacing:1px">{rec}</div>
            </div>
          </div>

          <div style="margin-bottom:8px">
            <div style="display:flex;justify-content:space-between;font-size:0.65rem;
                        color:var(--muted);font-family:var(--mono);margin-bottom:3px">
              <span>Combined conviction</span><span>{c['combined']*100:.0f}/100</span>
            </div>
            <div style="height:6px;background:rgba(255,255,255,0.05);border-radius:3px">
              <div style="height:100%;width:{bar_w}%;background:{rec_color};border-radius:3px"></div>
            </div>
          </div>
          <div style="display:flex;gap:16px">
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
                <span>Sentiment (40%)</span><span>{sent_bar}</span>
              </div>
              <div style="height:4px;background:rgba(255,255,255,0.05);border-radius:2px">
                <div style="height:100%;width:{sent_bar}%;background:{tone_color};border-radius:2px"></div>
              </div>
            </div>
          </div>

          {f"""<div style="margin-top:14px;padding-top:12px;border-top:1px solid var(--border)">
            <div style="font-family:var(--mono);font-size:0.6rem;color:var(--muted);
                        letter-spacing:1px;margin-bottom:8px">RECENT HEADLINES</div>
            {"".join(f'<div style="font-size:0.75rem;color:var(--muted);padding:4px 0;border-bottom:1px solid rgba(255,255,255,0.04);line-height:1.4"><span style=color:rgba(255,255,255,0.15)>›</span> {h["title"][:110]}{"…" if len(h["title"])>110 else ""}</div>' for h in g["headlines"][:3])}
          </div>""" if g['headlines'] else ""}
        </div>
        """, unsafe_allow_html=True)

    # ── Full sector radar ──────────────────────────────────────────────────
    st.markdown("""
    <div style="font-family:var(--mono);font-size:0.65rem;letter-spacing:2px;
                text-transform:uppercase;color:var(--muted);margin:24px 0 12px">
      Full Sector Narrative Scan
    </div>
    """, unsafe_allow_html=True)

    # Sort by combined conviction descending
    sorted_sectors = sorted(all_sector_tickers,
                            key=lambda t: conviction[t]["combined"], reverse=True)

    for ticker in sorted_sectors:
        g    = gdelt_data[ticker]
        c    = conviction[ticker]
        rec  = c["recommendation"]
        is_selected = ticker in top3
        rec_color = {
            "STRONG HOLD": "#10b981", "HOLD": "#3b82f6",
            "MONITOR": "#f59e0b",     "REDUCE": "#ef4444",
        }.get(rec, "#64748b")
        tone_color = "#10b981" if g["norm"] > 0.1 else ("#ef4444" if g["norm"] < -0.1 else "#64748b")
        bar_w = int(c["combined"] * 100)
        ret   = sector_returns[ticker] if ticker in sector_returns.index else 0.0
        ret_c = "#10b981" if ret >= 0 else "#ef4444"
        sel_badge = f'<span style="background:#10b981;color:#0a0c10;font-family:var(--mono);font-size:0.58rem;padding:2px 7px;border-radius:3px;font-weight:700;margin-left:6px">TACTICAL</span>' if is_selected else ""

        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:12px;padding:10px 0;
                    border-bottom:1px solid var(--border)">
          <div style="width:46px;font-family:var(--mono);font-size:0.82rem;
                      font-weight:700;color:{'var(--text)' if is_selected else 'var(--muted)'}">{ticker}</div>
          <div style="width:110px;font-size:0.72rem;color:var(--muted)">
            {SECTOR_ETFS.get(ticker,'')} {sel_badge}
          </div>
          <div style="flex:1;height:5px;background:var(--surface2);border-radius:3px">
            <div style="height:100%;width:{bar_w}%;background:{rec_color};border-radius:3px;
                        opacity:{'1' if is_selected else '0.5'}"></div>
          </div>
          <div style="width:34px;text-align:right;font-family:var(--mono);font-size:0.75rem;
                      color:{rec_color}">{bar_w}</div>
          <div style="width:60px;text-align:right;font-family:var(--mono);font-size:0.72rem;
                      color:{ret_c}">{ret*100:+.1f}%</div>
          <div style="width:68px;text-align:right;font-family:var(--mono);font-size:0.65rem;
                      color:{tone_color}">{g['tone_label']}</div>
          <div style="width:80px;text-align:right;font-family:var(--mono);font-size:0.65rem;
                      color:{rec_color};letter-spacing:0.5px">{rec}</div>
        </div>
        """, unsafe_allow_html=True)

    # ── Methodology note ───────────────────────────────────────────────────
    st.markdown(f"""
    <div style="margin-top:24px;padding:16px 20px;background:rgba(59,130,246,0.06);
                border:1px solid rgba(59,130,246,0.15);border-radius:8px;
                font-size:0.77rem;color:var(--muted);line-height:1.6">
      <b style="color:#3b82f6;font-family:var(--mono)">METHODOLOGY</b><br><br>
      <b style="color:var(--text)">Conviction score</b> = 60% momentum rank + 40% GDELT sentiment.
      Momentum remains the primary signal; sentiment acts as a confirming or cautioning overlay.
      A high-momentum sector with negative narrative (e.g. energy during a regulatory crackdown)
      will show reduced conviction relative to pure price action.<br><br>
      <b style="color:var(--text)">GDELT tone</b> is the average
      <i>DocumentTone</i> across English-language articles matching sector keywords over a
      7-day rolling window. Scores &gt; +0.10 normalized = Bullish;
      &lt; -0.10 = Bearish; otherwise Neutral. Data refreshes every 30 minutes.
      <br><br>
      <b style="color:var(--text)">Recommendation thresholds:</b>
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

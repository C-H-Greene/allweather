import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Bridgewater Knock-Off",
    page_icon="🌦",
    layout="wide",
    initial_sidebar_state="expanded",
)

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

CORE_ASSETS   = ["VOO", "TLT", "IEF", "GLD", "GSG"]
CORE_COLORS   = ["#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444"]
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
    "VOO": 480.0, "TLT": 94.0,  "IEF": 98.0,  "GLD": 225.0, "GSG": 19.5,
    "XLE": 89.0,  "XLK": 222.0, "XLV": 141.0, "XLF": 44.0,  "XLI": 119.0,
    "XLY": 191.0, "XLP": 77.0,  "XLB": 88.0,  "XLC": 91.0,  "XLU": 68.0,
    "XLRE": 42.0, "BIL": 91.5,  "SH": 14.0,   "VIXY": 25.0,
}
DEMO_VOLS = {
    "VOO": 0.155, "TLT": 0.135, "IEF": 0.065, "GLD": 0.115, "GSG": 0.225,
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
        cpi_trend = "rising" if cpi.iloc[-1] > cpi.iloc[-5] else "falling"
        cpi_vals  = cpi.tolist()

    return gdp_trend, cpi_trend, gdp_vals, cpi_vals

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
    total_inv = st.number_input("Total Investment ($)", min_value=1000,
                                 max_value=10_000_000, value=100_000, step=1000,
                                 format="%d")
    st.markdown("---")
    st.markdown("##### Bucket Weights")
    core_pct    = st.slider("Core All-Weather %", 40, 80, 60, 5)
    tactical_pct= st.slider("Tactical Pure Alpha %", 10, 40, 30, 5)
    hedge_pct   = 100 - core_pct - tactical_pct
    st.markdown(f"Hedge (auto) **{hedge_pct}%**")
    st.markdown("---")
    run_btn = st.button("🔄  REFRESH DATA", use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.markdown(f"""
<div class="aw-header">
  <span style="font-size:2rem">🌦</span>
  <div>
    <h1>PROJECT ALL-WEATHER</h1>
    <div style="margin-top:4px;display:flex;gap:8px">
      <span class="aw-badge">RISK PARITY</span>
      <span class="aw-badge" style="background:#10b981">PURE ALPHA</span>
      <span class="aw-badge" style="background:#f59e0b">TAIL HEDGE</span>
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
    all_tickers = CORE_ASSETS + list(SECTOR_ETFS.keys()) + list(HEDGE_ASSETS.keys()) + ["VOO"]
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
# PART 1 — CORE ALL-WEATHER (Risk Parity)
# ══════════════════════════════════════════════════════════════════════════════

core_prices   = prices_all[[t for t in CORE_ASSETS if t in prices_all.columns]]
core_weights  = compute_volatility_weights(core_prices)
core_assets_w = {t: core_weights.get(t, 0.0) for t in CORE_ASSETS}
core_bucket   = core_pct / 100

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
def get_atrs(tickers):
    result = {}
    for t in tickers:
        px = prices_all[t].iloc[-1] if t in prices_all.columns else 0
        atr_val = compute_atr(prices_all, t)
        stop    = float(px) - 2 * float(atr_val)
        result[t] = {"price": float(px), "atr": float(atr_val), "stop": stop}
    return result

atr_data = get_atrs(tuple(top3))

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

tab1, tab2, tab3 = st.tabs(["📊  ALLOCATION ENGINE", "📈  SECTOR MOMENTUM", "⚖  DRIFT REPORT"])

# ─── TAB 1 — ALLOCATION ENGINE ───────────────────────────────────────────────
with tab1:
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<div class="aw-card">', unsafe_allow_html=True)
        st.markdown('<div class="aw-card-title">🏛 Core All-Weather (Risk Parity)</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div style="font-size:0.8rem;color:var(--muted);margin-bottom:16px">
          Volatility-weighted across 4 economic quadrants · Bucket: <b style="color:var(--accent)">{core_pct}%</b>
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
            st.markdown(f"""
            <div class="alloc-bar-container">
              <div class="alloc-bar-label">
                <span><b>{ticker}</b></span>
                <span style="color:var(--muted)">{pct_of_total:.1f}% · ${dollar:,.0f} · {shares} shares</span>
              </div>
              <div class="alloc-bar-track">
                <div class="alloc-bar-fill" style="width:{w*100:.1f}%;background:{color}"></div>
              </div>
              <div style="font-size:0.65rem;color:var(--muted);margin-top:3px">
                30d Vol: {vol*100:.1f}% · Inv-vol weight: {w*100:.1f}%
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
            ret    = sector_returns.get(ticker, 0.0)
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
          <div class="sub">{core_pct}% · Risk Parity</div>
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
          <div class="label">Regime</div>
          <div class="value" style="color:#a78bfa;font-size:1rem">{quad_emoji} {quad_name}</div>
          <div class="sub">GDP {gdp_trend} · CPI {cpi_trend}</div>
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
      Enter your current holdings to see rebalancing actions required.
    </div>
    """, unsafe_allow_html=True)

    target_rows = []
    for ticker in CORE_ASSETS:
        if ticker not in core_weights.index:
            continue
        w       = core_weights[ticker]
        target  = core_bucket * w * 100
        target_rows.append({"Ticker": ticker, "Bucket": "Core", "Target %": target})
    for ticker in top3:
        target_rows.append({"Ticker": ticker, "Bucket": "Tactical", "Target %": tactical_per_sector * 100})
    target_rows.append({"Ticker": hedge_ticker, "Bucket": "Hedge", "Target %": hedge_pct})

    target_df = pd.DataFrame(target_rows)
    target_df["Current %"] = 0.0  # default

    drift_edit = st.data_editor(
        target_df,
        column_config={
            "Current %": st.column_config.NumberColumn(
                "Current % (edit me)", min_value=0.0, max_value=100.0, step=0.1, format="%.1f"
            )
        },
        use_container_width=True,
        hide_index=True,
    )

    drift_edit["Drift %"] = drift_edit["Current %"] - drift_edit["Target %"]
    drift_edit["Action"]  = drift_edit["Drift %"].apply(
        lambda d: "▲ BUY" if d < -1 else ("▼ SELL" if d > 1 else "✓ OK")
    )

    for _, row in drift_edit.iterrows():
        drift = row["Drift %"]
        action= row["Action"]
        col   = "#10b981" if action == "✓ OK" else ("#3b82f6" if "BUY" in action else "#ef4444")
        target_bar = min(row["Target %"], 30)
        current_bar= min(row["Current %"], 30)
        st.markdown(f"""
        <div style="padding:12px 0;border-bottom:1px solid var(--border)">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:8px">
            <b style="font-family:var(--mono);width:48px">{row['Ticker']}</b>
            <span style="font-size:0.7rem;color:var(--muted);font-family:var(--mono)">{row['Bucket']}</span>
            <span style="margin-left:auto;font-family:var(--mono);font-size:0.8rem;color:{col}">{action}</span>
            <span style="font-family:var(--mono);font-size:0.8rem;color:{col}">{drift:+.1f}%</span>
          </div>
          <div style="display:flex;gap:8px;align-items:center;font-size:0.7rem;color:var(--muted)">
            <span>Target</span>
            <div style="flex:1;height:4px;background:var(--surface2);border-radius:2px">
              <div style="height:100%;width:{target_bar/30*100:.0f}%;background:#3b82f6;border-radius:2px"></div>
            </div>
            <span>{row['Target %']:.1f}%</span>
          </div>
          <div style="display:flex;gap:8px;align-items:center;font-size:0.7rem;color:var(--muted);margin-top:4px">
            <span>Current</span>
            <div style="flex:1;height:4px;background:var(--surface2);border-radius:2px">
              <div style="height:100%;width:{current_bar/30*100:.0f}%;background:{col};border-radius:2px"></div>
            </div>
            <span>{row['Current %']:.1f}%</span>
          </div>
        </div>
        """, unsafe_allow_html=True)

    total_drift = drift_edit["Drift %"].abs().sum()
    st.markdown(f"""
    <div style="margin-top:16px;padding:12px 16px;background:var(--surface2);
                border:1px solid var(--border);border-radius:6px;
                font-family:var(--mono);font-size:0.8rem">
      Total portfolio drift: <b style="color:{'#10b981' if total_drift < 5 else '#f59e0b' if total_drift < 15 else '#ef4444'}">{total_drift:.1f}%</b>
      &nbsp;—&nbsp;
      {'✓ Within tolerance' if total_drift < 5 else '⚠ Rebalance recommended' if total_drift < 15 else '🚨 Immediate rebalance required'}
    </div>
    """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:40px;padding-top:20px;border-top:1px solid var(--border);
            text-align:center;font-family:var(--mono);font-size:0.65rem;color:var(--muted)">
  PROJECT ALL-WEATHER · Risk Parity + Pure Alpha Framework ·
  Data via yfinance & FRED · Not financial advice ·
  {datetime.now().strftime('%Y')}
</div>
""", unsafe_allow_html=True)

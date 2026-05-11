import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import logging
import warnings

# ── Setup & Logging ──────────────────────────────────────────────────────────
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

st.set_page_config(
    page_title="Project All-Weather",
    page_icon="🌦",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Data Helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_all_data(tickers):
    """Batches all yfinance calls into one. Uses 2-year window for stability."""
    if not tickers:
        return pd.DataFrame()
    
    ticker_str = " ".join(tickers) if isinstance(tickers, list) else tickers
    
    try:
        # 'progress=False' replaces 'silent=True' in newer yfinance versions
        data = yf.download(
            tickers=ticker_str,
            period="2y",
            interval="1d",
            auto_adjust=True,
            group_by='ticker',
            progress=False
        )
        return data
    except Exception as e:
        st.error(f"Financial Data Error: {e}")
        return pd.DataFrame()

def get_ticker_close(data, ticker):
    """Robustly extracts Close prices from MultiIndex yfinance DataFrames."""
    try:
        if isinstance(data.columns, pd.MultiIndex):
            # If ticker is the top level (group_by='ticker')
            if ticker in data.columns.levels[0]:
                return data[ticker]['Close']
            # If price type is top level
            elif 'Close' in data.columns.levels[0] and ticker in data.columns.levels[1]:
                return data.xs(key=('Close', ticker), axis=1)
        # Single index fallback
        if ticker in data.columns:
            return data[ticker]
        if 'Close' in data.columns:
            return data['Close']
        return pd.Series()
    except:
        return pd.Series()

# ── New Feature: Regime Volatility ───────────────────────────────────────────

def display_regime_volatility(data, benchmark="SPY"):
    """Calculates 21-day realized volatility to gauge market stability."""
    prices = get_ticker_close(data, benchmark)
    if prices.empty: return
    
    returns = prices.pct_change().dropna()
    realized_vol = returns.rolling(window=21).std() * np.sqrt(252) * 100
    current_vol = realized_vol.iloc[-1]
    
    if current_vol < 15:
        status, color = "Stable / Expansion", "normal"
    elif current_vol < 25:
        status, color = "Moderate / Transition", "off"
    else:
        status, color = "High / Unstable", "inverse"
        
    st.metric("Regime Volatility (VIX-Proxy)", f"{current_vol:.1f}%", delta=status, delta_color=color)

# ── New Feature: Correlation Radar ───────────────────────────────────────────

def display_correlation_radar(data, tickers):
    """Plots a heatmap of asset correlations for the last 90 days."""
    series_dict = {}
    for t in tickers:
        c = get_ticker_close(data, t)
        if not c.empty:
            series_dict[t] = c.pct_change()
            
    if not series_dict: return
    
    df_corr = pd.DataFrame(series_dict).tail(90).corr()
    
    fig = px.imshow(df_corr, text_auto=".2f", aspect="auto",
                    color_continuous_scale='RdBu_r', origin='lower',
                    title="Portfolio Correlation Radar (90-Day Returns)")
    fig.update_layout(margin=dict(l=20, r=20, t=40, b=20), height=350)
    st.plotly_chart(fig, use_container_width=True)

# ── Core Calculations ────────────────────────────────────────────────────────

def calculate_risk_parity_weights(data, tickers):
    """Standard inverse-volatility weighting."""
    volatilities = {}
    for t in tickers:
        prices = get_ticker_close(data, t)
        if not prices.empty:
            vol = prices.pct_change().tail(30).std()
            volatilities[t] = vol if vol > 0 else 0.01
            
    inv_vol = {t: 1/v for t, v in volatilities.items()}
    total_inv_vol = sum(inv_vol.values())
    return {t: v/total_inv_vol for t, v in inv_vol.items()}

# ── Main Application ─────────────────────────────────────────────────────────

def main():
    # 1. Sidebar Inputs
    st.sidebar.header("Strategy Configuration")
    total_inv = st.sidebar.number_input("Total Investment ($)", value=100000, step=1000)
    profile = st.sidebar.selectbox("Risk Profile", ["31y Aggressive Global", "Standard All-Weather"])
    
    core_pct = st.sidebar.slider("Core Allocation %", 0, 100, 60)
    alpha_pct = st.sidebar.slider("Tactical Alpha %", 0, 100, 30)
    
    # 2. Asset Definitions
    if profile == "31y Aggressive Global":
        core_assets = ["VOO", "VEA", "VWO", "GLD"]
    else:
        core_assets = ["VOO", "TLT", "IEF", "GLD", "GSG"]
        
    tactical_sectors = ["XLK", "XLRE", "XLE", "XLU", "XLY", "XLF", "XLV", "XLI", "XLB", "XLP"]
    all_needed = list(set(core_assets + tactical_sectors + ["SPY"]))
    
    # 3. Data Fetching
    with st.spinner("Fetching Global Market Data..."):
        raw_data = fetch_all_data(all_needed)
    
    if raw_data.empty:
        st.error("Unable to load market data. Please refresh.")
        return

    # 4. Top Header Metrics
    m1, m2, m3 = st.columns(3)
    with m1:
        display_regime_volatility(raw_data)
    with m2:
        st.metric("Active Macro Regime", "Stagflation Lite", "CPI: 3.26%")
    with m3:
        st.metric("Portfolio Goal", "10.5% CAGR", "Aggressive")

    # 5. Core Allocation
    st.divider()
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("Core: Global Risk Parity")
        weights = calculate_risk_parity_weights(raw_data, core_assets)
        
        core_df = pd.DataFrame([
            {"Asset": t, "Weight %": f"{w*100:.1f}%", "Dollars": f"${(total_inv*(core_pct/100)*w):,.0f}"}
            for t, w in weights.items()
        ])
        st.table(core_df)
        
    with col_right:
        display_correlation_radar(raw_data, core_assets + ["XLK"])

    # 6. Tactical Alpha Rankings
    st.subheader("Tactical Alpha: Momentum & Sentiment")
    
    # Simple momentum calc for demonstration
    mom_data = []
    for s in tactical_sectors:
        prices = get_ticker_close(raw_data, s)
        if not prices.empty:
            ret = (prices.iloc[-1] / prices.iloc[-63]) - 1 # 3-month approx
            mom_data.append({"Sector": s, "3M

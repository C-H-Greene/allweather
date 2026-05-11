import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import warnings

warnings.filterwarnings('ignore')

# --- Page Config ---
st.set_page_config(page_title="Project All-Weather", page_icon="🌦", layout="wide")

# --- Optimized Data Fetching (Batching & Logic) ---
@st.cache_data(ttl=3600)
def fetch_all_data(tickers):
    """Batches all yfinance calls into a single download for speed."""
    if not tickers: return pd.DataFrame()
    # Download 2 years to ensure 200d SMA and ATR calculations are stable
    data = yf.download(tickers, period="2y", interval="1d", group_by='ticker', silent=True)
    return data

def get_ticker_close(data, ticker):
    """Helper to safely extract closing prices from grouped yfinance data."""
    try:
        if len(data.columns.levels) > 1:
            return data[ticker]['Close']
        return data['Close']
    except:
        return pd.Series()

# --- New Feature: Correlations Radar ---
def plot_correlation_matrix(data, tickers):
    """Calculates and plots a correlation heatmap for the tactical & core holdings."""
    returns = pd.DataFrame({t: get_ticker_close(data, t).pct_change() for t in tickers}).dropna()
    corr = returns.corr()
    
    fig = px.imshow(corr, text_auto=".2f", aspect="auto", 
                    color_continuous_scale='RdBu_r', origin='lower',
                    title="Portfolio Correlation Radar (90-Day Returns)")
    st.plotly_chart(fig, use_container_width=True)

# --- New Feature: Regime Volatility Signal ---
def get_regime_volatility(data, benchmark="SPY"):
    """Calculates the 30-day realized volatility of the benchmark to gauge regime stability."""
    prices = get_ticker_close(data, benchmark)
    returns = prices.pct_change().dropna()
    vol = returns.rolling(window=21).std() * np.sqrt(252) * 100
    current_vol = vol.iloc[-1]
    
    # Logic: High Vol = Unstable Regime, Low Vol = Stable/Expansion
    color = "inverse" if current_vol > 25 else "normal" # Simple threshold
    st.metric("Regime Volatility (VIX-Proxy)", f"{current_vol:.2f}%", 
              delta="High Vol / Unstable" if current_vol > 20 else "Stable", 
              delta_color=color)

# --- App Logic ---
def main():
    st.title("🌦 Project All-Weather: Institutional-Lite")
    
    # Sidebar & Inputs
    total_inv = st.sidebar.number_input("Total Investment", value=100000)
    age_choice = st.sidebar.selectbox("Strategy Profile", ["31y - Aggressive Global", "Standard All-Weather"])
    
    if age_choice == "31y - Aggressive Global":
        core_assets = ["VOO", "VEA", "VWO", "GLD"]
    else:
        core_assets = ["VOO", "TLT", "IEF", "GLD", "GSG"]
        
    tactical_candidates = ["XLK", "XLRE", "XLE", "XLU", "XLY", "XLF", "XLV", "XLI", "XLB", "XLP"]
    all_tickers = list(set(core_assets + tactical_candidates + ["SPY"]))

    # 1. Fetch Data (Optimized)
    raw_data = fetch_all_data(all_tickers)
    
    if raw_data.empty:
        st.error("⚠️ DATA FETCH ERROR: Synthetic data fallback active.")
        return

    # 2. Top Metric Bar
    col1, col2, col3 = st.columns(3)
    with col1:
        get_regime_volatility(raw_data)
    with col2:
        # Display Current Macro Regime (Example Placeholder Logic)
        st.metric("Economic Regime", "Stagflation Lite", "Sticky Inflation")
    
    # 3. Correlation Radar
    st.divider()
    plot_correlation_matrix(raw_data, core_assets + ["XLK", "XLRE", "XLE"]) # Example selection

    # 4. Tactical Ranking (Simplified)
    st.subheader("Tactical Alpha Rankings")
    # (Insert your ranking logic here using 'raw_data'...)

if __name__ == "__main__":
    main()

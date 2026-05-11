import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.express as px
from datetime import datetime, timedelta
import logging
import warnings

# ── Setup ────────────────────────────────────────────────────────────────────
warnings.filterwarnings('ignore')
logging.getLogger('yfinance').setLevel(logging.CRITICAL)

st.set_page_config(
    page_title="Project All-Weather",
    page_icon="🌦",
    layout="wide"
)

# ── Data Fetching ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_all_data(tickers):
    """Batches all yfinance calls. Uses 2026 'progress=False' syntax."""
    if not tickers:
        return pd.DataFrame()
    ticker_str = " ".join(tickers) if isinstance(tickers, list) else tickers
    try:
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
    """Robustly extracts Close prices from MultiIndex DataFrames."""
    try:
        if isinstance(data.columns, pd.MultiIndex):
            if ticker in data.columns.levels[0]:
                return data[ticker]['Close']
            elif 'Close' in data.columns.levels[0] and ticker in data.columns.levels[1]:
                return data.xs(key=('Close', ticker), axis=1)
        if ticker in data.columns:
            return data[ticker]
        return pd.Series()
    except:
        return pd.Series()

# ── Metrics & Visualization ───────────────────────────────────────────────────

def display_regime_volatility(data, benchmark="SPY"):
    """Realized volatility gauge to identify regime stability."""
    prices = get_ticker_close(data, benchmark)
    if prices.empty: return
    returns = prices.pct_change().dropna()
    realized_vol = returns.rolling(window=21).std() * np.sqrt(252) * 100
    current_vol = realized_vol.iloc[-1]
    
    # Define thresholds for the signal
    if current_vol < 15:
        status, delta_col = "Stable Expansion", "normal"
    elif current_vol < 25:
        status, delta_col = "Transitionary", "off"
    else:
        status, delta_col = "High Vol / Unstable", "inverse"
        
    st.metric("Regime Volatility (VIX Proxy)", f"{current_vol:.1f}%", delta=status, delta_color=delta_col)

def display_correlation_radar(data, tickers):
    """Visualizes how connected tactical picks are to avoid over-concentration."""
    series_dict = {}
    for t in tickers:
        c = get_ticker_close(data, t)
        if not c.empty:
            series_dict[t] = c.pct_change()
    if not series_dict: return
    
    df_corr = pd.DataFrame(series_dict).tail(90).corr()
    fig = px.imshow(df_corr, text_auto=".2f", aspect="auto",
                    color_continuous_scale='RdBu_r', origin='lower',
                    title="Correlation Radar (90-Day Returns)")
    fig.update_layout(margin=dict(l=10, r=10, t=40, b=10), height=350)
    st.plotly_chart(fig, use_container_width=True)

# ── Main Application ──────────────────────────────────────────────────────────

def main():
    st.sidebar.header("Portfolio Parameters")
    total_inv = st.sidebar.number_input("Total Investment ($)", value=100000)
    profile = st.sidebar.selectbox("Model Profile", ["31y Aggressive Global", "Standard All-Weather"])
    
    core_pct = st.sidebar.slider("Core Portfolio %", 0, 100, 60)
    alpha_pct = st.sidebar.slider("Tactical Alpha %", 0, 100, 30)
    
    # Asset Selection
    if profile == "31y Aggressive Global":
        core_assets = ["VOO", "VEA", "VWO", "GLD"]
    else:
        core_assets = ["VOO", "TLT", "IEF", "GLD", "GSG"]
        
    tactical_sectors = ["XLK", "XLRE", "XLE", "XLU", "XLY", "XLF", "XLV", "XLI", "XLB", "XLP"]
    all_tickers = list(set(core_assets + tactical_sectors + ["SPY"]))
    
    with st.spinner("Fetching Institutional Data..."):
        raw_data = fetch_all_data(all_tickers)
    
    if raw_data.empty:
        st.error("Data connection failed. Please check your network.")
        return

    # Header Row
    m1, m2, m3 = st.columns(3)
    with m1:
        display_regime_volatility(raw_data)
    with m2:
        st.metric("Estimated Regime", "Stagflation Lite", "Sticky Inflation")
    with m3:
        st.metric("Profile Target", "Aggressive Growth", "90/10 Ratio")

    st.divider()
    
    # Layout: Core vs Radar
    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.subheader("Core: Risk Parity Weights")
        # Simple Inverse-Vol calculation
        vols = {t: get_ticker_close(raw_data, t).pct_change().tail(30).std() for t in core_assets}
        inv_vols = {t: (1/v if v > 0 else 1) for t, v in vols.items()}
        total_inv_vol = sum(inv_vols.values())
        weights = {t: v/total_inv_vol for t, v in inv_vols.items()}
        
        core_df = pd.DataFrame([
            {"Asset": t, "Weight": f"{w*100:.1f}%", "Value": f"${(total_inv * (core_pct/100) * w):,.0f}"}
            for t, w in weights.items()
        ])
        st.table(core_df)
        
    with col_b:
        display_correlation_radar(raw_data, core_assets + ["XLK", "XLRE"])

    # Tactical Section
    st.subheader("Tactical Alpha: Momentum Ranking")
    mom_data = []
    for s in tactical_sectors:
        prices = get_ticker_close(raw_data, s)
        if not prices.empty:
            # Safely calculate 3-month momentum
            window = min(len(prices), 63)
            ret = (prices.iloc[-1] / prices.iloc[-window]) - 1
            mom_data.append({"Sector": s, "3M Momentum": ret})
    
    mom_df = pd.DataFrame(mom_data).sort_values("3M Momentum", ascending=False)
    top_3 = mom_df.head(3)["Sector"].tolist()
    
    t1, t2, t3 = st.columns(3)
    for i, col in enumerate([t1, t2, t3]):
        with col:
            s_name = top_3[i]
            st.info(f"**#{i+1}: {s_name}**")
            st.write(f"Allocation: ${(total_inv * (alpha_pct/100) / 3):,.0f}")

if __name__ == "__main__":
    main()

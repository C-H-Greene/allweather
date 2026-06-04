"""
data.py
All data fetching functions. Each is decorated with @st.cache_data.
Edit this file to change data sources, cache TTLs, or fallback behaviour.
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta

from config import PE_ESTIMATES, SPY_PE_ESTIMATE


# ── Price / OHLCV ──────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_prices(tickers: tuple, period: str = "1y") -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Returns (close, high, low) DataFrames for all tickers.
    Falls back to synthetic demo data when yfinance is blocked.
    """
    try:
        raw = yf.download(list(tickers), period=period, auto_adjust=True, progress=False)
        if raw.empty:
            raise ValueError("empty response")

        if isinstance(raw.columns, pd.MultiIndex):
            close = raw["Close"].ffill()
            high  = raw["High"].ffill()
            low   = raw["Low"].ffill()
        else:
            close = raw.ffill()
            high  = close * 1.005
            low   = close * 0.995

        if close.isnull().all().all():
            raise ValueError("all NaN")

        return close, high, low

    except Exception:
        st.warning(
            "⚠ Live market data unavailable — running in Demo Mode.",
            icon="🔌",
        )
        return _demo_prices(tickers)


def _demo_prices(tickers: tuple) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    BASE = {
        "VOO": 480, "VEA": 52,  "VWO": 43,  "GLD": 225, "TLT": 94,
        "IEF": 98,  "TIP": 105, "BIL": 91.5,"SH":  14,
        "XLE": 89,  "XLK": 222, "XLV": 141, "XLF": 44,  "XLI": 119,
        "XLY": 191, "XLP": 77,  "XLB": 88,  "XLC": 91,  "XLU": 68,
        "XLRE":42,  "SMH": 220, "VNQ": 88,
    }
    np.random.seed(42)
    dates = pd.bdate_range(end=datetime.today(), periods=252)
    result = {}
    for t in tickers:
        p = float(BASE.get(t, 100))
        v = 0.18 / np.sqrt(252)
        r = np.random.normal(0.0003, v, len(dates))
        prices = p * np.exp(np.cumsum(r) - np.cumsum(r)[-1])
        result[t] = prices
    close = pd.DataFrame(result, index=dates)
    return close, close * 1.005, close * 0.995


# ── Macro (FRED) ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_macro() -> dict:
    """
    Fetch GDP, CPI, yield curve (T10Y2Y), industrial production (INDPRO),
    and initial jobless claims (ICSA) from FRED public CSV endpoint.
    No API key required.

    Returns a flat dict with all fields needed by the engine and UI.
    """
    import urllib.request

    def fred(series_id: str, tail: int = 18) -> pd.Series | None:
        url = (
            f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
            f"&vintage_date={datetime.today().strftime('%Y-%m-%d')}"
        )
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                raw = r.read().decode().strip().split("\n")
            rows = [l.split(",") for l in raw[1:] if "." in l]
            s = pd.Series(
                [float(r[1]) for r in rows],
                index=pd.to_datetime([r[0] for r in rows]),
            ).dropna()
            return s.tail(tail)
        except Exception:
            return None

    def streak(s: pd.Series) -> tuple[str, int]:
        """Return (direction, consecutive_periods) for the latest trend."""
        d = np.sign(s.diff().dropna())
        cur = d.iloc[-1]
        n = 1
        for v in reversed(d.iloc[:-1].tolist()):
            if np.sign(v) == cur:
                n += 1
            else:
                break
        return ("rising" if cur > 0 else "falling"), n

    gdp    = fred("GDP",      12)
    cpi    = fred("CPIAUCSL", 18)
    yc_raw = fred("T10Y2Y",  756)
    indpro = fred("INDPRO",   24)
    claims = fred("ICSA",    104)

    # ── GDP ───────────────────────────────────────────────────────────────────
    gdp_trend, gdp_streak, gdp_mom = "rising", 1, 0.0
    if gdp is not None and len(gdp) >= 2:
        gdp_trend, gdp_streak = streak(gdp)
        gdp_mom = float((gdp.iloc[-1] - gdp.iloc[-2]) / gdp.iloc[-2] * 100)

    # ── CPI ───────────────────────────────────────────────────────────────────
    cpi_trend, cpi_streak, cpi_mom = "falling", 1, 0.0
    if cpi is not None and len(cpi) >= 2:
        lb = min(5, len(cpi) - 1)
        cpi_trend = "rising" if cpi.iloc[-1] > cpi.iloc[-lb] else "falling"
        cpi_mom   = float((cpi.iloc[-1] - cpi.iloc[-lb]) / cpi.iloc[-lb] * 100)
        _, cpi_streak = streak(cpi)

    # ── Yield curve ───────────────────────────────────────────────────────────
    yc_current = yc_3m_avg = None
    yc_signal  = "unknown"
    if yc_raw is not None and len(yc_raw) >= 60:
        yc_current = round(float(yc_raw.iloc[-1]), 2)
        yc_3m_avg  = round(float(yc_raw.tail(63).mean()), 2)
        if yc_current < -0.25:
            yc_signal = "inverted"
        elif yc_current < 0.25:
            yc_signal = "flat"
        else:
            monthly = yc_raw.resample("ME").mean().dropna().tail(6)
            yc_signal = (
                "steepening"
                if len(monthly) >= 3 and monthly.iloc[-1] > monthly.iloc[-3]
                else "normal"
            )

    # ── Industrial production (PMI proxy) ─────────────────────────────────────
    pmi_mom, pmi_signal, pmi_current = 0.0, "stalling", None
    if indpro is not None and len(indpro) >= 3:
        pmi_current = round(float(indpro.iloc[-1]), 2)
        pmi_mom     = float((indpro.iloc[-1] - indpro.iloc[-3]) / indpro.iloc[-3] * 100)
        pmi_signal  = (
            "expanding"    if pmi_mom >  0.5 else
            "contracting"  if pmi_mom < -0.5 else
            "stalling"
        )

    # ── Jobless claims ────────────────────────────────────────────────────────
    claims_current, claims_signal = None, "stable"
    if claims is not None and len(claims) >= 8:
        c4 = float(claims.tail(4).mean())
        cp = float(claims.tail(8).head(4).mean())
        claims_current = round(c4 / 1000, 1)
        pct = (c4 - cp) / cp * 100
        claims_signal = (
            "deteriorating" if pct >  5 else
            "improving"     if pct < -5 else
            "stable"
        )

    # ── Leading composite ─────────────────────────────────────────────────────
    ls = [
        1  if yc_signal in ("steepening", "normal")  else (-1 if yc_signal == "inverted"    else 0),
        1  if pmi_signal == "expanding"               else (-1 if pmi_signal == "contracting" else 0),
        1  if claims_signal == "improving"            else (-1 if claims_signal == "deteriorating" else 0),
    ]
    composite    = sum(ls)
    leading_bias = (
        "growth_positive" if composite >= 2  else
        "growth_negative" if composite <= -2 else
        "mixed"
    )

    return {
        "gdp_trend":      gdp_trend,
        "gdp_streak":     gdp_streak,
        "gdp_mom":        round(gdp_mom, 3),
        "cpi_trend":      cpi_trend,
        "cpi_streak":     cpi_streak,
        "cpi_mom":        round(cpi_mom, 3),
        "yc_current":     yc_current,
        "yc_3m_avg":      yc_3m_avg,
        "yc_signal":      yc_signal,
        "pmi_current":    pmi_current,
        "pmi_mom":        round(pmi_mom, 2),
        "pmi_signal":     pmi_signal,
        "claims_current": claims_current,
        "claims_signal":  claims_signal,
        "leading_bias":   leading_bias,
        "leading_scores": ls,
    }


# ── Forward P/E ────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def fetch_forward_pe(tickers: tuple) -> tuple[dict, float]:
    """
    Fetch forward P/E for sector ETFs via yfinance .info.
    Falls back to calibrated estimates when live data is unavailable.

    Returns (pe_dict, spy_fwd_pe) where pe_dict[ticker] has:
        fwd_pe, rel_pe (vs SPY), valuation ("cheap"/"fair"/"expensive"), source
    """
    spy_pe = SPY_PE_ESTIMATE
    try:
        si = yf.Ticker("SPY").info
        v  = si.get("forwardPE") or si.get("trailingPE")
        if v and 10 < float(v) < 60:
            spy_pe = float(v)
    except Exception:
        pass

    result = {}
    for t in tickers:
        fwd_pe = None
        source = "estimate"
        try:
            info   = yf.Ticker(t).info
            fpe    = info.get("forwardPE")
            if fpe and 5 < float(fpe) < 100:
                fwd_pe = float(fpe)
                source = "live"
        except Exception:
            pass

        if fwd_pe is None:
            fwd_pe = PE_ESTIMATES.get(t)
            source = "estimate"

        if fwd_pe is None:
            result[t] = {"fwd_pe": None, "rel_pe": None, "valuation": "unknown", "source": source}
        else:
            rel = round(fwd_pe / spy_pe, 2)
            val = (
                "expensive" if rel > 1.25 else
                "cheap"     if rel < 0.80 else
                "fair"
            )
            result[t] = {
                "fwd_pe":    round(fwd_pe, 1),
                "rel_pe":    rel,
                "valuation": val,
                "source":    source,
            }

    return result, round(spy_pe, 1)

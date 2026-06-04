"""
engine.py
Pure computation — no Streamlit imports, no UI calls.
All functions take data in, return structured results out.

Edit this file to change:
  - Scoring weights for sector selection
  - Regime confidence signal weights
  - Transition probability logic
  - Stop-loss calculation method
"""

import pandas as pd
import numpy as np
from datetime import timedelta

from config import (
    BUCKET_WEIGHTS, TILT_SLOTS, ETF_DATA, TLH_ONLY,
    EXCLUSIVE_FACTOR_GROUPS, REGIME_TILTS, REGIME_META,
)


# ── Core weights ───────────────────────────────────────────────────────────────

def inv_vol_weights(prices: pd.DataFrame, tickers: list) -> dict:
    """
    Inverse-volatility weights from 30-day log returns.
    Returns {ticker: weight} normalised to sum to 1.0.
    """
    available = [t for t in tickers if t in prices.columns]
    if not available:
        n = max(len(tickers), 1)
        return {t: 1 / n for t in tickers}

    log_ret = np.log(prices[available] / prices[available].shift(1)).dropna()
    vols    = log_ret.tail(30).std() * np.sqrt(252)
    vols    = vols.replace(0, np.nan).dropna()

    if vols.empty:
        n = len(available)
        return {t: 1 / n for t in available}

    inv   = 1 / vols
    total = inv.sum()
    return {t: float(inv.get(t, 0) / total) for t in available}


# ── ATR & stop-loss ────────────────────────────────────────────────────────────

def compute_atr(prices: pd.DataFrame, highs: pd.DataFrame,
                lows: pd.DataFrame, ticker: str, window: int = 14) -> float:
    """Average True Range over `window` days."""
    try:
        if ticker not in prices.columns:
            return 0.0
        hi = highs[ticker].dropna()
        lo = lows[ticker].dropna()
        cl = prices[ticker].dropna()
        tr = pd.concat([
            hi - lo,
            (hi - cl.shift()).abs(),
            (lo - cl.shift()).abs(),
        ], axis=1).max(axis=1)
        val = tr.rolling(window).mean().iloc[-1]
        return float(val) if pd.notna(val) else 0.0
    except Exception:
        return 0.0


def stop_price(prices: pd.DataFrame, highs: pd.DataFrame,
               lows: pd.DataFrame, ticker: str) -> tuple[float, float]:
    """
    Returns (stop_px, atr_val) where stop_px = current_price - 2 * ATR.
    Returns (0.0, 0.0) if data unavailable.
    """
    if ticker not in prices.columns:
        return 0.0, 0.0
    px      = float(prices[ticker].iloc[-1])
    atr_val = compute_atr(prices, highs, lows, ticker)
    return round(px - 2 * atr_val, 2), round(atr_val, 2)


def check_stop_triggered(prices: pd.DataFrame, highs: pd.DataFrame,
                         lows: pd.DataFrame, ticker: str,
                         cost_basis: float) -> bool:
    """True if current price is at or below the 2×ATR stop."""
    if cost_basis <= 0 or ticker not in prices.columns:
        return False
    stop_px, _ = stop_price(prices, highs, lows, ticker)
    if stop_px <= 0:
        return False
    return float(prices[ticker].iloc[-1]) <= stop_px


# ── Sector selection engine ────────────────────────────────────────────────────

def score_sectors(
    prices:          pd.DataFrame,
    macro:           dict,
    regime_key:      tuple,
    pe_data:         dict,
    stopped_tickers: list,
) -> list:
    """
    Score and rank all tilt candidates for the given regime.

    Steps:
      1. Score each eligible candidate on 4 signals
      2. Sort by combined score
      3. Deduplicate by exclusive factor groups
      4. Return ranked list (caller slices to n_tilts)

    Scoring weights:
      40% — 3-month momentum rank
      35% — regime alignment
      15% — relative valuation (forward P/E vs SPY)
      10% — leading indicator confirmation

    Returns list of dicts, each with:
      ticker, combined, momentum, regime, valuation, leading,
      ret_3m, is_preferred, pe_data, rationale
    """
    preferred = set(REGIME_TILTS.get(regime_key, []))

    # All eligible primaries (not TLH-only, not stopped)
    candidates = [
        t for tilts in REGIME_TILTS.values()
        for t in tilts
        if t in ETF_DATA
        and t not in TLH_ONLY
        and t not in stopped_tickers
        and t in prices.columns
    ]
    candidates = list(dict.fromkeys(candidates))   # dedupe, preserve order

    if not candidates:
        return []

    # 3-month returns
    three_mo   = prices.index[-1] - timedelta(days=90)
    start_rows = prices[candidates][prices.index >= three_mo]
    if start_rows.empty:
        return []
    ret_3m  = (prices[candidates].iloc[-1] - start_rows.iloc[0]) / start_rows.iloc[0]
    ret_rank = ret_3m.rank(pct=True)

    bias = macro["leading_bias"]

    scored = []
    for t in candidates:
        info = ETF_DATA.get(t, {})
        tags = info.get("factors", [])

        # Signal 1: Momentum (40%)
        mom = float(ret_rank.get(t, 0.5))

        # Signal 2: Regime alignment (35%)
        if t in preferred:
            reg = 1.0
        else:
            pref_factors = {
                f for pt in preferred
                if pt in ETF_DATA
                for f in ETF_DATA[pt].get("factors", [])
            }
            overlap = len(set(tags) & pref_factors) / max(len(tags), 1)
            reg = overlap * 0.4

        # Signal 3: Valuation (15%)
        pe  = pe_data.get(t, {})
        rel = pe.get("rel_pe")
        if rel is not None:
            # 0.80→1.0, 1.25→0.36, 1.50→0.0
            val_score = max(0.0, min(1.0, (1.5 - rel) / 0.7))
        else:
            val_score = 0.5

        # Signal 4: Leading indicator confirmation (10%)
        if bias == "growth_positive":
            lead = 1.0 if any(f in tags for f in ["growth", "cyclical", "financials"]) else 0.4
        elif bias == "growth_negative":
            lead = 1.0 if any(f in tags for f in ["defensive", "inflation", "gold", "long_bond"]) else 0.2
        else:
            lead = 0.5

        combined = 0.40 * mom + 0.35 * reg + 0.15 * val_score + 0.10 * lead

        # Small P/E adjustment
        val_label = pe.get("valuation", "fair")
        if val_label == "expensive":
            combined -= 0.03
        elif val_label == "cheap":
            combined += 0.02

        scored.append({
            "ticker":       t,
            "combined":     round(combined, 3),
            "momentum":     round(mom,       3),
            "regime":       round(reg,       3),
            "valuation":    round(val_score, 3),
            "leading":      round(lead,      3),
            "ret_3m":       round(float(ret_3m.get(t, 0)), 4),
            "is_preferred": t in preferred,
            "pe_data":      pe,
            "rationale":    _rationale(t, t in preferred, reg, mom, pe, bias),
        })

    # Sort descending
    scored.sort(key=lambda x: -x["combined"])

    # Deduplicate by exclusive factor groups
    claimed: set = set()
    deduped = []
    for s in scored:
        tags = ETF_DATA.get(s["ticker"], {}).get("factors", [])
        skip = False
        for group in EXCLUSIVE_FACTOR_GROUPS:
            if any(f in tags for f in group):
                key = group[0]
                if key in claimed:
                    skip = True
                    break
                claimed.add(key)
        if not skip:
            deduped.append(s)

    return deduped


def _rationale(ticker, is_preferred, reg_score, mom_score, pe, bias) -> str:
    parts = []
    if is_preferred:
        parts.append("regime-aligned")
    elif reg_score > 0.3:
        parts.append("adjacent regime exposure")

    if mom_score > 0.7:
        parts.append("strong 3M momentum")
    elif mom_score < 0.3:
        parts.append("weak momentum")

    val = pe.get("valuation", "fair") if pe else "fair"
    if val == "cheap":
        parts.append(f"undervalued vs market ({pe.get('rel_pe','?')}× P/E)")
    elif val == "expensive":
        parts.append(f"premium valuation ({pe.get('rel_pe','?')}× P/E)")

    tags = ETF_DATA.get(ticker, {}).get("factors", [])
    if bias == "growth_positive" and any(f in tags for f in ["growth", "cyclical"]):
        parts.append("leading indicators bullish")
    elif bias == "growth_negative" and any(f in tags for f in ["defensive", "inflation"]):
        parts.append("leading indicators support defensives")

    return " · ".join(parts) if parts else "momentum-driven"


def n_tilt_slots(confidence_score: int) -> int:
    """Determine how many tilt positions to take based on regime confidence."""
    for threshold in sorted(TILT_SLOTS.keys(), reverse=True):
        if confidence_score >= threshold:
            return TILT_SLOTS[threshold]
    return 0


# ── Regime confidence ──────────────────────────────────────────────────────────

def regime_confidence(
    macro:          dict,
    quad_preferred: list,
    sector_rets:    pd.Series,
    prices:         pd.DataFrame,
) -> dict:
    """
    0–100 score measuring confidence that the current regime is correctly identified.

    Signals (weights):
      20% — Macro momentum magnitude (how hard are GDP/CPI moving?)
      20% — Trend streak (how many consecutive periods in this regime?)
      25% — Sector price confirmation (are preferred sectors outperforming?)
      15% — Equity/bond decorrelation (is risk parity assumption holding?)
      20% — Leading indicator alignment
    """
    # Signal 1: Macro momentum magnitude
    gdp_mag  = min(abs(macro["gdp_mom"]) / 2.0, 1.0)
    cpi_mag  = min(abs(macro["cpi_mom"]) / 1.5, 1.0)
    macro_s  = (gdp_mag + cpi_mag) / 2

    # Signal 2: Streak age
    ms = min(macro["gdp_streak"], macro["cpi_streak"])
    streak_s = (
        0.25 if ms <= 1 else
        0.60 if ms <= 3 else
        0.85 if ms <= 6 else
        max(0.60, 0.85 - (ms - 6) * 0.05)
    )

    # Signal 3: Sector confirmation
    spy_ret = float(sector_rets.get("VOO", 0)) if hasattr(sector_rets, "get") else 0.0
    if quad_preferred:
        beats    = sum(
            1 for t in quad_preferred
            if t in sector_rets.index and float(sector_rets[t]) > spy_ret
        )
        sector_s = beats / len(quad_preferred)
    else:
        sector_s = 0.5

    # Signal 4: Equity/bond decorrelation
    corr_s = 0.5
    if "VOO" in prices.columns and "TLT" in prices.columns:
        eq = prices["VOO"].pct_change().dropna().tail(60)
        bd = prices["TLT"].pct_change().dropna().tail(60)
        df = pd.concat([eq, bd], axis=1).dropna()
        if len(df) >= 20:
            c      = float(df.iloc[:, 0].corr(df.iloc[:, 1]))
            corr_s = max(0.0, min(1.0, (1 - c) / 2))

    # Signal 5: Leading indicators
    ls     = macro["leading_scores"]
    lead_s = max(0.0, min(1.0, (sum(ls) + 3) / 6))

    score = round(
        (0.20 * macro_s +
         0.20 * streak_s +
         0.25 * sector_s +
         0.15 * corr_s +
         0.20 * lead_s) * 100
    )

    label = (
        "ESTABLISHED"   if score >= 75 else
        "CONFIRMED"     if score >= 55 else
        "FORMING"       if score >= 35 else
        "TRANSITIONING"
    )
    color = (
        "#3fb950" if score >= 75 else
        "#58a6ff" if score >= 55 else
        "#d29922" if score >= 35 else
        "#f85149"
    )

    return {
        "score":   score,
        "label":   label,
        "color":   color,
        "signals": [
            ("Macro momentum",    round(macro_s  * 100)),
            ("Trend streak",      round(streak_s * 100)),
            ("Sector confirm",    round(sector_s * 100)),
            ("EQ/Bond decorr",    round(corr_s   * 100)),
            ("Leading indicators",round(lead_s   * 100)),
        ],
    }


# ── Transition probability ─────────────────────────────────────────────────────

def transition_probability(
    macro:     dict,
    gdp_trend: str,
    cpi_trend: str,
) -> dict:
    """
    Estimates the probability that the current regime will change within ~2-3 quarters.

    Signals (weights):
      40% — Leading indicator divergence from current regime expectations
      20% — Yield curve level (inverted = high transition risk)
      20% — Streak age vs empirical regime durations
      20% — Axis momentum pressure (how close are GDP/CPI to flipping?)

    Also returns the most likely destination regime and implied position shifts.
    """
    MEDIAN_DUR = {
        ("rising",  "falling"): 14,
        ("rising",  "rising"):   4,
        ("falling", "rising"):   3,
        ("falling", "falling"):  2,
    }
    med = MEDIAN_DUR.get((gdp_trend, cpi_trend), 6)
    ms  = min(macro["gdp_streak"], macro["cpi_streak"])

    # Signal 1: Leading divergence
    expected_map = {
        ("rising",  "falling"):  {"yc":  1, "pmi":  1, "claims":  1},
        ("rising",  "rising"):   {"yc": -1, "pmi":  0, "claims": -1},
        ("falling", "rising"):   {"yc": -1, "pmi": -1, "claims": -1},
        ("falling", "falling"):  {"yc":  1, "pmi": -1, "claims":  0},
    }
    expected = expected_map.get((gdp_trend, cpi_trend), {"yc": 0, "pmi": 0, "claims": 0})
    ls  = macro["leading_scores"]
    keys = ["yc", "pmi", "claims"]
    div_scores = []
    for i, k in enumerate(keys):
        act, exp = ls[i], expected[k]
        if exp == 0:
            div_scores.append(abs(act) * 0.5)
        elif act == -exp:
            div_scores.append(1.0)
        elif act == exp:
            div_scores.append(0.0)
        else:
            div_scores.append(0.35)
    div_s = sum(div_scores) / 3

    # Signal 2: Yield curve
    yc_s = {
        "inverted":   0.85,
        "flat":       0.55,
        "steepening": 0.15,
        "normal":     0.10,
        "unknown":    0.40,
    }.get(macro["yc_signal"], 0.40)

    # Signal 3: Streak age
    if ms == 0:
        streak_s = 0.0
    elif ms < med * 0.5:
        streak_s = 0.1
    elif ms < med:
        streak_s = 0.3 + 0.3 * (ms / med)
    elif ms < med * 1.5:
        streak_s = 0.65
    else:
        streak_s = min(0.90, 0.65 + (ms - med * 1.5) * 0.05)

    # Signal 4: Axis pressure
    axis_s = (
        max(0.0, min(1.0, 1.0 - abs(macro["gdp_mom"]) / 1.5)) +
        max(0.0, min(1.0, 1.0 - abs(macro["cpi_mom"]) / 1.0))
    ) / 2

    prob  = round((0.40 * div_s + 0.20 * yc_s + 0.20 * streak_s + 0.20 * axis_s) * 100)
    label = (
        "HIGH"     if prob >= 65 else
        "ELEVATED" if prob >= 45 else
        "MODERATE" if prob >= 25 else
        "LOW"
    )
    color = (
        "#f85149" if prob >= 65 else
        "#d29922" if prob >= 45 else
        "#58a6ff" if prob >= 25 else
        "#3fb950"
    )

    # Target quadrant probabilities
    all_q = [
        ("rising",  "falling"),
        ("rising",  "rising"),
        ("falling", "rising"),
        ("falling", "falling"),
    ]
    q_names = {
        ("rising",  "falling"): "🚀 Expansion",
        ("rising",  "rising"):  "🔥 Stagflation",
        ("falling", "rising"):  "❄️ Recession",
        ("falling", "falling"): "🌧 Deflation",
    }
    raw = {}
    for q in all_q:
        if q == (gdp_trend, cpi_trend):
            raw[q] = 0.0
            continue
        flips = sum(a != b for a, b in zip(q, (gdp_trend, cpi_trend)))
        w     = 1.5 if flips == 1 else 0.5

        qg, qc = q
        if qg != gdp_trend:
            w += 1.5 if (
                (qg == "falling" and ls[1] <= 0 and ls[2] <= 0) or
                (qg == "rising"  and ls[1] >= 0 and ls[2] >= 0)
            ) else 0.3
        if qc != cpi_trend:
            w += 0.8 if (
                (qc == "rising"  and macro["yc_signal"] in ("flat", "inverted")) or
                (qc == "falling" and macro["yc_signal"] in ("steepening", "normal"))
            ) else 0.3
        raw[q] = max(0.0, w)

    tw     = sum(raw.values()) or 1.0
    target = {
        q_names[q]: round(raw[q] / tw * prob)
        for q in all_q
        if q != (gdp_trend, cpi_trend)
    }
    top = max(target, key=target.get) if target else "Unknown"

    # What positions would the destination regime imply?
    next_regime  = next((q for q in all_q if q_names[q] == top), None)
    next_tilts   = REGIME_TILTS.get(next_regime, [])[:3] if next_regime else []
    current_set  = set(REGIME_TILTS.get((gdp_trend, cpi_trend), []))
    new_tilts    = [t for t in next_tilts if t not in current_set]
    exit_tilts   = [t for t in list(current_set)[:3] if t not in next_tilts]

    return {
        "prob":        prob,
        "label":       label,
        "color":       color,
        "stay":        max(0, 100 - prob),
        "target":      target,
        "top":         top,
        "new_tilts":   new_tilts,
        "exit_tilts":  exit_tilts,
        "signals": [
            ("Lead divergence", round(div_s    * 100), f"{sum(1 for s in div_scores if s > 0.5)}/3 indicators contradict regime"),
            ("Yield curve",     round(yc_s     * 100), macro["yc_signal"]),
            ("Streak age",      round(streak_s * 100), f"{ms} periods vs median {med}q"),
            ("Axis pressure",   round(axis_s   * 100), f"GDP {macro['gdp_mom']:+.2f}% · CPI {macro['cpi_mom']:+.2f}%"),
        ],
    }


# ── Hedge logic ────────────────────────────────────────────────────────────────

def hedge_decision(prices: pd.DataFrame) -> tuple[str, float, float, bool]:
    """
    Returns (ticker, voo_price, sma200, is_crisis).
    Crisis = VOO below its 200-day SMA → rotate to SH.
    Normal = VOO above SMA → hold BIL.
    """
    if "VOO" not in prices.columns:
        return "BIL", 0.0, 0.0, False
    voo_px  = float(prices["VOO"].iloc[-1])
    sma200  = float(prices["VOO"].tail(200).mean()) if len(prices) >= 200 else voo_px
    crisis  = voo_px < sma200
    ticker  = "SH" if crisis else "BIL"
    return ticker, round(voo_px, 2), round(sma200, 2), crisis


# ── Rebalancing orders ─────────────────────────────────────────────────────────

def compute_orders(
    target_map:    dict,
    current_map:   dict,
    prices:        pd.DataFrame,
    highs:         pd.DataFrame,
    lows:          pd.DataFrame,
    cost_bases:    dict,
    tolerance_pct: float,
    sched_due:     bool,
    stopped:       list,
) -> list:
    """
    Compute rebalancing orders.

    Priority:
      0 — Stop-loss triggered (always execute)
      1 — Threshold breach (drift > tolerance)
      2 — Scheduled rebalance (calendar due, any drift > 1%)

    Returns list of order dicts sorted by priority then drift magnitude.
    """
    from config import ETF_DATA

    orders = []
    for ticker, tm in target_map.items():
        target_pct  = tm["target_pct"]
        current_pct = current_map.get(ticker, 0.0)
        drift       = round(current_pct - target_pct, 2)
        cb          = cost_bases.get(ticker, 0.0)
        px          = float(prices[ticker].iloc[-1]) if ticker in prices.columns else 0.0

        is_stopped   = ticker in stopped and cb > 0
        is_threshold = abs(drift) >= tolerance_pct
        is_sched     = sched_due and abs(drift) > 1.0

        if not (is_stopped or is_threshold or is_sched):
            continue

        if is_stopped:
            priority = 0
            trigger  = "🚨 STOP"
            direction = "SELL ALL"
        elif drift > 0:
            priority  = 1 if is_threshold else 2
            trigger   = f"⚠ DRIFT +{abs(drift):.1f}%" if is_threshold else "📅 SCHED"
            direction = "▼ SELL"
        else:
            priority  = 1 if is_threshold else 2
            trigger   = f"⚠ DRIFT {drift:.1f}%" if is_threshold else "📅 SCHED"
            direction = "▲ BUY"

        # Tax note for sells
        tlh   = ETF_DATA.get(ticker, {}).get("tlh") or "—"
        tax   = ""
        if "SELL" in direction and cb > 0 and px > 0:
            pnl_pct = (px - cb) / cb * 100
            tax = (
                f"Loss harvest → TLH: {tlh}"
                if pnl_pct < 0 else
                "Check hold period (ST vs LT gains)"
            )
        elif "BUY" in direction:
            tax = "New cost basis on purchase"

        orders.append({
            "priority":  priority,
            "ticker":    ticker,
            "bucket":    tm["bucket"],
            "direction": direction,
            "trigger":   trigger,
            "drift":     drift,
            "price":     px,
            "tax":       tax,
        })

    orders.sort(key=lambda o: (o["priority"], -abs(o["drift"])))
    return orders

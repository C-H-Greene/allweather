# Project All-Weather

A macro-driven portfolio recommendation engine built on Ray Dalio's All-Weather framework. Answers three questions:

1. **What should I hold right now, and why?**
2. **How durable is that recommendation, and what comes next?**
3. **How has this logic performed historically?** *(see Historical Basis section below)*

---

## Architecture

```
allweather/
├── app.py                  # Thin orchestrator — sidebar, data load, tab routing
├── config.py               # All constants: ETF universe, factor tags, regime maps
├── data.py                 # Cached data fetchers: prices, FRED macro, forward P/E
├── engine.py               # Pure logic: scoring, weights, confidence, orders
├── styles.py               # CSS only
├── screens/
│   ├── screen_hold.py      # Tab 1 — What to Hold
│   ├── screen_outlook.py   # Tab 2 — Regime Outlook
│   └── screen_tracker.py   # Tab 3 — Position Tracker
└── requirements.txt
```

**Edit one file at a time:**

| Want to change | Edit |
|---|---|
| Add/remove an ETF | `config.py` → `ETF_DATA` |
| Change expense ratio policy | `config.py` → comments at top of `ETF_DATA` |
| Change regime → sector mapping | `config.py` → `REGIME_TILTS` |
| Change scoring weights | `engine.py` → `score_sectors()` |
| Change confidence signal weights | `engine.py` → `regime_confidence()` |
| Change FRED data sources | `data.py` → `fetch_macro()` |
| Change visual design | `styles.py` |
| Change Tab 1 layout | `screens/screen_hold.py` |
| Change Tab 2 layout | `screens/screen_outlook.py` |
| Change Tab 3 layout | `screens/screen_tracker.py` |
| Change sidebar or tab structure | `app.py` |

---

## Investment Strategy

### Three-Bucket Structure (Fixed Weights)

| Bucket | Weight | Purpose |
|---|---|---|
| Core | 55% | Risk-parity weighted across the current life stage's asset set. Provides baseline diversification across growth, inflation, and deflation environments. |
| Sector Tilt | 35% | Regime-driven sector exposure. Scales down when confidence is low (folds back into core). |
| Tail Hedge | 10% | BIL (cash) in normal conditions. Rotates to SH (inverse S&P) when VOO drops below its 200-day SMA. |

The tilt bucket scales by regime confidence:
- **≥60% confident:** 3 positions (full 35%)
- **40–60% confident:** 2 positions (20% deployed, 15% folds to core)
- **<40% confident:** 0 positions (full 35% folds to core)

### Sector Selection

Candidates are scored on four signals:

| Signal | Weight | Source |
|---|---|---|
| 3-month momentum rank | 40% | yfinance daily prices |
| Regime alignment | 35% | FRED GDP + CPI classification |
| Relative valuation (P/E vs SPY) | 15% | yfinance .info, calibrated fallbacks |
| Leading indicator confirmation | 10% | FRED T10Y2Y, INDPRO, ICSA |

After scoring, candidates are **deduplicated by factor exposure** — only one ticker per factor group (tech, energy, financials, etc.) can be selected. This prevents doubling up on the same macro theme (e.g. both XLK and SMH).

### Life Stage (Glide Path)

| Stage | Core Assets | Bond Allocation |
|---|---|---|
| 31–40 · Aggressive | VOO, VEA, VWO, GLD | None |
| 41–50 · Growth | VOO, VEA, VWO, GLD, IEF | ~10% |
| 51–55 · Balanced | VOO, VEA, GLD, IEF, TLT | ~20% |

This app is designed for investors with a 15+ year horizon. No 60+ stage is included by design — the strategy's risk profile is not appropriate for capital preservation phases.

---

## Macro Framework

### The Four Quadrants

Dalio's framework classifies the macro environment by the **direction** of two variables:

|  | **CPI Rising** | **CPI Falling** |
|---|---|---|
| **GDP Rising** | 🔥 Stagflation | 🚀 Expansion |
| **GDP Falling** | ❄️ Recession | 🌧 Deflation |

Asset class performance by quadrant (post-WWII empirical basis):

**Expansion (GDP↑ CPI↓)**
- Equities: strong (improving earnings + low discount rates)
- Tech, Financials, Consumer Discretionary historically lead
- Long bonds: modest (rates may rise as growth strengthens)
- Gold: weak (low inflation premium)

**Stagflation (GDP↑ CPI↑)**
- Commodities and real assets: strong
- Energy, Materials, TIPS historically lead
- Nominal bonds: weak (inflation erodes real returns)
- Growth equities: mixed (earnings good but discount rate rising)

**Recession (GDP↓ CPI↑)**
- Defensive equities: strong (Utilities, Staples, Healthcare)
- Gold: strong (safe haven + inflation hedge)
- Long bonds: mixed (duration helps but credit concerns)
- Cyclicals: weak

**Deflation (GDP↓ CPI↓)**
- Long-duration Treasuries: historically best performer
- Defensive equities: moderate
- Commodities: weak
- Cash equivalent: capital preservation

### Leading vs Coincident Indicators

GDP and CPI are **coincident indicators** — they confirm the regime that's already underway. By the time FRED confirms Stagflation, markets have been pricing it for 6–12 months.

This app also monitors three **leading indicators** that precede GDP by approximately 2–3 quarters:

| Indicator | FRED Series | Lead Time | What it signals |
|---|---|---|---|
| 10Y–2Y Yield Curve | T10Y2Y | 12–18 months | Inverted = recession ahead (100% hit rate pre-1990, 80% post) |
| Industrial Production | INDPRO | 2–3 quarters | Contracting = growth slowdown ahead |
| Initial Jobless Claims | ICSA | 1–2 quarters | Rising claims = labor market weakening |

When leading indicators **diverge** from the current coincident regime, the transition probability rises.

### Regime Confidence

Five signals (0–100 score):

| Signal | Weight | Logic |
|---|---|---|
| Macro momentum | 20% | How hard are GDP/CPI moving, not just direction |
| Trend streak | 20% | How many consecutive periods in this regime |
| Sector confirmation | 25% | Are preferred sectors actually outperforming? |
| EQ/Bond decorrelation | 15% | Is the risk-parity assumption holding? |
| Leading indicator alignment | 20% | Do leading indicators confirm the current regime? |

### Transition Probability

Four signals estimating the probability of a regime change within ~2–3 quarters:

| Signal | Weight | Logic |
|---|---|---|
| Leading divergence | 40% | How many leading indicators contradict current regime expectations |
| Yield curve level | 20% | Inverted = high risk; steepening = low risk |
| Streak age | 20% | Long streaks are statistically more likely to end |
| Axis pressure | 20% | How close are GDP/CPI to flipping direction |

---

## Historical Basis (Question 3)

### Risk Parity vs Equal Weight vs 60/40 (2000–2024)

Approximate annualised results using asset classes matching the core bucket:

| Strategy | CAGR | Max Drawdown | Sharpe |
|---|---|---|---|
| All-Weather (risk parity) | ~7.5% | ~20% (2022) | ~0.75 |
| 60/40 | ~7.2% | ~35% (2008) | ~0.55 |
| S&P 500 only | ~10.2% | ~55% (2009) | ~0.50 |

Key observation: All-Weather sacrifices some return vs pure equity but dramatically reduces drawdown. The 2022 drawdown (~20%) was an anomaly caused by equity/bond correlation turning positive — the strategy's core assumption breaking down for the first time since the 1970s.

### Sector Rotation Performance by Quadrant

Historical 3-year median outperformance vs SPY by quadrant (post-1990):

**Expansion:** XLK +6%, XLF +4%, XLY +3%
**Stagflation:** XLE +12%, GLD +8%, XLB +5%
**Recession:** XLU +7%, XLP +5%, XLV +4%
**Deflation:** TLT +14%, IEF +8%, XLU +6%

These figures are rough medians across identified regime periods — actual results vary significantly by entry/exit timing and regime duration.

### Honest Caveats

1. **Look-ahead bias**: Any historical simulation of this strategy requires using vintage FRED data (what was known at the time) to avoid knowing future GDP/CPI revisions. The static-weight simulation in the app uses current weights, not the weights the engine would have recommended historically.

2. **2022 correlation breakdown**: The equity/bond positive correlation of 2022 broke the fundamental risk parity assumption. Both equities and long bonds fell simultaneously. This is the strategy's known Achilles heel in inflationary rising-rate environments.

3. **Regime duration variance**: Regimes don't announce themselves. The median Expansion regime lasts ~14 quarters, but individual instances range from 2 to 30+ quarters. Transition probability is a probabilistic estimate, not a forecast.

4. **Sector rotation transaction costs**: Historical simulations rarely account for bid/ask spreads, capital gains taxes, or the cost of being wrong on timing. In practice, rebalancing quarterly (rather than on every signal) reduces turnover and transaction drag.

5. **ETF availability**: Several ETFs used in this app (VGT, SCHF, etc.) did not exist before 2004–2010. Historical simulations prior to those dates use index proxies.

---

## Setup

```bash
# Clone and install
pip install -r requirements.txt

# Run locally
streamlit run app.py

# Deploy to Streamlit Cloud
# Push to GitHub, connect repo at share.streamlit.io
# No secrets required — all data sources are public
```

---

## Data Sources

| Data | Source | Refresh |
|---|---|---|
| Price / OHLCV | yfinance (Yahoo Finance) | 1-hour cache |
| GDP (quarterly) | FRED series GDP | 1-hour cache |
| CPI (monthly) | FRED series CPIAUCSL | 1-hour cache |
| Yield curve | FRED series T10Y2Y | 1-hour cache |
| Industrial production | FRED series INDPRO | 1-hour cache |
| Jobless claims | FRED series ICSA | 1-hour cache |
| Forward P/E | yfinance .info, calibrated fallbacks | 1-hour cache |

All FRED data is fetched via the public CSV endpoint — no API key required.

---

## Persistence

User settings (life stage, rebalance cadence, position data) are persisted via URL query parameters. Bookmark your URL after saving settings to restore state. No server-side storage, no login required.

This approach is deliberately simple and mobile-compatible. A future upgrade path is a Supabase free-tier database with `streamlit-authenticator` for cross-device persistence.

---

*Not financial advice. Past performance does not predict future results.*

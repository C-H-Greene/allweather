# 🌦 Project All-Weather

> A Python/Streamlit portfolio management dashboard implementing Bridgewater's **Risk Parity** and **Pure Alpha** frameworks for retail investors.

![Python](https://img.shields.io/badge/Python-3.10%2B-3b82f6?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35%2B-ff4b4b?style=flat-square&logo=streamlit&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10b981?style=flat-square)
![Data](https://img.shields.io/badge/Data-yfinance%20%2B%20FRED-f59e0b?style=flat-square)

---

## What It Does

Project All-Weather divides capital into three systematic buckets, each with a distinct job:

| Bucket | Size | Strategy | Purpose |
|--------|------|----------|---------|
| **Core All-Weather** | 60% | Volatility-Weighted Risk Parity | Survive all four economic quadrants |
| **Tactical Pure Alpha** | 30% | Regime-Driven Sector Momentum | Capture the current macro cycle |
| **Tail-Risk Hedge** | 10% | SMA-Triggered Crisis Rotation | Protect against systemic crashes |

---

## Architecture

### Part 1 — Core All-Weather (Risk Parity)

Allocates the core bucket across five assets using **inverse-volatility weighting**, so each position contributes equal risk rather than equal capital:

```
Weight_i = (1 / σ_i) / Σ(1 / σ_j)
```

| Asset | Role | Economic Quadrant |
|-------|------|-------------------|
| `VOO` | US Equities | Growth / Low Inflation |
| `TLT` | Long-Term Bonds | Deflation / Recession |
| `IEF` | Mid-Term Bonds | Moderate Growth |
| `GLD` | Gold | Inflation / Stagflation |
| `GSG` | Commodities | Rising Inflation |

Volatility is computed from **30-day realized log-returns**, annualized. This means bonds — with lower vol — naturally receive larger allocations, matching the Bridgewater insight that equities dominate most portfolios on a *risk* basis, not capital basis.

---

### Part 2 — Tactical Pure Alpha Engine

**Step 1 — Regime Identification**

Pulls `GDP` and `CPIAUCSL` series from the FRED public API (no key required). Compares latest readings to prior periods to classify the current macro environment:

```
GDP Rising  + CPI Rising  → 🔥 Stagflation   → XLE, XLB, GLD
GDP Rising  + CPI Falling → 🚀 Expansion      → XLK, XLY, XLF
GDP Falling + CPI Rising  → ❄️ Recession      → XLU, XLP, XLV
GDP Falling + CPI Falling → 🌧 Deflation      → TLT, XLU, GLD
```

**Step 2 — Momentum Filter**

Ranks all 11 S&P 500 sector ETFs by **3-month total return**. Selects the top 3 that overlap with the current regime's preferred sectors. Regime-aligned sectors take priority; remaining slots fill with the highest-momentum names.

**Sectors Covered:** XLE, XLK, XLV, XLF, XLI, XLY, XLP, XLB, XLC, XLU, XLRE

---

### Part 3 — Tail-Risk Hedge

```
VOO > 200-Day SMA  →  Hedge in BIL  (Cash / T-Bills)
VOO < 200-Day SMA  →  Rotate into SH (Short S&P 500)
```

The 200-day SMA crossing is a battle-tested bear market signal. When breached, the hedge bucket rotates from cash into an inverse S&P position to provide direct downside protection during systemic drawdowns.

---

### Part 4 — Risk Management

**ATR Stop-Losses (Tactical Positions)**

Each tactical sector position carries a trailing stop calculated as:

```
Stop Price = Current Price − (2 × ATR₁₄)
```

ATR (Average True Range) over 14 days accounts for each sector's natural volatility range, preventing premature stops while capping maximum loss.

**Drift Report**

Enter your actual current portfolio weights to generate a rebalancing action list. The app computes percentage drift from target and classifies each position as:
- `✓ OK` — within ±1% of target
- `▲ BUY` — underweight, needs topping up
- `▼ SELL` — overweight, needs trimming

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/YOUR_USERNAME/project-all-weather.git
cd project-all-weather

# 2. Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`.

---

## Dependencies

```
streamlit>=1.35.0    # Dashboard framework
pandas>=2.0.0        # Data manipulation
numpy>=1.26.0        # Numerical computing
yfinance>=0.2.40     # Market data (Yahoo Finance)
requests>=2.31.0     # HTTP client
```

No API keys required. FRED macro data is fetched from the public CSV endpoint. Market data comes via `yfinance`.

> **Demo Mode**: If `yfinance` is network-blocked (e.g., restricted cloud environments), the app automatically falls back to synthetic price series generated with a seeded random walk, preserving all functionality for testing and presentation.

---

## Deploying to Streamlit Cloud

1. Fork this repo to your GitHub account
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub, select this repo, set `app.py` as the entry point
4. Deploy — no secrets or environment variables needed

---

## Sidebar Controls

| Parameter | Description | Default |
|-----------|-------------|---------|
| **Total Investment ($)** | Portfolio size in USD | $100,000 |
| **Core All-Weather %** | Core bucket weight | 60% |
| **Tactical Pure Alpha %** | Tactical bucket weight | 30% |
| **Hedge (auto)** | Remainder assigned to hedge | 10% |

The "Required Shares" for each position auto-calculate from your total investment amount.

---

## Dashboard Sections

### Macro Regime Matrix
A 2×2 grid showing all four economic quadrants. The current regime (based on live FRED data) is highlighted with a pulsing indicator.

### Tail-Risk Hedge Status
Shows VOO vs. its 200-day SMA with the percentage distance. Red alert banner activates when crisis mode triggers.

### Tab 1 — Allocation Engine
- **Core bucket**: Allocation bars with inverse-vol weights and 30-day volatility per asset
- **Tactical bucket**: Top 3 sectors with 3-month returns, ATR stop-loss prices, and regime-alignment badges
- **Portfolio summary**: Dollar amounts for all three buckets at a glance

### Tab 2 — Sector Momentum
Full ranking of all 11 SPDR sector ETFs by 3-month return with momentum bars, selection status, and regime-alignment flags.

### Tab 3 — Drift Report
Editable table. Enter your current holdings as percentages. The report calculates drift, required actions, and an aggregate portfolio drift score.

---

## Theoretical Basis

This implementation draws from:

- **Ray Dalio / Bridgewater's All-Weather Portfolio** — asset allocation across four economic environments defined by growth and inflation surprises
- **Risk Parity** — equalizing risk contribution rather than capital allocation, pioneered by Bridgewater's Pure Alpha fund
- **Momentum Factor** — the well-documented tendency of recent outperformers to continue outperforming over 3–12 month horizons (Jegadeesh & Titman, 1993)
- **200-Day SMA as Bear Market Signal** — widely used by systematic trend-following strategies as a regime filter

---

## Disclaimer

This tool is for **educational and research purposes only**. It does not constitute financial advice. Past performance of any strategy does not guarantee future results. Always consult a qualified financial advisor before making investment decisions.

---

## License

MIT — use it, fork it, build on it.

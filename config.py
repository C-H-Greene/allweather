"""
config.py
All application constants. Edit this file to:
  - Add/remove ETFs
  - Change expense ratio thresholds
  - Update factor tags or regime mappings
  - Adjust bucket weights or glide path stages
"""

# ── Portfolio structure ────────────────────────────────────────────────────────
BUCKET_WEIGHTS = {"core": 0.55, "tilt": 0.35, "hedge": 0.10}

# Tilt allocation by regime confidence
# confidence >= 60 → 3 positions (full 35%)
# confidence 40-60 → 2 positions (20% deployed, 15% folds to core)
# confidence < 40  → 0 positions (full 35% folds to core)
TILT_SLOTS = {60: 3, 40: 2, 0: 0}

# ── Glide path ─────────────────────────────────────────────────────────────────
GLIDE_ASSETS = {
    "31–40 · Aggressive": {
        "assets": ["VOO", "VEA", "VWO", "GLD"],
        "desc":   "Pure equity + gold. Zero bond drag. Maximum compounding window.",
    },
    "41–50 · Growth": {
        "assets": ["VOO", "VEA", "VWO", "GLD", "IEF"],
        "desc":   "Adding mid-term bonds (~10% weight). Begin reducing sequence risk.",
    },
    "51–55 · Balanced": {
        "assets": ["VOO", "VEA", "GLD", "IEF", "TLT"],
        "desc":   "Reduced international, adding long bonds (~20%). Capital preservation begins.",
    },
}

# ── ETF Registry ───────────────────────────────────────────────────────────────
# Keys: ticker
# Values: name, er (expense ratio %), tlh (tax-loss harvest alternative), factors (list)
#
# FACTOR TAGS drive deduplication — two tickers sharing a primary factor
# cannot both be recommended in the tilt bucket simultaneously.
#
# ER POLICY: core/hedge max 0.20%, tilt max 0.35%

ETF_DATA = {
    # ── Core assets ────────────────────────────────────────────────────────────
    "VOO":  {"name": "Vanguard S&P 500",            "er": 0.03, "tlh": "IVV",  "factors": ["us_equity",      "growth"]},
    "IVV":  {"name": "iShares Core S&P 500",        "er": 0.03, "tlh": "VOO",  "factors": ["us_equity",      "growth"]},
    "VEA":  {"name": "Vanguard Dev. Markets",        "er": 0.05, "tlh": "SCHF", "factors": ["intl_equity",    "growth"]},
    "SCHF": {"name": "Schwab Intl Equity",           "er": 0.06, "tlh": "VEA",  "factors": ["intl_equity",    "growth"]},
    "VWO":  {"name": "Vanguard Emerging Mkts",       "er": 0.08, "tlh": "IEMG", "factors": ["em_equity",      "growth"]},
    "IEMG": {"name": "iShares Core EM",              "er": 0.09, "tlh": "VWO",  "factors": ["em_equity",      "growth"]},
    "GLD":  {"name": "SPDR Gold Shares",             "er": 0.40, "tlh": "IAU",  "factors": ["gold",           "inflation"]},
    "IAU":  {"name": "iShares Gold Trust",           "er": 0.25, "tlh": "GLD",  "factors": ["gold",           "inflation"]},
    "IEF":  {"name": "iShares 7-10yr Treasury",      "er": 0.15, "tlh": "VGIT", "factors": ["mid_bond",       "deflation"]},
    "VGIT": {"name": "Vanguard Interm-Term Treasury", "er": 0.04, "tlh": "IEF",  "factors": ["mid_bond",       "deflation"]},
    "TLT":  {"name": "iShares 20yr+ Treasury",       "er": 0.15, "tlh": "VGLT", "factors": ["long_bond",      "deflation", "recession"]},
    "VGLT": {"name": "Vanguard Long-Term Treasury",  "er": 0.04, "tlh": "TLT",  "factors": ["long_bond",      "deflation", "recession"]},
    "TIP":  {"name": "iShares TIPS Bond",            "er": 0.19, "tlh": "SCHP", "factors": ["inflation_bond", "inflation"]},
    "SCHP": {"name": "Schwab U.S. TIPS",             "er": 0.03, "tlh": "TIP",  "factors": ["inflation_bond", "inflation"]},

    # ── Sector tilt candidates ─────────────────────────────────────────────────
    "XLE":  {"name": "Energy",                       "er": 0.09, "tlh": "VDE",  "factors": ["energy",         "commodity",    "inflation"]},
    "VDE":  {"name": "Vanguard Energy",              "er": 0.10, "tlh": "XLE",  "factors": ["energy",         "commodity",    "inflation"]},
    "XLK":  {"name": "Technology",                   "er": 0.09, "tlh": "VGT",  "factors": ["tech",           "growth",       "rate_sensitive"]},
    "VGT":  {"name": "Vanguard Information Tech",    "er": 0.10, "tlh": "XLK",  "factors": ["tech",           "growth",       "rate_sensitive"]},
    "SMH":  {"name": "VanEck Semiconductors",        "er": 0.35, "tlh": "SOXX", "factors": ["tech",           "growth",       "cyclical"]},
    "SOXX": {"name": "iShares Semiconductor",        "er": 0.35, "tlh": "SMH",  "factors": ["tech",           "growth",       "cyclical"]},
    "XLV":  {"name": "Health Care",                  "er": 0.09, "tlh": "VHT",  "factors": ["healthcare",     "defensive"]},
    "VHT":  {"name": "Vanguard Health Care",         "er": 0.10, "tlh": "XLV",  "factors": ["healthcare",     "defensive"]},
    "XLF":  {"name": "Financials",                   "er": 0.09, "tlh": "VFH",  "factors": ["financials",     "growth",       "rate_sensitive"]},
    "VFH":  {"name": "Vanguard Financials",          "er": 0.10, "tlh": "XLF",  "factors": ["financials",     "growth",       "rate_sensitive"]},
    "XLI":  {"name": "Industrials",                  "er": 0.09, "tlh": "VIS",  "factors": ["industrial",     "growth",       "cyclical"]},
    "VIS":  {"name": "Vanguard Industrials",         "er": 0.10, "tlh": "XLI",  "factors": ["industrial",     "growth",       "cyclical"]},
    "XLY":  {"name": "Consumer Disc.",               "er": 0.09, "tlh": "VCR",  "factors": ["consumer_disc",  "growth",       "cyclical"]},
    "VCR":  {"name": "Vanguard Consumer Disc.",      "er": 0.10, "tlh": "XLY",  "factors": ["consumer_disc",  "growth",       "cyclical"]},
    "XLP":  {"name": "Consumer Staples",             "er": 0.09, "tlh": "VDC",  "factors": ["consumer_staples","defensive",   "inflation"]},
    "VDC":  {"name": "Vanguard Consumer Staples",    "er": 0.10, "tlh": "XLP",  "factors": ["consumer_staples","defensive",   "inflation"]},
    "XLB":  {"name": "Materials",                    "er": 0.09, "tlh": "VAW",  "factors": ["materials",      "commodity",    "inflation"]},
    "VAW":  {"name": "Vanguard Materials",           "er": 0.10, "tlh": "XLB",  "factors": ["materials",      "commodity",    "inflation"]},
    "XLU":  {"name": "Utilities",                    "er": 0.09, "tlh": "VPU",  "factors": ["utilities",      "defensive",    "rate_sensitive"]},
    "VPU":  {"name": "Vanguard Utilities",           "er": 0.10, "tlh": "XLU",  "factors": ["utilities",      "defensive",    "rate_sensitive"]},
    "XLRE": {"name": "Real Estate",                  "er": 0.09, "tlh": "VNQ",  "factors": ["real_estate",    "rate_sensitive","inflation"]},
    "VNQ":  {"name": "Vanguard Real Estate",         "er": 0.13, "tlh": "XLRE", "factors": ["real_estate",    "rate_sensitive","inflation"]},
    "XLC":  {"name": "Communication Services",       "er": 0.09, "tlh": None,   "factors": ["tech_adjacent",  "growth"]},

    # ── Tail hedge ─────────────────────────────────────────────────────────────
    "BIL":  {"name": "SPDR Bloomberg 1-3mo T-Bill",  "er": 0.14, "tlh": "SHV",  "factors": ["cash",           "defensive"]},
    "SHV":  {"name": "iShares Short Treasury Bond",  "er": 0.15, "tlh": "BIL",  "factors": ["cash",           "defensive"]},
    "SH":   {"name": "ProShares Short S&P 500",      "er": 0.88, "tlh": None,   "factors": ["inverse_equity", "crisis"]},
}

# Tickers that are TLH alternatives — not recommended as primary positions
TLH_ONLY = {"IVV","SCHF","IEMG","IAU","VGIT","VGLT","SCHP",
             "VDE","VGT","SOXX","VHT","VFH","VIS","VCR",
             "VDC","VAW","VPU","VNQ","SHV"}

# ── Factor deduplication ───────────────────────────────────────────────────────
# Within each group, only the highest-scoring ticker is selected.
# "tech" and "tech_adjacent" are in the same group — XLK and XLC can't coexist.
EXCLUSIVE_FACTOR_GROUPS = [
    ["tech", "tech_adjacent"],
    ["real_estate"],
    ["gold"],
    ["energy"],
    ["consumer_disc"],
    ["consumer_staples"],
    ["healthcare"],
    ["financials"],
    ["industrial"],
    ["materials"],
    ["utilities"],
    ["mid_bond"],
    ["long_bond"],
    ["inflation_bond"],
]

# ── Regime definitions ─────────────────────────────────────────────────────────
REGIME_META = {
    ("rising",  "falling"): {
        "name":      "Expansion",
        "emoji":     "🚀",
        "color":     "#3fb950",
        "rationale": (
            "Growth accelerating, inflation contained. Risk assets historically outperform. "
            "Cyclical and rate-sensitive sectors benefit from improving earnings "
            "and low discount rates."
        ),
    },
    ("rising",  "rising"): {
        "name":      "Stagflation",
        "emoji":     "🔥",
        "color":     "#f85149",
        "rationale": (
            "Growth with rising inflation. Commodities and real assets preserve "
            "purchasing power. Nominal bonds lose value; inflation-linked instruments "
            "and hard assets are preferred."
        ),
    },
    ("falling", "rising"): {
        "name":      "Recession",
        "emoji":     "❄️",
        "color":     "#d29922",
        "rationale": (
            "Growth contracting, inflation elevated. Defensive positioning required. "
            "Utilities, staples, and healthcare provide stability; "
            "gold hedges systemic risk."
        ),
    },
    ("falling", "falling"): {
        "name":      "Deflation",
        "emoji":     "🌧",
        "color":     "#58a6ff",
        "rationale": (
            "Growth and inflation both falling. Long-duration Treasuries historically surge. "
            "Defensive sectors outperform; avoid cyclicals and commodities."
        ),
    },
}

# Regime → preferred tilt candidates (ordered by priority)
REGIME_TILTS = {
    ("rising",  "falling"): ["XLK", "SMH", "XLF", "XLI", "XLY", "XLC"],
    ("rising",  "rising"):  ["XLE", "XLB", "XLP", "TIP", "XLI"],
    ("falling", "rising"):  ["XLU", "XLP", "XLV", "GLD", "TLT", "TIP"],
    ("falling", "falling"): ["TLT", "IEF", "XLU", "XLV", "XLP"],
}

# ── Forward P/E fallback estimates (2024-2025 baseline) ───────────────────────
PE_ESTIMATES = {
    "XLK":  29.5, "XLC":  20.8, "XLY":  24.1,
    "XLF":  15.2, "XLI":  21.3, "XLV":  18.4,
    "XLB":  19.6, "XLRE": 36.2, "XLE":  12.8,
    "XLP":  20.1, "XLU":  17.9, "SMH":  28.0,
}
SPY_PE_ESTIMATE = 21.5

"""
screens/screen_hold.py
Tab 1 — What to Hold

Renders:
  - Regime banner with confidence score
  - Core bucket (inv-vol weighted positions with rationale)
  - Sector tilt bucket (scored positions, stop prices, TLH alts)
  - Tail hedge bucket
  - Right column: macro signal rows + confidence breakdown + quadrant matrix
"""

import streamlit as st
from config import ETF_DATA, REGIME_META, BUCKET_WEIGHTS


def render(
    prices,
    macro:           dict,
    regime_key:      tuple,
    conf:            dict,
    core_assets:     list,
    core_weights:    dict,
    selected_tilts:  list,
    n_tilts:         int,
    hedge_ticker:    str,
    voo_sma_pct:     float,
    crisis:          bool,
    stopped:         list,
    get_stop_fn,          # callable(ticker) → (stop_px, atr_val)
):
    gdp_trend = macro["gdp_trend"]
    cpi_trend = macro["cpi_trend"]
    meta      = REGIME_META.get(regime_key, {})
    quad_name = meta.get("name",      "Unknown")
    quad_emoji= meta.get("emoji",     "❓")
    quad_color= meta.get("color",     "#7d8590")
    quad_rat  = meta.get("rationale", "")

    gdp_c = "#3fb950" if gdp_trend == "rising" else "#f85149"
    cpi_c = "#f85149" if cpi_trend == "rising" else "#3fb950"

    # ── Regime banner ─────────────────────────────────────────────────────────
    conf_score = conf.get("score", 0)
    conf_color = conf.get("color", "#7d8590")
    conf_label = conf.get("label", "—")
    gdp_mom_str = f"{macro['gdp_mom']:+.2f}%"
    cpi_mom_str = f"{macro['cpi_mom']:+.2f}%"

    st.markdown(
        f'<div class="regime-banner" role="region" aria-label="Current macro regime: {quad_name}">'
        f'<div class="regime-emoji" aria-hidden="true">{quad_emoji}</div>'
        f'<div style="flex:1">'
        f'<div class="regime-name" style="color:{quad_color}">{quad_name}</div>'
        f'<div class="regime-meta">'
        f'GDP <b style="color:{gdp_c}">{gdp_trend.upper()}</b> ({gdp_mom_str})'
        f'&nbsp;·&nbsp;'
        f'CPI <b style="color:{cpi_c}">{cpi_trend.upper()}</b> ({cpi_mom_str})'
        f'</div>'
        f'<div class="regime-rationale">{quad_rat}</div>'
        f'</div>'
        f'<div class="regime-score">'
        f'<div class="regime-score-num" style="color:{conf_color}">{conf_score}</div>'
        f'<div class="regime-score-label">{conf_label}</div>'
        f'<div style="font-size:.6rem;color:var(--dim);margin-top:4px">regime confidence</div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Alerts ────────────────────────────────────────────────────────────────
    if stopped:
        stops_str = ", ".join(stopped)
        st.markdown(
            f'<div class="aw-alert aw-alert-warn" role="alert">'
            f'<span aria-hidden="true">⚠</span>'
            f'<span><b>Stop-loss triggered:</b> {stops_str}. '
            f'Replacement shown below. Clear in Position Tracker when re-entered.</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    if n_tilts == 0:
        st.markdown(
            '<div class="aw-alert aw-alert-info" role="status">'
            '<span aria-hidden="true">ℹ</span>'
            '<span><b>No sector tilt recommended.</b> '
            'Regime confidence below 40% — the 35% tilt allocation folds into core '
            'until macro signals clarify.</span>'
            '</div>',
            unsafe_allow_html=True,
        )

    # ── Two-column layout ─────────────────────────────────────────────────────
    left, right = st.columns([1.35, 1])

    with left:
        _render_core(core_assets, core_weights, n_tilts, prices)
        if n_tilts > 0:
            _render_tilt(selected_tilts, n_tilts, prices, get_stop_fn)
        _render_hedge(hedge_ticker, crisis, voo_sma_pct)

    with right:
        _render_signals(macro, gdp_c, cpi_c)
        _render_confidence(conf)
        _render_quadrant_matrix(regime_key)


# ── Core bucket ────────────────────────────────────────────────────────────────

def _render_core(core_assets, core_weights, n_tilts, prices):
    effective_pct = 55 + (35 if n_tilts == 0 else 0)

    st.markdown(
        f'<div class="bucket-card" role="region" aria-label="Core bucket">'
        f'<div class="bucket-header">'
        f'<span class="bucket-name">Core Bucket</span>'
        f'<span class="bucket-weight" style="color:#58a6ff">{effective_pct}%</span>'
        f'</div>',
        unsafe_allow_html=True,
    )

    for ticker in core_assets:
        w    = core_weights.get(ticker, 0)
        info = ETF_DATA.get(ticker, {})
        pct  = effective_pct * w
        tlh  = info.get("tlh")
        tlh_er = ETF_DATA.get(tlh, {}).get("er") if tlh else None
        tags = ", ".join(f.replace("_", " ") for f in info.get("factors", [])[:2])
        px   = float(prices[ticker].iloc[-1]) if ticker in prices.columns else 0

        tlh_line = (
            f'<div class="pos-tlh">TLH alt → {tlh} ({tlh_er:.2f}% ER)</div>'
            if tlh and tlh_er else ""
        )
        st.markdown(
            f'<div class="pos-row">'
            f'<div><div class="pos-ticker">{ticker}</div>'
            f'<div style="font-family:var(--mono);font-size:.62rem;color:var(--dim)">'
            f'{pct:.1f}%</div></div>'
            f'<div><div class="pos-name">{info.get("name","")}</div>'
            f'<div class="pos-why">{tags} · inverse-vol weight</div>'
            f'{tlh_line}</div>'
            f'<div class="pos-weight">${px:.0f}</div>'
            f'<div class="pos-er">{info.get("er",0):.2f}%<br><span style="font-size:.58rem">ER</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ── Tilt bucket ────────────────────────────────────────────────────────────────

def _render_tilt(selected_tilts, n_tilts, prices, get_stop_fn):
    tilt_per = round(35 / n_tilts)

    st.markdown(
        '<div class="bucket-card" role="region" aria-label="Sector tilt bucket">'
        '<div class="bucket-header">'
        '<span class="bucket-name">Sector Tilt</span>'
        '<span class="bucket-weight" style="color:#3fb950">35%</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    for s in selected_tilts:
        ticker = s["ticker"]
        info   = ETF_DATA.get(ticker, {})
        stop_px, atr_val = get_stop_fn(ticker)
        px     = float(prices[ticker].iloc[-1]) if ticker in prices.columns else 0
        tlh    = info.get("tlh")
        tlh_er = ETF_DATA.get(tlh, {}).get("er") if tlh else None

        # Build pill badges as string concat — never inside f-string braces
        regime_pill = (
            '<span class="pill pill-regime">● regime</span>'
            if s["is_preferred"] else
            '<span class="pill pill-momentum">● momentum</span>'
        )
        pe     = s.get("pe_data", {})
        pe_val = pe.get("fwd_pe")
        pe_str = f'{pe_val:.1f}×' if pe_val else "—"
        val    = pe.get("valuation", "fair")
        pe_col = "#3fb950" if val == "cheap" else "#f85149" if val == "expensive" else "#7d8590"
        ret_str = f'{s["ret_3m"]*100:+.1f}%'

        pe_pill = (
            f'<span class="pill pill-pe" style="color:{pe_col}">P/E {pe_str}</span>'
        )
        ret_pill = (
            f'<span class="pill pill-momentum">{ret_str} 3M</span>'
        )

        tlh_line = (
            f'<div class="pos-tlh">TLH alt → {tlh} ({tlh_er:.2f}% ER)</div>'
            if tlh and tlh_er else ""
        )
        stop_line = (
            f'<div class="pos-stop">Stop ${stop_px:.2f} &nbsp;(2×ATR ${atr_val:.2f})</div>'
            if stop_px > 0 else ""
        )

        st.markdown(
            f'<div class="pos-row">'
            f'<div><div class="pos-ticker">{ticker}</div>'
            f'<div style="font-family:var(--mono);font-size:.62rem;color:var(--dim)">'
            f'{tilt_per}%</div></div>'
            f'<div>'
            f'<div class="pos-name">{info.get("name","")}</div>'
            f'<div style="display:flex;gap:4px;flex-wrap:wrap;margin-top:3px">'
            f'{regime_pill}{ret_pill}{pe_pill}</div>'
            f'<div class="pos-why">{s.get("rationale","")}</div>'
            f'{tlh_line}{stop_line}'
            f'</div>'
            f'<div class="pos-weight">${px:.0f}</div>'
            f'<div class="pos-er">{info.get("er",0):.2f}%<br><span style="font-size:.58rem">ER</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown('</div>', unsafe_allow_html=True)


# ── Tail hedge ─────────────────────────────────────────────────────────────────

def _render_hedge(hedge_ticker, crisis, voo_sma_pct):
    info    = ETF_DATA.get(hedge_ticker, {})
    h_color = "#f85149" if crisis else "#3fb950"
    sign    = f"{voo_sma_pct:+.1f}%"
    reason  = (
        f"VOO {sign} vs 200d SMA — crisis mode, inverse equity hedge"
        if crisis else
        f"VOO {sign} vs 200d SMA — normal regime, cash equivalent"
    )
    aria = "Tail hedge bucket — CRISIS MODE active" if crisis else "Tail hedge bucket"

    st.markdown(
        f'<div class="bucket-card" role="region" aria-label="{aria}">'
        f'<div class="bucket-header">'
        f'<span class="bucket-name">Tail Hedge</span>'
        f'<span class="bucket-weight" style="color:{h_color}">10%</span>'
        f'</div>'
        f'<div class="pos-row">'
        f'<div><div class="pos-ticker" style="color:{h_color}">{hedge_ticker}'
        f'{"  🚨" if crisis else ""}</div></div>'
        f'<div><div class="pos-name">{info.get("name","")}</div>'
        f'<div class="pos-why">{reason}</div></div>'
        f'<div class="pos-weight">10%</div>'
        f'<div class="pos-er">{info.get("er",0):.2f}%<br><span style="font-size:.58rem">ER</span></div>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Macro signals (right column) ───────────────────────────────────────────────

def _render_signals(macro, gdp_c, cpi_c):
    st.markdown(
        '<div style="font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;'
        'text-transform:uppercase;color:var(--muted);margin-bottom:10px">'
        'Macro Signal Detail</div>',
        unsafe_allow_html=True,
    )

    yc_col = (
        "#f85149" if macro["yc_signal"] == "inverted" else
        "#d29922" if macro["yc_signal"] == "flat"     else
        "#3fb950"
    )
    pmi_col = (
        "#3fb950" if macro["pmi_signal"] == "expanding"   else
        "#f85149" if macro["pmi_signal"] == "contracting" else
        "#d29922"
    )
    cl_col = (
        "#3fb950" if macro["claims_signal"] == "improving"      else
        "#f85149" if macro["claims_signal"] == "deteriorating"  else
        "#d29922"
    )

    yc_val    = f'{macro["yc_current"]:+.2f}%' if macro["yc_current"] is not None else "—"
    pmi_val   = f'{macro["pmi_mom"]:+.2f}%'
    cl_val    = f'{macro["claims_current"]}K'   if macro["claims_current"] else "—"
    gdp_val   = f'{macro["gdp_mom"]:+.2f}%'
    cpi_val   = f'{macro["cpi_mom"]:+.2f}%'
    gdp_streak = macro["gdp_streak"]
    cpi_streak = macro["cpi_streak"]

    def row(name, val, color, bar_pct, desc, aria=""):
        bp = min(max(bar_pct, 0), 100)
        al = aria if aria else f"{name} {val}"
        return (
            f'<div class="signal-row" aria-label="{al}">'
            f'<div class="signal-name">{name}</div>'
            f'<div class="signal-val" style="color:{color}">{val}</div>'
            f'<div class="signal-track">'
            f'<div style="height:4px;width:{bp:.0f}%;background:{color};border-radius:2px"></div>'
            f'</div>'
            f'<div class="signal-desc">{desc}</div>'
            f'</div>'
        )

    rows = (
        row("GDP trend",    gdp_val, gdp_c,  min(abs(macro["gdp_mom"])/2*100,100),
            f'{macro["gdp_trend"]} · {gdp_streak}q', f"GDP {macro['gdp_trend']} {gdp_val}") +
        row("CPI trend",    cpi_val, cpi_c,  min(abs(macro["cpi_mom"])/2*100,100),
            f'{macro["cpi_trend"]} · {cpi_streak}q', f"CPI {macro['cpi_trend']} {cpi_val}") +
        row("Yield curve",  yc_val,  yc_col, min(abs(macro["yc_current"] or 0)/2*100,100),
            macro["yc_signal"], f"Yield curve {macro['yc_signal']} {yc_val}") +
        row("Ind. prod.",   pmi_val, pmi_col,min(abs(macro["pmi_mom"])/2*100,100),
            macro["pmi_signal"], f"Industrial production {macro['pmi_signal']}") +
        row("Jobless claims",cl_val, cl_col, 50,
            macro["claims_signal"], f"Jobless claims {macro['claims_signal']} {cl_val}")
    )

    st.markdown(
        '<div style="background:var(--bg1);border:1px solid var(--border);'
        'border-radius:var(--radius);padding:12px 14px;margin-bottom:12px">'
        + rows + '</div>',
        unsafe_allow_html=True,
    )


# ── Confidence breakdown ───────────────────────────────────────────────────────

def _render_confidence(conf):
    score = conf.get("score", 0)
    with st.expander(f"Confidence breakdown · {score}/100", expanded=False):
        for name, val in conf.get("signals", []):
            c = "#3fb950" if val >= 70 else "#d29922" if val >= 40 else "#f85149"
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'font-family:var(--mono);font-size:.65rem;padding:5px 0;'
                f'border-bottom:1px solid var(--border)" '
                f'role="meter" aria-valuenow="{val}" aria-valuemin="0" aria-valuemax="100" '
                f'aria-label="{name}: {val} out of 100">'
                f'<span style="color:var(--muted)">{name}</span>'
                f'<span style="color:{c}">{val}/100</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Quadrant matrix ────────────────────────────────────────────────────────────

def _render_quadrant_matrix(regime_key):
    st.markdown(
        '<div style="font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;'
        'text-transform:uppercase;color:var(--muted);margin:12px 0 8px">'
        'Quadrant Matrix</div>',
        unsafe_allow_html=True,
    )

    cells = [
        ("rising",  "falling", "Expansion",   "🚀"),
        ("rising",  "rising",  "Stagflation",  "🔥"),
        ("falling", "falling", "Deflation",    "🌧"),
        ("falling", "rising",  "Recession",    "❄️"),
    ]

    html = (
        '<div class="quad-grid" role="grid" '
        'aria-label="Economic regime quadrant matrix">'
    )
    for gdp, cpi, name, emoji in cells:
        active  = (gdp, cpi) == regime_key
        cls     = "quad-cell active" if active else "quad-cell"
        tc      = "color:var(--text)" if active else "color:var(--muted)"
        now_div = '<div class="quad-cell-now">◉ NOW</div>' if active else ""
        html += (
            f'<div class="{cls}" role="gridcell" '
            f'aria-selected="{str(active).lower()}" aria-label="{name}">'
            f'<div class="quad-cell-emoji">{emoji}</div>'
            f'<div class="quad-cell-name" style="{tc}">{name}</div>'
            f'{now_div}</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)

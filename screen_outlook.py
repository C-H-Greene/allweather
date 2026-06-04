"""
screens/screen_outlook.py
Tab 2 — Regime Outlook

Renders:
  - Transition probability bar + stay probability
  - Destination regime distribution
  - Watch-to-exit / watch-to-enter position implications
  - Three leading indicator cards (yield curve, ind. production, claims)
  - Leading composite summary
"""

import streamlit as st


def render(macro: dict, tp: dict):
    st.markdown(
        '<div style="padding:4px 0 16px;border-bottom:1px solid var(--border);'
        'margin-bottom:20px;display:flex;align-items:baseline;gap:12px">'
        '<span style="font-family:var(--mono);font-size:1rem;font-weight:600">'
        'Regime Outlook</span>'
        '<span style="font-size:.75rem;color:var(--muted)">'
        'Transition probability and forward positioning</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    left, right = st.columns(2)

    with left:
        _render_transition(tp)

    with right:
        _render_indicators(macro)


# ── Transition probability panel ───────────────────────────────────────────────

def _render_transition(tp: dict):
    prob  = tp["prob"]
    color = tp["color"]
    label = tp["label"]
    stay  = tp["stay"]
    top   = tp["top"]

    st.markdown(
        f'<div style="background:var(--bg1);border:1px solid var(--border);'
        f'border-radius:var(--radius);padding:20px;margin-bottom:14px" '
        f'role="region" aria-label="Regime transition probability: {prob} percent">'

        f'<div style="font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;'
        f'text-transform:uppercase;color:var(--muted);margin-bottom:10px">'
        f'Transition Probability</div>'

        f'<div style="display:flex;align-items:baseline;gap:12px;margin-bottom:8px">'
        f'<span style="font-family:var(--mono);font-size:2.4rem;font-weight:600;'
        f'color:{color}">{prob}%</span>'
        f'<span style="font-family:var(--mono);font-size:.75rem;color:{color}">'
        f'{label}</span>'
        f'</div>'

        f'<div class="tp-track" role="meter" aria-valuenow="{prob}" '
        f'aria-valuemin="0" aria-valuemax="100">'
        f'<div style="height:100%;width:{prob}%;background:{color};border-radius:5px">'
        f'</div></div>'

        f'<div style="font-size:.72rem;color:var(--muted);margin-top:8px">'
        f'Stay probability: <b style="color:var(--text)">{stay}%</b>'
        f'&nbsp;·&nbsp;'
        f'Most likely next: <b style="color:{color}">{top}</b>'
        f'</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Signal breakdown (collapsed)
    with st.expander("Transition signal detail", expanded=False):
        for sig_name, sig_val, sig_detail in tp.get("signals", []):
            s_col = (
                "#f85149" if sig_val >= 60 else
                "#d29922" if sig_val >= 35 else
                "#3fb950"
            )
            st.markdown(
                f'<div style="padding:5px 0;border-bottom:1px solid var(--border)" '
                f'role="meter" aria-valuenow="{sig_val}" '
                f'aria-valuemin="0" aria-valuemax="100" '
                f'aria-label="{sig_name}: {sig_val} out of 100">'
                f'<div style="display:flex;justify-content:space-between;'
                f'font-family:var(--mono);font-size:.65rem;margin-bottom:3px">'
                f'<span style="color:var(--muted)">{sig_name}</span>'
                f'<span style="color:{s_col}">{sig_val}</span>'
                f'</div>'
                f'<div style="height:3px;background:var(--bg3);border-radius:2px">'
                f'<div style="height:100%;width:{sig_val}%;background:{s_col};'
                f'border-radius:2px"></div></div>'
                f'<div style="font-size:.6rem;color:var(--dim);margin-top:2px">'
                f'{sig_detail}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Destination distribution
    st.markdown(
        '<div style="font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;'
        'text-transform:uppercase;color:var(--muted);margin:14px 0 8px">'
        'If Transition Occurs</div>',
        unsafe_allow_html=True,
    )
    for dest, prob_d in sorted(tp["target"].items(), key=lambda x: -x[1]):
        is_top = dest == top
        dc = color if is_top else "#3d4f63"
        tc = "var(--text)" if is_top else "var(--muted)"
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:10px;padding:5px 0" '
            f'aria-label="{dest}: {prob_d}%{"  — most likely" if is_top else ""}">'
            f'<div style="font-family:var(--mono);font-size:.72rem;'
            f'color:{tc};width:120px">{dest}</div>'
            f'<div style="flex:1;height:5px;background:var(--bg3);border-radius:3px">'
            f'<div style="height:100%;width:{prob_d}%;background:{dc};'
            f'border-radius:3px"></div></div>'
            f'<div style="font-family:var(--mono);font-size:.7rem;'
            f'color:{dc};width:32px;text-align:right">{prob_d}%</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Position implications
    new_tilts  = tp.get("new_tilts",  [])
    exit_tilts = tp.get("exit_tilts", [])

    if new_tilts or exit_tilts:
        parts = [
            '<div style="margin-top:14px;padding:10px 12px;'
            'background:rgba(210,153,34,.08);border:1px solid rgba(210,153,34,.2);'
            'border-radius:var(--radius);font-size:.74rem;color:var(--muted);line-height:1.7">'
        ]
        if exit_tilts:
            parts.append(
                f'<div><b style="color:#d29922">Watch to exit:</b> '
                f'{", ".join(exit_tilts)} — not in next regime</div>'
            )
        if new_tilts:
            parts.append(
                f'<div><b style="color:#3fb950">Watch to enter:</b> '
                f'{", ".join(new_tilts)} — preferred in {top}</div>'
            )
        parts.append('</div>')
        st.markdown("".join(parts), unsafe_allow_html=True)


# ── Leading indicators panel ───────────────────────────────────────────────────

def _render_indicators(macro: dict):
    st.markdown(
        '<div style="font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;'
        'text-transform:uppercase;color:var(--muted);margin-bottom:12px">'
        'Leading Indicator Evidence</div>',
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
        "#3fb950" if macro["claims_signal"] == "improving"     else
        "#f85149" if macro["claims_signal"] == "deteriorating" else
        "#d29922"
    )

    yc_val  = f'{macro["yc_current"]:+.2f}%' if macro["yc_current"] is not None else "—"
    pmi_val = f'{macro["pmi_mom"]:+.2f}%'
    cl_val  = f'{macro["claims_current"]}K'   if macro["claims_current"] else "—"

    indicators = [
        (
            "10Y–2Y Yield Curve",
            yc_val,
            macro["yc_signal"],
            yc_col,
            {
                "inverted":   "Historically precedes recession by 12–18 months. "
                              "Strongest single leading indicator.",
                "flat":       "Transition zone — yield curve near zero. "
                              "Watch for direction.",
                "steepening": "Growth-positive. Expansion conditions supported.",
                "normal":     "Healthy yield curve. Low near-term transition risk.",
                "unknown":    "Data unavailable.",
            }.get(macro["yc_signal"], ""),
        ),
        (
            "Industrial Production",
            pmi_val,
            macro["pmi_signal"],
            pmi_col,
            {
                "expanding":   "Manufacturing accelerating. "
                               "Supports current growth regime.",
                "contracting": "Production falling. "
                               "Headwind for growth assets — watch for rotation.",
                "stalling":    "Flat production. No clear directional signal yet.",
            }.get(macro["pmi_signal"], "Data unavailable."),
        ),
        (
            "Initial Claims (4wk avg)",
            cl_val,
            macro["claims_signal"],
            cl_col,
            {
                "improving":    "Labor market strengthening. "
                                "Supports consumer spending and growth.",
                "deteriorating":"Claims rising. Growth headwind developing "
                                "— historically leads GDP by 1–2 quarters.",
                "stable":       "Labor market stable. Neutral signal.",
            }.get(macro["claims_signal"], "Data unavailable."),
        ),
    ]

    for name, val, sig, col, desc in indicators:
        st.markdown(
            f'<div class="ind-card" style="border-top:3px solid {col}" '
            f'role="article" aria-label="{name}: {sig}">'
            f'<div style="display:flex;justify-content:space-between;align-items:baseline">'
            f'<div class="ind-label">{name}</div>'
            f'<div class="ind-value" style="color:{col}">{val}</div>'
            f'</div>'
            f'<div class="ind-signal" style="color:{col}">{sig.upper()}</div>'
            f'<div class="ind-desc">{desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Composite summary
    ls     = macro["leading_scores"]
    n_bull = sum(1 for s in ls if s > 0)
    n_bear = sum(1 for s in ls if s < 0)
    bias   = macro["leading_bias"]
    bc     = (
        "#3fb950" if bias == "growth_positive" else
        "#f85149" if bias == "growth_negative" else
        "#d29922"
    )
    bias_label = bias.replace("_", " ").title()

    tail_note = (
        "Macro thesis supported by forward-looking data."
        if bias == "growth_positive" else
        "Forward data warns of slowdown — monitor leading indicators closely."
        if bias == "growth_negative" else
        "Signals mixed — no clear regime shift imminent. Monitor for confirmation."
    )

    st.markdown(
        f'<div style="padding:10px 12px;background:rgba(255,255,255,.03);'
        f'border:1px solid var(--border);border-radius:var(--radius);'
        f'font-size:.74rem;color:var(--muted);line-height:1.6;margin-top:4px">'
        f'<b style="color:{bc};font-family:var(--mono)">{bias_label}</b>'
        f' — {n_bull}/3 signals bullish, {n_bear}/3 bearish. '
        f'Leads GDP by ~2–3 quarters. {tail_note}'
        f'</div>',
        unsafe_allow_html=True,
    )

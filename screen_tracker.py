"""
screens/screen_tracker.py
Tab 3 — Position Tracker

Renders:
  - Editable position table (current %, cost basis)
  - Stop-loss triggered alerts (auto-detected)
  - Rebalancing orders (priority: stop → threshold → scheduled)
  - Rebalance cadence status
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from config import ETF_DATA


def render(
    target_map:   dict,
    prices,
    highs,
    lows,
    rebal_freq:   str,
    compute_orders_fn,   # callable from engine.py
    get_stop_fn,         # callable(ticker) → (stop_px, atr_val)
):
    st.markdown(
        '<div style="padding:4px 0 16px;border-bottom:1px solid var(--border);'
        'margin-bottom:20px;display:flex;align-items:baseline;gap:12px">'
        '<span style="font-family:var(--mono);font-size:1rem;font-weight:600">'
        'Position Tracker</span>'
        '<span style="font-size:.75rem;color:var(--muted)">'
        'Cost basis · stop-losses · rebalancing orders</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Rebalance cadence status ───────────────────────────────────────────────
    freq_days = {"Quarterly": 90, "Semi-annual": 182, "Annual": 365}[rebal_freq]

    last_rebal_str = st.query_params.get("last_rebal", "")
    try:
        last_rebal = datetime.strptime(last_rebal_str, "%Y-%m-%d").date()
    except Exception:
        last_rebal = None

    days_since = (datetime.today().date() - last_rebal).days if last_rebal else 9999
    sched_due  = days_since >= freq_days
    next_date  = (last_rebal + timedelta(days=freq_days)) if last_rebal else None

    cs1, cs2, cs3 = st.columns([2, 2, 1])
    with cs1:
        tol_band = st.slider(
            "Tolerance band %", 1, 15,
            int(st.query_params.get("tol_band", "5")),
            1, key="tol_sl",
        )
    with cs2:
        if last_rebal:
            dr_col = (
                "#3fb950" if days_since < 90  else
                "#d29922" if days_since < 180 else
                "#f85149"
            )
            sched_str = (
                '  ·  <b style="color:#f85149">REBALANCE DUE</b>'
                if sched_due else
                f'  ·  Next: {next_date}'
            )
            st.markdown(
                f'<div style="font-family:var(--mono);font-size:.7rem;'
                f'color:var(--muted);padding-top:28px">'
                f'Last rebalanced: <b style="color:{dr_col}">{last_rebal}</b>'
                f' ({days_since}d ago){sched_str}</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                '<div style="font-family:var(--mono);font-size:.7rem;'
                'color:var(--dim);padding-top:28px">'
                'No rebalance recorded yet</div>',
                unsafe_allow_html=True,
            )
    with cs3:
        if st.button("✓ Mark rebalanced today", use_container_width=True):
            today_str = datetime.today().strftime("%Y-%m-%d")
            st.query_params["last_rebal"] = today_str
            st.query_params["tol_band"]   = str(tol_band)
            st.success(f"Recorded {today_str}")
            last_rebal = datetime.today().date()
            days_since = 0
            sched_due  = False

    st.markdown("---")

    # ── Build position editor DataFrame ───────────────────────────────────────
    rows = []
    for ticker, tm in target_map.items():
        cb_str  = st.query_params.get(f"cb_{ticker}",  "0")
        cur_str = st.query_params.get(f"cur_{ticker}", "0")
        try:    cb  = float(cb_str)
        except: cb  = 0.0
        try:    cur = float(cur_str)
        except: cur = 0.0
        rows.append({
            "Ticker":       ticker,
            "Bucket":       tm["bucket"],
            "Target %":     tm["target_pct"],
            "Current %":    cur,
            "Cost Basis $": cb,
        })

    df_edit = st.data_editor(
        pd.DataFrame(rows),
        column_config={
            "Ticker":       st.column_config.TextColumn("Ticker",     disabled=True),
            "Bucket":       st.column_config.TextColumn("Bucket",     disabled=True),
            "Target %":     st.column_config.NumberColumn("Target %", disabled=True, format="%.1f"),
            "Current %":    st.column_config.NumberColumn(
                "Current % ✏️",
                min_value=0.0, max_value=100.0, step=0.1, format="%.1f",
            ),
            "Cost Basis $": st.column_config.NumberColumn(
                "Cost Basis ✏️",
                min_value=0.0, step=0.01, format="$%.2f",
            ),
        },
        use_container_width=True,
        hide_index=True,
        key="tracker_editor",
    )

    sc1, sc2 = st.columns(2)
    with sc1:
        if st.button("💾 Save positions", use_container_width=True, key="save_pos"):
            for _, row in df_edit.iterrows():
                st.query_params[f"cb_{row['Ticker']}"]  = str(row["Cost Basis $"])
                st.query_params[f"cur_{row['Ticker']}"] = str(row["Current %"])
            st.query_params["tol_band"] = str(tol_band)
            st.success("Positions saved.")

    with sc2:
        # Stopped tickers management
        stopped_raw = st.query_params.get("stopped", "")
        stop_input  = st.text_input(
            "Stopped tickers (comma-separated)",
            value=stopped_raw,
            key="stop_input",
            help="Tickers stopped out — excluded from recommendations until cleared.",
        )
        if st.button("Update stops", key="upd_stops"):
            cleaned = ",".join(
                t.strip().upper() for t in stop_input.split(",") if t.strip()
            )
            st.query_params["stopped"] = cleaned
            st.success(f"Stops updated: {cleaned or 'none'}")

    st.markdown("---")

    # ── Build current / target / cost_basis maps from edited df ───────────────
    current_map = {
        row["Ticker"]: float(row["Current %"])
        for _, row in df_edit.iterrows()
    }
    cost_bases = {
        row["Ticker"]: float(row["Cost Basis $"])
        for _, row in df_edit.iterrows()
    }
    stopped = [
        t.strip().upper()
        for t in st.query_params.get("stopped", "").split(",")
        if t.strip()
    ]

    # ── Stop-loss alerts ───────────────────────────────────────────────────────
    for _, row in df_edit.iterrows():
        ticker = row["Ticker"]
        cb     = float(row["Cost Basis $"])
        if cb <= 0:
            continue
        if ticker not in prices.columns:
            continue
        px              = float(prices[ticker].iloc[-1])
        stop_px, atr_v  = get_stop_fn(ticker)
        if stop_px > 0 and px <= stop_px:
            tlh      = ETF_DATA.get(ticker, {}).get("tlh") or "—"
            pnl      = round((px - cb), 2)
            pnl_pct  = round((px - cb) / cb * 100, 1) if cb else 0
            st.markdown(
                f'<div class="aw-alert aw-alert-crit" role="alert" aria-live="assertive">'
                f'<span aria-hidden="true">🚨</span>'
                f'<div><b>STOP-LOSS TRIGGERED — {ticker}</b><br>'
                f'Price ${px:.2f} ≤ stop ${stop_px:.2f} &nbsp;·&nbsp; '
                f'ATR ${atr_v:.2f} &nbsp;·&nbsp; '
                f'Cost basis ${cb:.2f} &nbsp;·&nbsp; '
                f'P/L ${pnl:+.2f}/share ({pnl_pct:+.1f}%)<br>'
                f'TLH alternative: <b>{tlh}</b> &nbsp;·&nbsp; '
                f'Mark as stopped above to update recommendations.</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # ── Compute orders ─────────────────────────────────────────────────────────
    df_edit["Drift %"] = (df_edit["Current %"] - df_edit["Target %"]).round(2)
    orders = compute_orders_fn(
        target_map    = target_map,
        current_map   = current_map,
        prices        = prices,
        highs         = highs,
        lows          = lows,
        cost_bases    = cost_bases,
        tolerance_pct = tol_band,
        sched_due     = sched_due,
        stopped       = stopped,
    )

    if orders:
        st.markdown(
            '<div style="font-family:var(--mono);font-size:.62rem;letter-spacing:.1em;'
            'text-transform:uppercase;color:var(--muted);margin-bottom:8px">'
            'Rebalancing Orders</div>',
            unsafe_allow_html=True,
        )

        # Column header
        st.markdown(
            '<div style="display:grid;'
            'grid-template-columns:52px 72px 90px 68px 68px 1fr;'
            'gap:8px;padding:6px 0 8px;border-bottom:1px solid var(--border);'
            'font-family:var(--mono);font-size:.58rem;color:var(--muted);'
            'letter-spacing:.08em;text-transform:uppercase">'
            '<div>Ticker</div><div>Action</div><div>Trigger</div>'
            '<div style="text-align:right">Drift</div>'
            '<div style="text-align:right">Price</div>'
            '<div>Tax Note</div></div>',
            unsafe_allow_html=True,
        )

        for o in orders:
            ac     = o["direction"]
            ac_col = "#3fb950" if "BUY" in ac else "#f85149"
            st.markdown(
                f'<div style="display:grid;'
                f'grid-template-columns:52px 72px 90px 68px 68px 1fr;'
                f'gap:8px;padding:9px 0;border-bottom:1px solid var(--border);'
                f'font-size:.72rem;align-items:center">'
                f'<div style="font-family:var(--mono);font-weight:600">{o["ticker"]}</div>'
                f'<div style="font-family:var(--mono);font-size:.7rem;color:{ac_col}">{ac}</div>'
                f'<div style="font-family:var(--mono);font-size:.65rem;color:var(--muted)">'
                f'{o["trigger"]}</div>'
                f'<div style="font-family:var(--mono);text-align:right;color:{ac_col}">'
                f'{o["drift"]:+.1f}%</div>'
                f'<div style="font-family:var(--mono);text-align:right;color:var(--muted)">'
                f'${o["price"]:.2f}</div>'
                f'<div style="font-size:.68rem;color:var(--dim)">{o["tax"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # Summary totals
        n_buys  = sum(1 for o in orders if "BUY"  in o["direction"])
        n_sells = sum(1 for o in orders if "SELL" in o["direction"])
        st.markdown(
            f'<div style="font-family:var(--mono);font-size:.68rem;'
            f'color:var(--muted);padding:8px 0;'
            f'border-top:1px solid var(--border);margin-top:4px">'
            f'{len(orders)} orders &nbsp;·&nbsp; '
            f'<span style="color:#3fb950">{n_buys} buys</span>'
            f' &nbsp;·&nbsp; '
            f'<span style="color:#f85149">{n_sells} sells</span>'
            f' &nbsp;·&nbsp; '
            f'Tolerance ±{tol_band}% &nbsp;·&nbsp; {rebal_freq}'
            f'</div>',
            unsafe_allow_html=True,
        )

    else:
        st.markdown(
            f'<div class="aw-alert aw-alert-good">'
            f'<span aria-hidden="true">✓</span>'
            f'<span>All positions within ±{tol_band}% tolerance band. '
            f'{"Scheduled rebalance due but no material drift detected." if sched_due else "No action required."}'
            f'</span></div>',
            unsafe_allow_html=True,
        )

    # ── Total drift summary ────────────────────────────────────────────────────
    total_d = df_edit["Drift %"].abs().sum()
    d_col   = "#3fb950" if total_d < 5 else "#d29922" if total_d < 15 else "#f85149"
    st.markdown(
        f'<div style="font-family:var(--mono);font-size:.7rem;color:var(--muted);'
        f'padding:8px 0;border-top:1px solid var(--border);margin-top:8px">'
        f'Total drift: <b style="color:{d_col}">{total_d:.1f}%</b>'
        f'</div>',
        unsafe_allow_html=True,
    )

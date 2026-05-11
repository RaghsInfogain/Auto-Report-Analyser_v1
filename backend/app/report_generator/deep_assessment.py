"""
Deep System Health Assessment payload for JMeter HTML reports.
Derives load bands, health cards, error views, and RCA-style hypotheses from summarized metrics only.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _pct(a: float, b: float) -> float:
    return (100.0 * a / b) if b else 0.0


def _safe_mean(vals: List[float]) -> float:
    return float(np.mean(vals)) if vals else 0.0


def _corr(a: List[float], b: List[float]) -> float:
    if len(a) < 3 or len(a) != len(b):
        return 0.0
    xa, xb = np.array(a, dtype=float), np.array(b, dtype=float)
    if np.std(xa) == 0 or np.std(xb) == 0:
        return 0.0
    try:
        return float(np.corrcoef(xa, xb)[0, 1])
    except Exception:
        return 0.0


def _load_bands_from_series(
    time_series: List[Dict[str, Any]], max_vu: int
) -> List[Tuple[str, float, float]]:
    """Return (label, vu_lo, vu_hi) bands; default 6 bands scaled to max_vu."""
    if max_vu <= 0:
        mx = max((float(d.get("vusers") or 0) for d in time_series), default=0)
        max_vu = int(mx) if mx else 1
    step = max(1, max_vu // 6)
    edges = [0]
    while edges[-1] < max_vu:
        edges.append(min(max_vu, edges[-1] + step))
    bands: List[Tuple[str, float, float]] = []
    for i in range(len(edges) - 1):
        lo, hi = edges[i] + (1 if i == 0 else 0), edges[i + 1]
        if i == 0:
            lo = 1
        bands.append((f"{int(lo)}–{int(hi)} VU", float(lo), float(hi)))
    return bands


def _aggregate_band(
    time_series: List[Dict[str, Any]], vu_lo: float, vu_hi: float
) -> Dict[str, float]:
    rows = [
        d
        for d in time_series
        if vu_lo <= float(d.get("vusers") or 0) <= vu_hi
    ]
    if not rows:
        return {"mean_rt": 0.0, "p90_rt": 0.0, "tps": 0.0, "err_pct": 0.0, "n": 0}
    rts = [float(d.get("avg_response_time") or 0) for d in rows]
    errs = [float(d.get("error_rate_pct") or 0) for d in rows]
    tps = [float(d.get("throughput_pass") or d.get("throughput") or 0) for d in rows]
    return {
        "mean_rt": _safe_mean(rts),
        "p90_rt": float(np.percentile(rts, 90)) if rts else 0.0,
        "tps": _safe_mean(tps),
        "err_pct": _safe_mean(errs),
        "n": len(rows),
    }


def build_deep_assessment(metrics: Dict[str, Any]) -> Dict[str, Any]:
    summary = metrics.get("summary") or {}
    ts = summary.get("time_series_data") or []
    tx = summary.get("transaction_stats") or {}
    req = summary.get("request_stats") or {}
    rc = metrics.get("response_codes") or {}
    hdr = summary.get("report_header") or {}
    tx_sla = summary.get("transaction_sla_p90_peak") or {}
    max_vu = int(summary.get("max_concurrent_users") or 0)
    total_samples = int(metrics.get("total_samples") or 0)
    err_rate_pct = float(metrics.get("error_rate") or 0) * 100.0
    throughput = float(metrics.get("throughput") or 0)

    st = metrics.get("sample_time") or {}
    mean_ms = st.get("mean")
    p99_ms = st.get("p99")
    mean_sec = float(mean_ms) / 1000.0 if isinstance(mean_ms, (int, float)) else None
    p99_sec = float(p99_ms) / 1000.0 if isinstance(p99_ms, (int, float)) else None

    vu_series = [float(d.get("vusers") or 0) for d in ts]
    rt_series = [float(d.get("avg_response_time") or 0) for d in ts]
    err_ser = [float(d.get("error_rate_pct") or 0) for d in ts]
    tput_ser = [float(d.get("throughput_pass") or d.get("throughput") or 0) for d in ts]

    degrad_vu = None
    if len(vu_series) >= 4 and mean_sec:
        baseline_idx = [i for i, v in enumerate(vu_series) if v <= max(1, max_vu * 0.25)]
        if baseline_idx:
            base_rt = _safe_mean([rt_series[i] for i in baseline_idx])
            for i, v in enumerate(vu_series):
                if v > max_vu * 0.35 and rt_series[i] > base_rt * 1.4:
                    degrad_vu = int(v)
                    break

    n404 = sum(int(rc.get(k, 0) or 0) for k in rc if str(k).startswith("404"))
    n4xx = sum(
        int(rc.get(k, 0) or 0)
        for k in rc
        if str(k).startswith("4") and str(k) != "429"
    )
    n5xx = sum(int(rc.get(k, 0) or 0) for k in rc if str(k).startswith("5"))
    n_tot_rc = sum(int(v or 0) for v in rc.values()) or 1
    n_err_samples = int(metrics.get("total_errors") or int(total_samples * err_rate_pct / 100.0))

    client_share = _pct(n4xx, n_err_samples) if n_err_samples else 0.0
    server_share = _pct(n5xx, n_err_samples) if n_err_samples else 0.0

    # --- Executive KPI cards ---
    tx_pass = int(tx_sla.get("transactions_pass") or 0)
    tx_tot = int(tx_sla.get("transactions_tested") or len(tx) or 0)
    sla_pass_pct = float(tx_sla.get("pass_rate_pct") or 0)
    failed_req = n_err_samples

    kpi_cards = [
        {
            "label": "Overall error rate",
            "value": f"{err_rate_pct:.2f}%",
            "sub": f"{failed_req:,} failed requests",
            "tone": "bad" if err_rate_pct >= 1 else "warn" if err_rate_pct >= 0.5 else "ok",
        },
        {
            "label": "Avg throughput",
            "value": f"{throughput:.1f} TPS",
            "sub": f"Peak ~{max(tput_ser):.1f} TPS" if tput_ser else "TPS from passed samples",
            "tone": "neutral",
        },
        {
            "label": "Mean response time",
            "value": f"{mean_sec * 1000:,.0f} ms" if mean_sec is not None else "N/A",
            "sub": f"P99 = {p99_sec:.1f}s" if p99_sec is not None else "",
            "tone": (
                "bad"
                if mean_sec is not None and mean_sec > 3
                else "warn"
                if mean_sec is not None and mean_sec > 1.5
                else "ok"
            ),
        },
        {
            "label": "SLA P90 pass rate",
            "value": f"{sla_pass_pct:.0f}%",
            "sub": f"{tx_pass}/{tx_tot} transactions (<{int(tx_sla.get('sla_p90_ms') or 3000)} ms P90 at peak load)",
            "tone": "bad" if sla_pass_pct < 80 else "warn" if sla_pass_pct < 95 else "ok",
        },
    ]

    # --- Key findings paragraphs ---
    worst_tx = sorted(
        tx.items(),
        key=lambda kv: (kv[1].get("error_rate") or 0, -(kv[1].get("count") or 0)),
        reverse=True,
    )[:5]
    worst_names = [n for n, _ in worst_tx if (_.get("error_rate") or 0) > 5]
    worst_clause = (
        f"Critical transactions ({', '.join(worst_names[:4])}{'…' if len(worst_names) > 4 else ''}) exhibit elevated failures under load."
        if worst_names
        else "Several transactions show elevated latency or failures under load."
    )

    p1 = (
        "The system demonstrates severe performance degradation above ~120 concurrent users."
        if max_vu >= 120 and degrad_vu
        else "Performance materially changes as concurrent users increase; review load-shaped metrics and error onset."
    )
    p4 = (
        "The application requires significant architectural remediation before any production rollout."
        if err_rate_pct > 1 or sla_pass_pct < 70
        else "Continue monitoring and address regressions before broad production rollout."
    )
    t1 = "bad" if (max_vu >= 120 and degrad_vu) else "warn"
    t2 = "bad" if err_rate_pct >= 1 else "warn" if err_rate_pct >= 0.5 else "ok"
    t3 = "bad" if sla_pass_pct < 80 else "warn" if sla_pass_pct < 95 else "ok"
    t4 = "bad" if (err_rate_pct > 1 or sla_pass_pct < 70) else "ok"

    key_paragraphs = [
        p1,
        f"{worst_clause} "
        f"Overall error rate is {err_rate_pct:.2f}%.",
        f"Only {tx_pass} of {tx_tot} tested transactions ({sla_pass_pct:.0f}%) pass the P90 <{int(tx_sla.get('sla_p90_ms') or 3000) / 1000:.0f}s SLA at peak concurrency.",
        p4,
    ]
    key_findings_items = [
        {"text": key_paragraphs[0], "tone": t1},
        {"text": key_paragraphs[1], "tone": t2},
        {"text": key_paragraphs[2], "tone": t3},
        {"text": key_paragraphs[3], "tone": t4},
    ]

    # --- Overall system health (4 cards) ---
    def _hcard(
        title: str,
        badge: str,
        main: str,
        foot: str,
        fill: float,
        tone: str,
    ) -> Dict[str, Any]:
        return {
            "title": title,
            "badge": badge,
            "main": main,
            "footer": foot,
            "fill_pct": max(5, min(100, fill)),
            "tone": tone,
        }

    err_target = 1.0
    st_bad = err_rate_pct > err_target
    st_warn = err_rate_pct > 0.5 and not st_bad
    health_cards = [
        _hcard(
            "Stability (error rate)",
            "FAIL" if st_bad else "WARN" if st_warn else "PASS",
            f"{err_rate_pct:.2f}% — {'Critical' if st_bad else 'Elevated' if st_warn else 'Within target'}",
            f"Target: <{err_target:.0f}% | {failed_req:,} errors recorded",
            min(100, max(0, 100 - err_rate_pct * 20)),
            "red" if st_bad else "orange" if st_warn else "green",
        ),
        _hcard(
            "Response time (P90 SLA)",
            "FAIL" if sla_pass_pct < 80 else "WARN" if sla_pass_pct < 95 else "PASS",
            f"{sla_pass_pct:.0f}% pass — {'Critical' if sla_pass_pct < 80 else 'Below target' if sla_pass_pct < 95 else 'Healthy'}",
            f"Target: >95% | {tx_pass} of {tx_tot} pass",
            sla_pass_pct,
            "red" if sla_pass_pct < 80 else "orange" if sla_pass_pct < 95 else "green",
        ),
    ]

    tps_hi = [tput_ser[i] for i, v in enumerate(vu_series) if v >= max_vu * 0.5] if max_vu else tput_ser
    tps_lo = [tput_ser[i] for i, v in enumerate(vu_series) if v <= max_vu * 0.35] if max_vu else tput_ser
    tps_drop = (_safe_mean(tps_lo) - _safe_mean(tps_hi)) if tps_lo and tps_hi else 0.0
    tp_warn = tps_drop > 5 or (_safe_mean(tps_hi) > 0 and _safe_mean(tps_lo) > 1.3 * _safe_mean(tps_hi))
    health_cards.append(
        _hcard(
            "Throughput stability",
            "WARN" if tp_warn else "PASS",
            "Moderate — degrades" if tp_warn else "Stable",
            "TPS may stall or oscillate at higher concurrency — review saturation knee",
            55 if tp_warn else 88,
            "orange" if tp_warn else "green",
        )
    )

    auth_label = None
    for name in tx:
        up = (name or "").upper()
        if "LOGIN" in up or "T002" in up or "AUTH" in up:
            auth_label = name
            break
    if auth_label and auth_label in tx:
        te = tx[auth_label].get("error_rate") or 0
        p90 = tx[auth_label].get("p90")
        p90s = float(p90) / 1000.0 if isinstance(p90, (int, float)) else None
        health_cards.append(
            _hcard(
                f"Login / Auth ({auth_label[:24]})",
                "PASS" if te < 1 else "WARN",
                f"P90 {p90s:.2f}s — {'Healthy' if p90s and p90s < 3 else 'Slow'}" if p90s else "See transaction table",
                f"{te:.1f}% error across {int(tx[auth_label].get('count') or 0):,} samples",
                90 if te < 1 else 55,
                "green" if te < 1 else "orange",
            )
        )
    else:
        health_cards.append(
            _hcard(
                "Key user journey",
                "—",
                "Review transaction table",
                "No clear Login/Auth transaction label detected for auto-summary",
                50,
                "neutral",
            )
        )

    # --- Response-time behaviour cards ---
    base_rt = None
    if ts:
        low_vu_rows = [d for d in ts if float(d.get("vusers") or 0) <= max(1, max_vu * 0.22)]
        if low_vu_rows:
            base_rt = _safe_mean(
                [float(d.get("avg_response_time") or 0) for d in low_vu_rows]
            )
    onset_rt = (
        _safe_mean([rt_series[i] for i, v in enumerate(vu_series) if degrad_vu and abs(v - degrad_vu) < 15])
        if degrad_vu
        else None
    )
    hi_v_rt = (
        _safe_mean([rt_series[i] for i, v in enumerate(vu_series) if v >= max_vu * 0.88])
        if max_vu
        else None
    )

    rt_behave_cards = [
        {
            "label": "Baseline RT (low load)",
            "value": f"{base_rt * 1000:,.0f} ms" if base_rt else "—",
            "sub": "Mean in lowest VU band",
            "tone": "ok",
        },
        {
            "label": "Degradation onset",
            "value": f"{degrad_vu} VU" if degrad_vu else "—",
            "sub": (
                f"+{((onset_rt / base_rt - 1) * 100):.0f}% vs baseline"
                if base_rt and onset_rt
                else "From time-series inflection"
            ),
            "tone": "warn",
        },
        {
            "label": "RT at peak VU (avg interval)",
            "value": f"{hi_v_rt * 1000:,.0f} ms" if hi_v_rt else "—",
            "sub": "Bucketed mean RT under high concurrency",
            "tone": "bad" if hi_v_rt and hi_v_rt > 3 else "warn",
        },
        {
            "label": "Max response time",
            "value": f"{p99_sec:.1f}s" if p99_sec else "—",
            "sub": "P99 (passed-sample aggregate)",
            "tone": "bad",
        },
        {
            "label": "Median / Mean gap",
            "value": (
                f"{(float(st.get('max') or 0) / float(st.get('mean') or 1)):.1f}x"
                if st.get("mean")
                else "—"
            ),
            "sub": "Tail vs typical (global aggregate)",
            "tone": "bad",
        },
    ]

    # Load bands table (percentiles approximated from transaction rollup — global per band from time series)
    bands = _load_bands_from_series(ts, max_vu)
    band_rows = []
    for lab, lo, hi in bands:
        agg = _aggregate_band(ts, lo, hi)
        band_rows.append(
            {
                "band": lab,
                "users": lab,
                "median": round(agg["mean_rt"] * 1000, 0),
                "p90": round(agg["p90_rt"] * 1000, 0),
                "err": round(agg["err_pct"], 2),
                "sla": "PASS" if agg["p90_rt"] < 3 else "FAIL",
            }
        )

    # Throughput by band (from aggregated mean TPS)
    tps_by_band = []
    for lab, lo, hi in bands:
        agg = _aggregate_band(ts, lo, hi)
        tps_by_band.append({"band": lab, "tps": round(agg["tps"], 1), "n": agg["n"]})

    r_corr = _corr(err_ser, rt_series)

    # Error table by transaction
    err_rows = []
    for name, s in sorted(tx.items(), key=lambda kv: -(kv[1].get("errors") or 0))[:40]:
        ec = int(s.get("errors") or 0)
        if ec == 0 and (s.get("error_rate") or 0) < 0.01:
            continue
        err_rows.append(
            {
                "transaction": name,
                "total_err": ec,
                "err_rate": round(s.get("error_rate") or 0, 2),
            }
        )

    # Structured SEV issues
    structured_issues = []
    for name, s in tx.items():
        er = float(s.get("error_rate") or 0)
        p95 = s.get("p95")
        p95s = float(p95) / 1000.0 if isinstance(p95, (int, float)) else None
        if er >= 25:
            structured_issues.append(
                {
                    "severity": "SEV-1",
                    "title": f"{name} — {er:.1f}% errors",
                    "body": f"{int(s.get('count') or 0):,} samples; investigate 4xx/5xx and timeouts on this transaction.",
                }
            )
        elif er >= 10:
            structured_issues.append(
                {
                    "severity": "SEV-2",
                    "title": f"{name} — {er:.1f}% errors",
                    "body": "Material failure rate; prioritize before production.",
                }
            )
        elif p95s and p95s > 30 and er < 1:
            structured_issues.append(
                {
                    "severity": "SEV-2",
                    "title": f"{name} — very slow (P95 ~{p95s:.0f}s), low errors",
                    "body": "Serialized or DB-bound path; SLA risk even without hard failures.",
                }
            )
    structured_issues = structured_issues[:8]

    if max_vu >= 120 and (mean_sec or 0) > 2:
        structured_issues.append(
            {
                "severity": "SEV-2",
                "title": "Progressive degradation above mid-load",
                "body": "Response time and/or errors worsen as VUsers approach peak — review backpressure and pool sizing.",
            }
        )

    # Root cause hypotheses (template + data hooks)
    hypos: List[Dict[str, Any]] = []
    if n404 > 100 and err_rate_pct > 0.5:
        hypos.append(
            {
                "id": "RCA-01",
                "title": "Client / routing defects under concurrency (HTTP 404 cluster)",
                "confidence": min(95, 70 + min(25, n404 // 500)),
                "text": (
                    "404 volume grows with load in many runs when URLs or session-scoped identifiers are not thread-safe. "
                    "Validate route tables, tenant context, and per-user URLs."
                ),
                "evidence": f"{n404:,} responses with HTTP 404 (~{_pct(n404, total_samples):.2f}% of samples).",
            }
        )
    if n5xx > 50:
        hypos.append(
            {
                "id": f"RCA-{len(hypos) + 1:02d}",
                "title": "Gateway / upstream saturation (HTTP 5xx & timeouts)",
                "confidence": min(95, 75 + min(20, n5xx // 100)),
                "text": (
                    "5xx and timeout walls often indicate thread pool exhaustion, reverse-proxy limits, or slow backends shared across requests."
                ),
                "evidence": f"{n5xx:,} HTTP 5xx responses; error–latency correlation ≈ {r_corr:.2f}.",
            }
        )
    if tps_drop > 3:
        hypos.append(
            {
                "id": f"RCA-{len(hypos) + 1:02d}",
                "title": "Capacity knee — throughput stops scaling before peak users",
                "confidence": 82,
                "text": (
                    "When added users no longer increase TPS, queues build in the app tier (USL-style saturation) rather than the network edge."
                ),
                "evidence": f"Mean TPS differed ~{tps_drop:.1f} req/s between mid and high load buckets.",
            }
        )
    if float(st.get("skewness") or 0) > 1.0:
        hypos.append(
            {
                "id": f"RCA-{len(hypos) + 1:02d}",
                "title": "Heavy-tail latency — contention or blocking workflows",
                "confidence": 78,
                "text": (
                    "Right-skewed elapsed times usually mix fast cache hits with rare slow paths (locks, DB, remote calls)."
                ),
                "evidence": f"Skewness {float(st.get('skewness') or 0):.2f}; P99 {'%.1fs' % p99_sec if p99_sec else 'elevated'}.",
            }
        )
    while len(hypos) < 3:
        hypos.append(
            {
                "id": f"RCA-{len(hypos) + 1:02d}",
                "title": "Validate with APM and infra metrics",
                "confidence": 55,
                "text": "Capture thread/DB pool utilisation, GC, and dependency latency for windows matching this test.",
                "evidence": "Hypothesis padded when specific patterns were not decisive.",
            }
        )

    optimization_plan = [
        {
            "phase": "Phase 1",
            "tone": "red",
            "focus": "Fix dominant 4xx/5xx; isolate worst transactions; improve logging and tracing.",
            "outcome": f"Drive error rate toward <0.5% (current {err_rate_pct:.2f}%).",
            "timeline": "Week 1–2",
        },
        {
            "phase": "Phase 2",
            "tone": "orange",
            "focus": "Async/circuit-break patterns on hot services; gateway timeouts aligned with SLOs.",
            "outcome": "Reduce timeout clusters; stabilise P95/P99 on critical journeys.",
            "timeline": "Week 2–4",
        },
        {
            "phase": "Phase 3",
            "tone": "amber",
            "focus": "Workflow engine, indexing, caching; lazy-load heavy UI metadata paths.",
            "outcome": "Restore transaction P90 under SLA for majority of labels.",
            "timeline": "Week 4–8",
        },
        {
            "phase": "Phase 4",
            "tone": "green",
            "focus": "Scale tests at target peak; soak and chaos drills; re-baseline.",
            "outcome": "Prove full SLA compliance at declared peak load.",
            "timeline": "Week 8–10",
        },
    ]

    return {
        "report_header": hdr,
        "kpi_cards": kpi_cards,
        "key_paragraphs": key_paragraphs,
        "key_findings_items": key_findings_items,
        "overall_health_cards": health_cards,
        "response_time": {
            "cards": rt_behave_cards,
            "zones_intro": [
                {
                    "zone": "A — Stable",
                    "range": "Low–mid VU",
                    "summary": "Latency and errors near baseline if test data is healthy.",
                },
                {
                    "zone": "B — Degrading",
                    "range": "Mid VU",
                    "summary": "Mean/P90 rise; first timeouts or queueing signals often appear here.",
                },
                {
                    "zone": "C — Critical",
                    "range": "High VU",
                    "summary": "Sustained tail growth, error spikes, or negative scalability in TPS.",
                },
            ],
            "band_table": band_rows,
        },
        "throughput": {
            "by_band": tps_by_band,
            "narrative": [
                {
                    "tone": "green",
                    "title": "Linear scaling phase",
                    "body": "While TPS rises with users, capacity is catching up with offered load.",
                },
                {
                    "tone": "orange",
                    "title": "Saturation / plateau",
                    "body": "TPS stalls while latency grows — typical pool or thread limit.",
                },
                {
                    "tone": "red",
                    "title": "Contention zone",
                    "body": "Oscillating TPS at flat concurrency suggests lock/pool thrash or overload.",
                },
            ],
        },
        "errors": {
            "summary": {
                "total": n_err_samples,
                "rate_pct": err_rate_pct,
                "client_4xx": n4xx,
                "client_share": client_share,
                "server_5xx": n5xx,
                "server_share": server_share,
                "n404": n404,
                "corr_r": round(r_corr, 2),
            },
            "by_transaction": err_rows[:25],
        },
        "root_causes": hypos[:8],
        "structured_issues": structured_issues,
        "optimization_plan": optimization_plan,
        "chart_downsample_note": len(ts),
    }


def performance_grading_methodology_html(grade: str, *, tooltip_on_dark: bool = False) -> str:
    """HTML fragment for modal or hover tooltip: grading scale (reuses prior scorecard copy).

    When ``tooltip_on_dark`` is True (combined report hover over overall grade), paragraph copy
    uses light text; grade-band tiles always use dark text on pastel backgrounds for contrast.
    """
    intro_c = "rgba(245,243,238,0.92)" if tooltip_on_dark else "#475569"
    tx = "#0f172a"
    sub = "#334155"
    cur = " · current" if grade == "C+" else ""
    return f"""
    <div style="padding:0.5rem 0;">
      <p style="margin:0 0 1rem 0; color:{intro_c}; font-size:0.95rem;">
        Weighted model: Performance 30%, Reliability 25%, User Experience 25%, Scalability 20%.
        Targets default to enterprise SaaS style SLAs unless overridden in the run configuration.
      </p>
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap:0.75rem;">
        <div style="background:#dcfce7;padding:0.75rem;border-radius:6px;border-left:4px solid #16a34a;"><strong style="color:{tx};font-weight:700">A+ (90–100)</strong><br><small style="color:{sub};font-size:0.8rem">Exceptional</small></div>
        <div style="background:#f0fdf4;padding:0.75rem;border-radius:6px;border-left:4px solid #22c55e;"><strong style="color:{tx};font-weight:700">A (80–89)</strong><br><small style="color:{sub};font-size:0.8rem">Excellent</small></div>
        <div style="background:#fefce8;padding:0.75rem;border-radius:6px;border-left:4px solid #eab308;"><strong style="color:{tx};font-weight:700">B+ (75–79)</strong><br><small style="color:{sub};font-size:0.8rem">Good</small></div>
        <div style="background:#fffbeb;padding:0.75rem;border-radius:6px;border-left:4px solid #f59e0b;"><strong style="color:{tx};font-weight:700">B (70–74)</strong><br><small style="color:{sub};font-size:0.8rem">Acceptable</small></div>
        <div style="background:#fef3c7;padding:0.75rem;border-radius:6px;border-left:4px solid #d97706;"><strong style="color:{tx};font-weight:700">C+ (65–69)</strong><br><small style="color:{sub};font-size:0.8rem">Marginal{cur}</small></div>
        <div style="background:#fee2e2;padding:0.75rem;border-radius:6px;border-left:4px solid #dc2626;"><strong style="color:{tx};font-weight:700">D / F (&lt;65)</strong><br><small style="color:{sub};font-size:0.8rem">Critical</small></div>
      </div>
    </div>
    """


# Re-export for backward compatibility (prefer app.report_generator.grade_narrative).
from app.report_generator.grade_narrative import format_performance_grade_release_line  # noqa: E402

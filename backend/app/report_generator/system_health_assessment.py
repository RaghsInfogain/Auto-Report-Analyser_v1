"""
Builds the structured payload for "System Health Assessment (Enhanced)" in JMeter HTML reports.
Uses global metrics (sample_time), per-label stats, GraphAnalyzer output, and time-series intervals.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _safe_corr(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 2 or len(x) != len(y):
        return 0.0
    if np.std(x) == 0 or np.std(y) == 0:
        return 0.0
    m = np.corrcoef(x, y)
    try:
        return float(m[0, 1])
    except Exception:
        return 0.0


def _guidance_latency_tail(vi: float, g_skew: float, p99: float, p50: float) -> Dict[str, str]:
    """Plain English for section 1."""
    heavy = vi > 10 or g_skew > 2
    u = (
        "Most requests finish near the median (P50), but a minority of samples are much slower, stretching the tail to P99 and beyond. "
        "A high variability index means the slowest responses are far worse than the typical response—not a uniform slowdown."
        if heavy
        else "Response times are spread in a fairly predictable way; the gap between typical and worst-case is moderate."
    )
    imp = (
        "Users hitting the slow tail see timeouts, poor UX, and failed SLAs even when the average looks acceptable. "
        "Capacity planning based only on mean or P50 will under-provision for real traffic."
        if heavy
        else "Risk to tail-sensitive SLAs (e.g. checkout) is moderate; keep monitoring P95/P99 in production."
    )
    res = (
        "Profile the slowest samples (traces, APM); tune timeouts and retries; add caching or indexes on hot paths; "
        "set alerts on P99 and VI (P99/P50), not only average latency."
        if heavy
        else "Continue periodic load tests; spot-check P99 vs P50 on each release."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_throughput_load(vu_tp_corr: float, peak_tp: float, peak_vu: int) -> Dict[str, str]:
    u = (
        "This compares how throughput moves with virtual users across time buckets. "
        "A low correlation often means throughput is capped by something other than load (serialization, thread pools, or backend limits), "
        "or that the test window mixes different phases."
        if abs(vu_tp_corr) < 0.5
        else "Throughput generally rises or falls with load in a way that matches expectations for a scalable system."
    )
    imp = (
        "If throughput does not scale with users, you may hit a hidden bottleneck before peak marketing traffic. "
        "Peak numbers alone do not prove capacity if correlation is weak."
        if abs(vu_tp_corr) < 0.5
        else "Scaling behavior looks broadly aligned with load; still validate at target peak concurrency."
    )
    res = (
        "Compare peak VUsers to thread pool, connection pool, and CPU; run a longer steady-state test at target load; "
        "use APM to see whether work queues when VUsers increase."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_timeseries(pct_drift: float, step_changes: int, n_buckets: int) -> Dict[str, str]:
    drift_big = abs(pct_drift) > 50
    many_steps = step_changes > 30
    u = (
        "We split the run into early vs late windows and count sharp jumps in average interval response time. "
        "Large drift or many steps suggests warming/cooling, saturation, GC, or dependency instability—not a flat line."
        if drift_big or many_steps
        else "Latency is relatively steady across the run; no strong late-run collapse or ramp-up artifact."
    )
    imp = (
        "Strong drift can hide a leak, cache fill, or growing queue—production may degrade over hours. "
        "Many step changes make it hard to pick a single baseline for SLAs."
        if drift_big or many_steps
        else "Release risk from time drift is lower; focus on absolute tail latency and errors."
    )
    res = (
        "Align timestamps from this test with GC logs, deployments, and downstream dashboards; extend duration if drift appears; "
        "re-run with fixed load shape to separate warmup from regression."
        if drift_big or many_steps
        else "Keep a similar duration for regression comparisons."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_errors_latency(corr_rt_err: float, hi_lat_err: float, lo_lat_err: float) -> Dict[str, str]:
    strong = abs(corr_rt_err) > 0.7
    u = (
        "We compare error rate in high-latency buckets vs low-latency buckets. "
        "A strong positive link means failures cluster when the system is already slow—often timeouts or overload."
        if strong
        else "Errors and interval latency are only weakly linked; failures may be independent of slowness (e.g. bad data, auth)."
    )
    imp = (
        "When slow intervals and errors move together, fixing latency often reduces errors; users see both pain at once."
        if strong
        else "You may need separate triage for logic bugs vs performance—errors won’t disappear only by tuning speed."
    )
    res = (
        "If correlated: increase timeouts only after fixing root cause; add circuit breakers; shed load under stress. "
        "If not: map HTTP codes and messages to business rules vs infrastructure."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_api_focus(has_slow: bool, has_unstable: bool) -> Dict[str, str]:
    u = (
        "The tables name which labels are slowest by P95 and which combine high error rate or a wide P95-to-average gap—"
        "a sign of inconsistent performance for that transaction."
    )
    imp = (
        "A few bad labels can dominate customer journeys (login, cart). Fixing them moves real user experience more than shaving a fast API."
        if has_slow
        else "Limited label data; broaden the test mix if possible."
    )
    res = (
        "Start remediation with the top P95 rows; add per-label traces; compare with production traffic mix."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_detailed(stability_badge: str, vi: float, err_pct: float, vu_rt_corr: float) -> Dict[str, str]:
    stressed = stability_badge == "Low" or vi > 15
    u = (
        "This pulls together global spread (CV, skew, VI), success rate, throughput, and how strongly latency tracks load. "
        "It is a health summary of the whole test, not a single graph."
    )
    imp = (
        "Low stability or high VI means unpredictable response times and higher incident risk under stress."
        if stressed
        else "Overall signals are mixed but not catastrophic; prioritize tail and error work before new features."
    )
    res = (
        "Use this snapshot to agree release criteria: e.g. cap on VI, minimum success rate, and max P95 for critical paths."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_correlations(vu_rt: float, vu_tp: float, rt_err: float) -> Dict[str, str]:
    u = (
        "Correlations are linear shortcuts: they show whether two series move together. "
        "They do not prove cause, but they tell you where to look first (load vs latency vs errors)."
    )
    imp = (
        "Weak VU–RT correlation with high tail latency can mean internal contention, not under-scaling. "
        "Strong error–latency correlation stresses fixing slowness and failure handling together."
    )
    res = (
        "Pair these numbers with traces: if VU–RT is flat but latency is high, profile code and data stores; "
        "if VU–RT is steep, test horizontal scale."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_bottleneck(has_bottlenecks: bool) -> Dict[str, str]:
    u = (
        "These are patterns inferred from distribution shape (tail heaviness, dispersion), not a single metric. "
        "They name likely system behaviors to validate with data."
        if has_bottlenecks
        else "No single dominant pattern stood out beyond normal variance; still validate in staging."
    )
    imp = (
        "Ignoring tail-heavy behavior leads to surprise outages when a small fraction of traffic hits the slow path."
        if has_bottlenecks
        else "Risk is lower but not zero; watch for regression on the next build."
    )
    res = (
        "Confirm each hypothesis with logs and metrics (GC, DB, thread dumps); then re-test with the same load profile."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_root_cause() -> Dict[str, str]:
    u = (
        "These are starting guesses: garbage-collection pauses, pool exhaustion, or slow backends often match long tails and weak scaling. "
        "They must be confirmed with timestamps and infrastructure signals."
    )
    imp = (
        "Acting on guesses alone can waste effort; missing a real GC or pool issue prolongs customer impact."
    )
    res = (
        "Capture JVM/GC or runtime logs for the test window; compare max threads vs pool sizes; run one controlled experiment per hypothesis."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_actionable_lists() -> Dict[str, str]:
    u = (
        "The Immediate / Medium-term / Long-term lists in this section turn findings into concrete work: "
        "immediate items reduce risk before the next release; medium-term items improve architecture; "
        "long-term items guard quality across releases."
    )
    imp = (
        "Without ownership and dates, recommendations stay in the report; production behavior stays unchanged."
    )
    res = (
        "Assign an owner per item; track in your backlog; re-run the same load profile after fixes to prove improvement."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _guidance_bottleneck_table() -> Dict[str, str]:
    u = (
        "The mapping table in this section ties each symptom to evidence and a fix direction so teams can triage "
        "in stand-up without re-reading the whole report."
    )
    imp = (
        "Duplicate symptoms across environments mean the same fix may apply everywhere."
    )
    res = (
        "Verify evidence in monitoring, then close the loop with a post-fix test run and updated thresholds."
    )
    return {"understanding": u, "impact": imp, "resolution": res}


def _stability_labels(level: Optional[str]) -> Tuple[str, str, str]:
    """Returns (stability_badge, variability_hint, overall_behavior) display strings."""
    level = (level or "").lower()
    if level in ("highly_stable", "stable"):
        return "High", "Moderate", "Stable"
    if level == "moderately_stable":
        return "Medium", "Moderate", "Mostly stable"
    if level == "unstable":
        return "Low", "High", "Unstable"
    return "Medium", "Moderate", "Mixed"


def build_enhanced_system_health(
    time_series_data: Optional[List[Dict[str, Any]]],
    metrics: Dict[str, Any],
    graph_analysis: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Returns a dict consumed by HTMLReportGenerator._generate_enhanced_system_health_html.
    """
    summary = metrics.get("summary") or {}
    st = metrics.get("sample_time") or {}
    err_frac = float(metrics.get("error_rate") or 0)
    err_pct = err_frac * 100.0
    tput = float(metrics.get("throughput") or 0)

    p50 = float(st.get("median") or 0)
    p90 = float(st.get("p90") or 0)
    p95 = float(st.get("p95") or 0)
    p99 = float(st.get("p99") or 0)
    pmax = float(st.get("max") or 0)
    mean_ms = float(st.get("mean") or 0)
    skew = float(st.get("skewness") or 0)

    vi = (p99 / p50) if p50 > 0 else 0.0

    dist = (graph_analysis.get("distribution_analysis") or {}).get("statistics") or {}
    g_skew = float(dist.get("skewness", skew) or skew)
    g_cv = float(dist.get("coefficient_of_variation", 0) or 0)

    stab = graph_analysis.get("stability")
    if isinstance(stab, dict):
        level = stab.get("level")
    else:
        level = None
    stability_badge, variability_badge, overall_behavior = _stability_labels(level)

    if vi >= 15 or g_skew > 2:
        variability_badge = "High"
    elif vi >= 8 or g_skew > 1:
        variability_badge = "Moderate"

    if stability_badge == "Low" or variability_badge == "High":
        overall_behavior = "Unstable"

    sections: List[Dict[str, Any]] = []

    shape = "right-skewed (long tail of slow requests)" if g_skew > 0.5 else "approximately symmetric"
    sections.append(
        {
            "n": 1,
            "title": "Latency distribution & tail",
            "body": (
                f"Elapsed/sample-time distribution: P50={p50:.0f} ms, P90={p90:.0f} ms, P95={p95:.0f} ms, "
                f"P99={p99:.0f} ms, max={pmax:.0f} ms. Shape is {shape} (skewness={g_skew:.2f}). "
                f"Variability Index P99/P50={vi:.2f}"
                + ("—heavy tail vs median." if vi > 5 else ".")
            ),
            **_guidance_latency_tail(vi, g_skew, p99, p50),
        }
    )

    ts = time_series_data or []
    vu_tp_corr = 0.0
    vu_rt_corr = 0.0
    peak_tp = 0.0
    peak_vu = 0
    n_buckets = len(ts)
    mean_rt_first = mean_rt_last = 0.0
    pct_drift = 0.0
    step_changes = 0
    med_delta_rt = 0.0
    hi_lat_err = lo_lat_err = 0.0
    corr_rt_err = 0.0

    if len(ts) >= 3:
        rts = np.array([float(d.get("avg_response_time") or 0) for d in ts], dtype=float)
        vus = np.array([float(d.get("vusers") or 0) for d in ts], dtype=float)
        tps = np.array([float(d.get("throughput") or 0) for d in ts], dtype=float)
        vu_tp_corr = _safe_corr(vus, tps)
        vu_rt_corr = _safe_corr(vus, rts)
        peak_tp = float(np.max(tps)) if len(tps) else 0.0
        peak_vu = int(np.max(vus)) if len(vus) else 0
        third = max(1, len(rts) // 3)
        mean_rt_first = float(np.mean(rts[:third]))
        mean_rt_last = float(np.mean(rts[-third:]))
        if mean_rt_first > 0:
            pct_drift = (mean_rt_last - mean_rt_first) / mean_rt_first * 100.0
        diffs = np.abs(np.diff(rts))
        if len(diffs):
            med_delta_rt = float(np.median(diffs))
            step_changes = int(np.sum(diffs > max(0.05, 3 * med_delta_rt)))
        # interval error ratio
        errs = []
        rts_for_bucket = []
        for d in ts:
            p = float(d.get("pass_count") or 0)
            f = float(d.get("fail_count") or 0)
            tot = p + f
            if tot <= 0:
                continue
            errs.append(f / tot)
            rts_for_bucket.append(float(d.get("avg_response_time") or 0))
        if len(errs) >= 5 and len(rts_for_bucket) == len(errs):
            rta = np.array(rts_for_bucket)
            era = np.array(errs)
            thr = float(np.percentile(rta, 75))
            hi_mask = rta >= thr
            lo_mask = rta <= float(np.percentile(rta, 25))
            hi_lat_err = float(np.mean(era[hi_mask])) * 100 if np.any(hi_mask) else 0.0
            lo_lat_err = float(np.mean(era[lo_mask])) * 100 if np.any(lo_mask) else 0.0
            corr_rt_err = _safe_corr(rta, era)

    sections.append(
        {
            "n": 2,
            "title": "Throughput vs load",
            "body": (
                f"Peak observed throughput {peak_tp:.2f} req/s at ~{peak_vu} VUsers (max VUsers {peak_vu}). "
                f"Correlation(VUsers, throughput) = {vu_tp_corr:.2f}."
            ),
            **_guidance_throughput_load(vu_tp_corr, peak_tp, peak_vu),
        }
    )

    sections.append(
        {
            "n": 3,
            "title": "Time-series behavior",
            "body": (
                f"Mean RT first third {mean_rt_first:.2f}s vs last third {mean_rt_last:.2f}s "
                f"({pct_drift:+.1f}%); "
                + ("no strong end-to-end drift." if abs(pct_drift) < 12 else "material drift across the run.")
                + f" Detected {step_changes} sharp step changes in interval RT (median |ΔRT| = {med_delta_rt:.3f}s). "
                "Intermittent spikes may indicate GC, batch work, or dependency timeouts—correlate with raw logs. "
                f"Buckets analyzed: {n_buckets}."
            ),
            **_guidance_timeseries(pct_drift, step_changes, n_buckets),
        }
    )

    sections.append(
        {
            "n": 4,
            "title": "Errors vs latency",
            "body": (
                f"In highest-latency buckets (RT ≥ ~75th percentile), mean interval error ratio ≈ {hi_lat_err:.2f}%; "
                f"in lowest-latency buckets, ≈ {lo_lat_err:.2f}%. "
                f"Correlation(RT, error_rate) = {corr_rt_err:.2f}."
            ),
            **_guidance_errors_latency(corr_rt_err, hi_lat_err, lo_lat_err),
        }
    )

    tx = summary.get("transaction_stats") or {}
    rq = summary.get("request_stats") or {}
    merged = {**tx, **rq}

    def row_slow(label: str, d: Dict[str, Any]) -> Dict[str, Any]:
        avg = float(d.get("avg_response") or 0)
        p95v = float(d.get("p95") or 0)
        p99v = float(d.get("p99") or 0)
        er = float(d.get("error_rate") or 0)
        return {"label": label, "avg_ms": avg, "p95_ms": p95v, "p99_ms": p99v, "error_pct": er}

    slow_rows = sorted((row_slow(k, v) for k, v in merged.items()), key=lambda r: -r["p95_ms"])[:8]

    unstable_rows = []
    for label, d in merged.items():
        cnt = int(d.get("count") or 0)
        if cnt < 20:
            continue
        avg = float(d.get("avg_response") or 1)
        p95v = float(d.get("p95") or 0)
        er = float(d.get("error_rate") or 0)
        ratio = (p95v / avg) if avg > 0 else 0
        if er > 0.1 or ratio > 2.0:
            unstable_rows.append(
                {"label": label, "error_pct": er, "p95_avg": ratio, "samples": cnt}
            )
    unstable_rows.sort(key=lambda x: (-x["error_pct"], -x["p95_avg"]))
    unstable_rows = unstable_rows[:8]

    sections.append(
        {
            "n": 5,
            "title": "API-level focus",
            "body": "Top slowest by P95 (ms); unstable = high error % and high P95/Avg among labels with sufficient samples.",
            **_guidance_api_focus(bool(slow_rows), bool(unstable_rows)),
        }
    )

    sections.append(
        {
            "n": 6,
            "title": "Detailed assessment",
            "body": (
                f"Stability & variability: Stability score {stability_badge} from global CV≈{g_cv:.2f}, skew={g_skew:.2f}, and VI={vi:.2f}. "
                f"Tail latency (P99) dominates median performance when VI is high. "
                f"Resource inference: success rate {100 - err_pct:.2f}%, throughput {tput:.2f} req/s, "
                f"correlation(VU,RT)={vu_rt_corr:.2f}. "
                "Contention & queuing: right-skewed latency often reflects episodic contention (DB locks, external APIs)."
            ),
            **_guidance_detailed(stability_badge, vi, err_pct, vu_rt_corr),
        }
    )

    sections.append(
        {
            "n": 7,
            "title": "Correlation insights",
            "body": (
                f"Response time vs VUsers: correlation = {vu_rt_corr:.2f}. "
                f"Throughput vs VUsers: correlation = {vu_tp_corr:.2f}. "
                f"Errors vs latency: correlation(RT, interval error rate) = {corr_rt_err:.2f}."
            ),
            **_guidance_correlations(vu_rt_corr, vu_tp_corr, corr_rt_err),
        }
    )

    bottlenecks: List[Dict[str, str]] = []
    if g_skew > 1 and vi > 5:
        bottlenecks.append(
            {
                "symptom": "Tail-heavy latency (GC, locks, or slow dependencies)",
                "evidence": f"Sample-time skewness {g_skew:.2f}; VI P99/P50 = {vi:.2f} (P99 {p99:.0f} ms vs P50 {p50:.0f} ms).",
                "root_cause": "Tail-heavy latency (GC, locks, or slow dependencies)",
                "recommendation": "Validate with JVM/GC and dependency traces; tune pools; retest with same profile.",
            }
        )
    if vi > 20:
        bottlenecks.append(
            {
                "symptom": "Extreme tail dispersion",
                "evidence": f"P99/P50 = {vi:.1f} (P99 {p99:.0f} ms, P50 {p50:.0f} ms, max {pmax:.0f} ms).",
                "root_cause": "Extreme tail dispersion",
                "recommendation": "Trace slowest percentile samples; review timeouts and downstream SLOs.",
            }
        )

    sections.append(
        {
            "n": 8,
            "title": "Bottleneck analysis",
            "body": (
                "; ".join(b["symptom"] for b in bottlenecks)
                if bottlenecks
                else "No dominant bottleneck pattern beyond general tail variability."
            ),
            **_guidance_bottleneck(bool(bottlenecks)),
        }
    )

    sections.append(
        {
            "n": 9,
            "title": "Root cause hypotheses",
            "body": (
                "GC or long pauses: validate with JVM/app GC logs aligned to timestamps. "
                "Thread pool or queue limits: throughput scaling vs VUsers—compare max threads to peak active threads in APM."
            ),
            **_guidance_root_cause(),
        }
    )

    top_labels = ", ".join(r["label"] for r in slow_rows[:3])
    rec_immediate = [
        "Tune thread pools and HTTP client max connections to match peak VUsers in this run.",
        "Align DB pool size (and connection timeout) with expected concurrency.",
        "Increase logging on timeout-related response codes to separate client vs server aborts.",
    ]
    rec_medium = [
        f"Prioritize code/query path for slowest endpoints: {top_labels}." if top_labels else "Profile slowest endpoints from the table above.",
        "Optimize slowest endpoints: reduce payload, add caching, or batch calls.",
        "Review indexes and slow query log for labels correlating with latency spikes.",
    ]
    rec_long = [
        "Horizontal scaling with autoscaling tied to queue depth and P95—not CPU alone.",
        "Synthetic tracing (OpenTelemetry) from gateway to DB to prove bottleneck tier.",
        "SLOs on P99 and error budget; alert on VI (P99/P50) regression across releases.",
    ]

    sections.append(
        {
            "n": 10,
            "title": "Actionable recommendations",
            "body": "",
            "embed_recommendations": True,
            **_guidance_actionable_lists(),
        }
    )

    sections.append(
        {
            "n": 11,
            "title": "Bottleneck mapping",
            "body": "",
            "embed_bottleneck_table": True,
            **_guidance_bottleneck_table(),
        }
    )

    business_answers = (graph_analysis.get("distribution_analysis") or {}).get("business_answers") or {}

    return {
        "subtitle": "Data-driven view: global percentiles, time-bucket correlations, API tails, and bottleneck hypotheses tied to this run.",
        "badges": {
            "stability": stability_badge,
            "variability": variability_badge,
            "overall": overall_behavior,
            "vi": round(vi, 2),
            "errors_pct": round(err_pct, 4),
            "tp_rps": round(tput, 2),
        },
        "sections": sections,
        "api_slowest": slow_rows,
        "api_unstable": unstable_rows[:8],
        "bottleneck_mapping": bottlenecks,
        "recommendations": {
            "immediate": rec_immediate,
            "medium": rec_medium,
            "long": rec_long,
        },
        "business_answers": business_answers,
    }

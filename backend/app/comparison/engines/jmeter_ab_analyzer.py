"""
JMeter Test A vs Test B deep comparison from raw JTL records.
Produces KPIs, fairness checks, per-label deltas, trend/correlation hints, and SRE-oriented narratives.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def _is_error_sample(d: Dict[str, Any]) -> bool:
    if not d.get("success", True):
        return True
    rc = str(d.get("response_code", "") or "")
    return rc.startswith("4") or rc.startswith("5")


def _calc_stats(values: np.ndarray) -> Dict[str, float]:
    if len(values) == 0:
        return {
            "mean": 0.0, "median": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0,
            "min": 0.0, "max": 0.0, "std": 0.0, "skewness": 0.0,
        }
    try:
        from scipy import stats as scipy_stats
        skewness = float(scipy_stats.skew(values))
    except ImportError:
        mean = float(np.mean(values))
        std = float(np.std(values))
        skewness = float(np.mean(((values - mean) / std) ** 3)) if std > 0 else 0.0
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p90": float(np.percentile(values, 90)),
        "p95": float(np.percentile(values, 95)),
        "p99": float(np.percentile(values, 99)),
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "std": float(np.std(values)),
        "skewness": skewness,
    }


def _pct_change(baseline: Optional[float], current: Optional[float], lower_is_better: bool = True) -> Optional[float]:
    if baseline is None or current is None:
        return None
    if baseline == 0:
        return None if current == 0 else (100.0 if current > 0 else -100.0)
    return round((current - baseline) / baseline * 100.0, 2)


def _skew_label(skew: float) -> str:
    if skew > 1.0:
        return "strong right-skew (long tail)"
    if skew > 0.5:
        return "moderate right-skew"
    if skew < -0.5:
        return "left-skew (unusual for latency)"
    return "approximately symmetric"


def _dataset_kpis(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    n = len(records)
    if n == 0:
        return {
            "sample_count": 0, "error_count": 0, "error_pct": 0.0,
            "throughput_rps": 0.0, "duration_sec": 0.0,
            "sample_time": _calc_stats(np.array([])),
            "latency": _calc_stats(np.array([])),
            "connect_time": _calc_stats(np.array([])),
        }
    sample_times = np.array([float(d.get("sample_time") or 0) for d in records], dtype=float)
    latencies = np.array([float(d.get("latency") or 0) for d in records], dtype=float)
    connects = np.array([float(d.get("connect_time") or 0) for d in records], dtype=float)
    ts_list = [int(d.get("timestamp") or 0) for d in records if d.get("timestamp")]
    err = sum(1 for d in records if _is_error_sample(d))
    duration_sec = (max(ts_list) - min(ts_list)) / 1000.0 if len(ts_list) > 1 else 0.0
    throughput = n / duration_sec if duration_sec > 0 else 0.0
    return {
        "sample_count": n,
        "error_count": err,
        "error_pct": round(100.0 * err / n, 4) if n else 0.0,
        "throughput_rps": round(throughput, 4),
        "duration_sec": round(duration_sec, 3),
        "sample_time": _calc_stats(sample_times),
        "latency": _calc_stats(latencies),
        "connect_time": _calc_stats(connects),
    }


def _workload_profile(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "max_threads": 0, "mean_threads": 0.0, "p95_threads": 0.0,
            "unique_labels": 0, "first_ts": 0, "last_ts": 0, "duration_sec": 0.0,
        }
    threads = [int(d.get("all_threads") or 0) for d in records]
    labels = {d.get("label") or "" for d in records}
    labels.discard("")
    ts = [int(d.get("timestamp") or 0) for d in records if d.get("timestamp")]
    arr = np.array(threads, dtype=float) if threads else np.array([], dtype=float)
    duration_sec = (max(ts) - min(ts)) / 1000.0 if len(ts) > 1 else 0.0
    return {
        "max_threads": int(max(threads)) if threads else 0,
        "mean_threads": float(np.mean(arr)) if len(arr) else 0.0,
        "p95_threads": float(np.percentile(arr, 95)) if len(arr) else 0.0,
        "unique_labels": len(labels),
        "first_ts": min(ts) if ts else 0,
        "last_ts": max(ts) if ts else 0,
        "duration_sec": round(duration_sec, 3),
    }


def _per_label(records: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    groups: Dict[str, List[Dict]] = defaultdict(list)
    for d in records:
        lb = (d.get("label") or "").strip()
        if not lb:
            continue
        groups[lb].append(d)
    out: Dict[str, Dict[str, Any]] = {}
    for lb, items in groups.items():
        st = np.array([float(x.get("sample_time") or 0) for x in items], dtype=float)
        err = sum(1 for x in items if _is_error_sample(x))
        n = len(items)
        stats = _calc_stats(st)
        dur_items = [int(x.get("timestamp") or 0) for x in items if x.get("timestamp")]
        dsec = (max(dur_items) - min(dur_items)) / 1000.0 if len(dur_items) > 1 else 0.0
        tput = n / dsec if dsec > 0 else 0.0
        out[lb] = {
            "count": n,
            "error_count": err,
            "error_pct": round(100.0 * err / n, 4) if n else 0.0,
            "avg_ms": round(stats["mean"], 2),
            "p95_ms": round(stats["p95"], 2),
            "p99_ms": round(stats["p99"], 2),
            "throughput_rps": round(tput, 4),
        }
    return out


def _time_buckets(records: List[Dict[str, Any]], num_buckets: int = 24) -> List[Dict[str, Any]]:
    if not records:
        return []
    ts = [int(d.get("timestamp") or 0) for d in records if d.get("timestamp")]
    if len(ts) < 2:
        return []
    t0, t1 = min(ts), max(ts)
    span = max((t1 - t0) / 1000.0, 1e-6)
    bucket_sec = span / num_buckets
    buckets: Dict[int, Dict[str, Any]] = defaultdict(lambda: {"rts": [], "threads": [], "errs": 0, "n": 0})
    for d in records:
        t = int(d.get("timestamp") or 0)
        if not t:
            continue
        idx = int((t - t0) / 1000.0 / bucket_sec)
        idx = min(max(idx, 0), num_buckets - 1)
        b = buckets[idx]
        b["rts"].append(float(d.get("sample_time") or 0))
        b["threads"].append(int(d.get("all_threads") or 0))
        b["n"] += 1
        if _is_error_sample(d):
            b["errs"] += 1
    rows = []
    for i in sorted(buckets.keys()):
        b = buckets[i]
        rts = np.array(b["rts"], dtype=float)
        thr = np.array(b["threads"], dtype=float) if b["threads"] else np.array([0.0])
        rows.append({
            "bucket_index": i,
            "time_start_sec": round(i * bucket_sec, 2),
            "mean_rt_ms": round(float(np.mean(rts)), 2) if len(rts) else 0.0,
            "p95_rt_ms": round(float(np.percentile(rts, 95)), 2) if len(rts) else 0.0,
            "mean_threads": round(float(np.mean(thr)), 2),
            "samples": b["n"],
            "error_pct": round(100.0 * b["errs"] / b["n"], 2) if b["n"] else 0.0,
            "throughput_rps": round(b["n"] / bucket_sec, 4),
        })
    return rows


def _threads_vs_rt_bins(records: List[Dict[str, Any]], bins: int = 5) -> List[Dict[str, Any]]:
    if not records:
        return []
    pairs = [(int(d.get("all_threads") or 0), float(d.get("sample_time") or 0)) for d in records]
    threads = np.array([p[0] for p in pairs], dtype=float)
    rts = np.array([p[1] for p in pairs], dtype=float)
    if len(threads) == 0:
        return []
    edges = np.linspace(threads.min(), max(threads.max(), threads.min() + 1), bins + 1)
    rows = []
    for i in range(bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (threads >= lo) & (threads <= hi if i == bins - 1 else threads < hi)
        if not np.any(mask):
            continue
        sub = rts[mask]
        err_n = sum(1 for j in range(len(records)) if bool(mask[j]) and _is_error_sample(records[j]))
        rows.append({
            "thread_range": f"{int(lo)}–{int(hi)}",
            "samples": int(np.sum(mask)),
            "mean_rt_ms": round(float(np.mean(sub)), 2),
            "error_pct": round(100.0 * err_n / max(int(np.sum(mask)), 1), 2),
        })
    return rows


def _fairness_warnings(
    ka: Dict, kb: Dict, wa: Dict, wb: Dict,
) -> Tuple[List[str], bool]:
    warnings = []
    apples = True
    da, db = ka.get("duration_sec") or 0, kb.get("duration_sec") or 0
    if da > 0 and db > 0:
        ratio = max(da, db) / min(da, db)
        if ratio > 1.25:
            warnings.append(
                f"Test duration differs materially (A: {da:.1f}s vs B: {db:.1f}s, ratio {ratio:.2f}x). "
                "Throughput and saturation windows are not directly comparable."
            )
            apples = False
    na, nb = wa.get("max_threads", 0), wb.get("max_threads", 0)
    if na > 0 and nb > 0 and max(na, nb) / min(na, nb) > 1.2:
        warnings.append(
            f"Peak concurrent threads differ (A max {na} vs B max {nb}). "
            "Tail latency and error trends may reflect load level, not build quality alone."
        )
        apples = False
    ca, cb = ka["sample_count"], kb["sample_count"]
    if ca > 0 and cb > 0 and max(ca, cb) / min(ca, cb) > 1.5:
        warnings.append(
            f"Sample counts differ strongly (A: {ca:,} vs B: {cb:,}). "
            "Statistical confidence and workload intensity may not match."
        )
        apples = False
    return warnings, apples


def _label_overlap(a_labels: Dict, b_labels: Dict) -> float:
    sa, sb = set(a_labels.keys()), set(b_labels.keys())
    if not sa or not sb:
        return 0.0
    return round(100.0 * len(sa & sb) / len(sa | sb), 1)


def _bottleneck_hypotheses(
    name: str, kpis: Dict, workload: Dict, buckets: List[Dict], tv_bins: List[Dict]
) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    st = kpis["sample_time"]
    lat = kpis["latency"]["mean"]
    conn = kpis["connect_time"]["mean"]
    errp = kpis["error_pct"]
    skew = st["skewness"]
    vi = (st["p99"] / st["median"]) if st["median"] and st["median"] > 0 else None

    if conn > 50 and conn > 0.25 * max(lat, 1):
        out.append({
            "type": "Network / TCP connect",
            "evidence": f"{name}: mean connect time {conn:.1f} ms vs mean latency {lat:.1f} ms.",
            "impact": "Handshake or path latency may dominate; check DNS, TLS, and geographic distance.",
            "when": "Visible across samples, not only tail.",
        })

    if tv_bins and len(tv_bins) >= 2:
        first, last = tv_bins[0], tv_bins[-1]
        if last.get("mean_rt_ms", 0) > first.get("mean_rt_ms", 0) * 1.4 and workload.get("max_threads", 0) > 10:
            out.append({
                "type": "Saturation / thread scaling",
                "evidence": f"Mean RT rises from ~{first['mean_rt_ms']:.0f} ms at lower thread counts "
                f"to ~{last['mean_rt_ms']:.0f} ms in the highest thread bin ({last.get('thread_range', '')}).",
                "impact": "Suggests queueing or resource limits as concurrency increases.",
                "when": f"Under higher active threads (up to {workload.get('max_threads', 0)}).",
            })

    if vi and vi > 8 and skew > 0.5:
        out.append({
            "type": "Long-tail latency (GC, locks, or slow dependencies)",
            "evidence": f"P99/P50 variability index {vi:.1f}; skewness {skew:.2f} ({_skew_label(skew)}).",
            "impact": "A small fraction of requests drive SLO risk; investigate tail-specific causes.",
            "when": "Typically intermittent or load-correlated.",
        })

    if buckets and len(buckets) >= 4:
        rts = [b["mean_rt_ms"] for b in buckets]
        med = float(np.median(np.array(rts)))
        spikes = [b for b in buckets if b["mean_rt_ms"] > med * 1.6 and b["samples"] > 10]
        if spikes:
            t0 = spikes[0]["time_start_sec"]
            out.append({
                "type": "Time-localized degradation or spike",
                "evidence": f"One or more windows show mean RT >1.6× median ({med:.0f} ms), e.g. near t≈{t0:.0f}s.",
                "impact": "Could be cache warm-up, external dependency incident, or infra event.",
                "when": f"Mid-test windows (see bucket {spikes[0]['bucket_index']}).",
            })

    if errp > 1.0 and tv_bins:
        hi = max(tv_bins, key=lambda x: x.get("mean_rt_ms", 0))
        if hi.get("error_pct", 0) > errp * 0.8:
            out.append({
                "type": "Errors correlated with latency",
                "evidence": f"Error rate {errp:.2f}% with elevated RT in high-load thread bin ({hi.get('thread_range', 'n/a')}).",
                "impact": "Timeouts or circuit-breaking under stress; verify thread pools and downstream SLOs.",
                "when": "Under stress bins with highest mean RT.",
            })

    return out[:6]


def _correlation_insights(
    name_a: str, name_b: str,
    buckets_a: List[Dict], buckets_b: List[Dict],
    tv_a: List[Dict], tv_b: List[Dict],
    wa: Dict, wb: Dict,
    kp_a: Dict, kp_b: Dict,
) -> List[str]:
    lines = []
    if tv_a and len(tv_a) >= 2:
        lo, hi = tv_a[0]["mean_rt_ms"], tv_a[-1]["mean_rt_ms"]
        if hi > lo * 1.25:
            lines.append(
                f"{name_a}: response time increases from ~{lo:.0f} ms to ~{hi:.0f} ms from lowest to highest thread bin."
            )
    if tv_b and len(tv_b) >= 2:
        lo, hi = tv_b[0]["mean_rt_ms"], tv_b[-1]["mean_rt_ms"]
        if hi > lo * 1.25:
            lines.append(
                f"{name_b}: response time increases from ~{lo:.0f} ms to ~{hi:.0f} ms as thread bins increase."
            )
    if buckets_a and len(buckets_a) >= 3:
        tps = [b["throughput_rps"] for b in buckets_a]
        tail = np.mean(tps[-3:]) if len(tps) >= 3 else tps[-1]
        head = np.mean(tps[:3]) if len(tps) >= 3 else tps[0]
        if head > 0 and 0.85 <= (tail / head) <= 1.15 and wa.get("max_threads", 0) > 5:
            lines.append(
                f"{name_a}: throughput stays within ~±15% between early and late windows (possible plateau ~{tail:.1f} req/s)."
            )
    if buckets_b and len(buckets_b) >= 3:
        tps = [b["throughput_rps"] for b in buckets_b]
        tail = np.mean(tps[-3:]) if len(tps) >= 3 else tps[-1]
        head = np.mean(tps[:3]) if len(tps) >= 3 else tps[0]
        if head > 0 and 0.85 <= (tail / head) <= 1.15:
            lines.append(
                f"{name_b}: similar throughput stability late in the test (~{tail:.1f} req/s vs early ~{head:.1f} req/s)."
            )
    # Errors when latency high
    high_lat_threshold_a = kp_a["sample_time"]["p95"]
    high_lat_threshold_b = kp_b["sample_time"]["p95"]
    # approximate: bucket error vs mean rt
    for label, buckets, thr in ((name_a, buckets_a, high_lat_threshold_a), (name_b, buckets_b, high_lat_threshold_b)):
        hi_err = [b for b in buckets if b.get("mean_rt_ms", 0) > thr * 1.1]
        lo_err = [b for b in buckets if b.get("mean_rt_ms", 0) <= thr * 0.9]
        if hi_err and lo_err:
            eh = np.mean([b["error_pct"] for b in hi_err])
            el = np.mean([b["error_pct"] for b in lo_err])
            if eh > el + 0.5:
                lines.append(
                    f"{label}: errors average {eh:.2f}% in windows with mean RT above ~{thr * 1.1:.0f} ms "
                    f"vs {el:.2f}% in cooler windows."
                )
    return lines


def _executive_verdict(ka: Dict, kb: Dict, pct: Dict[str, Optional[float]]) -> Dict[str, Any]:
    p95_c = pct.get("p95_ms")
    p99_c = pct.get("p99_ms")
    err_c = pct.get("error_pct")
    tput_c = pct.get("throughput_rps")
    risks = []
    if p95_c is not None and p95_c > 10:
        risks.append(f"P95 latency regressed ~{p95_c:.1f}% vs baseline.")
    if p99_c is not None and p99_c > 20:
        risks.append(f"P99 regressed ~{p99_c:.1f}% — tail SLO risk.")
    if err_c is not None and err_c > 0 and kb["error_pct"] > ka["error_pct"] + 0.5:
        risks.append(f"Error rate increased (A {ka['error_pct']:.2f}% → B {kb['error_pct']:.2f}%).")
    if tput_c is not None and tput_c < -15:
        risks.append(f"Throughput dropped ~{abs(tput_c):.1f}% at comparable calendar duration.")

    score = 0
    if p95_c is not None:
        score += -2 if p95_c > 15 else (-1 if p95_c > 5 else (1 if p95_c < -5 else 0))
    if p99_c is not None:
        score += -2 if p99_c > 25 else (-1 if p99_c > 10 else 0)
    if err_c is not None:
        score += -2 if kb["error_pct"] > ka["error_pct"] + 2 else (-1 if kb["error_pct"] > ka["error_pct"] + 0.5 else 0)
    if tput_c is not None:
        score += 1 if tput_c > 5 and (p95_c is None or p95_c < 10) else 0
        score += -1 if tput_c < -20 else 0

    if score >= 1 and not risks:
        verdict, rec = "Improved", "Go — primary latency and reliability signals improved or stable."
    elif score <= -3 or (p95_c and p95_c > 20) or (kb["error_pct"] > 5 and kb["error_pct"] > ka["error_pct"]):
        verdict, rec = "Degraded", "No-Go — address regressions before production; re-test after fixes."
    elif score < 0 or risks:
        verdict, rec = "Mixed / at risk", "Conditional — review tail latency and errors; consider canary only with guardrails."
    else:
        verdict, rec = "No material change", "Go with monitoring — no strong signal of improvement or regression."

    improvements = []
    if p95_c is not None and p95_c < -5:
        improvements.append(f"P95 ~{abs(p95_c):.1f}% lower than baseline.")
    if p99_c is not None and p99_c < -5:
        improvements.append(f"P99 ~{abs(p99_c):.1f}% lower.")
    if tput_c is not None and tput_c > 10:
        improvements.append(f"Throughput ~{tput_c:.1f}% higher.")

    if verdict == "Degraded":
        traffic_signal = "red"
    elif verdict == "Mixed / at risk":
        traffic_signal = "amber"
    else:
        traffic_signal = "green"

    return {
        "verdict": verdict,
        "recommendation": rec,
        "risks": risks,
        "improvements": improvements,
        "traffic_signal": traffic_signal,
    }


def _slo_and_alerts(ka: Dict, kb: Dict) -> Tuple[List[str], List[str], List[str]]:
    """Recommend SLO targets and alert thresholds from the stricter of observed behavior."""
    p95 = min(ka["sample_time"]["p95"], kb["sample_time"]["p95"])
    p99 = min(ka["sample_time"]["p99"], kb["sample_time"]["p99"])
    # Target slightly better than best observed under test (aspirational)
    slo = [
        f"Latency SLO (P95): ≤ {max(p95 * 1.1, p95 + 50):.0f} ms under comparable load.",
        f"Latency SLO (P99): ≤ {max(p99 * 1.15, p99 + 100):.0f} ms.",
        f"Availability SLO: ≥ {100 - max(ka['error_pct'], kb['error_pct']) * 2:.2f}% success (test-derived ceiling).",
    ]
    alerts = [
        f"Alert if P95 > {max(ka['sample_time']['p95'], kb['sample_time']['p95']) * 1.25:.0f} ms for 5+ minutes.",
        f"Alert if P99 > {max(ka['sample_time']['p99'], kb['sample_time']['p99']) * 1.3:.0f} ms (tail regression).",
        f"Alert if error rate > {max(ka['error_pct'], kb['error_pct'], 0.5) * 2:.2f}% over 3 consecutive windows.",
        f"Alert if throughput drops > 25% vs same-load baseline window.",
    ]
    remed = [
        "Auto-scale out (HPA) when P95 > SLO and CPU > 70% for 3m.",
        "Circuit-break slow dependencies when error spike correlates with RT > P95 test threshold.",
        "Restart or drain noisy instances when single AZ shows error burst + connect time spike.",
        "Throttle non-critical traffic when thread-pool queue depth exceeds configured watermark.",
    ]
    return slo, alerts, remed


def analyze_jmeter_ab(
    records_a: List[Dict[str, Any]],
    records_b: List[Dict[str, Any]],
    name_a: str = "Test A (Baseline)",
    name_b: str = "Test B",
    environment_a: Optional[str] = None,
    environment_b: Optional[str] = None,
    build_a: Optional[str] = None,
    build_b: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full A/B analysis dict for HTML/JSON report.
    """
    issues_a, issues_b = [], []
    if not records_a:
        issues_a.append("Test A has no valid samples after parsing.")
    if not records_b:
        issues_b.append("Test B has no valid samples after parsing.")

    ka = _dataset_kpis(records_a)
    kb = _dataset_kpis(records_b)
    wa = _workload_profile(records_a)
    wb = _workload_profile(records_b)
    la = _per_label(records_a)
    lb = _per_label(records_b)

    sta, stb = ka["sample_time"], kb["sample_time"]
    via = (sta["p99"] / sta["median"]) if sta["median"] > 0 else None
    vib = (stb["p99"] / stb["median"]) if stb["median"] > 0 else None

    fairness_warnings, apples = _fairness_warnings(ka, kb, wa, wb)
    overlap = _label_overlap(la, lb)
    if overlap < 60 and la and lb:
        fairness_warnings.append(
            f"Only {overlap}% label overlap between runs — API mix may differ; per-API deltas are partial."
        )
        apples = False

    pct = {
        "avg_ms": _pct_change(sta["mean"], stb["mean"], True),
        "median_ms": _pct_change(sta["median"], stb["median"], True),
        "p90_ms": _pct_change(sta["p90"], stb["p90"], True),
        "p95_ms": _pct_change(sta["p95"], stb["p95"], True),
        "p99_ms": _pct_change(sta["p99"], stb["p99"], True),
        "max_ms": _pct_change(sta["max"], stb["max"], True),
        "throughput_rps": _pct_change(ka["throughput_rps"], kb["throughput_rps"], False),
        "error_pct": _pct_change(ka["error_pct"], kb["error_pct"], True),
        "latency_avg_ms": _pct_change(ka["latency"]["mean"], kb["latency"]["mean"], True),
        "connect_avg_ms": _pct_change(ka["connect_time"]["mean"], kb["connect_time"]["mean"], True),
    }

    buckets_a = _time_buckets(records_a)
    buckets_b = _time_buckets(records_b)
    tv_a = _threads_vs_rt_bins(records_a)
    tv_b = _threads_vs_rt_bins(records_b)

    corr = _correlation_insights(name_a, name_b, buckets_a, buckets_b, tv_a, tv_b, wa, wb, ka, kb)
    bottlenecks = []
    bottlenecks.extend(_bottleneck_hypotheses(name_a, ka, wa, buckets_a, tv_a))
    bottlenecks.extend(_bottleneck_hypotheses(name_b, kb, wb, buckets_b, tv_b))

    # Per-label deltas (common labels)
    api_rows = []
    common = set(la.keys()) & set(lb.keys())
    for lb_name in sorted(common):
        a, b = la[lb_name], lb[lb_name]
        dp95 = _pct_change(a["p95_ms"], b["p95_ms"], True)
        api_rows.append({
            "label": lb_name,
            "a_avg": a["avg_ms"], "b_avg": b["avg_ms"],
            "a_p95": a["p95_ms"], "b_p95": b["p95_ms"],
            "a_p99": a["p99_ms"], "b_p99": b["p99_ms"],
            "a_err_pct": a["error_pct"], "b_err_pct": b["error_pct"],
            "a_tput": a.get("throughput_rps", 0),
            "b_tput": b.get("throughput_rps", 0),
            "p95_change_pct": dp95,
            "a_n": a["count"], "b_n": b["count"],
        })
    api_rows.sort(key=lambda x: x["b_p95"], reverse=True)
    top_slow_labels = sorted(lb.keys(), key=lambda k: lb[k]["p99_ms"], reverse=True)[:3]

    improved = [r for r in api_rows if r["p95_change_pct"] is not None and r["p95_change_pct"] < -5]
    improved.sort(key=lambda x: x["p95_change_pct"] or 0)
    degraded = [r for r in api_rows if r["p95_change_pct"] is not None and r["p95_change_pct"] > 5]
    degraded.sort(key=lambda x: x["p95_change_pct"] or 0, reverse=True)

    exec_summary = _executive_verdict(ka, kb, pct)
    slo, alerts, remed = _slo_and_alerts(ka, kb)

    # Trend narrative
    def _trend_sentence(name: str, buckets: List[Dict]) -> str:
        if len(buckets) < 3:
            return f"{name}: insufficient time resolution for trend."
        early = np.mean([b["mean_rt_ms"] for b in buckets[:3]])
        late = np.mean([b["mean_rt_ms"] for b in buckets[-3:]])
        if late > early * 1.2:
            return f"{name}: mean response time drifts upward late in the test (~{early:.0f} ms → ~{late:.0f} ms), suggesting gradual degradation or warming effects."
        if late < early * 0.85:
            return f"{name}: mean response time improves in later windows (~{early:.0f} ms → ~{late:.0f} ms), consistent with warm-up or cache fill."
        return f"{name}: mean response time is relatively stable across windows (~{early:.0f}–{late:.0f} ms)."

    trend_notes = [_trend_sentence(name_a, buckets_a), _trend_sentence(name_b, buckets_b)]
    stability = (
        f"Variability index (P99/P50): A {via:.2f}" if via else "A n/a"
    ) + (f", B {vib:.2f}. " if vib else ". ")
    if via and vib:
        stability += "Lower is more stable; compare skewness for long-tail risk."
    observations = [
        f"Response-time skew: A {_skew_label(sta['skewness'])} (skew={sta['skewness']:.2f}); "
        f"B {_skew_label(stb['skewness'])} (skew={stb['skewness']:.2f}).",
        stability,
    ]
    if via and vib and vib > via * 1.15:
        observations.append("Test B shows higher tail variability than A (P99/P50 larger) — prioritize tail-focused tuning on B.")

    recommendations = {
        "immediate": [],
        "medium": [],
        "long": [],
    }
    if pct.get("p95_ms", 0) and pct["p95_ms"] > 10:
        recommendations["immediate"].append("Profile top regressed APIs (see table) and verify thread pool / DB pool sizes under peak threads.")
    if kb["error_pct"] > ka["error_pct"]:
        recommendations["immediate"].append("Triage new failures: map HTTP codes and messages to downstream timeouts vs assertions.")
    if (via or 0) > 6 or (vib or 0) > 6:
        recommendations["medium"].append("Add tracing on P99 path; check GC logs and external dependency dashboards during spike windows.")
    recommendations["medium"].append("Re-run with matched duration and max threads to confirm findings if fairness warnings apply.")
    recommendations["long"].append("Define SLOs from production traffic; align load model to critical user journeys and peak concurrency.")

    out = {
        "meta": {
            "name_a": name_a,
            "name_b": name_b,
            "environment_a": environment_a,
            "environment_b": environment_b,
            "build_a": build_a,
            "build_b": build_b,
            "generated_for": "jmeter_ab_comparison",
        },
        "data_prep": {
            "issues_a": issues_a,
            "issues_b": issues_b,
            "fairness_warnings": fairness_warnings,
            "apples_to_apples": apples,
            "label_overlap_pct": overlap,
        },
        "test_a": {"kpis": ka, "workload": wa, "variability_index": round(via, 3) if via else None},
        "test_b": {"kpis": kb, "workload": wb, "variability_index": round(vib, 3) if vib else None},
        "kpi_percent_change": pct,
        "workload_table": [
            {"parameter": "Duration (s)", "test_a": ka["duration_sec"] if records_a else 0, "test_b": kb["duration_sec"] if records_b else 0,
             "remarks": "Wall-clock span from first to last sample timestamp."},
            {"parameter": "Total samples", "test_a": ka["sample_count"], "test_b": kb["sample_count"],
             "remarks": "All parsed rows with label+timestamp."},
            {"parameter": "Max active threads (allThreads)", "test_a": wa["max_threads"], "test_b": wb["max_threads"],
             "remarks": "Peak reported concurrency in JTL."},
            {"parameter": "Mean active threads", "test_a": round(wa["mean_threads"], 2), "test_b": round(wb["mean_threads"], 2),
             "remarks": "Average across samples."},
            {"parameter": "Unique labels (APIs)", "test_a": wa["unique_labels"], "test_b": wb["unique_labels"],
             "remarks": f"Overlap {overlap}% of combined label set."},
        ],
        "trend": {
            "notes": trend_notes,
            "series_a": buckets_a,
            "series_b": buckets_b,
        },
        "correlation_insights": corr,
        "bottlenecks": bottlenecks,
        "api_comparison": api_rows,
        "highlights": {
            "top_slowest_apis_b": [{"label": x, "p99_ms": lb[x]["p99_ms"], "p95_ms": lb[x]["p95_ms"]} for x in top_slow_labels],
            "most_improved_p95": [{"label": x["label"], "p95_change_pct": x["p95_change_pct"]} for x in improved[:5]],
            "most_degraded_p95": [{"label": x["label"], "p95_change_pct": x["p95_change_pct"]} for x in degraded[:5]],
        },
        "executive_summary": exec_summary,
        "observations": observations,
        "recommendations": recommendations,
        "slo_recommendations": slo,
        "alert_thresholds": alerts,
        "auto_remediation": remed,
        "threads_vs_rt": {"test_a": tv_a, "test_b": tv_b},
        "conclusion": {
            "decision": exec_summary["verdict"],
            "production_readiness": exec_summary["recommendation"],
        },
    }
    try:
        from app.report_generator.jmeter_ab_enrichment import extend_jmeter_ab_analysis

        out.update(
            extend_jmeter_ab_analysis(
                out,
                records_a,
                records_b,
                la,
                lb,
                buckets_a,
                buckets_b,
                name_a,
                name_b,
            )
        )
    except Exception as e:
        print(f"JMeter A/B enrichment skipped: {e}")
    return out

"""
Build structured payload for the Combined Load Test HTML report (editorial layout).
Computes per-minute series, load bands, scenarios, scorecard, Apdex, and chart arrays from raw JMeter rows.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

import numpy as np

from app.analyzers.jmeter_analyzer_v2 import JMeterAnalyzerV2 as _JMeterV2
from app.report_generator.grade_narrative import format_performance_grade_release_line
from app.utils.jmeter_outcome import is_jmeter_error_outcome
from app.utils.jmeter_url import is_jmeter_transaction_controller_by_url, normalize_jmeter_url_value


def _elapsed_ms(d: Dict[str, Any]) -> float:
    v = d.get("sample_time")
    if v is None:
        v = d.get("elapsed")
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _jm_explicit_success(d: Dict[str, Any]) -> bool:
    """True when the JMeter sample is marked successful (used for RT stats and pass counting per user rules)."""
    if "success" not in d:
        return True
    s = d["success"]
    if isinstance(s, bool):
        return s
    if isinstance(s, str):
        return s.strip().lower() in ("true", "1", "yes")
    if isinstance(s, (int, float)):
        return s != 0
    return bool(s)


def _vu(d: Dict[str, Any]) -> int:
    for k in ("all_threads", "allThreads", "grp_threads", "grpThreads"):
        v = d.get(k)
        if v is not None:
            try:
                return int(float(v))
            except (TypeError, ValueError):
                continue
    return 0


def _scenario_display(thread_name: str) -> str:
    base = (thread_name or "").split(" - ")[0].strip()
    u = base.upper()
    if "TS01" in u and "TS02" in u:
        return "TS01/02 CreateLead"
    if "TS03" in u:
        return "TS03 Leads"
    if "TS06" in u:
        return "TS06 Case"
    if "TS05" in u:
        return "TS05 Lead"
    if base:
        return base[:56]
    return "Other"


def _environment_from_url(url: str) -> str:
    u = normalize_jmeter_url_value(url)
    if not u:
        return ""
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u):
        u = "https://" + u.lstrip("/")
    try:
        host = urlparse(u).hostname or ""
    except Exception:
        return ""
    return host.split(".")[0] if host else ""


def _apdex(samples_ms: List[float], t_ms: float = 3000.0) -> float:
    if not samples_ms:
        return 0.0
    sat = sum(1 for x in samples_ms if x <= t_ms)
    tol = sum(1 for x in samples_ms if t_ms < x <= 4 * t_ms)
    return round((sat + 0.5 * tol) / len(samples_ms), 3)


def _apdex_label(score: float) -> str:
    if score >= 0.94:
        return "Excellent"
    if score >= 0.85:
        return "Good"
    if score >= 0.70:
        return "Fair"
    if score >= 0.50:
        return "Poor"
    return "Unacceptable"


def _tx_status(err_pct: float, p90_ms: Optional[float]) -> str:
    p90_s = (p90_ms or 0) / 1000.0
    if err_pct > 10 or p90_s > 30:
        return "critical"
    if err_pct > 2 or p90_s > 10:
        return "warning"
    if p90_s >= 3:
        return "slow"
    return "healthy"


HEAT_EDGES_MS = [0, 100, 500, 1000, 3000, 5000, 10000, 30000, 60000, 180000, 1e12]


def _heat_bucket_idx(ms: float) -> int:
    for i in range(len(HEAT_EDGES_MS) - 1):
        if HEAT_EDGES_MS[i] <= ms < HEAT_EDGES_MS[i + 1]:
            return i
    return len(HEAT_EDGES_MS) - 2


LOAD_BANDS: List[Tuple[str, int, int]] = [
    ("1–30 VU", 1, 30),
    ("31–60 VU", 31, 60),
    ("61–120 VU", 61, 120),
    ("121–180 VU", 121, 180),
    ("181–240 VU", 181, 240),
    ("241–300 VU", 241, 300),
]

# Latency decomposition (TTFB P90 ms): first band uses an absolute cutoff; later bands use
# % increase vs previous non-empty band. Saturating/Critical also use deviation + ceilings.
_LAT_INIT_APPQ_MS = 850.0
_LAT_DEV_APPQ = 0.25  # >25% vs previous → App queuing
_LAT_DEV_SAT = 0.40  # ≥40% vs previous → Saturating
_LAT_DEV_CRIT = 0.60  # ≥60% vs previous → Critical
_LAT_TTFB_SAT_MS = 1200.0
_LAT_TTFB_CRIT_MS = 2000.0
_LAT_MEAN_RT_CRIT_MS = 8000.0


def _latency_decomp_badge(
    ttfb_p90: float,
    mean_rt: float,
    band_index: int,
    prev_ttfb_p90: Optional[float],
) -> Tuple[str, str]:
    """
    First populated band: TTFB P90 > 850 ms → App queuing, else Healthy.
    Later bands: TTFB P90 vs previous band — >25% increase → App queuing; ≥40% → Saturating;
    ≥60% or absolute TTFB / mean-RT pressure → Critical.
    """
    cur = float(ttfb_p90)
    mrt = float(mean_rt)
    rel_inc: Optional[float] = None
    if band_index > 0 and prev_ttfb_p90 is not None:
        prev = float(prev_ttfb_p90)
        rel_inc = (cur - prev) / max(prev, 1e-6)

    if (
        cur >= _LAT_TTFB_CRIT_MS
        or mrt > _LAT_MEAN_RT_CRIT_MS
        or (rel_inc is not None and rel_inc >= _LAT_DEV_CRIT)
    ):
        return ("red", "Critical")
    if cur >= _LAT_TTFB_SAT_MS or (rel_inc is not None and rel_inc >= _LAT_DEV_SAT):
        return ("outline-red", "Saturating")
    if band_index == 0:
        if cur > _LAT_INIT_APPQ_MS:
            return ("outline-amber", "App queuing")
        return ("outline-green", "Healthy")
    if rel_inc is not None and rel_inc > _LAT_DEV_APPQ:
        return ("outline-amber", "App queuing")
    return ("outline-green", "Healthy")


def _derive_dynamic_load_bands(data: List[Dict[str, Any]], max_vu: int) -> List[Tuple[str, int, int]]:
    """
    VU buckets sized from observed concurrency in this run (not fixed 1–30 / 31–60 …).
    Partitions [min_vu, max_vu] into a small number of bands so each band can be classified
    as stable / degrading / high-stress vs saved gates.
    """
    vus = [_vu(d) for d in data]
    if not vus:
        return [("0 VU", 0, 0)]
    mn = int(min(vus))
    mx = max(int(max(vus)), int(max_vu or 0))
    if mx < mn:
        mx = mn
    if mx == mn:
        return [(f"{mn} VU", mn, mx)]
    span = mx - mn + 1
    if span <= 4:
        n_bin = min(span, 3)
    elif span <= 20:
        n_bin = 4
    elif span <= 80:
        n_bin = 5
    else:
        n_bin = min(7, max(5, span // 45))
    width = max(1, int(np.ceil(span / n_bin)))
    bands: List[Tuple[str, int, int]] = []
    lo = mn
    while lo <= mx:
        hi = min(lo + width - 1, mx)
        lbl = f"{lo} VU" if lo == hi else f"{lo}–{hi} VU"
        bands.append((lbl, lo, hi))
        lo = hi + 1
    return bands


def _zone_agg(band_stats: List[Dict[str, Any]], labels: List[str]) -> Optional[Dict[str, Any]]:
    sub = [b for b in band_stats if b.get("label") in labels and b.get("n")]
    if not sub:
        return None
    n = sum(int(b["n"]) for b in sub)
    if n <= 0:
        return None
    mean_rt = sum(float(b["mean_rt"]) * int(b["n"]) for b in sub) / n
    p90 = sum(float(b["p90"]) * int(b["n"]) for b in sub) / n
    err = sum(float(b["err_pct"]) * int(b["n"]) for b in sub) / n
    lbls = [str(b.get("label") or "") for b in sub]
    return {"n": float(n), "mean_rt": mean_rt, "p90": p90, "err_pct": err, "band_labels": lbls}


def _targets_from_summary(summary: Dict[str, Any]) -> Dict[str, float]:
    """Display targets attached by JMeterAnalyzerV2 (availability %, response_time ms, etc.)."""
    t = summary.get("targets")
    if not isinstance(t, dict):
        t = {}
    p95v = float(t.get("p95_percentile") or 3000)
    p90_opt = t.get("p90_percentile")
    if p90_opt is not None and str(p90_opt).strip() != "":
        p90v = float(p90_opt)
    else:
        p90v = min(3000.0, p95v * 0.6)
    return {
        "availability": float(t.get("availability") or 99),
        "response_time_ms": float(t.get("response_time") or 2000),
        "error_rate": float(t.get("error_rate") or 1),
        "throughput": float(t.get("throughput") or 100),
        "p90_percentile_ms": p90v,
        "p95_percentile_ms": p95v,
        "sla_compliance": float(t.get("sla_compliance") or 95),
    }


def _capacity_thresholds_from_targets(tgt: Dict[str, float]) -> Dict[str, Any]:
    """
    Three-tier capacity boundaries: Target Values override Tier-1 (proven-safe) cutoffs where present;
    Tier-2/3 and non-targeted metrics use the product default table (industry-style).
    """
    err_t1 = float(tgt.get("error_rate") or 1.0)
    p95_t1 = float(tgt.get("p95_percentile_ms") or 5000)
    p90_t1 = float(tgt.get("p90_percentile_ms") or min(3000.0, p95_t1 * 0.6))
    return {
        "err_t1": err_t1,
        "err_t2_hi": 5.0,
        "p90_t1": p90_t1,
        "p90_t2_hi": 8000.0,
        "p95_t1": p95_t1,
        "p95_t2_hi": 20000.0,
        "p99_t1": 10000.0,
        "p99_t2_hi": 60000.0,
        "timeout_ms_wall": 180000.0,
        "tps_cv_t1": 0.15,
        "tps_cv_t2_hi": 0.50,
        "apdex_t1": 0.85,
        "apdex_t2_lo": 0.50,
        "ttfb_t1": 500.0,
        "ttfb_t2_hi": 3000.0,
        "n5xx_t2_max": 50,
        "nconn_t2_max": 10,
        "spike_t2_per_hr_max": 1.0,
    }


def _tier_err_pct(err_pct: float, th: Dict[str, Any]) -> int:
    if err_pct < th["err_t1"]:
        return 1
    if err_pct <= th["err_t2_hi"] + 1e-9:
        return 2
    return 3


def _tier_latency_ms(ms: float, t1: float, t2: float, wall: float) -> int:
    if ms < t1:
        return 1
    if ms <= t2:
        return 2
    if ms >= wall - 2000.0:
        return 3
    return 3


def _tier_apdex(score: float, th: Dict[str, Any]) -> int:
    if score + 1e-9 >= th["apdex_t1"]:
        return 1
    if score + 1e-9 >= th["apdex_t2_lo"]:
        return 2
    return 3


def _tier_throughput_shape(
    bs: Dict[str, Any],
    prev_bs: Optional[Dict[str, Any]],
    lo: int,
    hi: int,
    plo: int,
    phi: int,
) -> int:
    """1 = scaling (linear-ish), 2 = plateau, 3 = declining goodput."""
    if prev_bs is None:
        return 1
    pt = float(bs.get("avg_tps") or 0)
    ppt = float(prev_bs.get("avg_tps") or 0)
    if ppt <= 0.05:
        return 1
    if pt < ppt * 0.87:
        return 3
    vu_now = (lo + hi) / 2.0
    vu_prev = (plo + phi) / 2.0
    if vu_now > vu_prev + 1 and pt <= ppt * 1.03:
        return 2
    return 1


def _tps_coefficient_variation(tps_arr: List[float]) -> float:
    arr = [float(x) for x in tps_arr if x is not None and float(x) >= 0]
    if len(arr) < 2:
        return 0.0
    a = np.asarray(arr, dtype=float)
    m = float(np.mean(a))
    if m < 1e-9:
        return 0.0
    return float(np.std(a) / m)


def _rt_spikes_per_hour(MINS: List[str], MEAN_RT: List[float], dur_min: float) -> float:
    if len(MEAN_RT) < 5 or dur_min <= 0:
        return 0.0
    v = np.asarray(MEAN_RT, dtype=float)
    base = float(np.median(v))
    thr = max(base * 1.35, base + 500.0)
    spikes = int(np.sum(v > thr))
    hours = max(dur_min / 60.0, 0.25)
    return spikes / hours


def _tier_tps_cv(cv: float, th: Dict[str, Any]) -> int:
    if cv < th["tps_cv_t1"]:
        return 1
    if cv <= th["tps_cv_t2_hi"] + 1e-9:
        return 2
    return 3


def _tier_5xx_count(n: int, total: int, th: Dict[str, Any]) -> int:
    if n == 0:
        return 1
    er = 100.0 * n / max(total, 1)
    if n <= th["n5xx_t2_max"] and er <= 1.0 + 1e-9:
        return 2
    return 3


def _tier_conn_err(n: int, th: Dict[str, Any]) -> int:
    if n == 0:
        return 1
    if n <= th["nconn_t2_max"]:
        return 2
    return 3


def _tier_spike_rate(per_hr: float, th: Dict[str, Any]) -> int:
    if per_hr <= 0.05:
        return 1
    if per_hr <= th["spike_t2_per_hr_max"] + 1e-9:
        return 2
    return 3


# Marginal / stress deviation vs saved Target Values (mean RT, P95, error %).
_MARGINAL_MEAN_RT_DELTA_MS = 1000.0
_MARGINAL_P95_DELTA_MS = 2000.0
_MARGINAL_ERR_DELTA_PCT = 1.0


def _deviation_capacity_band_tier(bs: Dict[str, Any], tgt: Dict[str, float]) -> int:
    """
    Tier 1 — proven safe: band mean RT, P95, and error % are all within Target Values.
    Tier 2 — marginal: at least one metric is above target, but mean ≤ target+1000 ms,
        P95 ≤ target+2000 ms, error % ≤ target+1 (percentage points).
    Tier 3 — stress / observed peak: any marginal bound exceeded.
    """
    t_m = float(tgt.get("response_time_ms") or 0)
    t_p95 = float(tgt.get("p95_percentile_ms") or 0)
    t_e = float(tgt.get("error_rate") or 0)
    mean = float(bs.get("mean_rt") or 0)
    p95 = float(bs.get("p95") or 0)
    err = float(bs.get("err_pct") or 0)
    if mean <= t_m + 1e-9 and p95 <= t_p95 + 1e-9 and err <= t_e + 1e-9:
        return 1
    if (
        mean > t_m + _MARGINAL_MEAN_RT_DELTA_MS + 1e-9
        or p95 > t_p95 + _MARGINAL_P95_DELTA_MS + 1e-9
        or err > t_e + _MARGINAL_ERR_DELTA_PCT + 1e-9
    ):
        return 3
    return 2


def _band_capacity_tier(
    bs: Dict[str, Any],
    prev_bs: Optional[Dict[str, Any]],
    lo: int,
    hi: int,
    plo: int,
    phi: int,
    lat_row: Optional[Dict[str, Any]],
    apdex_band: float,
    th: Dict[str, Any],
) -> int:
    tiers_l: List[int] = [
        _tier_err_pct(float(bs.get("err_pct") or 0), th),
        _tier_latency_ms(float(bs.get("p90") or 0), th["p90_t1"], th["p90_t2_hi"], th["timeout_ms_wall"]),
        _tier_latency_ms(float(bs.get("p95") or 0), th["p95_t1"], th["p95_t2_hi"], th["timeout_ms_wall"]),
        _tier_latency_ms(float(bs.get("p99") or 0), th["p99_t1"], th["p99_t2_hi"], th["timeout_ms_wall"]),
        _tier_apdex(float(apdex_band), th),
        _tier_throughput_shape(bs, prev_bs, lo, hi, plo, phi),
    ]
    if lat_row:
        tiers_l.append(
            _tier_latency_ms(
                float(lat_row.get("ttfb_p90") or 0),
                th["ttfb_t1"],
                th["ttfb_t2_hi"],
                th["timeout_ms_wall"],
            )
        )
    return int(max(tiers_l))


def _capacity_envelope_vu(
    band_stats: List[Dict[str, Any]],
    max_vu: int,
    load_bands: List[Tuple[str, int, int]],
    tgt: Dict[str, float],
    *,
    err_rate_pct: float,
    lat_rows: List[Dict[str, Any]],
    apdex_by_band: List[float],
    TPS_ARR: List[float],
    MINS: List[str],
    MEAN_RT: List[float],
    dur_min: float,
    total: int,
    n5xx: int,
    no_http: int,
) -> Tuple[Optional[int], Optional[int], Optional[int], str, str, str, bool]:
    """
    VU envelope from load bands vs Target Values (mean RT, P95, error % per band).

    - Proven safe: all three within targets → contiguous light-load prefix; range 0–upper VU.
    - Marginal: above targets but mean ≤ target+1000 ms, P95 ≤ target+2000 ms, error ≤ target+1 pp.
    - Stress / peak: beyond those marginal caps (or whole-run context only in narrative).

    Unused parameters are kept for a stable call signature from the combined report builder.
    """
    _ = (
        err_rate_pct,
        lat_rows,
        apdex_by_band,
        TPS_ARR,
        MINS,
        MEAN_RT,
        dur_min,
        total,
        n5xx,
        no_http,
    )
    if max_vu <= 0:
        return None, None, None, "No concurrent-user data in samples.", "—", "—", False

    populated: List[Tuple[str, int, int, Dict[str, Any]]] = []
    for label, lo, hi in load_bands:
        bs = next((b for b in band_stats if b.get("label") == label), None)
        if not bs or not bs.get("n"):
            continue
        populated.append((label, int(lo), int(hi), bs))

    if not populated:
        return None, None, None, (
            f"No populated load bands — cannot estimate envelope (tested peak {max_vu} VU)."
        ), "—", "—", False

    tiers = [_deviation_capacity_band_tier(bs, tgt) for _, _, _, bs in populated]
    has_stress = any(t == 3 for t in tiers)

    j = 0
    while j < len(tiers) and tiers[j] == 1:
        j += 1
    safe_hi: Optional[int] = min(int(populated[j - 1][2]), int(max_vu)) if j > 0 else None

    marginal_lo: Optional[int] = None
    marginal_hi: Optional[int] = None
    k = j
    while k < len(tiers) and tiers[k] == 2:
        k += 1
    if k > j:
        marginal_lo = int(populated[j][1])
        marginal_hi = min(int(populated[k - 1][2]), int(max_vu))
        if safe_hi is not None:
            marginal_lo = max(marginal_lo, int(safe_hi) + 1)
        if marginal_lo > marginal_hi:
            marginal_lo, marginal_hi = None, None

    t_m = float(tgt.get("response_time_ms") or 0)
    t_p95 = float(tgt.get("p95_percentile_ms") or 0)
    t_e = float(tgt.get("error_rate") or 0)

    if safe_hi is not None:
        safe_detail = (
            f"Per load band, mean RT ≤{t_m:.0f} ms, P95 ≤{t_p95:.0f} ms, and error % ≤{t_e:.2f}% "
            f"(Target Values) through the last fully compliant band (high end ≈{safe_hi} VU). "
            f"Shown as 0–{safe_hi} VUsers — numeric bounds come from this JMeter analysis, not fixed defaults."
        )
    else:
        safe_detail = (
            "No load band kept mean RT, P95, and error % simultaneously within Target Values; "
            "a proven-safe VU ceiling cannot be stated from this run."
        )

    if marginal_lo is not None and marginal_hi is not None and marginal_lo <= marginal_hi:
        marginal_detail = (
            f"From {marginal_lo} VU upward after the safe ceiling: at least one metric is above target, "
            f"but mean remains ≤ target+{_MARGINAL_MEAN_RT_DELTA_MS:.0f} ms, P95 ≤ target+{_MARGINAL_P95_DELTA_MS:.0f} ms, "
            f"and error % ≤ target+{_MARGINAL_ERR_DELTA_PCT:.0f} percentage points, through ≈{marginal_hi} VU."
        )
    elif has_stress and j > 0 and k == j:
        marginal_detail = (
            "Load moved from proven safe directly into stress in band order — no distinct marginal slice "
            "(still use marginal rules: small excess over targets vs large excess as defined above)."
        )
    elif marginal_lo is None and not has_stress:
        marginal_detail = (
            "No marginal slice in band progression — populated bands stayed within Target Values end-to-end "
            f"(tested maximum {max_vu} VU)."
        )
    else:
        marginal_detail = (
            f"Marginal tier uses deviation caps: +{_MARGINAL_MEAN_RT_DELTA_MS:.0f} ms mean, "
            f"+{_MARGINAL_P95_DELTA_MS:.0f} ms P95, +{_MARGINAL_ERR_DELTA_PCT:.0f}% error vs targets."
        )

    if has_stress:
        if marginal_hi is not None:
            peak_detail = (
                f"Stress / observed peak: beyond marginal deviation caps vs targets, from above ≈{marginal_hi} VU "
                f"(summarised as {marginal_hi}+ VUsers). Maximum concurrency in this JTL: {max_vu} VU."
            )
        elif safe_hi is not None:
            peak_detail = (
                f"Stress tier appears without a resolved marginal band; above ≈{safe_hi} VU violates marginal ceilings. "
                f"Maximum concurrent users in JTL: {max_vu} VU."
            )
        else:
            first_stress_lo = int(populated[next(i for i, t in enumerate(tiers) if t == 3)][1])
            peak_detail = (
                f"Stress / peak from ≈{first_stress_lo} VU (first band exceeding marginal deviation caps). "
                f"Maximum concurrent users in JTL: {max_vu} VU."
            )
    else:
        peak_detail = (
            f"No band exceeded marginal deviation ceilings; highest exercised concurrency is {max_vu} VU "
            f"(observed peak for this dataset)."
        )

    return safe_hi, marginal_lo, marginal_hi, safe_detail, marginal_detail, peak_detail, has_stress


def _release_decision_three_pillars(
    *,
    err_rate_pct: float,
    errs: int,
    total: int,
    sla_pct: float,
    n_tx_pass: int,
    n_tx_test: int,
    success_rate: float,
    mean_rt_ms: float,
    p95_ms: float,
    throughput: float,
    band_stats: List[Dict[str, Any]],
    t: Dict[str, float],
) -> Tuple[str, str, str]:
    """
    Release decision from three behaviours vs saved targets (Target Values modal), using the
    same business-facing labels as JMeterAnalyzerV2._get_business_impact / release_decision.
    Pillars: responsive (latency + peak-slice SLA), throughput (sustained TPS + shape), errors.
    """
    t_err = float(t["error_rate"])
    t_sla = float(t["sla_compliance"])
    t_avail = float(t["availability"])
    t_rt = float(t["response_time_ms"])
    t_p95 = float(t["p95_percentile_ms"])
    t_tp = float(t["throughput"])
    populated = [b for b in band_stats if b.get("n")]

    r_lines: List[str] = []
    responsive_crit = False
    responsive_warn = False
    mean_bad = mean_rt_ms > t_rt + 1e-12
    mean_warn_only = (not mean_bad) and (mean_rt_ms > t_rt * 0.90 + 1e-12)
    p95_bad = p95_ms > t_p95 + 1e-12
    p95_warn_only = (not p95_bad) and (p95_ms > t_p95 * 0.85 + 1e-12)

    if mean_bad:
        responsive_crit = True
        r_lines.append(f"Mean RT {mean_rt_ms:.0f} ms exceeds target ≤{t_rt:.0f} ms.")
    elif mean_warn_only:
        responsive_warn = True
        r_lines.append(f"Mean RT {mean_rt_ms:.0f} ms within ~10% of limit {t_rt:.0f} ms.")
    if p95_bad:
        responsive_crit = True
        r_lines.append(f"P95 {p95_ms:.0f} ms exceeds target ≤{t_p95:.0f} ms.")
    elif p95_warn_only:
        responsive_warn = True
        r_lines.append(f"P95 {p95_ms:.0f} ms approaching tail limit {t_p95:.0f} ms.")

    if n_tx_test > 0:
        if sla_pct + 1e-12 < t_sla:
            responsive_crit = True
            r_lines.append(
                f"Peak-slice transaction P90 SLA pass {sla_pct:.1f}% is below target ≥{t_sla:.1f}% "
                f"({n_tx_pass}/{n_tx_test} controllers)."
            )
        elif sla_pct < t_sla + 5.0:
            responsive_warn = True
            r_lines.append(
                f"SLA pass {sla_pct:.1f}% is within 5 pp of floor {t_sla:.1f}% ({n_tx_pass}/{n_tx_test} controllers)."
            )
    if not r_lines and not responsive_crit and not responsive_warn:
        if n_tx_test > 0:
            r_lines.append(
                f"Mean RT {mean_rt_ms:.0f} ms ≤ {t_rt:.0f} ms; P95 {p95_ms:.0f} ms ≤ {t_p95:.0f} ms; "
                f"SLA pass {sla_pct:.1f}% ≥ {t_sla:.1f}%."
            )
        else:
            r_lines.append(
                f"Mean RT {mean_rt_ms:.0f} ms ≤ {t_rt:.0f} ms; P95 {p95_ms:.0f} ms ≤ {t_p95:.0f} ms; "
                "peak-slice SLA pass n/a (no transaction controllers in peak window)."
            )
    elif n_tx_test == 0 and r_lines:
        r_lines.append("Peak-slice SLA pass n/a (no transaction controllers in peak window).")

    tp_lines: List[str] = []
    throughput_crit = False
    throughput_warn = False
    t_first = float(populated[0].get("avg_tps") or 0) if populated else 0.0
    t_last = float(populated[-1].get("avg_tps") or 0) if populated else 0.0
    lbl0 = str(populated[0].get("label") or "first band") if populated else ""
    lbl1 = str(populated[-1].get("label") or "last band") if populated else ""

    if throughput + 1e-12 < t_tp:
        throughput_crit = True
        tp_lines.append(
            f"Mean throughput {throughput:.1f} req/s is below target ≥{t_tp:.0f} req/s."
        )
    elif throughput >= t_tp * 0.90 + 1e-12:
        throughput_warn = True
        tp_lines.append(
            f"Mean throughput {throughput:.1f} req/s is within ~10% under target {t_tp:.0f} req/s."
        )

    if len(populated) >= 2 and t_first > 1e-9:
        ratio = t_last / t_first
        if ratio < 0.85:
            throughput_crit = True
            tp_lines.append(
                f"Throughput shape: avg TPS falls ~{(1.0 - ratio) * 100:.0f}% from {lbl0} to {lbl1} — "
                "capacity likely saturating or errors slowing success path."
            )
        elif ratio < 0.95:
            if not throughput_crit:
                throughput_warn = True
            tp_lines.append(
                f"Throughput shape: ~{(1.0 - ratio) * 100:.0f}% lower avg TPS at {lbl1} vs {lbl0} (watch scaling)."
            )
        elif not tp_lines:
            tp_lines.append(
                f"Mean {throughput:.1f} req/s vs target ≥{t_tp:.0f} req/s; band TPS {lbl0} → {lbl1} is non-decreasing."
            )
    elif not tp_lines:
        tp_lines.append(
            f"Mean {throughput:.1f} req/s vs target ≥{t_tp:.0f} req/s"
            + (f" ({populated[0].get('label')}-only data)." if len(populated) == 1 else ".")
        )

    e_lines: List[str] = []
    error_crit = False
    error_warn = False
    if err_rate_pct > t_err + 1e-12:
        error_crit = True
        e_lines.append(
            f"Sample error rate {err_rate_pct:.2f}% exceeds target ≤{t_err:.2f}% "
            f"({errs:,} / {total:,} samples)."
        )
    elif err_rate_pct > t_err * 0.85 + 1e-12:
        error_warn = True
        e_lines.append(
            f"Error rate {err_rate_pct:.2f}% is within ~15% of ceiling {t_err:.2f}%."
        )
    if success_rate + 1e-12 < t_avail:
        error_crit = True
        e_lines.append(
            f"Sample success {success_rate:.2f}% is below availability target {t_avail:.2f}% "
            f"({max(0.0, t_avail - success_rate):.2f} pp gap)."
        )
    if not e_lines:
        e_lines.append(
            f"Errors {err_rate_pct:.2f}% ≤ {t_err:.2f}%; success {success_rate:.2f}% ≥ {t_avail:.2f}%."
        )

    n_crit = sum([responsive_crit, throughput_crit, error_crit])
    n_warn = sum(
        [
            bool(not responsive_crit and responsive_warn),
            bool(not throughput_crit and throughput_warn),
            bool(not error_crit and error_warn),
        ]
    )

    if n_crit >= 3:
        label = "⛔ PRODUCTION BLOCKER"
        css = "red"
    elif n_crit >= 2:
        label = "🔴 Release Blocked - Critical Issues"
        css = "red"
    elif n_crit == 1:
        if responsive_crit or error_crit:
            label = "🔴 Release Not Recommended"
        else:
            label = "🟠 Release Only with Business Sign-Off"
        css = "red"
    elif n_warn >= 2:
        label = "🟡 Conditional Release (Business Approval Required)"
        css = "amber"
    elif n_warn >= 1:
        label = "🟢 Release with Monitoring"
        css = "amber"
    else:
        label = "🟢 Immediate Release Approved"
        css = "green"

    detail = (
        "Decision uses saved targets vs responsive behaviour, throughput behaviour, and error behaviour.\n"
        f"Responsive behaviour: {'FAIL' if responsive_crit else 'WARN' if responsive_warn else 'OK'} — "
        + " ".join(r_lines)
        + "\n"
        f"Throughput behaviour: {'FAIL' if throughput_crit else 'WARN' if throughput_warn else 'OK'} — "
        + " ".join(tp_lines)
        + "\n"
        f"Error behaviour: {'FAIL' if error_crit else 'WARN' if error_warn else 'OK'} — "
        + " ".join(e_lines)
    )

    return label, css, detail


def _release_decision_from_grading(pg: Dict[str, Any]) -> Tuple[str, str, str]:
    """
    Release pill from weighted performance grade — same ``release_decision`` strings as
    ``JMeterAnalyzerV2._get_business_impact`` (scorecard / grading model).
    """
    grade = str(pg.get("overall_grade") or "C+").strip().upper().replace(" ", "")
    try:
        score = float(pg.get("overall_score") or 0)
    except (TypeError, ValueError):
        score = 0.0
    title = str(pg.get("title") or "").strip()
    sub = str(pg.get("subtitle") or "").strip()
    if grade in ("N/A", "—", "", "NA"):
        grade = "C+"
    if grade == "F":
        label, css = "⛔ PRODUCTION BLOCKER", "red"
    elif grade == "D":
        label, css = "⛔ Release Blocked (Go-Live Stopper)", "red"
    elif grade == "C":
        label, css = "🔴 Release Blocked - Critical Issues", "red"
    elif grade == "C+":
        label, css = "🔴 Release Not Recommended", "red"
    elif grade == "B":
        label, css = "🟠 Release Only with Business Sign-Off", "red"
    elif grade == "B+":
        label, css = "🟡 Conditional Release (Business Approval Required)", "amber"
    elif grade == "A":
        label, css = "🟢 Release with Monitoring", "amber"
    elif grade == "A+":
        label, css = "🟢 Immediate Release Approved", "green"
    else:
        label, css = "🟡 Conditional Release (Business Approval Required)", "amber"
    detail = format_performance_grade_release_line(grade, score, title, sub)
    return label, css, detail


def _band_lo_hi(label: str, load_bands: Optional[List[Tuple[str, int, int]]] = None) -> Tuple[Optional[int], Optional[int]]:
    if load_bands:
        for lbl, lo, hi in load_bands:
            if lbl == label:
                return lo, hi
    m = re.match(r"^(\d+)\s*[–\-]\s*(\d+)\s+VU\s*$", str(label).strip())
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.match(r"^(\d+)\s+VU\s*$", str(label).strip())
    if m2:
        v = int(m2.group(1))
        return v, v
    for lbl, lo, hi in LOAD_BANDS:
        if lbl == label:
            return lo, hi
    return None, None


def _degradation_onset_vu(
    band_stats: List[Dict[str, Any]],
    p90_gate_ms: float,
    err_gate_pct: float,
    load_bands: Optional[List[Tuple[str, int, int]]] = None,
) -> Optional[Tuple[int, str, str]]:
    """
    First load band (after the first populated band) where latency or errors jump materially
    vs baseline low-load band or breach saved gates.
    Returns (lower VU bound of onset band, band label, severity word).
    """
    populated = [b for b in band_stats if b.get("n")]
    if len(populated) < 2:
        return None
    base = populated[0]
    b_p90 = float(base.get("p90") or 0)
    b_err = float(base.get("err_pct") or 0)
    for b in populated[1:]:
        p90 = float(b.get("p90") or 0)
        er = float(b.get("err_pct") or 0)
        lbl = str(b.get("label") or "")
        breach_gate = p90 >= p90_gate_ms or er >= err_gate_pct
        rel_p90 = b_p90 > 400 and p90 > b_p90 * 1.35
        rel_err = er >= max(5.0, b_err * 2.0 + 2.0) or (b_err < 2.0 and er >= max(4.0, b_err + 8.0))
        if breach_gate or rel_p90 or rel_err:
            lo, _ = _band_lo_hi(lbl, load_bands)
            if lo is None:
                continue
            sev = "severe" if breach_gate or er >= 10 or p90 >= p90_gate_ms * 1.1 else "meaningful"
            return lo, lbl, sev
    return None


def _pretty_tx_name(name: str, max_len: int = 52) -> str:
    s = (name or "").strip()
    if len(s) > max_len:
        return s[: max_len - 1] + "…"
    return s or "—"


def _transaction_peak_profiles(
    data: List[Dict[str, Any]],
    tx_stats: Dict[str, Any],
    max_vu: int,
    peak_frac: float = 0.85,
) -> List[Tuple[str, float, float]]:
    """Top transactions by error rate at peak load, with P90 elapsed (ms) on all samples in window."""
    if max_vu <= 0:
        thr = 0
    else:
        thr = max(1, int(max_vu * peak_frac))
    by_label: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in data:
        if not is_jmeter_transaction_controller_by_url(d.get("url")):
            continue
        lab = d.get("label")
        if not lab or lab not in tx_stats:
            continue
        if _vu(d) < thr:
            continue
        by_label[str(lab)].append(d)
    prof: List[Tuple[str, float, float]] = []
    for lab, rows in by_label.items():
        if len(rows) < 3:
            continue
        nf = sum(1 for d in rows if is_jmeter_error_outcome(d))
        er = 100.0 * nf / len(rows)
        elapsed_all = [_elapsed_ms(d) for d in rows]
        p90 = float(np.percentile(np.array(elapsed_all, dtype=float), 90)) if elapsed_all else 0.0
        prof.append((lab, er, p90))
    prof.sort(key=lambda x: (-x[1], -x[2]))
    return prof[:8]


def _finding_severity_score(
    *,
    sla_pct: float,
    n_tx_pass: int,
    n_tx_test: int,
    err_rate_pct: float,
    tgt_err: float,
    tgt_sla: float,
    max_vu: int,
    onset: Optional[Tuple[int, str, str]],
    crit_er_max: float,
    n504: int,
    n404: int,
    total: int,
) -> int:
    """0 = benign … 5 = extreme; used to derive a finding-based release posture."""
    sev = 0
    ratio_pass = (n_tx_pass / max(n_tx_test, 1)) if n_tx_test else 1.0
    if n_tx_test and (sla_pct < 45 or ratio_pass < 0.45):
        sev = max(sev, 4)
    elif sla_pct < 70 or ratio_pass < 0.70:
        sev = max(sev, 3)
    elif sla_pct + 1e-12 < tgt_sla:
        sev = max(sev, 2)
    if err_rate_pct > 10:
        sev = max(sev, 4)
    elif err_rate_pct > 5:
        sev = max(sev, 3)
    elif err_rate_pct > max(tgt_err * 2, 2.0):
        sev = max(sev, 2)
    elif err_rate_pct > tgt_err + 1e-12:
        sev = max(sev, 1)
    if onset and max_vu >= (onset[0] + 1):
        if sla_pct < 85 or err_rate_pct > 1.5 or crit_er_max > 8:
            sev = max(sev, 2)
        if crit_er_max > 15 or err_rate_pct > 4:
            sev = max(sev, 3)
    if crit_er_max > 60:
        sev = max(sev, 5)
    elif crit_er_max > 35:
        sev = max(sev, 4)
    elif crit_er_max > 15:
        sev = max(sev, 3)
    elif crit_er_max > 8:
        sev = max(sev, 2)
    tmax = max(total, 1)
    if n504 > max(200, int(tmax * 0.02)):
        sev = max(sev, 4)
    elif n504 > max(40, int(tmax * 0.005)):
        sev = max(sev, 3)
    elif n504 > 10 and err_rate_pct > 1.0:
        sev = max(sev, 2)
    if n404 > int(tmax * 0.12) and err_rate_pct > 2.0:
        sev = max(sev, 2)
    return min(sev, 5)


def _derive_key_findings_for_release(
    *,
    data: List[Dict[str, Any]],
    band_stats: List[Dict[str, Any]],
    tx_stats: Dict[str, Any],
    max_vu: int,
    sla_peak: Dict[str, Any],
    tgt: Dict[str, float],
    err_rate_pct: float,
    errs: int,
    total: int,
    rcounter: Counter,
    p90_gate_ms: float,
    err_gate_pct: float,
    load_bands: Optional[List[Tuple[str, int, int]]] = None,
) -> Tuple[List[str], int]:
    """
    Narrative key findings (evidence-led) and a severity score for release posture.
    Mirrors the style of deep assessment / executive reports.
    """
    sla_pct = float(sla_peak.get("pass_rate_pct") or 0)
    n_tx_pass = int(sla_peak.get("transactions_pass") or 0)
    n_tx_test = int(sla_peak.get("transactions_tested") or 0)
    sla_ms = float(sla_peak.get("sla_p90_ms") or tgt.get("p95_percentile_ms") or 3000)
    peak_thr = int(sla_peak.get("peak_vu_threshold") or 0) or max(1, int(max_vu * 0.85))

    n504 = sum(c for k, c in rcounter.items() if str(k) == "504")
    n404 = sum(c for k, c in rcounter.items() if str(k).startswith("404"))

    onset = _degradation_onset_vu(band_stats, p90_gate_ms, err_gate_pct, load_bands)
    peak_prof = _transaction_peak_profiles(data, tx_stats, max_vu, 0.85)
    crit_er_vals = [p[1] for p in peak_prof[:5]]
    crit_er_max = max(crit_er_vals) if crit_er_vals else 0.0
    crit_er_min = min(crit_er_vals) if crit_er_vals else 0.0
    p90_max_ms = max((p[2] for p in peak_prof[:5]), default=0.0)

    sev = _finding_severity_score(
        sla_pct=sla_pct,
        n_tx_pass=n_tx_pass,
        n_tx_test=n_tx_test,
        err_rate_pct=err_rate_pct,
        tgt_err=float(tgt["error_rate"]),
        tgt_sla=float(tgt["sla_compliance"]),
        max_vu=max_vu,
        onset=onset,
        crit_er_max=crit_er_max,
        n504=n504,
        n404=n404,
        total=total,
    )

    findings: List[str] = []

    if onset:
        lo, lbl, sev_w = onset
        findings.append(
            f"The system demonstrates {sev_w} performance degradation above ~{lo} concurrent users "
            f"(observed in the {lbl} band: higher P90 RT and/or error share vs lower-load bands, or breach of saved gates)."
        )
    elif max_vu >= 60:
        findings.append(
            "Throughput and latency change with load; compare lower vs upper load bands in this report for non-linear behaviour."
        )

    top_names: List[str] = []
    if peak_prof:
        pick = peak_prof[:5]
        top_names = [_pretty_tx_name(x[0]) for x in pick[:4] if x[1] >= 1.5 or x[2] >= 8000]
        if not top_names:
            top_names = [_pretty_tx_name(x[0]) for x in pick]
        tx_paragraph = top_names and (
            crit_er_max >= 4 or p90_max_ms >= 15_000 or len(top_names) >= 2 or p90_max_ms >= 8000
        )
        if tx_paragraph:
            p90_s = max(p[2] for p in pick)
            if p90_s >= 120_000:
                rt_clause = (
                    f"response times exceeding {p90_s / 60000:.1f} minutes at the P90 level for the heaviest cases"
                )
            elif p90_s >= 60_000:
                rt_clause = "response times exceeding about a minute at P90 for the heaviest cases"
            elif p90_s >= 10_000:
                rt_clause = f"P90 response times reaching {p90_s / 1000:.0f}s under sustained peak load"
            else:
                rt_clause = "elevated P90 response times under sustained peak load"
            http_txt = ""
            if n504 > 10 and n404 > max(20, total // 100):
                http_txt = ", with HTTP 504 Gateway Timeouts and elevated 404 responses under load"
            elif n504 > 10:
                http_txt = ", with HTTP 504 Gateway Timeouts under load"
            elif n404 > max(20, total // 100):
                http_txt = ", with elevated 404 responses under load"
            findings.append(
                f"Critical transactions ({', '.join(top_names)}) exhibit sample error rates from "
                f"{crit_er_min:.0f}% to {crit_er_max:.0f}% in the high-concurrency window, {rt_clause}"
                f"{http_txt}."
            )
        elif peak_prof[0][1] >= 0.5:
            findings.append(
                f"Under peak load, transactions such as {_pretty_tx_name(peak_prof[0][0])} reach "
                f"~{peak_prof[0][1]:.1f}% errors — expand the scorecard for full controller-level detail."
            )

    if (n504 > max(15, total // 300) or n404 > max(50, total // 80)) and not any(
        "504" in f or "404" in f for f in findings
    ):
        findings.append(
            "HTTP 504 (gateway / upstream) and 404 (routing or resource) outcomes are material in this run — "
            "review gateway capacity, timeouts, and URL stability alongside application code."
        )

    if n_tx_test > 0:
        findings.append(
            f"Only {n_tx_pass} of {n_tx_test} tested transactions ({sla_pct:.0f}%) pass the P90 <{sla_ms / 1000:.0f}s SLA "
            f"in the peak-load slice (≈{peak_thr}+ concurrent users)."
        )

    if sev >= 4:
        findings.append(
            "The application requires significant architectural remediation before any production rollout."
        )
    elif sev >= 3:
        findings.append(
            "Stabilize error budgets, tail latency, and capacity at peak before a wide production rollout; expect stakeholder sign-off."
        )
    elif sev >= 2:
        findings.append(
            "Plan for a gated or phased rollout with strong monitoring and rollback, given residual risk in the findings above."
        )
    else:
        findings.append(
            "No blocking pattern surfaced in the automated finding scan; still validate business-critical journeys manually."
        )

    return findings, sev


def _top_error_minutes(minute_map: Dict[str, List[Dict[str, Any]]], top_n: int = 6) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for key, rowsamples in minute_map.items():
        if not rowsamples:
            continue
        fails = sum(1 for r in rowsamples if is_jmeter_error_outcome(r))
        if fails == 0:
            continue
        er = 100.0 * fails / len(rowsamples) if rowsamples else 0.0
        vus = int(round(float(np.mean([_vu(r) for r in rowsamples])))) if rowsamples else 0
        mean_rt = float(np.mean([_elapsed_ms(r) for r in rowsamples])) if rowsamples else 0.0
        n504 = sum(1 for r in rowsamples if str(r.get("response_code") or "") == "504")
        n404 = sum(1 for r in rowsamples if str(r.get("response_code") or "").startswith("4"))
        if fails and n504 / fails > 0.35:
            dom = "504 surge"
        elif fails and n404 / fails > 0.35:
            dom = "404 dominant"
        else:
            dom = "504 + 404" if n504 and n404 else "mixed"
        rows.append(
            {
                "time": key,
                "vu": vus,
                "errors": fails,
                "samples": len(rowsamples),
                "err_pct": round(er, 1),
                "mean_rt": int(mean_rt),
                "dominant": dom,
            }
        )
    rows.sort(key=lambda x: (-x["err_pct"], -x["errors"]))
    return rows[:top_n]


def _iter_band_rows(
    band_stats: List[Dict[str, Any]],
    load_bands: List[Tuple[str, int, int]],
) -> List[Tuple[str, int, int, Dict[str, Any]]]:
    out: List[Tuple[str, int, int, Dict[str, Any]]] = []
    for label, lo, hi in load_bands:
        bs = next((b for b in band_stats if b.get("label") == label), None)
        if bs and bs.get("n"):
            out.append((label, int(lo), int(hi), bs))
    return out


def _evidence_err_pct_chain(rows: List[Tuple[str, int, int, Dict[str, Any]]]) -> str:
    if not rows:
        return ""
    parts = [f"{float(bs['err_pct']):.1f}% sample errors at {lbl}" for lbl, _lo, _hi, bs in rows]
    return " → ".join(parts)


def _evidence_404_chain(
    data: List[Dict[str, Any]],
    load_bands: List[Tuple[str, int, int]],
) -> str:
    parts: List[str] = []
    for label, lo, hi in load_bands:
        band = [d for d in data if lo <= _vu(d) <= hi]
        if not band:
            continue
        n4 = sum(1 for d in band if str(d.get("response_code") or "").startswith("4"))
        if n4 == 0:
            continue
        pct = 100.0 * n4 / len(band)
        parts.append(f"{pct:.1f}% HTTP 4xx-class responses at {label}")
    return " → ".join(parts) if parts else ""


def _evidence_504_chain(data: List[Dict[str, Any]], load_bands: List[Tuple[str, int, int]]) -> str:
    parts: List[str] = []
    for label, lo, hi in load_bands:
        band = [d for d in data if lo <= _vu(d) <= hi]
        if not band:
            continue
        n504 = sum(1 for d in band if str(d.get("response_code") or "") == "504")
        if n504 == 0:
            continue
        parts.append(f"{n504}× HTTP 504 at {label} ({100.0 * n504 / len(band):.2f}% of samples in band)")
    return " → ".join(parts) if parts else ""


def _worst_transactions_for_rca(tx_stats: Dict[str, Any], limit: int = 4) -> List[Tuple[str, float, float, int]]:
    acc: List[Tuple[str, float, float, int]] = []
    for lab, st in tx_stats.items():
        cnt = int(st.get("count") or 0)
        if cnt < 5:
            continue
        xp = float(st.get("error_rate") or 0)
        if xp < 3.0:
            continue
        p95 = float(st.get("p95") or 0)
        acc.append((str(lab), xp, p95, cnt))
    acc.sort(key=lambda x: -x[1])
    return acc[:limit]


def _rca_url_path(d: Dict[str, Any]) -> str:
    u = str(d.get("url") or "").strip()
    if not u:
        return str(d.get("label") or "").strip() or "—"
    try:
        p = urlparse(u)
        path = (p.path or "").strip() or u[:140]
        if len(path) > 160:
            path = path[:157] + "…"
        return path or u[:120]
    except Exception:
        return u[:120]


def _best_404_path_profile(
    data: List[Dict[str, Any]],
    load_bands: List[Tuple[str, int, int]],
) -> Optional[Tuple[str, List[Tuple[str, float, int, int]]]]:
    """Return (path, [(band_label, pct_4xx_among_path_hits_in_band, n_4xx, n_path_samples_in_band), ...])."""
    path_band_n: Dict[str, Dict[Tuple[str, int, int], int]] = defaultdict(lambda: defaultdict(int))
    path_band_4: Dict[str, Dict[Tuple[str, int, int], int]] = defaultdict(lambda: defaultdict(int))
    for label, lo, hi in load_bands:
        key = (label, lo, hi)
        for d in data:
            if not (lo <= _vu(d) <= hi):
                continue
            path = _rca_url_path(d)
            path_band_n[path][key] += 1
            rc = str(d.get("response_code") or "")
            if rc.startswith("4"):
                path_band_4[path][key] += 1
    best_path: Optional[str] = None
    best_w = 0
    for path, bands in path_band_n.items():
        w = sum(path_band_4[path].get(k, 0) for k in bands.keys())
        if w > best_w:
            best_w = w
            best_path = path
    if not best_path or best_w < 8:
        return None
    profile: List[Tuple[str, float, int, int]] = []
    for label, lo, hi in load_bands:
        key = (label, lo, hi)
        n = path_band_n[best_path].get(key, 0)
        if n <= 0:
            continue
        n4 = path_band_4[best_path].get(key, 0)
        profile.append((label, 100.0 * n4 / n, n4, n))
    if len(profile) < 2:
        return None
    return best_path, profile


def _detailed_hypothesis_404_cluster(
    *,
    path_profile: Optional[Tuple[str, List[Tuple[str, float, int, int]]]],
    worst_tx: List[Tuple[str, float, float, int]],
    monotonic_err: bool,
    n404: int,
    total: int,
    errs: int,
    chain_404: str,
) -> str:
    tx_tail = ""
    if worst_tx:
        lab, er, _p95, cnt = worst_tx[0]
        if er >= 45:
            tx_tail = (
                f"{lab}'s {er:.1f}% sample error rate (near-total failure on that controller at the concurrency levels exercised) "
                f"suggests a query-string or navigation token that is effectively always wrong or null once threads interleave — "
                f"consistent with lost or overwritten correlation state rather than an occasional bad record id."
            )
        elif er >= 15:
            tx_tail = (
                f"The controller `{lab}` shows a material {er:.1f}% error rate across {cnt:,} samples — worth correlating with "
                f"whether those failures are predominantly HTTP 404 on the same path family as above."
            )

    if path_profile:
        path, prof = path_profile
        first, last = prof[0], prof[-1]
        seq = ", ".join(f"{pct:.1f}% 4xx (of requests touching this path) at {lbl}" for lbl, pct, _n4, _ns in prof)
        para1 = (
            f"The HTTP 404 / 4xx behaviour on `{path}` is not flat across load — it trends from about {first[1]:.1f}% at {first[0]} "
            f"to about {last[1]:.1f}% at {last[0]} among samples that exercise that path. "
            f"A purely static misconfiguration (one bad route table entry) usually yields a nearly constant failure rate "
            f"regardless of how many users are on the system. Here, the rate moves with concurrency, which is the textbook "
            f"signature of cross-talk between threads: a correlation variable (query key, opener token, chart render id, etc.) "
            f"stored in a session-scoped bean, static map, or framework-level shared cache is being overwritten while another "
            f"request still believes it owns that value."
        )
        para2 = (
            f"When User A's code path reads that variable it may briefly see User B's payload — producing a URL that points at "
            f"the wrong record or a missing composite key, so the server correctly returns 404. "
            f"The band-by-band progression is: {seq}. "
        )
        if not tx_tail:
            para2 += (
                "Cross-check the worst transaction controllers in this report; very high error rates on a single label under "
                "moderate load often mark the navigation step that consumes the fragile state."
            )
        else:
            para2 += tx_tail
        para3 = (
            "\n\nRemediate by proving thread safety (or request scoping) for every field that feeds dynamic URL segments, "
            "by removing static caches for per-request identifiers, and by validating with access logs that 404s line up with "
            "interleaved requests rather than a single bad deployment artifact."
        )
        return para1 + "\n\n" + para2 + para3

    para = (
        f"4xx volume in this run reaches {n404:,} samples (~{100.0 * n404 / max(total, 1):.2f}% of the JTL). "
        f"A load-correlated 4xx ramp is still visible at the aggregate level"
    )
    if chain_404:
        para += f" ({chain_404})."
    else:
        para += "."
    para += (
        " Treat this as a concurrency-sensitive routing or session state problem until logs show a single frozen bad URL. "
        "Inspect thread safety on URL builders, spring scopes, and any map keyed without tenant + user + request isolation."
    )
    if tx_tail:
        para += f"\n\n{tx_tail}"
    if monotonic_err:
        para += (
            "\n\nErrors also rise monotonically across successive VU bands — that pattern pairs well with pool or identity "
            "exhaustion, but when the dominant HTTP outcome is 4xx, root cause still skews client-visible routing over pure CPU."
        )
    return para


def _detailed_hypothesis_504_cluster(
    *,
    n504: int,
    n5xx: int,
    no_http: int,
    chain_504: str,
    chain_err: str,
    worst_tx: List[Tuple[str, float, float, int]],
    max_vu: int,
) -> str:
    wall_tx = [(lab, er, p95, cnt) for lab, er, p95, cnt in worst_tx if p95 >= 120_000]
    wall_line = ""
    if wall_tx:
        lab, er, p95, cnt = wall_tx[0]
        wall_line = (
            f"`{lab}` stacks at P95 ≈ {p95:,.0f} ms with {er:.1f}% errors over {cnt:,} samples — percentiles glued to a timeout "
            f"rail strongly implicate synchronous blocking behind a fixed upstream or servlet limit."
        )
    elif worst_tx:
        lab, er, p95, cnt = worst_tx[0]
        wall_line = f"Heaviest tail: `{lab}` at P95 {p95:,.0f} ms, {er:.1f}% errors ({cnt:,} samples)."

    para1 = (
        f"This run records {n504:,} explicit HTTP 504 responses and {n5xx:,} total 5xx outcomes at up to {max_vu} concurrent users. "
        f"504 at the edge almost always means the origin never answered in the proxy's window — thread pools, JDBC pools, or "
        f"dependency HTTP clients backing up while request threads stay parked."
    )
    para2 = "When latency percentiles collapse to the same ceiling (often 120s or 180s), you are observing queueing behind a "
    para2 += "finite worker count, not a gradual algorithmic slowdown."
    if chain_504:
        para2 += f" Band-level context: {chain_504}."
    if chain_err:
        para2 += f" Aggregate sample errors by band move as: {chain_err}."
    if no_http:
        para2 += f" {no_http:,} NoHttpResponse-style drops reinforce connection churn or abrupt worker death alongside timeouts."
    para3 = "\n\nValidate async boundaries, increase safely-sized pools, or shed load earlier (fast-fail) so the gateway does not "
    para3 += "mask the saturated tier. "
    if wall_line:
        para3 += wall_line
    return para1 + "\n\n" + para2 + para3


def _detailed_hypothesis_tx_hotspot(
    lab: str, er: float, p95: float, cnt: int, max_vu: int, chain_err: str
) -> str:
    p1 = (
        f"The controller `{lab}` is not merely noisy — it fails {er:.1f}% of {cnt:,} sampled invocations during this run, with "
        f"P95 latency ≈ {p95:,.0f} ms on successful samples where JMeter recorded elapsed time. That combination usually means "
        f"a brittle downstream contract (timeout, throttle, or semantic mismatch) rather than a diffuse platform issue."
    )
    p2 = (
        "Split the failures by `response_code`: a 404-heavy mix suggests bad IDs or routing; 5xx / Non HTTP response suggests "
        "saturation; assertion or JSR223 failures point to test data. Tie the label to APM service maps for the same test window."
    )
    if chain_err:
        p2 += f" At the macro level, errors accrue across bands as: {chain_err} — confirm whether this label tracks that slope or is an early outlier."
    p3 = (
        f"\n\nPeak concurrency was {max_vu} VU; if this label is business-critical, hold the release until the error budget on "
        f"this path clears independently of generic capacity tuning."
    )
    return p1 + "\n\n" + p2 + p3


def _detailed_hypothesis_tps_knee(rows: List[Tuple[str, int, int, Dict[str, Any]]]) -> str:
    seq = " → ".join(f"{float(bs['avg_tps']):.1f} TPS @ {lbl}" for lbl, _a, _b, bs in rows)
    return (
        f"Goodput should climb roughly linearly with offered users until a finite resource saturates. Here, average TPS traces "
        f"{seq} across the dynamic bands derived from this JTL. When the last bands flatten or fall while VU still rises, threads "
        f"are spending time waiting (locks, I/O, pool acquire) instead of finishing work — classic Universal Scalability Law knee.\n\n"
        f"Use APM to distinguish CPU saturation vs pool wait vs cooperative contention. The fix is rarely 'add random caching'; "
        f"it is identifying the narrow queue (DB connections, integration HTTP, fat lock) and widening or removing it."
    )


def _detailed_hypothesis_monotonic_ramp(chain_err: str, err_rate_pct: float) -> str:
    return (
        f"Failure rate increases from light to heavy bands without a plateau: {chain_err}. "
        f"Graduated exhaustion — connection pools, ephemeral ports, or credential throttles — often produces this staircase. "
        f"It is a different shape from a single bad URL, which tends to spike flatly. Overall error in the file is {err_rate_pct:.2f}%.\n\n"
        f"Correlate each step with infrastructure metrics (DB `active connections`, HTTP 429/503 from dependencies) rather than "
        f"assuming uniform application defects."
    )


def _detailed_hypothesis_no_http(no_http: int, max_vu: int, err_rate_pct: float) -> str:
    return (
        f"JMeter recorded {no_http:,} samples where the HTTP session did not complete cleanly (RST, truncated response, or "
        f"client-side reset). At {max_vu} peak VU and {err_rate_pct:.2f}% overall error, these events often ride along with LB "
        f"health flaps, keep-alive timeouts, or GC-stop-the-world on small heaps.\n\n"
        f"Grab packet captures or proxy logs only if APM already shows correlated failures; otherwise start with LB idle timeout vs "
        f"client pooling settings."
    )


def _build_combined_rca_hypotheses(
    *,
    data: List[Dict[str, Any]],
    band_stats: List[Dict[str, Any]],
    load_bands: List[Tuple[str, int, int]],
    tx_stats: Dict[str, Any],
    summary: Dict[str, Any],
    max_vu: int,
    total: int,
    errs: int,
    err_rate_pct: float,
    n404: int,
    n5xx: int,
    no_http: int,
) -> List[Dict[str, Any]]:
    """
    Evidence-backed root-cause hypotheses for the combined report (VU bands, HTTP classes, transaction stats).
    """
    rows = _iter_band_rows(band_stats, load_bands)
    path_profile = _best_404_path_profile(data, load_bands)
    n504 = sum(1 for d in data if str(d.get("response_code") or "") == "504")
    chain_err = _evidence_err_pct_chain(rows)
    chain_404 = _evidence_404_chain(data, load_bands)
    chain_504 = _evidence_504_chain(data, load_bands)
    worst_tx = _worst_transactions_for_rca(tx_stats, 6)

    tps_vals = [float(bs.get("avg_tps") or 0) for _lbl, _lo, _hi, bs in rows]
    tps_knee = False
    if len(tps_vals) >= 3 and tps_vals[0] > 0 and tps_vals[-1] < tps_vals[0] * 0.88:
        tps_knee = True

    monotonic_err = False
    if len(rows) >= 3:
        er_seq = [float(bs.get("err_pct") or 0) for _a, _b, _c, bs in rows]
        monotonic_err = all(er_seq[i] <= er_seq[i + 1] + 0.35 for i in range(len(er_seq) - 1)) and er_seq[-1] > er_seq[0] + 0.4

    p404_fails = (100.0 * n404 / max(errs, 1)) if errs else 0.0

    candidates: List[Dict[str, Any]] = []

    def add_card(
        *,
        title: str,
        description: str,
        hypothesis: str,
        evidence_chain: str,
        conf: int,
        sev_label: str,
    ) -> None:
        sl = (sev_label or "SEV-2").strip().upper()
        sev_key = "sev1" if sl in ("SEV-1", "SEV1", "P0", "P1") else "sev2"
        ci = min(95, max(52, int(conf)))
        candidates.append(
            {
                "title": title,
                "description": description,
                "hypothesis": hypothesis,
                "evidence_chain": evidence_chain.strip(),
                "conf": ci,
                "sev": sev_key,
                "sev_label": sl if sl.startswith("SEV-") else ("SEV-1" if sev_key == "sev1" else "SEV-2"),
            }
        )

    # 1) 404 / 4xx cluster
    if n404 > max(20, total // 200) or (err_rate_pct > 0.8 and n404 > errs * 0.25):
        ev = []
        if chain_404:
            ev.append(chain_404)
        if chain_err:
            ev.append(f"Overall error progression: {chain_err}")
        ev.append(f"{n404:,} samples with HTTP 4xx response codes (~{100.0 * n404 / max(total, 1):.2f}% of all samples).")
        if errs:
            ev.append(f"~{p404_fails:.0f}% of failed samples are 4xx-class (routing / client-visible failures).")
        if worst_tx:
            lab, er, p95, cnt = worst_tx[0]
            ev.append(f"Worst controller in this export: {lab} — {er:.1f}% error rate over {cnt:,} samples (P95 {p95:,.0f} ms).")
        conf = 73 + min(18, n404 // 400) + (6 if monotonic_err else 0)
        title404 = "Client / routing stress — HTTP 4xx cluster grows with offered load"
        if path_profile:
            title404 = f"Concurrency-sensitive 4xx / 404 on `{path_profile[0][:90]}{'…' if len(path_profile[0]) > 90 else ''}`"
        add_card(
            title=title404,
            description=(
                "4xx-heavy mix under rising load suggests unstable URLs, session-scoped identifiers, or tenant routing — "
                "a different signature than flat CPU saturation."
            ),
            hypothesis=_detailed_hypothesis_404_cluster(
                path_profile=path_profile,
                worst_tx=worst_tx,
                monotonic_err=monotonic_err,
                n404=n404,
                total=total,
                errs=errs,
                chain_404=chain_404,
            ),
            evidence_chain=" ".join(ev),
            conf=conf,
            sev_label="SEV-1" if err_rate_pct > 2.5 or (worst_tx and worst_tx[0][1] > 25) else "SEV-2",
        )

    # 2) 504 / 5xx gateway saturation
    if n504 > max(8, total // 500) or n5xx > max(25, total // 150):
        ev = []
        if chain_504:
            ev.append(chain_504)
        if chain_err:
            ev.append(f"Sample error % by VU band: {chain_err}")
        ev.append(f"{n5xx:,} HTTP 5xx responses in the JTL; {n504:,} are explicit HTTP 504 (gateway / upstream timeout).")
        if no_http:
            ev.append(f"NoHttpResponse / connection drops: {no_http:,} samples — often co-located with pool exhaustion or idle timeouts.")
        wall_tx = [(lab, er, p95, cnt) for lab, er, p95, cnt in worst_tx if p95 >= 120_000]
        if wall_tx:
            lab, er, p95, cnt = wall_tx[0]
            ev.append(f"{lab}: P95 = {p95:,.0f} ms with {er:.1f}% errors ({cnt:,} samples) — response times stacked near a fixed timeout wall.")
        elif worst_tx:
            lab, er, p95, cnt = worst_tx[0]
            ev.append(f"Heaviest failing controller: {lab} — {er:.1f}% error rate, P95 {p95:,.0f} ms ({cnt:,} samples).")
        conf = 76 + min(16, n504 // 25) + (4 if no_http else 0)
        add_card(
            title="Gateway / upstream saturation — 504s and synchronous blocking behind the edge",
            description=(
                "504 Gateway Timeout and 5xx spikes typically indicate thread pool, worker, or dependency queues backing up — "
                "the edge proxy gives up before the application returns."
            ),
            hypothesis=_detailed_hypothesis_504_cluster(
                n504=n504,
                n5xx=n5xx,
                no_http=no_http,
                chain_504=chain_504,
                chain_err=chain_err,
                worst_tx=worst_tx,
                max_vu=max_vu,
            ),
            evidence_chain=" ".join(ev),
            conf=conf,
            sev_label="SEV-1" if n504 > 30 or err_rate_pct > 3 else "SEV-2",
        )

    # 3) Dominant failing transaction (if not already covered by strong 404/5xx cards)
    if worst_tx and worst_tx[0][1] >= 12:
        lab, er, p95, cnt = worst_tx[0]
        if not any(lab in str(c.get("evidence_chain", "")) for c in candidates):
            add_card(
                title=f"Controller hotspot — {_pretty_tx_name(lab)} drives {er:.1f}% of sample failures",
                description=(
                    f"This label concentrates errors relative to others in the same run — isolate it before tuning generic capacity."
                ),
                hypothesis=_detailed_hypothesis_tx_hotspot(lab, er, p95, cnt, max_vu, chain_err),
                evidence_chain=(
                    f"{lab}: {er:.1f}% error rate over {cnt:,} samples; P95 {p95:,.0f} ms. "
                    f"Peak concurrency in file: {max_vu} VU."
                ),
                conf=71 + min(20, int(er)),
                sev_label="SEV-1" if er >= 35 else "SEV-2",
            )

    # 4) Throughput knee
    if tps_knee and rows:
        ev = [
            f"Average TPS by band: " + " → ".join(f"{float(bs['avg_tps']):.1f}/s @ {lbl}" for lbl, _a, _b, bs in rows),
            "Offered load rises while goodput flattens or falls — queues are building server-side.",
        ]
        add_card(
            title="Capacity knee — throughput stops scaling before peak VUsers",
            description=(
                "When added users no longer increase TPS-USL-style saturation dominates: threads spend time waiting, not serving."
            ),
            hypothesis=_detailed_hypothesis_tps_knee(rows),
            evidence_chain=" ".join(ev),
            conf=78,
            sev_label="SEV-2",
        )

    # 5) Progressive error ramp
    if monotonic_err and err_rate_pct > 0.35 and not any("4xx cluster" in c.get("title", "") for c in candidates):
        add_card(
            title="Monotonic error ramp — failure rate worsens with each load step",
            description="Errors increase roughly in step with each higher concurrency band without recovery.",
            hypothesis=_detailed_hypothesis_monotonic_ramp(chain_err or f"{err_rate_pct:.2f}% overall", err_rate_pct),
            evidence_chain=(f"Error % by band: {chain_err}." if chain_err else f"Overall error rate {err_rate_pct:.2f}%."),
            conf=74,
            sev_label="SEV-2",
        )

    # 6) NoHttpResponse emphasis
    if no_http > max(5, total // 2000) and not any("NoHttpResponse" in c.get("evidence_chain", "") for c in candidates):
        add_card(
            title="Connection instability — NoHttpResponse and dropped HTTP sessions",
            description="Client-side JMeter view shows connections reset or incomplete HTTP responses.",
            hypothesis=_detailed_hypothesis_no_http(no_http, max_vu, err_rate_pct),
            evidence_chain=(
                f"{no_http:,} samples tagged NoHttpResponse / empty reply in this file; peak {max_vu} VU; overall error {err_rate_pct:.2f}%."
            ),
            conf=68 + min(12, no_http // 50),
            sev_label="SEV-2",
        )

    # Merge structured critical issues from the analyser (title + narrative + synthetic evidence)
    for issue in (summary.get("critical_issues") or [])[:4]:
        if isinstance(issue, dict):
            it = str(issue.get("title") or issue.get("issue") or "").strip()
            desc = str(issue.get("description") or issue.get("detail") or "").strip()
        else:
            it, desc = str(issue).strip(), ""
        if not it or any(it.lower() in str(c.get("title", "")).lower() for c in candidates):
            continue
        enriched = desc.strip()
        if len(enriched) < 220:
            enriched = (
                (enriched + " ") if enriched else ""
            ) + (
                "Automated issue titles are a starting point only. Static misconfiguration tends to produce time-flat error rates, "
                "whereas load-correlated drift implicates shared mutable request state, pool exhaustion, or throttled backends. "
                "Map each claim onto the VU-band error curves and HTTP class mix in this HTML, then confirm with traces."
            )
        add_card(
            title=it[:220],
            description="Imported from automated critical-issues scan — validate with engineering owners.",
            hypothesis=enriched[:8000],
            evidence_chain=(
                f"Source: analyser critical_issues; overall run error {err_rate_pct:.2f}% at {max_vu} VU peak; "
                f"{errs:,} failed samples of {total:,}."
            ),
            conf=70,
            sev_label="SEV-1",
        )

    # Ensure minimum coverage for stakeholders
    while len(candidates) < 2:
        add_card(
            title="Correlate this run with APM and infrastructure metrics",
            description="No single dominant mechanical pattern was auto-promoted — deepen evidence before codifying a root cause.",
            hypothesis=(
                "Export transaction traces, database wait analytics, pool occupancy, GC timelines, and dependency (HTTP/queue) "
                "latency for the same clock window as this JMeter dataset. The charts in this report bound *where* concurrency "
                "hurts — they rarely replace a full service-level trace when leadership needs a signed root cause.\n\n"
                "When multiple weak signals appear, prioritize the failure class that consumes user journeys (timeouts vs 4xx vs "
                "assertions) before optimizing secondary noise."
            ),
            evidence_chain=(
                f"Baseline context: {total:,} samples, {err_rate_pct:.2f}% errors, peak {max_vu} VU, duration inferred from timestamps."
            ),
            conf=55,
            sev_label="SEV-2",
        )

    out: List[Dict[str, Any]] = []
    for i, c in enumerate(candidates[:6], 1):
        hypo = c["hypothesis"]
        evc = c["evidence_chain"]
        out.append(
            {
                "id": f"RCA-{i:02d}",
                "sev": c["sev"],
                "sev_label": c["sev_label"],
                "title": c["title"],
                "description": c["description"],
                "hypothesis": hypo,
                "evidence_chain": evc,
                "conf": c["conf"],
                "body": hypo,
                "evidence": evc,
            }
        )
    return out


def _combined_performance_grading_payload(
    summary: Dict[str, Any],
    tgt: Dict[str, float],
    *,
    success_rate_pct: float,
    err_rate_pct: float,
    mean_rt_ms: float,
    p95_ms: float,
    throughput: float,
    sla_pct: float,
) -> Dict[str, Any]:
    """Mirror classic JMeter HTML scorecard: overall grade, four pillars, detailed metrics table."""
    try:
        from app.analyzers.jmeter_analyzer_v2 import JMeterAnalyzerV2 as J2
    except Exception:
        J2 = None

    sr = float(success_rate_pct)
    er_dec = float(err_rate_pct) / 100.0
    avg_s = float(mean_rt_ms) / 1000.0
    p95_s = float(p95_ms) / 1000.0
    tp = float(throughput)
    sla = float(sla_pct)

    scores: Dict[str, Any] = {}
    ss = summary.get("scores")
    if isinstance(ss, dict) and ss:
        scores = {k: float(v) for k, v in ss.items() if isinstance(v, (int, float))}
    if not scores and J2 is not None:
        st = summary.get("targets")
        score_targets = J2._resolve_score_targets(st if isinstance(st, dict) else None)
        scores = J2._calculate_scores(sr, er_dec, avg_s, p95_s, tp, sla, score_targets)

    overall_score = float(summary.get("overall_score") or scores.get("overall") or 0)
    grade = str(summary.get("overall_grade") or "").strip()
    grade_class = str(summary.get("grade_class") or "warning")
    if J2 is not None:
        if not overall_score and scores.get("overall") is not None:
            overall_score = float(scores["overall"])
        if not grade:
            grade, grade_class = J2._calculate_grade(overall_score)
    if not grade:
        grade = "C+"
    if not overall_score and scores.get("overall") is not None:
        overall_score = float(scores["overall"])

    reasons = summary.get("grade_reasons")
    if (not reasons or not isinstance(reasons, dict)) and J2 is not None:
        reasons = J2._build_grade_reasons(scores, avg_s, sr, err_rate_pct, tp, p95_s, sla, grade, grade_class)
    if not isinstance(reasons, dict):
        reasons = {}

    ogd = dict(summary.get("overall_grade_description") or {})
    if J2 is not None:
        if not ogd.get("title"):
            ogd["title"] = J2._get_grade_title(grade)
        if not ogd.get("description"):
            ogd["description"] = J2._get_grade_description(grade)
        if not ogd.get("score_range"):
            ogd["score_range"] = J2._get_grade_range(grade)

    disp_targets = {
        "availability": float(tgt.get("availability") or 99),
        "response_time_ms": float(tgt.get("response_time_ms") or 2000),
        "error_rate": float(tgt.get("error_rate") or 1),
        "throughput": float(tgt.get("throughput") or 100),
        "p95_percentile_ms": float(tgt.get("p95_percentile_ms") or 3000),
        "sla_compliance": float(tgt.get("sla_compliance") or 95),
    }

    def _one_liner(g: str) -> str:
        m = {
            "A+": "Exceptional — exceeds expectations",
            "A": "Excellent — strong performance",
            "B+": "Good — meets most standards",
            "B": "Above average — minor gaps",
            "C+": "Average — needs improvement",
            "C": "Below average — significant issues",
            "D": "Poor — critical problems",
            "F": "Failing — immediate action needed",
        }
        return m.get(g, "See methodology")

    cat_keys = ["performance", "reliability", "user_experience", "scalability"]
    cards_out: List[Dict[str, Any]] = []
    for ck in cat_keys:
        block = reasons.get(ck) if isinstance(reasons.get(ck), dict) else {}
        cards_out.append(
            {
                "key": ck,
                "grade": str(block.get("grade") or "—"),
                "score": float(block.get("score") or scores.get(ck) or 0),
                "name": str(block.get("name") or ck.replace("_", " ").title()),
                "icon": str(block.get("icon") or ""),
                "weight": str(block.get("weight") or ""),
                "reason": str(block.get("reason") or ""),
                "css_class": str(block.get("class") or "warning"),
                "one_liner": _one_liner(str(block.get("grade") or "C+")),
            }
        )

    avail_pass = sr >= disp_targets["availability"] - 1e-9
    err_pass = err_rate_pct < disp_targets["error_rate"] - 1e-9
    tp_pass = tp + 1e-9 >= disp_targets["throughput"]
    rt_pass = mean_rt_ms <= disp_targets["response_time_ms"] + 1e-9
    p95_pass = p95_ms <= disp_targets["p95_percentile_ms"] + 1e-9
    sla_pass = sla + 1e-9 >= disp_targets["sla_compliance"]

    return {
        "overall_grade": grade,
        "overall_score": round(overall_score, 1),
        "grade_class": grade_class,
        "title": str(ogd.get("title") or "Performance assessment"),
        "subtitle": str(ogd.get("description") or "").strip(),
        "score_range": str(ogd.get("score_range") or ""),
        "grade_reasons": reasons,
        "category_cards": cards_out,
        "scores": scores,
        "targets": disp_targets,
        "metrics_rows": [
            {
                "metric": "Availability / success",
                "result": f"{sr:.2f}%",
                "target": f"≥{disp_targets['availability']:.0f}%",
                "status": "PASS" if avail_pass else "MARGINAL" if sr >= disp_targets["availability"] - 5 else "FAIL",
                "score": f"{scores.get('availability', 0):.0f}/100",
                "tone": "green" if avail_pass else "amber" if sr >= disp_targets["availability"] - 5 else "red",
            },
            {
                "metric": "Mean response time",
                "result": f"{mean_rt_ms:.0f} ms",
                "target": f"≤{disp_targets['response_time_ms']:.0f} ms",
                "status": "PASS" if rt_pass else "MARGINAL" if mean_rt_ms <= disp_targets["response_time_ms"] * 1.1 else "FAIL",
                "score": f"{scores.get('response_time', 0):.0f}/100",
                "tone": "green" if rt_pass else "amber",
            },
            {
                "metric": "P95 response time",
                "result": f"{p95_ms:.0f} ms",
                "target": f"≤{disp_targets['p95_percentile_ms']:.0f} ms",
                "status": "PASS" if p95_pass else "MARGINAL" if p95_ms <= disp_targets["p95_percentile_ms"] * 1.15 else "FAIL",
                "score": f"{scores.get('p95_percentile', 0):.0f}/100",
                "tone": "green" if p95_pass else "amber",
            },
            {
                "metric": "Error rate",
                "result": f"{err_rate_pct:.2f}%",
                "target": f"≤{disp_targets['error_rate']:.2f}%",
                "status": "PASS" if err_pass else "MARGINAL" if err_rate_pct < disp_targets["error_rate"] * 3 else "FAIL",
                "score": f"{scores.get('error_rate', 0):.0f}/100",
                "tone": "green" if err_pass else "amber" if err_rate_pct < disp_targets["error_rate"] * 3 else "red",
            },
            {
                "metric": "Throughput (avg)",
                "result": f"{tp:.1f} /s",
                "target": f"≥{disp_targets['throughput']:.0f} /s",
                "status": "PASS" if tp_pass else "BELOW",
                "score": f"{scores.get('throughput', 0):.0f}/100",
                "tone": "green" if tp_pass else "amber",
            },
            {
                "metric": "P90 SLA pass rate (peak slice)",
                "result": f"{sla:.1f}%",
                "target": f"≥{disp_targets['sla_compliance']:.0f}%",
                "status": "PASS" if sla_pass else "FAIL",
                "score": f"{scores.get('sla_compliance', 0):.0f}/100",
                "tone": "green" if sla_pass else "red",
            },
        ],
    }


def _heat_footnote(heat_rows: List[Dict[str, Any]]) -> str:
    if len(heat_rows) < 2:
        return ""
    lo = heat_rows[0].get("pcts") or []
    hi = heat_rows[-1].get("pcts") or []
    if len(lo) < 4 or len(hi) < 4:
        return ""
    fast_lo = sum(lo[:4])
    fast_hi = sum(hi[:4])
    tail_hi = sum(hi[-3:]) if len(hi) >= 3 else 0.0
    return (
        f"Fast responses (&lt;~3s bucket sum): {fast_lo:.1f}% at {heat_rows[0]['label']} vs {fast_hi:.1f}% at "
        f"{heat_rows[-1]['label']}. Tail (30s+ buckets): {tail_hi:.1f}% at peak band."
    )


# Response-time distribution panel: per-band cells vs Target Values + fixed error bands.
_DIST_SLA_MEAN_AMBER_MS = 1000.0
_DIST_SLA_P90_AMBER_MS = 2000.0


def _distribution_sla_tone_rt(actual: float, target_ms: float, amber_delta_ms: float) -> str:
    if actual <= target_ms + 1e-9:
        return "green"
    if actual <= target_ms + amber_delta_ms + 1e-9:
        return "amber"
    return "red"


def _distribution_sla_tone_err_pct(err_pct: float) -> str:
    if err_pct < 1.0 - 1e-9:
        return "green"
    if err_pct < 2.0 - 1e-9:
        return "amber"
    return "red"


def _build_distribution_sla_rows(
    band_stats: List[Dict[str, Any]], tgt: Dict[str, float]
) -> Tuple[List[Dict[str, Any]], float, float]:
    t_mean = float(tgt.get("response_time_ms") or 2000)
    t_p90 = float(tgt.get("p90_percentile_ms") or 3000)
    rows: List[Dict[str, Any]] = []
    for bs in band_stats:
        label = str(bs.get("label") or "")
        n = int(bs.get("n") or 0)
        if n <= 0:
            rows.append(
                {
                    "label": label,
                    "mean_rt": None,
                    "p90_rt": None,
                    "err_pct": None,
                    "mean_tone": "neu",
                    "p90_tone": "neu",
                    "err_tone": "neu",
                }
            )
            continue
        mean_rt = float(bs.get("mean_rt") or 0)
        p90_rt = float(bs.get("p90") or 0)
        err_pct = float(bs.get("err_pct") or 0)
        rows.append(
            {
                "label": label,
                "mean_rt": mean_rt,
                "p90_rt": p90_rt,
                "err_pct": err_pct,
                "mean_tone": _distribution_sla_tone_rt(mean_rt, t_mean, _DIST_SLA_MEAN_AMBER_MS),
                "p90_tone": _distribution_sla_tone_rt(p90_rt, t_p90, _DIST_SLA_P90_AMBER_MS),
                "err_tone": _distribution_sla_tone_err_pct(err_pct),
            }
        )
    return rows, t_mean, t_p90


def _tps_band_bg_colors(avg_tps_list: List[float]) -> List[str]:
    palette = ["#2D6A2D", "#2D6A2D", "#B45309", "#C0392B", "#C0392B", "#8B1F1C"]
    if len(avg_tps_list) != 6:
        return palette[: max(1, len(avg_tps_list))]
    mt = avg_tps_list[2] or 0
    mh = avg_tps_list[-1] or 0
    if mt > 0 and mh > 0 and mh < mt * 0.95:
        return palette
    return ["#2D6A2D", "#2D6A2D", "#2D6A2D", "#B45309", "#B45309", "#B45309"]


def _first_vu_for_code(data: List[Dict[str, Any]], predicate) -> str:
    rows = sorted((d for d in data if d.get("timestamp")), key=lambda x: float(x["timestamp"]))
    for d in rows:
        if predicate(d):
            return str(_vu(d))
    return "—"


def _score_targets_from_combined_tgt(tgt: Optional[Dict[str, float]]) -> Dict[str, float]:
    """Map combined-load target dict to JMeterAnalyzerV2._calculate_scores targets."""
    if not tgt:
        return _JMeterV2._resolve_score_targets(None)
    return {
        "availability": float(tgt.get("availability") or 99),
        "avg_response_sec": float(tgt.get("response_time_ms") or 2000) / 1000.0,
        "error_rate": float(tgt.get("error_rate") or 1) / 100.0,
        "throughput": float(tgt.get("throughput") or 100),
        "p95_sec": float(tgt.get("p95_percentile_ms") or 3000) / 1000.0,
        "sla_compliance": float(tgt.get("sla_compliance") or 95),
    }


def _label_row_grading(
    n_pass: int,
    n_fail: int,
    rt_ms_list: List[float],
    avg_ms: float,
    p95_ms: float,
    duration_s: float,
    score_targets: Dict[str, float],
) -> Tuple[str, float, str]:
    """
    Letter grade + overall score + CSS tone (green|amber|red|neu) for one label,
    using the same _calculate_scores / _calculate_grade path as the full JMeter report.
    """
    n_tot = n_pass + n_fail
    if n_tot <= 0:
        return "—", 0.0, "neu"
    success_rate = 100.0 * n_pass / n_tot
    err_dec = n_fail / n_tot
    tput = (n_tot / duration_s) if duration_s and duration_s > 0 else 0.0
    if rt_ms_list:
        sla_2s = 100.0 * sum(1.0 for x in rt_ms_list if float(x) < 2000.0) / len(rt_ms_list)
        avg_s = float(avg_ms) / 1000.0
        p95_s = float(p95_ms) / 1000.0
    else:
        # No successful latency samples: penalize RT/UX so grade reflects failures.
        sla_2s = 0.0
        avg_s = 30.0
        p95_s = 30.0
    scores = _JMeterV2._calculate_scores(
        success_rate, err_dec, avg_s, p95_s, tput, sla_2s, score_targets
    )
    overall = float(scores.get("overall") or 0)
    letter, gcls = _JMeterV2._calculate_grade(overall)
    tone = {"success": "green", "warning": "amber", "danger": "red"}.get(str(gcls), "neu")
    return letter, overall, tone


def _subset_duration_s(samples: List[Dict[str, Any]], throughput_global: float) -> float:
    """Wall-clock span for a sample subset; short windows use same fallback as load-band stats."""
    ts_b = [float(d["timestamp"]) for d in samples if d.get("timestamp")]
    dur = (max(ts_b) - min(ts_b)) / 1000.0 if len(ts_b) > 1 else 0.0
    if dur < 1.0:
        tp = max(float(throughput_global or 0.0), 0.01)
        dur = max(len(samples) / tp, 1.0)
    return dur


def _band_grades_for_bucket(
    bucket: List[Dict[str, Any]],
    load_bands: List[Tuple[str, int, int]],
    score_targets: Dict[str, float],
    throughput_global: float,
) -> List[Dict[str, Any]]:
    """One grade dict per load band, same scorecard as overall row; empty band → em dash."""
    out: List[Dict[str, Any]] = []
    for band_lbl, lo, hi in load_bands:
        sub = [d for d in bucket if lo <= _vu(d) <= hi]
        if not sub:
            out.append(
                {
                    "band": band_lbl,
                    "grade": "—",
                    "grade_score": 0.0,
                    "grade_tone": "neu",
                    "n": 0,
                }
            )
            continue
        n_pass = sum(1 for d in sub if _jm_explicit_success(d))
        n_fail = len(sub) - n_pass
        rt_ms = [_elapsed_ms(d) for d in sub if _jm_explicit_success(d)]
        dur_s = _subset_duration_s(sub, throughput_global)
        if rt_ms:
            arr = np.asarray(rt_ms, dtype=float)
            avg_v = float(np.mean(arr))
            p95_v = float(np.percentile(arr, 95.0))
            g_letter, g_score, g_tone = _label_row_grading(
                n_pass, n_fail, list(rt_ms), avg_v, p95_v, dur_s, score_targets
            )
        else:
            g_letter, g_score, g_tone = _label_row_grading(
                n_pass, n_fail, [], 0.0, 0.0, dur_s, score_targets
            )
        out.append(
            {
                "band": band_lbl,
                "grade": g_letter,
                "grade_score": round(float(g_score), 1),
                "grade_tone": g_tone,
                "n": len(sub),
            }
        )
    return out


def _build_tx_or_label_percentile_table(
    data: List[Dict[str, Any]],
    tgt: Optional[Dict[str, float]] = None,
    duration_s: float = 0.0,
    load_bands: Optional[List[Tuple[str, int, int]]] = None,
    throughput_global: float = 0.0,
) -> Dict[str, Any]:
    """
    Per-label elapsed stats on success=true samples only.
    If any transaction-controller rows exist (empty URL), restrict rows to those only and
    count pass/fail on those samples; otherwise include all samplers by label.
    """
    has_tc = any(is_jmeter_transaction_controller_by_url(d.get("url")) for d in data)
    tx_only = has_tc
    by_label: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in data:
        lab_raw = d.get("label")
        if lab_raw is None or str(lab_raw).strip() == "":
            continue
        lab = str(lab_raw).strip()
        if tx_only and not is_jmeter_transaction_controller_by_url(d.get("url")):
            continue
        by_label[lab].append(d)

    rows_out: List[Dict[str, Any]] = []
    score_targets = _score_targets_from_combined_tgt(tgt)
    bands = load_bands or []
    for lab in sorted(by_label.keys(), key=lambda x: x.lower()):
        bucket = by_label[lab]
        band_grade_rows = (
            _band_grades_for_bucket(bucket, bands, score_targets, throughput_global) if bands else []
        )
        rt_ms = [_elapsed_ms(d) for d in bucket if _jm_explicit_success(d)]
        n_pass = sum(1 for d in bucket if _jm_explicit_success(d))
        n_fail = len(bucket) - n_pass

        if not rt_ms:
            g_letter, g_score, g_tone = _label_row_grading(
                n_pass, n_fail, [], 0, 0, duration_s, score_targets
            )
            rows_out.append(
                {
                    "name": lab,
                    "empty_rt": True,
                    "pass": n_pass,
                    "fail": n_fail,
                    "band_grades": band_grade_rows,
                    "grade": g_letter,
                    "grade_score": round(g_score, 1),
                    "grade_tone": g_tone,
                }
            )
            continue
        arr = np.asarray(rt_ms, dtype=float)

        def _pct(p: float) -> int:
            return int(round(float(np.percentile(arr, p))))

        n_tot = n_pass + n_fail
        err_pct_tx = 100.0 * n_fail / n_tot if n_tot > 0 else 0.0
        t_mean = float((tgt or {}).get("response_time_ms") or 2000)
        t_p90 = float((tgt or {}).get("p90_percentile_ms") or 3000)
        avg_v = int(round(float(np.mean(arr))))
        p90_v = _pct(90)
        p95_v = _pct(95)
        g_letter, g_score, g_tone = _label_row_grading(
            n_pass, n_fail, list(rt_ms), float(avg_v), float(p95_v), duration_s, score_targets
        )
        rows_out.append(
            {
                "name": lab,
                "empty_rt": False,
                "min": int(np.min(arr)),
                "median": _pct(50),
                "avg": avg_v,
                "p50": _pct(50),
                "p60": _pct(60),
                "p70": _pct(70),
                "p80": _pct(80),
                "p90": p90_v,
                "p95": p95_v,
                "p99": _pct(99),
                "max": int(np.max(arr)),
                "pass": n_pass,
                "fail": n_fail,
                "avg_tone": _distribution_sla_tone_rt(float(avg_v), t_mean, _DIST_SLA_MEAN_AMBER_MS),
                "p90_tone": _distribution_sla_tone_rt(float(p90_v), t_p90, _DIST_SLA_P90_AMBER_MS),
                "fail_tone": _distribution_sla_tone_err_pct(err_pct_tx),
                "band_grades": band_grade_rows,
                "grade": g_letter,
                "grade_score": round(g_score, 1),
                "grade_tone": g_tone,
            }
        )

    band_col_txt = (
        "Load-band columns (VU ranges match the concurrency bands used elsewhere in this report) show the same grade "
        "for that label restricted to samples in that band; duration for throughput uses the sample time span in the band "
        "(or the same short-window fallback as aggregate load-band stats). "
    )
    if tx_only:
        foot = (
            "Transaction controller rows only (empty URL). Elapsed statistics (min, median, average, percentiles, max) "
            "use samples with success=true only. "
            "Pass = count of rows with success=true and empty URL; fail = count with success=false and empty URL. "
            + band_col_txt
            + "Overall grade uses the same weighted scorecard as the main report (performance 30%, reliability 25%, "
            "user experience 25%, scalability 20%) for all samples of the label: success/error mix, mean and P95 on "
            "successful samples, label throughput (samples ÷ full test duration), and % of successful samples under 2s."
        )
        title_mode = "Transaction controllers (empty URL)"
    else:
        foot = (
            "No transaction-controller samples detected — all sampler labels are listed. "
            "Elapsed statistics use samples with success=true only. Pass/fail use the success flag per row. "
            + band_col_txt
            + "Overall grade uses the same weighted scorecard as the main report (performance 30%, reliability 25%, "
            "user experience 25%, scalability 20%) for all samples of the label: success/error mix, mean and P95 on "
            "successful samples, label throughput (samples ÷ full test duration), and % of successful samples under 2s."
        )
        title_mode = "Sampler labels"

    return {
        "mode": "transactions" if tx_only else "labels",
        "title_mode": title_mode,
        "footnote": foot,
        "load_band_labels": [b[0] for b in bands],
        "rows": rows_out,
    }


def _normalize_phase_list_for_combined(phased_plan: Any) -> List[Dict[str, Any]]:
    """Ensure phased remediation is a list of dicts; map A+ maintenance payload into one phase."""
    if not isinstance(phased_plan, dict):
        return []
    phases = phased_plan.get("phases")
    if isinstance(phases, list) and phases:
        return [p for p in phases if isinstance(p, dict)]
    maint = phased_plan.get("maintenance_actions")
    if isinstance(maint, list) and maint:
        lines = [str(x).strip() for x in maint if str(x).strip()]
        msg = phased_plan.get("message") or phased_plan.get("status") or ""
        acts: List[Dict[str, Any]] = [
            {"action": line, "detail": "", "steps": []} for line in lines[:14]
        ]
        if not acts:
            acts = [{"action": "Maintain current performance baseline", "detail": "", "steps": []}]
        return [
            {
                "phase": "Sustain performance (maintenance)",
                "timeline": phased_plan.get("estimated_timeline") or "Ongoing",
                "priority": "Maintenance",
                "actions": acts,
                "expected_outcome": (str(msg).strip() or "Keep monitoring, regression load tests, and capacity reviews."),
            }
        ]
    return []


def build_combined_load_report_payload(
    data: List[Dict[str, Any]],
    metrics: Dict[str, Any],
) -> Dict[str, Any]:
    summary = metrics.get("summary") or {}
    tx_stats: Dict[str, Any] = dict(summary.get("transaction_stats") or {})
    hdr = dict(summary.get("report_header") or {})
    total = len(data) or 1
    errs = sum(1 for d in data if is_jmeter_error_outcome(d))
    err_rate_pct = 100.0 * errs / total
    ts_list = [d.get("timestamp", 0) for d in data if d.get("timestamp")]
    min_ts = min(ts_list) if ts_list else 0
    max_ts = max(ts_list) if ts_list else 0
    duration_s = (max_ts - min_ts) / 1000.0 if ts_list and max_ts > min_ts else 0.0
    dur_min = duration_s / 60.0

    # JMeter CSV timeStamp is ms since epoch (UTC). Use UTC for chart buckets so wall times
    # match standard reports; reference HTML labels some lines "IST" but uses these UTC clocks.
    tz = timezone.utc
    tz_label = "UTC"

    def fmt_clock(ms: int) -> str:
        if not ms:
            return ""
        return datetime.fromtimestamp(ms / 1000.0, tz=tz).strftime("%H:%M")

    def fmt_date(ms: int) -> str:
        if not ms:
            return ""
        return datetime.fromtimestamp(ms / 1000.0, tz=tz).strftime("%d %B %Y")

    t_start_s = fmt_clock(min_ts) if min_ts else ""
    t_end_s = fmt_clock(max_ts) if max_ts else ""
    date_s = fmt_date(min_ts) if min_ts else ""

    row_peak_vu = max((_vu(d) for d in data), default=0) or int(summary.get("max_concurrent_users") or 0)
    parallel_sum = int(summary.get("multi_source_peak_vusers_sum") or 0)
    peak_vu_report = parallel_sum if parallel_sum > 0 else row_peak_vu
    max_vu = row_peak_vu
    load_bands = _derive_dynamic_load_bands(data, max_vu)

    # Environment + host from data
    env_host = ""
    for d in data:
        u = d.get("url") or ""
        env_host = _environment_from_url(str(u))
        if env_host:
            break
    host_meta = ""
    for d in data:
        h = str(d.get("hostname") or d.get("Hostname") or "").strip()
        if h:
            host_meta = h
            break

    scenario_names = sorted({_scenario_display(str(d.get("thread_name") or "")) for d in data})
    scenarios_line = " · ".join(scenario_names[:8])
    if len(scenario_names) > 8:
        scenarios_line += " · …"

    # Per-minute buckets (wall clock in TZ)
    minute_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for d in data:
        ts = d.get("timestamp")
        if not ts:
            continue
        key = datetime.fromtimestamp(ts / 1000.0, tz=tz).strftime("%H:%M")
        minute_map[key].append(d)

    minutes_sorted = sorted(minute_map.keys())
    MINS: List[str] = []
    VUS: List[float] = []
    MEAN_RT: List[float] = []
    P90_RT: List[float] = []
    ERR_RT: List[float] = []
    TPS_ARR: List[float] = []
    for key in minutes_sorted:
        rows = minute_map[key]
        if not rows:
            continue
        MINS.append(key)
        vus = [_vu(r) for r in rows]
        VUS.append(float(max(vus)) if vus else 0.0)
        e_times = [_elapsed_ms(r) for r in rows]
        MEAN_RT.append(float(np.mean(e_times)) if e_times else 0.0)
        P90_RT.append(float(np.percentile(np.array(e_times, dtype=float), 90)) if e_times else 0.0)
        fails = sum(1 for r in rows if is_jmeter_error_outcome(r))
        ERR_RT.append(round(100.0 * fails / len(rows), 2) if rows else 0.0)
        TPS_ARR.append(round(len(rows) / 60.0, 2))

    passed = total - errs
    throughput = passed / duration_s if duration_s > 0 else float(metrics.get("throughput") or 0)
    sample_stats = metrics.get("sample_time") or {}
    mean_all = float(sample_stats.get("mean") or 0)
    p99_all = float(sample_stats.get("p99") or 0)

    # Peak TPS minute
    peak_tps = max(TPS_ARR) if TPS_ARR else 0.0
    peak_tps_min = MINS[TPS_ARR.index(peak_tps)] if TPS_ARR and peak_tps in TPS_ARR else ""

    # Scenario bars
    scen_samples: Dict[str, int] = defaultdict(int)
    scen_errs: Dict[str, int] = defaultdict(int)
    for d in data:
        sk = _scenario_display(str(d.get("thread_name") or ""))
        scen_samples[sk] += 1
        if is_jmeter_error_outcome(d):
            scen_errs[sk] += 1
    scenario_rows = []
    total_s = sum(scen_samples.values()) or 1
    colors = ["red", "green", "amber", "blue"]
    for i, (name, cnt) in enumerate(sorted(scen_samples.items(), key=lambda x: -x[1])[:8]):
        er = 100.0 * scen_errs[name] / cnt if cnt else 0.0
        pct = max(5, int(100 * cnt / total_s))
        scenario_rows.append(
            {
                "name": name,
                "width_pct": pct,
                "color": colors[i % len(colors)],
                "samples": cnt,
                "err_pct": round(er, 1),
            }
        )

    # Load-band stats
    band_stats: List[Dict[str, Any]] = []
    heat_rows: List[Dict[str, Any]] = []
    lat_rows: List[Dict[str, Any]] = []
    apdex_by_band: List[float] = []
    err_band_404: List[int] = []
    err_band_5xx: List[int] = []
    err_band_other: List[int] = []

    for label, lo, hi in load_bands:
        band_rows = [d for d in data if lo <= _vu(d) <= hi]
        if not band_rows:
            band_stats.append(
                {
                    "label": label,
                    "n": 0,
                    "mean_rt": 0.0,
                    "p50": 0.0,
                    "p90": 0.0,
                    "p95": 0.0,
                    "p99": 0.0,
                    "err_pct": 0.0,
                    "avg_tps": 0.0,
                    "rx_mb": 0.0,
                    "tx_mb": 0.0,
                }
            )
            heat_rows.append({"label": label, "pcts": [0.0] * 10})
            lat_rows.append(
                {
                    "band": label,
                    "tcp_med": 0,
                    "tcp_p90": 0,
                    "ttfb_med": 0,
                    "ttfb_p90": 0,
                    "elapsed_med": 0,
                    "server_med": 0,
                    "mean_rt": 0,
                    "badge": "gray",
                    "badge_text": "N/A",
                }
            )
            apdex_by_band.append(0.0)
            err_band_404.append(0)
            err_band_5xx.append(0)
            err_band_other.append(0)
            continue
        et = [_elapsed_ms(d) for d in band_rows]
        arr = np.array(et, dtype=float)
        errn = sum(1 for d in band_rows if is_jmeter_error_outcome(d))
        ts_b = [float(d["timestamp"]) for d in band_rows if d.get("timestamp")]
        dur_band = (max(ts_b) - min(ts_b)) / 1000.0 if len(ts_b) > 1 else 0.0
        if dur_band < 1.0:
            dur_band = max(len(band_rows) / max(throughput, 0.01), 1.0)
        avg_tps_band = len(band_rows) / dur_band if dur_band > 0 else 0.0
        rx_mb = sum(int(d.get("bytes") or 0) for d in band_rows) / (1024 * 1024)
        tx_mb = sum(int(d.get("sent_bytes") or 0) for d in band_rows) / (1024 * 1024)
        n404 = sum(
            1
            for d in band_rows
            if str(d.get("response_code") or "").startswith("4")
        )
        n5 = sum(
            1
            for d in band_rows
            if str(d.get("response_code") or "").startswith("5")
        )
        nnhr = sum(
            1
            for d in band_rows
            if "nohttp" in str(d.get("response_message", "")).lower()
            or "no http" in str(d.get("failure_message", "")).lower()
        )
        err_band_404.append(n404)
        err_band_5xx.append(n5)
        err_band_other.append(nnhr)
        band_stats.append(
            {
                "label": label,
                "n": len(band_rows),
                "mean_rt": float(np.mean(arr)),
                "p50": float(np.percentile(arr, 50)),
                "p90": float(np.percentile(arr, 90)),
                "p95": float(np.percentile(arr, 95)),
                "p99": float(np.percentile(arr, 99)),
                "err_pct": round(100.0 * errn / len(band_rows), 2),
                "avg_tps": round(avg_tps_band, 2),
                "rx_mb": round(rx_mb, 1),
                "tx_mb": round(tx_mb, 1),
            }
        )
        # heatmap %
        bucket_counts = [0] * (len(HEAT_EDGES_MS) - 1)
        for ms in et:
            bucket_counts[_heat_bucket_idx(ms)] += 1
        totb = len(et) or 1
        heat_rows.append(
            {"label": label, "pcts": [round(100.0 * c / totb, 1) for c in bucket_counts]}
        )
        # latency decomposition (median / p90)
        lats = [float(d.get("latency") or 0) for d in band_rows]
        cts = [float(d.get("connect_time") or d.get("Connect") or 0) for d in band_rows]
        tcp_med = float(np.median(cts)) if cts else 0.0
        tcp_p90 = float(np.percentile(np.array(cts, dtype=float), 90)) if cts else 0.0
        ttfb_med = float(np.median(lats)) if lats else 0.0
        ttfb_p90 = float(np.percentile(np.array(lats, dtype=float), 90)) if lats else 0.0
        elapsed_med = float(np.median(arr))
        server_med = max(0.0, elapsed_med - ttfb_med)
        mean_band = float(np.mean(arr))
        # Defer badge to chain pass — append provisional row
        lat_rows.append(
            {
                "band": label,
                "tcp_med": int(tcp_med),
                "tcp_p90": int(tcp_p90),
                "ttfb_med": int(ttfb_med),
                "ttfb_p90": int(ttfb_p90),
                "elapsed_med": int(elapsed_med),
                "server_med": int(server_med),
                "mean_rt": int(mean_band),
                "badge": "outline-green",
                "badge_text": "Healthy",
            }
        )
        apdex_by_band.append(_apdex(et, 3000.0))

    # Apply TTFB chain logic (skip N/A rows; only populations with samples)
    populated_indices = [i for i, r in enumerate(lat_rows) if r.get("badge_text") != "N/A"]
    prev_ttfb: Optional[float] = None
    data_band_idx = 0
    for i in populated_indices:
        row = lat_rows[i]
        ttfb_f = float(row["ttfb_p90"])
        mean_f = float(row.get("mean_rt", 0))
        badge, btext = _latency_decomp_badge(ttfb_f, mean_f, data_band_idx, prev_ttfb)
        row["badge"] = badge
        row["badge_text"] = btext
        prev_ttfb = ttfb_f
        data_band_idx += 1

    # Bar chart percentiles per band (passed samples for RT percentiles)
    bar_percentiles = []
    for label, lo, hi in load_bands:
        band_rows = [
            d
            for d in data
            if lo <= _vu(d) <= hi and not is_jmeter_error_outcome(d) and _elapsed_ms(d) > 0
        ]
        if not band_rows:
            bar_percentiles.append([0, 0, 0, 0])
            continue
        et = [_elapsed_ms(d) for d in band_rows]
        arr = np.array(et, dtype=float)
        bar_percentiles.append(
            [
                float(np.median(arr)),
                float(np.percentile(arr, 75)),
                float(np.percentile(arr, 90)),
                float(np.percentile(arr, 95)),
            ]
        )

    ttfb_stack = []
    content_stack = []
    for row in lat_rows:
        ttfb_stack.append(row["ttfb_med"])
        content_stack.append(max(0, row["elapsed_med"] - row["ttfb_med"]))

    # Scorecard from transaction_stats
    crit_rows, healthy_rows = [], []
    counts = {"critical": 0, "warning": 0, "slow": 0, "healthy": 0}
    for label, st in sorted(tx_stats.items(), key=lambda x: (x[0] or "").lower()):
        cnt = int(st.get("count") or 0)
        if cnt == 0:
            continue
        err_pct = float(st.get("error_rate") or 0)
        p90 = st.get("p90")
        p90f = float(p90) if p90 is not None else None
        mean_v = st.get("avg_response")
        mean_f = float(mean_v) if mean_v is not None else 0.0
        samples_tx = [ _elapsed_ms(d) for d in data if d.get("label") == label]
        apx = _apdex(samples_tx, 3000.0)
        st_code = _tx_status(err_pct, p90f)
        if st_code in counts:
            counts[st_code] += 1
        else:
            counts["healthy"] += 1
        rowd = {
            "tx": label,
            "samples": cnt,
            "mean": int(mean_f),
            "p90": int(p90f) if p90f is not None else 0,
            "p95": int(float(st.get("p95") or 0)),
            "err_pct": round(err_pct, 1),
            "apdex": apx,
            "status": st_code,
        }
        if st_code == "critical":
            crit_rows.append(rowd)
        elif st_code == "healthy" and len(healthy_rows) < 12:
            healthy_rows.append(rowd)
    crit_rows.sort(key=lambda x: -x["err_pct"])

    # Apdex showcase (worst + best)
    apdex_cells = []
    tx_ap = []
    for label, st in tx_stats.items():
        samples_tx = [_elapsed_ms(d) for d in data if d.get("label") == label]
        if len(samples_tx) < 3:
            continue
        sc = _apdex(samples_tx, 3000.0)
        tx_ap.append((label, sc))
    tx_ap.sort(key=lambda x: x[1])
    worst_pick = tx_ap[:6]
    seen_ap = {x[0] for x in worst_pick}
    for label, sc in worst_pick:
        apdex_cells.append(
            {
                "name": label,
                "score": sc,
                "rating": _apdex_label(sc),
                "tone": "red" if sc < 0.5 else "amber",
            }
        )
    for label, sc in reversed(tx_ap):
        if sc < 0.85 or label in seen_ap:
            continue
        apdex_cells.append({"name": label, "score": sc, "rating": _apdex_label(sc), "tone": "green"})
        seen_ap.add(label)
        if len(apdex_cells) >= 18:
            break

    # Response codes breakdown
    rcounter = Counter(str(d.get("response_code") or "") for d in data)
    n4 = sum(c for k, c in rcounter.items() if k.startswith("4"))
    n5 = sum(c for k, c in rcounter.items() if k.startswith("5"))
    no_http = sum(
        1
        for d in data
        if "nohttp" in str(d.get("response_message", "")).lower()
        or "no http" in str(d.get("failure_message", "")).lower()
    )

    sla_peak = summary.get("transaction_sla_p90_peak") or {}
    sla_pct = float(sla_peak.get("pass_rate_pct") or 0)
    n_tx_pass = int(sla_peak.get("transactions_pass") or 0)
    n_tx_test = int(sla_peak.get("transactions_tested") or len(tx_stats))

    tgt = _targets_from_summary(summary)
    success_rate = float(summary.get("success_rate") or (100.0 - err_rate_pct))
    p95_all_ms = float(sample_stats.get("p95") or 0)

    p90_gate_ms = float(tgt["p90_percentile_ms"])
    err_gate_pct = float(tgt["error_rate"])

    performance_grading = _combined_performance_grading_payload(
        summary,
        tgt,
        success_rate_pct=success_rate,
        err_rate_pct=err_rate_pct,
        mean_rt_ms=mean_all,
        p95_ms=p95_all_ms,
        throughput=throughput,
        sla_pct=sla_pct,
    )

    verdict, verdict_class, verdict_detail = _release_decision_from_grading(performance_grading)

    sla_peak_dict: Dict[str, Any] = dict(sla_peak) if isinstance(sla_peak, dict) else {}
    key_findings, finding_sev = _derive_key_findings_for_release(
        data=data,
        band_stats=band_stats,
        tx_stats=tx_stats,
        max_vu=max_vu,
        sla_peak=sla_peak_dict,
        tgt=tgt,
        err_rate_pct=err_rate_pct,
        errs=errs,
        total=total,
        rcounter=rcounter,
        p90_gate_ms=p90_gate_ms,
        err_gate_pct=err_gate_pct,
        load_bands=load_bands,
    )

    raw_safe, marginal_lo, marginal_hi, safe_cap_detail, med_detail, peak_detail, cap_has_stress = _capacity_envelope_vu(
        band_stats,
        max_vu,
        load_bands,
        tgt,
        err_rate_pct=err_rate_pct,
        lat_rows=lat_rows,
        apdex_by_band=apdex_by_band,
        TPS_ARR=TPS_ARR,
        MINS=MINS,
        MEAN_RT=MEAN_RT,
        dur_min=dur_min,
        total=total,
        n5xx=n5,
        no_http=no_http,
    )
    if raw_safe is None:
        safe_vu = 0
        safe_kpi_sub = safe_cap_detail
        safe_kpi_tone = "red"
    else:
        safe_vu = raw_safe
        safe_kpi_sub = safe_cap_detail
        safe_kpi_tone = "amber" if safe_vu < max_vu else ""

    if marginal_lo is not None and marginal_hi is not None and marginal_lo <= marginal_hi:
        medium_vu = marginal_hi
    elif cap_has_stress:
        medium_vu = raw_safe if raw_safe is not None else max_vu
    else:
        medium_vu = max_vu

    # Primary value: when no band meets tier-1 targets, show explicit text (subtitle still has full rationale).
    safe_range = (
        f"0–{raw_safe} VUsers"
        if raw_safe is not None
        else "None — no band met all tier-1 targets"
    )
    marginal_range = (
        f"{marginal_lo}–{marginal_hi} VUsers"
        if marginal_lo is not None and marginal_hi is not None and marginal_lo <= marginal_hi
        else "—"
    )
    if cap_has_stress:
        if marginal_hi is not None:
            peak_range = f"{marginal_hi}+ VUsers"
        elif raw_safe is not None:
            peak_range = f"{raw_safe}+ VUsers"
        else:
            peak_range = f"{max_vu}+ VUsers"
    else:
        peak_range = f"{max_vu} VUsers"

    err_onset_clock = "—"
    for k in minutes_sorted:
        rs = minute_map.get(k, [])
        if rs and sum(1 for r in rs if is_jmeter_error_outcome(r)) > 0:
            err_onset_clock = k
            break
    onset_504_vu = _first_vu_for_code(data, lambda d: str(d.get("response_code") or "") == "504")
    top_err_minutes = _top_error_minutes(minute_map, 6)
    peak_err_time = top_err_minutes[0]["time"] if top_err_minutes else ""
    peak_err_vu = top_err_minutes[0].get("vu", 0) if top_err_minutes else 0

    line1_hdr = str(hdr.get("line1", "") or "")
    title_part = line1_hdr.split(" · ")[1] if " · " in line1_hdr else ""
    title_line = str(hdr.get("application_name") or title_part or line1_hdr or "Application")

    uniq_tx = len(tx_stats)
    n_sc = len(scenario_names)
    gate_lines = (
        f"Capacity vs Target Values: proven safe = mean RT, P95, and error % within targets per band; "
        f"marginal = above targets but within +{_MARGINAL_MEAN_RT_DELTA_MS:.0f} ms mean, "
        f"+{_MARGINAL_P95_DELTA_MS:.0f} ms P95, +{_MARGINAL_ERR_DELTA_PCT:.0f}% error; "
        f"stress / observed peak = beyond those marginal caps."
    )
    _cap_suffix = " — combined load across merged JMeter files" if parallel_sum > 0 else ""
    if raw_safe is not None:
        cap_sentence = (
            f"Proven-safe band from band-wise analysis: {safe_range} (tested peak {peak_vu_report} VU{_cap_suffix})."
        )
    else:
        cap_sentence = (
            f"No concurrent-user band kept all three metrics within Target Values; tested peak {peak_vu_report} VU{_cap_suffix}."
        )
    _peak_blurb = (
        f"{peak_vu_report} VU combined across merged result files (up to {row_peak_vu} VU in any row). "
        if parallel_sum > 0
        else f"{peak_vu_report} VU per sample file. "
    )
    exec_blurb = (
        f"{n_sc} scenario(s); concurrent users peaked at {_peak_blurb}"
        f"({total:,} samples, {dur_min:.1f} min). "
        f"Overall error rate {err_rate_pct:.2f}%. {gate_lines} {cap_sentence}"
    )
    if scenario_rows:
        _worst_sc = max(scenario_rows, key=lambda x: (x["err_pct"] / 100.0) * x["samples"])
        scenario_foot = (
            f"{_worst_sc['name']} drives {_worst_sc['err_pct']:.1f}% of sample errors ({_worst_sc['samples']:,} samples) — prioritize triage there."
        )
    else:
        scenario_foot = ""

    heat_foot = _heat_footnote(heat_rows)
    dist_sla_rows, dist_mean_tgt, dist_p90_tgt = _build_distribution_sla_rows(band_stats, tgt)
    band_avg_tps_list = [float(b.get("avg_tps") or 0) for b in band_stats]
    tps_band_colors = _tps_band_bg_colors(band_avg_tps_list)

    kpis = [
        {"label": "Total samples", "value": f"{total:,}", "sub": f"across {uniq_tx} transaction controllers", "tone": ""},
        {"label": "Overall error rate", "value": f"{err_rate_pct:.2f}%", "sub": f"{errs:,} failed samples", "tone": "red" if err_rate_pct >= tgt["error_rate"] else "amber" if err_rate_pct >= tgt["error_rate"] * 0.85 else ""},
        {"label": "Peak concurrent users", "value": str(peak_vu_report), "sub": (
            f"sum of peak VU per merged file ({parallel_sum}); up to {row_peak_vu} VU in any row"
            if parallel_sum > 0
            else "max allThreads / grpThreads in CSV rows"
        ), "tone": ""},
        {"label": "Avg TPS", "value": f"{throughput:.1f}", "sub": f"peak {peak_tps:.1f} / min · {peak_tps_min}" if peak_tps_min else f"peak {peak_tps:.1f} / min", "tone": ""},
        {
            "label": "Overall mean RT",
            "value": f"{int(mean_all):,} ms",
            "sub": f"P95 = {p95_all_ms:.0f} ms (target ≤{tgt['p95_percentile_ms']:.0f} ms)",
            "tone": "red" if mean_all > tgt["response_time_ms"] else "amber" if mean_all > tgt["response_time_ms"] * 0.9 else "",
        },
        {"label": "P90 SLA pass rate", "value": f"{sla_pct:.0f}%", "sub": f"{n_tx_pass} of {n_tx_test} transactions (target ≥{tgt['sla_compliance']:.0f}%)", "tone": "red" if sla_pct < tgt["sla_compliance"] else "amber" if sla_pct < tgt["sla_compliance"] + 5 else ""},
        {"label": "Safe capacity", "value": safe_range, "sub": safe_kpi_sub, "tone": safe_kpi_tone},
        {"label": "Test duration", "value": f"{dur_min:.1f} min", "sub": f"{t_start_s} → {t_end_s} {tz_label}" if t_start_s else "", "tone": ""},
    ]

    rca = _build_combined_rca_hypotheses(
        data=data,
        band_stats=band_stats,
        load_bands=load_bands,
        tx_stats=tx_stats,
        summary=summary,
        max_vu=max_vu,
        total=total,
        errs=errs,
        err_rate_pct=err_rate_pct,
        n404=n4,
        n5xx=n5,
        no_http=no_http,
    )

    phased_plan = summary.get("phased_improvement_plan") or {}
    phase_list = _normalize_phase_list_for_combined(phased_plan)

    tx_pct_table = _build_tx_or_label_percentile_table(
        data, tgt, duration_s, load_bands, throughput
    )

    band_labels_dyn = [x[0] for x in load_bands]
    _par_zone = (
        f" Combined parallel load (sum of per-file peaks): {parallel_sum} VU."
        if parallel_sum > 0
        else ""
    )
    zones_preamble = (
        "Concurrency bands in this report follow the VU range actually exercised in this JMeter run "
        f"(up to {row_peak_vu} VU in any sample row).{_par_zone} "
        f"Split into about {len(band_labels_dyn)} windows such as "
        f"{', '.join(band_labels_dyn[:4])}{' …' if len(band_labels_dyn) > 4 else ''}. "
        "Zone A / B / C below is behaviour-based — stable green load, degrading amber, and high stress — "
        "using your saved P90 and error targets plus how throughput moves between bands, not fixed 1–30 / 31–60 tiers."
    )
    chart_observations = _build_chart_observations(
        MINS,
        VUS,
        MEAN_RT,
        P90_RT,
        ERR_RT,
        TPS_ARR,
        band_stats,
        bar_percentiles,
        heat_rows,
        apdex_by_band,
        float(max_vu),
        float(tgt["p95_percentile_ms"]),
        float(tgt["error_rate"]),
        err_rate_pct,
    )

    return {
        "meta": {
            "title_line": title_line,
            "report_title": "Load Test Report",
            "subtitle": f"Observed load · peak {peak_vu_report} VU · {total:,} samples · {dur_min:.1f} minutes",
            "test_date_line": f"{date_s} · {t_start_s}–{t_end_s} {tz_label}" if date_s else hdr.get("line3", ""),
            "environment": env_host or "—",
            "host": host_meta or "—",
            "scenarios": scenarios_line or "—",
            "prepared_by": "RAGHVENDRA KUMAR",
        },
        "verdict": {"text": verdict, "detail": verdict_detail, "css": verdict_class},
        "key_findings": key_findings,
        "finding_severity": finding_sev,
        "exec_blurb": exec_blurb,
        "scenario_foot": scenario_foot,
        "kpis": kpis,
        "scenarios": scenario_rows,
        "zones_preamble": zones_preamble,
        "zones_intro": _zones_intro_detailed(
            band_stats,
            lat_rows,
            data,
            max_vu,
            float(tgt["p95_percentile_ms"]),
            float(tgt["error_rate"]),
            load_bands,
        ),
        "chart_observations": chart_observations,
        "timeline": _build_key_events_timeline(
            minute_map,
            MINS,
            VUS,
            MEAN_RT,
            P90_RT,
            ERR_RT,
            TPS_ARR,
            tz_label,
            max_vu,
            float(tgt["p95_percentile_ms"]),
        ),
        "charts": {
            "MINS": MINS,
            "VUS": VUS,
            "MEAN_RT": MEAN_RT,
            "P90_RT": P90_RT,
            "ERR_RT": ERR_RT,
            "TPS_ARR": TPS_ARR,
            "BANDS": band_labels_dyn,
            "bar_percentiles": bar_percentiles,
            "ttfb": ttfb_stack,
            "content": content_stack,
            "apdex_bands": apdex_by_band,
            "score_donut": [counts["healthy"], counts["slow"], counts["warning"], counts["critical"]],
            "band_avg_tps": band_avg_tps_list,
            "tps_band_colors": tps_band_colors,
            "band_rx_mb": [float(b.get("rx_mb") or 0) for b in band_stats],
            "band_tx_mb": [float(b.get("tx_mb") or 0) for b in band_stats],
            "err_band_404": err_band_404,
            "err_band_5xx": err_band_5xx,
            "err_band_nhr": err_band_other,
        },
        "heatmap": heat_rows,
        "heat_foot": heat_foot,
        "distribution_sla": {
            "rows": dist_sla_rows,
            "mean_target_ms": dist_mean_tgt,
            "p90_target_ms": dist_p90_tgt,
        },
        "latency_rows": lat_rows,
        "latency_diag_version": "ttfb_chain_v2_initial850_step25_40_60",
        "throughput_kpis": _throughput_kpis(
            band_stats, MINS, TPS_ARR, VUS, max_vu, peak_tps, peak_tps_min, tz_label
        ),
        "errors_kpis": {
            "n4xx": n4,
            "n5xx": n5,
            "no_http": no_http,
            "peak_err_pct": max(ERR_RT) if ERR_RT else 0,
            "err_onset": err_onset_clock,
            "onset_504_vu": onset_504_vu,
            "peak_err_time": peak_err_time,
            "peak_err_vu": peak_err_vu,
        },
        "error_top_minutes": top_err_minutes,
        "performance_grading": performance_grading,
        "scorecard": {"counts": counts, "critical": crit_rows[:15], "healthy": healthy_rows[:12]},
        "scorecard_desc": {
            "total_rated": sum(counts.values()),
        },
        "apdex_cells": apdex_cells[:18],
        "rca": rca,
        "capacity": {
            "safe_vu": safe_vu,
            "medium_vu": medium_vu,
            "max_vu": max_vu,
            "peak_parallel_vusers": peak_vu_report,
            "multi_source_peak_vusers_sum": parallel_sum,
            "target_vu": max_vu,
            "safe_range": safe_range,
            "marginal_range": marginal_range,
            "peak_range": peak_range,
            "safe_sub": safe_cap_detail,
            "med_sub": med_detail,
            "target_sub": peak_detail,
        },
        "phased_plan": phased_plan,
        "phase_list": phase_list,
        "success_rows": _success_gate_rows(err_rate_pct, sla_pct, throughput, band_stats, tgt),
        "transaction_percentile_table": tx_pct_table,
        "footer": {
            "left": f"{title_line} · {date_s}",
            "right": f"{total:,} samples · {dur_min:.1f} min · {verdict}",
        },
    }


def _throughput_kpis(
    band_stats: List[Dict[str, Any]],
    mins: List[str],
    tps: List[float],
    vus: List[float],
    max_vu: int,
    peak_tps: float,
    peak_tps_min: str,
    tz_label: str,
) -> List[Dict[str, str]]:
    populated = [b for b in band_stats if b.get("n")]
    hi_idxs = [i for i in range(len(vus)) if vus[i] >= max(1, int(max_vu * 0.9))]
    sub_tps = [tps[i] for i in hi_idxs] if hi_idxs else tps
    spread = "—"
    tone_spread = ""
    if sub_tps:
        lo, hi = min(sub_tps), max(sub_tps)
        spread = f"{lo:.1f}–{hi:.1f}"
        if hi > 0 and (hi - lo) / hi > 0.45:
            tone_spread = "red"
    rows: List[Dict[str, str]] = [
        {
            "label": "Max TPS achieved",
            "value": f"{peak_tps:.1f}",
            "sub": f"{peak_tps_min} {tz_label}" if peak_tps_min else "per rolling minute",
            "tone": "green",
        }
    ]
    for b in populated:
        rows.append(
            {
                "label": f"TPS ({b.get('label')})",
                "value": f"{float(b.get('avg_tps') or 0):.1f}",
                "sub": f"{int(b.get('n') or 0):,} samples",
                "tone": "",
            }
        )
    rows.append(
        {
            "label": "TPS spread (high-load minutes)",
            "value": spread,
            "sub": "min–max when minute-mean VU ≥90% of peak",
            "tone": tone_spread,
        }
    )
    sat = "—"
    sat_tone = ""
    if len(populated) >= 2:
        r0 = float(populated[0].get("avg_tps") or 0)
        r1 = float(populated[-1].get("avg_tps") or 0)
        lbl0 = str(populated[0].get("label") or "")
        lbl1 = str(populated[-1].get("label") or "")
        if r0 > 0 and r1 < r0 * 0.95:
            sat = f"↓ {((r1 / r0 - 1) * 100):.0f}% TPS ({lbl1} vs {lbl0})"
            sat_tone = "amber"
        else:
            sat = f"No regression ({lbl0} → {lbl1})"
    elif len(populated) == 1:
        sat = f"Single band {populated[0].get('label')}"
    rows.append(
        {
            "label": "Saturation signal (band TPS)",
            "value": sat,
            "sub": "compare first vs last populated bands only",
            "tone": sat_tone,
        }
    )
    return rows


def _success_gate_rows(
    err_rate_pct: float,
    sla_pct: float,
    throughput: float,
    band_stats: List[Dict[str, Any]],
    targets: Dict[str, float],
) -> List[Dict[str, str]]:
    t_err = float(targets["error_rate"])
    t_sla = float(targets["sla_compliance"])
    t_tp = float(targets["throughput"])
    populated = [b for b in band_stats if b.get("n")]
    gap_tps = "—"
    if len(populated) >= 2:
        t_first = float(populated[0].get("avg_tps") or 0)
        t_last = float(populated[-1].get("avg_tps") or 0)
        if t_first > 0 and t_last < t_first * 0.95:
            gap_tps = f"{((t_last / t_first - 1) * 100):.0f}% vs first band"
        else:
            gap_tps = "Non-decreasing vs first band"
    elif len(populated) == 1:
        gap_tps = "Single VU band in file"
    gap_err = (
        f"+{err_rate_pct - t_err:.2f} pp vs ≤{t_err:.2f}%"
        if err_rate_pct > t_err + 1e-12
        else f"Met (≤{t_err:.2f}%)"
    )
    gap_sla = (
        f"{sla_pct - t_sla:.1f} pp below ≥{t_sla:.1f}%"
        if sla_pct + 1e-12 < t_sla
        else f"Met (≥{t_sla:.1f}%)"
    )
    if throughput + 1e-12 < t_tp:
        tp_gap = f"Short by {t_tp - throughput:.1f}/s vs ≥{t_tp:.0f}/s"
    else:
        tp_gap = f"Met (≥{t_tp:.0f}/s)"
    return [
        {"criterion": "Overall error rate", "target": f"≤{t_err:.2f}%", "current": f"{err_rate_pct:.2f}%", "gap": gap_err},
        {
            "criterion": "P90 SLA pass rate (peak slice)",
            "target": f"≥{t_sla:.1f}%",
            "current": f"{sla_pct:.1f}%",
            "gap": gap_sla,
        },
        {"criterion": "Mean throughput", "target": f"≥{t_tp:.0f} req/s", "current": f"{throughput:.1f}/s", "gap": tp_gap},
        {
            "criterion": "Throughput vs first populated band",
            "target": "Non-decreasing at higher bands",
            "current": f"{throughput:.1f}/s avg",
            "gap": gap_tps,
        },
    ]


def _vu_range_mix(data: List[Dict[str, Any]], lo: int, hi: int) -> Dict[str, int]:
    rows = [d for d in data if lo <= _vu(d) <= hi]
    n = len(rows)
    if n == 0:
        return {"n404": 0, "n5xx": 0, "nnhr": 0, "nfail": 0, "samples": 0}
    nf = sum(1 for d in rows if is_jmeter_error_outcome(d))
    n404 = sum(1 for d in rows if str(d.get("response_code") or "").startswith("4"))
    n5 = sum(1 for d in rows if str(d.get("response_code") or "").startswith("5"))
    nnhr = sum(
        1
        for d in rows
        if "nohttp" in str(d.get("response_message", "")).lower()
        or "no http" in str(d.get("failure_message", "")).lower()
    )
    return {"n404": n404, "n5xx": n5, "nnhr": nnhr, "nfail": nf, "samples": n}


def _err_range_from_bands(band_stats: List[Dict[str, Any]], labels: List[str]) -> Optional[Tuple[float, float]]:
    sub = [b for b in band_stats if b.get("label") in labels and b.get("n")]
    if not sub:
        return None
    ers = [float(b.get("err_pct") or 0) for b in sub]
    return min(ers), max(ers)


def _tcp_note_for_band_labels(lat_rows: List[Dict[str, Any]], band_labels: List[str]) -> str:
    rows = [r for r in lat_rows if r.get("band") in band_labels]
    if not rows:
        return ""
    tcp_max = max(int(r.get("tcp_med") or 0) for r in rows)
    if tcp_max <= 2:
        return (
            f"TCP connect medians stay ≤{tcp_max} ms in {', '.join(band_labels)} — "
            "the LAN/client stack is not driving latency here."
        )
    return (
        f"TCP connect medians reach {tcp_max} ms in this slice — validate DNS/TLS or remote client paths if unexpected."
    )


def _tps_progression_in_zone(band_stats: List[Dict[str, Any]], band_labels: List[str]) -> str:
    sub = [b for b in band_stats if b.get("label") in band_labels and b.get("n")]
    if len(sub) < 2:
        if len(sub) == 1:
            return (
                f"Throughput ~{float(sub[0].get('avg_tps') or 0):.1f} avg TPS in {sub[0].get('label')} "
                "(only one populated band in this zone)."
            )
        return ""
    tpsv = [float(b.get("avg_tps") or 0) for b in sub]
    if tpsv[-1] > tpsv[0] * 1.05:
        return (
            f"Average TPS climbs ~{tpsv[0]:.1f} → {tpsv[-1]:.1f}/s from {sub[0].get('label')} to {sub[-1].get('label')} "
            "— throughput still scaling with offered load."
        )
    if tpsv[-1] < tpsv[0] * 0.95:
        return (
            f"Throughput slips ~{tpsv[0]:.1f} → {tpsv[-1]:.1f}/s inside {sub[0].get('label')} → {sub[-1].get('label')} "
            "before the highest VU bands — early capacity signal."
        )
    return (
        f"TPS remains near ~{float(np.mean(tpsv)):.1f}/s across {', '.join(band_labels)} — flat delivery versus step-ups in VU."
    )


def _error_dominant_narrative(mix: Dict[str, int]) -> str:
    if mix["samples"] == 0:
        return "No samples land in this VU envelope."
    if mix["nfail"] == 0:
        return f"No failed transactions in-zone ({mix['samples']:,} samples) — clean slice for this concurrency band."
    nfail = max(1, mix["nfail"])
    p404 = 100.0 * mix["n404"] / nfail
    p5 = 100.0 * mix["n5xx"] / nfail
    if p404 >= 55:
        return (
            f"4xx-heavy mix (~{p404:.0f}% of {mix['nfail']:,} failures): likely routing, fixtures, or client-visible rejects — "
            "different root cause than pure saturation."
        )
    if p5 >= 50:
        return (
            f"5xx / gateway-heavy mix (~{p5:.0f}% of {mix['nfail']:,} failures) — server-side timeouts or saturation typical here."
        )
    if mix["nnhr"] > max(3, nfail // 4):
        return (
            f"Connection drops (NoHttp) materially present ({mix['nnhr']:,}) alongside {mix['n404']:,} 4xx and {mix['n5xx']:,} 5xx — "
            "watch thread pools and keep-alive handling."
        )
    return (
        f"Mixed failures: {mix['n404']:,} 4xx, {mix['n5xx']:,} 5xx, {mix['nnhr']:,} connection anomalies out of {mix['nfail']:,} bad samples."
    )


def _observed_vu_bounds(data: List[Dict[str, Any]], lo: int, hi: int) -> Optional[Tuple[int, int]]:
    vals = [_vu(d) for d in data if lo <= _vu(d) <= hi]
    if not vals:
        return None
    return min(vals), max(vals)


def _combined_vu_span_for_labels(
    data: List[Dict[str, Any]],
    band_labels: List[str],
    load_bands: List[Tuple[str, int, int]],
) -> Tuple[int, int]:
    lo_mn, hi_mx = None, None
    for lab in band_labels:
        lo, hi = _band_lo_hi(lab, load_bands)
        if lo is None:
            continue
        obs = _observed_vu_bounds(data, lo, hi)
        a, b = obs if obs else (lo, hi)
        if lo_mn is None:
            lo_mn, hi_mx = int(a), int(b)
        else:
            lo_mn = min(lo_mn, int(a))
            hi_mx = max(hi_mx, int(b))
    if lo_mn is None:
        return 0, 0
    return lo_mn, hi_mx


def _zone_p99_over_span(data: List[Dict[str, Any]], vu_lo: int, vu_hi: int) -> float:
    et = [_elapsed_ms(d) for d in data if vu_lo <= _vu(d) <= vu_hi]
    if len(et) < 3:
        return 0.0
    return float(np.percentile(np.array(et, dtype=float), 99))


def _classify_band_letter(
    b: Dict[str, Any],
    prev: Optional[Dict[str, Any]],
    peak_tps_stable: float,
    sla_ms: float,
    err_gate: float,
) -> str:
    """Behaviour class for one populated VU bucket: A stable, B degrading, C high stress."""
    p90 = float(b.get("p90") or 0)
    er = float(b.get("err_pct") or 0)
    tps = float(b.get("avg_tps") or 0)
    if er >= err_gate or p90 >= sla_ms:
        return "C"
    if er >= err_gate * 0.55 or p90 >= sla_ms * 0.93:
        return "B"
    if prev:
        ptps = float(prev.get("avg_tps") or 0)
        if ptps > 0 and tps < ptps * 0.88 and p90 >= sla_ms * 0.82:
            return "B"
    if peak_tps_stable > 0 and tps < peak_tps_stable * 0.85 and p90 >= sla_ms * 0.75:
        return "B"
    return "A"


def _observed_vu_caption(mn: int, mx: int) -> str:
    if mn == mx:
        return f"{mn} VU"
    return f"{mn}–{mx} VU"


def _zone_title_observed(
    z: Dict[str, Any],
    band_labels: List[str],
    data: List[Dict[str, Any]],
    vu_lo: int,
    vu_hi: int,
    err_txt: str,
) -> str:
    obs = _observed_vu_bounds(data, vu_lo, vu_hi)
    vu_part = _observed_vu_caption(obs[0], obs[1]) if obs else "—"
    bl = ", ".join(band_labels)
    return (
        f"Observed {vu_part} in CSV · buckets {bl} · "
        f"Mean RT {z['mean_rt']:.0f}ms · P90 {z['p90']:.0f}ms · Error {err_txt}"
    )


def _zone_label_and_css(
    z: Dict[str, Any],
    sla_ms: float,
    err_gate: float,
    letter: str,
) -> Tuple[str, str]:
    """Strip label + CSS vs saved gates; A=green load, B=amber degrading, C=high stress."""
    p90, err = float(z["p90"]), float(z["err_pct"])
    if letter == "A":
        if p90 > sla_ms * 1.1 or err > err_gate * 1.5:
            return "Zone A · Stress in low-VU band", "critical"
        if p90 > sla_ms or err > err_gate:
            return "Zone A · Above SLO / error target", "warn"
        if p90 > sla_ms * 0.92 or err > err_gate * 0.85:
            return "Zone A · Approaching limits", "warn"
        return "Zone A · Stable — green load", "healthy"
    if letter == "B":
        if p90 > sla_ms * 1.35 or err > max(err_gate, 1.0) * 2.0:
            return "Zone B · Severe degradation (amber/red edge)", "critical"
        return "Zone B · Degrading (amber)", "warn"
    if letter == "C":
        if p90 < sla_ms * 0.95 and err < err_gate:
            return "Zone C · High concurrency (mixed metrics)", "warn"
        return "Zone C · High stress", "critical"
    return "Zone · Summary", "warn"


def _zones_intro_detailed(
    band_stats: List[Dict[str, Any]],
    lat_rows: List[Dict[str, Any]],
    data: List[Dict[str, Any]],
    max_vu: int,
    sla_ms: float,
    err_gate_pct: float,
    load_bands: List[Tuple[str, int, int]],
) -> List[Dict[str, str]]:
    """
    Three behaviour zones from this run's VU buckets (dynamic banding) vs saved P90 / error gates
    and throughput shape — not fixed 1–30 / 31–60 tiers.
    """
    populated = [b for b in band_stats if b.get("n")]
    if not populated:
        common = (
            "There are no populated concurrency bands in this run (no samples fell into a VU bucket), "
            "so load-correlated health cannot be derived from band aggregates. "
            "The three zones below remain visible for context; use minute-level charts and raw samples once load steps produce band-level data."
        )
        return [
            {
                "label": "Zone A · Stable — green load",
                "css": "warn",
                "title": "Zone A · No observed VU range",
                "body": common,
            },
            {
                "label": "Zone B · Degrading (amber)",
                "css": "warn",
                "title": "Zone B · No observed VU range",
                "body": common,
            },
            {
                "label": "Zone C · High stress",
                "css": "warn",
                "title": "Zone C · No observed VU range",
                "body": common,
            },
        ]

    classes: List[str] = []
    peak_a_tps = 0.0
    prev: Optional[Dict[str, Any]] = None
    for b in populated:
        letter = _classify_band_letter(b, prev, peak_a_tps, sla_ms, err_gate_pct)
        classes.append(letter)
        prev = b
        if letter == "A":
            peak_a_tps = max(peak_a_tps, float(b.get("avg_tps") or 0))

    ia = 0
    while ia < len(classes) and classes[ia] == "A":
        ia += 1
    ib = ia
    while ib < len(classes) and classes[ib] == "B":
        ib += 1

    a_bands = populated[:ia]
    b_bands = populated[ia:ib]
    c_bands = populated[ib:]

    tps_hi = float(populated[-1].get("avg_tps") or 0) if len(populated) >= 2 else 0.0
    tps_prev = float(populated[-2].get("avg_tps") or 0) if len(populated) >= 2 else 0.0
    z_a_for_compare = _zone_agg(band_stats, [x["label"] for x in a_bands]) if a_bands else None
    z_b_agg = _zone_agg(band_stats, [x["label"] for x in b_bands]) if b_bands else None

    zones: List[Dict[str, str]] = []

    def _emit_zone(letter: str, bands_slice: List[Dict[str, Any]], z_prior: Optional[Dict[str, Any]]) -> None:
        if not bands_slice:
            return
        z = _zone_agg(band_stats, [x["label"] for x in bands_slice])
        if not z:
            return
        bl = list(z.get("band_labels") or [])
        vu_lo, vu_hi = _combined_vu_span_for_labels(data, bl, load_bands)
        err_r = _err_range_from_bands(band_stats, bl)
        if err_r and abs(err_r[0] - err_r[1]) < 1e-9:
            er_txt = f"{err_r[0]:.1f}%"
        else:
            er_txt = f"{err_r[0]:.1f}–{err_r[1]:.1f}%" if err_r else f"{z['err_pct']:.1f}%"
        title = _zone_title_observed(z, bl, data, vu_lo, vu_hi, er_txt)
        mix = _vu_range_mix(data, vu_lo, vu_hi)
        p99z = _zone_p99_over_span(data, vu_lo, vu_hi)
        zlbl, zcss = _zone_label_and_css(z, sla_ms, err_gate_pct, letter)
        parts: List[str] = []
        if letter == "A":
            parts.append(
                "Green load in this segment: latency is contained relative to higher tiers, throughput generally tracks load, "
                "and error share is low versus your saved gates (see P90 / error targets in Target Values)."
            )
            if z["p90"] <= sla_ms + 1e-9:
                parts.append(
                    f"P90 {z['p90']:.0f} ms is at or below the {sla_ms:.0f} ms benchmark for this slice."
                )
            else:
                parts.append(
                    f"P90 {z['p90']:.0f} ms already exceeds the {sla_ms:.0f} ms benchmark — the usable green region may be narrower than nominal low VU."
                )
        elif letter == "B":
            parts.append(
                "Amber / degrading: slight or moderate drift on response time, errors, and/or throughput shape versus the stable slice — "
                "typical early saturation, queue growth, or dependency slowdown before hard failure rates dominate."
            )
            if z_prior and z_prior.get("mean_rt"):
                ratio_mean = z["mean_rt"] / z_prior["mean_rt"] if z_prior["mean_rt"] else 1.0
                if ratio_mean >= 1.2:
                    parts.append(
                        f"Mean RT ~{ratio_mean:.1f}× the stable slice ({z_prior['mean_rt']:.0f} → {z['mean_rt']:.0f} ms)."
                    )
        else:
            parts.append(
                "High stress (red): P90 and/or errors breach saved SLO gates and/or delivery (TPS) has rolled off — "
                "prioritize capacity, timeouts, and downstream reliability in this concurrency range."
            )
            if p99z > 30000:
                parts.append(f"P99 ~{p99z/1000:.1f}s — long-tail queueing or hard timeouts in raw samples.")
            if len(populated) >= 2 and tps_hi and tps_prev and tps_hi < tps_prev * 0.92:
                parts.append(
                    f"Throughput at the heaviest band is lower than the prior band (~{tps_prev:.1f} → {tps_hi:.1f} avg TPS) — negative scalability."
                )
        n504z = sum(
            1
            for d in data
            if vu_lo <= _vu(d) <= vu_hi and str(d.get("response_code") or "") == "504"
        )
        if n504z:
            parts.append(f"{n504z:,} HTTP 504 outcomes in this VU span — check gateways and upstream timeouts.")
        parts.append(_error_dominant_narrative(mix))
        parts.append(_tps_progression_in_zone(band_stats, bl))
        parts.append(_tcp_note_for_band_labels(lat_rows, bl))
        if p99z > z["mean_rt"] * 2.5 and p99z > 5000:
            parts.append(
                f"P99 ~{p99z/1000:.1f}s vs mean {z['mean_rt']:.0f} ms — tail drives perceived slowness."
            )
        zones.append({"label": zlbl, "css": zcss, "title": title, "body": " ".join(p for p in parts if p)})

    def _emit_zone_a_placeholder() -> None:
        """Always show Zone A; when no band classifies as A, explain the gap."""
        body = (
            "No concurrent-user band was classified as Zone A (stable / green). "
            "The lightest populated bucket may already exceed stable thresholds vs your saved gates, "
            "or the segmentation did not isolate a low-VU slice — review the lightest band in charts and Target Values."
        )
        zones.append(
            {
                "label": "Zone A · Stable — green load — not observed",
                "css": "warn",
                "title": "No observed VU range in Zone A · stable slice empty",
                "body": body,
            }
        )

    def _emit_zone_c_placeholder() -> None:
        """Always show Zone C; when no band classifies as C, explain the gap."""
        body = (
            "No concurrent-user band was classified as Zone C (high stress). "
            "Peak VU in this run may still sit within stable or degrading envelopes, the heaviest step did not breach stress rules used here, "
            "or the test ended before a distinct red slice formed — confirm against the top load band and error / P90 curves."
        )
        zones.append(
            {
                "label": "Zone C · High stress — not observed",
                "css": "warn",
                "title": "No observed VU range in Zone C · high-stress slice empty",
                "body": body,
            }
        )

    def _emit_zone_b_placeholder() -> None:
        """When no load band classifies as B, still show Zone B with an explicit narrative."""
        if b_bands:
            return
        if a_bands and c_bands:
            body = (
                "No concurrent-user band fell in the marginal (amber) tier for this run. "
                "Behaviour moved straight from Zone A (stable relative to gates) to Zone C (high stress) "
                "without an intermediate slice where only the softer degrading thresholds applied. "
                "That is expected when the first heavier band already breaches P90 or error gates used for Zone C, "
                "or when throughput shape alone would classify bands as stable until a sharp jump to stress."
            )
        elif a_bands and not c_bands:
            body = (
                "All populated load bands stayed in Zone A for this classification. "
                "There is no separate degrading slice up to the maximum VU exercised — "
                "either headroom remains before stress markers or the test did not extend into higher concurrency."
            )
        elif c_bands and not a_bands:
            body = (
                "Every populated band already satisfies Zone C (high stress) style gates from the lightest bucket onward. "
                "Zone B does not appear as a distinct range — there is no transitional “amber-only” slice in this dataset."
            )
        else:
            body = (
                "No bands could be placed in Zone B for this segmentation. "
                "See Zone A / Zone C (if present) for where samples landed."
            )
        zones.append(
            {
                "label": "Zone B · Degrading (amber) — not observed",
                "css": "warn",
                "title": "No observed VU range in Zone B · marginal tier empty",
                "body": body,
            }
        )

    if a_bands:
        _emit_zone("A", a_bands, None)
    else:
        _emit_zone_a_placeholder()
    if b_bands:
        _emit_zone("B", b_bands, z_a_for_compare)
    else:
        _emit_zone_b_placeholder()
    if c_bands:
        _emit_zone("C", c_bands, z_b_agg or z_a_for_compare)
    else:
        _emit_zone_c_placeholder()

    return zones


def _build_chart_observations(
    MINS: List[str],
    VUS: List[float],
    MEAN_RT: List[float],
    P90_RT: List[float],
    ERR_RT: List[float],
    TPS_ARR: List[float],
    band_stats: List[Dict[str, Any]],
    bar_percentiles: List[List[float]],
    heat_rows: List[Dict[str, Any]],
    apdex_by_band: List[float],
    max_vu: float,
    sla_ms: float,
    err_gate: float,
    err_rate_pct: float,
) -> Dict[str, str]:
    """Short interpretation strings for each major chart (what it shows + implication for SUT)."""
    out: Dict[str, str] = {}
    n = len(VUS)
    if n >= 3 and MEAN_RT and P90_RT:
        i1, i2 = n // 3, (2 * n) // 3
        v0, v1 = float(np.mean(VUS[:i1])), float(np.mean(VUS[i2:]))
        m0, m1 = float(np.mean(MEAN_RT[:i1])), float(np.mean(MEAN_RT[i2:]))
        p0, p1 = float(np.mean(P90_RT[:i1])), float(np.mean(P90_RT[i2:]))
        if v1 > v0 + 1:
            if m1 > m0 * 1.15 or p1 > sla_ms:
                out["rt_main"] = (
                    f"As concurrency rises from ~{v0:.0f} to ~{v1:.0f} VU (early vs late thirds of the timeline), "
                    f"mean RT moves ~{m0:.0f} → {m1:.0f} ms and P90 ~{p0:.0f} → {p1:.0f} ms — "
                    "the system is latency-sensitive to load; expect user-visible stretch under similar traffic."
                )
            else:
                out["rt_main"] = (
                    f"Mean/P90 RT stay relatively flat while VU increases (~{v0:.0f} → ~{v1:.0f}) — "
                    "good headroom in this window, subject to error and tail checks in other charts."
                )
        else:
            out["rt_main"] = "Concurrency is fairly flat across the timeline — use load-band charts to see RT vs VU rather than clock time."
    else:
        out["rt_main"] = "Insufficient timeline points — rely on load-band percentile and zone panels for RT vs concurrency."

    pop_b = [b for b in band_stats if b.get("n")]
    if len(pop_b) >= 2 and bar_percentiles:
        widen = 0
        for row in bar_percentiles:
            if len(row) >= 4 and row[0] > 0 and row[3] > row[0] * 2:
                widen += 1
        if widen >= len([x for x in bar_percentiles if x and x != [0, 0, 0, 0]]) // 2:
            out["rt_percentile"] = (
                "P90/P95 spread grows vs median in upper load bands — distribution fat-tails: a minority of requests drives worst UX even if mean looks acceptable."
            )
        else:
            out["rt_percentile"] = (
                "Median through P95 stay in a moderate band across load buckets — less evidence of explosive tail within-band (still verify P99 / errors)."
            )
    else:
        out["rt_percentile"] = "Compare median, P75, P90, P95 across dynamic VU buckets; widening upper percentiles under load usually signals queueing or contention."

    if apdex_by_band and len(apdex_by_band) == len(pop_b):
        lo_a, hi_a = float(apdex_by_band[0]), float(apdex_by_band[-1])
        if hi_a < lo_a - 0.08:
            out["ttfb"] = (
                "Apdex falls in heavier VU buckets while TTFB/stacked elapsed grows — user-perceived quality erodes with load (frustration / abandonment risk)."
            )
        else:
            out["ttfb"] = (
                "TTFB vs remainder by band shows where time sits: large TTFB share implies network/server first-byte delay; large remainder implies app/processing after first byte."
            )
    else:
        out["ttfb"] = "Stacked bars separate first-byte wait from post-TTFB work — imbalance helps decide CDN/TLS/gateway tuning vs application logic."

    if heat_rows and len(heat_rows) >= 2:
        out["heatmap"] = (
            "Each column is a latency bucket; each row is a dynamic load band. If probability mass shifts right as you move down rows, "
            "the SUT delivers slower responses at higher concurrency — classic capacity or lock contention signature."
        )
    else:
        out["heatmap"] = "Heatmap relates response-time distribution shape to load; rightward shift under load is the usual stress signal."

    out["lat_decomp"] = (
        "TCP connect and TTFB medians vs total elapsed show whether delay is path/network vs server think-time; rising TTFB P90 with flat connect hints back-end queueing."
    )

    if n >= 2 and TPS_ARR and VUS:
        t0, t1 = float(np.mean(TPS_ARR[: n // 3])), float(np.mean(TPS_ARR[-n // 3 :]))
        if t1 > t0 * 1.05:
            out["tps_main"] = "TPS rises with wall-clock phases where VU ramps — useful validation that the workload generator and SUT are exchanging more work over time."
        elif t1 < t0 * 0.9:
            out["tps_main"] = "TPS falls in later timeline thirds while stress continues — possible client/saturation or error-induced slowdown of successful throughput."
        else:
            out["tps_main"] = "TPS vs VU shows effective delivery rate per minute; flat lines under rising VU can mean queuing (same TPS, longer queues)."
    else:
        out["tps_main"] = "TPS vs concurrent users indicates how much useful work completes per second at each load level."

    if len(pop_b) >= 2:
        tps0, tps1 = float(pop_b[0].get("avg_tps") or 0), float(pop_b[-1].get("avg_tps") or 0)
        if tps0 > 0 and tps1 < tps0 * 0.9:
            out["tps_band"] = (
                "Average TPS drops from lowest to highest dynamic load band — capacity ceiling or error-driven loss of goodput."
            )
        else:
            out["tps_band"] = "TPS by band should ideally hold or rise with VU; dips mean less completed work per second at higher nominal load."
    else:
        out["tps_band"] = "Band-level TPS summarises throughput inside each observed VU window."

    out["bw"] = "Receive/transmit volume by band helps spot payload bloat or chatty APIs that correlate with latency under load."

    if n >= 3 and ERR_RT and MEAN_RT and len(ERR_RT) == len(MEAN_RT):
        try:
            a = np.asarray(ERR_RT, dtype=float)
            b = np.asarray(MEAN_RT, dtype=float)
            if np.std(a) > 1e-12 and np.std(b) > 1e-12:
                cx = float(np.corrcoef(a, b)[0, 1])
            else:
                cx = 0.0
        except (FloatingPointError, ValueError):
            cx = 0.0
        if cx > 0.4:
            out["err_corr"] = (
                "Error rate and mean RT move together across minutes — failures and slowness are coupled (timeouts, retries, or shared bottleneck)."
            )
        else:
            out["err_corr"] = (
                "Error rate vs mean RT scatter: weak coupling can mean errors are bursty (gates, auth) while RT is driven by happy-path saturation — triage separately."
            )
    else:
        out["err_corr"] = "This view links minute error share to mean latency — upward joint trend usually indicates stress collapse."

    if pop_b:
        er_last = float(pop_b[-1].get("err_pct") or 0)
        if er_last > err_gate:
            out["err_band"] = f"Heaviest dynamic band shows {er_last:.1f}% errors vs {err_gate:.2f}% target — failure mix by row clarifies 4xx vs 5xx drivers."
        else:
            out["err_band"] = "Error composition by band shows whether client (4xx) vs server (5xx) issues dominate as load increases."
    else:
        out["err_band"] = "4xx/5xx/connection anomalies by load band localise where the SUT starts returning bad outcomes."

    out["score_donut"] = (
        "Share of transactions rated critical / warning / healthy — a concentration in critical at end of test usually blocks release until those controllers are fixed."
    )
    out["apdex_band"] = (
        "Apdex by dynamic load band (T=3s): sustained drops in heavier bands mean more users perceive slow or failing responses under peak-shaped load."
    )
    out["tx_percentile"] = (
        "Per-transaction elapsed percentiles summarise behaviour across the full test window; "
        "VU-band grade columns score each controller within that concurrency range only (same model as the main scorecard). "
        "Wide P95–P99 vs median on critical flows usually justifies drill-down in the sample-level charts."
    )

    return out


def _build_key_events_timeline(
    minute_map: Dict[str, List[Dict[str, Any]]],
    MINS: List[str],
    VUS: List[float],
    MEAN_RT: List[float],
    P90_RT: List[float],
    ERR_RT: List[float],
    TPS_ARR: List[float],
    tz_label: str,
    max_vu: int,
    sla_ms: float,
) -> List[Dict[str, str]]:
    """Derive ~10 milestone events from minute buckets (baseline-style narrative)."""
    n = len(MINS)
    if n == 0:
        return []

    events: List[Tuple[int, str, str, str, str]] = []

    def push(ord_i: int, dot: str, time_s: str, title: str, body: str) -> None:
        events.append((ord_i, dot, time_s, title, body))

    # 1 — test start
    rows0 = minute_map.get(MINS[0], [])
    f0 = sum(1 for r in rows0 if is_jmeter_error_outcome(r))
    push(
        10,
        "green",
        f"{MINS[0]} {tz_label} · {int(VUS[0])} VU",
        "Test initiated — first minute",
        f"{len(rows0):,} samples; mean RT {MEAN_RT[0]:.0f} ms; P90 {P90_RT[0]:.0f} ms; "
        f"{f0} failures ({ERR_RT[0]:.2f}% error rate).",
    )

    # 2 — first failures
    for i in range(n):
        if ERR_RT[i] <= 0:
            continue
        rows = minute_map.get(MINS[i], [])
        fails = [r for r in rows if is_jmeter_error_outcome(r)]
        n504 = sum(1 for r in fails if str(r.get("response_code") or "") == "504")
        n404 = sum(1 for r in fails if str(r.get("response_code") or "").startswith("4"))
        dom = "504-heavy" if n504 > len(fails) * 0.4 else "4xx-heavy" if n404 > len(fails) * 0.4 else "mixed codes"
        push(
            20 + i,
            "amber",
            f"{MINS[i]} {tz_label} · {int(VUS[i])} VU",
            "First minute with failed requests",
            f"{len(fails)} failures / {len(rows):,} samples ({ERR_RT[i]:.2f}%). Dominant signature: {dom} "
            f"(504:{n504}, 4xx:{n404}). Mean RT {MEAN_RT[i]:.0f} ms.",
        )
        break

    # 3 — first 504 minute
    for i in range(n):
        rows = minute_map.get(MINS[i], [])
        c504 = sum(1 for r in rows if str(r.get("response_code") or "") == "504")
        if c504 == 0:
            continue
        push(
            30 + i,
            "amber",
            f"{MINS[i]} {tz_label} · {int(VUS[i])} VU",
            "First HTTP 504 / gateway timeouts",
            f"{c504} responses returned 504 in this minute ({len(rows):,} samples). "
            f"Usually aligns with upstream queues or exhausted worker pools.",
        )
        break

    # 3b — first NoHttp / connection-drop minute
    for i in range(n):
        rows = minute_map.get(MINS[i], [])
        cnhr = sum(
            1
            for r in rows
            if "nohttp" in str(r.get("response_message", "")).lower()
            or "no http" in str(r.get("failure_message", "")).lower()
        )
        if cnhr == 0:
            continue
        push(
            35 + i,
            "amber",
            f"{MINS[i]} {tz_label} · {int(VUS[i])} VU",
            "Connection anomalies (NoHttp heuristic)",
            f"{cnhr} samples classified as NoHttp / abrupt TCP close in this minute ({len(rows):,} samples).",
        )
        break

    # 4 — longest low-error / SLA-stable window
    best_len, best_a, best_b = 0, 0, -1
    run_s: Optional[int] = None
    cur_e = -1
    for i in range(n):
        ok = ERR_RT[i] < 2.85 and P90_RT[i] < sla_ms * 1.18
        if ok:
            if run_s is None:
                run_s = i
            cur_e = i
        else:
            if run_s is not None and cur_e >= run_s:
                ln = cur_e - run_s + 1
                if ln > best_len:
                    best_len, best_a, best_b = ln, run_s, cur_e
            run_s = None
    if run_s is not None and cur_e >= run_s:
        ln = cur_e - run_s + 1
        if ln > best_len:
            best_len, best_a, best_b = ln, run_s, cur_e
    if best_len >= 3:
        a, b = best_a, best_b
        vm = int(round(float(np.mean(VUS[a : b + 1]))))
        p90_lo, p90_hi = min(P90_RT[a : b + 1]), max(P90_RT[a : b + 1])
        tp_lo, tp_hi = min(TPS_ARR[a : b + 1]), max(TPS_ARR[a : b + 1])
        er_lo, er_hi = min(ERR_RT[a : b + 1]), max(ERR_RT[a : b + 1])
        push(
            40,
            "green" if best_len >= 5 else "amber",
            f"{MINS[a]}–{MINS[b]} {tz_label} · ~{vm} VU",
            f"Comparatively stable window ({best_len} minutes)",
            f"P90 {p90_lo:.0f}–{p90_hi:.0f} ms vs {sla_ms:.0f} ms benchmark; errors {er_lo:.2f}–{er_hi:.2f}%; "
            f"per-minute TPS buckets {tp_lo:.1f}–{tp_hi:.1f}.",
        )

    # 5 — latency inflection on ramp
    for i in range(1, n):
        if VUS[i] + 1e-6 >= VUS[i - 1] and MEAN_RT[i] > max(300.0, MEAN_RT[i - 1] * 1.45):
            push(
                50 + i,
                "amber",
                f"{MINS[i]} {tz_label} · {int(VUS[i])} VU",
                "Latency inflection under increasing load",
                f"Mean RT {MEAN_RT[i-1]:.0f} → {MEAN_RT[i]:.0f} ms while VU {int(VUS[i-1])} → {int(VUS[i])}. "
                f"P90 {P90_RT[i]:.0f} ms; errors {ERR_RT[i]:.2f}%.",
            )
            break

    # 6 — breach 3% error minute
    for i in range(n):
        if ERR_RT[i] < 3.0:
            continue
        rows = minute_map.get(MINS[i], [])
        fails = sum(1 for r in rows if is_jmeter_error_outcome(r))
        push(
            60 + i,
            "red",
            f"{MINS[i]} {tz_label} · {int(VUS[i])} VU",
            "High error-rate minute (≥3%)",
            f"{fails} failures / {len(rows):,} samples ({ERR_RT[i]:.2f}%). Mean RT {MEAN_RT[i]:.0f} ms; P90 {P90_RT[i]:.0f} ms.",
        )
        break

    # 7 — strongest 504 surge
    best504, idx504 = 0, -1
    for i in range(n):
        rows = minute_map.get(MINS[i], [])
        c504 = sum(1 for r in rows if str(r.get("response_code") or "") == "504")
        if c504 > best504:
            best504, idx504 = c504, i
    if best504 >= 2 and idx504 >= 0:
        rows = minute_map.get(MINS[idx504], [])
        push(
            70 + idx504,
            "red",
            f"{MINS[idx504]} {tz_label} · {int(VUS[idx504])} VU",
            "504 surge minute",
            f"{best504} gateway timeouts in 60s ({len(rows):,} samples) — strongest 504 concentration in the run.",
        )

    # 8 — approach / hold peak VU
    target_peak = max(1, int(max_vu * 0.97))
    for i in range(n):
        if VUS[i] < target_peak:
            continue
        j = i
        while j + 1 < n and VUS[j + 1] >= target_peak * 0.95:
            j += 1
        if j > i:
            vmax_hold = int(max(VUS[k] for k in range(i, j + 1)))
            push(
                80 + i,
                "amber",
                f"{MINS[i]}–{MINS[j]} {tz_label} · {vmax_hold} VU",
                "Peak concurrent users sustained",
                f"VU holds near test maximum (~{max_vu}) for {j - i + 1} minutes. "
                f"Mean RT {MEAN_RT[j]:.0f} ms at tail; TPS bucket {TPS_ARR[j]:.1f}; errors {ERR_RT[j]:.2f}%.",
            )
        else:
            push(
                80 + i,
                "amber",
                f"{MINS[i]} {tz_label} · {int(VUS[i])} VU",
                "Peak concurrent users reached",
                f"Minute hits ~{max_vu} VU. Mean RT {MEAN_RT[i]:.0f} ms; P90 {P90_RT[i]:.0f} ms; "
                f"TPS bucket {TPS_ARR[i]:.1f}; errors {ERR_RT[i]:.2f}%.",
            )
        break

    # 9 — worst minute overall
    wi = int(np.argmax(np.array(ERR_RT, dtype=float)))
    if ERR_RT[wi] > 0.05:
        rows = minute_map.get(MINS[wi], [])
        fails = sum(1 for r in rows if is_jmeter_error_outcome(r))
        n5 = sum(1 for r in rows if str(r.get("response_code") or "").startswith("5"))
        push(
            90 + wi,
            "red",
            f"{MINS[wi]} {tz_label} · {int(VUS[wi])} VU — worst error minute",
            f"Peak observed error rate {ERR_RT[wi]:.2f}%",
            f"{fails} failures / {len(rows):,} samples (≈{n5} 5xx-class outcomes). Mean RT {MEAN_RT[wi]:.0f} ms; P90 {P90_RT[wi]:.0f} ms.",
        )

    # 10 — ramp-down recovery
    wi_worst = int(np.argmax(np.array(ERR_RT, dtype=float)))
    peak_err = float(ERR_RT[wi_worst]) if n else 0.0
    if (
        n >= 5
        and VUS[-1] < VUS[-4] * 0.78
        and peak_err > 0.15
        and ERR_RT[-1] < min(peak_err * 0.62, max(0.05, ERR_RT[-4] * 0.85))
    ):
        push(
            200,
            "green",
            f"{MINS[-4]}–{MINS[-1]} {tz_label} · ramp-down",
            "Load reduced — errors/latency ease",
            f"VU {int(VUS[-4])} → {int(VUS[-1])}; error rate {ERR_RT[-4]:.2f}% → {ERR_RT[-1]:.2f}%; "
            f"mean RT {MEAN_RT[-4]:.0f} → {MEAN_RT[-1]:.0f} ms — recovery once load is shed.",
        )

    # 11 — closing snapshot (baseline-style bookend)
    rows_last = minute_map.get(MINS[-1], [])
    push(
        260 + n,
        "amber" if ERR_RT[-1] >= 1.0 else "green",
        f"{MINS[-1]} {tz_label} · {int(VUS[-1])} VU",
        "Last minute in dataset",
        f"{len(rows_last):,} samples; mean RT {MEAN_RT[-1]:.0f} ms; P90 {P90_RT[-1]:.0f} ms; "
        f"errors {ERR_RT[-1]:.2f}% (end of analyzed window).",
    )

    events.sort(key=lambda x: x[0])
    out: List[Dict[str, str]] = []
    seen_titles = set()
    for _, dot, tim, tit, bod in events:
        if tit in seen_titles:
            continue
        seen_titles.add(tit)
        out.append({"dot": dot, "time": tim, "title": tit, "body": bod})
        if len(out) >= 14:
            break
    return out

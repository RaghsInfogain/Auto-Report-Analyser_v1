"""
Weighted performance grading for A/B comparison reports (T2 candidate).
Mirrors JMeterAnalyzerV2._calculate_scores / _calculate_grade (30/25/25/20 pillars).
Release labels match the scorecard methodology (combined load / JMeter grade scale).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from analyser.decisions import SLAConfig


def _score_metric(value: float, target: float, higher_better: bool) -> float:
    if higher_better:
        return min(100.0, max(0.0, (value / target) * 100.0)) if target > 0 else 0.0
    if value <= 0:
        return 100.0
    if target <= 0:
        return 0.0
    return min(100.0, max(0.0, (target / value) * 100.0))


def _tx_sla_compliance_pct(tx2: pd.DataFrame) -> float:
    if tx2 is None or len(tx2) == 0:
        return 100.0
    if "sla_pass" in tx2.columns:
        return 100.0 * float(tx2["sla_pass"].sum()) / float(len(tx2))
    if "sla_t2" in tx2.columns:
        return 100.0 * float((tx2["sla_t2"].astype(str).isin(("True", "true", "1"))).sum()) / float(
            len(tx2)
        )
    return 85.0


# Letter grade from overall score (0–100) → release headline + header pill colour.
# Score bands must stay in sync with _calculate_grade().
RELEASE_DECISION_BY_GRADE: Dict[str, Tuple[str, str]] = {
    "A+": ("Immediate Release Approved", "green"),
    "A": ("Release with Monitoring", "amber"),
    "B+": ("Conditional Release…", "amber"),
    "B": ("Release Only with Business Sign-Off", "red"),
    "C+": ("Release Not Recommended", "red"),
    "C": ("Release Blocked - Critical Issues", "red"),
    "D": ("Release Blocked (Go-Live Stopper)", "red"),
    "F": ("PRODUCTION BLOCKER", "red"),
}


def release_decision_from_grade(grade: str) -> Dict[str, str]:
    """
    JMeter comparison report header: release decision from overall letter grade.
    pill_class: green | amber | red (matches scorecard).
    """
    g = str(grade or "").strip().upper().replace(" ", "")
    if g in ("N/A", "—", "", "NA"):
        g = "C+"
    label, pill = RELEASE_DECISION_BY_GRADE.get(g, RELEASE_DECISION_BY_GRADE["B+"])
    emoji = {"A+": "🟢", "A": "🟢", "B+": "🟡", "B": "🟠"}.get(g, "🔴" if pill == "red" else "🟡")
    return {
        "release_header_label": label,
        "release_header_pill_class": pill,
        "release_title_emoji": emoji,
    }


def _grading_hard_veto(k2: dict, sla: SLAConfig) -> bool:
    """
    Override to NO-GO only for clearly unacceptable run-wide error rate.
    (Does not use per-transaction P90 heuristics — those belong in narrative, not automatic NO-GO at grade B.)
    """
    er = float(k2.get("error_rate_pct") or 0)
    return er > max(10.0, float(sla.sla_error) * 4.0)


def compute_comparison_grading(
    k2: dict,
    tx2: pd.DataFrame,
    tx_m: Optional[pd.DataFrame],
    tp2: dict,
    sla: SLAConfig,
) -> Dict[str, Any]:
    """Return overall score, letter grade, pillar scores, and release verdict (GO / CONDITIONAL / NO_GO)."""
    success_rate = float(100.0 - float(k2.get("error_rate_pct") or 0))
    error_dec = float(k2.get("error_rate_pct") or 0) / 100.0
    avg_s = float(k2.get("mean_rt") or 0) / 1000.0
    p95_s = float(k2.get("p95_rt") or 0) / 1000.0
    tp = float(k2.get("overall_tps") or 0)
    sla_comp = _tx_sla_compliance_pct(tx2)

    t_avail = float(getattr(sla, "availability_target", 99.0))
    t_avg = float(getattr(sla, "sla_mean_rt_ms", 2000.0)) / 1000.0
    t_err = float(sla.sla_error) / 100.0
    t_tp = float(getattr(sla, "throughput_target", 100.0))
    t_p95 = float(sla.sla_p95) / 1000.0
    t_sla = float(getattr(sla, "sla_compliance_target", 95.0))

    availability_score = _score_metric(success_rate, t_avail, True)
    response_time_score = _score_metric(avg_s, t_avg, False)
    error_rate_score = _score_metric(error_dec, t_err, False)
    throughput_score = _score_metric(tp, t_tp, True)
    p95_score = _score_metric(p95_s, t_p95, False)
    sla_score = _score_metric(sla_comp, t_sla, True)

    performance_score = (response_time_score + p95_score) / 2.0
    reliability_score = (availability_score + error_rate_score) / 2.0
    ux_score = sla_score
    scalability_score = throughput_score
    sc_type = str((tp2 or {}).get("scalability_type") or "")
    if sc_type == "negative":
        scalability_score = min(scalability_score, max(0.0, scalability_score * 0.75))
    elif sc_type == "plateau" and (tp2 or {}).get("collapse_detected"):
        scalability_score = min(scalability_score, max(0.0, scalability_score * 0.88))

    overall = (
        performance_score * 0.30
        + reliability_score * 0.25
        + ux_score * 0.25
        + scalability_score * 0.20
    )

    grade, grade_class = _calculate_grade(overall)
    hard_veto = _grading_hard_veto(k2, sla)
    verdict = _grade_to_verdict(grade, hard_veto)

    hdr = release_decision_from_grade(grade)
    if hard_veto and verdict == "NO_GO":
        # Letter grade can stay high if errors alone breach the hard gate — header matches F-tier wording.
        hdr = {
            "release_header_label": RELEASE_DECISION_BY_GRADE["F"][0],
            "release_header_pill_class": RELEASE_DECISION_BY_GRADE["F"][1],
            "release_title_emoji": "🔴",
        }

    detail = (
        f"Release decision from scoring & grading: grade {grade} ({overall:.1f}/100). "
        f"Pillars vs targets — performance {performance_score:.0f}, reliability {reliability_score:.0f}, "
        f"user experience {ux_score:.0f} (SLA pass mix), scalability {scalability_score:.0f}."
    )
    if hard_veto and verdict == "NO_GO":
        detail += (
            f" Run-wide error rate {float(k2.get('error_rate_pct') or 0):.2f}% exceeds the hard veto "
            f"threshold (max(10%, 4× SLA error target)) — treated as NO-GO regardless of letter grade."
        )

    out: Dict[str, Any] = {
        "overall_score": round(overall, 1),
        "grade": grade,
        "grade_class": grade_class,
        "pillars": {
            "performance": round(performance_score, 1),
            "reliability": round(reliability_score, 1),
            "user_experience": round(ux_score, 1),
            "scalability": round(scalability_score, 1),
        },
        "raw_category_scores": {
            "availability": round(availability_score, 1),
            "response_time": round(response_time_score, 1),
            "error_rate": round(error_rate_score, 1),
            "throughput": round(throughput_score, 1),
            "p95_percentile": round(p95_score, 1),
            "sla_compliance": round(sla_score, 1),
        },
        "verdict": verdict,
        "grading_detail": detail,
        "hard_gate_triggered": bool(hard_veto),
    }
    out.update(hdr)
    return out


def _calculate_grade(score: float) -> Tuple[str, str]:
    if score >= 90:
        return "A+", "success"
    if score >= 80:
        return "A", "success"
    if score >= 75:
        return "B+", "warning"
    if score >= 70:
        return "B", "warning"
    if score >= 65:
        return "C+", "warning"
    if score >= 60:
        return "C", "warning"
    if score >= 50:
        return "D", "danger"
    return "F", "danger"


def _grade_to_verdict(grade: str, hard_veto: bool) -> str:
    """
    Three-state verdict driven primarily by letter grade.
    B (e.g. score 70) → CONDITIONAL, not NO-GO. C and below → NO-GO unless only C+ remains conditional.
    """
    if hard_veto:
        return "NO_GO"
    if grade in ("A+", "A"):
        return "GO"
    if grade in ("B+", "B", "C+"):
        return "CONDITIONAL"
    return "NO_GO"


def apply_grading_to_go_nogo(gng: Dict[str, Any], grading: Dict[str, Any], kpis: dict, sla: SLAConfig) -> Dict[str, Any]:
    """Mutate a copy of go/nogo: primary verdict from grading; keep weighted gate checklist for reference."""
    out = dict(gng)
    out["verdict"] = grading.get("verdict") or out.get("verdict")
    out["grading"] = grading
    out["weighted_gate_score_pct"] = out.get("score")
    base_just = str(out.get("justification") or "").strip()
    lead = str(grading.get("grading_detail") or "")
    if lead:
        if base_just and base_just not in lead:
            out["justification"] = lead + " " + base_just
        else:
            out["justification"] = lead if not base_just else base_just
    out["score"] = grading.get("overall_score", out.get("score"))
    return out

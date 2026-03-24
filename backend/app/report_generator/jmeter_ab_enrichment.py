"""
Enrichment payload for JMeter A/B HTML report: grades, charts, phased plan, executive cards, issues.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.analyzers.jmeter_analyzer_v2 import JMeterAnalyzerV2


def _sla_under_ms(records: List[Dict[str, Any]], ms: float) -> float:
    if not records:
        return 0.0
    ok = sum(1 for d in records if float(d.get("sample_time") or 0) < ms)
    return round(100.0 * ok / len(records), 2)


def _arrow_for_change(
    pct: Optional[float], lower_is_better: bool, eps: float = 0.5
) -> Tuple[str, str]:
    """Unicode arrow + short label for candidate vs baseline."""
    if pct is None:
        return "→", "N/A"
    if abs(pct) < eps:
        return "→", "Stable"
    if lower_is_better:
        if pct > 0:
            return "↑", "Degradation"
        return "↓", "Improvement"
    if pct > 0:
        return "↓", "Improvement"
    return "↑", "Degradation"


def _error_direction(ka: Dict, kb: Dict) -> Tuple[str, float]:
    a = float(ka.get("error_pct") or 0)
    b = float(kb.get("error_pct") or 0)
    d = round(b - a, 4)
    if abs(d) < 0.02:
        return "constant", d
    if d > 0:
        return "increased", d
    return "decreased", d


def _label_stats_for_phased(per_label: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for k, v in per_label.items():
        out[k] = {"avg_response": v.get("avg_ms", 0), "p95": v.get("p95_ms", 0)}
    return out


def _scores_from_kpis(kpi: Dict[str, Any], records: List[Dict[str, Any]]) -> Dict[str, Any]:
    st = kpi.get("sample_time") or {}
    err = float(kpi.get("error_pct") or 0)
    success_rate = 100.0 - err
    avg_sec = float(st.get("mean") or 0) / 1000.0
    p95_sec = float(st.get("p95") or 0) / 1000.0
    tput = float(kpi.get("throughput_rps") or 0)
    sla = _sla_under_ms(records, 2000.0)
    targets = JMeterAnalyzerV2._resolve_score_targets(None)
    scores = JMeterAnalyzerV2._calculate_scores(
        success_rate, err / 100.0, avg_sec, p95_sec, tput, sla, targets
    )
    grade, gcls = JMeterAnalyzerV2._calculate_grade(scores["overall"])
    return {"scores": scores, "grade": grade, "grade_class": gcls, "sla_2s_pct": sla}


def extend_jmeter_ab_analysis(
    analysis: Dict[str, Any],
    records_a: List[Dict[str, Any]],
    records_b: List[Dict[str, Any]],
    la: Dict[str, Dict[str, Any]],
    lb: Dict[str, Dict[str, Any]],
    buckets_a: List[Dict[str, Any]],
    buckets_b: List[Dict[str, Any]],
    name_a: str,
    name_b: str,
) -> Dict[str, Any]:
    ka = analysis["test_a"]["kpis"]
    kb = analysis["test_b"]["kpis"]
    pct = analysis.get("kpi_percent_change") or {}
    exec_s = analysis.get("executive_summary") or {}

    sa = _scores_from_kpis(ka, records_a)
    sb = _scores_from_kpis(kb, records_b)
    d_overall = round(sb["scores"]["overall"] - sa["scores"]["overall"], 2)

    def dim_row(key: str, label: str):
        va, vb = sa["scores"][key], sb["scores"][key]
        ga, _ = JMeterAnalyzerV2._calculate_grade(va)
        gb, _ = JMeterAnalyzerV2._calculate_grade(vb)
        return {
            "key": key,
            "label": label,
            "score_a": va,
            "score_b": vb,
            "grade_a": ga,
            "grade_b": gb,
            "delta": round(vb - va, 2),
        }

    dimensions = [
        dim_row("performance", "Performance"),
        dim_row("reliability", "Reliability"),
        dim_row("user_experience", "User experience"),
        dim_row("scalability", "Scalability"),
    ]

    p95_c, p99_c, tput_c = pct.get("p95_ms"), pct.get("p99_ms"), pct.get("throughput_rps")
    err_dir, err_pp = _error_direction(ka, kb)
    a95, a99 = _arrow_for_change(p95_c, True), _arrow_for_change(p99_c, True)
    a_tp = _arrow_for_change(tput_c, False)

    targets_disp = JMeterAnalyzerV2._resolve_display_targets(None)

    executive_cards = [
        {
            "title": "P95 latency",
            "arrow": a95[0],
            "trend": a95[1],
            "value": f"{p95_c:+.1f}%" if p95_c is not None else "—",
            "detail": f"Baseline {ka['sample_time']['p95']:.0f} ms → Candidate {kb['sample_time']['p95']:.0f} ms",
        },
        {
            "title": "P99 latency",
            "arrow": a99[0],
            "trend": a99[1],
            "value": f"{p99_c:+.1f}%" if p99_c is not None else "—",
            "detail": f"Baseline {ka['sample_time']['p99']:.0f} ms → Candidate {kb['sample_time']['p99']:.0f} ms",
        },
        {
            "title": "Error rate",
            "arrow": "↑" if err_dir == "increased" else ("↓" if err_dir == "decreased" else "→"),
            "trend": err_dir.capitalize(),
            "value": f"{ka['error_pct']:.3f}% → {kb['error_pct']:.3f}%",
            "detail": f"Change vs baseline: {err_pp:+.3f} pp ({err_dir})",
        },
        {
            "title": "Throughput",
            "arrow": a_tp[0],
            "trend": a_tp[1],
            "value": f"{tput_c:+.1f}%" if tput_c is not None else "—",
            "detail": f"{ka['throughput_rps']:.1f} → {kb['throughput_rps']:.1f} req/s",
        },
    ]

    sla_a = sa["sla_2s_pct"]
    sla_b = sb["sla_2s_pct"]
    key_findings = [
        (
            f"Response time: baseline avg {ka['sample_time']['mean']:.0f} ms; candidate {kb['sample_time']['mean']:.0f} ms "
            f"({pct.get('avg_ms'):+.1f}% vs baseline)."
            if pct.get("avg_ms") is not None
            else f"Response time: baseline avg {ka['sample_time']['mean']:.0f} ms; candidate {kb['sample_time']['mean']:.0f} ms."
        ),
        f"Error rate: {ka['error_pct']:.3f}% (baseline) vs {kb['error_pct']:.3f}% (candidate) — {err_dir}.",
        (
            f"Throughput: {ka['throughput_rps']:.1f} vs {kb['throughput_rps']:.1f} req/s ({tput_c:+.1f}% change)."
            if tput_c is not None
            else f"Throughput: {ka['throughput_rps']:.1f} vs {kb['throughput_rps']:.1f} req/s."
        ),
        f"SLA compliance (<2s): baseline {sla_a:.1f}%, candidate {sla_b:.1f}%.",
        f"Success rate: {100 - ka['error_pct']:.2f}% (baseline) vs {100 - kb['error_pct']:.2f}% (candidate).",
    ]

    verdict = exec_s.get("verdict", "")
    business_release = {
        "release_decision": verdict,
        "recommendation": exec_s.get("recommendation", ""),
        "customer_impact": (
            "Higher tail latency or errors in the candidate can increase abandonment and support load."
            if exec_s.get("traffic_signal") in ("red", "amber")
            else "Candidate aligns with baseline expectations for latency and reliability under tested load."
        ),
        "business_outcomes": (
            "Revenue and NPS at risk if regressions reach production without mitigation."
            if exec_s.get("traffic_signal") == "red"
            else "Controlled rollout with monitoring is viable if business accepts residual risk."
            if exec_s.get("traffic_signal") == "amber"
            else "Release window can proceed with standard monitoring."
        ),
        "recommended_actions": (exec_s.get("risks") or [])[:5] or ["Continue monitoring in pre-production."],
        "technical_indicators": [
            f"P95 delta {p95_c:+.1f}%" if p95_c is not None else "P95 delta n/a",
            f"Error rate {err_dir} ({err_pp:+.3f} pp)",
            f"Overall score {sa['scores']['overall']:.1f} → {sb['scores']['overall']:.1f} ({d_overall:+.1f})",
        ],
    }

    skew_a = ka["sample_time"].get("skewness", 0)
    skew_b = kb["sample_time"].get("skewness", 0)
    via = analysis["test_a"].get("variability_index")
    vib = analysis["test_b"].get("variability_index")
    distribution_deep = {
        "observations": analysis.get("observations") or [],
        "interpretations": [
            f"Baseline skewness {skew_a:.2f} vs candidate {skew_b:.2f} — "
            f"{'heavier tail on candidate' if skew_b > skew_a + 0.2 else 'similar or improved tail shape'}.",
            f"Variability index (P99/P50): {via} vs {vib}." if via and vib else "Variability index computed per test.",
        ],
        "root_causes": [b.get("type", "") + ": " + b.get("evidence", "") for b in (analysis.get("bottlenecks") or [])[:6]],
        "business_impact": business_release["business_outcomes"],
    }

    def _status_for_b(metric: str, val_b: float, target: float, lower_better: bool) -> str:
        if lower_better:
            if val_b <= target:
                return "Met"
            if val_b <= target * 1.15:
                return "Marginal"
            return "Miss"
        if val_b >= target:
            return "Met"
        if val_b >= target * 0.85:
            return "Marginal"
        return "Miss"

    avail_a = 100.0 - ka["error_pct"]
    avail_b = 100.0 - kb["error_pct"]
    detailed_rows = [
        {
            "metric": "Availability / success",
            "baseline": f"{avail_a:.2f}%",
            "candidate": f"{avail_b:.2f}%",
            "target": f"≥ {targets_disp['availability']:.0f}%",
            "status": _status_for_b("av", avail_b, targets_disp["availability"], False),
            "score_a": sa["scores"]["availability"],
            "score_b": sb["scores"]["availability"],
        },
        {
            "metric": "Avg response time",
            "baseline": f"{ka['sample_time']['mean']:.0f} ms",
            "candidate": f"{kb['sample_time']['mean']:.0f} ms",
            "target": f"≤ {targets_disp['response_time']:.0f} ms",
            "status": _status_for_b("rt", kb["sample_time"]["mean"], targets_disp["response_time"], True),
            "score_a": sa["scores"]["response_time"],
            "score_b": sb["scores"]["response_time"],
        },
        {
            "metric": "Error rate",
            "baseline": f"{ka['error_pct']:.3f}%",
            "candidate": f"{kb['error_pct']:.3f}%",
            "target": f"≤ {targets_disp['error_rate']:.2f}%",
            "status": _status_for_b("er", kb["error_pct"], targets_disp["error_rate"], True),
            "score_a": sa["scores"]["error_rate"],
            "score_b": sb["scores"]["error_rate"],
        },
        {
            "metric": "Throughput",
            "baseline": f"{ka['throughput_rps']:.1f} req/s",
            "candidate": f"{kb['throughput_rps']:.1f} req/s",
            "target": f"≥ {targets_disp['throughput']:.0f} req/s",
            "status": _status_for_b("tp", kb["throughput_rps"], targets_disp["throughput"], False),
            "score_a": sa["scores"]["throughput"],
            "score_b": sb["scores"]["throughput"],
        },
        {
            "metric": "P95",
            "baseline": f"{ka['sample_time']['p95']:.0f} ms",
            "candidate": f"{kb['sample_time']['p95']:.0f} ms",
            "target": f"≤ {targets_disp['p95_percentile']:.0f} ms",
            "status": _status_for_b("p95", kb["sample_time"]["p95"], targets_disp["p95_percentile"], True),
            "score_a": sa["scores"]["p95_percentile"],
            "score_b": sb["scores"]["p95_percentile"],
        },
        {
            "metric": "SLA compliance (<2s)",
            "baseline": f"{sla_a:.1f}%",
            "candidate": f"{sla_b:.1f}%",
            "target": f"≥ {targets_disp['sla_compliance']:.0f}%",
            "status": _status_for_b("sla", sla_b, targets_disp["sla_compliance"], False),
            "score_a": sa["scores"]["sla_compliance"],
            "score_b": sb["scores"]["sla_compliance"],
        },
    ]

    def _bucket_map(buckets: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
        return {int(b["bucket_index"]): b for b in buckets}

    ma, mb = _bucket_map(buckets_a), _bucket_map(buckets_b)
    all_idx = sorted(set(ma.keys()) | set(mb.keys()))
    chart_labels = [f"W{i + 1}" for i in all_idx] if all_idx else []

    def _pick(m: Dict[int, Dict[str, Any]], idx: int, key: str) -> float:
        return float(m.get(idx, {}).get(key, 0) or 0)

    chart_data = {
        "labels": chart_labels,
        "mean_rt_a": [_pick(ma, i, "mean_rt_ms") for i in all_idx],
        "mean_rt_b": [_pick(mb, i, "mean_rt_ms") for i in all_idx],
        "p95_a": [_pick(ma, i, "p95_rt_ms") for i in all_idx],
        "p95_b": [_pick(mb, i, "p95_rt_ms") for i in all_idx],
        "tput_a": [_pick(ma, i, "throughput_rps") for i in all_idx],
        "tput_b": [_pick(mb, i, "throughput_rps") for i in all_idx],
        "err_a": [_pick(ma, i, "error_pct") for i in all_idx],
        "err_b": [_pick(mb, i, "error_pct") for i in all_idx],
    }
    n = len(all_idx)

    chart_insights = []
    if n >= 3:
        late_b = sum(chart_data["mean_rt_b"][-3:]) / 3
        early_b = sum(chart_data["mean_rt_b"][:3]) / 3
        if late_b > early_b * 1.15:
            chart_insights.append(
                f"Candidate mean response time rises in later windows (~{early_b:.0f} → ~{late_b:.0f} ms) — check saturation or warm-up."
            )
        late_e = sum(chart_data["err_b"][-3:]) / 3
        early_e = sum(chart_data["err_b"][:3]) / 3
        if late_e > early_e + 0.5:
            chart_insights.append("Candidate error rate is higher in later time windows — stress or timeout pattern.")
        chart_insights.append(
            "Compare throughput lines: parallel trends suggest comparable load shape; diverging lines indicate different workload duration or intensity."
        )
    else:
        chart_insights.append("Not enough aligned time windows for trend comparison.")

    structured_issues: List[Dict[str, str]] = []
    for i, r in enumerate(exec_s.get("risks") or []):
        structured_issues.append(
            {
                "issue": f"Risk {i + 1}",
                "example": r,
                "impact": "SLO breach or user-visible slowdowns if released unchecked.",
                "recommendations": "Validate in staging; add guardrails and monitoring.",
                "business_benefit": "Reduces incident cost and protects customer trust.",
                "priority": "High" if exec_s.get("traffic_signal") == "red" else "Medium",
            }
        )
    for b in analysis.get("bottlenecks") or []:
        structured_issues.append(
            {
                "issue": b.get("type", "Bottleneck"),
                "example": b.get("evidence", "")[:200],
                "impact": b.get("impact", ""),
                "recommendations": "Correlate with infra traces and dependency dashboards.",
                "business_benefit": "Faster root-cause resolution and predictable releases.",
                "priority": "Medium",
            }
        )
    if not structured_issues:
        structured_issues.append(
            {
                "issue": "No critical pattern flagged",
                "example": "JTL signals within expected variance.",
                "impact": "Low under tested load.",
                "recommendations": "Keep regression suite on critical paths.",
                "business_benefit": "Sustained release confidence.",
                "priority": "Low",
            }
        )

    phased = JMeterAnalyzerV2._generate_phased_improvement_plan(
        sb["grade"],
        sb["scores"]["overall"],
        sb["scores"],
        kb["sample_time"]["mean"] / 1000.0,
        kb["error_pct"],
        kb["throughput_rps"],
        kb["sample_time"]["p95"] / 1000.0,
        sb["sla_2s_pct"],
        _label_stats_for_phased(la),
        _label_stats_for_phased(lb),
    )

    success_metrics = list(analysis.get("slo_recommendations") or [])[:5]
    if not success_metrics:
        success_metrics = [
            f"P95 ≤ {targets_disp['p95_percentile']:.0f} ms",
            f"Error rate ≤ {targets_disp['error_rate']:.1f}%",
            f"SLA <2s ≥ {targets_disp['sla_compliance']:.0f}%",
        ]

    strengths = []
    if d_overall > 1:
        strengths.append(f"Candidate overall score improved by {d_overall} points vs baseline.")
    if err_dir == "decreased":
        strengths.append("Error rate decreased vs baseline.")
    if p95_c is not None and p95_c < -3:
        strengths.append("P95 latency improved materially vs baseline.")
    if not strengths:
        strengths.append("Baseline and candidate are comparable on several KPIs under this load model.")

    improvements = []
    if err_dir == "increased":
        improvements.append("Error rate increased — triage failures before production.")
    if p95_c is not None and p95_c > 5:
        improvements.append("P95 regression — profile slowest endpoints and dependencies.")
    if tput_c is not None and tput_c < -10:
        improvements.append("Throughput drop — verify capacity and thread pools.")
    if not improvements:
        improvements.append("Continue monitoring tail latency and errors in longer runs.")

    final_conclusion = {
        "key_strengths": strengths[:4],
        "areas_of_improvement": improvements[:4],
        "immediate_actions": (analysis.get("recommendations") or {}).get("immediate") or ["Review executive risks and API table."],
        "success_metrics": success_metrics,
    }

    next_steps = {
        "immediate_actions_required": [
            "Executive review of release decision and comparison report",
            "Assign owners for each high-priority issue",
            "Confirm production SLOs vs test assumptions",
        ],
        "reporting_schedule": [
            "Daily: fix progress on blocker defects",
            "Weekly: performance metrics review vs baseline",
            "Post-release: error and latency dashboards for 2 weeks",
        ],
        "key_takeaways": [
            f"Verdict: {verdict}",
            f"Traffic signal: {exec_s.get('traffic_signal', 'green')}",
            "; ".join(exec_s.get("improvements") or ["No major wins flagged"])[:300],
        ],
    }

    report_footer = {
        "generated_date": __import__("datetime").datetime.now().strftime("%B %d, %Y %H:%M"),
        "generated_by": "Raghvendra Kumar",
        "classification": "Internal — Performance testing",
    }

    return {
        "executive_dashboard": {
            "cards": executive_cards,
            "error_direction": err_dir,
            "error_delta_pp": err_pp,
        },
        "key_findings": key_findings,
        "business_release": business_release,
        "distribution_deep": distribution_deep,
        "grades": {
            "baseline": {
                "overall_score": sa["scores"]["overall"],
                "grade": sa["grade"],
            },
            "candidate": {
                "overall_score": sb["scores"]["overall"],
                "grade": sb["grade"],
            },
            "delta_overall": d_overall,
            "dimensions": dimensions,
        },
        "detailed_metric_table": detailed_rows,
        "chart_data": chart_data,
        "chart_insights": chart_insights,
        "structured_issues": structured_issues[:12],
        "action_plan": phased,
        "success_metrics_targets": success_metrics,
        "final_conclusion": final_conclusion,
        "next_steps": next_steps,
        "report_footer": report_footer,
    }

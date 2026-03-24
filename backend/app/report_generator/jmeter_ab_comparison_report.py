"""
HTML report for JMeter Test A vs Test B — styled like the main JMeter Performance Assessment Report
(same CSS and section layout as HTMLReportGenerator.generate_jmeter_html_report).
"""
from __future__ import annotations

import html as html_module
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.report_generator.html_report_generator import HTMLReportGenerator


def _esc(x: Any) -> str:
    if x is None:
        return ""
    return html_module.escape(str(x))


def _metric_traffic_tier(
    key: str,
    pct: Optional[float],
    lower_is_better: bool,
    ka: Dict[str, Any],
    kb: Dict[str, Any],
) -> str:
    """
    traffic-green: within SLA / acceptable (no blocker).
    traffic-amber: degradation — may proceed with business approval.
    traffic-red: degradation — release blocker.
    traffic-neutral: N/A or inconclusive.
    """
    if key == "error_pct":
        a_err = float(ka.get("error_pct") or 0)
        b_err = float(kb.get("error_pct") or 0)
        d = b_err - a_err
        if b_err > 2.0 or d > 1.0:
            return "traffic-red"
        if (b_err > 0.5 and d > 0.05) or d > 0.25:
            return "traffic-amber"
        if d < -0.01:
            return "traffic-green"
        if d <= 0.05 and b_err <= 0.5:
            return "traffic-green"
        return "traffic-amber" if d > 0.05 else "traffic-green"

    if pct is None:
        return "traffic-neutral"

    if not lower_is_better:
        if pct >= 5:
            return "traffic-green"
        if pct >= -3:
            return "traffic-green"
        if pct <= -20:
            return "traffic-red"
        if pct <= -8:
            return "traffic-amber"
        return "traffic-green"

    if pct <= 0:
        return "traffic-green"

    if key in ("p95_ms", "p99_ms"):
        if pct >= 15:
            return "traffic-red"
        if pct >= 5:
            return "traffic-amber"
        if pct > 3:
            return "traffic-amber"
        return "traffic-green"

    if key == "p90_ms":
        if pct >= 18:
            return "traffic-red"
        if pct >= 7:
            return "traffic-amber"
        return "traffic-amber" if pct > 3 else "traffic-green"

    if key in ("avg_ms", "median_ms", "latency_avg_ms"):
        if pct >= 22:
            return "traffic-red"
        if pct >= 8:
            return "traffic-amber"
        return "traffic-amber" if pct > 3 else "traffic-green"

    if key == "max_ms":
        if pct >= 30:
            return "traffic-red"
        if pct >= 12:
            return "traffic-amber"
        return "traffic-amber" if pct > 3 else "traffic-green"

    if key == "connect_avg_ms":
        if pct >= 40:
            return "traffic-red"
        if pct >= 15:
            return "traffic-amber"
        return "traffic-amber" if pct > 5 else "traffic-green"

    if pct >= 20:
        return "traffic-red"
    if pct >= 8:
        return "traffic-amber"
    return "traffic-amber" if pct > 3 else "traffic-green"


def _fmt_pct_traffic(
    key: str,
    pct: Optional[float],
    lower_better: bool,
    ka: Dict[str, Any],
    kb: Dict[str, Any],
) -> str:
    tier = _metric_traffic_tier(key, pct, lower_better, ka, kb)
    if pct is None:
        return '<span class="traffic-val traffic-val-neutral">—</span>'
    sign = "+" if pct > 0 else ""
    return f'<span class="traffic-val {tier}">{sign}{pct:.2f}%</span>'


def _sla_caption(tier: str) -> str:
    if tier == "traffic-red":
        return "SLA signal: blocker — do not release without remediation."
    if tier == "traffic-amber":
        return "SLA signal: degraded — business approval recommended."
    return "SLA signal: acceptable vs baseline / within band."


def _insight_for_metric(key: str, pct: Optional[float], ka: Dict[str, Any], kb: Dict[str, Any], lb: bool) -> str:
    tier = _metric_traffic_tier(key, pct, lb, ka, kb)
    if pct is None and key != "error_pct":
        return "Baseline or current value missing; cannot compare."
    is_tput = key == "throughput_rps"
    improved = (pct is not None and pct > 0 and is_tput) or (pct is not None and pct < 0 and not is_tput)
    if pct is not None and abs(pct) < 3:
        base = "Within noise band (~3%); treat as stable."
    elif pct is not None:
        mag = "material" if abs(pct) >= 15 else "moderate"
        tag = "improvement" if improved else "regression"
        base = f"{mag.capitalize()} relative change ({pct:+.2f}%); treat as a {tag} for this KPI."
    else:
        base = "Compare absolute error rates between runs."
    return f"{base} {_sla_caption(tier)}"


COMPARE_SUPPLEMENT_CSS = """
<style>
/* Traffic legend */
.traffic-legend {
    display: flex; flex-wrap: wrap; align-items: center; gap: 1.25rem;
    margin: 0 0 1.5rem 0; padding: 0.85rem 1.25rem;
    background: var(--card-background); border-radius: 10px;
    border: 1px solid var(--border-color); font-size: 0.88rem;
}
.traffic-legend strong { margin-right: 0.5rem; color: var(--text-primary); }
.traffic-legend-item { display: inline-flex; align-items: center; gap: 0.45rem; color: var(--text-secondary); }
.tl-dot { width: 11px; height: 11px; border-radius: 50%; flex-shrink: 0; }
.tl-dot-red { background: #dc2626; }
.tl-dot-amber { background: #d97706; }
.tl-dot-green { background: #059669; }

/* KPI table & white sections */
.traffic-val { font-weight: 700; }
.traffic-val.traffic-green { color: #047857; }
.traffic-val.traffic-amber { color: #b45309; }
.traffic-val.traffic-red { color: #b91c1c; }
.traffic-val.traffic-neutral { color: #64748b; font-weight: 600; }

/* Executive banner by overall outcome */
.executive-summary.exec-traffic-red {
    background: linear-gradient(135deg, #7f1d1d 0%, #dc2626 100%) !important;
}
.executive-summary.exec-traffic-amber {
    background: linear-gradient(135deg, #78350f 0%, #d97706 100%) !important;
}
.executive-summary.exec-traffic-green {
    background: linear-gradient(135deg, #064e3b 0%, #059669 100%) !important;
}

/* Summary tiles: high-contrast value colors on gradient */
.executive-summary .summary-item .traffic-val.traffic-green { color: #bbf7d0; }
.executive-summary .summary-item .traffic-val.traffic-amber { color: #fde68a; }
.executive-summary .summary-item .traffic-val.traffic-red { color: #fecaca; }
.executive-summary .summary-item .traffic-val.traffic-neutral { color: rgba(255,255,255,0.85); }

.compare-header-sub { font-size: 1.05rem; opacity: 0.95; margin-top: 0.35rem; }
.bottleneck-item {
    background: #fffbeb;
    border-left: 4px solid var(--warning-color);
    padding: 1rem;
    margin: 1rem 0;
    border-radius: 0 8px 8px 0;
}
.bottleneck-item h4 { color: #92400e; margin-bottom: 0.5rem; font-size: 1rem; }
.inner-list { margin: 0.5rem 0 0 1.25rem; }
.section .muted { color: var(--text-secondary); font-size: 0.9rem; margin-top: 0.35rem; }

.section-conclusion-traffic-red { border-left: 4px solid #dc2626 !important; }
.section-conclusion-traffic-amber { border-left: 4px solid #d97706 !important; }
.section-conclusion-traffic-green { border-left: 4px solid #059669 !important; }

/* Enriched executive & report sections */
.exec-card-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
    gap: 1rem;
    margin-top: 1rem;
}
.exec-card {
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.25);
    border-radius: 12px;
    padding: 1rem 1.1rem;
    text-align: left;
}
.exec-card h3 { margin: 0 0 0.35rem 0; font-size: 0.95rem; font-weight: 600; opacity: 0.95; }
.exec-card .ec-arrow-row { display: flex; align-items: center; gap: 0.5rem; margin: 0.25rem 0; }
.exec-card .ec-arrow { font-size: 1.85rem; line-height: 1; font-weight: 800; }
.exec-card .ec-trend { font-size: 0.88rem; font-weight: 700; text-transform: capitalize; }
.exec-card .ec-trend.imp { color: #bbf7d0; }
.exec-card .ec-trend.deg { color: #fecaca; }
.exec-card .ec-trend.stable { color: #e0e7ff; }
.exec-card .ec-value { font-size: 1.35rem; font-weight: 800; margin: 0.35rem 0; }
.exec-card .ec-detail { font-size: 0.82rem; opacity: 0.9; line-height: 1.35; }
.key-findings-box {
    background: rgba(255,255,255,0.1);
    border-radius: 10px;
    padding: 1rem 1.25rem;
    margin-top: 1rem;
}
.key-findings-box h3 { margin: 0 0 0.65rem 0; font-size: 1.05rem; color: #fff; }
.key-findings-box ul { margin: 0; padding-left: 1.2rem; }
.key-findings-box li { margin: 0.35rem 0; opacity: 0.95; }

.roadmap-card {
    background: linear-gradient(135deg, #f5f3ff 0%, #ede9fe 100%);
    border: 2px solid #7c3aed;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0;
}
.roadmap-card h3 { color: #5b21b6; margin: 0 0 1rem 0; font-size: 1.1rem; }
.roadmap-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
}
.roadmap-grid .rg-item label { display: block; font-size: 0.78rem; color: #6b7280; text-transform: uppercase; letter-spacing: 0.03em; }
.roadmap-grid .rg-item .v { font-weight: 800; font-size: 1.05rem; margin-top: 0.25rem; }
.rg-curr { color: #6d28d9; }
.rg-target { color: #059669; }
.rg-gap { color: #ea580c; }
.rg-time { color: #2563eb; }

.focus-areas-callout {
    background: #fffbeb;
    border-left: 4px solid #d97706;
    padding: 0.85rem 1.1rem;
    border-radius: 0 8px 8px 0;
    margin: 1rem 0;
}
.focus-areas-callout h4 { margin: 0 0 0.5rem 0; color: #92400e; font-size: 1rem; }
.focus-areas-callout ul { margin: 0; padding-left: 1.2rem; color: #78350f; }

.phase-card {
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 1.25rem;
    margin: 1rem 0;
    background: var(--card-background);
}
.phase-head { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 1rem; align-items: flex-start; }
.phase-target-pill { text-align: right; }
.phase-target-pill .lbl { font-size: 0.75rem; color: var(--text-secondary); }
.phase-target-pill .scr { font-size: 1.5rem; font-weight: 800; color: #059669; }
.phase-action-block {
    margin-top: 1rem;
    border-left: 4px solid #dc2626;
    padding: 0.85rem 1rem 0.85rem 1rem;
    background: #fef2f2;
    border-radius: 0 8px 8px 0;
}
.phase-action-block.alt { border-left-color: #d97706; background: #fffbeb; }
.phase-action-block h5 { margin: 0 0 0.35rem 0; font-size: 1rem; }
.phase-action-block .obj { font-style: italic; color: #6b7280; font-size: 0.9rem; margin-bottom: 0.5rem; }
.phase-action-block ol { margin: 0.5rem 0 0 1.2rem; padding: 0; }
.impact-badge {
    display: inline-block;
    margin-top: 0.75rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: #d1fae5;
    color: #065f46;
    font-size: 0.85rem;
    font-weight: 600;
}

.grades-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 1rem;
    margin-top: 0.75rem;
}
.grade-tile {
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 1rem;
    background: var(--card-background);
}
.grade-tile h4 { margin: 0 0 0.5rem 0; font-size: 0.95rem; color: var(--text-secondary); }
.grade-tile .big { font-size: 1.35rem; font-weight: 800; color: var(--text-primary); }

.conclusion-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: 1rem;
    margin-top: 0.75rem;
}
.conclusion-card {
    border: 1px solid var(--border-color);
    border-radius: 10px;
    padding: 1rem;
    background: var(--card-background);
}
.conclusion-card h4 { margin: 0 0 0.5rem 0; font-size: 1rem; color: #4f46e5; }
.conclusion-card ul { margin: 0; padding-left: 1.1rem; font-size: 0.92rem; }

.chart-wrap { position: relative; height: 320px; margin: 1.25rem 0; }
.chart-grid-1 { max-width: 100%; }

.report-footer-meta {
    text-align: center;
    padding: 1.5rem 1rem 2rem;
    color: var(--text-secondary);
    font-size: 0.9rem;
    border-top: 1px solid var(--border-color);
    margin-top: 2rem;
}
.report-footer-meta .by { margin-top: 0.35rem; font-weight: 600; color: var(--text-primary); }
</style>
"""


def _exec_card_trend_class(title: str, trend: str) -> str:
    t = (trend or "").lower()
    if "throughput" in (title or "").lower():
        if "improvement" in t:
            return "imp"
        if "degradation" in t:
            return "deg"
        return "stable"
    if "error" in (title or "").lower():
        if "decreased" in t:
            return "imp"
        if "increased" in t:
            return "deg"
        return "stable"
    if "improvement" in t:
        return "imp"
    if "degradation" in t:
        return "deg"
    return "stable"


def _render_action_plan_html(plan: Dict[str, Any]) -> str:
    if not plan:
        return '<p class="muted">Action plan not available.</p>'
    if plan.get("status") and "Already" in str(plan.get("status", "")):
        parts = [
            f'<div class="roadmap-card"><h3>{_esc(plan.get("status"))}</h3>'
            f'<p>{_esc(plan.get("message", ""))}</p><ul class="inner-list">'
        ]
        for m in plan.get("maintenance_actions") or []:
            parts.append(f"<li>{_esc(m)}</li>")
        parts.append("</ul></div>")
        return "\n".join(parts)
    weak = plan.get("weak_areas") or []
    focus_lis = "".join(
        f"<li>{_esc(w.get('area', ''))}: score {_esc(w.get('current_score', '—'))}</li>" for w in weak
    ) or "<li>No weak area flagged — maintain current posture.</li>"
    roadmap = f"""
<div class="roadmap-card">
    <h3>Improvement roadmap to A+ grade</h3>
    <div class="roadmap-grid">
        <div class="rg-item"><label>Current status</label>
            <div class="v rg-curr">{_esc(plan.get('current_grade', '—'))} ({_esc(plan.get('current_score', '—'))}/100)</div></div>
        <div class="rg-item"><label>Target grade</label>
            <div class="v rg-target">{_esc(plan.get('target_grade', 'A+'))} ({_esc(plan.get('target_score', 90))}+/100)</div></div>
        <div class="rg-item"><label>Score gap</label>
            <div class="v rg-gap">{_esc(plan.get('score_gap', '—'))} points</div></div>
        <div class="rg-item"><label>Estimated timeline</label>
            <div class="v rg-time">{_esc(plan.get('estimated_timeline', '4-6 weeks'))}</div></div>
    </div>
</div>
<div class="focus-areas-callout">
    <h4>Focus areas (weakest performance)</h4>
    <ul>{focus_lis}</ul>
</div>
"""
    phase_blocks = []
    for idx, ph in enumerate(plan.get("phases") or []):
        alt = " alt" if idx % 2 else ""
        actions_html = []
        for act in ph.get("actions") or []:
            steps = "".join(f"<li>{_esc(s)}</li>" for s in act.get("steps") or [])
            imp = _esc(act.get("expected_impact", ""))
            actions_html.append(
                f'<div class="phase-action-block{alt}"><h5>{_esc(act.get("action", ""))}</h5>'
                f'<div class="obj">{_esc(act.get("detail", ""))}</div>'
                f"<ol>{steps}</ol>"
                f'<span class="impact-badge">Impact: {imp}</span></div>'
            )
        phase_blocks.append(
            f'<div class="phase-card"><div class="phase-head">'
            f'<div><h3 style="margin:0;color:#2563eb;">{_esc(ph.get("phase", ""))}</h3>'
            f'<p class="muted" style="margin:0.35rem 0 0 0;">{_esc(ph.get("timeline", ""))} | Priority: {_esc(ph.get("priority", ""))}</p></div>'
            f'<div class="phase-target-pill"><span class="lbl">Target</span>'
            f'<div class="scr">{_esc(ph.get("expected_grade", ""))} ({_esc(ph.get("target_score", ""))})</div></div></div>'
            f'{"".join(actions_html)}</div>'
        )
    success = plan.get("success_metrics") or []
    succ_html = "<ul class='inner-list'>" + "".join(f"<li>{_esc(s)}</li>" for s in success) + "</ul>"
    return roadmap + "<h3 style='margin-top:1.5rem;'>Implementation phases</h3>" + "\n".join(phase_blocks) + (
        f"<h3>Success metrics &amp; targets</h3>{succ_html}"
    )


def generate_jmeter_ab_comparison_html(analysis: Dict[str, Any]) -> str:
    meta = analysis.get("meta", {})
    name_a = meta.get("name_a", "Test A")
    name_b = meta.get("name_b", "Test B")
    now_utc = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    current_date = datetime.now().strftime("%B %d, %Y")

    da = analysis.get("data_prep", {})
    ka = analysis.get("test_a", {}).get("kpis", {})
    kb = analysis.get("test_b", {}).get("kpis", {})
    pct = analysis.get("kpi_percent_change", {})
    exec_s = analysis.get("executive_summary", {})
    _ta = analysis.get("test_a") or {}
    _tb = analysis.get("test_b") or {}
    _tr = analysis.get("trend") or {}
    _hi = analysis.get("highlights") or {}
    _rec = analysis.get("recommendations") or {}
    _con = analysis.get("conclusion") or {}

    css_content = HTMLReportGenerator._generate_css()

    def kpi_rows() -> str:
        keys = [
            ("avg_ms", "Average response time (ms)", True),
            ("median_ms", "Median / P50 (ms)", True),
            ("p90_ms", "P90 (ms)", True),
            ("p95_ms", "P95 (ms)", True),
            ("p99_ms", "P99 (ms)", True),
            ("max_ms", "Max (ms)", True),
            ("throughput_rps", "Throughput (req/s)", False),
            ("error_pct", "Error %", True),
            ("latency_avg_ms", "Avg latency (ms)", True),
            ("connect_avg_ms", "Avg connect time (ms)", True),
        ]
        rows = []
        st_a, st_b = ka.get("sample_time", {}), kb.get("sample_time", {})
        lat_a, lat_b = ka.get("latency", {}), kb.get("latency", {})
        conn_a, conn_b = ka.get("connect_time", {}), kb.get("connect_time", {})
        values_a = {
            "avg_ms": st_a.get("mean"), "median_ms": st_a.get("median"), "p90_ms": st_a.get("p90"),
            "p95_ms": st_a.get("p95"), "p99_ms": st_a.get("p99"), "max_ms": st_a.get("max"),
            "throughput_rps": ka.get("throughput_rps"), "error_pct": ka.get("error_pct"),
            "latency_avg_ms": lat_a.get("mean"), "connect_avg_ms": conn_a.get("mean"),
        }
        values_b = {
            "avg_ms": st_b.get("mean"), "median_ms": st_b.get("median"), "p90_ms": st_b.get("p90"),
            "p95_ms": st_b.get("p95"), "p99_ms": st_b.get("p99"), "max_ms": st_b.get("max"),
            "throughput_rps": kb.get("throughput_rps"), "error_pct": kb.get("error_pct"),
            "latency_avg_ms": lat_b.get("mean"), "connect_avg_ms": conn_b.get("mean"),
        }
        for k, label, lb in keys:
            va, vb = values_a.get(k), values_b.get(k)
            pc = pct.get(k)
            insight = _insight_for_metric(k, pc, ka, kb, lb)
            rows.append(
                f"<tr><td>{_esc(label)}</td><td>{_esc(f'{va:.2f}' if va is not None else '—')}</td>"
                f"<td>{_esc(f'{vb:.2f}' if vb is not None else '—')}</td>"
                f"<td>{_fmt_pct_traffic(k, pc, lb, ka, kb)}</td><td>{_esc(insight)}</td></tr>"
            )
        return "\n".join(rows)

    def workload_rows() -> str:
        lines = []
        for row in analysis.get("workload_table", []):
            lines.append(
                f"<tr><td>{_esc(row.get('parameter'))}</td><td>{_esc(row.get('test_a'))}</td>"
                f"<td>{_esc(row.get('test_b'))}</td><td>{_esc(row.get('remarks'))}</td></tr>"
            )
        return "\n".join(lines)

    def api_rows() -> str:
        rows = analysis.get("api_comparison", [])
        out = []
        for r in rows:
            pc = r.get("p95_change_pct")
            atp = r.get("a_tput")
            btp = r.get("b_tput")
            atp_s = f"{float(atp):.2f}" if atp is not None else "—"
            btp_s = f"{float(btp):.2f}" if btp is not None else "—"
            out.append(
                f"<tr><td>{_esc(r.get('label'))}</td>"
                f"<td>{r.get('a_avg'):.2f}</td><td>{r.get('b_avg'):.2f}</td>"
                f"<td>{r.get('a_p95'):.2f}</td><td>{r.get('b_p95'):.2f}</td>"
                f"<td>{atp_s}</td><td>{btp_s}</td>"
                f"<td>{r.get('a_err_pct'):.4f}</td><td>{r.get('b_err_pct'):.4f}</td>"
                f"<td>{_fmt_pct_traffic('p95_ms', pc, True, ka, kb)}</td></tr>"
            )
        return "\n".join(out) if out else (
            "<tr><td colspan='10'>No overlapping labels between runs.</td></tr>"
        )

    def list_block(title: str, items: List[str], alert_class: str = "alert-warning") -> str:
        if not items:
            return ""
        lis = "".join(f"<li>{_esc(i)}</li>" for i in items)
        return (
            f'<div class="alert {alert_class}" style="margin-top:1rem;">'
            f"<h3 style=\"margin-top:0;font-size:1.1rem;\">{_esc(title)}</h3>"
            f'<ul class="inner-list">{lis}</ul></div>'
        )

    def bottleneck_cards() -> str:
        cards = []
        for b in analysis.get("bottlenecks", []):
            cards.append(
                f'<div class="bottleneck-item"><h4>{_esc(b.get("type", ""))}</h4>'
                f'<p><strong>Evidence:</strong> {_esc(b.get("evidence", ""))}</p>'
                f'<p><strong>Impact:</strong> {_esc(b.get("impact", ""))}</p>'
                f'<p><strong>When:</strong> {_esc(b.get("when", ""))}</p></div>'
            )
        return (
            "\n".join(cards)
            if cards
            else '<p class="muted">No strong bottleneck pattern detected from JTL fields alone.</p>'
        )

    apples = da.get("apples_to_apples", True)
    apples_note = (
        "Comparison is approximately apples-to-apples on duration, threads, and sample volume."
        if apples
        else "Fairness warnings apply — interpret deltas cautiously (see Data preparation)."
    )

    def _pct_display(p: Optional[float], lb: bool) -> str:
        if p is None:
            return "—"
        sign = "+" if p > 0 else ""
        return f"{sign}{p:.1f}%"

    p95_c, p99_c, err_c, tput_c = pct.get("p95_ms"), pct.get("p99_ms"), pct.get("error_pct"), pct.get("throughput_rps")
    exec_signal = exec_s.get("traffic_signal") or "green"
    if exec_signal not in ("red", "amber", "green"):
        exec_signal = "green"

    tier_p95 = _metric_traffic_tier("p95_ms", p95_c, True, ka, kb)
    tier_p99 = _metric_traffic_tier("p99_ms", p99_c, True, ka, kb)
    tier_err = _metric_traffic_tier("error_pct", err_c, True, ka, kb)
    tier_tput = _metric_traffic_tier("throughput_rps", tput_c, False, ka, kb)

    pdf_button = """<button onclick="window.print()" class="pdf-button no-print" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; font-size: 0.95rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); transition: all 0.2s;">
                    <span style="font-size: 1.2rem;">📄</span>
                    Save as PDF
                </button>"""

    dash = analysis.get("executive_dashboard") or {}
    cards = dash.get("cards")
    if cards:
        ec_parts = []
        for c in cards:
            tc = _exec_card_trend_class(c.get("title", ""), c.get("trend", ""))
            ec_parts.append(
                f'<div class="exec-card"><h3>{_esc(c.get("title"))}</h3>'
                f'<div class="ec-arrow-row"><span class="ec-arrow">{_esc(c.get("arrow", "→"))}</span>'
                f'<span class="ec-trend {tc}">{_esc(c.get("trend", ""))}</span></div>'
                f'<div class="ec-value">{_esc(c.get("value", ""))}</div>'
                f'<div class="ec-detail">{_esc(c.get("detail", ""))}</div></div>'
            )
        executive_cards_html = '<div class="exec-card-grid">' + "".join(ec_parts) + "</div>"
    else:
        executive_cards_html = f"""
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value" style="font-size: 1.25rem;">P95 Δ</div>
                    <div class="metric-label">vs baseline</div>
                    <div style="font-size:1.5rem;font-weight:700;"><span class="traffic-val {tier_p95}">{_esc(_pct_display(p95_c, True))}</span></div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="font-size: 1.25rem;">P99 Δ</div>
                    <div class="metric-label">tail latency</div>
                    <div style="font-size:1.5rem;font-weight:700;"><span class="traffic-val {tier_p99}">{_esc(_pct_display(p99_c, True))}</span></div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="font-size: 1.25rem;">Error rate B</div>
                    <div class="metric-label">candidate</div>
                    <div style="font-size:1.5rem;font-weight:700;"><span class="traffic-val {tier_err}">{_esc(f"{kb.get('error_pct', 0):.3f}")}%</span></div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="font-size: 1.25rem;">Throughput Δ</div>
                    <div class="metric-label">req/s</div>
                    <div style="font-size:1.5rem;font-weight:700;"><span class="traffic-val {tier_tput}">{_esc(_pct_display(tput_c, False))}</span></div>
                </div>
            </div>"""

    kf_list = analysis.get("key_findings")
    if not kf_list:
        kf_list = [
            f"Response time: baseline avg {ka.get('sample_time', {}).get('mean', 0):.0f} ms; candidate {kb.get('sample_time', {}).get('mean', 0):.0f} ms.",
            f"Error rate: {ka.get('error_pct', 0):.3f}% vs {kb.get('error_pct', 0):.3f}%.",
            f"Throughput: {ka.get('throughput_rps', 0):.1f} vs {kb.get('throughput_rps', 0):.1f} req/s.",
        ]
    key_findings_html = '<ul>' + "".join(f"<li>{_esc(x)}</li>" for x in kf_list) + "</ul>"

    br = analysis.get("business_release") or {}
    business_html = f"""
        <p><strong>Release decision:</strong> {_esc(br.get("release_decision", exec_s.get("verdict", "")))}</p>
        <p><strong>Recommendation:</strong> {_esc(br.get("recommendation", exec_s.get("recommendation", "")))}</p>
        <p><strong>Customer impact:</strong> {_esc(br.get("customer_impact", ""))}</p>
        <p><strong>Business outcomes:</strong> {_esc(br.get("business_outcomes", ""))}</p>
        <p><strong>Recommended actions:</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(a)}</li>" for a in (br.get("recommended_actions") or [])[:8])}</ul>
        <p><strong>Technical indicators:</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(t)}</li>" for t in (br.get("technical_indicators") or [])[:8])}</ul>
    """

    dd = analysis.get("distribution_deep") or {}
    dist_html = f"""
        <p><strong>Observations</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(o)}</li>" for o in (dd.get("observations") or analysis.get("observations") or []))}</ul>
        <p><strong>Interpretations</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(i)}</li>" for i in (dd.get("interpretations") or []))}</ul>
        <p><strong>Possible root causes</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(r)}</li>" for r in (dd.get("root_causes") or []) if r)}</ul>
        <p><strong>Business impact:</strong> {_esc(dd.get("business_impact", ""))}</p>
    """

    gr = analysis.get("grades") or {}
    ga, gb = gr.get("baseline") or {}, gr.get("candidate") or {}
    dims = gr.get("dimensions") or []
    dim_tiles = "".join(
        f'<div class="grade-tile"><h4>{_esc(d.get("label", ""))}</h4>'
        f'<div class="big">{_esc(d.get("grade_a", ""))} ({d.get("score_a", "")}) → {_esc(d.get("grade_b", ""))} ({d.get("score_b", "")})</div>'
        f'<p class="muted" style="margin:0.35rem 0 0 0;">Δ {_esc(d.get("delta", ""))} pts</p></div>'
        for d in dims
    )
    grades_html = f"""
        <div class="grades-grid">
            <div class="grade-tile"><h4>Overall</h4>
                <div class="big">{_esc(ga.get("grade", "—"))} ({ga.get("overall_score", "—")}) → {_esc(gb.get("grade", "—"))} ({gb.get("overall_score", "—")})</div>
                <p class="muted" style="margin:0.35rem 0 0 0;">Δ {_esc(gr.get("delta_overall", "—"))} pts (candidate vs baseline)</p></div>
            {dim_tiles}
        </div>
    """

    def detailed_metric_rows() -> str:
        lines = []
        for row in analysis.get("detailed_metric_table") or []:
            lines.append(
                f"<tr><td>{_esc(row.get('metric'))}</td>"
                f"<td>{_esc(row.get('baseline'))}</td><td>{_esc(row.get('candidate'))}</td>"
                f"<td>{_esc(row.get('target'))}</td><td>{_esc(row.get('status'))}</td>"
                f"<td>{_esc(row.get('score_b'))}</td><td>{_esc(row.get('score_a'))}</td></tr>"
            )
        return "\n".join(lines) if lines else (
            f"<tr><td colspan='7'>Detailed scoring not available for this report.</td></tr>"
        )

    iss_rows = []
    for it in analysis.get("structured_issues") or []:
        iss_rows.append(
            f"<tr><td>{_esc(it.get('issue'))}</td><td>{_esc(it.get('example'))}</td>"
            f"<td>{_esc(it.get('impact'))}</td><td>{_esc(it.get('recommendations'))}</td>"
            f"<td>{_esc(it.get('business_benefit'))}</td><td>{_esc(it.get('priority'))}</td></tr>"
        )
    issues_table_html = "\n".join(iss_rows) if iss_rows else (
        "<tr><td colspan='6'>No structured issues.</td></tr>"
    )

    fc = analysis.get("final_conclusion") or {}
    conclusion_cards_html = f"""
        <div class="conclusion-cards">
            <div class="conclusion-card"><h4>Key strengths</h4><ul>{"".join(f"<li>{_esc(x)}</li>" for x in (fc.get("key_strengths") or []))}</ul></div>
            <div class="conclusion-card"><h4>Areas of improvement</h4><ul>{"".join(f"<li>{_esc(x)}</li>" for x in (fc.get("areas_of_improvement") or []))}</ul></div>
            <div class="conclusion-card"><h4>Recommended immediate actions</h4><ul>{"".join(f"<li>{_esc(x)}</li>" for x in (fc.get("immediate_actions") or []))}</ul></div>
            <div class="conclusion-card"><h4>Success metrics</h4><ul>{"".join(f"<li>{_esc(x)}</li>" for x in (fc.get("success_metrics") or []))}</ul></div>
        </div>
    """

    ns = analysis.get("next_steps") or {}
    next_steps_html = f"""
        <p><strong>Immediate actions required</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(x)}</li>" for x in (ns.get("immediate_actions_required") or []))}</ul>
        <p><strong>Reporting schedule</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(x)}</li>" for x in (ns.get("reporting_schedule") or []))}</ul>
        <p><strong>Key takeaways</strong></p>
        <ul class="inner-list">{"".join(f"<li>{_esc(x)}</li>" for x in (ns.get("key_takeaways") or []))}</ul>
    """

    rf = analysis.get("report_footer") or {}
    footer_html = f"""
        <div class="report-footer-meta">
            <div>Report generated: {_esc(rf.get("generated_date", current_date))}</div>
            <div class="by">Generated by: {_esc(rf.get("generated_by", "Raghvendra Kumar"))}</div>
            <div>{_esc(rf.get("classification", "Internal — Performance testing"))}</div>
        </div>
    """

    chart_data = analysis.get("chart_data") or {}
    chart_insights = analysis.get("chart_insights") or []
    chart_insights_html = "<ul class='inner-list'>" + "".join(f"<li>{_esc(i)}</li>" for i in chart_insights) + "</ul>"
    chart_json = json.dumps(
        {
            "labels": chart_data.get("labels") or [],
            "mean_rt_a": chart_data.get("mean_rt_a") or [],
            "mean_rt_b": chart_data.get("mean_rt_b") or [],
            "p95_a": chart_data.get("p95_a") or [],
            "p95_b": chart_data.get("p95_b") or [],
            "tput_a": chart_data.get("tput_a") or [],
            "tput_b": chart_data.get("tput_b") or [],
            "err_a": chart_data.get("err_a") or [],
            "err_b": chart_data.get("err_b") or [],
            "name_a": name_a,
            "name_b": name_b,
        }
    )
    action_plan_html = _render_action_plan_html(analysis.get("action_plan") or {})

    sm_extra = analysis.get("success_metrics_targets") or []
    success_targets_extra = (
        "<h3>Program success metrics &amp; targets</h3><ul class='inner-list'>"
        + "".join(f"<li>{_esc(s)}</li>" for s in sm_extra)
        + "</ul>"
        if sm_extra
        else ""
    )

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Test Comparison Report</title>
    {css_content}
    {COMPARE_SUPPLEMENT_CSS}
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
</head>
<body>
    <div class="header">
        <div class="container">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem;">
                <div style="text-align: left;">
                    <h1 style="margin: 0;">Performance Test Comparison Report</h1>
                    <p class="compare-header-sub" style="margin: 0.5rem 0 0 0;">Load testing comparison &amp; executive analysis | {current_date}</p>
                    <p class="compare-header-sub" style="margin: 0.35rem 0 0 0; font-size: 0.95rem;">
                        <strong>{_esc(name_a)}</strong> (baseline) vs <strong>{_esc(name_b)}</strong> (candidate) · Generated {now_utc}
                    </p>
                </div>
                {pdf_button}
            </div>
        </div>
    </div>

    <div class="container">
        <div class="traffic-legend no-print">
            <strong>Color key</strong>
            <span class="traffic-legend-item"><span class="tl-dot tl-dot-green"></span>Green — within SLA / acceptable</span>
            <span class="traffic-legend-item"><span class="tl-dot tl-dot-amber"></span>Amber — degraded; business approval may allow proceed</span>
            <span class="traffic-legend-item"><span class="tl-dot tl-dot-red"></span>Red — blocker; remediation before release</span>
        </div>

        <div class="executive-summary exec-traffic-{_esc(exec_signal)}">
            <h2 style="color: white; margin-top: 0; border-bottom: 1px solid rgba(255,255,255,0.35); padding-bottom: 0.5rem;">Executive summary</h2>
            <p style="font-size: 1.25rem; font-weight: 700; margin: 0.75rem 0;">{_esc(exec_s.get("verdict", "N/A"))}</p>
            <p style="opacity: 0.95; margin-bottom: 1rem;">{_esc(exec_s.get("recommendation", ""))}</p>
            {executive_cards_html}
            <div class="key-findings-box">
                <h3>Key findings</h3>
                {key_findings_html}
            </div>
            <p style="margin-top: 1rem; opacity: 0.95;"><strong>Key improvements:</strong> {_esc("; ".join(exec_s.get("improvements") or ["None flagged"]))}</p>
            <p style="opacity: 0.95;"><strong>Risks:</strong> {_esc("; ".join(exec_s.get("risks") or ["None flagged"]))}</p>
            <p style="opacity: 0.9; font-size: 0.95rem;">{_esc(apples_note)}</p>
        </div>

        <div class="section">
            <h2>Business impact analysis &amp; release decision</h2>
            {business_html}
        </div>

        <div class="section">
            <h2>Statistical distribution analysis</h2>
            {dist_html}
        </div>

        <div class="section">
            <h2>Grade comparison</h2>
            <p class="muted">Overall and by dimension (baseline → candidate). Higher scores are better.</p>
            {grades_html}
        </div>

        <div class="section">
            <h2>Detailed performance metrics</h2>
            <p class="muted">Baseline vs candidate vs display targets; dimension scores for each run.</p>
            <table class="endpoint-table">
                <thead>
                    <tr>
                        <th>Metric</th><th>Baseline</th><th>Candidate</th><th>Target</th><th>Status (candidate)</th>
                        <th>Score (candidate)</th><th>Score (baseline)</th>
                    </tr>
                </thead>
                <tbody>{detailed_metric_rows()}</tbody>
            </table>
        </div>

        <div class="section">
            <h2>Performance test summary (per endpoint)</h2>
            <p class="muted">Overlapping transaction labels only. Sorted by candidate P95 (descending).</p>
            <table class="endpoint-table">
                <thead>
                    <tr>
                        <th>Label</th><th>Avg RT (baseline)</th><th>Avg RT (candidate)</th>
                        <th>P95 (baseline)</th><th>P95 (candidate)</th>
                        <th>Throughput (baseline) req/s</th><th>Throughput (candidate) req/s</th>
                        <th>Error % (baseline)</th><th>Error % (candidate)</th><th>P95 Δ%</th>
                    </tr>
                </thead>
                <tbody>{api_rows()}</tbody>
            </table>
        </div>

        <div class="section">
            <h2>Comparative charts</h2>
            <p class="muted">Time windows are aligned by bucket index where both runs have samples. Read trends relative to the same window label.</p>
            <h3>Average response time &amp; P95 over time</h3>
            <div class="chart-wrap chart-grid-1"><canvas id="abChartLatency"></canvas></div>
            <h3>Throughput over time</h3>
            <div class="chart-wrap chart-grid-1"><canvas id="abChartTput"></canvas></div>
            <h3>Error rate over time</h3>
            <div class="chart-wrap chart-grid-1"><canvas id="abChartErr"></canvas></div>
            <h3>Chart observations &amp; insights</h3>
            {chart_insights_html}
        </div>

        <div class="section">
            <h2>Highlighted issues</h2>
            <table class="endpoint-table">
                <thead>
                    <tr>
                        <th>Issue</th><th>Example</th><th>Impact</th><th>Recommendations</th><th>Business benefit</th><th>Priority</th>
                    </tr>
                </thead>
                <tbody>{issues_table_html}</tbody>
            </table>
        </div>

        <div class="section">
            <h2>Recommended action plan</h2>
            <p class="muted">Phased plan derived from candidate scores and weakest dimensions (same engine as the main JMeter report).</p>
            {action_plan_html}
            {success_targets_extra}
        </div>

        <div class="section">
            <h2>Final conclusion</h2>
            {conclusion_cards_html}
        </div>

        <div class="section">
            <h2>Next steps &amp; contacts</h2>
            {next_steps_html}
        </div>

        <div class="section">
            <h2>Test overview</h2>
            <table class="endpoint-table">
                <thead><tr><th>Field</th><th>{_esc(name_a)}</th><th>{_esc(name_b)}</th></tr></thead>
                <tbody>
                    <tr><td>Environment</td><td>{_esc(meta.get("environment_a") or "—")}</td><td>{_esc(meta.get("environment_b") or "—")}</td></tr>
                    <tr><td>Build / version</td><td>{_esc(meta.get("build_a") or "—")}</td><td>{_esc(meta.get("build_b") or "—")}</td></tr>
                    <tr><td>Tooling</td><td colspan="2">JMeter JTL / CSV / XML · Auto Report Analyzer</td></tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Data preparation &amp; fairness</h2>
            <p><strong>Apples-to-apples:</strong> {"Yes" if apples else "No — review warnings below"}</p>
            <p><strong>Label overlap:</strong> {_esc(da.get("label_overlap_pct"))}%</p>
            {list_block("Fairness / workload warnings", da.get("fairness_warnings") or [])}
            {list_block("Test A data issues", da.get("issues_a") or [], "alert-danger")}
            {list_block("Test B data issues", da.get("issues_b") or [], "alert-danger")}
        </div>

        <div class="section">
            <h2>Workload comparison</h2>
            <table class="endpoint-table">
                <thead><tr><th>Parameter</th><th>{_esc(name_a)}</th><th>{_esc(name_b)}</th><th>Remarks</th></tr></thead>
                <tbody>{workload_rows()}</tbody>
            </table>
        </div>

        <div class="section">
            <h2>KPI comparison</h2>
            <p class="muted">Percent change = (B − A) / A × 100. For latency and errors, lower is better. For throughput, higher is better.
            Cell colors follow the legend: green = acceptable vs baseline, amber = degraded (business sign-off), red = release blocker.</p>
            <table class="endpoint-table">
                <thead><tr><th>Metric</th><th>{_esc(name_a)}</th><th>{_esc(name_b)}</th><th>% change</th><th>Insight</th></tr></thead>
                <tbody>{kpi_rows()}</tbody>
            </table>
        </div>

        <div class="section">
            <h2>Distribution &amp; variability (quick index)</h2>
            <p><strong>Variability index (P99 / P50)</strong> — {_esc(name_a)}: {_esc(_ta.get("variability_index"))},
            {_esc(name_b)}: {_esc(_tb.get("variability_index"))}</p>
            <p class="muted">Deeper observations and interpretations are in <strong>Statistical distribution analysis</strong> above.</p>
        </div>

        <div class="section">
            <h2>Trend analysis</h2>
            <ul class="inner-list">
                {"".join(f"<li>{_esc(n)}</li>" for n in _tr.get("notes", []))}
            </ul>
            <p class="muted">See <strong>Comparative charts</strong> for window-by-window latency, throughput, and error trends.</p>
        </div>

        <div class="section">
            <h2>Correlation insights</h2>
            <ul class="inner-list">
                {"".join(f"<li>{_esc(i)}</li>" for i in analysis.get("correlation_insights") or ["No correlation statements met detection thresholds."])}
            </ul>
        </div>

        <div class="section">
            <h2>Bottleneck analysis (hypothesis)</h2>
            <p class="muted">Inferred from JTL patterns — validate with traces, JVM/GC, database, and dependency dashboards.</p>
            {bottleneck_cards()}
        </div>

        <div class="section">
            <h2>Endpoint highlights</h2>
            <p class="muted">Supplement to the <strong>Performance test summary</strong> table above.</p>
            <h3>Highlights</h3>
            <p><strong>Top slowest APIs (B, by P99):</strong></p>
            <ul class="inner-list">
                {"".join(
                    f"<li>{_esc(h.get('label'))}: P99 {_esc(h.get('p99_ms'))} ms, P95 {_esc(h.get('p95_ms'))} ms</li>"
                    for h in _hi.get("top_slowest_apis_b", [])
                )}
            </ul>
            <p><strong>Most improved (P95):</strong></p>
            <ul class="inner-list">
                {"".join(
                    f"<li>{_esc(h.get('label'))}: {_esc(h.get('p95_change_pct'))}%</li>"
                    for h in _hi.get("most_improved_p95", [])
                )}
            </ul>
            <p><strong>Most degraded (P95):</strong></p>
            <ul class="inner-list">
                {"".join(
                    f"<li>{_esc(h.get('label'))}: {_esc(h.get('p95_change_pct'))}%</li>"
                    for h in _hi.get("most_degraded_p95", [])
                )}
            </ul>
        </div>

        <div class="section">
            <h2>Observations</h2>
            <ul class="inner-list">{"".join(f"<li>{_esc(o)}</li>" for o in analysis.get("observations", []))}</ul>
        </div>

        <div class="section">
            <h2>SLO recommendations</h2>
            <ul class="inner-list">{"".join(f"<li>{_esc(s)}</li>" for s in analysis.get("slo_recommendations", []))}</ul>
        </div>

        <div class="section">
            <h2>Alert thresholds (starting points)</h2>
            <ul class="inner-list">{"".join(f"<li>{_esc(s)}</li>" for s in analysis.get("alert_thresholds", []))}</ul>
        </div>

        <div class="section">
            <h2>Auto-remediation suggestions</h2>
            <ul class="inner-list">{"".join(f"<li>{_esc(s)}</li>" for s in analysis.get("auto_remediation", []))}</ul>
        </div>

        <div class="section">
            <h2>Recommendations</h2>
            <h3>Immediate</h3>
            <ul class="inner-list">{"".join(f"<li>{_esc(i)}</li>" for i in _rec.get("immediate", []) or ["—"])}</ul>
            <h3>Medium-term</h3>
            <ul class="inner-list">{"".join(f"<li>{_esc(i)}</li>" for i in _rec.get("medium", []) or ["—"])}</ul>
            <h3>Long-term</h3>
            <ul class="inner-list">{"".join(f"<li>{_esc(i)}</li>" for i in _rec.get("long", []) or ["—"])}</ul>
        </div>

        <div class="section section-conclusion-traffic-{_esc(exec_signal)}">
            <h2>Conclusion</h2>
            <p><strong>Decision:</strong> {_esc(_con.get("decision", ""))}</p>
            <p><strong>Production readiness:</strong> {_esc(_con.get("production_readiness", ""))}</p>
        </div>

        {footer_html}
    </div>
    <script type="application/json" id="ab-chart-data">{chart_json}</script>
    <script>
    (function() {{
        var el = document.getElementById('ab-chart-data');
        if (!el || typeof Chart === 'undefined') return;
        var D;
        try {{ D = JSON.parse(el.textContent); }} catch (e) {{ return; }}
        if (!D.labels || D.labels.length === 0) return;
        var na = D.name_a || 'Baseline';
        var nb = D.name_b || 'Candidate';
        var common = {{
            responsive: true,
            maintainAspectRatio: false,
            interaction: {{ mode: 'index', intersect: false }},
            scales: {{
                x: {{ grid: {{ display: false }} }},
                y: {{ beginAtZero: true }}
            }}
        }};
        new Chart(document.getElementById('abChartLatency'), {{
            type: 'line',
            data: {{
                labels: D.labels,
                datasets: [
                    {{ label: na + ' avg RT (ms)', data: D.mean_rt_a, borderColor: '#6366f1', tension: 0.2, fill: false }},
                    {{ label: nb + ' avg RT (ms)', data: D.mean_rt_b, borderColor: '#0ea5e9', tension: 0.2, fill: false }},
                    {{ label: na + ' P95 (ms)', data: D.p95_a, borderColor: '#7c3aed', borderDash: [6,4], tension: 0.2, fill: false }},
                    {{ label: nb + ' P95 (ms)', data: D.p95_b, borderColor: '#059669', borderDash: [6,4], tension: 0.2, fill: false }}
                ]
            }},
            options: common
        }});
        new Chart(document.getElementById('abChartTput'), {{
            type: 'line',
            data: {{
                labels: D.labels,
                datasets: [
                    {{ label: na + ' req/s', data: D.tput_a, borderColor: '#6366f1', tension: 0.2, fill: false }},
                    {{ label: nb + ' req/s', data: D.tput_b, borderColor: '#0ea5e9', tension: 0.2, fill: false }}
                ]
            }},
            options: common
        }});
        new Chart(document.getElementById('abChartErr'), {{
            type: 'line',
            data: {{
                labels: D.labels,
                datasets: [
                    {{ label: na + ' error %', data: D.err_a, borderColor: '#dc2626', tension: 0.2, fill: false }},
                    {{ label: nb + ' error %', data: D.err_b, borderColor: '#f97316', tension: 0.2, fill: false }}
                ]
            }},
            options: common
        }});
    }})();
    </script>
</body>
</html>"""
    return html_out

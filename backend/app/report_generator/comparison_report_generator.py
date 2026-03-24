"""
Comparison Report Generator
Generates HTML reports comparing baseline vs current run for JMeter (transactions/requests)
and Lighthouse/Web Vitals (pages), in the same style as single-run JMeter and Web Vitals reports.
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import html as html_module


def _get_jmeter_stats(metrics: Optional[Dict]) -> tuple:
    """Extract transaction_stats and request_stats from JMeter metrics."""
    if not metrics:
        return {}, {}
    summary = metrics.get("summary", {})
    trans = summary.get("transaction_stats", {})
    req = summary.get("request_stats", {})
    return trans, req


def _get_lighthouse_pages(metrics: Optional[Dict]) -> Dict[str, Dict]:
    """Extract page-level metrics from Lighthouse/Web Vitals data."""
    if not metrics:
        return {}
    if "pages" in metrics and isinstance(metrics["pages"], dict):
        return metrics["pages"]
    if isinstance(metrics, list):
        return {p.get("url", p.get("page_url", "Unknown")): p for p in metrics}
    url = metrics.get("url", metrics.get("page_url", "default_page"))
    return {url: metrics} if url else {}


def _format_ms(ms: Any) -> str:
    if ms is None:
        return "N/A"
    try:
        v = float(ms)
        if v >= 1000:
            return f"{v/1000:.2f}s"
        return f"{v:.0f}ms"
    except (TypeError, ValueError):
        return "N/A"


def _change_class(change_pct: Optional[float], lower_is_better: bool) -> str:
    if change_pct is None:
        return ""
    if abs(change_pct) < 5:
        return "stable"
    if lower_is_better:
        return "regression" if change_pct > 0 else "improvement"
    return "improvement" if change_pct > 0 else "regression"


def generate_comparison_html_report(
    baseline_run_id: str,
    current_run_id: str,
    comparison_type: str,
    overall_score: Optional[float],
    backend_score: Optional[float],
    frontend_score: Optional[float],
    reliability_score: Optional[float],
    verdict: str,
    regression_count: int,
    improvement_count: int,
    stable_count: int,
    summary_text: Optional[str],
    comparison_data: Optional[Dict[str, Any]],
    baseline_metrics: Dict[str, Dict],
    current_metrics: Dict[str, Dict],
) -> str:
    """
    Generate a full HTML comparison report similar to JMeter/Web Vitals reports.
    Shows baseline vs current for transactions, requests, and pages with change % and status.
    """
    current_date = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    verdict_display = {
        "approved": "Release Approved",
        "monitor": "Monitor",
        "approval_needed": "Approval Needed",
        "blocked": "Release Blocked",
    }.get(verdict, verdict or "N/A")
    verdict_color = {
        "approved": "#10b981",
        "monitor": "#f59e0b",
        "approval_needed": "#ef4444",
        "blocked": "#dc2626",
    }.get(verdict, "#6b7280")

    jmeter_section = _build_jmeter_comparison_section(
        baseline_metrics.get("jmeter"),
        current_metrics.get("jmeter"),
        comparison_data.get("jmeter", {}) if comparison_data else {},
    )
    lighthouse_section = _build_lighthouse_comparison_section(
        baseline_metrics.get("lighthouse") or baseline_metrics.get("web_vitals"),
        current_metrics.get("lighthouse") or current_metrics.get("web_vitals"),
        comparison_data.get("lighthouse", {}) if comparison_data else {},
    )
    regressions_section = _build_regressions_section(comparison_data)
    improvements_section = _build_improvements_section(comparison_data)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Comparison Report - {baseline_run_id} vs {current_run_id}</title>
    <style>
        :root {{
            --primary-color: #2563eb;
            --success-color: #059669;
            --warning-color: #d97706;
            --danger-color: #dc2626;
            --border-color: #e2e8f0;
            --bg-light: #f8fafc;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: #f1f5f9; color: #1e293b; line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 1.5rem; }}
        .header {{ background: linear-gradient(135deg, #1e40af 0%, #3b82f6 100%); color: white; padding: 1.5rem 2rem; border-radius: 12px; margin-bottom: 1.5rem; }}
        .header h1 {{ margin: 0; font-size: 1.75rem; }}
        .header p {{ margin: 0.5rem 0 0 0; opacity: 0.95; font-size: 0.95rem; }}
        .pdf-button {{ background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.5); color: white; padding: 0.5rem 1rem; border-radius: 8px; cursor: pointer; font-weight: 600; margin-top: 0.75rem; }}
        .section {{ background: white; padding: 1.5rem; border-radius: 12px; margin-bottom: 1.5rem; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }}
        .section h2 {{ color: var(--primary-color); margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--border-color); font-size: 1.25rem; }}
        .section h3 {{ color: #475569; margin: 1rem 0 0.5rem 0; font-size: 1rem; }}
        table {{ width: 100%; border-collapse: collapse; font-size: 0.875rem; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid var(--border-color); }}
        th {{ background: var(--bg-light); font-weight: 600; color: #475569; }}
        td {{ vertical-align: middle; }}
        .score-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 1rem; margin: 1rem 0; }}
        .score-card {{ background: var(--bg-light); padding: 1rem; border-radius: 8px; text-align: center; }}
        .score-card .value {{ font-size: 1.5rem; font-weight: 700; }}
        .score-card .label {{ font-size: 0.8rem; color: #64748b; margin-top: 0.25rem; }}
        .verdict-badge {{ display: inline-block; padding: 0.5rem 1rem; border-radius: 8px; color: white; font-weight: 600; margin-top: 0.5rem; }}
        .regression {{ color: var(--danger-color); font-weight: 600; }}
        .improvement {{ color: var(--success-color); font-weight: 600; }}
        .stable {{ color: #64748b; }}
        .change-up {{ color: var(--danger-color); }}
        .change-down {{ color: var(--success-color); }}
        .two-cols {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }}
        @media (max-width: 768px) {{ .two-cols {{ grid-template-columns: 1fr; }} }}
        ul {{ margin: 0.5rem 0 0 1rem; padding: 0; }}
        li {{ margin-bottom: 0.35rem; }}
        .no-print {{ display: block; }}
        @media print {{ .no-print {{ display: none !important; }} }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Performance Comparison Report</h1>
            <p>Baseline: <strong>{html_module.escape(baseline_run_id)}</strong> &nbsp; vs &nbsp; Current: <strong>{html_module.escape(current_run_id)}</strong></p>
            <p style="margin-top: 0.5rem; font-size: 0.9rem;">Comparison type: {html_module.escape(comparison_type)} &nbsp;|&nbsp; {current_date}</p>
            <button onclick="window.print()" class="pdf-button no-print">Save as PDF</button>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="verdict-badge" style="background: {verdict_color};">
                {html_module.escape(verdict_display)}
            </div>
            <div class="score-grid">
                <div class="score-card">
                    <div class="value">{overall_score if overall_score is not None else "N/A"}</div>
                    <div class="label">Overall Score</div>
                </div>
                <div class="score-card">
                    <div class="value">{backend_score if backend_score is not None else "N/A"}</div>
                    <div class="label">Backend (JMeter)</div>
                </div>
                <div class="score-card">
                    <div class="value">{frontend_score if frontend_score is not None else "N/A"}</div>
                    <div class="label">Frontend (UX)</div>
                </div>
                <div class="score-card">
                    <div class="value">{reliability_score if reliability_score is not None else "N/A"}</div>
                    <div class="label">Reliability</div>
                </div>
                <div class="score-card">
                    <div class="value">{regression_count}</div>
                    <div class="label">Regressions</div>
                </div>
                <div class="score-card">
                    <div class="value">{improvement_count}</div>
                    <div class="label">Improvements</div>
                </div>
                <div class="score-card">
                    <div class="value">{stable_count or 0}</div>
                    <div class="label">Stable</div>
                </div>
            </div>
            {f'<div style="margin-top: 1rem; padding: 1rem; background: var(--bg-light); border-radius: 8px; white-space: pre-wrap; font-size: 0.9rem;">{html_module.escape(summary_text or "")}</div>' if summary_text else ""}
        </div>

        {jmeter_section}

        {lighthouse_section}

        {regressions_section}

        {improvements_section}
    </div>
</body>
</html>"""
    return html


def _build_jmeter_comparison_section(
    baseline_jmeter: Optional[Dict],
    current_jmeter: Optional[Dict],
    jmeter_results: Dict,
) -> str:
    """Build JMeter transactions/requests comparison table (baseline vs current)."""
    b_trans, b_req = _get_jmeter_stats(baseline_jmeter)
    c_trans, c_req = _get_jmeter_stats(current_jmeter)
    b_all = {**b_trans, **b_req}
    c_all = {**c_trans, **c_req}
    all_labels = sorted(set(b_all.keys()) | set(c_all.keys()))
    if not all_labels:
        return '<div class="section"><h2>JMeter (Transactions &amp; Requests)</h2><p>No transaction or request data available for either run.</p></div>'

    regressions_by_key = {(r.get("transaction_name") or r.get("metric_name")): r for r in jmeter_results.get("regressions", [])}
    improvements_by_key = {(r.get("transaction_name") or r.get("metric_name")): r for r in jmeter_results.get("improvements", [])}
    stable_by_key = {(r.get("transaction_name") or r.get("metric_name")): r for r in jmeter_results.get("stable_metrics", [])}

    rows = []
    for label in all_labels:
        b_row = b_all.get(label, {})
        c_row = c_all.get(label, {})
        b_avg = (b_row.get("avg_response") or 0) / 1000.0
        b_p95 = (b_row.get("p95") or 0) / 1000.0
        b_err = b_row.get("error_rate") or 0
        c_avg = (c_row.get("avg_response") or 0) / 1000.0
        c_p95 = (c_row.get("p95") or 0) / 1000.0
        c_err = c_row.get("error_rate") or 0

        avg_chg = None
        if b_avg and c_avg is not None:
            avg_chg = ((c_avg - b_avg) / b_avg) * 100 if b_avg else 0
        p95_chg = None
        if b_p95 and c_p95 is not None:
            p95_chg = ((c_p95 - b_p95) / b_p95) * 100 if b_p95 else 0
        err_chg = None
        if b_err is not None and c_err is not None:
            err_chg = c_err - b_err

        status = ""
        status_class = "stable"
        if label in regressions_by_key:
            status = "Regression"
            status_class = "regression"
        elif label in improvements_by_key:
            status = "Improvement"
            status_class = "improvement"
        elif label in stable_by_key:
            status = "Stable"
            status_class = "stable"
        elif not b_row and c_row:
            status = "New"
            status_class = "improvement"
        elif b_row and not c_row:
            status = "Removed"
            status_class = "regression"

        def chg_cell(val: Optional[float], lower_is_better: bool) -> str:
            if val is None:
                return "<td>—</td>"
            cls = "change-down" if (val < 0 and lower_is_better) or (val > 0 and not lower_is_better) else "change-up"
            sign = "+" if val > 0 else ""
            return f'<td class="{cls}">{sign}{val:.1f}%</td>'

        rows.append(
            f"<tr>"
            f"<td style='font-weight:600;'>{html_module.escape(label[:80])}</td>"
            f"<td>{b_avg:.2f}s</td><td>{b_p95:.2f}s</td><td>{b_err:.2f}%</td>"
            f"<td>{c_avg:.2f}s</td><td>{c_p95:.2f}s</td><td>{c_err:.2f}%</td>"
            f"{chg_cell(avg_chg, True)}{chg_cell(p95_chg, True)}"
            f"<td class='{status_class}'>{status}</td>"
            f"</tr>"
        )

    return f"""<div class="section">
        <h2>JMeter – Transactions &amp; Requests Comparison</h2>
        <p style="margin-bottom: 1rem;">Baseline vs Current run for each transaction/request. Green = improvement, red = regression.</p>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Transaction / Request</th>
                        <th colspan="3" style="text-align: center;">Baseline</th>
                        <th colspan="3" style="text-align: center;">Current</th>
                        <th colspan="2" style="text-align: center;">Change %</th>
                        <th>Status</th>
                    </tr>
                    <tr>
                        <th></th>
                        <th>Avg</th><th>P95</th><th>Err%</th>
                        <th>Avg</th><th>P95</th><th>Err%</th>
                        <th>Avg</th><th>P95</th>
                        <th></th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
    </div>"""


def _build_lighthouse_comparison_section(
    baseline_lh: Optional[Dict],
    current_lh: Optional[Dict],
    lighthouse_results: Dict,
) -> str:
    """Build Lighthouse/Web Vitals pages comparison table."""
    b_pages = _get_lighthouse_pages(baseline_lh)
    c_pages = _get_lighthouse_pages(current_lh)
    if not b_pages and not c_pages:
        return '<div class="section"><h2>Lighthouse / Web Vitals – Pages Comparison</h2><p>No page data available for either run.</p></div>'

    metric_keys = [
        ("performance_score", "Perf Score", False),
        ("lcp", "LCP (ms)", True),
        ("fid", "FID (ms)", True),
        ("cls", "CLS", True),
        ("fcp", "FCP (ms)", True),
        ("ttfb", "TTFB (ms)", True),
    ]
    reg_list = lighthouse_results.get("regressions", [])
    imp_list = lighthouse_results.get("improvements", [])
    stable_list = lighthouse_results.get("stable_metrics", [])

    def find_status(page_url: str, metric_name: str) -> tuple:
        for r in reg_list:
            if (r.get("page_url") or r.get("transaction_name")) == page_url and r.get("metric_name") == metric_name:
                return "Regression", "regression"
        for r in imp_list:
            if (r.get("page_url") or r.get("transaction_name")) == page_url and r.get("metric_name") == metric_name:
                return "Improvement", "improvement"
        for r in stable_list:
            if (r.get("page_url") or r.get("transaction_name")) == page_url and r.get("metric_name") == metric_name:
                return "Stable", "stable"
        return "", "stable"

    all_pages = sorted(set(b_pages.keys()) | set(c_pages.keys()))
    rows = []
    for page_url in all_pages:
        b_page = b_pages.get(page_url, {})
        c_page = c_pages.get(page_url, {})
        for mkey, mlabel, lower_is_better in metric_keys:
            b_val = b_page.get(mkey)
            c_val = c_page.get(mkey)
            if b_val is None and c_val is None:
                continue
            b_str = _format_ms(b_val) if mkey != "performance_score" and mkey != "cls" else (f"{b_val:.0f}" if b_val is not None else "N/A")
            if mkey == "cls" and b_val is not None:
                b_str = f"{b_val:.3f}"
            c_str = _format_ms(c_val) if mkey != "performance_score" and mkey != "cls" else (f"{c_val:.0f}" if c_val is not None else "N/A")
            if mkey == "cls" and c_val is not None:
                c_str = f"{c_val:.3f}"
            chg = None
            if b_val is not None and c_val is not None and (isinstance(b_val, (int, float)) and isinstance(c_val, (int, float))):
                if b_val != 0:
                    chg = ((c_val - b_val) / b_val) * 100
                else:
                    chg = 100.0 if c_val != 0 else 0
            status_txt, status_cls = find_status(page_url, mkey)
            chg_cls = ""
            if chg is not None:
                chg_cls = "change-up" if (chg > 0 and lower_is_better) or (chg < 0 and not lower_is_better) else "change-down"
            chg_str = f"{chg:+.1f}%" if chg is not None else "—"
            rows.append(
                f"<tr>"
                f"<td>{html_module.escape(page_url[:60])}</td>"
                f"<td>{mlabel}</td>"
                f"<td>{b_str}</td><td>{c_str}</td>"
                f"<td class='{chg_cls}'>{chg_str}</td>"
                f"<td class='{status_cls}'>{status_txt}</td>"
                f"</tr>"
            )

    if not rows:
        return '<div class="section"><h2>Lighthouse / Web Vitals – Pages Comparison</h2><p>No comparable page metrics found.</p></div>'

    return f"""<div class="section">
        <h2>Lighthouse / Web Vitals – Pages Comparison</h2>
        <p style="margin-bottom: 1rem;">Per-page metrics: Baseline vs Current. Green = improvement, red = regression.</p>
        <div style="overflow-x: auto;">
            <table>
                <thead>
                    <tr>
                        <th>Page</th>
                        <th>Metric</th>
                        <th>Baseline</th>
                        <th>Current</th>
                        <th>Change %</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {"".join(rows)}
                </tbody>
            </table>
        </div>
    </div>"""


def _build_regressions_section(comparison_data: Optional[Dict]) -> str:
    """Build regressions list from comparison_data."""
    if not comparison_data:
        return ""
    jm_reg = comparison_data.get("jmeter", {}).get("regressions", [])
    lh_reg = comparison_data.get("lighthouse", {}).get("regressions", [])
    all_reg = jm_reg + lh_reg
    if not all_reg:
        return ""

    items = []
    for r in all_reg[:50]:
        name = r.get("transaction_name") or r.get("page_url") or r.get("metric_name", "—")
        metric = r.get("metric_name", "")
        bv = r.get("baseline_value")
        cv = r.get("current_value")
        chg = r.get("change_percent")
        sev = r.get("severity", "")
        bv_str = f"{bv:.2f}" if isinstance(bv, (int, float)) else str(bv)
        cv_str = f"{cv:.2f}" if isinstance(cv, (int, float)) else str(cv)
        chg_str = f"{chg:+.1f}%" if isinstance(chg, (int, float)) else ""
        items.append(f"<li><strong>{html_module.escape(str(name))}</strong> {html_module.escape(str(metric))}: {bv_str} → {cv_str} {chg_str} <span class='regression'>({sev})</span></li>")

    return f"""<div class="section">
        <h2>Regressions</h2>
        <ul>{''.join(items)}</ul>
    </div>"""


def _build_improvements_section(comparison_data: Optional[Dict]) -> str:
    """Build improvements list from comparison_data."""
    if not comparison_data:
        return ""
    jm_imp = comparison_data.get("jmeter", {}).get("improvements", [])
    lh_imp = comparison_data.get("lighthouse", {}).get("improvements", [])
    all_imp = jm_imp + lh_imp
    if not all_imp:
        return ""

    items = []
    for r in all_imp[:50]:
        name = r.get("transaction_name") or r.get("page_url") or r.get("metric_name", "—")
        metric = r.get("metric_name", "")
        bv = r.get("baseline_value")
        cv = r.get("current_value")
        chg = r.get("change_percent")
        bv_str = f"{bv:.2f}" if isinstance(bv, (int, float)) else str(bv)
        cv_str = f"{cv:.2f}" if isinstance(cv, (int, float)) else str(cv)
        chg_str = f"{chg:+.1f}%" if isinstance(chg, (int, float)) else ""
        items.append(f"<li><strong>{html_module.escape(str(name))}</strong> {html_module.escape(str(metric))}: {bv_str} → {cv_str} {chg_str} <span class='improvement'>Improvement</span></li>")

    return f"""<div class="section">
        <h2>Improvements</h2>
        <ul>{''.join(items)}</ul>
    </div>"""

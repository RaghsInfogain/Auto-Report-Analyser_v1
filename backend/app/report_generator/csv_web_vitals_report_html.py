"""Editorial tabbed HTML for CSV-based Web Vitals reports (same chrome as JMeter combined / Lighthouse)."""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from app.report_generator.combined_load_report_html import _COMBINED_CSS, _BRAND_TAGLINE, _brand_logo_data_uri
from app.report_generator.experience_recommendations_html import recommendations_panel_html


def _score_class(metric: str, value: float) -> str:
    if metric == "lcp":
        return "success" if value <= 2500 else "warning" if value <= 4000 else "danger"
    if metric == "inp":
        return "success" if value <= 200 else "warning" if value <= 500 else "danger"
    if metric == "fid":
        return "success" if value <= 100 else "warning" if value <= 300 else "danger"
    if metric == "cls":
        return "success" if value <= 0.1 else "warning" if value <= 0.25 else "danger"
    if metric == "fcp":
        return "success" if value <= 1800 else "warning" if value <= 3000 else "danger"
    if metric == "ttfb":
        return "success" if value <= 800 else "warning" if value <= 1800 else "danger"
    return "warning"


def _kpi_class(metric: str, value: float) -> str:
    sc = _score_class(metric, value)
    if sc == "success":
        return "green"
    if sc == "danger":
        return "red"
    return "amber"


def render_csv_web_vitals_editorial_html(metrics: Dict[str, Any], filename: str = "web_vitals_report.csv") -> str:
    current_date = datetime.now().strftime("%d %B %Y")
    total_samples = int(metrics.get("total_samples") or 0)
    lcp, fid, cls_d, fcp, ttfb, inp_d = (
        metrics.get("lcp") or {},
        metrics.get("fid") or {},
        metrics.get("cls") or {},
        metrics.get("fcp") or {},
        metrics.get("ttfb") or {},
        metrics.get("inp") or {},
    )
    summary = metrics.get("summary") or {}

    lcp_m = float(lcp.get("mean") or 0)
    fid_m = float(fid.get("mean") or 0)
    cls_m = float(cls_d.get("mean") or 0)
    fcp_m = float(fcp.get("mean") or 0)
    ttfb_m = float(ttfb.get("mean") or 0)
    has_inp = inp_d.get("mean") is not None
    inp_mean = float(inp_d["mean"]) if has_inp else 0.0

    title_esc = html.escape(Path(str(filename)).stem or "Web Vitals")
    fname_esc = html.escape(str(filename))
    tag_esc = html.escape(_BRAND_TAGLINE)
    logo_uri = _brand_logo_data_uri()
    header_brand = ""
    if logo_uri:
        header_brand = f"""  <div class="report-header-brand-row">
    <div class="report-brand">
      <img src="{logo_uri}" alt="Autoload.AI" loading="lazy" />
      <div class="report-brand-tagline">{tag_esc}</div>
    </div>
  </div>
"""

    def fmt_row(label: str, d: Dict[str, Any], unit: str = "ms", dec: int = 0) -> str:
        def fv(k: str) -> float:
            return float(d.get(k) or 0)

        if dec == 3:
            return (
                f"<tr><td><strong>{label}</strong></td>"
                f"<td class=\"mono\">{fv('mean'):.{dec}f}{unit}</td>"
                f"<td class=\"mono\">{fv('median'):.{dec}f}{unit}</td>"
                f"<td class=\"mono\">{fv('p95'):.{dec}f}{unit}</td>"
                f"<td class=\"mono\">{fv('p99'):.{dec}f}{unit}</td>"
                f"<td class=\"mono\">{fv('min'):.{dec}f}{unit}</td>"
                f"<td class=\"mono\">{fv('max'):.{dec}f}{unit}</td></tr>"
            )
        return (
            f"<tr><td><strong>{label}</strong></td>"
            f"<td class=\"mono\">{fv('mean'):.0f}{unit}</td>"
            f"<td class=\"mono\">{fv('median'):.0f}{unit}</td>"
            f"<td class=\"mono\">{fv('p95'):.0f}{unit}</td>"
            f"<td class=\"mono\">{fv('p99'):.0f}{unit}</td>"
            f"<td class=\"mono\">{fv('min'):.0f}{unit}</td>"
            f"<td class=\"mono\">{fv('max'):.0f}{unit}</td></tr>"
        )

    detail_rows = (
        fmt_row("LCP", lcp)
        + fmt_row("FID", fid)
        + fmt_row("CLS", cls_d, unit="", dec=3)
        + fmt_row("FCP", fcp)
        + fmt_row("TTFB", ttfb)
        + (fmt_row("INP", inp_d) if has_inp else "")
    )
    details_table = (
        "<table class=\"data-table\"><thead><tr><th>Metric</th><th>Mean</th><th>Median</th><th>P95</th><th>P99</th><th>Min</th><th>Max</th></tr></thead><tbody>"
        + detail_rows
        + "</tbody></table>"
    )

    dist_table = f"""<table class="data-table">
<thead><tr><th>Metric</th><th>Good</th><th>Needs improvement</th><th>Poor</th></tr></thead>
<tbody>
<tr><td><strong>LCP</strong></td><td>{summary.get("lcp_good", 0)}</td><td>{summary.get("lcp_needs_improvement", 0)}</td><td>{summary.get("lcp_poor", 0)}</td></tr>
<tr><td><strong>FID</strong></td><td>{summary.get("fid_good", 0)}</td><td>{summary.get("fid_needs_improvement", 0)}</td><td>{summary.get("fid_poor", 0)}</td></tr>
<tr><td><strong>CLS</strong></td><td>{summary.get("cls_good", 0)}</td><td>{summary.get("cls_needs_improvement", 0)}</td><td>{summary.get("cls_poor", 0)}</td></tr>
</tbody></table>"""

    overview_body = f"""
  <div class="section">
    <div class="section-label">Summary</div>
    <h2 class="section-title">Core Web Vitals snapshot</h2>
    <p class="section-desc">Aggregated from <strong>{total_samples:,}</strong> samples in <strong>{fname_esc}</strong>.</p>
  </div>
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-label">LCP (mean)</div><div class="kpi-value {_kpi_class('lcp', lcp_m)}">{lcp_m:.0f} ms</div><div class="kpi-sub">Target ≤ 2500 ms</div></div>
    <div class="kpi"><div class="kpi-label">FID (mean)</div><div class="kpi-value {_kpi_class('fid', fid_m)}">{fid_m:.0f} ms</div><div class="kpi-sub">Target ≤ 100 ms</div></div>
    <div class="kpi"><div class="kpi-label">CLS (mean)</div><div class="kpi-value {_kpi_class('cls', cls_m)}">{cls_m:.3f}</div><div class="kpi-sub">Target ≤ 0.1</div></div>
    <div class="kpi"><div class="kpi-label">FCP (mean)</div><div class="kpi-value {_kpi_class('fcp', fcp_m)}">{fcp_m:.0f} ms</div><div class="kpi-sub">Target ≤ 1800 ms</div></div>
    <div class="kpi"><div class="kpi-label">TTFB (mean)</div><div class="kpi-value {_kpi_class('ttfb', ttfb_m)}">{ttfb_m:.0f} ms</div><div class="kpi-sub">Target ≤ 800 ms</div></div>
    {f'<div class="kpi"><div class="kpi-label">INP (mean)</div><div class="kpi-value {_kpi_class("inp", inp_mean)}">{inp_mean:.0f} ms</div><div class="kpi-sub">Target ≤ 200 ms</div></div>' if has_inp else ""}
  </div>
"""

    details_panel = f"""
<div class="section">
  <div class="section-label">Statistics</div>
  <h2 class="section-title">Detailed statistics</h2>
  <p class="section-desc">Distribution of each metric across uploaded samples.</p>
  <div style="overflow-x:auto">{details_table}</div>
</div>
"""

    dist_panel = f"""
<div class="section">
  <div class="section-label">Quality mix</div>
  <h2 class="section-title">Good / needs improvement / poor</h2>
  <p class="section-desc">Counts using standard Web Vitals thresholds (same bins as the prior report).</p>
  {dist_table}
</div>
"""

    tab_ids = ["overview", "details", "distribution", "recommendations"]
    nav_labels = ["Overview", "Details", "Distribution", "Recommendations"]
    nav_html = "".join(
        f"""<button class="{'nav-btn active' if tid == tab_ids[0] else 'nav-btn'}" onclick="show('{tid}')">{lab}</button>\n"""
        for tid, lab in zip(tab_ids, nav_labels)
    )
    rec_panel = recommendations_panel_html(title_esc, report_context="web_vitals")
    tab_js_ids = json.dumps(tab_ids)
    show_script = f"""<script>
function show(id) {{
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  const el = document.getElementById('panel-'+id);
  if(el) el.classList.add('active');
  const btns=[...document.querySelectorAll('.nav-btn')];
  const ids={tab_js_ids};
  const idx = ids.indexOf(id);
  if(idx>=0 && btns[idx]) btns[idx].classList.add('active');
  window.scrollTo({{top:0,behavior:'smooth'}});
}}
</script>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title_esc} · Web Vitals Report</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;1,9..144,300&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
{_COMBINED_CSS}
</style>
</head>
<body>
<div class="report-header">
{header_brand}  <div class="header-eyebrow">Performance Engineering · Web Vitals · Confidential</div>
  <h1 class="header-title">{title_esc}<br>Web Vitals Report</h1>
  <div class="header-sub">CSV aggregate · {html.escape(current_date)} · {total_samples:,} samples</div>
  <div class="header-meta">
    <div class="header-meta-item"><span class="header-meta-label">Source file</span><span class="header-meta-value">{fname_esc}</span></div>
    <div class="header-meta-item"><span class="header-meta-label">Prepared by</span><span class="header-meta-value">Raghvendra Kumar</span></div>
  </div>
</div>
<nav class="sticky-nav">
{nav_html}
</nav>
<div id="panel-overview" class="panel active"><div class="page">{overview_body}</div></div>
<div id="panel-details" class="panel"><div class="page">{details_panel}</div></div>
<div id="panel-distribution" class="panel"><div class="page">{dist_panel}</div></div>
{rec_panel}
{show_script}
</body>
</html>"""

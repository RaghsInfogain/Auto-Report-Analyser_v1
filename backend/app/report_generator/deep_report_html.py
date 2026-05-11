"""HTML fragments for Deep System Health Assessment (JMeter reports)."""
from __future__ import annotations

import html
import json
from typing import Any, Dict, List


def _esc(s: Any) -> str:
    return html.escape(str(s))


def _tone_color(tone: str) -> str:
    return {
        "ok": "#0f172a",
        "neutral": "#0f172a",
        "warn": "#c2410c",
        "bad": "#b91c1c",
    }.get(tone or "neutral", "#0f172a")


def _kpi_card(c: Dict[str, Any]) -> str:
    col = _tone_color(c.get("tone"))
    return f"""
        <div style="background:#ffffff;border-radius:12px;padding:1.1rem 1.15rem;border:1px solid #e5e7eb;">
          <div style="font-size:0.78rem;color:#64748b;text-transform:uppercase;letter-spacing:0.04em;">{_esc(c.get("label"))}</div>
          <div style="font-size:1.45rem;font-weight:800;color:{col};margin:0.35rem 0;">{_esc(c.get("value"))}</div>
          <div style="font-size:0.82rem;color:#475569;line-height:1.4;">{_esc(c.get("sub"))}</div>
        </div>"""


def _health_card(h: Dict[str, Any]) -> str:
    badge = h.get("badge", "")
    tone = h.get("tone", "neutral")
    bc = {"red": "#fee2e2", "orange": "#ffedd5", "green": "#dcfce7", "neutral": "#f1f5f9"}.get(tone, "#f8fafc")
    fc = {"red": "#b91c1c", "orange": "#c2410c", "green": "#166534", "neutral": "#334155"}.get(tone, "#334155")
    fill = float(h.get("fill_pct") or 0)
    bar = min(100, max(0, fill))
    return f"""
        <div style="background:white;border-radius:12px;padding:1rem 1.1rem;border:1px solid #e2e8f0;position:relative;">
          <span style="position:absolute;top:10px;right:10px;font-size:0.68rem;font-weight:700;padding:0.2rem 0.55rem;border-radius:8px;background:{bc};color:{fc};">{_esc(badge)}</span>
          <div style="font-size:0.72rem;color:#64748b;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:0.5rem;">{_esc(h.get("title"))}</div>
          <div style="font-size:1rem;font-weight:700;color:{fc};margin-bottom:0.5rem;">{_esc(h.get("main"))}</div>
          <div style="height:8px;background:#f1f5f9;border-radius:6px;overflow:hidden;margin-bottom:0.5rem;">
            <div style="width:{bar:.1f}%;height:100%;background:{fc};opacity:0.85;"></div>
          </div>
          <div style="font-size:0.8rem;color:#64748b;line-height:1.45;">{_esc(h.get("footer"))}</div>
        </div>"""


def render_executive_title_block(hdr: Dict[str, Any]) -> str:
    if not hdr:
        return ""
    return f"""
        <div style="margin: 0 0 1.25rem 0; color: #0f172a; text-align: center;">
          <p style="margin:0;font-size:0.8125rem;color:#0f172a;">{_esc(hdr.get("line1"))}</p>
          <h1 style="margin:0.65rem 0;font-size:1.875rem;font-weight:600;font-family:Georgia,'Times New Roman',Times,serif;line-height:1.2;">{_esc(hdr.get("line2"))}</h1>
          <p style="margin:0;font-size:0.9375rem;color:#0f172a;">{_esc(hdr.get("line3"))}</p>
        </div>"""


def render_report_top_header(
    hdr: Dict[str, Any],
    *,
    consolidated_extra_html: str = "",
    pdf_button_html: str = "",
) -> str:
    """Centered three-line title band (white). PDF control absolutely positioned top-right."""
    if not hdr or not (hdr.get("line1") or hdr.get("line2")):
        return ""
    line1 = _esc(hdr.get("line1") or "")
    line2 = _esc(hdr.get("line2") or "")
    line3 = _esc(hdr.get("line3") or "")
    return f"""
    <header class="report-page-title-header" style="background:#ffffff;color:#0f172a;padding:1.75rem 1rem 1.5rem;border-bottom:1px solid #e5e7eb;">
      <div class="container" style="position:relative;max-width:1200px;margin:0 auto;">
        <div class="no-print" style="position:absolute;right:0;top:0;z-index:2;">
          {pdf_button_html}
        </div>
        <div style="text-align:center;padding:0 6rem 0 1rem;max-width:920px;margin:0 auto;">
          {f'<p style="margin:0;font-size:0.8125rem;font-weight:400;color:#0f172a;">{line1}</p>' if line1 else ''}
          {f'<h1 style="margin:0.65rem 0;font-size:1.875rem;font-weight:600;font-family:Georgia,&quot;Times New Roman&quot;,Times,serif;color:#0f172a;line-height:1.2;">{line2}</h1>' if line2 else ''}
          {f'<p style="margin:0;font-size:0.9375rem;font-weight:400;color:#0f172a;">{line3}</p>' if line3 else ''}
          {consolidated_extra_html}
        </div>
      </div>
    </header>"""


def _finding_icon_span(tone: str) -> str:
    t = (tone or "neutral").lower()
    if t == "ok":
        return '<span aria-hidden="true" title="Positive">✅</span>'
    if t in ("warn", "warning"):
        return '<span aria-hidden="true" title="Attention">⚠️</span>'
    if t in ("bad", "danger", "critical"):
        return '<span aria-hidden="true" title="Critical">❌</span>'
    return '<span aria-hidden="true" style="color:#64748b;" title="Note">•</span>'


def render_key_findings_list(items: List[Dict[str, Any]]) -> str:
    if not items:
        return ""
    parts: List[str] = []
    for it in items:
        text = it.get("text") or ""
        tone = it.get("tone") or "neutral"
        inner = text if it.get("html") else _esc(text)
        parts.append(
            f'''<li style="display:flex;gap:0.65rem;align-items:flex-start;margin:0 0 0.75rem 0;line-height:1.55;font-size:0.98rem;list-style:none;">
            <span style="flex-shrink:0;width:1.35rem;text-align:center;margin-top:0.1rem;">{_finding_icon_span(tone)}</span>
            <span style="flex:1;color:#0f172a;">{inner}</span>
            </li>'''
        )
    return f'<ul style="margin:0;padding:0;">{"".join(parts)}</ul>'


def render_kpi_grid(cards: List[Dict[str, Any]]) -> str:
    inner = "".join(_kpi_card(c) for c in cards)
    return f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:0.85rem;margin-top:1rem;">{inner}</div>'


def render_overall_health_section(cards: List[Dict[str, Any]]) -> str:
    if not cards:
        return ""
    inner = "".join(_health_card(h) for h in cards[:4])
    return f"""
        <div style="background: rgba(255,255,255,0.96); padding: 1.35rem; border-radius: 10px; margin-top: 1.25rem; color: var(--text-primary); border:1px solid #e5e7eb;">
          <h3 style="margin:0 0 1rem 0;font-size:0.85rem;letter-spacing:0.12em;color:#64748b;font-weight:700;">OVERALL SYSTEM HEALTH</h3>
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:0.9rem;">{inner}</div>
        </div>"""


def render_deep_charts_script(
    labels: List[float],
    rt: List[float],
    vu: List[float],
    tps: List[float],
    err_pct: List[float],
) -> str:
    """JSON arrays for Chart.js canvases in deep assessment."""
    payload = {
        "labels": labels,
        "rt": rt,
        "vu": vu,
        "tps": tps,
        "err": err_pct,
    }
    j = json.dumps(payload)
    return f"""
<script>
(function() {{
  const D = {j};
  function dualLine(id, title, leftLabel, dsA, dsB) {{
    const ctx = document.getElementById(id);
    if (!ctx || typeof Chart === 'undefined') return;
    new Chart(ctx, {{
      type: 'line',
      data: {{ labels: D.labels, datasets: [dsA, dsB] }},
      options: {{
        responsive: true,
        interaction: {{ mode: 'index', intersect: false }},
        plugins: {{
          title: {{ display: true, text: title }},
          legend: {{ position: 'top' }}
        }},
        scales: {{
          x: {{ title: {{ display: true, text: 'Bucket index' }} }},
          y: {{
            type: 'linear', position: 'left',
            title: {{ display: true, text: leftLabel }},
            grid: {{ color: 'rgba(0,0,0,0.06)' }}
          }},
          y1: {{
            type: 'linear', position: 'right',
            title: {{ display: true, text: 'Virtual users' }},
            grid: {{ drawOnChartArea: false }}
          }}
        }}
      }}
    }});
  }}
  dualLine(
    'deepChartRT',
    'Response time vs concurrent users — trend',
    'Mean RT (s)',
    {{ label: 'Mean RT (s)', data: D.rt, borderColor: '#dc2626', tension: 0.2, fill: false, yAxisID: 'y' }},
    {{ label: 'VUsers', data: D.vu, borderColor: '#16a34a', borderDash: [4,4], tension: 0.1, fill: false, yAxisID: 'y1' }}
  );
  dualLine(
    'deepChartTPS',
    'Throughput (TPS) vs load — saturation curve',
    'TPS (pass)',
    {{ label: 'TPS (pass)', data: D.tps, borderColor: '#2563eb', backgroundColor: 'rgba(37,99,235,0.12)', tension: 0.2, fill: true, yAxisID: 'y' }},
    {{ label: 'VUsers', data: D.vu, borderColor: '#16a34a', borderDash: [4,4], tension: 0.1, fill: false, yAxisID: 'y1' }}
  );
  const ctxE = document.getElementById('deepChartErr');
  if (ctxE && typeof Chart !== 'undefined') {{
    new Chart(ctxE, {{
      type: 'line',
      data: {{
        labels: D.labels,
        datasets: [
          {{ label: 'Error %', data: D.err, borderColor: '#b91c1c', backgroundColor: 'rgba(185,28,28,0.12)', tension: 0.15, fill: true, yAxisID: 'y' }},
          {{ label: 'VUsers', data: D.vu, borderColor: '#64748b', borderDash: [3,3], tension: 0.1, fill: false, yAxisID: 'y1' }}
        ]
      }},
      options: {{
        responsive: true,
        plugins: {{
          title: {{ display: true, text: 'Error rate vs concurrent users — correlation' }},
          legend: {{ position: 'top' }}
        }},
        scales: {{
          x: {{}},
          y: {{ type: 'linear', position: 'left', title: {{ display: true, text: 'Error %' }} }},
          y1: {{ type: 'linear', position: 'right', title: {{ display: true, text: 'VUsers' }}, grid: {{ drawOnChartArea: false }} }}
        }}
      }}
    }});
  }}
}})();
</script>"""


def render_deep_system_health_body(
    deep: Dict[str, Any],
    chart_labels: List[str],
    chart_rt: List[float],
    chart_vu: List[float],
    chart_tps: List[float],
    chart_err: List[float],
) -> str:
    key_ps = "".join(
        f'<p style="margin:0 0 0.65rem 0;line-height:1.55;font-size:0.95rem;">{_esc(p)}</p>'
        for p in deep.get("key_paragraphs") or []
    )
    zones = deep.get("response_time") or {}
    zone_html = ""
    for z in zones.get("zones_intro") or []:
        zone_html += f"""
        <div style="margin:0.6rem 0;padding:0.85rem;border-radius:10px;border:1px solid #d9e2ec;background:#f8fafc;">
          <strong>{_esc(z.get("zone"))}</strong> — <span style="color:#64748b;">{_esc(z.get("range"))}</span>
          <p style="margin:0.35rem 0 0 0;font-size:0.88rem;">{_esc(z.get("summary"))}</p>
        </div>"""
    band_rows = ""
    for row in zones.get("band_table") or []:
        band_rows += f"""<tr>
            <td>{_esc(row.get("band"))}</td>
            <td>{_esc(row.get("users"))}</td>
            <td style="text-align:right">{_esc(row.get("median"))}</td>
            <td style="text-align:right">{_esc(row.get("p90"))}</td>
            <td style="text-align:right">{_esc(row.get("err"))}%</td>
            <td><span style="padding:0.15rem 0.5rem;border-radius:6px;font-size:0.75rem;background:{'#dcfce7' if row.get('sla')=='PASS' else '#fee2e2'};">{_esc(row.get("sla"))}</span></td>
        </tr>"""
    tps_rows = ""
    for row in (deep.get("throughput") or {}).get("by_band") or []:
        tps_rows += f"<tr><td>{_esc(row.get('band'))}</td><td style='text-align:right'>{_esc(row.get('tps'))}</td></tr>"
    narr = ""
    for n in (deep.get("throughput") or {}).get("narrative") or []:
        c = {"green": "#166534", "orange": "#c2410c", "red": "#b91c1c"}.get(n.get("tone"), "#334155")
        narr += f"""<div style="border-left:4px solid {c};padding:0.6rem 0.85rem;margin:0.5rem 0;background:#fafafa;border-radius:0 8px 8px 0;">
            <strong style="color:{c};">{_esc(n.get("title"))}</strong>
            <p style="margin:0.25rem 0 0 0;font-size:0.88rem;">{_esc(n.get("body"))}</p>
        </div>"""
    es = (deep.get("errors") or {}).get("summary") or {}
    err_tx = "".join(
        f"<tr><td>{_esc(r.get('transaction'))}</td><td style='text-align:right'>{r.get('total_err')}</td><td style='text-align:right'>{r.get('err_rate')}%</td></tr>"
        for r in (deep.get("errors") or {}).get("by_transaction") or []
    )
    rc_html = ""
    for h in deep.get("root_causes") or []:
        conf = int(h.get("confidence") or 0)
        rc_html += f"""
        <div style="margin:1rem 0;padding:1rem;border:1px solid #e2e8f0;border-radius:12px;background:white;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:0.5rem;flex-wrap:wrap;">
            <span style="font-size:0.75rem;font-weight:700;background:#fee2e2;color:#991b1b;padding:0.2rem 0.55rem;border-radius:8px;">{_esc(h.get("id"))}</span>
            <span style="font-size:0.72rem;background:#dbeafe;color:#1e40af;padding:0.2rem 0.55rem;border-radius:8px;">Confidence {conf}%</span>
          </div>
          <h4 style="margin:0.5rem 0;font-size:1rem;">{_esc(h.get("title"))}</h4>
          <p style="margin:0;font-size:0.9rem;color:#334155;line-height:1.55;">{_esc(h.get("text"))}</p>
          <div style="margin-top:0.75rem;padding:0.75rem;background:#faf6f0;border-radius:8px;font-size:0.85rem;color:#444;">{_esc(h.get("evidence"))}</div>
        </div>"""
    script = render_deep_charts_script(
        [float(x) for x in chart_labels],
        chart_rt,
        chart_vu,
        chart_tps,
        chart_err,
    )
    rt_cards = "".join(
        _kpi_card(x)
        for x in (deep.get("response_time") or {}).get("cards") or []
    )
    err_cards = f"""
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:0.65rem;margin:0.75rem 0;">
          <div style="background:#faf6f0;border-radius:10px;padding:0.75rem;border:1px solid #e8dfd0;"><div style="font-size:0.7rem;color:#64748b;">Total errors</div><div style="font-weight:800;font-size:1.1rem;">{es.get("total",0):,}</div><div style="font-size:0.75rem;">{es.get("rate_pct",0):.2f}%</div></div>
          <div style="background:#faf6f0;border-radius:10px;padding:0.75rem;border:1px solid #e8dfd0;"><div style="font-size:0.7rem;color:#64748b;">Client 4xx</div><div style="font-weight:800;font-size:1.1rem;">{es.get("client_4xx",0):,}</div><div style="font-size:0.75rem;">{es.get("client_share",0):.1f}% of errors</div></div>
          <div style="background:#faf6f0;border-radius:10px;padding:0.75rem;border:1px solid #e8dfd0;"><div style="font-size:0.7rem;color:#64748b;">Server 5xx</div><div style="font-weight:800;font-size:1.1rem;">{es.get("server_5xx",0):,}</div><div style="font-size:0.75rem;">{es.get("server_share",0):.1f}% of errors</div></div>
          <div style="background:#faf6f0;border-radius:10px;padding:0.75rem;border:1px solid #e8dfd0;"><div style="font-size:0.7rem;color:#64748b;">Corr (err vs RT)</div><div style="font-weight:800;font-size:1.1rem;">R≈{es.get("corr_r",0)}</div></div>
        </div>"""
    return f"""
    <div class="section" id="section-deep-assessment" style="background:#fdfcfa;">
      <h2 style="letter-spacing:0.06em;color:#334155;">Deep System Health Assessment</h2>
      
      <h3 style="margin-top:1.5rem;font-size:0.9rem;letter-spacing:0.1em;color:#64748b;">1 · RESPONSE TIME BEHAVIOUR</h3>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:0.75rem;">{rt_cards}</div>
      <div style="margin:1rem 0;padding:1rem;background:white;border-radius:12px;border:1px solid #e8dfd0;">
        <canvas id="deepChartRT" height="120"></canvas>
      </div>
      <h4 style="font-size:0.82rem;letter-spacing:0.08em;color:#64748b;margin:1rem 0 0.5rem 0;">Response time behaviour zones</h4>
      {zone_html}
      <div style="overflow-x:auto;margin-top:0.75rem;">
        <table class="endpoint-table" style="font-size:0.82rem;">
          <thead><tr><th>Load band</th><th>Users</th><th>Median~</th><th>P90~ (ms)</th><th>Err%</th><th>SLA P90</th></tr></thead>
          <tbody>{band_rows}</tbody>
        </table>
      </div>

      <h3 style="margin-top:2rem;font-size:0.9rem;letter-spacing:0.1em;color:#64748b;">2 · THROUGHPUT ANALYSIS</h3>
      <div style="margin:1rem 0;padding:1rem;background:white;border-radius:12px;border:1px solid #e8dfd0;">
        <canvas id="deepChartTPS" height="120"></canvas>
      </div>
      {narr}
      <h4 style="font-size:0.82rem;letter-spacing:0.08em;color:#64748b;margin:1rem 0 0.5rem 0;">Throughput by load band (TPS summary)</h4>
      <div style="overflow-x:auto;">
        <table class="endpoint-table" style="font-size:0.82rem;"><thead><tr><th>Band</th><th style="text-align:right">Avg TPS</th></tr></thead><tbody>{tps_rows}</tbody></table>
      </div>

      <h3 style="margin-top:2rem;font-size:0.9rem;letter-spacing:0.1em;color:#64748b;">3 · ERROR ANALYSIS</h3>
      {err_cards}
      <div style="margin:1rem 0;padding:1rem;background:white;border-radius:12px;border:1px solid #e8dfd0;">
        <canvas id="deepChartErr" height="120"></canvas>
      </div>
      <h4 style="font-size:0.82rem;letter-spacing:0.08em;color:#64748b;">Errors by transaction (high signal)</h4>
      <div style="overflow-x:auto;">
        <table class="endpoint-table" style="font-size:0.82rem;"><thead><tr><th>Transaction</th><th style="text-align:right">Errors</th><th style="text-align:right">Error %</th></tr></thead><tbody>{err_tx}</tbody></table>
      </div>

      <h3 style="margin-top:2rem;font-size:0.9rem;letter-spacing:0.1em;color:#64748b;">4 · ROOT CAUSE HYPOTHESES</h3>
      <p style="font-size:0.9rem;color:#475569;margin:0 0 0.5rem 0;">Ranked by confidence from error mix, load correlation, and tail behaviour. Each should be confirmed with traces and infra metrics.</p>
      {rc_html}
      {script}
    </div>
    """


def render_structured_issues(issues: List[Dict[str, Any]]) -> str:
    if not issues:
        return """
        <div class="section" id="section-issues"><h2>Critical issues identified</h2>
        <p>No SEV-pattern issues auto-detected. Review the transaction table for edge cases.</p></div>"""
    cards = ""
    for i in issues:
        sev = i.get("severity", "SEV")
        color = "#b91c1c" if sev.endswith("1") else "#c2410c"
        bg = "#fef2f2" if sev.endswith("1") else "#fff7ed"
        cards += f"""
        <div style="margin:0.65rem 0;padding:1rem;border-radius:12px;border:1px solid #e8dfd0;background:{bg};">
          <span style="font-size:0.72rem;font-weight:800;color:{color};">{_esc(sev)}</span>
          <h4 style="margin:0.35rem 0;font-size:1.02rem;">{_esc(i.get("title"))}</h4>
          <p style="margin:0;font-size:0.9rem;color:#334155;line-height:1.55;">{_esc(i.get("body"))}</p>
        </div>"""
    return f"""
    <div class="section" id="section-issues" style="background:#fdfcfa;">
      <h2 style="letter-spacing:0.06em;color:#334155;">CRITICAL ISSUES IDENTIFIED</h2>
      {cards}
    </div>"""


def render_resolution_plan(rows: List[Dict[str, Any]]) -> str:
    tr = ""
    tone_bg = {
        "red": "#fef2f2",
        "orange": "#fff7ed",
        "amber": "#fffbeb",
        "green": "#f0fdf4",
    }
    for r in rows:
        t = r.get("tone", "amber")
        tr += f"""<tr style="background:{tone_bg.get(t,'#fff')};">
        <td style="padding:0.65rem;"><span style="font-size:0.72rem;font-weight:700;padding:0.15rem 0.45rem;border-radius:6px;background:white;border:1px solid #e5e7eb;">{_esc(r.get("phase"))}</span></td>
        <td style="padding:0.65rem;">{_esc(r.get("focus"))}</td>
        <td style="padding:0.65rem;">{_esc(r.get("outcome"))}</td>
        <td style="padding:0.65rem;white-space:nowrap;">{_esc(r.get("timeline"))}</td>
        </tr>"""
    return f"""
    <div class="section" id="section-resolution-plan">
      <h2 style="letter-spacing:0.06em;color:#334155;">PERFORMANCE OPTIMIZATION PLAN</h2>
      <div style="overflow-x:auto;">
        <table class="endpoint-table" style="font-size:0.88rem;">
          <thead><tr><th>Phase</th><th>Focus</th><th>Expected outcome</th><th>Timeline</th></tr></thead>
          <tbody>{tr}</tbody>
        </table>
      </div>
    </div>"""

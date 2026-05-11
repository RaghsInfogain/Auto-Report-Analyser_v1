"""Render Combined Load report HTML (editorial tab layout + Chart.js) from analysis payload."""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.report_generator.combined_load_report_analysis import _distribution_sla_tone_err_pct
from app.report_generator.deep_assessment import performance_grading_methodology_html

_LOGO_PATH = Path(__file__).resolve().parent / "static" / "autoload_ai_logo.png"
_BRAND_TAGLINE = "Performance Engineering without Headache"


def _brand_logo_data_uri() -> str:
    try:
        raw = _LOGO_PATH.read_bytes()
    except OSError:
        return ""
    b64 = base64.standard_b64encode(raw).decode("ascii")
    return f"data:image/png;base64,{b64}"

_COMBINED_CSS = """
:root{
  --ink:#0D0D0B;--paper:#F5F3EE;--cream:#EDE9E1;--rule:#D5D0C5;
  --red:#C0392B;--red-light:#F9E8E7;--red-mid:#E8A09A;
  --amber:#B45309;--amber-light:#FEF3C7;--amber-mid:#F5D78A;
  --green:#2D6A2D;--green-light:#EAF3DA;--green-mid:#A3D17E;
  --blue:#1A4E8C;--blue-light:#E8F0FB;--blue-mid:#6FA3E0;
  --gray:#6B6860;--gray-light:#F0EDE7;
  --mono:'DM Mono',monospace;
  --serif:'Fraunces',Georgia,serif;
  --sans:'Instrument Sans',sans-serif;
}
*{box-sizing:border-box;margin:0;padding:0}
html{font-size:14px;scroll-behavior:smooth}
body{background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.6;-webkit-font-smoothing:antialiased}
.report-header{background:var(--ink);color:var(--paper);padding:3rem 3rem 2.5rem;position:relative;overflow:hidden}
.report-header-brand-row{display:flex;justify-content:space-between;align-items:flex-start;gap:1.5rem;margin-bottom:1.35rem;flex-wrap:wrap}
.report-brand{display:flex;flex-direction:column;align-items:flex-start;gap:0.45rem}
.report-brand img{height:42px;width:auto;display:block;object-fit:contain;max-width:min(280px,100%)}
.report-brand-tagline{font-family:var(--sans);font-size:11px;font-weight:500;font-style:italic;color:#c9b8e8;letter-spacing:.02em;line-height:1.4;max-width:24rem;opacity:.95}
.report-footer-brand{display:flex;align-items:center;gap:0.65rem;margin-top:0.25rem;flex-wrap:wrap}
.report-footer-brand img{height:28px;width:auto;object-fit:contain;opacity:.85}
.report-footer-tagline{font-size:9px;font-style:italic;color:rgba(245,243,238,.45);letter-spacing:.02em}
.report-header::before{content:'';position:absolute;top:-60px;right:-60px;width:300px;height:300px;border-radius:50%;border:1px solid rgba(245,243,238,.08);pointer-events:none}
.report-header::after{content:'';position:absolute;top:-30px;right:-30px;width:180px;height:180px;border-radius:50%;border:1px solid rgba(245,243,238,.06);pointer-events:none}
.header-eyebrow{font-family:var(--mono);font-size:10px;letter-spacing:.12em;text-transform:uppercase;color:rgba(245,243,238,.82);margin-bottom:.6rem}
.header-title{font-family:var(--serif);font-size:2.4rem;font-weight:600;line-height:1.15;margin-bottom:.4rem}
.header-sub{font-family:var(--sans);font-size:13px;color:rgba(245,243,238,.88);margin-bottom:2rem;line-height:1.55}
.header-meta{display:flex;gap:2rem;flex-wrap:wrap}
.header-meta-item{display:flex;flex-direction:column;gap:2px}
.header-meta-label{font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:rgba(245,243,238,.72)}
.header-meta-value{font-family:var(--mono);font-size:12px;color:rgba(245,243,238,.97);font-weight:500}
.key-findings-overview{margin-top:1.5rem;margin-bottom:1.25rem;padding:1.25rem 1.35rem;background:var(--cream);border:1px solid var(--rule);border-radius:2px}
.key-findings-overview .key-findings-label{font-family:var(--mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--gray);margin-bottom:.65rem}
.key-findings-overview .key-findings-list{margin:0;padding-left:1.15rem;color:var(--ink);font-size:13px;line-height:1.65;font-weight:500}
.key-findings-overview .key-findings-list li{margin:.45rem 0;letter-spacing:.015em}
.tx-pct-wrap{overflow-x:auto;margin-top:.75rem;border:1px solid var(--rule);border-radius:2px;background:var(--paper)}
.tx-pct-table{font-size:10px;min-width:1220px;width:100%}
.tx-pct-table th,.tx-pct-table td{text-align:right;white-space:nowrap}
.tx-pct-table th:first-child,.tx-pct-table td:first-child{text-align:left;white-space:normal;max-width:300px;word-break:break-word}
.verdict-strip{display:flex;align-items:flex-start;gap:1rem;margin-top:2rem;padding-top:1.5rem;border-top:1px solid rgba(245,243,238,.12)}
.verdict-pill{background:var(--red);color:#fff;font-family:var(--mono);font-size:11px;font-weight:500;letter-spacing:.08em;padding:5px 14px;border-radius:2px}
.verdict-pill.amber{background:var(--amber)}
.verdict-pill.green{background:var(--green);color:#fff}
.verdict-text{font-size:14px;color:#F5F3EE;font-family:var(--sans);font-weight:500;font-style:normal;line-height:1.65;letter-spacing:.015em;text-rendering:optimizeLegibility;-webkit-font-smoothing:antialiased;white-space:pre-line}
.sticky-nav{position:sticky;top:0;z-index:100;background:var(--paper);border-bottom:1px solid var(--rule);padding:0 3rem;display:flex;gap:0;overflow-x:auto}
.nav-btn{font-family:var(--mono);font-size:10px;letter-spacing:.08em;text-transform:uppercase;padding:.75rem 1.2rem;border:none;background:none;color:var(--gray);cursor:pointer;border-bottom:2px solid transparent;white-space:nowrap;transition:color .15s,border-color .15s}
.nav-btn:hover{color:var(--ink)}
.nav-btn.active{color:var(--ink);border-bottom-color:var(--ink)}
.page{padding:2.5rem 3rem;max-width:1200px}
.section{margin-bottom:3rem}
.section-label{font-family:var(--mono);font-size:9px;letter-spacing:.14em;text-transform:uppercase;color:var(--gray);margin-bottom:1rem;display:flex;align-items:center;gap:.6rem}
.section-label::after{content:'';flex:1;height:1px;background:var(--rule)}
.section-title{font-family:var(--serif);font-size:1.35rem;font-weight:600;margin-bottom:.6rem;line-height:1.3}
.section-desc{font-size:12px;color:var(--gray);margin-bottom:1.5rem;max-width:680px;line-height:1.7}
.panel{display:none}.panel.active{display:block}
.kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin-bottom:2rem}
.kpi{background:var(--paper);padding:1.1rem 1.2rem}
.kpi-label{font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--gray);margin-bottom:.4rem}
.kpi-value{font-family:var(--serif);font-size:1.8rem;font-weight:600;line-height:1;margin-bottom:.2rem}
.kpi-sub{font-family:var(--mono);font-size:10px;color:var(--gray)}
.kpi-value.red{color:var(--red)}
.kpi-value.amber{color:var(--amber)}
.kpi-value.green{color:var(--green)}
.chart-card{background:var(--paper);border:1px solid var(--rule);padding:1.25rem 1.5rem;margin-bottom:1rem}
.chart-title{font-family:var(--sans);font-size:12px;font-weight:600;margin-bottom:.2rem}
.chart-desc{font-family:var(--mono);font-size:9px;color:var(--gray);margin-bottom:.35rem;letter-spacing:.03em}
.chart-observation{font-family:var(--sans);font-size:11px;color:var(--ink);margin-bottom:1rem;line-height:1.65;max-width:52rem;padding:0.65rem 0.85rem;background:var(--gray-light);border-left:3px solid var(--blue);border-radius:0 2px 2px 0}
.chart-wrap{position:relative;width:100%}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:1rem}
.zone{border-left:3px solid;padding:.9rem 1.1rem;margin-bottom:.7rem;background:var(--cream)}
.zone.healthy{border-color:var(--green);background:var(--green-light)}
.zone.warn{border-color:var(--amber);background:var(--amber-light)}
.zone.critical{border-color:var(--red);background:var(--red-light)}
.zone-head{display:flex;align-items:flex-start;gap:.8rem;margin-bottom:.4rem;flex-wrap:wrap}
.zone-label{font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;padding:2px 8px;border-radius:1px;white-space:nowrap;margin-top:2px}
.zone.healthy .zone-label{background:var(--green);color:#fff}
.zone.warn .zone-label{background:var(--amber);color:#fff}
.zone.critical .zone-label{background:var(--red);color:#fff}
.zone-title{font-family:var(--sans);font-size:12px;font-weight:600;flex:1}
.zone-body{font-size:11.5px;line-height:1.75;color:var(--ink)}
.data-table{width:100%;border-collapse:collapse;font-size:11px}
.data-table th{font-family:var(--mono);font-size:9px;letter-spacing:.08em;text-transform:uppercase;color:var(--gray);padding:6px 10px;border-bottom:2px solid var(--rule);text-align:left;white-space:nowrap;font-weight:400}
.data-table td{padding:6px 10px;border-bottom:1px solid var(--rule)}
.data-table tr:last-child td{border-bottom:none}
.data-table tr:hover td{background:var(--cream)}
.data-table .mono{font-family:var(--mono);font-size:10px}
.data-table .red{color:var(--red);font-weight:600}
.data-table .amber{color:var(--amber);font-weight:600}
.data-table .green{color:var(--green)}
.badge{display:inline-block;font-family:var(--mono);font-size:9px;letter-spacing:.06em;padding:2px 8px;border-radius:1px;white-space:nowrap;font-weight:500}
.badge.red{background:var(--red);color:#fff}
.badge.amber{background:var(--amber);color:#fff}
.badge.green{background:var(--green);color:#fff}
.badge.blue{background:var(--blue);color:#fff}
.badge.gray{background:var(--gray);color:#fff}
.badge.outline-red{background:var(--red-light);color:var(--red);border:1px solid var(--red-mid)}
.badge.outline-amber{background:var(--amber-light);color:var(--amber);border:1px solid var(--amber-mid)}
.badge.outline-green{background:var(--green-light);color:var(--green);border:1px solid var(--green-mid)}
.apdex-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:1px;background:var(--rule);border:1px solid var(--rule);margin-bottom:1.5rem}
.apdex-cell{background:var(--paper);padding:.9rem 1rem}
.apdex-name{font-family:var(--mono);font-size:9px;color:var(--gray);margin-bottom:.3rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;letter-spacing:.03em}
.apdex-score{font-family:var(--serif);font-size:1.5rem;font-weight:600;line-height:1;margin-bottom:.3rem}
.apdex-bar-track{background:var(--rule);height:3px;border-radius:1px;overflow:hidden;margin-bottom:.25rem}
.apdex-bar{height:3px;border-radius:1px}
.apdex-rating{font-family:var(--mono);font-size:9px;letter-spacing:.06em}
.rca-card{border:1px solid var(--rule);padding:1.25rem 1.5rem 1.35rem;margin-bottom:1rem;background:#F7F6F2;position:relative;border-radius:2px}
.rca-card::before{content:'';position:absolute;left:0;top:0;bottom:0;width:5px;border-radius:2px 0 0 2px}
.rca-card.sev1::before{background:var(--red)}
.rca-card.sev2::before{background:var(--amber)}
.rca-card.sev3::before{background:var(--blue)}
.rca-top-row{display:flex;justify-content:space-between;align-items:flex-start;gap:1rem;margin-bottom:.35rem;flex-wrap:wrap}
.rca-head-left{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap}
.rca-id-pill{font-family:var(--mono);font-size:9px;padding:4px 9px;background:var(--paper);border:1px solid var(--rule);border-radius:2px;color:var(--gray);letter-spacing:.04em}
.rca-sev-badge{font-family:var(--mono);font-size:8px;letter-spacing:.1em;text-transform:uppercase;padding:4px 11px;border-radius:2px;font-weight:600}
.rca-card.sev1 .rca-sev-badge{background:var(--red);color:#fff}
.rca-card.sev2 .rca-sev-badge{background:var(--amber);color:#1a1a1a}
.rca-conf-pill{font-family:var(--mono);font-size:9px;letter-spacing:.04em;background:#0D3F7C;color:#fff;padding:6px 12px;border-radius:2px;white-space:nowrap}
.rca-headline{font-family:var(--sans);font-size:1rem;font-weight:600;line-height:1.45;margin:.15rem 0 .3rem;color:var(--ink)}
.rca-desc{font-size:11px;color:var(--gray);line-height:1.6;margin-bottom:.5rem}
.rca-hypo{font-size:11.5px;line-height:1.78;color:var(--ink);margin-bottom:.9rem;white-space:pre-line}
.pg-grading{margin-bottom:2rem}
.pg-grading-head{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.75rem;margin-bottom:.75rem}
.pg-overall{text-align:center;padding:1.35rem 1.5rem;border-radius:4px;margin-bottom:1.25rem;border:2px solid var(--rule);background:linear-gradient(145deg,var(--cream),var(--paper));position:relative}
.pg-overall-label{font-family:var(--mono);font-size:9px;letter-spacing:.12em;text-transform:uppercase;color:var(--gray);display:block;margin-bottom:.4rem}
.pg-grade-wrap{position:relative;display:inline-block;cursor:help;margin:.2rem 0}
.pg-grade-letter{font-family:var(--serif);font-size:2.75rem;font-weight:700;line-height:1;color:var(--pg-accent,var(--ink))}
.pg-grade-tip{display:none;position:absolute;left:50%;transform:translateX(-50%);top:calc(100% + 8px);z-index:80;width:min(420px,calc(100vw - 2rem));max-height:70vh;overflow:auto;text-align:left;background:var(--ink);color:var(--paper);padding:1rem 1.1rem;border-radius:4px;font-family:var(--sans);font-size:10px;line-height:1.55;box-shadow:0 12px 40px rgba(0,0,0,.22)}
.pg-grade-wrap:hover .pg-grade-tip,.pg-grade-wrap:focus-within .pg-grade-tip{display:block}
.pg-overall-score{font-family:var(--mono);font-size:11px;color:var(--gray);margin-top:.35rem}
.pg-overall-title{font-family:var(--sans);font-size:1.05rem;font-weight:600;margin:.25rem 0 0 0;color:var(--ink)}
.pg-overall-sub{font-size:11px;color:var(--gray);max-width:720px;margin:.5rem auto 0;line-height:1.55}
.pg-cat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:.85rem;margin-bottom:1.35rem}
@media(max-width:900px){.pg-cat-grid{grid-template-columns:1fr 1fr}}
@media(max-width:520px){.pg-cat-grid{grid-template-columns:1fr}}
.pg-cat-card{border:1px solid var(--rule);border-radius:4px;padding:.95rem 1rem;background:var(--paper)}
.pg-cat-card.pg-cat-success{border-top:4px solid var(--green)}
.pg-cat-card.pg-cat-warning{border-top:4px solid var(--amber)}
.pg-cat-card.pg-cat-danger{border-top:4px solid var(--red)}
.pg-cat-grade{font-family:var(--serif);font-size:1.65rem;font-weight:600;line-height:1.1;margin-bottom:.15rem}
.pg-cat-sub{font-family:var(--mono);font-size:8px;color:var(--gray);line-height:1.3;margin-bottom:.5rem;min-height:2.2em}
.pg-cat-head{display:flex;justify-content:space-between;align-items:flex-start;gap:.5rem;margin-bottom:.35rem;font-size:11px;font-weight:600}
.pg-cat-w{font-family:var(--mono);font-size:8px;color:var(--gray);white-space:nowrap}
.pg-cat-body{font-size:10.5px;line-height:1.55;color:var(--ink)}
.pg-metrics-h{font-family:var(--sans);font-size:1rem;font-weight:600;margin:1.25rem 0 .65rem 0}
.pg-metrics-table{width:100%;border-collapse:collapse;font-size:10.5px}
.pg-metrics-table th{font-family:var(--mono);font-size:8px;letter-spacing:.06em;text-transform:uppercase;color:var(--gray);text-align:left;padding:8px 10px;border-bottom:2px solid var(--rule);font-weight:500}
.pg-metrics-table td{padding:8px 10px;border-bottom:1px solid var(--rule);vertical-align:middle}
.pg-metrics-table tr:last-child td{border-bottom:none}
.pg-m-status{font-family:var(--mono);font-size:9px;font-weight:600}
.pg-m-tone-green{color:var(--green)}
.pg-m-tone-amber{color:var(--amber)}
.pg-m-tone-red{color:var(--red)}
.rca-conf-bar-wrap{margin:.15rem 0 .85rem 0}
.rca-conf-bar-track{height:4px;background:var(--rule);border-radius:2px;overflow:hidden;max-width:100%}
.rca-conf-bar-fill{height:4px;background:#0D3F7C;border-radius:2px;transition:width .3s ease}
.rca-evidence-box{background:#E8E6E0;border:1px solid var(--rule);border-radius:2px;padding:.85rem 1rem;font-size:11px;line-height:1.7;color:var(--ink)}
.rca-evidence-box .rca-evidence-label{font-family:var(--sans);font-weight:600;display:block;margin-bottom:.35rem;font-size:10.5px;color:var(--ink)}
.rca-panel-intro{max-width:920px}
.rca-head{display:flex;align-items:flex-start;gap:.75rem;margin-bottom:.6rem;flex-wrap:wrap}
.rca-id{font-family:var(--mono);font-size:10px;color:var(--gray);white-space:nowrap;margin-top:2px}
.rca-title{font-family:var(--sans);font-size:13px;font-weight:600;flex:1;min-width:0;line-height:1.4}
.rca-body{font-size:11.5px;line-height:1.75;color:var(--ink);margin-bottom:.75rem}
.conf-row{display:flex;align-items:center;gap:.75rem;margin-top:.6rem}
.conf-track{flex:1;height:3px;background:var(--rule);border-radius:1px;overflow:hidden}
.conf-fill{height:3px;border-radius:1px;background:var(--blue)}
.conf-pct{font-family:var(--mono);font-size:9px;color:var(--gray);white-space:nowrap}
.scenario-bar{display:grid;grid-template-columns:140px 1fr auto;align-items:center;gap:.75rem;padding:.6rem 0;border-bottom:1px solid var(--rule)}
.scenario-bar:last-child{border-bottom:none}
.scenario-name{font-family:var(--mono);font-size:10px;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.bar-track{background:var(--rule);border-radius:1px;height:6px;overflow:hidden}
.bar-fill{height:6px;border-radius:1px}
.bar-meta{font-family:var(--mono);font-size:9px;color:var(--gray);text-align:right;white-space:nowrap}
.timeline{position:relative;padding-left:1.5rem;margin-bottom:1.5rem}
.timeline::before{content:'';position:absolute;left:5px;top:8px;bottom:8px;width:1px;background:var(--rule)}
.tl-item{position:relative;margin-bottom:1rem}
.tl-dot{position:absolute;left:-1.5rem;top:3px;width:10px;height:10px;border-radius:50%;border:1.5px solid}
.tl-dot.red{background:var(--red-light);border-color:var(--red)}
.tl-dot.amber{background:var(--amber-light);border-color:var(--amber)}
.tl-dot.green{background:var(--green-light);border-color:var(--green)}
.tl-time{font-family:var(--mono);font-size:9px;color:var(--gray);letter-spacing:.06em}
.tl-title{font-size:12px;font-weight:600;margin:.1rem 0 .2rem}
.tl-body{font-size:11px;color:var(--gray);line-height:1.6}
.capacity-box{background:var(--ink);color:var(--paper);padding:1.5rem 2rem;display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.5rem;margin-bottom:1.5rem}
.cap-label{font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:rgba(245,243,238,.45);margin-bottom:.3rem}
.cap-value{font-family:var(--serif);font-size:1.6rem;font-weight:600;color:var(--paper)}
.cap-sub{font-family:var(--mono);font-size:10px;color:rgba(245,243,238,.5)}
.phase-roadmap-card{border:1px solid var(--rule);margin-bottom:1rem;padding:1.15rem 1.35rem;background:var(--cream);border-radius:2px;border-left:6px solid var(--gray)}
.phase-roadmap-card.phase-r1{border-left-color:var(--red);background:var(--red-light)}
.phase-roadmap-card.phase-r2{border-left-color:#E07A5F;background:#FDEDE8}
.phase-roadmap-card.phase-r3{border-left-color:var(--amber);background:var(--amber-light)}
.phase-roadmap-card.phase-r4{border-left-color:var(--green);background:var(--green-light)}
.phase-badge{display:inline-block;font-family:var(--mono);font-size:8px;letter-spacing:.12em;text-transform:uppercase;background:var(--ink);color:var(--paper);padding:5px 12px;border-radius:2px;margin-bottom:.75rem;font-weight:500}
.phase-roadmap-title{font-family:var(--sans);font-size:1.05rem;font-weight:600;margin-bottom:.85rem;line-height:1.35;color:var(--ink)}
.phase-action-list{margin:0 0 .25rem 0;padding-left:1.15rem;font-size:11.5px;line-height:1.7;color:var(--ink)}
.phase-action-list>li{margin:.5rem 0}
.phase-action-list strong{font-weight:600}
.phase-steps{margin:.4rem 0 0 1rem;padding-left:1rem;list-style:disc;color:var(--gray);font-size:11px;line-height:1.6}
.phase-outcome{margin-top:1rem;padding-top:.85rem;border-top:1px solid var(--rule);font-size:11.5px;line-height:1.75;color:var(--ink)}
.phase-outcome .phase-outcome-label{font-family:var(--mono);font-size:9px;letter-spacing:.1em;text-transform:uppercase;color:var(--gray);display:block;margin-bottom:.35rem}
.heat-table{width:100%;border-collapse:collapse;font-size:10px}
.heat-table th{font-family:var(--mono);font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--gray);padding:5px 8px;text-align:center;font-weight:400;white-space:nowrap}
.heat-table td{padding:5px 8px;text-align:center;font-family:var(--mono)}
.heat-table .row-label{text-align:left;color:var(--gray);font-size:9px;letter-spacing:.05em;white-space:nowrap}
.heat-0{background:#F5F3EE;color:#aaa}
.heat-1{background:#E8F0FB;color:var(--blue)}
.heat-2{background:#d0e4f8;color:var(--blue)}
.heat-3{background:#b0cef0;color:#0D3F7C}
.heat-4{background:#EAF3DA;color:var(--green)}
.heat-5{background:#FEF3C7;color:var(--amber)}
.heat-6{background:#FDEBD0;color:#924D0B}
.heat-7{background:#F9E8E7;color:var(--red)}
.heat-8{background:#f2c7c5;color:#8B1F1C}
.heat-9{background:#E8A09A;color:#fff}
.dist-sla-wrap{margin-top:1.25rem}
.dist-sla-table{width:100%;border-collapse:collapse;font-size:10px;margin-top:.35rem}
.dist-sla-table th{font-family:var(--mono);font-size:9px;letter-spacing:.06em;text-transform:uppercase;color:var(--gray);padding:6px 8px;text-align:center;font-weight:400;border-bottom:.5px solid var(--rule);background:var(--cream)}
.dist-sla-table td{padding:6px 8px;border-bottom:.5px solid var(--rule);vertical-align:middle}
.dist-sla-table .row-label{text-align:left;color:var(--gray);font-size:9px;white-space:nowrap}
.dist-cell{text-align:center;font-family:var(--mono);font-size:10px;font-weight:600;border-radius:3px}
.dist-cell.green{background:var(--green-light);color:var(--green)}
.dist-cell.amber{background:var(--amber-light);color:var(--amber)}
.dist-cell.red{background:var(--red-light);color:var(--red)}
.dist-cell.neu{background:var(--gray-l,#F7F5F1);color:var(--gray)}
.score-split{display:grid;grid-template-columns:280px 1fr;gap:1.5rem;align-items:start}
@media(max-width:768px){
  .page{padding:1.5rem}
  .report-header{padding:2rem 1.5rem}
  .sticky-nav{padding:0 1rem}
  .two-col{grid-template-columns:1fr}
  .capacity-box{grid-template-columns:1fr 1fr}
  .scenario-bar{grid-template-columns:100px 1fr auto}
  .header-title{font-size:1.8rem}
  .report-brand img{height:34px}
  .score-split{grid-template-columns:1fr}
}
@media print{
  .sticky-nav{display:none}
  .panel{display:block!important}
}
""".strip()

_HEAT_HEADERS = [
    "0–100ms",
    "100–500ms",
    "500ms–1s",
    "1–3s",
    "3–5s",
    "5–10s",
    "10–30s",
    "30–60s",
    "60–180s",
    "&gt;180s",
]

_COMBINED_CHART_JS = r"""
<script>
const CHARTS = __CHARTS_JSON__;
function show(id) {
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById('panel-'+id).classList.add('active');
  const btns=[...document.querySelectorAll('.nav-btn')];
  const ids=['overview','scorecard','rt','throughput','errors','apdex','rca','capacity'];
  const idx = ids.indexOf(id);
  if(idx>=0 && btns[idx]) btns[idx].classList.add('active');
  window.scrollTo({top:0,behavior:'smooth'});
}
const chartDefaults={responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},plugins:{legend:{display:false}}};
const gridColor='rgba(0,0,0,0.06)';
const tickStyle={font:{size:9,family:"'DM Mono',monospace"},color:'#6B6860'};
const MINS=CHARTS.MINS||[];const VUS=CHARTS.VUS||[];const MEAN_RT=CHARTS.MEAN_RT||[];const P90_RT=CHARTS.P90_RT||[];const ERR_RT=CHARTS.ERR_RT||[];const TPS_ARR=CHARTS.TPS_ARR||[];
const BANDS=CHARTS.BANDS||[];const BP=CHARTS.bar_percentiles||[];const TTFB=CHARTS.ttfb||[];const CNT=CHARTS.content||[];
const APDX=CHARTS.apdex_bands||[];const SCORE=CHARTS.score_donut||[0,0,0,0];
const BTPS=CHARTS.band_avg_tps||[];const TCOL=CHARTS.tps_band_colors||[];
const BRX=CHARTS.band_rx_mb||[];const BTX=CHARTS.band_tx_mb||[];
const E404=CHARTS.err_band_404||[];const E5=CHARTS.err_band_5xx||[];const EN=CHARTS.err_band_nhr||[];
if(MINS.length && document.getElementById('rtMainChart')){
new Chart(document.getElementById('rtMainChart'),{type:'line',data:{labels:MINS,datasets:[
  {label:'Mean RT',data:MEAN_RT,borderColor:'#C0392B',borderWidth:2,pointRadius:0,fill:true,backgroundColor:'rgba(192,57,43,0.04)',yAxisID:'y'},
  {label:'P90 RT',data:P90_RT,borderColor:'#B45309',borderWidth:1.5,borderDash:[5,3],pointRadius:0,fill:false,yAxisID:'y'},
  {label:'VU',data:VUS,borderColor:'#2D6A2D',borderWidth:1.5,borderDash:[2,4],pointRadius:0,fill:false,yAxisID:'y2'}
]},options:{...chartDefaults,scales:{
  x:{ticks:{...tickStyle,maxTicksLimit:12},grid:{color:gridColor}},
  y:{title:{display:true,text:'Response time (ms)',font:{size:9,family:"'DM Mono',monospace"},color:'#C0392B'},ticks:{...tickStyle,callback:v=>v>=1000?Math.round(v/1000)+'s':v+'ms'},position:'left',grid:{color:gridColor}},
  y2:{title:{display:true,text:'Concurrent users',font:{size:9,family:"'DM Mono',monospace"},color:'#2D6A2D'},ticks:{...tickStyle,color:'#2D6A2D'},position:'right',grid:{display:false}}
}}});
}
if(BANDS.length && BP.length && document.getElementById('rtPercentileChart')){
const z=(i,j)=>(BP[i]&&BP[i][j]!=null)?BP[i][j]:0;
new Chart(document.getElementById('rtPercentileChart'),{type:'bar',data:{labels:BANDS,datasets:[
  {label:'Median',data:BANDS.map((_,i)=>z(i,0)),backgroundColor:'#2D6A2D',borderRadius:2},
  {label:'P75',data:BANDS.map((_,i)=>z(i,1)),backgroundColor:'#1A4E8C',borderRadius:2},
  {label:'P90',data:BANDS.map((_,i)=>z(i,2)),backgroundColor:'#B45309',borderRadius:2},
  {label:'P95',data:BANDS.map((_,i)=>z(i,3)),backgroundColor:'#C0392B',borderRadius:2}
]},options:{...chartDefaults,scales:{x:{ticks:tickStyle,grid:{display:false}},y:{ticks:{...tickStyle,callback:v=>v>=1000?Math.round(v/1000)+'s':v+'ms'},grid:{color:gridColor}}}}});
}
if(BANDS.length && document.getElementById('ttfbChart')){
new Chart(document.getElementById('ttfbChart'),{type:'bar',data:{labels:BANDS,datasets:[
  {label:'TTFB (first byte)',data:TTFB,backgroundColor:'#1A4E8C',borderRadius:2},
  {label:'Content transfer',data:CNT,backgroundColor:'#C0392B',borderRadius:2}
]},options:{...chartDefaults,scales:{x:{ticks:tickStyle,grid:{display:false}},y:{ticks:{...tickStyle,callback:v=>v+'ms'},stacked:true,grid:{color:gridColor}}},plugins:{legend:{display:true}}}});
}
if(MINS.length && document.getElementById('tpsMainChart')){
new Chart(document.getElementById('tpsMainChart'),{type:'line',data:{labels:MINS,datasets:[
  {label:'TPS',data:TPS_ARR,borderColor:'#1A4E8C',borderWidth:2,pointRadius:0,fill:true,backgroundColor:'rgba(26,78,140,0.06)',yAxisID:'y'},
  {label:'Mean RT (s)',data:MEAN_RT.map(v=>+(v/1000).toFixed(2)),borderColor:'#C0392B',borderWidth:1.5,borderDash:[4,3],pointRadius:0,fill:false,yAxisID:'y2'},
  {label:'VU',data:VUS,borderColor:'#2D6A2D',borderWidth:1,borderDash:[2,5],pointRadius:0,fill:false,yAxisID:'y2'}
]},options:{...chartDefaults,scales:{
  x:{ticks:{...tickStyle,maxTicksLimit:12},grid:{color:gridColor}},
  y:{title:{display:true,text:'TPS / min',font:{size:9,family:"'DM Mono',monospace"},color:'#1A4E8C'},ticks:tickStyle,position:'left',grid:{color:gridColor}},
  y2:{title:{display:true,text:'RT (s) / VU',font:{size:9,family:"'DM Mono',monospace"},color:'#6B6860'},ticks:{...tickStyle,callback:v=>v>100?v+'VU':v+'s'},position:'right',grid:{display:false}}
}}});
}
if(BTPS.length && document.getElementById('tpsBandChart')){
const cols=TCOL.length===BTPS.length?TCOL:BTPS.map(()=>'#1A4E8C');
new Chart(document.getElementById('tpsBandChart'),{type:'bar',data:{labels:BANDS,datasets:[{label:'Avg TPS',data:BTPS,backgroundColor:cols,borderRadius:3}]},options:{...chartDefaults,plugins:{legend:{display:false}},scales:{x:{ticks:tickStyle,grid:{display:false}},y:{ticks:{...tickStyle,callback:v=>v+' TPS'},grid:{color:gridColor}}}}});
}
if(BRX.length && document.getElementById('bwChart')){
new Chart(document.getElementById('bwChart'),{type:'bar',data:{labels:BANDS,datasets:[
  {label:'Received (MB)',data:BRX,backgroundColor:'#1A4E8C',borderRadius:3},
  {label:'Sent (MB)',data:BTX,backgroundColor:'#6FA3E0',borderRadius:3}
]},options:{...chartDefaults,scales:{x:{ticks:tickStyle,grid:{display:false}},y:{ticks:{...tickStyle,callback:v=>v+'MB'},grid:{color:gridColor}}}}});
}
if(MINS.length && document.getElementById('errCorrChart')){
new Chart(document.getElementById('errCorrChart'),{type:'line',data:{labels:MINS,datasets:[
  {label:'Error rate %',data:ERR_RT,borderColor:'#C0392B',borderWidth:2,pointRadius:0,fill:true,backgroundColor:'rgba(192,57,43,0.07)',yAxisID:'y'},
  {label:'Mean RT (s)',data:MEAN_RT.map(v=>+(v/1000).toFixed(2)),borderColor:'#B45309',borderWidth:1.5,borderDash:[4,3],pointRadius:0,fill:false,yAxisID:'y2'}
]},options:{...chartDefaults,scales:{
  x:{ticks:{...tickStyle,maxTicksLimit:10},grid:{color:gridColor}},
  y:{title:{display:true,text:'Error %',font:{size:9},color:'#C0392B'},ticks:{...tickStyle,color:'#C0392B'},position:'left',grid:{color:gridColor}},
  y2:{title:{display:true,text:'Mean RT (s)',font:{size:9},color:'#B45309'},ticks:{...tickStyle,color:'#B45309'},position:'right',grid:{display:false}}
}}});
}
if(BANDS.length && document.getElementById('errBandChart')){
new Chart(document.getElementById('errBandChart'),{type:'bar',data:{labels:BANDS,datasets:[
  {label:'4xx samples',data:E404,backgroundColor:'#C0392B',borderRadius:2},
  {label:'5xx samples',data:E5,backgroundColor:'#B45309',borderRadius:2},
  {label:'NoHTTP heuristic',data:EN,backgroundColor:'#6B6860',borderRadius:2}
]},options:{...chartDefaults,plugins:{legend:{display:true,position:'bottom'}},scales:{x:{ticks:tickStyle,grid:{display:false},stacked:true},y:{ticks:tickStyle,grid:{color:gridColor},stacked:true}}}});
}
const h=SCORE[0]||0,sl=SCORE[1]||0,w=SCORE[2]||0,c=SCORE[3]||0;
if(document.getElementById('scorecardDonut')){
new Chart(document.getElementById('scorecardDonut'),{type:'doughnut',data:{
  labels:['Healthy ('+h+')','Slow ('+sl+')','Warning ('+w+')','Critical ('+c+')'],
  datasets:[{data:[h,sl,w,c],backgroundColor:['#2D6A2D','#1A4E8C','#B45309','#C0392B'],borderWidth:0,hoverOffset:4}]
},options:{responsive:true,maintainAspectRatio:false,cutout:'65%',
  plugins:{legend:{display:true,position:'right',labels:{font:{size:10,family:"'DM Mono',monospace"},color:'#6B6860',padding:12,boxWidth:10}}}
}});
}
if(BANDS.length && APDX.length && document.getElementById('apdexBandChart')){
const acol=APDX.map(v=>v>=0.94?'#2D6A2D':(v>=0.85?'#B45309':'#C0392B'));
new Chart(document.getElementById('apdexBandChart'),{type:'bar',data:{labels:BANDS,datasets:[{label:'Apdex',data:APDX,backgroundColor:acol,borderRadius:3}]},options:{...chartDefaults,plugins:{legend:{display:false}},scales:{x:{ticks:tickStyle,grid:{display:false}},y:{min:0,max:1,ticks:{...tickStyle,callback:v=>v.toFixed(2)},grid:{color:gridColor}}}}});
}
</script>
"""


def _e(x: Any) -> str:
    if x is None:
        return ""
    return html.escape(str(x), quote=True)


def _heat_cell_class(pct: float, col_idx: int) -> str:
    if pct <= 0.2:
        return "heat-0"
    tier = min(9, int(pct / 15) + (3 if col_idx >= 5 else 1))
    return f"heat-{tier}"


_DIST_SLA_MEAN_LEGEND_MS = 1000.0
_DIST_SLA_P90_LEGEND_MS = 2000.0


def _render_distribution_sla_table(dist_sla: Any) -> str:
    if not isinstance(dist_sla, dict):
        return ""
    rows = dist_sla.get("rows") or []
    if not rows:
        return ""
    mt = float(dist_sla.get("mean_target_ms") or 2000)
    pt = float(dist_sla.get("p90_target_ms") or 3000)
    body_lines: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        label = _e(r.get("label"))
        body_lines.append(f'<tr><td class="row-label">{label}</td>')
        mean_v = r.get("mean_rt")
        mean_tone = str(r.get("mean_tone") or "neu")
        if mean_v is None:
            body_lines.append('<td class="dist-cell neu">—</td>')
        else:
            body_lines.append(
                f'<td class="dist-cell {mean_tone}">{int(round(float(mean_v))):,} ms</td>'
            )
        p90_v = r.get("p90_rt")
        p90_tone = str(r.get("p90_tone") or "neu")
        if p90_v is None:
            body_lines.append('<td class="dist-cell neu">—</td>')
        else:
            body_lines.append(
                f'<td class="dist-cell {p90_tone}">{int(round(float(p90_v))):,} ms</td>'
            )
        err_v = r.get("err_pct")
        err_tone = str(r.get("err_tone") or "neu")
        if err_v is None:
            body_lines.append('<td class="dist-cell neu">—</td>')
        else:
            body_lines.append(
                f'<td class="dist-cell {err_tone}">{float(err_v):.2f}%</td>'
            )
        body_lines.append("</tr>\n")
    cap = (
        f"Cell colors vs saved Target Values: mean ≤{mt:.0f} ms = green, up to +{_DIST_SLA_MEAN_LEGEND_MS:.0f} ms over = amber, beyond = red; "
        f"P90 ≤{pt:.0f} ms = green, up to +{_DIST_SLA_P90_LEGEND_MS:.0f} ms over = amber, beyond = red; "
        "sample error rate under 1% = green, 1% up to under 2% = amber, 2% or more = red."
    )
    return f"""
  <div class="dist-sla-wrap">
    <div class="section-desc" style="font-size:11px;line-height:1.55;margin-bottom:.2rem"><strong>SLA snapshot by load band</strong> — same bands as the heatmap.</div>
    <p class="section-desc" style="font-size:10px;color:var(--gray);line-height:1.55">{_e(cap)}</p>
    <table class="dist-sla-table">
      <thead><tr>
        <th style="text-align:left">Load band</th>
        <th>Avg RT</th>
        <th>P90 RT</th>
        <th>Error %</th>
      </tr></thead>
      <tbody>{"".join(body_lines)}</tbody>
    </table>
  </div>"""


def _kpi_value_class(tone: str) -> str:
    if tone == "red":
        return "kpi-value red"
    if tone == "amber":
        return "kpi-value amber"
    if tone == "green":
        return "kpi-value green"
    return "kpi-value"


def _apdex_bar_color(score: float, tone: str) -> str:
    if tone == "red" or score < 0.5:
        return "var(--red)"
    if tone == "amber":
        return "var(--amber)"
    return "var(--green)"


def _phase_expected_outcome_html(ph: Dict[str, Any]) -> str:
    eo = ph.get("expected_outcome")
    if isinstance(eo, str) and eo.strip():
        return _e(eo.strip())
    parts: List[str] = []
    ts = ph.get("target_score")
    eg = ph.get("expected_grade")
    if ts is not None:
        parts.append(
            f"Target health score ≈ {_e(ts)}" + (f" ({_e(eg)})" if eg else "") + "."
        )
    impacts: List[str] = []
    for a in ph.get("actions") or []:
        if isinstance(a, dict) and a.get("expected_impact"):
            s = str(a["expected_impact"]).strip()
            if s and s not in impacts:
                impacts.append(s)
    if impacts:
        parts.append("Expected score uplift / impact: " + _e("; ".join(impacts[:6])) + ".")
    if not parts:
        return _e(
            "Validate improvements with a repeat load test on the same scenarios and saved targets."
        )
    return " ".join(parts)


def _render_phases(phase_list: List[Dict[str, Any]]) -> str:
    if not phase_list:
        return '<p class="section-desc">No phased remediation plan was generated for this run.</p>'
    parts: List[str] = []
    tier_fallback = ("IMMEDIATE", "SHORT-TERM", "MID-TERM", "PRE-PRODUCTION")
    for i, ph in enumerate(phase_list):
        if not isinstance(ph, dict):
            continue
        title = _e(str(ph.get("phase") or f"Phase {i + 1}").strip())
        timeline_raw = str(ph.get("timeline") or "").strip()
        timeline_badge = timeline_raw.upper().replace("–", "-") if timeline_raw else "TIMELINE TBD"
        pri_raw = str(ph.get("priority") or "").strip()
        for sym in (
            "🔴",
            "🟡",
            "🟢",
            "⚠️",
            "✓",
            "🎉",
        ):
            pri_raw = pri_raw.replace(sym, "")
        pri_clean = pri_raw.strip() or tier_fallback[min(i, len(tier_fallback) - 1)]
        badge = _e(f"PHASE {i + 1} · {pri_clean.upper()} · {timeline_badge}")
        css_phase = f"phase-r{min(i + 1, 4)}"
        actions = ph.get("actions") or []
        li_parts: List[str] = []
        aj = 0
        for act in actions:
            if not isinstance(act, dict):
                continue
            an = str(act.get("action") or "").strip()
            if not an:
                continue
            aj += 1
            det = str(act.get("detail") or "").strip()
            line = f"<strong>Action {aj}:</strong> {_e(an)}"
            if det:
                line += f" — {_e(det)}"
            steps = act.get("steps") or []
            if isinstance(steps, list) and steps:
                sub = "".join(
                    f"<li>{_e(str(s).strip())}</li>" for s in steps if str(s).strip()
                )
                if sub:
                    line += f"<ul class=\"phase-steps\">{sub}</ul>"
            li_parts.append(f"<li>{line}</li>")
        if not li_parts and (ph.get("status") or ph.get("message")):
            li_parts.append(f"<li>{_e(ph.get('status') or ph.get('message'))}</li>")
        actions_html = (
            f"<ol class=\"phase-action-list\">{''.join(li_parts)}</ol>" if li_parts else ""
        )
        outcome = _phase_expected_outcome_html(ph)
        parts.append(
            f"""<div class="phase-roadmap-card {css_phase}">
      <span class="phase-badge">{badge}</span>
      <div class="phase-roadmap-title">{title}</div>
      {actions_html}
      <div class="phase-outcome"><span class="phase-outcome-label">Expected outcome</span>{outcome}</div>
    </div>"""
        )
    return "\n".join(parts) if parts else '<p class="section-desc">No phased remediation plan was generated for this run.</p>'


def _pg_overall_accent(grade: str) -> str:
    g = (grade or "C").strip().upper()
    first = g[0] if g else "C"
    if first == "A":
        return "#166534"
    if first == "B":
        return "#1e40af"
    if first == "C":
        return "#b45309"
    if first in ("D", "F"):
        return "#b91c1c"
    return "#0D3F7C"


def _pg_cat_border_class(css_class: str) -> str:
    c = (css_class or "warning").lower()
    if c == "success":
        return "pg-cat-success"
    if c == "danger":
        return "pg-cat-danger"
    return "pg-cat-warning"


def _pg_metric_tone_class(tone: str) -> str:
    t = (tone or "").lower()
    if t == "green":
        return "pg-m-tone-green"
    if t == "red":
        return "pg-m-tone-red"
    return "pg-m-tone-amber"


def _render_performance_grading_html(pg: Optional[Dict[str, Any]]) -> str:
    if not pg or not isinstance(pg, dict):
        return ""
    grade = str(pg.get("overall_grade") or "—")
    accent = _pg_overall_accent(grade)
    score = pg.get("overall_score")
    try:
        score_s = f"{float(score):.0f}"
    except (TypeError, ValueError):
        score_s = str(score or "—")
    title = _e(str(pg.get("title") or ""))
    sub = _e(str(pg.get("subtitle") or ""))
    sr_raw = str(pg.get("score_range") or "").strip()
    sr = _e(sr_raw)
    meth_inner = performance_grading_methodology_html(grade, tooltip_on_dark=True)
    cards_html = ""
    for c in pg.get("category_cards") or []:
        if not isinstance(c, dict):
            continue
        bcls = _pg_cat_border_class(str(c.get("css_class") or ""))
        gcol = _pg_overall_accent(str(c.get("grade") or ""))
        try:
            cat_score = f"{float(c.get('score') or 0):.0f}"
        except (TypeError, ValueError):
            cat_score = "0"
        cards_html += (
            f'<div class="pg-cat-card {bcls}">'
            f'<div class="pg-cat-grade" style="color:{gcol}">{_e(c.get("grade"))}</div>'
            f'<div class="pg-cat-sub">{_e(c.get("one_liner"))}</div>'
            f'<div class="pg-cat-head"><span>{_e(c.get("icon"))} {_e(c.get("name"))}</span>'
            f'<span class="pg-cat-w">{_e(c.get("weight"))} · {cat_score}/100</span></div>'
            f'<div class="pg-cat-body">{_e(c.get("reason"))}</div></div>\n'
        )
    rows_html = ""
    for row in pg.get("metrics_rows") or []:
        if not isinstance(row, dict):
            continue
        tc = _pg_metric_tone_class(str(row.get("tone") or ""))
        rows_html += (
            f'<tr><td style="font-weight:600">{_e(row.get("metric"))}</td>'
            f'<td class="mono">{_e(row.get("result"))}</td>'
            f'<td class="mono">{_e(row.get("target"))}</td>'
            f'<td><span class="pg-m-status {tc}">{_e(row.get("status"))}</span></td>'
            f'<td class="mono">{_e(row.get("score"))}</td></tr>\n'
        )
    range_line = f" · Range {sr}" if sr_raw else ""
    sub_block = f'<p class="pg-overall-sub">{sub}</p>' if sub else ""
    return (
        '<div class="pg-grading" id="section-performance-grading">\n'
        '  <div class="pg-grading-head">\n'
        '    <div class="section-label" style="margin:0">Performance scorecard</div>\n'
        "  </div>\n"
        '  <h2 class="section-title" style="margin-top:0">Performance Scorecard &amp; Grading Analysis</h2>\n'
        '  <p class="section-desc">Weighted model: Performance 30%, Reliability 25%, User Experience 25%, '
        "Scalability 20%. Hover the overall grade letter for the letter scale and methodology.</p>\n"
        f'  <div class="pg-overall" style="border-color:{accent};--pg-accent:{accent}">\n'
        '    <span class="pg-overall-label">Overall grade</span>\n'
        '    <div class="pg-grade-wrap" tabindex="0">\n'
        f'      <span class="pg-grade-letter">{_e(grade)}</span>\n'
        f'      <div class="pg-grade-tip" role="tooltip">{meth_inner}</div>\n'
        "    </div>\n"
        f'    <div class="pg-overall-title">{title}</div>\n'
        f'    <div class="pg-overall-score">Score {score_s}/100{range_line}</div>\n'
        f"    {sub_block}\n"
        "  </div>\n"
        f'  <div class="pg-cat-grid">{cards_html}</div>\n'
        '  <h3 class="pg-metrics-h">Detailed performance metrics</h3>\n'
        '  <div style="overflow-x:auto">\n'
        '    <table class="data-table pg-metrics-table">\n'
        "      <thead><tr><th>Metric</th><th>Result</th><th>Target</th><th>Status</th><th>Score</th></tr></thead>\n"
        f"      <tbody>{rows_html}</tbody>\n"
        "    </table>\n"
        "  </div>\n"
        "</div>"
    )


def render_combined_load_report_html(
    payload: Dict[str, Any],
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> str:
    def prog(p: int, m: str) -> None:
        if progress_callback:
            try:
                progress_callback(p, m)
            except Exception:
                pass

    prog(5, "Rendering combined load report…")
    meta = payload.get("meta") or {}
    ch = payload.get("charts") or {}
    verdict = payload.get("verdict") or {}
    vcss = verdict.get("css") or "amber"
    vt = str(verdict.get("text", ""))
    _release_emoji = ("🟢", "🟡", "🟠", "🔴", "⛔")
    led_by_release_emoji = any(vt.startswith(e) for e in _release_emoji)
    if led_by_release_emoji:
        vprefix = ""
    elif vcss == "red":
        pill_cls = "verdict-pill"
        vprefix = "⛔ "
    elif vcss == "green":
        pill_cls = "verdict-pill green"
        vprefix = "✓ "
    else:
        pill_cls = "verdict-pill amber"
        vprefix = "⚠ " if "RISK" in vt.upper() or "CONDITIONAL" in vt.upper() else "✓ "
    if not led_by_release_emoji and vt.upper().startswith("NO"):
        vprefix = "⛔ "
        pill_cls = "verdict-pill"

    if led_by_release_emoji:
        if vcss == "red":
            pill_cls = "verdict-pill"
        elif vcss == "green":
            pill_cls = "verdict-pill green"
        else:
            pill_cls = "verdict-pill amber"

    key_findings = payload.get("key_findings") or []
    if key_findings:
        kf_html = (
            '<div class="key-findings-overview">'
            '<div class="key-findings-label">Key findings · basis for release decision</div>'
            '<ul class="key-findings-list">'
            + "".join(f"<li>{_e(x)}</li>" for x in key_findings)
            + "</ul></div>"
        )
    else:
        kf_html = ""

    co_raw = payload.get("chart_observations")
    co: Dict[str, str] = co_raw if isinstance(co_raw, dict) else {}

    def chart_obs(key: str) -> str:
        s = str(co.get(key) or "").strip()
        if not s:
            return ""
        return f'<div class="chart-observation">{_e(s)}</div>'

    zp2 = str(payload.get("zones_preamble") or "").strip()
    zones_preamble_block = f'<p class="section-desc">{_e(zp2)}</p>' if zp2 else ""

    title_line = _e(meta.get("title_line") or "Application")
    report_title = _e(meta.get("report_title") or "Load Test Report")
    subtitle = _e(meta.get("subtitle") or "")
    test_date_line = _e(meta.get("test_date_line") or "")
    nav_items = [
        ("overview", "Overview"),
        ("scorecard", "Scorecard &amp; grading"),
        ("rt", "Response Time"),
        ("throughput", "Throughput"),
        ("errors", "Error Analysis"),
        ("apdex", "Apdex &amp; UX"),
        ("rca", "Root Cause"),
        ("capacity", "Capacity &amp; Plan"),
    ]
    nav_html = "".join(
        f"""<button class="nav-btn{" active" if k == "overview" else ""}" onclick="show('{k}')">{lab}</button>\n"""
        for k, lab in nav_items
    )

    kpis = payload.get("kpis") or []
    kpi_html = "".join(
        f"""<div class="kpi"><div class="kpi-label">{_e(x.get("label"))}</div>
    <div class="{_kpi_value_class(str(x.get("tone") or ""))}">{_e(x.get("value"))}</div>
    <div class="kpi-sub">{_e(x.get("sub"))}</div></div>\n"""
        for x in kpis
    )

    scenarios = payload.get("scenarios") or []
    scen_html = ""
    color_map = {"red": "var(--red)", "green": "var(--green)", "amber": "var(--amber)", "blue": "var(--blue)"}
    for s in scenarios:
        c = color_map.get(str(s.get("color")), "var(--gray)")
        scen_html += f"""<div class="scenario-bar">
        <span class="scenario-name">{_e(s.get("name"))}</span>
        <div class="bar-track"><div class="bar-fill" style="width:{int(s.get("width_pct") or 0)}%;background:{c}"></div></div>
        <span class="bar-meta">{s.get("samples", 0):,} samples · {s.get("err_pct", 0)}% errors</span>
      </div>\n"""

    zones = payload.get("zones_intro") or []
    zone_html = "".join(
        f"""<div class="zone {_e(z.get("css"))}">
      <div class="zone-head"><span class="zone-label">{_e(z.get("label"))}</span><span class="zone-title">{_e(z.get("title"))}</span></div>
      <div class="zone-body">{_e(z.get("body"))}</div>
    </div>\n"""
        for z in zones
    )

    tl = payload.get("timeline") or []
    tl_html = "".join(
        f"""<div class="tl-item">
        <div class="tl-dot {_e(ev.get("dot"))}"></div>
        <div class="tl-time">{_e(ev.get("time"))}</div>
        <div class="tl-title">{_e(ev.get("title"))}</div>
        <div class="tl-body">{_e(ev.get("body"))}</div>
      </div>\n"""
        for ev in tl
    )

    txp = payload.get("transaction_percentile_table") or {}
    tx_rows = txp.get("rows") or []
    tx_title_mode = _e(str(txp.get("title_mode") or "Samples"))
    tx_foot = _e(str(txp.get("footnote") or ""))
    tx_band_labels: List[str] = list(txp.get("load_band_labels") or [])

    def _band_grade_td(cell: Dict[str, Any]) -> str:
        gt = str(cell.get("grade_tone") or "neu")
        g_raw = str(cell.get("grade") or "—")
        gl = _e(g_raw)
        gs = cell.get("grade_score")
        n_raw = cell.get("n")
        try:
            n_smp = int(n_raw) if n_raw is not None else 0
        except (TypeError, ValueError):
            n_smp = 0
        tip_parts: List[str] = []
        if n_smp > 0:
            tip_parts.append(f"{n_smp} samples in this VU band")
        elif n_smp == 0:
            tip_parts.append("No samples in this band for this row")
        if gs is not None and g_raw != "—":
            tip_parts.append(f"Score {gs}/100 (same 30/25/25/20 model as scorecard)")
        gtitle = _e(" · ".join(tip_parts)) if tip_parts else ""
        return f'<td class="mono dist-cell {gt}" title="{gtitle}">{gl}</td>'

    def _row_band_cells(r: Dict[str, Any]) -> str:
        bg = r.get("band_grades") if isinstance(r.get("band_grades"), list) else []
        parts: List[str] = []
        for i, _bl in enumerate(tx_band_labels):
            cell = bg[i] if i < len(bg) else {"grade": "—", "grade_tone": "neu", "n": 0}
            if not isinstance(cell, dict):
                cell = {"grade": "—", "grade_tone": "neu", "n": 0}
            parts.append(_band_grade_td(cell))
        return "".join(parts)

    if tx_rows:
        n_bands = len(tx_band_labels)
        tx_table_min_w = 1220 + max(0, n_bands) * 72
        band_th = "".join(
            f'<th class="mono" title="Grade for samples in this VU band only (same weighted scorecard as main report)">{_e(bl)}</th>'
            for bl in tx_band_labels
        )
        tx_body_parts: List[str] = []
        for r in tx_rows:
            name = _e(str(r.get("name") or ""))
            if r.get("empty_rt"):
                np_ = int(r.get("pass") or 0)
                nf_ = int(r.get("fail") or 0)
                nt_ = np_ + nf_
                ep_ = 100.0 * nf_ / nt_ if nt_ > 0 else 0.0
                ft_ = _distribution_sla_tone_err_pct(ep_)
                gt = str(r.get("grade_tone") or "neu")
                gl = _e(str(r.get("grade") or "—"))
                gs = r.get("grade_score")
                gtitle = (
                    _e(f"Overall · Score {gs}/100 — same 30/25/25/20 model as report scorecard")
                    if gs is not None
                    else ""
                )
                tx_body_parts.append(
                    "<tr><td>"
                    + name
                    + "</td>"
                    + "".join('<td class="mono">—</td>' for _ in range(11))
                    + _row_band_cells(r)
                    + f'<td class="mono dist-cell {gt}" title="{gtitle}">{gl}</td>'
                    + f'<td class="mono">{np_}</td>'
                    f'<td class="mono dist-cell {ft_}">{nf_}</td></tr>'
                )
            else:
                at = str(r.get("avg_tone") or "neu")
                p9t = str(r.get("p90_tone") or "neu")
                ft = str(r.get("fail_tone") or "neu")
                gt = str(r.get("grade_tone") or "neu")
                gl = _e(str(r.get("grade") or "—"))
                gs = r.get("grade_score")
                gtitle = (
                    _e(f"Overall · Score {gs}/100 — same 30/25/25/20 model as report scorecard")
                    if gs is not None
                    else ""
                )
                tx_body_parts.append(
                    f"<tr><td>{name}</td>"
                    f'<td class="mono">{int(r["min"]):,}</td>'
                    f'<td class="mono">{int(r["median"]):,}</td>'
                    f'<td class="mono dist-cell {at}">{int(r["avg"]):,}</td>'
                    f'<td class="mono">{int(r["p50"]):,}</td>'
                    f'<td class="mono">{int(r["p60"]):,}</td>'
                    f'<td class="mono">{int(r["p70"]):,}</td>'
                    f'<td class="mono">{int(r["p80"]):,}</td>'
                    f'<td class="mono dist-cell {p9t}">{int(r["p90"]):,}</td>'
                    f'<td class="mono">{int(r["p95"]):,}</td>'
                    f'<td class="mono">{int(r["p99"]):,}</td>'
                    f'<td class="mono">{int(r["max"]):,}</td>'
                    + _row_band_cells(r)
                    + f'<td class="mono dist-cell {gt}" title="{gtitle}">{gl}</td>'
                    f'<td class="mono">{int(r.get("pass") or 0)}</td>'
                    f'<td class="mono dist-cell {ft}">{int(r.get("fail") or 0)}</td></tr>'
                )
        tx_pct_html = (
            '<div class="section" id="section-tx-percentiles">\n'
            '    <div class="section-label">Elapsed distribution</div>\n'
            '    <h2 class="section-title">'
            + tx_title_mode
            + ' — response times (ms)</h2>\n'
            + chart_obs("tx_percentile")
            + '    <p class="section-desc">'
            + tx_foot
            + '</p>\n'
            '    <div class="tx-pct-wrap">\n'
            f'    <table class="data-table tx-pct-table" style="min-width:{tx_table_min_w}px">\n'
            '    <thead><tr><th>Name</th><th>Min</th><th>Median</th><th>Average</th>'
            "<th>P50</th><th>P60</th><th>P70</th><th>P80</th><th>P90</th><th>P95</th><th>P99</th><th>Max</th>"
            + band_th
            + '<th title="All samples for this row; same weighted score (30/25/25/20) as main scorecard">Overall</th>'
            "<th>Pass</th><th>Fail</th></tr></thead>\n"
            "    <tbody>"
            + "".join(tx_body_parts)
            + "</tbody>\n    </table>\n    </div>\n    </div>\n"
        )
    else:
        tx_pct_html = ""

    heat_rows = payload.get("heatmap") or []
    heat_body = ""
    for hr in heat_rows:
        pcts: List[float] = list(hr.get("pcts") or [])
        cells = ""
        for j, p in enumerate(pcts[:10]):
            cls = _heat_cell_class(float(p), j)
            cells += f'<td class="{cls}">{p}%</td>'
        heat_body += f'<tr><td class="row-label">{_e(hr.get("label"))}</td>{cells}</tr>\n'

    heat_heads = "".join(f"<th>{h}</th>" for h in _HEAT_HEADERS)

    dist_sla_html = _render_distribution_sla_table(payload.get("distribution_sla"))

    lat_rows = payload.get("latency_rows") or []
    lat_body = ""
    for lr in lat_rows:
        bdg = str(lr.get("badge") or "gray")
        badge_html = f'<span class="badge {bdg}">{_e(lr.get("badge_text"))}</span>'
        lat_body += f"""<tr><td>{_e(lr.get("band"))}</td>
        <td class="mono">{lr.get("tcp_med", 0)}ms</td><td class="mono">{lr.get("tcp_p90", 0)}ms</td>
        <td class="mono">{lr.get("ttfb_med", 0)}ms</td><td class="mono">{lr.get("ttfb_p90", 0)}ms</td>
        <td class="mono">{lr.get("elapsed_med", 0)}ms</td><td class="mono">{lr.get("server_med", 0)}ms</td>
        <td>{badge_html}</td></tr>\n"""

    tp_kpis = payload.get("throughput_kpis") or []
    tp_k_html = "".join(
        f"""<div class="kpi"><div class="kpi-label">{_e(x.get("label"))}</div>
    <div class="{_kpi_value_class(str(x.get("tone") or ""))}">{_e(x.get("value"))}</div>
    <div class="kpi-sub">{_e(x.get("sub"))}</div></div>\n"""
        for x in tp_kpis
    )

    ek = payload.get("errors_kpis") or {}
    if not isinstance(ek, dict):
        ek = {}
    err_k_html = f"""<div class="kpi"><div class="kpi-label">Client errors (4xx)</div><div class="kpi-value red">{ek.get("n4xx", 0):,}</div><div class="kpi-sub">share of samples with 4xx outcome</div></div>
    <div class="kpi"><div class="kpi-label">Server errors (5xx)</div><div class="kpi-value amber">{ek.get("n5xx", 0):,}</div><div class="kpi-sub">timeouts / gateway errors</div></div>
    <div class="kpi"><div class="kpi-label">Connection anomalies</div><div class="kpi-value amber">{ek.get("no_http", 0):,}</div><div class="kpi-sub">NoHttp / connection drops (heuristic)</div></div>
    <div class="kpi"><div class="kpi-label">Error onset</div><div class="kpi-value">{_e(ek.get("err_onset"))}</div><div class="kpi-sub">first minute with failures</div></div>
    <div class="kpi"><div class="kpi-label">504 onset (VU)</div><div class="kpi-value">{_e(ek.get("onset_504_vu"))}</div><div class="kpi-sub">approx. concurrent users</div></div>
    <div class="kpi"><div class="kpi-label">Peak error rate</div><div class="kpi-value red">{ek.get("peak_err_pct", 0)}%</div><div class="kpi-sub">{_e(ek.get("peak_err_time"))} · {_e(ek.get("peak_err_vu"))} VU</div></div>"""

    top_err = payload.get("error_top_minutes") or []
    te_rows = ""
    for row in top_err:
        te_rows += f"""<tr><td>{_e(row.get("time"))}</td><td>{row.get("vu", 0)}</td><td class="red">{row.get("errors", 0)}</td>
        <td>{row.get("samples", 0):,}</td><td class="red">{row.get("err_pct", 0)}%</td><td class="red">{row.get("mean_rt", 0):,}ms</td>
        <td><span class="badge red">{_e(row.get("dominant"))}</span></td></tr>\n"""

    sc = payload.get("scorecard") or {}
    counts = sc.get("counts") or {}
    h, sl, w, c = counts.get("healthy", 0), counts.get("slow", 0), counts.get("warning", 0), counts.get("critical", 0)
    crit_rows = sc.get("critical") or []
    healthy_rows = sc.get("healthy") or []
    crit_tbl = ""
    for r in crit_rows:
        crit_tbl += f"""<tr><td>{_e(r.get("tx"))}</td><td class="mono">{r.get("samples", 0):,}</td><td class="mono">{r.get("mean", 0)}</td>
        <td class="mono">{r.get("p90", 0)}</td><td class="red">{r.get("err_pct", 0)}%</td><td class="mono">{r.get("apdex", 0)}</td>
        <td><span class="badge red">Critical</span></td></tr>\n"""
    ok_tbl = ""
    for r in healthy_rows:
        ok_tbl += f"""<tr><td>{_e(r.get("tx"))}</td><td class="mono">{r.get("samples", 0):,}</td><td class="mono">{r.get("mean", 0)}</td>
        <td class="mono">{r.get("p90", 0)}</td><td class="green">{r.get("err_pct", 0)}%</td><td class="mono">{r.get("apdex", 0)}</td>
        <td><span class="badge green">Healthy</span></td></tr>\n"""

    pg = payload.get("performance_grading")
    pg_html = _render_performance_grading_html(pg if isinstance(pg, dict) else None)

    apdex_cells = payload.get("apdex_cells") or []
    ap_html = ""
    for a in apdex_cells:
        scv = float(a.get("score") or 0)
        col = _apdex_bar_color(scv, str(a.get("tone") or ""))
        ap_html += f"""<div class="apdex-cell">
        <div class="apdex-name">{_e(a.get("name"))}</div>
        <div class="apdex-score" style="color:{col}">{scv:.3f}</div>
        <div class="apdex-bar-track"><div class="apdex-bar" style="width:{min(100, scv*100):.0f}%;background:{col}"></div></div>
        <div class="apdex-rating">{_e(a.get("rating"))}</div></div>\n"""

    rca = payload.get("rca") or []
    n_rca = len(rca) if isinstance(rca, list) else 0
    rca_heading = f"{n_rca} evidence-backed root cause{'s' if n_rca != 1 else ''} with confidence ratings"
    rca_intro = (
        "Each hypothesis below ties together patterns in this JTL — VU-band error and latency shapes, HTTP outcome classes, "
        "and per-controller statistics. Confidence reflects how strongly those signals agree; validate in APM and logs before "
        "closing the loop."
    )
    rca_html = ""
    for card in rca:
        if not isinstance(card, dict):
            continue
        sev = _e(card.get("sev") or "sev2")
        conf_pct = int(card.get("conf") or 0)
        sev_lbl = _e(card.get("sev_label") or ("SEV-1" if sev == "sev1" else "SEV-2"))
        hypo = card.get("hypothesis") or card.get("body") or ""
        evc = card.get("evidence_chain") or card.get("evidence") or ""
        desc = card.get("description") or ""
        rca_html += f"""<div class="rca-card {sev}">
      <div class="rca-top-row">
        <div class="rca-head-left">
          <span class="rca-id-pill">{_e(card.get("id"))}</span>
          <span class="rca-sev-badge">{sev_lbl}</span>
        </div>
        <span class="rca-conf-pill">{conf_pct}% confidence</span>
      </div>
      <div class="rca-headline">{_e(card.get("title"))}</div>
      <div class="rca-desc">{_e(desc)}</div>
      <div class="rca-conf-bar-wrap">
        <div class="rca-conf-bar-track"><div class="rca-conf-bar-fill" style="width:{min(100, max(0, conf_pct))}%"></div></div>
      </div>
      <div class="rca-hypo">{_e(hypo)}</div>
      <div class="rca-evidence-box">
        <span class="rca-evidence-label">Evidence chain:</span>
        <div class="rca-evidence-body">{_e(evc)}</div>
      </div>
    </div>\n"""

    cap = payload.get("capacity") or {}
    succ = payload.get("success_rows") or []
    succ_body = ""
    for s in succ:
        succ_body += f"""<tr><td>{_e(s.get("criterion"))}</td><td class="green">{_e(s.get("target"))}</td>
        <td class="red">{_e(s.get("current"))}</td><td class="amber">{_e(s.get("gap"))}</td></tr>\n"""

    phase_list = payload.get("phase_list") or []
    phases_html = _render_phases(phase_list if isinstance(phase_list, list) else [])

    footer = payload.get("footer") or {}
    chart_json = json.dumps(ch, separators=(",", ":"), allow_nan=False)
    exec_blurb = _e(payload.get("exec_blurb") or "")
    scenario_foot = payload.get("scenario_foot") or ""
    heat_foot = payload.get("heat_foot") or ""

    doc_title = f"Performance Test Report — {title_line}"
    prog(90, "Building HTML shell…")

    logo_uri = _brand_logo_data_uri()
    tag_esc = html.escape(_BRAND_TAGLINE)
    if logo_uri:
        header_brand_block = f"""  <div class="report-header-brand-row">
    <div class="report-brand">
      <img src="{logo_uri}" alt="Autoload.AI" loading="lazy" />
      <div class="report-brand-tagline">{tag_esc}</div>
    </div>
  </div>
"""
        footer_brand_inner = f"""<div class="report-footer-brand">
    <img src="{logo_uri}" alt="" aria-hidden="true" />
    <span class="report-footer-tagline">{tag_esc}</span>
  </div>"""
    else:
        header_brand_block = ""
        footer_brand_inner = ""

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{doc_title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Fraunces:ital,opsz,wght@0,9..144,300;0,9..144,600;1,9..144,300&family=Instrument+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
{_COMBINED_CSS}
</style>
</head>
<body>

<div class="report-header">
{header_brand_block}  <div class="header-eyebrow">Performance Engineering · JMeter Analysis · Confidential</div>
  <h1 class="header-title">{title_line}<br>{report_title}</h1>
  <div class="header-sub">{subtitle}</div>
  <div class="header-meta">
    <div class="header-meta-item"><span class="header-meta-label">Test date</span><span class="header-meta-value">{test_date_line}</span></div>
    <div class="header-meta-item"><span class="header-meta-label">Environment</span><span class="header-meta-value">{_e(meta.get("environment"))}</span></div>
    <div class="header-meta-item"><span class="header-meta-label">Host</span><span class="header-meta-value">{_e(meta.get("host"))}</span></div>
    <div class="header-meta-item"><span class="header-meta-label">Scenarios</span><span class="header-meta-value">{_e(meta.get("scenarios"))}</span></div>
    <div class="header-meta-item"><span class="header-meta-label">Report prepared by</span><span class="header-meta-value">{_e(meta.get("prepared_by"))}</span></div>
  </div>
  <div class="verdict-strip">
    <span class="{pill_cls}">{vprefix}{_e(verdict.get("text"))}</span>
    <span class="verdict-text">{_e(verdict.get("detail"))}</span>
  </div>
</div>

<nav class="sticky-nav">
{nav_html}
</nav>

<div id="panel-overview" class="panel active">
<div class="page">
  <div class="section">
    <div class="section-label">Executive Summary</div>
    <h2 class="section-title">Test at a glance</h2>
    <p class="section-desc">{exec_blurb}</p>
  </div>
  <div class="kpi-grid">{kpi_html}</div>
  {kf_html}
  <div class="section">
    <div class="section-label">Scenarios Tested</div>
    <h2 class="section-title">Business scenario breakdown</h2>
    <div style="background:var(--paper);border:1px solid var(--rule);padding:1.25rem 1.5rem">{scen_html}</div>
    <p style="font-family:var(--mono);font-size:9px;color:var(--gray);margin-top:.5rem">{_e(scenario_foot)}</p>
  </div>
  <div class="section" id="section-deep-assessment">
    <div class="section-label">System Health Zones</div>
    <h2 class="section-title">Load-correlated health progression</h2>
    {zones_preamble_block}
    {zone_html}
  </div>
  <div class="section">
    <div class="section-label">Test Event Timeline</div>
    <h2 class="section-title">Key events during the test</h2>
    <div class="timeline">{tl_html}</div>
  </div>
  {tx_pct_html}
</div></div>

<div id="panel-scorecard" class="panel">
<div class="page">
  {pg_html}
  <div class="section" id="section-issues">
    <div class="section-label">Transaction distribution</div>
    <h2 class="section-title">Controller health mix</h2>
    <p class="section-desc">Based on aggregate transaction_stats plus sample-derived Apdex (T=3s).</p>
    {chart_obs("score_donut")}
  </div>
  <div class="kpi-grid" style="max-width:600px">
    <div class="kpi"><div class="kpi-label">Critical</div><div class="kpi-value red">{c}</div><div class="kpi-sub">transactions</div></div>
    <div class="kpi"><div class="kpi-label">Warning</div><div class="kpi-value amber">{w}</div><div class="kpi-sub">transactions</div></div>
    <div class="kpi"><div class="kpi-label">Slow</div><div class="kpi-value" style="color:var(--blue)">{sl}</div><div class="kpi-sub">transactions</div></div>
    <div class="kpi"><div class="kpi-label">Healthy</div><div class="kpi-value green">{h}</div><div class="kpi-sub">transactions</div></div>
  </div>
  <div class="score-split">
    <div class="chart-card"><div class="chart-wrap" style="height:240px"><canvas id="scorecardDonut"></canvas></div></div>
    <div>
      <h3 class="section-title" style="font-size:1.05rem">Critical transactions</h3>
      <table class="data-table"><thead><tr><th>Transaction</th><th>Samples</th><th>Mean</th><th>P90</th><th>Err%</th><th>Apdex</th><th>Status</th></tr></thead><tbody>{crit_tbl}</tbody></table>
      <h3 class="section-title" style="font-size:1.05rem;margin-top:1rem">Healthy sample (top)</h3>
      <table class="data-table"><thead><tr><th>Transaction</th><th>Samples</th><th>Mean</th><th>P90</th><th>Err%</th><th>Apdex</th><th>Status</th></tr></thead><tbody>{ok_tbl}</tbody></table>
    </div>
  </div>
</div></div>

<div id="panel-rt" class="panel">
<div class="page">
  <div class="section">
    <div class="section-label">Response Time Behaviour</div>
    <h2 class="section-title">How response time evolves with load</h2>
    <p class="section-desc">End-to-end response times from JMeter samples. Latency / connect fields are shown in the decomposition table.</p>
  </div>
  <div class="chart-card">
    <div class="chart-title">Mean RT &amp; P90 RT vs concurrent users over time</div>
    <div class="chart-desc">Red = Mean RT · Dashed amber = P90 RT · Green dashes = concurrent user count</div>
    {chart_obs("rt_main")}
    <div class="chart-wrap" style="height:280px"><canvas id="rtMainChart"></canvas></div>
  </div>
  <div class="two-col">
    <div class="chart-card">
      <div class="chart-title">RT percentile spread by load band</div>
      <div class="chart-desc">Median · P75 · P90 · P95 (successful samples)</div>
      {chart_obs("rt_percentile")}
      <div class="chart-wrap" style="height:220px"><canvas id="rtPercentileChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">TTFB (first byte) vs Total elapsed — by load band</div>
      <div class="chart-desc">Stacked median TTFB (latency) vs remainder</div>
      {chart_obs("ttfb")}
      <div class="chart-wrap" style="height:220px"><canvas id="ttfbChart"></canvas></div>
    </div>
  </div>
  <div class="section">
    <div class="section-label">Response Time Distribution</div>
    <h2 class="section-title">Heatmap by bucket &amp; load</h2>
    {chart_obs("heatmap")}
    <div style="overflow-x:auto">
    <table class="heat-table">
      <thead><tr><th style="text-align:left">Load band</th>{heat_heads}</tr></thead>
      <tbody>{heat_body}</tbody>
    </table>
    </div>
    {dist_sla_html}
    <p style="font-family:var(--mono);font-size:9px;color:var(--gray);margin-top:.5rem">{heat_foot}</p>
  </div>
  <div class="section">
    <div class="section-label">Latency Decomposition</div>
    <!-- latency_diag: {_e(payload.get("latency_diag_version") or "unknown")} -->
    <h2 class="section-title">Where does the time go?</h2>
    {chart_obs("lat_decomp")}
    <table class="data-table">
      <thead><tr><th>Load band</th><th>TCP connect (med)</th><th>TCP P90</th><th>TTFB (med)</th><th>TTFB P90</th><th>Total elapsed (med)</th><th>Server process (med)</th><th>Diagnosis</th></tr></thead>
      <tbody>{lat_body}</tbody>
    </table>
  </div>
</div></div>

<div id="panel-throughput" class="panel">
<div class="page">
  <div class="section">
    <div class="section-label">Throughput &amp; Responsiveness</div>
    <h2 class="section-title">Work completed per second</h2>
    <p class="section-desc">TPS is derived from samples per wall-clock minute. Compare peak bands for scalability signals.</p>
  </div>
  <div class="kpi-grid">{tp_k_html}</div>
  <div class="chart-card">
    <div class="chart-title">TPS vs concurrent users</div>
    {chart_obs("tps_main")}
    <div class="chart-wrap" style="height:280px"><canvas id="tpsMainChart"></canvas></div>
  </div>
  <div class="two-col">
    <div class="chart-card">
      <div class="chart-title">Average TPS by load band</div>
      {chart_obs("tps_band")}
      <div class="chart-wrap" style="height:200px"><canvas id="tpsBandChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Bandwidth by load band (MB)</div>
      {chart_obs("bw")}
      <div class="chart-wrap" style="height:200px"><canvas id="bwChart"></canvas></div>
    </div>
  </div>
</div></div>

<div id="panel-errors" class="panel">
<div class="page">
  <div class="section">
    <div class="section-label">Error Analysis</div>
    <h2 class="section-title">Failures vs load</h2>
    <p class="section-desc">4xx/5xx counts are taken from JMeter <code>response_code</code>. Connection drops use response / failure message heuristics.</p>
  </div>
  <div class="kpi-grid">{err_k_html}</div>
  <div class="two-col">
    <div class="chart-card">
      <div class="chart-title">Error rate vs mean RT</div>
      {chart_obs("err_corr")}
      <div class="chart-wrap" style="height:220px"><canvas id="errCorrChart"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">Error composition by load band</div>
      {chart_obs("err_band")}
      <div class="chart-wrap" style="height:220px"><canvas id="errBandChart"></canvas></div>
    </div>
  </div>
  <div class="section">
    <div class="section-label">Error spike minutes</div>
    <h2 class="section-title">Highest error-rate minutes</h2>
    <table class="data-table">
      <thead><tr><th>Time (UTC)</th><th>VU</th><th>Errors</th><th>Samples</th><th>Error rate</th><th>Mean RT</th><th>Mix</th></tr></thead>
      <tbody>{te_rows}</tbody>
    </table>
  </div>
</div></div>

<div id="panel-apdex" class="panel">
<div class="page">
  <div class="section-label">Apdex</div>
  <h2 class="section-title">User-perceived performance (T=3s)</h2>
  <div class="chart-card">
    <div class="chart-title">Apdex by load band</div>
    {chart_obs("apdex_band")}
    <div class="chart-wrap" style="height:220px"><canvas id="apdexBandChart"></canvas></div>
  </div>
  <div class="apdex-grid">{ap_html}</div>
</div></div>

<div id="panel-rca" class="panel">
<div class="page">
  <div class="section-label">Root cause analysis</div>
  <h2 class="section-title">{rca_heading}</h2>
  <p class="section-desc rca-panel-intro">{rca_intro}</p>
  {rca_html}
</div></div>

<div id="panel-capacity" class="panel">
<div class="page">
  <div class="section-label">Capacity</div>
  <h2 class="section-title">Envelope &amp; remediation</h2>
  <div class="capacity-box">
    <div class="cap-item">
      <div class="cap-label">Proven safe capacity</div>
      <div class="cap-value">{_e(cap.get("safe_range") or (str(cap.get("safe_vu", 0)) + " VU"))}</div>
      <div class="cap-sub">{_e(cap.get("safe_sub"))}</div>
    </div>
    <div class="cap-item">
      <div class="cap-label">Marginal / next tier</div>
      <div class="cap-value">{_e(cap.get("marginal_range") or (str(cap.get("medium_vu", 0)) + " VU"))}</div>
      <div class="cap-sub">{_e(cap.get("med_sub"))}</div>
    </div>
    <div class="cap-item">
      <div class="cap-label">Observed peak (dataset)</div>
      <div class="cap-value">{_e(cap.get("peak_range") or (str(cap.get("target_vu", 0)) + " VU"))}</div>
      <div class="cap-sub">{_e(cap.get("target_sub") or "")}</div>
    </div>
  </div>
  <div class="section" id="section-resolution-plan">
    <div class="section-label">Remediation roadmap</div>
    <h2 class="section-title">Phased optimisation plan</h2>
    <p class="section-desc">Prioritised actions and expected outcomes per phase (from analyser output). Timelines are indicative.</p>
    {phases_html}
  </div>
  <div class="section">
    <div class="section-label">Success criteria</div>
    <h2 class="section-title">🎯 Success Metrics & Targets</h2>
    <table class="data-table">
      <thead><tr><th>Criterion</th><th>Target</th><th>Current</th><th>Gap</th></tr></thead>
      <tbody>{succ_body}</tbody>
    </table>
  </div>
</div></div>

<div style="background:var(--ink);color:rgba(245,243,238,.4);padding:1.5rem 3rem;font-family:var(--mono);font-size:9px;display:flex;justify-content:space-between;align-items:flex-end;flex-wrap:wrap;gap:1rem;margin-top:3rem">
  <div style="display:flex;flex-direction:column;gap:0.35rem">
    <span>{_e(footer.get("left"))}</span>
    {footer_brand_inner}
  </div>
  <span>{_e(footer.get("right"))}</span>
</div>
"""
    html_out = html_out + _COMBINED_CHART_JS.replace("__CHARTS_JSON__", chart_json) + "\n</body>\n</html>\n"
    prog(100, "Combined load report ready")
    return html_out

"""
Enterprise report styling aligned with enterprise_report_wireframe_v4.html (PerfSuite).
Used by JMeter, Web Vitals/Lighthouse, comparison, and A/B comparison HTML reports.
"""
from typing import List, Optional, Tuple

NavItem = Tuple[str, str, str]  # anchor id, label, icon class (Tabler)

ENTERPRISE_FONT_LINKS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.10.0/tabler-icons.min.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
"""


def get_enterprise_css(*, include_legacy: bool = True, extra: str = "") -> str:
    """Return <style> block with enterprise design tokens and optional legacy class aliases."""
    legacy = _LEGACY_ALIASES_CSS if include_legacy else ""
    extra_block = ""
    if extra:
        extra_block = extra if extra.strip().startswith("<style") else f"<style>\n{extra}\n</style>"
    return f"<style>\n{_ENTERPRISE_CORE_CSS}\n{legacy}\n</style>{extra_block}"


def render_report_header(
    title: str,
    subtitle: str = "",
    *,
    icon_class: str = "ti ti-chart-infographic",
    icon_tone: str = "bl",
    actions_html: str = "",
) -> str:
    """PerfSuite page header (.ph) from wireframe v4."""
    actions = f'<div class="ph-act">{actions_html}</div>' if actions_html else ""
    sub = f'<div class="ph-mt">{subtitle}</div>' if subtitle else ""
    return f"""
<header class="ph report-header">
  <div class="ph-ic ph-ic-{icon_tone}"><i class="{icon_class}"></i></div>
  <div class="ph-body">
    <div class="ph-ttl">{title}</div>
    {sub}
  </div>
  {actions}
</header>"""


def render_colour_legend() -> str:
    """SLA colour legend strip (wireframe transaction page)."""
    return """
<div class="colour-legend">
  <span class="colour-legend-title">Colour coding</span>
  <span><span class="sd sd-ok"></span>Green — within SLA (RT &lt;2s, Err &lt;1%)</span>
  <span><span class="sd sd-wn"></span>Amber — warning (RT 2–5s, Err 1–5%)</span>
  <span><span class="sd sd-er"></span>Red — SLA violation (RT &gt;5s, Err &gt;5%)</span>
</div>"""


def render_report_body_open() -> str:
    return '<div class="body report-body"><div class="container">'


def render_report_body_close() -> str:
    return "</div></div>"


def render_report_sidebar(nav_items: List[NavItem]) -> str:
    """Left navigation for in-report section jumping."""
    links = []
    for anchor_id, label, icon in nav_items:
        links.append(
            f'<a class="rn-link" href="#{anchor_id}" data-anchor="{anchor_id}">'
            f'<i class="{icon}"></i><span>{label}</span></a>'
        )
    return f"""
<aside class="rpt-nav no-print" aria-label="Report sections">
  <div class="rn-title">Report sections</div>
  <nav class="rn-links">{"".join(links)}</nav>
</aside>"""


def render_report_shell_open(nav_items: Optional[List[NavItem]] = None) -> str:
    nav = render_report_sidebar(nav_items) if nav_items else ""
    return f'<div class="report-main rpt-shell">{nav}<div class="rpt-main-col">'


def render_report_shell_close() -> str:
    return "</div></div>"


def section_anchor(section_id: str, html: str) -> str:
    """Wrap a report block with a stable id for sidebar navigation."""
    return f'<div id="{section_id}" class="report-anchor">{html}</div>'


def render_report_navigation_script() -> str:
    return """
<script>
(function () {
  var links = document.querySelectorAll('.rn-link');
  if (!links.length) return;
  var sections = [];
  links.forEach(function (a) {
    var id = a.getAttribute('data-anchor');
    var el = document.getElementById(id);
    if (!el) return;
    sections.push({ link: a, el: el });
    a.addEventListener('click', function (e) {
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      links.forEach(function (l) { l.classList.remove('on'); });
      a.classList.add('on');
    });
  });
  if (!sections.length) return;
  function onScroll() {
    var y = window.scrollY + 120;
    var active = sections[0];
    sections.forEach(function (s) {
      if (s.el.offsetTop <= y) active = s;
    });
    links.forEach(function (l) { l.classList.remove('on'); });
    if (active) active.link.classList.add('on');
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
</script>"""


# Default section nav for JMeter performance assessment reports
JMETER_REPORT_NAV: List[NavItem] = [
    ("report-executive", "Executive Summary", "ti ti-flag"),
    ("report-distribution", "Distribution Analysis", "ti ti-chart-dots"),
    ("report-scorecard", "Scorecard", "ti ti-chart-radar"),
    ("report-overview", "Test Overview & Transactions", "ti ti-table"),
    ("report-system-graph", "System Behaviour", "ti ti-chart-line"),
    ("report-graphs", "Additional Graphs", "ti ti-chart-area"),
    ("report-issues", "Issues", "ti ti-alert-triangle"),
    ("report-business", "Business Impact", "ti ti-building-bank"),
    ("report-action-plan", "Action Plan", "ti ti-list-check"),
    ("report-metrics", "Success Metrics", "ti ti-target"),
    ("report-conclusion", "Conclusion", "ti ti-checklist"),
    ("report-footer", "Next Steps", "ti ti-arrow-right"),
]

LIGHTHOUSE_REPORT_NAV: List[NavItem] = [
    ("report-executive", "Executive Summary", "ti ti-flag"),
    ("report-scorecard", "Scorecard", "ti ti-chart-radar"),
    ("report-overview", "Test Overview", "ti ti-table"),
    ("report-metrics", "Detailed Metrics", "ti ti-list-details"),
    ("report-issues", "Issues", "ti ti-alert-triangle"),
    ("report-roadmap", "Roadmap", "ti ti-route"),
    ("report-business", "Business Impact", "ti ti-building-bank"),
    ("report-monitoring", "Monitoring", "ti ti-eye"),
    ("report-aiml", "AIML Appendix", "ti ti-robot"),
    ("report-conclusion", "Conclusion", "ti ti-checklist"),
    ("report-details", "Report Details", "ti ti-info-circle"),
]

COMPARISON_REPORT_NAV: List[NavItem] = [
    ("report-executive", "Executive Summary", "ti ti-flag"),
    ("report-jmeter", "JMeter Comparison", "ti ti-flask"),
    ("report-webvitals", "Web Vitals", "ti ti-gauge"),
    ("report-regressions", "Regressions", "ti ti-trending-down"),
    ("report-improvements", "Improvements", "ti ti-trending-up"),
]

AB_COMPARISON_REPORT_NAV: List[NavItem] = [
    ("report-executive", "Executive Summary", "ti ti-flag"),
    ("report-release", "Release Decision", "ti ti-building-bank"),
    ("report-distribution", "Distribution Analysis", "ti ti-chart-dots"),
    ("report-grades", "Grade Comparison", "ti ti-chart-radar"),
    ("report-metrics", "Detailed Metrics", "ti ti-list-details"),
    ("report-charts", "Charts", "ti ti-chart-line"),
    ("report-conclusion", "Conclusion", "ti ti-checklist"),
]


def render_report_foot(
    *,
    generated: str = "",
    generated_by: str = "Raghvendra Kumar",
    classification: str = "Internal",
    extra: str = "",
) -> str:
    """Wireframe footer bar."""
    gen = f"<strong>Generated:</strong> {generated}" if generated else ""
    extra_div = f'<div class="fdv"></div>{extra}' if extra else ""
    return f"""
<footer class="foot report-foot">
  {gen}
  <div class="fdv"></div>
  <strong>Generated by:</strong> {generated_by}
  <div class="fdv"></div>
  <strong>Classification:</strong> {classification}
  {extra_div}
  <div style="margin-left:auto" class="no-print">
    <button type="button" class="btn bp" onclick="window.print()"><i class="ti ti-download"></i> PDF</button>
  </div>
</footer>"""


_ENTERPRISE_CORE_CSS = """
:root {
  --ink: #07070e; --ink2: #26263a; --ink3: #545468; --ink4: #8a8aa0;
  --bg: #f1f1f6; --bg2: #e3e3ec; --sur: #ffffff;
  --brd: rgba(7,7,14,.07); --brd2: rgba(7,7,14,.13);
  --bl: #1242c0; --bl-lt: #ebefff; --bl-md: #b3c3f8;
  --gn: #076b44; --gn-lt: #e1f4ec; --gn-md: #9fd4bc;
  --am: #9a5a00; --am-lt: #fff2d4; --am-md: #f5c660;
  --rd: #aa1515; --rd-lt: #fce8e8; --rd-md: #f5aaaa;
  --pu: #4e22b0; --pu-lt: #f0eaff;
  --te: #077070; --te-lt: #e1f3f3;
  --r: 4px; --rl: 10px; --rx: 16px;
  --primary-color: var(--bl);
  --success-color: var(--gn);
  --warning-color: var(--am);
  --danger-color: var(--rd);
  --secondary-color: var(--ink3);
  --background-light: var(--bg);
  --card-background: var(--sur);
  --text-primary: var(--ink);
  --text-secondary: var(--ink3);
  --border-color: var(--brd2);
}
*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: 'Inter', system-ui, sans-serif;
  background: var(--bg);
  color: var(--ink);
  font-size: 13px;
  line-height: 1.55;
}
.report-main {
  min-height: 100vh;
  background: var(--bg);
}
.rpt-shell {
  display: grid;
  grid-template-columns: 220px 1fr;
  min-height: 100vh;
}
.rpt-main-col {
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}
.rpt-nav {
  background: #0f0f1c;
  border-right: 1px solid rgba(255,255,255,.06);
  padding: 14px 0;
  position: sticky;
  top: 0;
  align-self: start;
  height: 100vh;
  overflow-y: auto;
  scrollbar-width: thin;
}
.rn-title {
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .09em;
  color: rgba(255,255,255,.22);
  padding: 0 14px 10px;
}
.rn-links { display: flex; flex-direction: column; gap: 1px; }
.rn-link {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 14px;
  font-size: 12px;
  color: rgba(255,255,255,.38);
  text-decoration: none;
  transition: background .12s, color .12s;
}
.rn-link .ti { font-size: 14px; flex-shrink: 0; }
.rn-link:hover {
  color: rgba(255,255,255,.78);
  background: rgba(255,255,255,.05);
}
.rn-link.on {
  color: #fff;
  background: rgba(18,66,192,.22);
  font-weight: 500;
}
.rn-link.on .ti { color: #6b98f5; }
.report-anchor { scroll-margin-top: 16px; }
.report-body { flex: 1; }
.report-body > .container { max-width: none; padding: 0; margin: 0; }
.report-readable,
.report-readable p,
.report-readable li,
.report-readable h3,
.report-readable h4,
.report-readable h5,
.report-readable td,
.report-readable th {
  color: var(--ink2) !important;
}
.report-readable h3,
.report-readable h4,
.report-readable h5 { color: var(--ink) !important; }
.executive-summary .report-readable,
.executive-summary .report-readable p,
.executive-summary .report-readable li,
.executive-summary .report-readable h3,
.executive-summary .report-readable h4 {
  color: var(--ink2) !important;
}
.executive-summary .report-readable h3 { color: var(--ink) !important; }
.chart-container {
  position: relative;
  width: 100%;
  max-width: 100%;
  height: min(360px, 40vh);
  min-height: 240px;
  overflow: hidden;
}
.chart-container canvas { max-width: 100% !important; height: 100% !important; }
.report-graph-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  max-width: 100%;
  align-items: start;
}
.report-graph-panel {
  background: var(--sur);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
  padding: 12px;
  min-width: 0;
  overflow: hidden;
}
.report-graph-panel h4 {
  margin: 0 0 10px 0;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--ink);
}
.report-data-panel {
  background: var(--bg);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
  padding: 12px;
  max-height: 360px;
  overflow: auto;
  min-width: 0;
}
.report-data-panel h4 { color: var(--ink); font-size: 11.5px; margin: 0 0 8px 0; }
.chart-granularity-note {
  font-size: 10px;
  color: var(--ink4);
  margin-bottom: 8px;
}
.tsc { overflow-x: auto; max-width: 100%; -webkit-overflow-scrolling: touch; }
.mn { font-family: 'JetBrains Mono', monospace; font-size: 11px; }

/* Page header */
.ph {
  background: var(--sur);
  border-bottom: 1px solid var(--brd);
  padding: 20px 26px 16px;
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.ph-ic {
  width: 38px; height: 38px; border-radius: var(--rl);
  display: flex; align-items: center; justify-content: center;
  font-size: 17px; flex-shrink: 0;
}
.ph-ic-bl { background: var(--bl-lt); color: var(--bl); }
.ph-ic-gn { background: var(--gn-lt); color: var(--gn); }
.ph-ic-am { background: var(--am-lt); color: var(--am); }
.ph-ic-pu { background: var(--pu-lt); color: var(--pu); }
.ph-ic-te { background: var(--te-lt); color: var(--te); }
.ph-body { flex: 1; min-width: 0; }
.ph-ttl { font-size: 16px; font-weight: 600; color: var(--ink); letter-spacing: -.02em; }
.ph-mt { font-size: 11.5px; color: var(--ink4); margin-top: 2px; line-height: 1.45; }
.ph-act { display: flex; gap: 5px; margin-left: auto; align-items: center; flex-shrink: 0; }

.colour-legend {
  padding: 10px 26px;
  background: var(--sur);
  border-bottom: 1px solid var(--brd);
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  font-size: 11px;
  color: var(--ink3);
  align-items: center;
}
.colour-legend-title { font-weight: 600; color: var(--ink2); }

/* Buttons */
.btn {
  display: inline-flex; align-items: center; gap: 5px;
  padding: 5px 12px; border-radius: var(--r);
  font-size: 11.5px; font-weight: 500; cursor: pointer;
  border: none; font-family: inherit; transition: all .12s;
}
.bp { background: var(--bl); color: #fff; }
.bp:hover { background: #0a2f9e; }
.bg-btn {
  background: transparent; border: 1px solid var(--brd2); color: var(--ink2);
}
.bg-btn:hover { background: var(--bg); }

/* Pills */
.p {
  font-size: 10px; font-weight: 500; padding: 2px 7px;
  border-radius: 20px; display: inline-flex; align-items: center; gap: 2px;
}
.p-bl { background: var(--bl-lt); color: var(--bl); }
.p-gn { background: var(--gn-lt); color: var(--gn); }
.p-am { background: var(--am-lt); color: var(--am); }
.p-rd { background: var(--rd-lt); color: var(--rd); }
.p-gy { background: var(--bg2); color: var(--ink3); }

/* Cards */
.card {
  background: var(--sur);
  border: 1px solid var(--brd);
  border-radius: var(--rx);
  overflow: hidden;
  margin: 16px 0;
}
.chd {
  padding: 12px 16px;
  border-bottom: 1px solid var(--brd);
  display: flex; align-items: center; gap: 7px;
}
.ctt { font-size: 12px; font-weight: 600; color: var(--ink); }
.cbd { padding: 16px; }

/* KPI strip */
.kstr {
  display: grid; gap: 1px;
  background: var(--brd);
  border-radius: var(--rx);
  overflow: hidden;
  border: 1px solid var(--brd);
  margin: 16px 0;
}
.kpi {
  background: var(--sur);
  padding: 12px 14px;
  display: flex; flex-direction: column; gap: 2px;
}
.klb {
  font-size: 9.5px; font-weight: 600; color: var(--ink4);
  text-transform: uppercase; letter-spacing: .04em;
}
.kval {
  font-size: 20px; font-weight: 600; letter-spacing: -.03em;
  color: var(--ink); font-family: 'JetBrains Mono', monospace; line-height: 1.1;
}
.kv-bl { color: var(--bl); }
.kv-gn { color: var(--gn); }
.kv-am { color: var(--am); }
.kv-rd { color: var(--rd); }
.kdlt { font-size: 10px; margin-top: 1px; color: var(--ink4); }
.ku { color: var(--gn); }
.kd { color: var(--rd); }

/* Tables */
.dt, table.endpoint-table, table {
  width: 100%;
  border-collapse: collapse;
  font-size: 11.5px;
}
.dt th, .endpoint-table th, table th {
  text-align: left;
  font-size: 9.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--ink4);
  padding: 8px 12px;
  border-bottom: 1px solid var(--brd);
  background: var(--bg);
  white-space: nowrap;
}
.dt td, .endpoint-table td, table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--brd);
  color: var(--ink2);
  vertical-align: middle;
}
.dt tr:last-child td, .endpoint-table tr:last-child td { border-bottom: none; }
.dt tr:hover td, .endpoint-table tbody tr:hover td { background: var(--bg); }
.tsc { overflow-x: auto; }

/* Status dots */
.sd { width: 5px; height: 5px; border-radius: 50%; display: inline-block; margin-right: 3px; }
.sd-ok { background: var(--gn); }
.sd-wn { background: var(--am); }
.sd-er { background: var(--rd); }

/* Alerts */
.alrt { padding: 11px 14px; border-radius: var(--rl); border-left: 3px solid; margin: 8px 0; }
.a-rd { background: var(--rd-lt); border-color: var(--rd); }
.a-am { background: var(--am-lt); border-color: var(--am); }
.a-gn { background: var(--gn-lt); border-color: var(--gn); }
.a-bl { background: var(--bl-lt); border-color: var(--bl); }
.att { font-size: 11.5px; font-weight: 600; margin-bottom: 3px; }

/* Grade hero */
.g-hero {
  background: var(--sur);
  border-bottom: 1px solid var(--brd);
  padding: 18px 26px;
  display: flex; align-items: center; gap: 22px;
}
.g-ring { width: 74px; height: 74px; position: relative; flex-shrink: 0; }
.g-in {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center; flex-direction: column;
}
.g-lt { font-size: 24px; font-weight: 600; color: var(--ink); line-height: 1; }
.g-sc { font-size: 9px; color: var(--ink4); }

/* Exec banner (comparison) */
.exec-bar {
  padding: 16px 26px;
  display: flex; align-items: center; gap: 18px;
  border-bottom: 1px solid var(--brd);
  color: #fff;
}
.exec-bar.amber { background: linear-gradient(135deg, #4f2000, var(--am)); }
.exec-bar.red { background: linear-gradient(135deg, #4f0000, var(--rd)); }
.exec-bar.green { background: linear-gradient(135deg, #002f1a, var(--gn)); }
.et {
  padding: 10px 13px; border-radius: var(--rl);
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.18);
  min-width: 130px;
}
.et-lbl {
  font-size: 9px; font-weight: 600;
  color: rgba(255,255,255,.55);
  text-transform: uppercase; letter-spacing: .05em;
}
.et-val {
  font-size: 15px; font-weight: 700; color: #fff;
  font-family: 'JetBrains Mono', monospace;
}

/* Compare rows */
.chr {
  display: grid;
  grid-template-columns: 160px 1fr 1fr;
  border-bottom: 1px solid var(--brd);
}
.cm { padding: 10px 13px; font-size: 11px; font-weight: 600; color: var(--ink3); border-right: 1px solid var(--brd); }
.cv {
  padding: 10px 13px; font-size: 11.5px;
  font-family: 'JetBrains Mono', monospace; color: var(--ink);
  border-right: 1px solid var(--brd);
}
.cw { background: var(--gn-lt); }
.cl { background: var(--rd-lt); color: var(--rd); }
.cn { background: var(--am-lt); }

/* Fairness box */
.fw-box {
  padding: 13px 15px; border-radius: var(--rl);
  background: var(--am-lt); border: 1px solid var(--am-md);
  margin: 16px 0;
}
.fw-ttl { font-size: 12px; font-weight: 600; color: var(--am); margin-bottom: 6px; }
.fw-ul { padding-left: 14px; }
.fw-ul li { font-size: 11.5px; color: var(--ink2); line-height: 1.5; margin: 4px 0; }

/* Progress */
.pb { flex: 1; height: 4px; border-radius: 99px; background: var(--bg2); overflow: hidden; }
.pf { height: 100%; border-radius: 99px; }

/* Footer */
.foot, .footer {
  background: var(--sur);
  border-top: 1px solid var(--brd);
  padding: 11px 26px;
  display: flex; align-items: center; gap: 14px;
  font-size: 10.5px; color: var(--ink4);
  margin-top: 24px;
}
.foot strong, .footer strong { color: var(--ink2); }
.fdv { width: 1px; height: 11px; background: var(--brd2); }

.body-pad { padding: 20px 26px; display: flex; flex-direction: column; gap: 16px; }
.g2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.g3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.g4 { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }

.chart-container { position: relative; height: 320px; margin: 12px 0; }
.two-column { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }

/* Grade scale */
.gs-strip { display: flex; border-radius: var(--r); overflow: hidden; height: 7px; margin: 8px 0; }
.gs-a { flex: 1; background: #076b44; }
.gs-b { flex: 1; background: #3a9060; }
.gs-c { flex: 1; background: var(--am); }
.gs-d { flex: 1; background: #8a4000; }
.gs-e { flex: 1; background: #9e1010; }
.gs-f { flex: 1; background: var(--rd); }

.slb {
  font-size: 9px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .08em; color: var(--ink4);
  display: flex; align-items: center; gap: 7px; margin: 12px 0 8px;
}
.slb::after { content: ''; flex: 1; height: 1px; background: var(--brd); }

::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-thumb { background: rgba(0,0,0,.1); border-radius: 99px; }

@media (max-width: 900px) {
  .g2, .g3, .g4, .two-column { grid-template-columns: 1fr; }
  .kstr { grid-template-columns: repeat(2, 1fr) !important; }
  .rpt-shell { grid-template-columns: 1fr; }
  .rpt-nav {
    position: relative;
    height: auto;
    max-height: 220px;
    width: 100%;
  }
  .report-graph-grid { grid-template-columns: 1fr; }
}
@media print {
  .rpt-nav { display: none !important; }
  .rpt-shell { grid-template-columns: 1fr !important; }
}
"""

_LEGACY_ALIASES_CSS = """
/* Legacy report class → enterprise look */
.container { max-width: 1280px; margin: 0 auto; padding: 0; }
.header {
  background: var(--sur);
  color: var(--ink);
  padding: 20px 26px;
  text-align: left;
  border-bottom: 1px solid var(--brd);
  box-shadow: none;
}
.header h1 {
  font-size: 16px;
  font-weight: 600;
  letter-spacing: -.02em;
  margin-bottom: 4px;
  color: var(--ink);
}
.header p { font-size: 11.5px; color: var(--ink4); opacity: 1; }
.section {
  background: var(--sur);
  margin: 16px 26px;
  padding: 0;
  border-radius: var(--rx);
  border: 1px solid var(--brd);
  box-shadow: none;
  overflow: hidden;
}
.section > h2, .section > h3 {
  padding: 12px 16px;
  margin: 0;
  border-bottom: 1px solid var(--brd);
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
  background: var(--sur);
}
.section > *:not(h2):not(h3) { padding-left: 16px; padding-right: 16px; }
.section > table, .section > .tsc, .section > .metrics-grid,
.section > .chart-container, .section > .executive-summary,
.section > div:first-of-type { padding: 16px; }
.section h2 {
  border-bottom: 1px solid var(--brd);
  padding-bottom: 12px;
  color: var(--ink);
  font-size: 12px;
}
.section h3 { font-size: 12px; font-weight: 600; color: var(--ink); }
.section p, .section li, .section td, .section th, .section .muted,
.inner-list, .inner-list li { color: var(--ink2); }
.section .muted { color: var(--ink3) !important; }
.metric-card, .metric-card .metric-label { color: var(--ink2); }
.metric-value { color: var(--ink); }
.executive-summary {
  background: var(--sur);
  color: var(--ink2);
  padding: 18px 26px !important;
  border-radius: 0;
  margin: 0;
  border: none;
  border-bottom: 1px solid var(--brd);
}
.executive-summary.exec-traffic-green {
  border-left: 4px solid var(--gn);
}
.executive-summary.exec-traffic-amber {
  border-left: 4px solid var(--am);
}
.executive-summary.exec-traffic-red {
  border-left: 4px solid var(--rd);
}
.executive-summary .exec-status-banner {
  background: var(--bg);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
  padding: 12px 14px;
  margin-bottom: 14px;
}
.executive-summary .exec-status-banner h3 {
  margin: 0 0 6px 0;
  font-size: 12px;
  font-weight: 600;
}
.executive-summary .exec-status-banner p {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.5;
  color: var(--ink2);
}
.endpoint-table td:not(:first-child),
.endpoint-table th:not(:first-child) {
  text-align: right;
}
.endpoint-table td.mn,
.endpoint-table .mn { font-family: 'JetBrains Mono', monospace; font-size: 11px; }
/* Graph understanding — RT vs TP row-aligned comparison */
.graph-analysis-wrap {
  margin-top: 12px;
  padding: 14px;
  background: var(--bg);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
}
.graph-analysis-wrap > h3 {
  margin: 0 0 12px 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--ink);
}
.graph-analysis-compare {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
}
.graph-analysis-compare thead th {
  width: 50%;
  padding: 8px 10px;
  font-size: 11px;
  font-weight: 600;
  color: var(--ink);
  text-align: left;
  vertical-align: bottom;
  border-bottom: 1px solid var(--brd);
  background: var(--sur);
}
.graph-analysis-compare thead th:first-child {
  border-right: 1px solid var(--brd);
}
.graph-analysis-compare tbody tr + tr td {
  border-top: 10px solid transparent;
}
.graph-analysis-compare tbody td {
  width: 50%;
  vertical-align: top;
  padding: 0 10px 0 0;
}
.graph-analysis-compare tbody td + td {
  padding: 0 0 0 10px;
  border-left: 1px solid var(--brd);
}
.graph-analysis-card {
  height: 100%;
  min-height: 72px;
  padding: 12px;
  background: var(--sur);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
  box-sizing: border-box;
}
.graph-analysis-card--empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink4);
  font-size: 11px;
}
.graph-analysis-card h5,
.graph-analysis-card .gac-title {
  margin: 0 0 8px 0;
  font-size: 10.5px;
  font-weight: 600;
  color: var(--ink);
}
.graph-analysis-card p,
.graph-analysis-card li {
  margin: 0;
  font-size: 11px;
  line-height: 1.55;
  color: var(--ink2);
}
.graph-analysis-card ul {
  margin: 0;
  padding-left: 1.1rem;
}
.graph-analysis-card .gac-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px 10px;
  font-size: 10.5px;
  color: var(--ink2);
}
.graph-analysis-card .gac-stats strong {
  color: var(--ink);
  font-weight: 600;
}
.graph-analysis-badge {
  display: inline-block;
  margin-top: 4px;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 9px;
  font-weight: 600;
  text-transform: uppercase;
  color: #fff;
}
.graph-analysis-business {
  margin-top: 14px;
}
@media (max-width: 768px) {
  .graph-analysis-compare thead { display: none; }
  .graph-analysis-compare,
  .graph-analysis-compare tbody,
  .graph-analysis-compare tr,
  .graph-analysis-compare td {
    display: block;
    width: 100%;
  }
  .graph-analysis-compare tbody td + td {
    border-left: none;
    border-top: 1px solid var(--brd);
    padding: 10px 0 0;
    margin-top: 10px;
  }
  .graph-analysis-compare tbody tr + tr td {
    border-top: none;
    margin-top: 14px;
    padding-top: 14px;
    border-top: 1px solid var(--brd);
  }
}
/* Scorecard detailed metrics — fixed columns, dividers, aligned headers/cells */
.scorecard-metrics-table {
  width: 100%;
  table-layout: fixed;
  border-collapse: collapse;
  font-size: 11.5px;
  border: 1px solid var(--brd);
  background: var(--sur);
}
.scorecard-metrics-table th,
.scorecard-metrics-table td {
  padding: 9px 12px;
  border-bottom: 1px solid var(--brd);
  border-right: 1px solid var(--brd);
  vertical-align: middle;
  color: var(--ink2);
}
.scorecard-metrics-table th:last-child,
.scorecard-metrics-table td:last-child {
  border-right: none;
}
.scorecard-metrics-table thead th {
  font-size: 9.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .05em;
  color: var(--ink4);
  background: var(--bg);
  white-space: nowrap;
}
.scorecard-metrics-table tbody tr:hover td {
  background: var(--bg);
}
.scorecard-metrics-table .scm-metric {
  text-align: left;
  font-weight: 600;
  color: var(--ink);
  width: 26%;
}
.scorecard-metrics-table .scm-result,
.scorecard-metrics-table .scm-target {
  text-align: center;
  width: 17%;
}
.scorecard-metrics-table .scm-status {
  text-align: center;
  width: 24%;
}
.scorecard-metrics-table .scm-score {
  text-align: center;
  width: 16%;
  font-weight: 600;
  color: var(--ink);
}
.scorecard-metrics-table .scm-result,
.scorecard-metrics-table .scm-target,
.scorecard-metrics-table .scm-score {
  font-family: 'JetBrains Mono', monospace;
  font-size: 11px;
}
.scorecard-metrics-table .scm-status .p {
  display: inline-block;
  white-space: nowrap;
}
.kv-gn { color: var(--gn); }
.kv-am { color: var(--am); }
.kv-rd { color: var(--rd); }
.kv-bl { color: var(--bl); }
.alert { padding: 11px 14px; border-radius: var(--rl); border-left: 3px solid; margin: 8px 0; }
.alert-success, .alert.alert-success { background: var(--gn-lt); border-color: var(--gn); color: var(--ink2); }
.alert-warning, .alert.alert-warning { background: var(--am-lt); border-color: var(--am); color: var(--ink2); }
.alert-danger, .alert.alert-danger { background: var(--rd-lt); border-color: var(--rd); color: var(--ink2); }
.alert h3, .alert h4 { font-size: 11.5px; font-weight: 600; margin-bottom: 4px; }
.score-grid { margin: 12px 0 !important; }
.header .container { max-width: none; padding: 0; }
.report-header .container { max-width: none; }
.executive-summary h2 {
  color: var(--ink);
  border-bottom: 1px solid var(--brd);
  padding-bottom: 10px;
}
.executive-summary > h2 { margin-top: 0; }
.executive-summary h3 { color: var(--ink); }
.executive-summary p { color: var(--ink2); }
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 1px;
  background: var(--brd);
  border: 1px solid var(--brd);
  border-radius: var(--rx);
  overflow: hidden;
  margin: 16px 0;
  padding: 0 !important;
}
.metric-card {
  background: var(--sur);
  border: none !important;
  border-radius: 0;
  padding: 12px 14px !important;
  text-align: left;
  min-height: auto;
  box-shadow: none;
}
.metric-card:hover { transform: none; box-shadow: none; }
.metric-card.success { background: var(--sur); }
.metric-card.warning { background: var(--sur); }
.metric-card.danger { background: var(--sur); }
.metric-value {
  font-size: 20px;
  font-weight: 600;
  font-family: 'JetBrains Mono', monospace;
  letter-spacing: -.03em;
}
.metric-value.success { color: var(--gn); }
.metric-value.warning { color: var(--am); }
.metric-value.danger { color: var(--rd); }
.metric-label {
  font-size: 9.5px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--ink4);
}
.status-badge, .badge-success, .badge-warning, .badge-danger, .badge-info {
  font-size: 10px;
  font-weight: 500;
  padding: 2px 7px;
  border-radius: 20px;
  text-transform: none;
}
.badge-success { background: var(--gn-lt); color: var(--gn); }
.badge-warning { background: var(--am-lt); color: var(--am); }
.badge-danger { background: var(--rd-lt); color: var(--rd); }
.badge-info { background: var(--bl-lt); color: var(--bl); }
.grade-a, .grade-b { background: var(--gn-lt); color: var(--gn); }
.grade-c { background: var(--am-lt); color: var(--am); }
.grade-d, .grade-e, .grade-f { background: var(--rd-lt); color: var(--rd); }
.issue-item {
  background: var(--rd-lt);
  border-left: 3px solid var(--rd);
  padding: 11px 14px;
  margin: 8px 0;
  border-radius: var(--rl);
}
.issue-item h4 { color: var(--rd); font-size: 11.5px; font-weight: 600; }
.scorecard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1px;
  background: var(--brd);
  border: 1px solid var(--brd);
  border-radius: var(--rx);
  overflow: hidden;
}
.scorecard-card {
  background: var(--sur);
  border: none;
  border-radius: 0;
  padding: 14px;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 12px;
}
.summary-item {
  background: var(--bg);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
  padding: 10px 12px;
}
.summary-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 18px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.2;
}
.summary-label {
  font-size: 10px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: .04em;
  color: var(--ink3);
  margin-top: 4px;
}
.summary-target {
  font-size: 10px;
  color: var(--ink4);
  margin-top: 3px;
  font-family: 'JetBrains Mono', monospace;
}
.improvement { color: var(--gn); font-weight: 600; }
.regression { color: var(--rd); font-weight: 600; }
.stable { color: var(--ink3); }
.traffic-val.traffic-green { color: var(--gn); font-weight: 600; }
.traffic-val.traffic-amber { color: var(--am); font-weight: 600; }
.traffic-val.traffic-red { color: var(--rd); font-weight: 600; }
.traffic-legend {
  margin: 0 26px 12px;
  padding: 10px 14px;
  background: var(--sur);
  border: 1px solid var(--brd);
  border-radius: var(--rl);
  font-size: 11px;
  color: var(--ink3);
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
}
.traffic-legend strong { color: var(--ink2); }
.tl-dot { width: 6px; height: 6px; border-radius: 50%; display: inline-block; margin-right: 4px; }
.tl-dot-green { background: var(--gn); }
.tl-dot-amber { background: var(--am); }
.tl-dot-red { background: var(--rd); }
"""

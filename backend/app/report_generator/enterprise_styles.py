"""
Enterprise report styling aligned with enterprise_report_wireframe_v4.html (PerfSuite).
Used by JMeter, Web Vitals/Lighthouse, comparison, and A/B comparison HTML reports.
"""

ENTERPRISE_FONT_LINKS = """
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@tabler/icons-webfont@3.10.0/tabler-icons.min.css">
<link href="https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
"""


def get_enterprise_css(*, include_legacy: bool = True) -> str:
    """Return <style> block with enterprise design tokens and optional legacy class aliases."""
    legacy = _LEGACY_ALIASES_CSS if include_legacy else ""
    return f"<style>\n{_ENTERPRISE_CORE_CSS}\n{legacy}\n</style>"


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
  background: var(--bl-lt); color: var(--bl);
}
.ph-ttl { font-size: 16px; font-weight: 600; color: var(--ink); letter-spacing: -.02em; }
.ph-mt { font-size: 11.5px; color: var(--ink4); margin-top: 2px; }

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
.section h2 { border-bottom: 1px solid var(--brd); padding-bottom: 12px; }
.executive-summary {
  background: linear-gradient(135deg, var(--bl), #3b5bdb);
  color: #fff;
  padding: 18px 26px !important;
  border-radius: 0;
  margin: 0;
  border: none;
}
.executive-summary h2, .executive-summary h3, .executive-summary p { color: #fff; }
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
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.15);
  border-radius: var(--rl);
  padding: 10px;
}
.summary-value { font-family: 'JetBrains Mono', monospace; font-size: 18px; font-weight: 600; }
.summary-label { font-size: 10px; opacity: .85; }
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

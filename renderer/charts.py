"""Chart.js defaults and helpers (embedded in HTML report)."""

CHART_DEFAULTS_JS = """
const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { mode: 'index', intersect: false },
  plugins: { legend: { display: false } }
};
const TICK_STYLE = {
  font: { size: 9, family: "'DM Mono', monospace" },
  color: '#6B6860'
};
const GRID_COLOR = 'rgba(0,0,0,0.06)';
function RT_CALLBACK(v) { return v >= 1000 ? Math.round(v/1000)+'s' : v+'ms'; }
"""

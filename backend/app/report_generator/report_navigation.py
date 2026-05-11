"""
Shared fixed navigation pane for HTML performance reports (smooth scroll, print-hidden).
"""
from __future__ import annotations

import html as html_module
from typing import Iterable, List, Sequence, Tuple

NavItem = Tuple[str, str]  # (anchor_id without #, label)


def report_navigation_css() -> str:
    return """
<style id="report-nav-shared-css">
.report-page-nav {
    position: fixed;
    left: 0;
    top: 0;
    width: 220px;
    height: 100vh;
    overflow-y: auto;
    overflow-x: hidden;
    background: #0f172a;
    color: #e2e8f0;
    padding: 0.75rem 0.5rem 1.5rem;
    z-index: 1000;
    font-size: 0.82rem;
    line-height: 1.35;
    box-shadow: 2px 0 12px rgba(15, 23, 42, 0.15);
}
.report-page-nav .report-nav-title {
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #94a3b8;
    padding: 0.5rem 0.6rem 0.35rem;
    margin: 0;
}
.report-page-nav a {
    display: block;
    padding: 0.4rem 0.55rem;
    margin: 0.1rem 0;
    color: #cbd5e1;
    text-decoration: none;
    border-radius: 6px;
    border-left: 3px solid transparent;
}
.report-page-nav a:hover {
    background: rgba(255, 255, 255, 0.06);
    color: #fff;
}
.report-page-nav a:focus-visible {
    outline: 2px solid #6366f1;
    outline-offset: 1px;
}
.report-main-with-nav {
    margin-left: 220px;
    min-height: 100vh;
}
/* Compact nav on medium widths (e.g. preview iframes ~700px) — still visible */
@media (max-width: 900px) and (min-width: 600px) {
    .report-page-nav {
        width: 168px;
        padding: 0.55rem 0.35rem 1rem;
        font-size: 0.78rem;
    }
    .report-page-nav .report-nav-title {
        font-size: 0.65rem;
        padding-left: 0.45rem;
    }
    .report-main-with-nav {
        margin-left: 168px;
    }
}
/* Hide fixed nav only on narrow mobile; wide iframes/modals keep the pane */
@media (max-width: 599px) {
    .report-page-nav { display: none; }
    .report-main-with-nav { margin-left: 0; }
}
@media print {
    .report-page-nav, .no-print { display: none !important; }
    .report-main-with-nav { margin-left: 0 !important; }
}
html { scroll-behavior: smooth; }
</style>
"""


def report_navigation_js() -> str:
    return """
<script id="report-nav-shared-js">
(function() {
  document.querySelectorAll('.report-page-nav a[href^="#"]').forEach(function(a) {
    a.addEventListener('click', function(e) {
      var id = this.getAttribute('href');
      if (!id || id.length < 2) return;
      var el = document.getElementById(id.slice(1));
      if (el) {
        e.preventDefault();
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
        try { history.replaceState(null, '', id); } catch (err) {}
      }
    });
  });
})();
</script>
"""


def build_report_navigation_html(items: Sequence[NavItem], title: str = "On this page") -> str:
    """items: list of (section_id, label). section_id must match element id (no #)."""
    if not items:
        return ""
    links: List[str] = []
    for sid, label in items:
        sid_esc = html_module.escape(sid, quote=True)
        label_esc = html_module.escape(label)
        links.append(f'<a href="#{sid_esc}">{label_esc}</a>')
    inner = "\n".join(links)
    title_esc = html_module.escape(title)
    return f"""<nav class="report-page-nav no-print" aria-label="{title_esc}">
<p class="report-nav-title">{title_esc}</p>
{inner}
</nav>"""


def wrap_report_main_content(inner_html: str) -> str:
    return f'<div class="report-main-with-nav">{inner_html}</div>'

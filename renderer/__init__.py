"""HTML + chart helpers for comparison reports."""

from renderer.html_report import ComparisonHtmlReport, build_report_payload, render_comparison_html
from renderer import charts

__all__ = [
    "ComparisonHtmlReport",
    "build_report_payload",
    "render_comparison_html",
    "charts",
]

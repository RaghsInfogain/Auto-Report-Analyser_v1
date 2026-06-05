"""Lighthouse + Navigation Timing report generator v2 (standalone pipeline, separate from legacy LighthouseHTMLGenerator)."""

from app.lighthouse_nav_report_v2.pipeline import build_report_data, generate_lighthouse_nav_html_v2

__all__ = ["generate_lighthouse_nav_html_v2", "build_report_data"]

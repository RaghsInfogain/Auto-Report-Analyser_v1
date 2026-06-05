"""Jinja2 render for Lighthouse + Navigation Timing report v2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_lh_nav_report_v2(report_data: Dict[str, Any], *, has_nav_timing: bool) -> str:
    tpl_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(
        loader=FileSystemLoader(str(tpl_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    tmpl = env.get_template("lh_nav_report_v2.html.jinja2")
    rd = json.dumps(report_data, ensure_ascii=False)
    v = report_data.get("verdict_raw") or report_data.get("verdict") or {}
    pill_map = {"red": "var(--red)", "amber": "var(--amber)", "green": "var(--green)"}
    vc = v.get("verdict_color") or report_data.get("verdict", {}).get("color") or "amber"
    pill_bg = pill_map.get(vc, "var(--amber)")
    return tmpl.render(
        report_data=report_data,
        REPORT_DATA_JSON=rd,
        has_nav_timing=has_nav_timing,
        META=report_data.get("meta") or {},
        VERDICT_PILL_BG=pill_bg,
    )

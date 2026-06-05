"""Helpers to resolve Lighthouse + navigation timing upload paths for report v2."""
from __future__ import annotations

import json
from typing import Any, List, Optional, Sequence, Tuple


def is_lighthouse_json_file(file_path: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return isinstance(data, dict) and "audits" in data and "categories" in data
    except (OSError, json.JSONDecodeError, TypeError):
        return False


def is_nav_timing_json_file(file_path: str) -> bool:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list) or not data:
            return False
        row = data[0]
        if not isinstance(row, dict):
            return False
        if "pageUrl" not in row and "page_url" not in row:
            return False
        return ("playwrightFullPageLoadTime" in row) or ("firstContentFulPaint" in row) or ("timeToFirstByte" in row)
    except (OSError, json.JSONDecodeError, TypeError):
        return False


def collect_lighthouse_and_nav_from_run(files: Sequence[Any]) -> Tuple[List[str], List[str]]:
    """Return sorted Lighthouse JSON paths and list of navigation timing JSON paths."""
    lh: List[str] = []
    nav: List[str] = []

    for f in files:
        path = getattr(f, "file_path", None) or ""
        cat = getattr(f, "category", "") or ""
        if not path.endswith(".json"):
            continue
        if cat == "web_vitals":
            if is_lighthouse_json_file(path):
                lh.append(path)
            elif is_nav_timing_json_file(path):
                nav.append(path)
        elif cat == "ui_performance" and is_nav_timing_json_file(path):
            nav.append(path)

    lh = sorted(set(lh))
    nav = sorted(set(nav))
    return lh, nav

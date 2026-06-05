"""Infer dominant HTTP origin (scheme + host [:port]) from JMeter JTL/CSV files."""
from __future__ import annotations

import csv
import os
from collections import Counter
from typing import Any, Dict, List
from urllib.parse import urlparse

from app.utils.jmeter_url import normalize_jmeter_url_value


def _origin_from_raw_url(url: str) -> str:
    u = normalize_jmeter_url_value(url)
    if not u:
        return ""
    if not u.startswith(("http://", "https://")):
        u = "https://" + u.lstrip("/")
    try:
        p = urlparse(u)
        if not p.netloc:
            return ""
        if p.scheme not in ("http", "https"):
            return ""
        return f"{p.scheme}://{p.netloc}"
    except Exception:
        return ""


def dominant_base_url_from_file(path: str, max_rows: int = 60000) -> Counter:
    """Count origins from a single JMeter result file; returns Counter of origin strings."""
    ctr: Counter = Counter()
    if not path or not os.path.isfile(path):
        return ctr
    try:
        with open(path, "r", encoding="utf-8", errors="replace", newline="") as f:
            reader = csv.reader(f)
            try:
                header = next(reader)
            except StopIteration:
                return ctr
            url_idx = None
            for i, h in enumerate(header):
                hn = (h or "").strip().lower()
                if hn == "url" or hn.endswith("/url"):
                    url_idx = i
                    break
            if url_idx is None:
                for i, h in enumerate(header):
                    if "url" in (h or "").lower():
                        url_idx = i
                        break
            if url_idx is None:
                return ctr
            for n, row in enumerate(reader):
                if n >= max_rows:
                    break
                if url_idx >= len(row):
                    continue
                origin = _origin_from_raw_url(row[url_idx])
                if origin:
                    ctr[origin] += 1
    except OSError:
        return ctr
    return ctr


def dominant_base_url_for_paths(paths: List[str]) -> str:
    """Most frequent origin across one or more JMeter files (empty string if unknown)."""
    total: Counter = Counter()
    for p in paths:
        if not p:
            continue
        total.update(dominant_base_url_from_file(p))
    if not total:
        return ""
    return str(total.most_common(1)[0][0])


def dominant_origin_from_jmeter_rows(rows: List[Dict[str, Any]], max_rows: int = 25000) -> str:
    """Most frequent http(s) origin from JTL row dicts (url field), for merged multi-source slices."""
    ctr: Counter = Counter()
    for i, d in enumerate(rows):
        if i >= max_rows:
            break
        u = d.get("url")
        origin = _origin_from_raw_url(str(u) if u is not None else "")
        if origin:
            ctr[origin] += 1
    if not ctr:
        return ""
    return str(ctr.most_common(1)[0][0])

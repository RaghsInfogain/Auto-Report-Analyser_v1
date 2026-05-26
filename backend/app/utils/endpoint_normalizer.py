"""
Normalize HTTP paths so dynamic segments (numeric IDs, UUIDs, etc.) roll up
into a single endpoint for reporting, e.g.
  /api/materials/113616/info  ->  /api/materials/<ID>/info
"""
import re
from typing import Dict
from urllib.parse import urlparse

_NUMERIC_SEGMENT = re.compile(r"^\d+$")
_UUID_SEGMENT = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_OBJECT_ID_SEGMENT = re.compile(r"^[0-9a-f]{24}$", re.IGNORECASE)
_LONG_HEX_SEGMENT = re.compile(r"^[0-9a-f]{12,}$", re.IGNORECASE)


def _normalize_path_segment(segment: str) -> str:
    if not segment:
        return segment
    if _NUMERIC_SEGMENT.match(segment):
        return "<ID>"
    if _UUID_SEGMENT.match(segment) or _OBJECT_ID_SEGMENT.match(segment):
        return "<ID>"
    if _LONG_HEX_SEGMENT.match(segment):
        return "<ID>"
    return segment


def normalize_endpoint_path(path: str) -> str:
    """Replace volatile path segments with <ID> placeholders."""
    if not path or not str(path).strip():
        return path or ""

    raw = str(path).strip()
    if "://" in raw:
        parsed = urlparse(raw)
        raw = parsed.path or "/"

    if "?" in raw:
        raw = raw.split("?", 1)[0]

    leading_slash = raw.startswith("/")
    segments = [s for s in raw.split("/") if s != ""]
    if not segments:
        return raw

    normalized = "/".join(_normalize_path_segment(seg) for seg in segments)
    return f"/{normalized}" if leading_slash else normalized


def request_grouping_key(sample: Dict) -> str:
    """
    Stable key for aggregating HTTP request samples.
    Prefers normalized URL path; falls back to normalized label when it looks like a path.
    """
    url = (sample.get("url") or "").strip()
    label = (sample.get("label") or "Unknown").strip()

    if url:
        key = normalize_endpoint_path(url)
        if key and key not in ("/", ""):
            return key

    if label.startswith("/") or "/api/" in label.lower():
        return normalize_endpoint_path(label)

    return label

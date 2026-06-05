"""Lighthouse JSON ingestion — v2 standalone implementation."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class LighthouseLoader:
    """Load and clean one or more Lighthouse JSON result files."""

    AUDIT_KEYS = [
        "first-contentful-paint",
        "largest-contentful-paint",
        "total-blocking-time",
        "cumulative-layout-shift",
        "speed-index",
        "interactive",
        "server-response-time",
        "unused-javascript",
        "unused-css-rules",
        "offscreen-images",
        "total-byte-weight",
        "uses-long-cache-ttl",
        "dom-size",
        "mainthread-work-breakdown",
        "bootup-time",
        "third-party-summary",
        "render-blocking-resources",
        "uses-optimized-images",
        "uses-webp-images",
        "network-rtt",
        "critical-request-chains",
        "uses-text-compression",
    ]

    @staticmethod
    def _audit_num(audits: Dict[str, Any], key: str) -> Optional[float]:
        a = audits.get(key) or {}
        v = a.get("numericValue")
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _audit_score(audits: Dict[str, Any], key: str) -> Optional[float]:
        a = audits.get(key) or {}
        s = a.get("score")
        if s is None:
            return None
        try:
            return float(s)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _cat_score(categories: Dict[str, Any], name: str) -> int:
        c = categories.get(name) or {}
        s = c.get("score")
        if s is None:
            return 0
        try:
            return int(round(float(s) * 100))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _extract_third_party_ms(display_value: str) -> float:
        if not display_value:
            return 0.0
        m = re.search(r"([\d,]+)\s*ms", display_value)
        if not m:
            return 0.0
        try:
            return float(m.group(1).replace(",", ""))
        except ValueError:
            return 0.0

    @staticmethod
    def _extract_chain_count(display_value: str) -> int:
        if not display_value:
            return 0
        m = re.search(r"(\d+)\s+chains?\s+found", display_value, re.I)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                return 0
        m2 = re.search(r"(\d+)\s+chains?", display_value, re.I)
        if m2:
            try:
                return int(m2.group(1))
            except ValueError:
                return 0
        return 0

    def load_file(self, filepath: str) -> dict:
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(filepath)
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if not isinstance(raw, dict) or "audits" not in raw:
            raise ValueError(f"Not a Lighthouse JSON: {path}")
        audits = raw.get("audits") or {}
        categories = raw.get("categories") or {}
        url = (
            raw.get("requestedUrl")
            or raw.get("finalUrl")
            or raw.get("url")
            or path.stem
        )
        third_audit = audits.get("third-party-summary") or {}
        third_dv = str(third_audit.get("displayValue") or "")
        crit_audit = audits.get("critical-request-chains") or {}
        crit_dv = str(crit_audit.get("displayValue") or "")

        unused_js = self._audit_num(audits, "unused-javascript")
        unused_css = self._audit_num(audits, "unused-css-rules")
        offscreen = self._audit_num(audits, "offscreen-images")
        tbw = self._audit_num(audits, "total-byte-weight")
        cache_ttl = self._audit_num(audits, "uses-long-cache-ttl")
        dom_sz = self._audit_num(audits, "dom-size")
        mt = self._audit_num(audits, "mainthread-work-breakdown")
        boot = self._audit_num(audits, "bootup-time")
        rtt = self._audit_num(audits, "network-rtt")

        opportunities = {
            "unused_js_kb": (unused_js or 0) / 1024.0,
            "unused_css_kb": (unused_css or 0) / 1024.0,
            "offscreen_img_kb": (offscreen or 0) / 1024.0,
            "total_bytes_kb": (tbw or 0) / 1024.0,
            "cache_resources": int(cache_ttl or 0),
            "dom_elements": int(dom_sz or 0),
            "main_thread_ms": float(mt or 0),
            "js_execution_ms": float(boot or 0),
            "third_party_block_ms": self._extract_third_party_ms(third_dv),
            "network_rtt_ms": float(rtt or 0),
            "critical_chains": self._extract_chain_count(crit_dv),
        }

        audit_scores: Dict[str, Optional[float]] = {}
        for k in self.AUDIT_KEYS:
            audit_scores[k] = self._audit_score(audits, k)

        fcp = self._audit_num(audits, "first-contentful-paint")
        lcp = self._audit_num(audits, "largest-contentful-paint")
        tbt = self._audit_num(audits, "total-blocking-time")
        cls = self._audit_num(audits, "cumulative-layout-shift")
        si = self._audit_num(audits, "speed-index")
        tti = self._audit_num(audits, "interactive")
        ttfb = self._audit_num(audits, "server-response-time")

        return {
            "url": str(url),
            "fetch_time": str(raw.get("fetchTime") or ""),
            "lh_version": str(raw.get("lighthouseVersion") or ""),
            "scores": {
                "performance": self._cat_score(categories, "performance"),
                "accessibility": self._cat_score(categories, "accessibility"),
                "best_practices": self._cat_score(categories, "best-practices"),
                "seo": self._cat_score(categories, "seo"),
            },
            "metrics": {
                "fcp": float(fcp or 0),
                "lcp": float(lcp or 0),
                "tbt": float(tbt or 0),
                "cls": float(cls or 0),
                "si": float(si or 0),
                "tti": float(tti or 0),
                "ttfb": float(ttfb or 0),
            },
            "opportunities": opportunities,
            "audit_scores": audit_scores,
        }

    def load_directory(self, dirpath: str) -> List[dict]:
        d = Path(dirpath)
        if not d.is_dir():
            raise NotADirectoryError(dirpath)
        out: List[dict] = []
        for p in sorted(d.glob("*.json")):
            try:
                out.append(self.load_file(str(p)))
            except (ValueError, json.JSONDecodeError, OSError):
                continue
        return out

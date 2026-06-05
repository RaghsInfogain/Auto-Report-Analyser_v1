"""Optional Playwright-style navigation timing JSON loader — v2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse, urlunparse

import numpy as np


class NavTimingLoader:
    NUMERIC_FIELDS = [
        "firstContentFulPaint",
        "lastContentFulPaint",
        "totalBlockingTime",
        "cumulativeLayoutShift",
        "speedIndex",
        "performanceScore",
        "timeToFirstByte",
        "firstInputDelay",
        "timeToInteractive",
        "dnsLookupTime",
        "connectionTime",
        "totalConnectionTime",
        "requestTime",
        "serverProcessingTime",
        "requestProcessingTime",
        "domInteractiveTime",
        "domContentLoadedTime",
        "domCompleteTime",
        "pageLoaded",
        "browserTime",
        "playwrightFullPageLoadTime",
    ]

    def load(self, filepath: str | None) -> Optional[List[dict]]:
        if not filepath:
            return None
        path = Path(filepath)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return None
        cleaned: List[dict] = []
        for row in data:
            if not isinstance(row, dict):
                continue
            rec = dict(row)
            url = rec.get("pageUrl") or rec.get("page_url") or ""
            if url:
                p = urlparse(str(url))
                rec["pageUrl"] = urlunparse(
                    (p.scheme, p.netloc, p.path.rstrip("/") or "/", "", "", "")
                )
            for fld in self.NUMERIC_FIELDS:
                v = rec.get(fld)
                if v == "N/A" or v is None or v == "":
                    rec[fld] = None
                    continue
                try:
                    rec[fld] = float(v)
                except (TypeError, ValueError):
                    rec[fld] = None
            if rec.get("pageUrl"):
                cleaned.append(rec)
        return cleaned if cleaned else None

    def load_many(self, filepaths: Sequence[Optional[str]]) -> Optional[List[dict]]:
        """Merge navigation timing records from multiple JSON files (same schema as load())."""
        merged: List[dict] = []
        for fp in filepaths:
            if not fp:
                continue
            rows = self.load(str(fp))
            if rows:
                merged.extend(rows)
        return merged if merged else None

    def compute_aggregates(self, records: List[dict]) -> dict:
        if not records:
            return {}

        def col(name: str) -> np.ndarray:
            vals = [r.get(name) for r in records]
            arr = [float(x) for x in vals if x is not None]
            return np.array(arr, dtype=float) if arr else np.array([], dtype=float)

        pl = col("playwrightFullPageLoadTime")
        if pl.size == 0:
            pl = col("pageLoaded")
        fid = col("firstInputDelay")

        def pctile(a: np.ndarray, q: float) -> float:
            if a.size == 0:
                return 0.0
            return float(np.percentile(a, q))

        def mean(a: np.ndarray) -> float:
            return float(np.mean(a)) if a.size else 0.0

        avg_pl = mean(pl)
        p90_pl = pctile(pl, 90) if pl.size else 0.0
        max_pl = float(np.max(pl)) if pl.size else 0.0
        min_pl = float(np.min(pl)) if pl.size else 0.0

        def bucket_pl(v: float) -> str:
            if v < 1000:
                return "under_1s"
            if v < 2000:
                return "1s_2s"
            if v < 3000:
                return "2s_3s"
            if v < 5000:
                return "3s_5s"
            if v < 8000:
                return "5s_8s"
            if v < 12000:
                return "8s_12s"
            return "over_12s"

        dist = {
            "under_1s": 0,
            "1s_2s": 0,
            "2s_3s": 0,
            "3s_5s": 0,
            "5s_8s": 0,
            "8s_12s": 0,
            "over_12s": 0,
        }
        for v in pl:
            dist[bucket_pl(float(v))] += 1

        def fid_class(ms: float) -> str:
            if ms < 100:
                return "good"
            if ms < 300:
                return "needs_improvement"
            return "poor"

        fid_dist = {"good": 0, "needs_improvement": 0, "poor": 0}
        for v in fid:
            fid_dist[fid_class(float(v))] += 1

        dns_vals = col("dnsLookupTime")
        conn_vals = col("connectionTime")
        req_vals = col("requestTime")
        srv_vals = col("serverProcessingTime")
        dom_i = col("domInteractiveTime")
        dom_c = col("domCompleteTime")

        avg_dns = mean(dns_vals)
        avg_conn = mean(conn_vals)
        avg_req = mean(req_vals)
        avg_srv = mean(srv_vals)
        avg_dom_intr = mean(dom_i)
        avg_dom_comp = mean(dom_c)

        tcp_only = np.maximum(0, conn_vals) if conn_vals.size else np.array([])
        # phase % of avg_pl
        if avg_pl <= 0:
            phase_pct = {
                "dns": 0.0,
                "tcp": 0.0,
                "request": 0.0,
                "server": 0.0,
                "dom_interactive": 0.0,
                "dom_complete": 0.0,
                "other": 100.0,
            }
        else:
            phases = {
                "dns": avg_dns,
                "tcp": float(np.mean(tcp_only)) if tcp_only.size else avg_conn,
                "request": avg_req,
                "server": avg_srv,
                "dom_interactive": max(0, avg_dom_intr - avg_srv - avg_req) if avg_dom_intr else 0,
                "dom_complete": max(0, avg_dom_comp),
            }
            summed = sum(phases.values())
            other = max(0, avg_pl - summed)
            total = avg_pl
            phase_pct = {k: round(100 * (v / total), 1) for k, v in phases.items()}
            phase_pct["other"] = round(100 * (other / total), 1) if total else 0.0

        gaps: List[dict] = []
        for r in records:
            plv = r.get("playwrightFullPageLoadTime") or r.get("pageLoaded") or 0
            dc = r.get("domCompleteTime") or 0
            try:
                plf = float(plv) if plv is not None else 0
                dcf = float(dc) if dc is not None else 0
            except (TypeError, ValueError):
                continue
            gaps.append(
                {"url": r.get("pageUrl", ""), "gap_ms": max(0, plf - dcf), "page_load": plf, "dom_complete": dcf}
            )
        gaps.sort(key=lambda x: x["gap_ms"], reverse=True)
        gaps = gaps[:10]

        slowest = sorted(
            records,
            key=lambda r: float(r.get("playwrightFullPageLoadTime") or r.get("pageLoaded") or 0),
            reverse=True,
        )[:20]
        slowest_pages = []
        for r in slowest:
            plv = r.get("playwrightFullPageLoadTime") or r.get("pageLoaded") or 0
            slowest_pages.append({"url": r.get("pageUrl", ""), "ms": float(plv or 0)})

        def _st(avg: float, warn: float, crit: float) -> str:
            if avg <= warn:
                return "healthy"
            if avg <= crit:
                return "warn"
            return "critical"

        network_health = {
            "dns_status": _st(avg_dns, 20, 100),
            "conn_status": _st(mean(conn_vals), 50, 150),
            "srv_status": _st(avg_srv, 50, 200),
            "req_status": _st(avg_req, 400, 1000),
        }

        run_id = next((str(r.get("runId") or r.get("run_id") or "") for r in records if r.get("runId") or r.get("run_id")), "")
        host = next((str(r.get("hostName") or r.get("host_name") or "") for r in records if r.get("hostName") or r.get("host_name")), "")

        return {
            "page_count": len(records),
            "avg_pl": avg_pl,
            "p90_pl": p90_pl,
            "max_pl": max_pl,
            "min_pl": min_pl,
            "avg_fid": mean(fid),
            "p90_fid": pctile(fid, 90) if fid.size else 0.0,
            "max_fid": float(np.max(fid)) if fid.size else 0.0,
            "avg_dns": avg_dns,
            "avg_conn": mean(conn_vals),
            "avg_req": avg_req,
            "avg_srv_proc": avg_srv,
            "avg_dom_intr": avg_dom_intr,
            "avg_dom_comp": avg_dom_comp,
            "avg_browser_time": mean(col("browserTime")),
            "pl_distribution": dist,
            "fid_distribution": fid_dist,
            "phase_pct": phase_pct,
            "dom_gaps": gaps,
            "slowest_pages": slowest_pages,
            "network_health": network_health,
            "run_id": run_id,
            "host": host,
        }

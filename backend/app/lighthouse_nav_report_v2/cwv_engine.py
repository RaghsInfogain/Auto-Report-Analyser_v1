"""Core Web Vitals classification — v2."""
from __future__ import annotations

from typing import Dict, List, Any

import numpy as np


class CWVEngine:
    THRESHOLDS = {
        "fcp": {"good": 1800, "ni": 3000},
        "lcp": {"good": 2500, "ni": 4000},
        "tbt": {"good": 200, "ni": 600},
        "cls": {"good": 0.1, "ni": 0.25},
        "si": {"good": 3400, "ni": 5800},
        "tti": {"good": 3800, "ni": 7300},
        "ttfb": {"good": 800, "ni": 1800},
        "fid": {"good": 100, "ni": 300},
    }

    def classify(self, metric: str, value: float) -> str:
        t = self.THRESHOLDS.get(metric)
        if not t:
            return "ni"
        g, ni = t["good"], t["ni"]
        if value <= g:
            return "good"
        if value <= ni:
            return "ni"
        return "poor"

    def score_to_rating(self, score: int) -> str:
        if score >= 90:
            return "good"
        if score >= 50:
            return "ni"
        return "poor"

    def compute_apdex(self, values: List[float], T: float = 3000) -> float:
        if not values:
            return 0.0
        sat = sum(1 for v in values if v < T)
        tol = sum(1 for v in values if T <= v < 4 * T)
        return (sat + 0.5 * tol) / len(values)

    def aggregate_pages(self, pages: List[dict]) -> dict:
        """pages: lh_loader records with scores.performance and metrics.* in ms / unitless cls."""

        def vals(key: str) -> List[float]:
            return [float(p["metrics"].get(key) or 0) for p in pages]

        def scores() -> List[int]:
            return [int(p["scores"].get("performance") or 0) for p in pages]

        n = len(pages)
        fcp_v, lcp_v, tbt_v, cls_v = vals("fcp"), vals("lcp"), vals("tbt"), vals("cls")
        si_v, tti_v = vals("si"), vals("tti")

        def dist(metric: str, arr: List[float]) -> Dict[str, int]:
            return {
                "good": sum(1 for v in arr if self.classify(metric, v) == "good"),
                "ni": sum(1 for v in arr if self.classify(metric, v) == "ni"),
                "poor": sum(1 for v in arr if self.classify(metric, v) == "poor"),
            }

        sc = scores()
        cwv_pass = 0
        for i in range(n):
            if (
                self.classify("lcp", lcp_v[i]) == "good"
                and self.classify("tbt", tbt_v[i]) == "good"
                and self.classify("cls", cls_v[i]) == "good"
            ):
                cwv_pass += 1

        def health_from_dist(d: Dict[str, int]) -> int:
            if n == 0:
                return 0
            return int(round(100 * (d.get("good", 0) / n)))

        return {
            "avg_perf_score": int(round(sum(sc) / n)) if n else 0,
            "min_perf_score": min(sc) if sc else 0,
            "max_perf_score": max(sc) if sc else 0,
            "avg_fcp": float(np.mean(fcp_v)) if n else 0.0,
            "avg_lcp": float(np.mean(lcp_v)) if n else 0.0,
            "avg_tbt": float(np.mean(tbt_v)) if n else 0.0,
            "avg_cls": float(np.mean(cls_v)) if n else 0.0,
            "avg_si": float(np.mean(si_v)) if n else 0.0,
            "avg_tti": float(np.mean(tti_v)) if n else 0.0,
            "p90_fcp": float(np.percentile(fcp_v, 90)) if n else 0.0,
            "p90_lcp": float(np.percentile(lcp_v, 90)) if n else 0.0,
            "p90_tbt": float(np.percentile(tbt_v, 90)) if n else 0.0,
            "p90_cls": float(np.percentile(cls_v, 90)) if n else 0.0,
            "fcp_distribution": dist("fcp", fcp_v),
            "lcp_distribution": dist("lcp", lcp_v),
            "tbt_distribution": dist("tbt", tbt_v),
            "cls_distribution": dist("cls", cls_v),
            "pages_passing_all_cwv": cwv_pass,
            "total_pages": n,
            "perf_score_distribution": sorted(sc),
            "loading_health_score": int(
                round((health_from_dist(dist("fcp", fcp_v)) + health_from_dist(dist("lcp", lcp_v))) / 2)
            ),
            "interactivity_health_score": health_from_dist(dist("tbt", tbt_v)),
            "stability_health_score": health_from_dist(dist("cls", cls_v)),
        }

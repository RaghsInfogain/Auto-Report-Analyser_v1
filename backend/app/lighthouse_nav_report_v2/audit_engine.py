"""Lighthouse audit opportunities + RCA — v2."""
from __future__ import annotations

from typing import Any, Dict, List


class AuditEngine:
    def extract_opportunities(self, pages: List[dict]) -> dict:
        n = len(pages) or 1

        unused_js_pages = [p for p in pages if float(p["opportunities"].get("unused_js_kb") or 0) > 10]

        def worst_pages(field: str, label_key: str = "url", top: int = 5) -> List[dict]:
            ranked = sorted(
                pages,
                key=lambda p: float(p["opportunities"].get(field) or 0),
                reverse=True,
            )
            return [{label_key: p["url"], field: float(p["opportunities"].get(field) or 0)} for p in ranked[:top]]

        ujs = [float(p["opportunities"].get("unused_js_kb") or 0) for p in pages]
        ucs = [float(p["opportunities"].get("unused_css_kb") or 0) for p in pages]
        off = [float(p["opportunities"].get("offscreen_img_kb") or 0) for p in pages]
        cache_vals = [int(p["opportunities"].get("cache_resources") or 0) for p in pages]
        dom_e = [int(p["opportunities"].get("dom_elements") or 0) for p in pages]
        mt = [float(p["opportunities"].get("main_thread_ms") or 0) for p in pages]
        boot = [float(p["opportunities"].get("js_execution_ms") or 0) for p in pages]
        tp = [float(p["opportunities"].get("third_party_block_ms") or 0) for p in pages]
        chains = [int(p["opportunities"].get("critical_chains") or 0) for p in pages]
        rtt = [float(p["opportunities"].get("network_rtt_ms") or 0) for p in pages]

        unused_css_pages = [p for p in pages if float(p["opportunities"].get("unused_css_kb") or 0) > 5]
        off_pages = [p for p in pages if float(p["opportunities"].get("offscreen_img_kb") or 0) > 0]
        cache_fail = [p for p in pages if int(p["opportunities"].get("cache_resources") or 0) > 0]
        dom_big = [p for p in pages if int(p["opportunities"].get("dom_elements") or 0) > 800]
        tp_affected = [p for p in pages if float(p["opportunities"].get("third_party_block_ms") or 0) > 200]

        depth_pages = [{"url": p["url"], "depth": int(p["opportunities"].get("critical_chains") or 0)} for p in pages]

        return {
            "unused_js": {
                "pages_failing": len(unused_js_pages),
                "avg_savings_kb": sum(ujs) / n,
                "max_savings_kb": max(ujs) if ujs else 0.0,
                "worst_pages": worst_pages("unused_js_kb", "url", 5),
            },
            "unused_css": {
                "pages_failing": len(unused_css_pages),
                "avg_savings_kb": sum(ucs) / n,
                "max_savings_kb": max(ucs) if ucs else 0.0,
                "worst_pages": worst_pages("unused_css_kb", "url", 5),
            },
            "offscreen_images": {
                "pages_failing": len(off_pages),
                "avg_savings_kb": sum(off) / n,
            },
            "cache_policy": {
                "pages_failing": len(cache_fail),
                "avg_resources_uncached": sum(cache_vals) / n,
            },
            "dom_size": {
                "pages_failing": len(dom_big),
                "avg_elements": sum(dom_e) / n,
                "max_elements": max(dom_e) if dom_e else 0,
                "worst_pages": [
                    {"url": p["url"], "elements": int(p["opportunities"].get("dom_elements") or 0)}
                    for p in sorted(pages, key=lambda x: int(x["opportunities"].get("dom_elements") or 0), reverse=True)[:5]
                ],
            },
            "main_thread": {
                "avg_ms": sum(mt) / n,
                "max_ms": max(mt) if mt else 0.0,
                "worst_pages": [
                    {"url": p["url"], "ms": float(p["opportunities"].get("main_thread_ms") or 0)}
                    for p in sorted(pages, key=lambda x: float(x["opportunities"].get("main_thread_ms") or 0), reverse=True)[:5]
                ],
            },
            "js_execution": {"avg_ms": sum(boot) / n, "max_ms": max(boot) if boot else 0.0},
            "third_party": {
                "avg_block_ms": sum(tp) / n,
                "max_block_ms": max(tp) if tp else 0.0,
                "pages_affected": len(tp_affected),
                "worst_pages": [
                    {"url": p["url"], "ms": float(p["opportunities"].get("third_party_block_ms") or 0)}
                    for p in sorted(pages, key=lambda x: float(x["opportunities"].get("third_party_block_ms") or 0), reverse=True)[:5]
                ],
            },
            "critical_chains": {
                "max_depth": max(chains) if chains else 0,
                "avg_depth": sum(chains) / n,
                "worst_pages": sorted(depth_pages, key=lambda x: x["depth"], reverse=True)[:5],
            },
            "network_rtt": {"avg_ms": sum(rtt) / n, "max_ms": max(rtt) if rtt else 0.0},
        }

    def generate_rca(self, opportunities: dict, cwv: dict) -> List[dict]:
        rcas: List[dict] = []
        total = max(1, cwv.get("total_pages") or 1)
        avg_tbt = cwv.get("avg_tbt") or 0
        ujs = opportunities.get("unused_js") or {}
        tp = opportunities.get("third_party") or {}
        chains = opportunities.get("critical_chains") or {}
        cls_d = cwv.get("cls_distribution") or {}
        cache = opportunities.get("cache_policy") or {}
        off = opportunities.get("offscreen_images") or {}
        avg_lcp = cwv.get("avg_lcp") or 0
        ttfb_avg = 0.0  # filled by caller via pages if needed; use lcp hint

        def add(cid: str, sev: str, title: str, conf: int, body: str, ev: str, badge: str):
            rcas.append(
                {
                    "id": cid,
                    "severity": sev,
                    "title": title,
                    "confidence": conf,
                    "body": body,
                    "evidence": ev,
                    "badge_text": badge,
                }
            )

        if float(ujs.get("avg_savings_kb") or 0) > 200 and avg_tbt > 2000:
            add(
                "RCA-01",
                "sev1",
                "Monolithic JavaScript and long main-thread tasks",
                88,
                "Unused JavaScript budgets remain elevated while Total Blocking Time sits far above the Good threshold. "
                "Large bundles delay hydration and keep the main thread busy during critical interaction windows.",
                f"Avg unused JS ≈ {ujs.get('avg_savings_kb', 0):.0f} KiB per page; avg TBT ≈ {avg_tbt:.0f} ms.",
                "SEV-1",
            )

        if float(tp.get("avg_block_ms") or 0) > 1000:
            add(
                "RCA-02",
                "sev1",
                "Third-party scripts blocking interactivity",
                85,
                "Tag managers, chat widgets, and analytics are consuming substantial main-thread time. "
                "This pattern typically inflates TBT and delays Time to Interactive.",
                f"Avg third-party blocking ≈ {tp.get('avg_block_ms', 0):.0f} ms; pages affected ≈ {tp.get('pages_affected', 0)}.",
                "SEV-1",
            )

        if int(chains.get("max_depth") or 0) > 10:
            add(
                "RCA-03",
                "sev2",
                "Deep critical request chains delaying LCP",
                72,
                "Sequential loading along long chains extends the critical path. "
                "Render-blocking resources and late-discovered hero assets compound LCP.",
                f"Max critical-chain depth ≈ {chains.get('max_depth', 0)}.",
                "SEV-2",
            )

        if int(cls_d.get("poor") or 0) > 0:
            add(
                "RCA-04",
                "sev2",
                "Layout instability (CLS) on key templates",
                70,
                "Cumulative Layout Shift failures often trace to images without dimensions, ads, or late-injected banners. "
                "User trust and conversion elements shift after interaction.",
                f"Pages in Poor CLS bucket: {cls_d.get('poor', 0)} of {total}.",
                "SEV-2",
            )

        if int(cache.get("pages_failing") or 0) / total > 0.5 and int(cache.get("pages_failing") or 0) > 0:
            add(
                "RCA-05",
                "sev3",
                "Weak cache policy on static assets",
                60,
                "Short TTLs increase repeat-visit cost and amplify variance on LCP/FCP. "
                "CDN and origin cache headers likely need alignment.",
                f"Pages with cache findings: {cache.get('pages_failing', 0)} ({100 * cache.get('pages_failing', 0) / total:.0f}%).",
                "SEV-3",
            )

        if int(off.get("pages_failing") or 0) / total > 0.5:
            add(
                "RCA-06",
                "sev3",
                "Off-screen images not deferred",
                58,
                "Downloaded bytes compete with hero content on the critical path. Lazy-loading and responsive sources reduce contention.",
                f"Pages with off-screen image opportunities: {off.get('pages_failing', 0)}.",
                "SEV-3",
            )

        if avg_lcp > 800 and cwv.get("lcp_distribution", {}).get("good", 0) == 0:
            add(
                "RCA-07",
                "sev2",
                "Server / document response limiting early paint",
                65,
                "When LCP is dominated by slow document or API responses, front-end optimisations alone rarely suffice. "
                "Consider edge caching, compression, and backend latency reductions.",
                f"Avg LCP ≈ {avg_lcp:.0f} ms with zero pages in the Good bucket.",
                "SEV-2",
            )

        sev_order = {"sev1": 1, "sev2": 2, "sev3": 3}
        rcas.sort(key=lambda r: (-r["confidence"], sev_order.get(r["severity"], 9)))
        for i, r in enumerate(rcas, 1):
            r["id"] = f"RCA-{i:02d}"
        return rcas

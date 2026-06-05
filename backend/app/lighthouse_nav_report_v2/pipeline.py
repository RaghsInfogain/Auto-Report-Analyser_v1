"""Orchestrate v2 Lighthouse + optional navigation timing → REPORT_DATA + HTML."""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.analyzers.lighthouse_analyzer import LighthouseAnalyzer
from app.lighthouse_nav_report_v2.audit_engine import AuditEngine
from app.lighthouse_nav_report_v2.cwv_engine import CWVEngine
from app.lighthouse_nav_report_v2.html_report import render_lh_nav_report_v2
from app.lighthouse_nav_report_v2.lh_loader import LighthouseLoader
from app.lighthouse_nav_report_v2.nav_loader import NavTimingLoader
from app.lighthouse_nav_report_v2.verdict_engine import VerdictEngine


def _norm_url(u: str) -> str:
    u = (u or "").strip().rstrip("/")
    return u


def _ring_class(score: int) -> str:
    if score >= 80:
        return "g"
    if score >= 50:
        return "a"
    return "r"


def _build_scorecard_rows(
    lh_pages: List[dict], nav_records: Optional[List[dict]], cwv: CWVEngine
) -> List[dict]:
    nav_map = {}
    if nav_records:
        for r in nav_records:
            nav_map[_norm_url(str(r.get("pageUrl") or ""))] = r
    rows = []
    for p in lh_pages:
        url = p["url"]
        m = p["metrics"]
        perf = int(p["scores"]["performance"])
        nav = nav_map.get(_norm_url(url))

        def st(metric: str, val: float) -> str:
            return cwv.classify(metric, val)

        pl = None
        if nav:
            pl = nav.get("playwrightFullPageLoadTime") or nav.get("pageLoaded")
            try:
                pl = float(pl) if pl is not None else None
            except (TypeError, ValueError):
                pl = None

        rows.append(
            {
                "url": url,
                "perf": perf,
                "fcp": m["fcp"],
                "lcp": m["lcp"],
                "tbt": m["tbt"],
                "cls": m["cls"],
                "si": m["si"],
                "page_load": pl,
                "loading": st("lcp", m["lcp"]),
                "tbt_status": st("tbt", m["tbt"]),
                "cls_status": st("cls", m["cls"]),
            }
        )
    rows.sort(key=lambda r: r["perf"])
    return rows


def _charts(lh_pages: List[dict], cwv_agg: dict, nav_agg: Optional[dict], nav_pages: Optional[List[dict]]) -> dict:
    scores = [int(p["scores"]["performance"]) for p in lh_pages]
    labels = [str(i + 1) for i in range(len(scores))]
    colors = []
    for s in scores:
        if s < 50:
            colors.append("#C0392B")
        elif s < 90:
            colors.append("#B45309")
        else:
            colors.append("#2D6A2D")

    lcp_sorted = sorted(lh_pages, key=lambda p: p["metrics"]["lcp"], reverse=True)
    lcp_labels = [(p["url"][:42] + "…") if len(p["url"]) > 42 else p["url"] for p in lcp_sorted]
    lcp_vals = [p["metrics"]["lcp"] for p in lcp_sorted]
    lcp_bar_colors = ["#C0392B" if v >= 10000 else "#C06A2B" if v >= 4000 else "#B45309" for v in lcp_vals]

    tbt_sorted = sorted(lh_pages, key=lambda p: p["metrics"]["tbt"], reverse=True)
    tbt_labels = [(p["url"][:42] + "…") if len(p["url"]) > 42 else p["url"] for p in tbt_sorted]
    tbt_vals = [p["metrics"]["tbt"] for p in tbt_sorted]

    cls_sorted = sorted(lh_pages, key=lambda p: p["metrics"]["cls"], reverse=True)
    cls_labels = [(p["url"][:40] + "…") if len(p["url"]) > 40 else p["url"] for p in cls_sorted]
    cls_vals = [p["metrics"]["cls"] for p in cls_sorted]
    cls_colors = [
        "#2D6A2D" if v < 0.1 else "#B45309" if v < 0.25 else "#C0392B" for v in cls_vals
    ]

    fcp_d = cwv_agg.get("fcp_distribution") or {}
    cls_d = cwv_agg.get("cls_distribution") or {}

    nav_charts = {}
    if nav_agg and nav_pages:
        pl_d = nav_agg.get("pl_distribution") or {}
        nav_charts["pl_dist"] = {
            "labels": ["<1s", "1–2s", "2–3s", "3–5s", "5–8s", "8–12s", ">12s"],
            "keys": ["under_1s", "1s_2s", "2s_3s", "3s_5s", "5s_8s", "8s_12s", "over_12s"],
            "data": [pl_d.get(k, 0) for k in ["under_1s", "1s_2s", "2s_3s", "3s_5s", "5s_8s", "8s_12s", "over_12s"]],
            "colors": ["#2D6A2D", "#A3D17E", "#F5D78A", "#B45309", "#C06A2B", "#C0392B", "#7B241C"],
        }
        phase = nav_agg.get("phase_pct") or {}
        nav_charts["phase_donut"] = {
            "labels": ["DNS", "TCP", "Request", "Server", "DOM int.", "DOM comp.", "Other"],
            "data": [
                phase.get("dns", 0),
                phase.get("tcp", 0),
                phase.get("request", 0),
                phase.get("server", 0),
                phase.get("dom_interactive", 0),
                phase.get("dom_complete", 0),
                phase.get("other", 0),
            ],
        }
        top30 = sorted(
            nav_pages,
            key=lambda r: float(r.get("playwrightFullPageLoadTime") or r.get("pageLoaded") or 0),
            reverse=True,
        )[:30]
        nav_charts["pl_per_page"] = {
            "labels": [
                (str(r.get("pageUrl") or "")[:38] + "…")
                if len(str(r.get("pageUrl") or "")) > 38
                else str(r.get("pageUrl") or "")
                for r in top30
            ],
            "data": [float(r.get("playwrightFullPageLoadTime") or r.get("pageLoaded") or 0) for r in top30],
        }
        fd = nav_agg.get("fid_distribution") or {}
        nav_charts["fid_dist"] = {
            "labels": ["Good", "NI", "Poor"],
            "data": [fd.get("good", 0), fd.get("needs_improvement", 0), fd.get("poor", 0)],
        }
        worst_fid = sorted(
            nav_pages,
            key=lambda r: float(r.get("firstInputDelay") or 0),
            reverse=True,
        )[:20]
        nav_charts["waterfall"] = {
            "labels": ["DNS", "TCP", "Request", "Server", "DOM interactive", "DOM complete"],
            "data": [
                float(nav_agg.get("avg_dns") or 0),
                float(nav_agg.get("avg_conn") or 0),
                float(nav_agg.get("avg_req") or 0),
                float(nav_agg.get("avg_srv_proc") or 0),
                float(nav_agg.get("avg_dom_intr") or 0),
                float(nav_agg.get("avg_dom_comp") or 0),
            ],
        }
        nav_charts["fid_pages"] = {
            "labels": [
                ((u := str(r.get("pageUrl") or ""))[:35] + ("…" if len(u) > 35 else ""))
                for r in worst_fid
            ],
            "data": [float(r.get("firstInputDelay") or 0) for r in worst_fid],
        }
        gaps = nav_agg.get("dom_gaps") or []
        nav_charts["dom_gap"] = {
            "labels": [
                ((g.get("url") or "")[:32] + ("…" if len(g.get("url") or "") > 32 else ""))
                for g in gaps[:10]
            ],
            "dom_complete": [float(g.get("dom_complete") or 0) for g in gaps[:10]],
            "gap": [float(g.get("gap_ms") or 0) for g in gaps[:10]],
        }

    return {
        "perf_dist": {"labels": labels, "data": scores, "colors": colors},
        "lcp_pages": {"labels": lcp_labels, "data": lcp_vals, "colors": lcp_bar_colors},
        "tbt_pages": {"labels": tbt_labels, "data": tbt_vals},
        "cls_pages": {"labels": cls_labels, "data": cls_vals, "colors": cls_colors},
        "fcp_h": {"labels": ["Good", "NI", "Poor"], "data": [fcp_d.get("good", 0), fcp_d.get("ni", 0), fcp_d.get("poor", 0)]},
        "cls_h": {"labels": ["Good", "NI", "Poor"], "data": [cls_d.get("good", 0), cls_d.get("ni", 0), cls_d.get("poor", 0)]},
        "nav": nav_charts,
    }


def _plan_data(cwv_agg: dict, verdict: dict) -> dict:
    avg = int(cwv_agg.get("avg_perf_score") or 0)
    rows: List[dict] = [
        {
            "rec": "Third-party audit & deferral",
            "phase": "1",
            "effort": "M",
            "lcp": "Medium",
            "tbt": "High",
            "cls": "Low",
            "gain": "+8–12",
            "pri": "P0",
        },
        {
            "rec": "Image optimisation & LCP hero prioritisation",
            "phase": "1",
            "effort": "M",
            "lcp": "High",
            "tbt": "Low",
            "cls": "Med",
            "gain": "+6–10",
            "pri": "P0",
        },
        {
            "rec": "Route-level code splitting",
            "phase": "2",
            "effort": "H",
            "lcp": "Med",
            "tbt": "High",
            "cls": "Low",
            "gain": "+10–18",
            "pri": "P1",
        },
        {
            "rec": "Cache/CDN hardening",
            "phase": "2",
            "effort": "L",
            "lcp": "Med",
            "tbt": "Low",
            "cls": "—",
            "gain": "+4–8",
            "pri": "P1",
        },
        {
            "rec": "CLS guardrails (dimensions, ads slot stability)",
            "phase": "3",
            "effort": "M",
            "lcp": "Low",
            "tbt": "Low",
            "cls": "High",
            "gain": "+5–9",
            "pri": "P2",
        },
    ]
    by_phase: Dict[str, List[str]] = {"1": [], "2": [], "3": []}
    for row in rows:
        ph = str(row.get("phase") or "")
        line = f"{row['rec']} — {row['pri']}, effort {row['effort']} (est. score {row['gain']})"
        if ph in by_phase:
            by_phase[ph].append(line)

    timeline: List[dict] = [
        {
            "time": "Phase 1 · Weeks 1–4",
            "title": "Stabilise critical path",
            "body": "Third-party audit and deferral, image and LCP hero fixes, cache header alignment — aim for measurable LCP and TBT reduction on worst URLs before wider rollout.",
            "item_class": "tl-item p1",
            "actions": by_phase["1"]
            + [
                "Measure before/after on the top five worst LCP URLs in synthetic runs.",
                "Align TTL and compression headers with CDN defaults in the release checklist.",
                "Remove or async non-critical tags blocking the critical path.",
            ],
        },
        {
            "time": "Phase 2 · Weeks 4–12",
            "title": "Architecture and delivery",
            "body": "Route-level code splitting, preload discipline, DOM budgets, CDN hardening — fold regressions into CI budgets and weekly synthetic cadence.",
            "item_class": "tl-item",
            "actions": by_phase["2"]
            + [
                "Introduce bundle-budget checks in CI for key routes.",
                "Preload only LCP-critical assets; audit fetchpriority usage on heroes.",
                "Reduce main-thread boot cost on entry chunks tied to worst TBT pages.",
            ],
        },
        {
            "time": "Phase 3 · Weeks 12–24",
            "title": "Harden and govern",
            "body": "CLS guardrails, marketing slot stability, edge caching for document/API paths, production gates tied to CWV and performance score SLAs.",
            "item_class": "tl-item p3",
            "actions": by_phase["3"]
            + [
                "Enforce media dimensions and reserved slots in the design system.",
                "Add staging review for ad/inject slots that affect above-the-fold layout.",
                "Gate releases on performance score and CWV thresholds documented in this report.",
            ],
        },
    ]

    return {
        "avg": avg,
        "p1_target": min(100, avg + 15),
        "p2_target": min(100, avg + 35),
        "p3_target": min(100, avg + 50),
        "rows": rows,
        "timeline": timeline,
    }


def _issues_identified_from_lh_pages(lh_pages: List[dict]) -> List[dict]:
    """Site-average metrics + per-page rows in the same units as LighthouseAnalyzer._identify_issues."""
    page_data: List[dict] = []
    for p in lh_pages:
        m = p.get("metrics") or {}
        url = str(p.get("url") or "")
        page_data.append(
            {
                "page_title": url[:200] if url else "Unknown",
                "lcp": float(m.get("lcp") or 0) / 1000.0,
                "fcp": float(m.get("fcp") or 0) / 1000.0,
                "tbt": float(m.get("tbt") or 0),
                "speed_index": float(m.get("si") or 0) / 1000.0,
                "cls": float(m.get("cls") or 0),
            }
        )
    n = max(1, len(page_data))
    avg_metrics = {
        "lcp": sum(x["lcp"] for x in page_data) / n,
        "fcp": sum(x["fcp"] for x in page_data) / n,
        "tbt": sum(x["tbt"] for x in page_data) / n,
        "speed_index": sum(x["speed_index"] for x in page_data) / n,
        "cls": sum(x["cls"] for x in page_data) / n,
    }
    return LighthouseAnalyzer._identify_issues(avg_metrics, page_data)


def _verdict_card_class(verdict: str) -> str:
    v = verdict.upper().replace("-", "_")
    if v == "GO":
        return "go"
    if "CONDITIONAL" in v:
        return "cond"
    return "nogo"


def _build_spec_payload(
    pages: List[dict],
    cwv_agg: dict,
    opps: dict,
    rca: List[dict],
    nav_agg: Optional[dict],
    nav_pages: Optional[List[dict]],
    verdict_raw: dict,
    exec_paragraph: str,
    cw_engine: CWVEngine,
    sla: dict,
) -> dict:
    """Template-only structured copy: zones, extended tables, metric cards."""
    n = max(1, len(pages))
    ld = cwv_agg.get("lcp_distribution") or {}
    td = cwv_agg.get("tbt_distribution") or {}
    cd = cwv_agg.get("cls_distribution") or {}
    fd = cwv_agg.get("fcp_distribution") or {}

    critical_lcp = [p for p in pages if float(p["metrics"].get("lcp") or 0) >= 10000]
    high_lcp = [p for p in pages if 4000 <= float(p["metrics"].get("lcp") or 0) < 10000]
    deep_chains = [p for p in pages if int(p["opportunities"].get("critical_chains") or 0) >= 10]

    avg_lcp = float(cwv_agg.get("avg_lcp") or 0)
    avg_tbt = float(cwv_agg.get("avg_tbt") or 0)
    avg_cls = float(cwv_agg.get("avg_cls") or 0)

    lcp_ratio = round(avg_lcp / 2500, 2) if avg_lcp else 0
    tbt_ratio = round(avg_tbt / 200, 2) if avg_tbt else 0
    fcp_ratio = round(float(cwv_agg.get("avg_fcp") or 0) / 1800, 2) if cwv_agg.get("avg_fcp") else 0

    top_rca_titles = [r.get("title", "") for r in (rca or [])[:2]]

    narrative = exec_paragraph
    if top_rca_titles:
        narrative += " Dominant themes: " + "; ".join(top_rca_titles) + "."

    loading_zones = []
    if critical_lcp:
        lines = ", ".join(
            f"{p['url'][:48]} ({float(p['metrics']['lcp']):.0f} ms)" for p in critical_lcp[:8]
        )
        loading_zones.append(
            {
                "cls": "r",
                "title": "Critical: LCP ≥ 10,000 ms",
                "body": f"The following pages exceed 10s LCP: {lines}.",
            }
        )
    elif high_lcp:
        loading_zones.append(
            {
                "cls": "a",
                "title": "High: LCP in 4–10 s range",
                "body": f"{len(high_lcp)} page(s) need hero and critical-path work before promotion.",
            }
        )
    if deep_chains:
        loading_zones.append(
            {
                "cls": "r",
                "title": "Critical: Deep critical request chains",
                "body": f"{len(deep_chains)} page(s) show chain depth ≥10 — sequencing and preload fixes required.",
            }
        )
    ujs = opps.get("unused_js") or {}
    if float(ujs.get("avg_savings_kb") or 0) > 50:
        loading_zones.append(
            {
                "cls": "a",
                "title": "High: Unused JavaScript",
                "body": f"Avg estimated unused JS ≈ {float(ujs.get('avg_savings_kb') or 0):.0f} KiB per page.",
            }
        )
    cache = opps.get("cache_policy") or {}
    if int(cache.get("pages_failing") or 0) > 0:
        loading_zones.append(
            {
                "cls": "a",
                "title": "High: Cache TTL opportunities",
                "body": f"{cache.get('pages_failing', 0)} page(s) flag long-cache / TTL improvements.",
            }
        )
    off = opps.get("offscreen_images") or {}
    if int(off.get("pages_failing") or 0) > n / 2:
        loading_zones.append(
            {
                "cls": "a",
                "title": "High: Off-screen images",
                "body": "Majority of pages still ship off-screen image weight on the critical path.",
            }
        )

    tp = opps.get("third_party") or {}
    dom_big = opps.get("dom_size") or {}
    mt = opps.get("main_thread") or {}
    rtt = opps.get("network_rtt") or {}

    inter_zones = []
    if float(tp.get("avg_block_ms") or 0) > 500:
        inter_zones.append(
            {
                "cls": "r",
                "title": "Third-party main-thread cost",
                "body": f"Avg blocking ≈ {float(tp.get('avg_block_ms') or 0):.0f} ms; worst pages include "
                + ", ".join((w.get("url", "")[:40] for w in (tp.get("worst_pages") or [])[:3])),
            }
        )
    big_dom = dom_big.get("worst_pages") or []
    big_dom_800 = [w for w in big_dom if int(w.get("elements") or 0) > 800]
    if big_dom_800:
        inter_zones.append(
            {
                "cls": "r",
                "title": "Excessive DOM size",
                "body": "Templates exceed 800 DOM nodes — review component density and list virtualisation.",
            }
        )
    inter_zones.append(
        {
            "cls": "a",
            "title": "JS execution & main-thread work",
            "body": f"Avg main-thread work ≈ {float(mt.get('avg_ms') or 0):.0f} ms; route-level splitting reduces TBT.",
        }
    )
    inter_zones.append(
        {
            "cls": "a",
            "title": "Network RTT compounding",
            "body": f"Avg RTT ≈ {float(rtt.get('avg_ms') or 0):.0f} ms — edge placement and HTTP/2 concurrency reduce chain latency.",
        }
    )

    poor_cls_pages = sorted(
        [p for p in pages if float(p["metrics"].get("cls") or 0) >= 0.25],
        key=lambda p: float(p["metrics"]["cls"]),
        reverse=True,
    )
    ni_cls_pages = sorted(
        [p for p in pages if 0.1 <= float(p["metrics"].get("cls") or 0) < 0.25],
        key=lambda p: float(p["metrics"]["cls"]),
        reverse=True,
    )
    stability_zones = []
    for p in poor_cls_pages[:6]:
        stability_zones.append(
            {
                "cls": "r",
                "badge": f"CLS {float(p['metrics']['cls']):.3f}",
                "title": p["url"][:72],
                "body": "Poor CLS impacts trust and conversion on above-the-fold CTAs; stabilise layout slots and media dimensions.",
            }
        )
    for p in ni_cls_pages[:4]:
        stability_zones.append(
            {
                "cls": "a",
                "badge": f"CLS {float(p['metrics']['cls']):.3f}",
                "title": p["url"][:72],
                "body": "Needs improvement — monitor font and ad slot behaviour under real user conditions.",
            }
        )

    cls_rows = len(poor_cls_pages) + len(ni_cls_pages)
    cls_causes = [
        {
            "cause": "Images without dimensions",
            "detail": f"Affects {cls_rows} template(s) with CLS NI/Poor; enforce width/height and aspect-ratio in design system.",
        },
        {
            "cause": "Late-injected ads / banners",
            "detail": "Reserve slot height early; use skeleton placeholders for marketing injec…",
        },
        {
            "cause": "Web font loading",
            "detail": "font-display: swap/optional and subset fonts to reduce layout shift on swap.",
        },
        {
            "cause": "Dynamic content injection",
            "detail": "Client-side inserts after LCP frequently bump CLS — batch DOM updates.",
        },
    ]

    lcp_header = "r" if cw_engine.classify("lcp", avg_lcp) == "poor" else "a"
    tbt_header = "r" if cw_engine.classify("tbt", avg_tbt) == "poor" else "a"
    cls_header = "a" if cw_engine.classify("cls", avg_cls) == "ni" else ("r" if cw_engine.classify("cls", avg_cls) == "poor" else "g")

    cwv_cards = [
        {
            "name": "LCP",
            "header": lcp_header,
            "value": f"{avg_lcp:.0f} ms",
            "sub": f"avg · target <2,500 ms · {lcp_ratio}× Good threshold" if lcp_ratio else "avg · target <2,500 ms",
            "desc": "Largest Contentful Paint measures perceived load speed of main content.",
            "badges": f"Poor: {ld.get('poor', 0)} | NI: {ld.get('ni', 0)} | Good: {ld.get('good', 0)}",
        },
        {
            "name": "TBT",
            "header": tbt_header,
            "value": f"{avg_tbt:.0f} ms",
            "sub": f"avg · target <200 ms · {tbt_ratio}× Good threshold" if tbt_ratio else "avg · target <200 ms",
            "desc": "Total Blocking Time captures main-thread blockage before interactivity.",
            "badges": f"Poor: {td.get('poor', 0)} | NI: {td.get('ni', 0)} | Good: {td.get('good', 0)}",
        },
        {
            "name": "CLS",
            "header": cls_header,
            "value": f"{avg_cls:.3f}",
            "sub": "avg · target <0.1 · stability bucket mix below",
            "desc": "Cumulative Layout Shift reflects visual stability during lifecycle.",
            "badges": f"Poor: {cd.get('poor', 0)} | NI: {cd.get('ni', 0)} | Good: {cd.get('good', 0)}",
        },
    ]

    cwv_threshold_rows = [
        {
            "metric": "FCP",
            "good": "≤1,800 ms",
            "ni": "1.8–3.0 s",
            "poor": ">3.0 s",
            "avg": f"{float(cwv_agg.get('avg_fcp') or 0):.0f} ms",
            "pg": fd.get("good", 0),
            "pn": fd.get("ni", 0),
            "pp": fd.get("poor", 0),
            "gap": "—",
        },
        {
            "metric": "LCP",
            "good": "≤2,500 ms",
            "ni": "2.5–4.0 s",
            "poor": ">4.0 s",
            "avg": f"{avg_lcp:.0f} ms",
            "pg": ld.get("good", 0),
            "pn": ld.get("ni", 0),
            "pp": ld.get("poor", 0),
            "gap": f"{max(0, int(avg_lcp - 2500))} ms" if avg_lcp > 2500 else "At Good",
        },
        {
            "metric": "TBT",
            "good": "≤200 ms",
            "ni": "200–600 ms",
            "poor": ">600 ms",
            "avg": f"{avg_tbt:.0f} ms",
            "pg": td.get("good", 0),
            "pn": td.get("ni", 0),
            "pp": td.get("poor", 0),
            "gap": f"{max(0, int(avg_tbt - 200))} ms" if avg_tbt > 200 else "At Good",
        },
        {
            "metric": "CLS",
            "good": "≤0.1",
            "ni": "0.1–0.25",
            "poor": ">0.25",
            "avg": f"{avg_cls:.3f}",
            "pg": cd.get("good", 0),
            "pn": cd.get("ni", 0),
            "pp": cd.get("poor", 0),
            "gap": f"{max(0, avg_cls - 0.1):.3f}" if avg_cls > 0.1 else "At Good",
        },
        {
            "metric": "Speed Index",
            "good": "≤3,400 ms",
            "ni": "3.4–5.8 s",
            "poor": ">5.8 s",
            "avg": f"{float(cwv_agg.get('avg_si') or 0):.0f} ms",
            "pg": "—",
            "pn": "—",
            "pp": "—",
            "gap": "—",
        },
        {
            "metric": "TTI (interactive)",
            "good": "≤3,800 ms",
            "ni": "3.8–7.3 s",
            "poor": ">7.3 s",
            "avg": f"{float(cwv_agg.get('avg_tti') or 0):.0f} ms",
            "pg": "—",
            "pn": "—",
            "pp": "—",
            "gap": "—",
        },
    ]

    nav_kpi12 = []
    if nav_agg:
        totaln = max(1, int(nav_agg.get("page_count") or 1))
        pl_d = nav_agg.get("pl_distribution") or {}
        under2 = sum(pl_d.get(k, 0) for k in ("under_1s", "1s_2s"))
        over5 = sum(pl_d.get(k, 0) for k in ("3s_5s", "5s_8s", "8s_12s", "over_12s"))
        fid_g = (nav_agg.get("fid_distribution") or {}).get("good", 0)
        fid_ni = (nav_agg.get("fid_distribution") or {}).get("needs_improvement", 0)
        fid_p = (nav_agg.get("fid_distribution") or {}).get("poor", 0)
        avg_pl = float(nav_agg.get("avg_pl") or 0)
        avg_dom_c = float(nav_agg.get("avg_dom_comp") or 0)
        pct_dom = round(100 * avg_dom_c / avg_pl, 1) if avg_pl > 0 else 0
        slowest_u = ""
        if nav_agg.get("slowest_pages"):
            slowest_u = (nav_agg["slowest_pages"][0].get("url") or "")[:56]
        fastest_u = ""
        if nav_pages:
            fast = min(
                nav_pages,
                key=lambda r: float(r.get("playwrightFullPageLoadTime") or r.get("pageLoaded") or 1e12),
            )
            fastest_u = (fast.get("pageUrl") or "")[:56]

        nav_kpi12 = [
            {"label": "Avg full page load", "value": f"{avg_pl:.0f} ms", "sub": f"Target <2,000 ms · {round(avg_pl/2000,2)}×"},
            {"label": "P90 page load", "value": f"{float(nav_agg.get('p90_pl') or 0):.0f} ms", "sub": "1 in 10 above this"},
            {"label": "Slowest page", "value": f"{float(nav_agg.get('max_pl') or 0):.0f} ms", "sub": slowest_u or "—"},
            {"label": "Fastest page", "value": f"{float(nav_agg.get('min_pl') or 0):.0f} ms", "sub": fastest_u or "—"},
            {"label": "Pages <2 s load", "value": f"{round(100*under2/totaln)}%", "sub": f"{under2} of {totaln}"},
            {"label": "Pages >5 s load", "value": f"{round(100*over5/totaln)}%", "sub": f"{over5} of {totaln}"},
            {"label": "Avg DOM complete", "value": f"{avg_dom_c:.0f} ms", "sub": f"{pct_dom}% of avg load"},
            {"label": "Avg FID / TTI proxy", "value": f"{float(nav_agg.get('avg_fid') or 0):.0f} ms", "sub": "Target <100 ms Good"},
            {"label": "FID Good count", "value": f"{fid_g} of {totaln}", "sub": f"{fid_p} poor · {fid_ni} NI"},
            {"label": "Avg server processing", "value": f"{float(nav_agg.get('avg_srv_proc') or 0):.0f} ms", "sub": "Origin / app tier"},
            {"label": "Avg DNS lookup", "value": f"{float(nav_agg.get('avg_dns') or 0):.1f} ms", "sub": (nav_agg.get("network_health") or {}).get("dns_status", "")},
            {"label": "Avg request time", "value": f"{float(nav_agg.get('avg_req') or 0):.0f} ms", "sub": "Transfer + wait"},
        ]

    nav_findings = []
    if nav_agg and nav_pages:
        fd_nav = nav_agg.get("fid_distribution") or {}
        fid_poor_count = int(fd_nav.get("poor") or 0)
        avg_pl = float(nav_agg.get("avg_pl") or 0)
        avg_dom_c = float(nav_agg.get("avg_dom_comp") or 0)
        pct = round(100 * avg_dom_c / avg_pl, 1) if avg_pl > 0 else 0
        if pct > 35:
            nav_findings.append(
                {
                    "cls": "r",
                    "title": "DOM complete dominates load",
                    "body": f"DOM complete represents ~{pct}% of average full load — correlate with TBT and long tasks on main thread.",
                }
            )
        gaps = nav_agg.get("dom_gaps") or []
        if gaps:
            g0 = gaps[0]
            nav_findings.append(
                {
                    "cls": "r",
                    "title": "Post-load resource gap",
                    "body": f"Largest gap (load − DOM complete): {float(g0.get('gap_ms') or 0):.0f} ms on {g0.get('url', '')[:64]}.",
                }
            )
        if fid_poor_count > 0:
            worst = max(nav_pages, key=lambda r: float(r.get("firstInputDelay") or 0))
            nav_findings.append(
                {
                    "cls": "r",
                    "title": f"Poor FID on {fid_poor_count} page(s)",
                    "body": f"Worst FID sample: {worst.get('pageUrl', '')[:64]} — input delay harms first interaction SLAs.",
                }
            )
        nh = nav_agg.get("network_health") or {}
        if nh.get("srv_status") == "healthy" and nh.get("dns_status") != "critical":
            nav_findings.append(
                {
                    "cls": "g",
                    "title": "Server & DNS within tolerance",
                    "body": "Server and DNS averages suggest client-side / main-thread work is the dominant bottleneck.",
                }
            )

    tbt_sorted = sorted(pages, key=lambda p: float(p["metrics"]["tbt"]), reverse=True)
    worst_t_page = tbt_sorted[0] if tbt_sorted else None
    best_t_page = min(pages, key=lambda p: float(p["metrics"]["tbt"])) if pages else None
    inter_kpis = [
        {"label": "Avg TBT", "value": f"{avg_tbt:.0f} ms", "sub": "Target <200 ms"},
        {
            "label": "Worst TBT",
            "value": f"{float(worst_t_page['metrics']['tbt']):.0f} ms" if worst_t_page else "—",
            "sub": (worst_t_page or {}).get("url", "")[:52] or "—",
        },
        {
            "label": "Best TBT",
            "value": f"{float(best_t_page['metrics']['tbt']):.0f} ms" if best_t_page else "—",
            "sub": (best_t_page or {}).get("url", "")[:52] or "—",
        },
        {"label": "Avg 3rd-party block", "value": f"{float(tp.get('avg_block_ms') or 0):.0f} ms", "sub": "Main-thread"},
        {"label": "Avg main-thread", "value": f"{float(mt.get('avg_ms') or 0):.0f} ms", "sub": "LH breakdown"},
        {"label": "Avg JS execution", "value": f"{float(opps.get('js_execution', {}).get('avg_ms') or 0):.0f} ms", "sub": "bootup-time"},
    ]

    nav_network_zones = []
    if nav_agg:
        nh = nav_agg.get("network_health") or {}
        nav_network_zones.append(
            {
                "cls": "g" if nh.get("srv_status") == "healthy" else ("a" if nh.get("srv_status") == "warn" else "r"),
                "title": "Server processing",
                "body": f"Avg {float(nav_agg.get('avg_srv_proc') or 0):.0f} ms — "
                + ("healthy vs. client work" if float(nav_agg.get("avg_srv_proc") or 0) < 100 else "elevated; validate origin latency."),
            }
        )
        nav_network_zones.append(
            {
                "cls": "g" if nh.get("conn_status") == "healthy" else "a",
                "title": "TCP connection",
                "body": f"Avg {float(nav_agg.get('avg_conn') or 0):.0f} ms — TLS + connect handshake budget.",
            }
        )
        nav_network_zones.append(
            {
                "cls": "r" if nh.get("dns_status") == "critical" else ("a" if nh.get("dns_status") == "warn" else "g"),
                "title": "DNS lookup",
                "body": f"Avg {float(nav_agg.get('avg_dns') or 0):.1f} ms — investigate outliers >100 ms.",
            }
        )
        nav_network_zones.append(
            {
                "cls": "r" if nh.get("req_status") == "critical" else ("a" if nh.get("req_status") == "warn" else "g"),
                "title": "Request transfer",
                "body": f"Avg {float(nav_agg.get('avg_req') or 0):.0f} ms — payload size and concurrency.",
            }
        )

    return {
        "verdict_card_class": _verdict_card_class(verdict_raw.get("verdict", "")),
        "executive_narrative": narrative,
        "capacity_line": verdict_raw.get("capacity_assessment", ""),
        "cwv_cards": cwv_cards,
        "cwv_threshold_rows": cwv_threshold_rows,
        "loading_zones": loading_zones,
        "interactivity_zones": inter_zones,
        "stability_zones": stability_zones,
        "cls_causes_table": cls_causes,
        "nav_kpi12": nav_kpi12,
        "nav_network_zones": nav_network_zones,
        "inter_kpis": inter_kpis,
        "nav_findings": nav_findings,
        "lcp_ratio": lcp_ratio,
        "tbt_ratio": tbt_ratio,
        "fcp_ratio": fcp_ratio,
    }


def build_report_data(
    lh_paths: Sequence[str],
    nav_paths: Optional[Sequence[Optional[str]]] = None,
    *,
    site_name: str = "Application",
    site_section: str = "",
    env: str = "Production",
    sla: Optional[dict] = None,
) -> Tuple[dict, bool]:
    if not lh_paths:
        raise ValueError("At least one Lighthouse JSON file is required")
    lh_loader = LighthouseLoader()
    pages = [lh_loader.load_file(str(p)) for p in lh_paths]

    nav_loader = NavTimingLoader()
    nav_pages = nav_loader.load_many(nav_paths or [])
    has_nav = bool(nav_pages)

    cw_engine = CWVEngine()
    cwv_agg = cw_engine.aggregate_pages(pages)

    audit_e = AuditEngine()
    opps = audit_e.extract_opportunities(pages)
    rca = audit_e.generate_rca(opps, cwv_agg)

    sla = dict(sla or {})
    sla.setdefault("perf_score", 85)
    sla.setdefault("lcp", 2500)
    sla.setdefault("tbt", 200)
    sla.setdefault("cls", 0.1)
    sla.setdefault("fcp", 1800)

    verdict_raw = VerdictEngine().evaluate(cwv_agg, opps, sla)
    verdict_ui = {
        "label": verdict_raw["verdict"].replace("-", "_"),
        "color": verdict_raw["verdict_color"],
        "icon": verdict_raw["verdict_icon"],
        "title": verdict_raw["justification"][:120] + "…"
        if len(verdict_raw["justification"]) > 120
        else verdict_raw["justification"],
        "justification": verdict_raw["justification"],
        "score": verdict_raw["score"],
        "failed_criteria": verdict_raw["failed_criteria"],
        "passed_criteria": verdict_raw["passed_criteria"],
        "capacity_assessment": verdict_raw["capacity_assessment"],
    }

    nav_agg = nav_loader.compute_aggregates(nav_pages) if nav_pages else None

    meta = {
        "site_name": site_name,
        "site_section": site_section,
        "env": env,
        "audit_date": pages[0].get("fetch_time") or datetime.now(timezone.utc).isoformat(),
        "lh_version": pages[0].get("lh_version") or "",
        "page_count": len(pages),
        "has_nav_timing": has_nav,
        "run_id": (nav_agg or {}).get("run_id") or "N/A",
        "host": (nav_agg or {}).get("host") or "",
        "sla": sla,
    }

    scorecard = _build_scorecard_rows(pages, nav_pages, cw_engine)
    charts = _charts(pages, cwv_agg, nav_agg, nav_pages)

    lh_fcp = cwv_agg.get("avg_fcp", 0)
    lh_lcp = cwv_agg.get("avg_lcp", 0)
    lh_tti = cwv_agg.get("avg_tti", 0)
    load_breakdown = {
        "labels": ["TTFB", "First Contentful Paint", "DOM Interactive", "Full page load (nav)"],
        "data": [
            float(sum(p["metrics"]["ttfb"] for p in pages) / len(pages)),
            lh_fcp,
            lh_tti,
            float(nav_agg["avg_pl"]) if nav_agg else max(lh_lcp, lh_fcp),
        ],
    }

    exec_summary = {
        "paragraph": (
            f"{verdict_raw['verdict_icon']} {verdict_raw['verdict'].replace('_', '-')} — {verdict_raw['justification']} "
            f"Across {len(pages)} Lighthouse runs, average performance score is {cwv_agg['avg_perf_score']}/100 "
            f"(SLA ≥{sla['perf_score']}). "
            f"LCP Good pages: {cwv_agg['lcp_distribution']['good']}/{len(pages)}; "
            f"TBT Good: {cwv_agg['tbt_distribution']['good']}/{len(pages)}; "
            f"FCP Good: {cwv_agg['fcp_distribution']['good']}/{len(pages)}. "
            f"Average LCP is {cwv_agg['avg_lcp']:.0f} ms vs 2,500 ms Good threshold."
            + (
                f" Navigation timing shows average full load {nav_agg['avg_pl']:.0f} ms."
                if nav_agg
                else ""
            )
        )
    }

    kpis = {
        "avg_perf": cwv_agg["avg_perf_score"],
        "sla_perf": sla["perf_score"],
        "lcp_good": cwv_agg["lcp_distribution"]["good"],
        "tbt_good": cwv_agg["tbt_distribution"]["good"],
        "fcp_good": cwv_agg["fcp_distribution"]["good"],
        "total": len(pages),
        "avg_lcp": cwv_agg["avg_lcp"],
        "avg_tbt": cwv_agg["avg_tbt"],
        "avg_fcp": cwv_agg["avg_fcp"],
        "avg_cls": cwv_agg["avg_cls"],
        "min_perf": cwv_agg["min_perf_score"],
        "max_perf": cwv_agg["max_perf_score"],
        "worst_url": min(pages, key=lambda p: p["scores"]["performance"])["url"],
        "best_url": max(pages, key=lambda p: p["scores"]["performance"])["url"],
        "avg_pl": float(nav_agg["avg_pl"]) if nav_agg else None,
        "avg_unused_js": opps["unused_js"]["avg_savings_kb"],
        "loading_ring": _ring_class(cwv_agg["loading_health_score"]),
        "loading_score": cwv_agg["loading_health_score"],
        "inter_ring": _ring_class(cwv_agg["interactivity_health_score"]),
        "inter_score": cwv_agg["interactivity_health_score"],
        "stab_ring": _ring_class(cwv_agg["stability_health_score"]),
        "stab_score": cwv_agg["stability_health_score"],
    }

    plan = _plan_data(cwv_agg, verdict_raw)
    for prow in plan["rows"]:
        prow["score_gain"] = prow["gain"]

    issues_identified = _issues_identified_from_lh_pages(pages)

    spec = _build_spec_payload(
        pages,
        cwv_agg,
        opps,
        rca,
        nav_agg,
        nav_pages,
        verdict_raw,
        exec_summary["paragraph"],
        cw_engine,
        sla,
    )

    report = {
        "meta": meta,
        "verdict": verdict_ui,
        "verdict_raw": verdict_raw,
        "cwv": cwv_agg,
        "pages": scorecard,
        "lh_pages": pages,
        "opportunities": opps,
        "rca": rca,
        "nav": nav_agg,
        "nav_pages": nav_pages,
        "plan": plan,
        "spec": spec,
        "charts": charts,
        "exec_summary": exec_summary,
        "load_breakdown": load_breakdown,
        "kpis": kpis,
        "issues_identified": issues_identified,
    }
    return _sanitize(report), has_nav


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


def generate_lighthouse_nav_html_v2(
    lh_paths: Sequence[str],
    nav_paths: Optional[Sequence[Optional[str]]] = None,
    *,
    site_name: str = "Application",
    site_section: str = "",
    env: str = "Production",
    sla: Optional[dict] = None,
) -> str:
    data, has_nav = build_report_data(
        lh_paths,
        nav_paths,
        site_name=site_name,
        site_section=site_section,
        env=env,
        sla=sla,
    )
    return render_lh_nav_report_v2(data, has_nav_timing=has_nav)

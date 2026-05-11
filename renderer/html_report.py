"""Build comparison report JSON and render Jinja HTML."""

from __future__ import annotations

import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape

from analyser.comparator import ComparisonEngine
from analyser.comparison_scoring import apply_grading_to_go_nogo, compute_comparison_grading
from analyser.decisions import GoNoGoEngine, SLAConfig
from analyser.kpis import KPIEngine, build_targeted_rt_heatmap_buckets
from renderer import charts as chart_snippets

_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"


def _sanitize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_sanitize(x) for x in obj]
    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return None
        return obj
    if isinstance(obj, (np.floating, np.integer)):
        v = float(obj) if isinstance(obj, np.floating) else int(obj)
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    if isinstance(obj, pd.Timestamp):
        return obj.isoformat() if pd.notna(obj) else None
    if isinstance(obj, datetime):
        return obj.isoformat()
    if obj is pd.NA:
        return None
    try:
        if pd.isna(obj):
            return None
    except (TypeError, ValueError):
        pass
    return obj


def _serialize_error_bundle(e: dict) -> dict:
    base = {
        "total_errors": int(e.get("total_errors") or 0),
        "client_4xx_count": int(e.get("client_4xx_count") or 0),
        "server_5xx_count": int(e.get("server_5xx_count") or 0),
        "connection_count": int(e.get("connection_count") or 0),
        "error_onset_minute": e.get("error_onset_minute"),
        "error_onset_vu": e.get("error_onset_vu"),
        "error_peak_minute": e.get("error_peak_minute"),
        "error_peak_rate": float(e.get("error_peak_rate") or 0),
        "errors_by_band": _df_records(e.get("errors_by_band")),
        "errors_by_transaction": _df_records(e.get("errors_by_transaction")),
    }
    return _sanitize(base)


def _df_records(df: Optional[pd.DataFrame]) -> List[dict]:
    if df is None or len(df) == 0:
        return []
    d = df.replace({np.nan: None})
    return _sanitize(d.to_dict(orient="records"))


def _downsample_df(df: pd.DataFrame, max_rows: int = 500) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    step = max(1, len(df) // max_rows)
    return df.iloc[::step].copy().reset_index(drop=True)


def _peak_vu(k2: dict) -> int:
    mv = float(k2.get("max_vu") or 0)
    return int(mv) if mv >= 1 else 300


def _core_metrics_improved(k1: dict, k2: dict) -> bool:
    """True when baseline vs candidate shows meaningful wins on error, latency, or throughput."""
    er1, er2 = float(k1.get("error_rate_pct") or 0), float(k2.get("error_rate_pct") or 0)
    m1, m2 = float(k1.get("mean_rt") or 0), float(k2.get("mean_rt") or 0)
    t1, t2 = float(k1.get("overall_tps") or 0), float(k2.get("overall_tps") or 0)
    wins = 0
    if er1 > 0.05 and er2 < er1 * 0.9:
        wins += 1
    if m1 > 1 and m2 < m1 * 0.9:
        wins += 1
    if t1 > 1e-6 and t2 > t1 * 1.12:
        wins += 1
    return wins >= 2 or (wins == 1 and er2 < er1 * 0.7)


def _verdict_ui(gng: dict, k1: dict, k2: dict, improved_core: bool) -> dict:
    v = gng.get("verdict") or "CONDITIONAL"
    mv = _peak_vu(k2)
    grading = gng.get("grading") if isinstance(gng.get("grading"), dict) else None
    grade_label = str((grading or {}).get("release_header_label") or "").strip()
    grade_pill = str((grading or {}).get("release_header_pill_class") or "").strip().lower()
    grade_emoji = str((grading or {}).get("release_title_emoji") or "").strip()
    letter = str((grading or {}).get("grade") or "").strip()

    def _header_pill() -> Tuple[str, str]:
        """(pill display text, pill CSS class green|amber|red)"""
        if grade_label and grade_pill in ("green", "amber", "red"):
            return grade_label, grade_pill
        if v == "GO":
            return "GO", "green"
        if v == "NO_GO":
            return "NO-GO", "red"
        return "CONDITIONAL", "amber"

    hdr_txt, hdr_pill = _header_pill()

    if v == "GO":
        strip = "GO — System meets all production SLA criteria"
        title = grade_label or strip
        icon = grade_emoji or "✓"
        return {
            "label": "GO",
            "card_class": "go",
            "icon": icon,
            "title": title,
            "body": gng.get("justification") or "",
            "pill_class": hdr_pill,
            "header_pill_text": hdr_txt,
            "strip_text": strip,
        }
    if v == "NO_GO":
        if improved_core:
            strip = f"NO-GO — Blockers remain at {mv} VU despite measurable gains vs baseline"
        else:
            strip = "NO-GO — System does not meet production readiness criteria"
        title = grade_label or strip
        icon = grade_emoji or "✗"
        return {
            "label": "NO_GO",
            "card_class": "nogo",
            "icon": icon,
            "title": title,
            "body": gng.get("justification") or "",
            "pill_class": hdr_pill,
            "header_pill_text": hdr_txt,
            "strip_text": strip,
        }

    # CONDITIONAL — use scorecard release line when grading exists (e.g. grade B → business sign-off, red pill)
    if improved_core:
        strip = f"CONDITIONAL — Significant improvement, but NOT yet production-ready at {mv} VU"
    else:
        strip = f"CONDITIONAL — Not yet production-ready at {mv} VU"
    if grade_label:
        strip = (
            f"CONDITIONAL ({letter}) — {grade_label}. "
            f"Operational verdict at {mv} VU is conditional pending gates above; not a hard NO-GO."
        )
    icon = grade_emoji or "~"
    card_class = "cond"
    if grade_pill == "red":
        card_class = "cond risk-red"
    return {
        "label": "CONDITIONAL",
        "card_class": card_class,
        "icon": icon,
        "title": grade_label or strip,
        "body": gng.get("justification") or "",
        "pill_class": hdr_pill,
        "header_pill_text": hdr_txt,
        "strip_text": strip,
    }


def _tps_story(t1: float, t2: float) -> str:
    if t2 < 1e-6:
        return ""
    if t1 < 1e-6:
        return f"Throughput reached {t2:.1f} TPS."
    r = t2 / t1
    if r >= 2.85:
        return f"Throughput tripled from {t1:.1f} → {t2:.1f} TPS."
    if r >= 1.9:
        return f"Throughput roughly doubled from {t1:.1f} → {t2:.1f} TPS."
    if r > 1.08:
        return f"Throughput increased from {t1:.1f} → {t2:.1f} TPS ({100.0 * (r - 1):.0f}% higher)."
    if r < 0.92:
        return f"Throughput moved from {t1:.1f} → {t2:.1f} TPS."
    return f"Throughput is {t2:.1f} TPS vs {t1:.1f} TPS for the baseline."


def _mean_rt_story(m1: float, m2: float) -> str:
    if m1 < 1 and m2 < 1:
        return ""
    if m2 < m1 and m1 > 1:
        pct = 100.0 * (m1 - m2) / m1
        return f"Mean response time improved from {m1:,.0f}ms → {m2:,.0f}ms ({pct:.0f}% faster)."
    if m2 > m1 and m1 > 1:
        pct = 100.0 * (m2 - m1) / m1
        return f"Mean response time moved from {m1:,.0f}ms → {m2:,.0f}ms ({pct:.0f}% slower)."
    return f"Mean response time is {m2:,.0f}ms vs {m1:,.0f}ms baseline."


def _error_rate_story(er1: float, er2: float) -> str:
    if er1 < 1e-6 and er2 < 1e-6:
        return ""
    if er1 > 1e-6 and er2 < er1:
        red = (1.0 - er2 / er1) * 100.0
        return f"Error rate dropped from {er1:.2f}% → {er2:.2f}% ({red:.0f}% reduction)."
    return f"Error rate moved from {er1:.2f}% to {er2:.2f}%."


def _resolved_rca_tail_sentence(rcas: List[dict]) -> str:
    for r in rcas or []:
        if str(r.get("t2_status")) != "resolved":
            continue
        rid = str(r.get("rca_id") or "").strip()
        tit = str(r.get("title") or "").split("(")[0].strip()
        if tit and rid:
            return f"the {tit} ({rid}) has been resolved"
        if rid:
            return f"{rid} has been resolved"
        if tit:
            return f"{tit} has been resolved"
    return ""


def _eliminated_504_nohttp_clause(k1: dict, k2: dict, rcas: List[dict]) -> str:
    s504_1, s504_2 = int(k1.get("count_504") or 0), int(k2.get("count_504") or 0)
    nh1, nh2 = int(k1.get("count_nohttpresponse") or 0), int(k2.get("count_nohttpresponse") or 0)
    parts = []
    if s504_1 > 0 and s504_2 == 0:
        parts.append("HTTP 504 gateway timeouts")
    if nh1 > 0 and nh2 == 0:
        parts.append("NoHttpResponse/connection drops")
    if not parts:
        return ""
    joined = " and ".join(parts)
    tail = _resolved_rca_tail_sentence(rcas)
    if tail:
        return f"All {joined} have been eliminated — {tail}"
    return f"All {joined} have been eliminated"


def _workflow_404_hint(e2: dict) -> str:
    edf = e2.get("errors_by_transaction")
    if edf is None or (isinstance(edf, pd.DataFrame) and len(edf) == 0):
        return ""
    rows = edf.to_dict(orient="records") if isinstance(edf, pd.DataFrame) else list(edf)
    dom404 = [r for r in rows if str(r.get("dominant_type", "")).lower() in ("4xx", "404")]
    if not dom404:
        dom404 = rows[:12]
    nums: List[int] = []
    for r in dom404:
        m = re.search(r"T(\d+)", str(r.get("label", "")), re.I)
        if m:
            nums.append(int(m.group(1)))
    if len(nums) >= 2:
        lo, hi = min(nums), max(nums)
        if hi - lo <= 120:
            return f"concentrated in the workflow tier (approx. T{lo}–T{hi})"
    return "concentrated in specific high-traffic transaction labels"


def _human_tx_label(lab: str) -> str:
    s = str(lab).strip()
    if not s:
        return ""
    if "_" in s:
        tail = s.split("_")[-1]
        if tail and not tail.startswith("R"):
            return tail[:56]
    return s[:56]


def _critical_transactions_clause(tx2: pd.DataFrame, sla_p90: float) -> str:
    if tx2 is None or len(tx2) == 0:
        return ""
    if "status" not in tx2.columns:
        return ""
    crit = tx2[tx2["status"].astype(str).eq("critical")]
    if len(crit) == 0 and "p90_rt" in tx2.columns:
        crit = tx2[pd.to_numeric(tx2["p90_rt"], errors="coerce").fillna(0) > max(sla_p90 * 3, 10000.0)]
    if len(crit) == 0:
        return ""
    crit = crit.sort_values("p90_rt", ascending=False).head(6)
    p90s = pd.to_numeric(crit["p90_rt"], errors="coerce").dropna()
    if len(p90s) == 0:
        return ""
    lo_ms, hi_ms = float(p90s.min()), float(p90s.max())
    names = []
    for _, r in crit.iterrows():
        h = _human_tx_label(str(r.get("label", "")))
        if h and h not in names:
            names.append(h)
        if len(names) >= 4:
            break
    if not names:
        return ""
    listed = ", ".join(names[:3])
    if len(names) > 3:
        listed += ", and related workflow steps"
    if hi_ms >= 10000:
        return f"critical workflow transactions ({listed}) still have P90 of {lo_ms / 1000:.0f}–{hi_ms / 1000:.0f}s"
    return f"critical workflow transactions ({listed}) still miss the P90 SLA"


def _build_executive_verdict_paragraphs(
    k1: dict,
    k2: dict,
    tx2: pd.DataFrame,
    tx_m: pd.DataFrame,
    b2: pd.DataFrame,
    e2: dict,
    rca_changes: List[dict],
    gng: dict,
    meta: dict,
    sla: SLAConfig,
    improved_core: bool,
) -> Tuple[str, str]:
    run2 = str(meta.get("run_id_2") or "the candidate run (T2)")
    er1, er2 = float(k1.get("error_rate_pct") or 0), float(k2.get("error_rate_pct") or 0)
    m1, m2 = float(k1.get("mean_rt") or 0), float(k2.get("mean_rt") or 0)
    t1, t2 = float(k1.get("overall_tps") or 0), float(k2.get("overall_tps") or 0)

    er_s = _error_rate_story(er1, er2)
    mean_s = _mean_rt_story(m1, m2)
    tps_s = _tps_story(t1, t2)
    elim_s = _eliminated_504_nohttp_clause(k1, k2, rca_changes)

    if improved_core:
        opener = (
            f"{run2} shows dramatic and measurable improvement across every core metric. "
            if (er2 < er1 and m2 < m1 and t2 > t1 and er1 > 0.01)
            else f"{run2} shows measurable improvement across core metrics. "
        )
    else:
        opener = f"{run2} relative to baseline shows a mixed performance picture. "

    body_bits = [x for x in (er_s, mean_s, tps_s) if x]
    if elim_s:
        body_bits.append(elim_s)

    lead = (opener + " ".join(body_bits)).strip() if body_bits else opener.strip()
    if lead and not lead.endswith((".", "!", "?")):
        lead += "."

    v = gng.get("verdict") or "CONDITIONAL"
    mv = _peak_vu(k2)
    caveats = ""

    if v == "GO":
        caveats = (
            "All weighted production gates pass for this slice. "
            "Promote under standard change control and observe early production intervals for drift on errors and tail latency."
        )
        return lead, caveats

    gate_intro = (
        f"However, the system cannot receive a GO decision for production at {mv} VU because: "
        if v == "CONDITIONAL"
        else f"However, a NO-GO is indicated for production at {mv} VU because: "
    )

    items: List[str] = []
    c404 = int(k2.get("count_404") or 0)
    c404_1 = int(k1.get("count_404") or 0)
    if c404 > 0:
        hint = _workflow_404_hint(e2)
        idx = len(items) + 1
        frag = f"({idx}) {c404:,} HTTP 404 errors persist"
        if hint:
            frag += f" {hint}"
        if c404_1 > 0 and c404 < c404_1:
            frag += f" ({(1.0 - c404 / c404_1) * 100:.0f}% reduction vs baseline, yet material volume remains)"
        items.append(frag)

    sla_fail = 0
    if len(tx2) and "sla_pass" in tx2.columns:
        sla_fail = int((tx2["sla_pass"] == False).sum())
    elif len(tx_m) and "sla_t2" in tx_m.columns:
        sla_fail = int((tx_m["sla_t2"] == False).sum())
    elif len(tx_m) and "sla_t2_pass" in tx_m.columns:
        sla_fail = int(tx_m["sla_t2_pass"].astype(str).eq("FAIL").sum())
    if sla_fail > 0:
        items.append(
            f"({len(items) + 1}) {sla_fail} transactions fail the P90 <{sla.sla_p90 / 1000:.0f}s SLA (and associated error-rate gate)"
        )

    peak_er = 0.0
    if b2 is not None and len(b2) and "load_band" in b2.columns:
        hi = b2[b2["load_band"].astype(str) == "241–300"]
        if len(hi):
            peak_er = float(hi.iloc[0].get("error_rate") or 0)
    if peak_er > float(sla.sla_error) + 1e-6:
        items.append(
            f"({len(items) + 1}) error rate exceeds the {sla.sla_error:.0f}% threshold in the highest load band (241–300 VU), "
            f"reaching up to {peak_er:.1f}%"
        )
    elif float(k2.get("error_rate_pct") or 0) > float(sla.sla_error) + 1e-6 and not any(
        "error rate exceeds" in x for x in items
    ):
        items.append(
            f"({len(items) + 1}) overall error rate is {float(k2.get('error_rate_pct') or 0):.2f}%, above the {sla.sla_error:.0f}% policy"
        )

    ctx = _critical_transactions_clause(tx2, float(sla.sla_p90))
    if ctx:
        items.append(f"({len(items) + 1}) {ctx}")

    if not items and v != "GO":
        blockers = gng.get("no_go_blockers") or []
        conds = gng.get("conditional_items") or []
        tags = [str(x.get("id") or x.get("label") or "") for x in (blockers + conds) if x]
        tag_txt = "; ".join(t for t in tags if t)[:500]
        if tag_txt:
            items.append(f"({len(items) + 1}) automated gates still flag: {tag_txt}")

    if items:
        caveats = gate_intro + " ".join(items) + "."
        caveats += (
            " The run demonstrates meaningful progress against prior failure modes; "
            "address the remaining items (or accept them explicitly with risk owners) before granting a full GO."
        )

    return lead, caveats


def _band_row_verdict(r: dict) -> str:
    p90_t2 = float(r.get("p90_rt_t2") or 0)
    er_t2 = float(r.get("error_rate_t2") or 0)
    if p90_t2 <= 3000 and er_t2 < 1.0:
        return "Improved"
    if p90_t2 <= 4500 and er_t2 < 2.0:
        return "Near-pass"
    p90_t1 = float(r.get("p90_rt_t1") or 0)
    if p90_t2 < p90_t1:
        return "Improving"
    return "Watch"


def _exec_kpi_strip(k1: dict, k2: dict, tx2: pd.DataFrame) -> List[dict]:
    n_tx = len(tx2)
    sla_pass = 0
    if n_tx and "sla_pass" in tx2.columns:
        sla_pass = int(tx2["sla_pass"].sum())
    ratio = round(100.0 * sla_pass / max(n_tx, 1), 0)
    cov1 = 0.0
    cov2 = 0.0
    return [
        {
            "kl": "Error rate",
            "kv": f"{k2.get('error_rate_pct', 0):.2f}%",
            "kvc": "g" if k2.get("error_rate_pct", 99) < 1 else "a",
            "ks": f"Was {k1.get('error_rate_pct', 0):.2f}% · {_fmt_pct_delta(k1.get('error_rate_pct', 0), k2.get('error_rate_pct', 0), True)}",
        },
        {
            "kl": "HTTP 404 errors",
            "kv": f"{int(k2.get('count_404', 0)):,}",
            "kvc": "a" if k2.get("count_404", 0) > 0 else "g",
            "ks": f"Was {int(k1.get('count_404', 0)):,} · {_fmt_pct_delta(float(k1.get('count_404', 0)), float(k2.get('count_404', 0)), True)}",
        },
        {
            "kl": "HTTP 504 timeouts",
            "kv": str(int(k2.get("count_504", 0))),
            "kvc": "g" if k2.get("count_504", 0) == 0 else "r",
            "ks": _fmt_504_ks(k1.get("count_504", 0), k2.get("count_504", 0)),
        },
        {
            "kl": "Mean response time",
            "kv": f"{k2.get('mean_rt', 0):.0f}ms",
            "kvc": "g",
            "ks": f"Was {k1.get('mean_rt', 0):.0f}ms · {_fmt_pct_delta(k1.get('mean_rt', 0), k2.get('mean_rt', 0), True)}",
        },
        {
            "kl": "P90 response time",
            "kv": f"{k2.get('p90_rt', 0):.0f}ms",
            "kvc": "g" if k2.get("p90_rt", 0) < 3000 else "a",
            "ks": f"Was {k1.get('p90_rt', 0):.0f}ms · {_fmt_pct_delta(k1.get('p90_rt', 0), k2.get('p90_rt', 0), True)}",
        },
        {
            "kl": "P95 response time",
            "kv": f"{k2.get('p95_rt', 0):.0f}ms",
            "kvc": "a" if k2.get("p95_rt", 0) > 5000 else "g",
            "ks": f"Was {k1.get('p95_rt', 0):.0f}ms · {_fmt_pct_delta(k1.get('p95_rt', 0), k2.get('p95_rt', 0), True)}",
        },
        {
            "kl": "Overall TPS",
            "kv": f"{k2.get('overall_tps', 0):.1f}",
            "kvc": "g",
            "ks": f"Was {k1.get('overall_tps', 0):.1f} · {_fmt_pct_delta(k1.get('overall_tps', 0), k2.get('overall_tps', 0), False)}",
        },
        {
            "kl": "TPS at 300 VU",
            "kv": "—",
            "kvc": "g",
            "ks": "See throughput panel for band-level TPS",
        },
        {
            "kl": "Apdex @ 300 VU",
            "kv": f"{k2.get('apdex', 0):.3f}",
            "kvc": "g",
            "ks": f"Was {k1.get('apdex', 0):.3f} · {_fmt_apdex_delta(k1.get('apdex', 0), k2.get('apdex', 0))}",
        },
        {
            "kl": "NoHTTP conn drops",
            "kv": str(int(k2.get("count_nohttpresponse", 0))),
            "kvc": "g" if k2.get("count_nohttpresponse", 0) == 0 else "r",
            "ks": _fmt_504_ks(k1.get("count_nohttpresponse", 0), k2.get("count_nohttpresponse", 0)).replace("504", "NoHTTP"),
        },
        {
            "kl": "Total samples (T2)",
            "kv": f"{int(k2.get('total_samples', 0)):,}",
            "kvc": "",
            "ks": _sample_conf_k(k1.get("total_samples", 0), k2.get("total_samples", 0)),
        },
        {
            "kl": "SLA P90 pass rate",
            "kv": f"{ratio:.0f}%",
            "kvc": "g" if ratio >= 85 else "a",
            "ks": "Share of transactions meeting P90 & error SLA (T2)",
        },
    ]


def _fmt_pct_delta(t1: float, t2: float, lower_better: bool) -> str:
    if abs(t1) < 1e-12:
        pct = 100.0 if abs(t2) > 1e-12 else 0.0
    else:
        pct = 100.0 * (t2 - t1) / abs(t1)
    if lower_better:
        return f"−{abs(pct):.0f}%" if pct < 0 else f"+{pct:.0f}%"
    return f"+{pct:.0f}%" if pct > 0 else f"−{abs(pct):.0f}%"


def _fmt_apdex_delta(t1: float, t2: float) -> str:
    d = t2 - t1
    sign = "+" if d >= 0 else "−"
    return f"{sign}{abs(d):.3f} delta"


def _fmt_504_ks(c1: Any, c2: Any) -> str:
    n1 = int(c1 or 0)
    n2 = int(c2 or 0)
    if n1 > 0 and n2 == 0:
        return f"Was {n1:,} · 100% eliminated"
    return f"Was {n1:,} · remains {n2:,}"


def _sample_conf_k(n1: Any, n2: Any) -> str:
    n1 = int(n1 or 0)
    n2 = int(n2 or 0)
    if n1 <= 0:
        return "T2 sample count"
    m = n2 / n1
    return f"{m:.1f}× vs T1 = higher confidence" if m > 1 else "vs baseline"


def _band_compare_sort_key(row: dict) -> Tuple[int, int]:
    lb = str(row.get("load_band") or "")
    m = re.match(r"^(\d+)\s*[–\-]\s*(\d+)", lb)
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.match(r"^(\d+)", lb)
    if m2:
        v = int(m2.group(1))
        return v, v
    return 999999, 999999


def _prune_heatmap_buckets(hm1: pd.DataFrame, hm2: pd.DataFrame, min_pct: float = 0.05) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
    cols_t2 = [c for c in hm2.columns if c != "load_band"]
    if not cols_t2:
        return hm1, hm2, []
    keep = [c for c in cols_t2 if float(hm2[c].max()) >= min_pct - 1e-9]
    if not keep:
        keep = cols_t2
    c1_ok = [c for c in keep if c in hm1.columns]
    hm1n = hm1[["load_band"] + c1_ok].copy() if c1_ok else hm1.copy()
    hm2n = hm2[["load_band"] + keep].copy()
    return hm1n, hm2n, keep


def _throughput_evidence_html(tp1: dict, tp2: dict) -> str:
    lines: List[str] = []
    lines.append(
        f"T2 overall {float((tp2 or {}).get('overall_tps') or 0):.1f} TPS vs T1 {float((tp1 or {}).get('overall_tps') or 0):.1f} TPS."
    )
    st1 = str((tp1 or {}).get("scalability_type") or "—")
    st2 = str((tp2 or {}).get("scalability_type") or "—")
    lines.append(
        f"Scalability pattern: T1 <strong>{st1}</strong> · T2 <strong>{st2}</strong> "
        f"(collapse T1={bool((tp1 or {}).get('collapse_detected'))} · T2={bool((tp2 or {}).get('collapse_detected'))})."
    )
    sat = (tp2 or {}).get("saturation_band") or (tp1 or {}).get("saturation_band")
    if sat:
        lines.append(f"Saturation band (T2-oriented): <strong>{sat}</strong>.")
    tb1 = tp1.get("tps_by_band") if isinstance(tp1, dict) else None
    tb2 = tp2.get("tps_by_band") if isinstance(tp2, dict) else None
    if isinstance(tb1, pd.DataFrame) and isinstance(tb2, pd.DataFrame) and len(tb2):
        lines.append("<br>TPS by load band (all buckets with T2 data):")
        b2 = tb2.copy()
        b2["_sk"] = b2["load_band"].astype(str).map(lambda x: _band_compare_sort_key({"load_band": x})[0])
        b2 = b2.sort_values("_sk").drop(columns=["_sk"])
        for _, r in b2.iterrows():
            band = str(r.get("load_band", ""))
            v2 = float(r.get("tps_mean") or 0)
            v1 = 0.0
            if len(tb1):
                m = tb1[tb1["load_band"].astype(str) == band]
                if len(m):
                    v1 = float(m.iloc[0].get("tps_mean") or 0)
            cov = float(r.get("tps_cov") or 0)
            lines.append(f"· {band}: T2 <strong>{v2:.1f}</strong> TPS (CoV {cov*100:.0f}%) vs T1 {v1:.1f}")
    elif isinstance(tb2, pd.DataFrame) and len(tb2):
        lines.append("Per-band TPS (T2):")
        for _, r in tb2.iterrows():
            lines.append(
                f"· {r.get('load_band')}: {float(r.get('tps_mean') or 0):.1f} TPS"
            )
    return " ".join(lines)


def _heatmap_cells(row: dict, bucket_cols: List[str]) -> List[dict]:
    cells = []
    for c in bucket_cols:
        pct = float(row.get(c) or 0)
        # heat class by bucket index and magnitude
        idx = bucket_cols.index(c)
        if pct <= 0.5:
            h = 0
        elif pct < 2:
            h = 1
        elif pct < 5:
            h = 2
        elif pct < 10:
            h = 3
        elif idx <= 3 and pct >= 15:
            h = 4
        elif idx <= 5 and pct >= 10:
            h = 5
        elif idx <= 6:
            h = 6
        elif idx <= 7:
            h = 7
        else:
            h = min(9, 7 + int(pct // 15))
        cells.append({"pct": pct, "heat": f"heat-{h}"})
    return cells


def build_report_payload(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    *,
    run_id_1: str ,
    run_id_2: str,
    meta_title: str = "Performance Test Comparison Report",
    environment: str = "—",
    analyst: str = "Performance Engineering Architect",
    sla: Optional[SLAConfig] = None,
) -> dict:
    sla = sla or SLAConfig()
    kpi = KPIEngine()
    cmp = ComparisonEngine()
    dec = GoNoGoEngine()

    k1 = kpi.overall_kpis(df1)
    k2 = kpi.overall_kpis(df2)
    pm1 = _downsample_df(kpi.per_minute_kpis(df1))
    pm2 = _downsample_df(kpi.per_minute_kpis(df2))
    b1 = kpi.per_band_kpis(df1)
    b2 = kpi.per_band_kpis(df2)
    tx1 = kpi.per_transaction_kpis(df1)
    tx2 = kpi.per_transaction_kpis(df2)
    e1 = kpi.error_analysis(df1)
    e2 = kpi.error_analysis(df2)
    tp1 = kpi.throughput_analysis(df1)
    tp2 = kpi.throughput_analysis(df2)

    tx_m = cmp.compare_transactions(tx1, tx2)
    band_m = cmp.compare_bands(b1, b2)
    cmp.compare_overall_kpis(k1, k2)
    err_comp = cmp.compare_errors(e1, e2)

    t1_for_rca = {
        "kpis": k1,
        "error_analysis": e1,
        "throughput": tp1,
        "transactions": tx1,
        "per_minute": pm1,
    }
    t2_for_rca = {
        "kpis": k2,
        "error_analysis": e2,
        "throughput": tp2,
        "transactions": tx2,
        "per_minute": pm2,
    }
    rca_changes = cmp.identify_rca_changes(t1_for_rca, t2_for_rca)

    gng = dec.evaluate(k2, tx2, b2, sla, compare_tx=tx_m)
    grading = compute_comparison_grading(k2, tx2, tx_m, tp2, sla)
    gng = apply_grading_to_go_nogo(gng, grading, k2, sla)
    improved_core = _core_metrics_improved(k1, k2)
    narrative_meta = {"run_id_1": run_id_1, "run_id_2": run_id_2}
    lead, caveats = _build_executive_verdict_paragraphs(
        k1,
        k2,
        tx2,
        tx_m,
        b2,
        e2,
        rca_changes,
        gng,
        narrative_meta,
        sla,
        improved_core,
    )
    narrative = lead + (f"\n\n{caveats}" if caveats else "")
    verdict_ui = _verdict_ui(gng, k1, k2, improved_core)

    apx1 = kpi.apdex_by_band(df1)
    apx2 = kpi.apdex_by_band(df2)
    rt_buck = build_targeted_rt_heatmap_buckets(float(sla.sla_mean_rt_ms), float(sla.sla_p90))
    hm1 = kpi.rt_distribution_heatmap(df1, buckets=rt_buck)
    hm2 = kpi.rt_distribution_heatmap(df2, buckets=rt_buck)
    hm1, hm2, hm_cols = _prune_heatmap_buckets(hm1, hm2, min_pct=0.05)
    lat1 = kpi.latency_decomposition(df1)
    lat2 = kpi.latency_decomposition(df2)

    band_rows = _df_records(band_m)
    band_rows.sort(key=_band_compare_sort_key)
    for r in band_rows:
        r["verdict_label"] = _band_row_verdict(r)

    hm_buckets = hm_cols
    heat_rows = []
    for _, rr in hm2.iterrows():
        rowd = rr.to_dict()
        heat_rows.append(
            {
                "load_band": str(rowd.get("load_band", "")),
                "cells": _heatmap_cells(rowd, hm_buckets),
            }
        )

    tps_hi_1 = 0.0
    tps_hi_2 = 0.0
    cov300_1 = 0.0
    cov300_2 = 0.0
    if len(b1):
        hi = b1[b1["load_band"] == "241–300"]
        if len(hi):
            tps_hi_1 = float(hi.iloc[0]["tps_mean"])
            cov300_1 = float(hi.iloc[0]["tps_cov"])
    if len(b2):
        hi = b2[b2["load_band"] == "241–300"]
        if len(hi):
            tps_hi_2 = float(hi.iloc[0]["tps_mean"])
            cov300_2 = float(hi.iloc[0]["tps_cov"])

    exec_kpis = _exec_kpi_strip(k1, k2, tx2)
    exec_kpis[7]["kv"] = f"~{tps_hi_2:.0f}"
    exec_kpis[7]["ks"] = (
        f"Was ~{tps_hi_1:.0f} · T2 CoV {cov300_2 * 100:.0f}% vs T1 {cov300_1 * 100:.0f}%"
    )

    err_table_rows: List[dict] = []
    if len(tx_m):
        sub = tx_m[
            (tx_m["ec_t2"].fillna(0) > 0) | (tx_m["ec_t1"].fillna(0) > 0)
        ].sort_values("ec_t2", ascending=False).head(40)
        for _, r in sub.iterrows():
            dom = "404"
            if float(r.get("err_t2") or 0) < 0.01:
                dom = "—"
            err_table_rows.append(
                {
                    "label": r["label"],
                    "e2": _safe_int(r.get("ec_t2"), 0),
                    "er2": _safe_float(r.get("err_t2"), 0),
                    "dom": dom,
                    "e1": _safe_int(r.get("ec_t1"), 0),
                    "er1": _safe_float(r.get("err_t1"), 0),
                    "st": _err_row_status(r),
                }
            )

    tx_score_rows: List[dict] = []
    for _, r in tx_m.iterrows():
        tx_score_rows.append(
            {
                "label": r["label"],
                "p90_t1": r.get("p90_t1"),
                "p90_t2": r.get("p90_t2"),
                "dp90": r.get("delta_p90"),
                "er1": r.get("err_t1"),
                "er2": r.get("err_t2"),
                "a1": r.get("apdex_t1"),
                "a2": r.get("apdex_t2"),
                "s1": r.get("sla_t1_pass"),
                "s2": r.get("sla_t2_pass"),
                "badgestatus": _tx_badge(r),
            }
        )

    t2_band_hi = b2[b2["load_band"] == "241–300"] if len(b2) else b2
    pct_spread = {}
    if len(t2_band_hi):
        sub = df2[df2["load_band"] == "241–300"]
        if len(sub):
            el = sub["elapsed"].astype(float)
            pct_spread = {
                "median": float(el.median()),
                "p75": float(el.quantile(0.75)),
                "p90": float(el.quantile(0.90)),
                "p95": float(el.quantile(0.95)),
                "p99": float(el.quantile(0.99)),
            }

    meta = {
        "run_id_1": run_id_1,
        "run_id_2": run_id_2,
        "title": meta_title,
        "env": environment,
        "analyst": analyst,
        "t1_start": k1.get("start_time", ""),
        "t2_start": k2.get("start_time", ""),
        "t1_duration_min": round(k1.get("duration_min", 0), 1),
        "t2_duration_min": round(k2.get("duration_min", 0), 1),
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "max_vu": int(max(k1.get("max_vu", 0), k2.get("max_vu", 0))),
    }

    tx_counts = _tx_status_counts(tx2)

    data = {
        "meta": meta,
        "verdict": verdict_ui,
        "verdict_narrative": narrative,
        "verdict_narrative_lead": lead,
        "verdict_narrative_caveats": caveats,
        "go_nogo": _sanitize(gng),
        "kpis_t1": _sanitize(k1),
        "kpis_t2": _sanitize(k2),
        "kpi_comparison": _sanitize(cmp.compare_overall_kpis(k1, k2)),
        "executive_kpis": exec_kpis,
        "bands_t1": _df_records(b1),
        "bands_t2": _df_records(b2),
        "band_compare": band_rows,
        "per_minute_t1": _df_records(pm1),
        "per_minute_t2": _df_records(pm2),
        "transactions": _sanitize(tx_score_rows),
        "transactions_full": _df_records(tx_m),
        "error_analysis": {
            "t1": _serialize_error_bundle(e1),
            "t2": _serialize_error_bundle(e2),
            "compare": _sanitize(err_comp),
        },
        "rca_changes": _sanitize(rca_changes),
        "heatmap_t1": _df_records(hm1),
        "heatmap_t2": _df_records(hm2),
        "heatmap_buckets": hm_buckets,
        "heatmap_bucket_note": "Buckets align with mean/P90 targets; empty tail ranges are omitted when no samples fall in them.",
        "heatmap_rows_t2": heat_rows,
        "throughput_evidence_html": _throughput_evidence_html(tp1, tp2),
        "apdex_t1": _df_records(apx1),
        "apdex_t2": _df_records(apx2),
        "throughput": {"t1": _sanitize({**{k: v for k, v in tp1.items() if k != "tps_by_band"}, "tps_by_band": _df_records(tp1.get("tps_by_band"))}), "t2": _sanitize({**{k: v for k, v in tp2.items() if k != "tps_by_band"}, "tps_by_band": _df_records(tp2.get("tps_by_band"))})},
        "latency_t1": _df_records(lat1),
        "latency_t2": _df_records(lat2),
        "t2_pct_spread_peak": _sanitize(pct_spread),
        "err_by_tx_table": err_table_rows,
        "what_changed_zones": _what_changed_zones(k1, k2, rca_changes, tp1, tp2),
        "tx_counts": tx_counts,
        "chart_defaults_js": chart_snippets.CHART_DEFAULTS_JS,
    }
    return _sanitize(data)


def _safe_float(x: Any, default: float = 0.0) -> float:
    try:
        v = float(x)
        if math.isnan(v):
            return default
        return v
    except (TypeError, ValueError):
        return default


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        v = float(x)
        if math.isnan(v):
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _err_row_status(r: pd.Series) -> str:
    if float(r.get("ec_t1") or 0) > 0 and float(r.get("ec_t2") or 0) == 0:
        return "Resolved ✓"
    if float(r.get("ec_t1") or 0) == 0 and float(r.get("ec_t2") or 0) > 0:
        return "New in T2"
    if float(r.get("err_t2") or 0) > float(r.get("err_t1") or 0) + 0.5:
        return "Regressed"
    if float(r.get("err_t2") or 0) < float(r.get("err_t1") or 0):
        return "Improved"
    return "—"


def _tx_badge(r: pd.Series) -> str:
    st = str(r.get("change_status") or "")
    m = {
        "fixed": "Fixed ✓",
        "stable": "Stable",
        "improved": "Improved",
        "major_gain": "Major gain",
        "regressed": "Regressed",
        "new_failure": "New errors",
        "resolved": "Resolved ✓",
        "baseline_only": "Baseline only",
        "current_only": "Current only",
        "partial": "Partial",
    }
    return m.get(st, st.replace("_", " ").title())


def _tx_status_counts(tx_m: pd.DataFrame) -> dict:
    if len(tx_m) == 0:
        return {"critical": 0, "warning": 0, "slow": 0, "healthy": 0}
    if "status" not in tx_m.columns:
        return {"critical": 0, "warning": 0, "slow": 0, "healthy": int(len(tx_m))}
    vc = tx_m["status"].value_counts().to_dict()
    return {
        "critical": int(vc.get("critical", 0)),
        "warning": int(vc.get("warning", 0)),
        "slow": int(vc.get("slow", 0)),
        "healthy": int(vc.get("healthy", 0)),
    }



def _what_changed_zones(
    k1: dict, k2: dict, rcas: List[dict], tp1: dict, tp2: dict
) -> List[dict]:
    zones = []
    if (k1.get("count_504", 0) or 0) > 0 and (k2.get("count_504", 0) or 0) == 0:
        zones.append(
            {
                "cls": "g",
                "badge": "FIXED",
                "badge_cls": "bg",
                "title": "504 gateway timeouts eliminated",
                "body": f"T1 had {int(k1.get('count_504', 0)):,} HTTP 504 responses; T2 has {int(k2.get('count_504', 0))}. Analytics/render or gateway capacity was addressed.",
            }
        )
    if (k1.get("count_404", 0) or 0) > (k2.get("count_404", 0) or 0) * 1.2:
        zones.append(
            {
                "cls": "g",
                "badge": "FIXED",
                "badge_cls": "bg",
                "title": "404 volume reduced",
                "body": f"404 count dropped from {int(k1.get('count_404', 0)):,} to {int(k2.get('count_404', 0)):,}. Routing/session fixes partially confirmed.",
            }
        )
    if str(tp1.get("scalability_type")) == "negative" and str(tp2.get("scalability_type")) != "negative":
        zones.append(
            {
                "cls": "g",
                "badge": "FIXED",
                "badge_cls": "bg",
                "title": "Throughput scalability improved",
                "body": f"T1 scalability pattern: {tp1.get('scalability_type')}; T2: {tp2.get('scalability_type')}. Collapse flag T1={tp1.get('collapse_detected')} T2={tp2.get('collapse_detected')}.",
            }
        )
    if (k2.get("count_404", 0) or 0) > 500:
        zones.append(
            {
                "cls": "a",
                "badge": "PARTIAL",
                "badge_cls": "ba",
                "title": "404 concentration may remain in workflow tier",
                "body": f"T2 still records {int(k2.get('count_404', 0)):,} client errors — validate remaining endpoints and session scope.",
            }
        )
    if float(k2.get("error_rate_pct", 0)) > 1.0:
        zones.append(
            {
                "cls": "r",
                "badge": "REMAINS",
                "badge_cls": "br",
                "title": "Overall error rate above 1% policy",
                "body": f"T2 error rate {float(k2.get('error_rate_pct', 0)):.2f}% exceeds typical GO gate; conditional release only.",
            }
        )
    for r in rcas:
        if r.get("t2_status") == "new":
            zones.append(
                {
                    "cls": "r",
                    "badge": "NEW",
                    "badge_cls": "br",
                    "title": r.get("title", "New risk"),
                    "body": f"{r.get('evidence_t1', '')} {r.get('evidence_t2', '')}",
                }
            )
    return zones[:8]


def _inject_json(template: str, data: dict) -> str:
    blob = json.dumps(data, separators=(",", ":"), allow_nan=False)
    return template.replace("__REPORT_DATA_JSON__", blob)


class ComparisonHtmlReport:
    def __init__(self, template_dir: Optional[Path] = None) -> None:
        tdir = template_dir or _TEMPLATE_DIR
        self.env = Environment(
            loader=FileSystemLoader(str(tdir)),
            autoescape=select_autoescape(["html", "xml"]),
        )

    def render(self, payload: dict) -> str:
        tpl = self.env.get_template("report.html.jinja2")
        html = tpl.render(data=payload)
        return _inject_json(html, payload)


def render_comparison_html(payload: dict) -> str:
    return ComparisonHtmlReport().render(payload)

"""
Bridge JTLParserV2 record lists to the repo-root comparison engine (analyser/ + renderer/).
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from analyser.decisions import SLAConfig  # noqa: E402
from analyser.loader import JMeterLoader  # noqa: E402
from renderer.html_report import build_report_payload, render_comparison_html  # noqa: E402


def _traffic_for_verdict(code: str) -> str:
    if code == "GO":
        return "green"
    if code == "NO_GO":
        return "red"
    return "amber"


def jtl_records_to_raw_df(records: List[Dict[str, Any]]) -> pd.DataFrame:
    """Map internal JTL parser keys to JMeterLoader column names."""
    if not records:
        return pd.DataFrame()
    rows = []
    for d in records:
        rows.append(
            {
                "timeStamp": int(d.get("timestamp") or 0),
                "elapsed": float(d.get("sample_time") or 0),
                "label": str(d.get("label") or ""),
                "responseCode": str(d.get("response_code") or ""),
                "success": d.get("success", True),
                "allThreads": int(d.get("all_threads") or 0),
                "Latency": float(d.get("latency") or 0),
                "Connect": float(d.get("connect_time") or 0),
                "bytes": int(d.get("bytes") or 0),
                "sentBytes": int(d.get("sent_bytes") or 0),
            }
        )
    return pd.DataFrame(rows)


def build_jmeter_comparison_v2(
    data_a: List[Dict[str, Any]],
    data_b: List[Dict[str, Any]],
    *,
    name_a: str,
    name_b: str,
    meta_title: str = "Performance Test Comparison Report",
    environment_a: Optional[str] = None,
    environment_b: Optional[str] = None,
    build_a: Optional[str] = None,
    build_b: Optional[str] = None,
    sla: Optional[SLAConfig] = None,
) -> Tuple[str, Dict[str, Any]]:
    """
    Returns (self-contained HTML, analysis dict for DB/API).
    analysis includes a heavy 'report_payload' for regenerate-from-library (file uploads).
    """
    if not data_a or not data_b:
        raise ValueError("Both baseline and candidate must contain at least one sample")

    loader = JMeterLoader()
    raw_a = jtl_records_to_raw_df(data_a)
    raw_b = jtl_records_to_raw_df(data_b)
    df1 = loader.from_dataframe(raw_a, name_a, source_path="api:baseline")
    df2 = loader.from_dataframe(raw_b, name_b, source_path="api:candidate")
    if len(df1) == 0 or len(df2) == 0:
        raise ValueError("Failed to build comparison frames from JMeter samples")

    env_parts = []
    if environment_a:
        env_parts.append(f"A: {environment_a}")
    if environment_b:
        env_parts.append(f"B: {environment_b}")
    if build_a:
        env_parts.append(f"Build A: {build_a}")
    if build_b:
        env_parts.append(f"Build B: {build_b}")
    environment = " · ".join(env_parts) if env_parts else "—"

    sla = sla or SLAConfig()
    payload = build_report_payload(
        df1,
        df2,
        run_id_1=name_a,
        run_id_2=name_b,
        meta_title=meta_title,
        environment=environment,
        analyst="Performance Engineering Architect",
        sla=sla,
    )
    html = render_comparison_html(payload)

    gng = payload.get("go_nogo") or {}
    vcode = str(gng.get("verdict") or "CONDITIONAL")
    verdict_ui = payload.get("verdict") or {}
    verdict_label = str(verdict_ui.get("label") or vcode)

    analysis: Dict[str, Any] = {
        "report_engine": "comparison_v2",
        "report_payload": payload,
        "executive_summary": {
            "verdict": verdict_label,
            "recommendation": gng.get("justification") or "",
            "traffic_signal": _traffic_for_verdict(vcode),
        },
        "go_nogo": gng,
        "meta": payload.get("meta"),
    }
    return html, analysis


def render_stored_v2_payload(payload: Dict[str, Any]) -> str:
    """Re-render HTML from a persisted report_payload (template/JS updates)."""
    return render_comparison_html(payload)


def compact_analysis_for_api(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """Omit large embedded payload from JSON responses; UI only needs ids + summary."""
    d = {k: v for k, v in analysis.items() if k != "report_payload"}
    d["has_report_payload"] = bool(analysis.get("report_payload"))
    return d

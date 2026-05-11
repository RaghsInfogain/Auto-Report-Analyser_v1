"""Heuristic root-cause delta helpers for comparative JMeter analysis."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import pandas as pd


def identify_rca_changes(t1_data: dict, t2_data: dict) -> List[dict]:
    """
    Produce RCA delta cards for the comparison report.
    t1_data / t2_data: 'kpis', 'error_analysis', 'throughput', 'transactions' (DataFrame), 'per_minute'
    """
    k1 = t1_data.get("kpis") or {}
    k2 = t2_data.get("kpis") or {}
    e1 = t1_data.get("error_analysis") or {}
    e2 = t2_data.get("error_analysis") or {}
    tp1 = t1_data.get("throughput") or {}
    tp2 = t2_data.get("throughput") or {}
    tx1 = t1_data.get("transactions")
    if not isinstance(tx1, pd.DataFrame):
        tx1 = pd.DataFrame()
    tx2 = t2_data.get("transactions")
    if not isinstance(tx2, pd.DataFrame):
        tx2 = pd.DataFrame()

    rcas: List[dict] = []

    def tx_p90(df: pd.DataFrame, label_substr: str) -> Optional[float]:
        if len(df) == 0 or "label" not in df.columns:
            return None
        m = df[df["label"].astype(str).str.contains(label_substr, case=False, na=False)]
        if len(m) == 0:
            return None
        return float(m["p90_rt"].max())

    t101_1 = tx_p90(tx1, "T101")
    t101_2 = tx_p90(tx2, "T101")

    if (k1.get("count_504") or 0) > 0 and (k2.get("count_504") or 0) == 0:
        rcas.append(
            {
                "rca_id": "RCA-ANALYTICS",
                "title": "Analytics / render thread pool saturation (504)",
                "confidence_pct": 88,
                "t1_status": "present",
                "t2_status": "resolved",
                "evidence_t1": f"504 count {k1.get('count_504', 0)}",
                "evidence_t2": f"504 count {k2.get('count_504', 0)}",
                "badge_color": "green",
            }
        )
    elif (k1.get("count_504") or 0) > 0:
        rcas.append(
            {
                "rca_id": "RCA-ANALYTICS",
                "title": "Analytics / render thread pool saturation (504)",
                "confidence_pct": 55,
                "t1_status": "present",
                "t2_status": "remains",
                "evidence_t1": f"504 count {k1.get('count_504', 0)}",
                "evidence_t2": f"504 count {k2.get('count_504', 0)}",
                "badge_color": "red",
            }
        )

    c404_1 = int(k1.get("count_404") or 0)
    c404_2 = int(k2.get("count_404") or 0)
    if c404_1 > 1000 and c404_2 < c404_1 * 0.3:
        rcas.append(
            {
                "rca_id": "RCA-ROUTING-ACCOUNT",
                "title": "Thread-unsafe session / Account URL routing",
                "confidence_pct": 75,
                "t1_status": "present",
                "t2_status": "resolved" if c404_2 == 0 else "partial",
                "evidence_t1": f"404 count {c404_1}",
                "evidence_t2": f"404 count {c404_2}",
                "badge_color": "green" if c404_2 == 0 else "amber",
            }
        )
    elif c404_1 > 100:
        rcas.append(
            {
                "rca_id": "RCA-ROUTING-ACCOUNT",
                "title": "Thread-unsafe session / Account URL routing",
                "confidence_pct": 50,
                "t1_status": "present",
                "t2_status": "remains",
                "evidence_t1": f"404 count {c404_1}",
                "evidence_t2": f"404 count {c404_2}",
                "badge_color": "red",
            }
        )

    st1 = str(tp1.get("scalability_type") or "")
    st2 = str(tp2.get("scalability_type") or "")
    if st1 == "negative" and st2 == "linear":
        rcas.append(
            {
                "rca_id": "RCA-THREAD-POOL",
                "title": "Application server thread pool / capacity",
                "confidence_pct": 70,
                "t1_status": "present",
                "t2_status": "resolved",
                "evidence_t1": f"T1 scalability {st1}",
                "evidence_t2": f"T2 scalability {st2}",
                "badge_color": "green",
            }
        )

    if t101_1 is not None and t101_2 is not None and t101_1 > 10000 and t101_2 < 3000:
        rcas.append(
            {
                "rca_id": "RCA-METADATA-SERIAL",
                "title": "Serial metadata API fan-out",
                "confidence_pct": 72,
                "t1_status": "present",
                "t2_status": "resolved",
                "evidence_t1": f"T101-like P90 ≈ {t101_1:.0f} ms",
                "evidence_t2": f"T101-like P90 ≈ {t101_2:.0f} ms",
                "badge_color": "green",
            }
        )

    pm1 = t1_data.get("per_minute")
    if not isinstance(pm1, pd.DataFrame):
        pm1 = pd.DataFrame()
    db_pool_status = "unclear"
    if len(pm1) > 5 and "mean_rt" in pm1.columns and "max_threads" in pm1.columns:
        mrt = pm1["mean_rt"].astype(float)
        mu = float(mrt.mean())
        sd = float(mrt.std())
        vu = pm1["max_threads"].astype(float)
        if mu > 1e-6 and (sd / mu) > 0.5 and float(vu.std()) < float(vu.mean()) * 0.15:
            db_pool_status = "present"
    if db_pool_status == "present":
        jitter2 = 0.0
        pm2 = t2_data.get("per_minute")
        if isinstance(pm2, pd.DataFrame) and len(pm2) > 5:
            m2 = pm2["mean_rt"].astype(float)
            jitter2 = float(m2.std() / max(m2.mean(), 1e-6))
        rcas.append(
            {
                "rca_id": "RCA-DB-CONNECTION",
                "title": "Database connection pool / wait spikes",
                "confidence_pct": 45,
                "t1_status": "present",
                "t2_status": "resolved" if jitter2 < 0.35 else "partial",
                "evidence_t1": "High RT coefficient vs flat VU (T1)",
                "evidence_t2": f"Post-fix minute RT CoV ≈ {jitter2:.2f}",
                "badge_color": "green" if jitter2 < 0.35 else "amber",
            }
        )

    wf1 = tx1[tx1["label"].astype(str).str.match(r"^T31[3-6]_", na=False)] if len(tx1) else tx1
    wf2 = tx2[tx2["label"].astype(str).str.match(r"^T31[3-6]_", na=False)] if len(tx2) else tx2
    p90_wf_1 = float(wf1["p90_rt"].max()) if len(wf1) else None
    p90_wf_2 = float(wf2["p90_rt"].max()) if len(wf2) else None
    if p90_wf_1 and p90_wf_2 and p90_wf_1 > 10000:
        st = "resolved" if p90_wf_2 < 3000 else "partial" if p90_wf_2 < p90_wf_1 else "remains"
        rcas.append(
            {
                "rca_id": "RCA-WORKFLOW-IO",
                "title": "Workflow engine blocking DB I/O",
                "confidence_pct": 60,
                "t1_status": "present",
                "t2_status": st,
                "evidence_t1": f"Workflow tx P90 up to {p90_wf_1:.0f} ms (T1)",
                "evidence_t2": f"Workflow tx P90 up to {p90_wf_2:.0f} ms (T2)",
                "badge_color": "green" if st == "resolved" else "amber" if st == "partial" else "red",
            }
        )

    lead_new = False
    if len(tx2):
        new_labels = set(tx2["label"].astype(str)) - set(tx1["label"].astype(str)) if len(tx1) else set()
        for lab in new_labels:
            if "lead" in lab.lower():
                lead_new = True
                break
    err_tx2 = e2.get("errors_by_transaction")
    if isinstance(err_tx2, pd.DataFrame) and len(err_tx2):
        for _, r in err_tx2.iterrows():
            if "lead" in str(r.get("label", "")).lower():
                lead_new = True

    if c404_2 > 0:
        et = tx2[tx2["label"].astype(str).str.contains("Lead", case=False, na=False)] if len(tx2) else pd.DataFrame()
        if len(et) and float(et["error_rate"].max()) > 0.5:
            lead_new = True

    if lead_new:
        rcas.append(
            {
                "rca_id": "RCA-NEW-LEAD",
                "title": "NEW: Lead URL routing / configuration",
                "confidence_pct": 65,
                "t1_status": "present",
                "t2_status": "new",
                "evidence_t1": "No Lead-tier failures isolated in T1",
                "evidence_t2": f"404 / errors on Lead-like endpoints (T2 404={c404_2})",
                "badge_color": "red",
            }
        )

    order = {"resolved": 0, "partial": 1, "remains": 2, "new": 3}
    rcas.sort(key=lambda x: order.get(str(x.get("t2_status")), 9))
    return rcas

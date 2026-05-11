"""Compare KPIs, transactions, bands, and errors between two runs."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

from analyser import rca

__all__ = ["ComparisonEngine"]


def _pct_delta(t1: float, t2: float) -> float:
    if abs(t1) < 1e-12:
        return 100.0 if abs(t2) > 1e-12 else 0.0
    return 100.0 * (t2 - t1) / abs(t1)


class ComparisonEngine:
    def compare_overall_kpis(self, kpi1: dict, kpi2: dict) -> List[dict]:
        defs: List[Tuple[str, str, str, bool]] = [
            ("error_rate_pct", "Error rate", "%", True),
            ("mean_rt", "Mean RT", "ms", True),
            ("median_rt", "Median RT", "ms", True),
            ("p90_rt", "P90 RT", "ms", True),
            ("p95_rt", "P95 RT", "ms", True),
            ("p99_rt", "P99 RT", "ms", True),
            ("overall_tps", "Overall TPS", "tps", False),
            ("count_404", "HTTP 404 count", "count", True),
            ("count_504", "HTTP 504 count", "count", True),
            ("apdex", "Apdex", "", False),
        ]
        out: List[dict] = []
        for mk, label, unit, lower_better in defs:
            t1 = float(kpi1.get(mk) or 0)
            t2 = float(kpi2.get(mk) or 0)
            d_abs = t2 - t1
            if mk == "apdex":
                d_pct = 100.0 * (t2 - t1)
                improved = t2 > t1 + 1e-12
            else:
                d_pct = _pct_delta(t1, t2)
                improved = (t2 < t1 - 1e-12) if lower_better else (t2 > t1 + 1e-12)
            out.append(
                {
                    "metric": mk,
                    "label": label,
                    "t1_value": t1,
                    "t2_value": t2,
                    "delta_absolute": float(d_abs),
                    "delta_pct": float(d_pct),
                    "improved": bool(improved),
                    "significance": "major" if abs(d_pct) >= 20 else "minor",
                    "unit": unit,
                }
            )
        return out

    def compare_transactions(self, tx1: pd.DataFrame, tx2: pd.DataFrame) -> pd.DataFrame:
        if len(tx1) == 0 and len(tx2) == 0:
            return pd.DataFrame()
        a = (
            tx1.rename(
                columns={
                    "p90_rt": "p90_t1",
                    "error_rate": "err_t1",
                    "apdex": "apdex_t1",
                    "sla_pass": "sla_t1",
                    "error_count": "ec_t1",
                }
            )[["label", "p90_t1", "err_t1", "apdex_t1", "sla_t1", "ec_t1"]].copy()
            if len(tx1)
            else pd.DataFrame(columns=["label", "p90_t1", "err_t1", "apdex_t1", "sla_t1", "ec_t1"])
        )
        b = (
            tx2.rename(
                columns={
                    "p90_rt": "p90_t2",
                    "error_rate": "err_t2",
                    "apdex": "apdex_t2",
                    "sla_pass": "sla_t2",
                    "error_count": "ec_t2",
                }
            )[["label", "p90_t2", "err_t2", "apdex_t2", "sla_t2", "ec_t2"]].copy()
            if len(tx2)
            else pd.DataFrame(columns=["label", "p90_t2", "err_t2", "apdex_t2", "sla_t2", "ec_t2"])
        )
        m = a.merge(b, on="label", how="outer")
        for c in ["p90_t1", "err_t1", "apdex_t1", "p90_t2", "err_t2", "apdex_t2", "ec_t1", "ec_t2", "sla_t1", "sla_t2"]:
            if c not in m.columns:
                m[c] = np.nan

        def d_p90(row: pd.Series) -> float:
            if pd.isna(row["p90_t1"]) or pd.isna(row["p90_t2"]):
                return 0.0
            return float(row["p90_t2"] - row["p90_t1"])

        m["delta_p90"] = m.apply(d_p90, axis=1)

        def d_pct(row: pd.Series) -> float:
            if pd.isna(row["p90_t1"]) or row["p90_t1"] == 0:
                return 0.0 if pd.isna(row["p90_t2"]) else 100.0
            if pd.isna(row["p90_t2"]):
                return 0.0
            return 100.0 * (row["p90_t2"] - row["p90_t1"]) / abs(row["p90_t1"])

        m["delta_p90_pct"] = m.apply(d_pct, axis=1)
        m["delta_err"] = m["err_t2"].fillna(0) - m["err_t1"].fillna(0)
        m["delta_apdex"] = m["apdex_t2"].fillna(0) - m["apdex_t1"].fillna(0)
        m["sla_t1_pass"] = m["sla_t1"].map(lambda x: "PASS" if x is True else "FAIL" if x is False else "—")
        m["sla_t2_pass"] = m["sla_t2"].map(lambda x: "PASS" if x is True else "FAIL" if x is False else "—")

        def status(row: pd.Series) -> str:
            only1 = pd.isna(row["p90_t2"]) and not pd.isna(row["p90_t1"])
            only2 = pd.isna(row["p90_t1"]) and not pd.isna(row["p90_t2"])
            if only1:
                return "baseline_only"
            if only2:
                return "current_only"
            e1 = float(row["err_t1"] or 0)
            e2 = float(row["err_t2"] or 0)
            dp = float(row["delta_p90_pct"])
            if e1 > 0.01 and e2 <= 0.0001:
                return "resolved"
            if row["sla_t1"] is False and row["sla_t2"] is True:
                return "fixed"
            if dp < -50:
                return "major_gain"
            if dp < -20:
                return "improved"
            if e1 < 0.01 and e2 > 0.01:
                return "new_failure"
            if dp > 20:
                return "regressed"
            if abs(dp) <= 20 and e2 <= max(e1, 0.01):
                return "stable"
            return "regressed"

        m["change_status"] = m.apply(status, axis=1)
        return m.sort_values("label").reset_index(drop=True)

    def compare_bands(self, band1: pd.DataFrame, band2: pd.DataFrame) -> pd.DataFrame:
        if len(band1) == 0 and len(band2) == 0:
            return pd.DataFrame()
        a = band1.copy()
        b = band2.copy()
        a = a.rename(columns=lambda c: f"{c}_t1" if c != "load_band" else c)
        b = b.rename(columns=lambda c: f"{c}_t2" if c != "load_band" else c)
        m = a.merge(b, on="load_band", how="outer")
        for col in ["mean_rt", "median_rt", "p75_rt", "p90_rt", "p95_rt", "error_rate", "error_count", "tps_mean", "tps_cov"]:
            c1, c2 = f"{col}_t1", f"{col}_t2"
            if c1 in m.columns and c2 in m.columns:
                m[f"delta_{col}"] = m[c2].fillna(0) - m[c1].fillna(0)
        return m

    def compare_errors(self, err1: dict, err2: dict) -> dict:
        e1t = err1.get("errors_by_transaction")
        e2t = err2.get("errors_by_transaction")
        l1 = set(e1t["label"].astype(str)) if isinstance(e1t, pd.DataFrame) and len(e1t) else set()
        l2 = set(e2t["label"].astype(str)) if isinstance(e2t, pd.DataFrame) and len(e2t) else set()
        resolved = sorted(l1 - l2)
        new = sorted(l2 - l1)
        persist = sorted(l1 & l2)
        return {
            "t1_total": int(err1.get("total_errors") or 0),
            "t2_total": int(err2.get("total_errors") or 0),
            "client_4xx_delta": int(err2.get("client_4xx_count") or 0) - int(err1.get("client_4xx_count") or 0),
            "server_5xx_delta": int(err2.get("server_5xx_count") or 0) - int(err1.get("server_5xx_count") or 0),
            "connection_delta": int(err2.get("connection_count") or 0) - int(err1.get("connection_count") or 0),
            "resolved_error_types": {"labels_cleared": resolved[:50]},
            "new_error_types": {"labels_new": new[:50]},
            "persisting_errors": {"labels": persist[:50]},
        }

    def identify_rca_changes(self, t1_data: Dict[str, Any], t2_data: Dict[str, Any]) -> List[dict]:
        return rca.identify_rca_changes(t1_data, t2_data)

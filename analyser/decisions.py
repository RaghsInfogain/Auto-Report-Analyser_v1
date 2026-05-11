"""GO / CONDITIONAL / NO-GO decision engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd


@dataclass
class SLAConfig:
    sla_error: float = 1.0  # percent
    sla_p90: float = 3000.0  # ms
    sla_p95: float = 5000.0  # ms
    sla_mean_rt_ms: float = 2000.0  # mean RT target for grading + heatmap (green cap)
    throughput_target: float = 100.0  # req/s for scalability pillar
    availability_target: float = 99.0  # percent
    sla_compliance_target: float = 95.0  # transaction SLA pass % for UX pillar


def _no_critical_tx(tx_df: pd.DataFrame, run_suffix: str = "_t2") -> bool:
    if len(tx_df) == 0:
        return True
    col = "status" if "status" in tx_df.columns else None
    if col is None:
        p90_col = f"p90{run_suffix}" if f"p90{run_suffix}" in tx_df.columns else "p90_t2"
        if p90_col not in tx_df.columns:
            return True
        er_col = f"err{run_suffix}" if f"err{run_suffix}" in tx_df.columns else "err_t2"
        if er_col not in tx_df.columns:
            return True
        crit = (tx_df[er_col].fillna(0) > 10) | (tx_df[p90_col].fillna(0) > 30000)
        return not bool(crit.any())
    return not bool((tx_df[col] == "critical").any())


def _no_warning_tx(tx_df: pd.DataFrame) -> bool:
    if len(tx_df) == 0 or "status" not in tx_df.columns:
        return True
    return not bool((tx_df["status"].isin(["warning", "critical"])).any())


class GoNoGoEngine:
    def evaluate(
        self,
        kpis: dict,
        tx_df: pd.DataFrame,
        band_df: pd.DataFrame,
        sla: SLAConfig,
        compare_tx: Optional[pd.DataFrame] = None,
    ) -> dict:
        """
        compare_tx: merged comparison frame (optional) — use T2 columns if present for NO_CRITICAL.
        """
        tx_for_crit = compare_tx if compare_tx is not None and len(compare_tx) else tx_df
        if compare_tx is not None and len(compare_tx) and "p90_t2" in compare_tx.columns:
            crit_mask = (compare_tx["err_t2"].fillna(0) > 10) | (compare_tx["p90_t2"].fillna(0) > 30000)
            no_critical = not bool(crit_mask.any())
        else:
            no_critical = _no_critical_tx(tx_for_crit if "status" in tx_for_crit.columns else tx_df)

        warn_mask = pd.Series([False])
        if compare_tx is not None and len(compare_tx) and "p90_t2" in compare_tx.columns:
            warn_mask = (compare_tx["err_t2"].fillna(0) > 2) | (compare_tx["p90_t2"].fillna(0) > 10000)
            no_warning = not bool(warn_mask.any())
        else:
            no_warning = _no_warning_tx(tx_df) if len(tx_df) and "status" in tx_df.columns else True

        checks: List[Tuple[str, str, Callable[[dict, SLAConfig], bool], str, int]] = [
            ("ERR_RATE", "Overall error rate < SLA", lambda k, s: k["error_rate_pct"] < s.sla_error, "NO_GO", 30),
            ("P90_SLA", "P90 response time < SLA", lambda k, s: k["p90_rt"] < s.sla_p90, "NO_GO", 25),
            ("NO_504", "Zero HTTP 504 gateway timeouts", lambda k, s: k["count_504"] == 0, "NO_GO", 20),
            ("NO_CRITICAL", "No critical transactions (T2)", lambda k, s: no_critical, "NO_GO", 15),
            ("P95_SLA", "P95 response time < SLA", lambda k, s: k["p95_rt"] < s.sla_p95, "CONDITIONAL", 5),
            ("NO_WARNING", "No warning-tier transactions (T2)", lambda k, s: no_warning, "CONDITIONAL", 5),
        ]

        passed: List[str] = []
        failed: List[str] = []
        blockers: List[dict] = []
        conditional: List[dict] = []
        score = 0.0
        total_w = sum(c[4] for c in checks)

        for cid, label, fn, fail_verdict, weight in checks:
            ok = False
            try:
                ok = bool(fn(kpis, sla))
            except Exception:
                ok = False
            entry = {"id": cid, "label": label, "weight": weight, "fail_verdict": fail_verdict, "pass": ok}
            if ok:
                passed.append(cid)
                score += weight
            else:
                failed.append(cid)
                if fail_verdict == "NO_GO":
                    blockers.append(entry)
                else:
                    conditional.append(entry)

        score_pct = round(100.0 * score / total_w, 1) if total_w else 0.0

        if blockers:
            verdict = "NO_GO"
        elif conditional:
            verdict = "CONDITIONAL"
        else:
            verdict = "GO"

        justification = self._justify(verdict, kpis, sla, passed, failed, blockers, conditional)

        cap = self._capacity_tiers(band_df, kpis, sla)

        return {
            "verdict": verdict,
            "score": score_pct,
            "passed": passed,
            "failed": failed,
            "no_go_blockers": blockers,
            "conditional_items": conditional,
            "justification": justification,
            "capacity_tiers": cap,
        }

    def _capacity_tiers(self, band_df: pd.DataFrame, kpis: dict, sla: SLAConfig) -> dict:
        if band_df is None or len(band_df) == 0:
            mv = float(kpis.get("max_vu") or 0)
            return {
                "proven_safe": {"vu": 0, "p90": 0.0, "error_rate": 0.0, "verdict_notes": "n/a"},
                "marginal": {"vu": int(mv), "p90": float(kpis.get("p90_rt") or 0), "error_rate": float(kpis.get("error_rate_pct") or 0), "verdict_notes": "single-bucket estimate"},
                "observed_peak": {"vu": int(mv), "p90": float(kpis.get("p90_rt") or 0), "error_rate": float(kpis.get("error_rate_pct") or 0), "verdict_notes": "overall"},
            }

        b = band_df.copy()
        if "p90_rt" not in b.columns:
            return self._capacity_tiers(pd.DataFrame(), kpis, sla)

        def ok_row(r: pd.Series) -> bool:
            return float(r.get("p90_rt") or 0) < sla.sla_p90 and float(r.get("error_rate") or 100) < sla.sla_error

        safe_rows = b[b.apply(ok_row, axis=1)]
        proven_vu = int(safe_rows["load_band"].str.extract(r"(\d+)").astype(float).max().max() or 0) if len(safe_rows) else 0
        if len(safe_rows):
            last_safe = safe_rows.iloc[-1]
            ps = {
                "vu": proven_vu,
                "p90": float(last_safe["p90_rt"]),
                "error_rate": float(last_safe["error_rate"]),
                "verdict_notes": "Highest band meeting SLA gates",
            }
        else:
            ps = {"vu": 0, "p90": 0.0, "error_rate": float(kpis.get("error_rate_pct") or 0), "verdict_notes": "No band fully met SLA — review bands"}

        last = b.iloc[-1]
        return {
            "proven_safe": ps,
            "marginal": {
                "vu": proven_vu,
                "p90": float(last["p90_rt"]),
                "error_rate": float(last["error_rate"]),
                "verdict_notes": "Top band stress posture",
            },
            "observed_peak": {
                "vu": int(float(kpis.get("max_vu") or 0)),
                "p90": float(kpis.get("p90_rt") or 0),
                "error_rate": float(kpis.get("error_rate_pct") or 0),
                "verdict_notes": "Run-wide peak concurrency",
            },
        }

    def _justify(
        self,
        verdict: str,
        kpis: dict,
        sla: SLAConfig,
        passed: List[str],
        failed: List[str],
        blockers: List[dict],
        conditional: List[dict],
    ) -> str:
        parts = [
            f"Error rate {kpis.get('error_rate_pct', 0):.2f}% vs SLA {sla.sla_error:.2f}%. ",
            f"P90 {kpis.get('p90_rt', 0):.0f} ms vs SLA {sla.sla_p90:.0f} ms. ",
            f"504 count {kpis.get('count_504', 0)}. ",
        ]
        if verdict == "GO":
            parts.append("All weighted NO-GO gates pass; CONDITIONAL checks pass. Production promotion is supported by this test slice.")
        elif verdict == "CONDITIONAL":
            parts.append(
                f"Remaining gaps: {', '.join(x['id'] for x in conditional) or 'conditional SLA'}. "
                "Address before declaring full production readiness at peak VU."
            )
        else:
            parts.append(
                "Blockers: "
                + ", ".join(x["id"] for x in blockers)
                + ". Further remediation and re-test required."
            )
        return "".join(parts)

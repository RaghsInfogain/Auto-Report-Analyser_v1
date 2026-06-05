"""GO / CONDITIONAL / NO-GO verdict — v2."""
from __future__ import annotations

from typing import Dict, List


class VerdictEngine:
    def evaluate(self, cwv: dict, opportunities: dict, sla: dict) -> dict:
        total = max(1, cwv.get("total_pages") or 1)
        failed: List[str] = []
        passed: List[str] = []
        warn: List[str] = []
        sla_perf = int(sla.get("perf_score") or 85)
        sla_tbt = float(sla.get("tbt") or 200)
        lcp_d = cwv.get("lcp_distribution") or {}
        tbt_d = cwv.get("tbt_distribution") or {}
        cls_d = cwv.get("cls_distribution") or {}
        avg_perf = int(cwv.get("avg_perf_score") or 0)
        avg_tbt = float(cwv.get("avg_tbt") or 0)
        ujs = opportunities.get("unused_js") or {}

        if avg_perf < sla_perf:
            failed.append("Avg score below SLA")
        else:
            passed.append(f"Avg performance score meets SLA (≥{sla_perf})")

        if lcp_d.get("good", 0) == 0:
            failed.append("Zero pages pass LCP")
        else:
            passed.append("At least one page passes LCP Good")

        if tbt_d.get("good", 0) == 0:
            failed.append("Zero pages pass TBT")
        else:
            passed.append("At least one page passes TBT Good")

        if avg_tbt > sla_tbt * 10:
            failed.append("TBT critically over SLA")

        if lcp_d.get("poor", 0) / total > 0.5:
            warn.append(">50% pages in poor LCP bucket")
        if cls_d.get("poor", 0) > 0:
            warn.append("Poor CLS on some pages")
        if float(ujs.get("avg_savings_kb") or 0) > 300:
            warn.append("Excessive unused JS")

        if failed:
            verdict, color, icon = "NO_GO", "red", "⛔"
            score = min(35, max(0, avg_perf))
        elif warn:
            verdict, color, icon = "CONDITIONAL", "amber", "~"
            score = min(70, max(40, avg_perf))
        else:
            verdict, color, icon = "GO", "green", "✓"
            score = max(80, min(100, avg_perf))

        if verdict == "GO":
            justification = (
                f"Average Lighthouse performance score is {avg_perf}/100 (target ≥{sla_perf}). "
                f"{lcp_d.get('good', 0)} of {total} pages meet LCP Good; {tbt_d.get('good', 0)} meet TBT Good. "
                "Sustain budgets via CI regressions and synthetic monitoring."
            )
        elif verdict == "CONDITIONAL":
            justification = (
                f"Mixed readiness: avg score {avg_perf}/100. "
                f"{'; '.join(warn)}. "
                f"LCP distribution — good {lcp_d.get('good', 0)}, ni {lcp_d.get('ni', 0)}, poor {lcp_d.get('poor', 0)}."
            )
        else:
            justification = (
                f"Blocking issues: {'; '.join(failed)}. "
                f"Avg TBT {avg_tbt:.0f} ms vs {sla_tbt:.0f} ms SLA multiplier; LCP good pages {lcp_d.get('good', 0)}/{total}."
            )

        capacity = (
            "Operate at current traffic only after clearing NO-GO criteria; staged rollouts with canary LCP/TBT checks."
            if verdict == "NO_GO"
            else "Maintain performance guardrails; scale marketing traffic once COND/Green KPIs hold for two consecutive releases."
        )

        return {
            "verdict": verdict,
            "verdict_color": color,
            "verdict_icon": icon,
            "score": int(score),
            "failed_criteria": failed + ([] if verdict != "CONDITIONAL" else warn),
            "passed_criteria": passed if verdict != "NO_GO" else [p for p in passed if p],
            "justification": justification,
            "capacity_assessment": capacity,
        }

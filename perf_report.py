#!/usr/bin/env python3
"""CLI: generate self-contained JMeter A/B comparison HTML from two CSV/JTL files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyser.decisions import SLAConfig
from analyser.loader import JMeterLoader
from renderer.html_report import build_report_payload, render_comparison_html


def main() -> int:
    p = argparse.ArgumentParser(description="JMeter comparison HTML report (baseline vs current)")
    p.add_argument("--baseline", required=True, help="Baseline run CSV path (T1)")
    p.add_argument("--current", required=True, help="Current run CSV path (T2)")
    p.add_argument("--run-id-1", default="Run #1", help="Label for baseline")
    p.add_argument("--run-id-2", default="Run #2", help="Label for current")
    p.add_argument("--title", default="Performance Test Comparison Report", help="Report title")
    p.add_argument("--environment", default="—", help="Environment description")
    p.add_argument("--analyst", default="Performance Engineering Architect", help="Analyst name")
    p.add_argument("--sla-error", type=float, default=1.0, help="Max error rate %% for GO gate")
    p.add_argument("--sla-p90", type=float, default=3000.0, help="P90 SLA ms")
    p.add_argument("--sla-p95", type=float, default=5000.0, help="P95 SLA ms (conditional)")
    p.add_argument("--out", required=True, help="Output HTML path")
    args = p.parse_args()

    loader = JMeterLoader()
    df1 = loader.load(str(Path(args.baseline).resolve()), args.run_id_1)
    df2 = loader.load(str(Path(args.current).resolve()), args.run_id_2)

    sla = SLAConfig(sla_error=args.sla_error, sla_p90=args.sla_p90, sla_p95=args.sla_p95)
    payload = build_report_payload(
        df1,
        df2,
        run_id_1=args.run_id_1,
        run_id_2=args.run_id_2,
        meta_title=args.title,
        environment=args.environment,
        analyst=args.analyst,
        sla=sla,
    )
    html = render_comparison_html(payload)
    out = Path(args.out).resolve()
    out.write_text(html, encoding="utf-8")
    print(f"Wrote {out} ({len(html) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

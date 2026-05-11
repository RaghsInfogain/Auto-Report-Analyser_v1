# JMeter performance comparison report (CLI)

Production-style **baseline vs current** analysis from two JMeter CSV/JTL exports. Produces a **single self-contained HTML** file (Google Fonts + Chart.js CDN only) suitable for executives and performance audits.

## Installation

```bash
cd /path/to/Auto-Report-Analyser_v1
pip install -r requirements.txt
```

## Quick start

```bash
python tests/fixtures/generate_sample.py
python perf_report.py --baseline t1_sample.csv --current t2_sample.csv \
  --run-id-1 "Test Run 1" --run-id-2 "Test Run 2" --out sample_output.html
```

Open `sample_output.html` in any browser (no server).

## CLI (`perf_report.py`)

| Flag | Description |
|------|-------------|
| `--baseline` | Path to baseline (T1) CSV |
| `--current` | Path to current (T2) CSV |
| `--run-id-1` | Display label for baseline |
| `--run-id-2` | Display label for current |
| `--title` | Report title (default: Performance Test Comparison Report) |
| `--environment` | Environment string (e.g. hostname/cluster) |
| `--analyst` | Prepared-by name |
| `--sla-error` | Max error rate % for GO gate (default `1.0`) |
| `--sla-p90` | P90 SLA in ms (default `3000`) |
| `--sla-p95` | P95 threshold for conditional gate (default `5000`) |
| `--out` | Output HTML path |

**Example — strict SLA**

```bash
python perf_report.py --baseline run_a.csv --current run_b.csv \
  --run-id-1 "UAT 29 Apr" --run-id-2 "UAT 30 Apr" \
  --environment "crm-uat-app01" \
  --sla-error 0.5 --sla-p90 2500 \
  --out comparison_uat.html
```

## Output

- **Panels**: Overview & Verdict · KPI Comparison · Response Time · Throughput · Error Analysis · Transaction Scorecard · Root Cause Delta  
- **Verdict**: `GO` / `CONDITIONAL` / `NO_GO` from weighted gates in `analyser/decisions.py`  
- **Charts**: All read from embedded `REPORT_DATA` JSON (no `fetch()`)

## Tests

```bash
pytest tests/ -v
```

## Modules

| Path | Role |
|------|------|
| `analyser/loader.py` | CSV load, bands, `is_transaction`, `err_type` |
| `analyser/kpis.py` | Overall / minute / band / transaction KPIs, heatmap, Apdex, throughput |
| `analyser/comparator.py` | Metric deltas, transaction join, RCA hook |
| `analyser/rca.py` | Heuristic RCA delta list |
| `analyser/decisions.py` | `GoNoGoEngine` + `SLAConfig` |
| `renderer/html_report.py` | Payload + Jinja render + JSON injection |
| `renderer/charts.py` | Chart.js default snippet |
| `renderer/templates/report.html.jinja2` | Report shell |

## Sample output

After running the quick start, `sample_output.html` is typically **under 100 KB** for the synthetic CSVs; real runs stay bounded by per-minute downsampling (~500 points/side).

## Confidentiality

Reports are static HTML; treat output files like any test artefact containing URLs and timing data.

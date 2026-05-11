import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from analyser.comparator import ComparisonEngine
from analyser.decisions import GoNoGoEngine, SLAConfig
from analyser.kpis import KPIEngine
from analyser.loader import JMeterLoader


def _df_minutes(elapsed_list, success=True, vu=10, code="200"):
    base = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp() * 1000)
    rows = []
    ts = base
    for e in elapsed_list:
        rows.append(
            {
                "timeStamp": ts,
                "elapsed": e,
                "label": "T001_X",
                "responseCode": code,
                "success": success,
                "allThreads": vu,
                "Latency": int(e * 0.8),
                "Connect": 1,
                "bytes": 100,
                "sentBytes": 10,
            }
        )
        ts += 1000
    return pd.DataFrame(rows)


def test_apdex_all_satisfied():
    df = _df_minutes([100, 500, 1000])
    k = KPIEngine().overall_kpis(df)
    assert abs(k["apdex"] - 1.0) < 1e-9


def test_apdex_all_frustrated():
    df = _df_minutes([15000, 16000, 17000])
    k = KPIEngine().overall_kpis(df)
    assert abs(k["apdex"] - 0.0) < 1e-9


def test_apdex_mixed():
    df = _df_minutes([1000] * 5 + [3500] * 5)
    k = KPIEngine().overall_kpis(df)
    assert abs(k["apdex"] - 0.75) < 1e-9


def test_go_verdict():
    n = 200
    df = pd.DataFrame(
        {
            "timeStamp": np.arange(n) * 1000 + 1_700_000_000_000,
            "elapsed": [200] * n,
            "label": ["T001_A"] * n,
            "responseCode": ["200"] * n,
            "success": [True] * n,
            "allThreads": [10] * n,
            "Latency": [150] * n,
            "Connect": [1] * n,
            "bytes": [100] * n,
            "sentBytes": [10] * n,
        }
    )
    k = KPIEngine().overall_kpis(df)
    tx = KPIEngine().per_transaction_kpis(df)
    b = KPIEngine().per_band_kpis(df)
    g = GoNoGoEngine().evaluate(k, tx, b, SLAConfig())
    assert g["verdict"] == "GO"


def test_no_go_verdict():
    n = 100
    df = pd.DataFrame(
        {
            "timeStamp": np.arange(n) * 1000 + 1_700_000_000_000,
            "elapsed": [200] * n,
            "label": ["T001_A"] * n,
            "responseCode": ["200"] * n,
            "success": [False] * n,
            "allThreads": [10] * n,
            "Latency": [150] * n,
            "Connect": [1] * n,
            "bytes": [100] * n,
            "sentBytes": [10] * n,
        }
    )
    k = KPIEngine().overall_kpis(df)
    tx = KPIEngine().per_transaction_kpis(df)
    b = KPIEngine().per_band_kpis(df)
    g = GoNoGoEngine().evaluate(k, tx, b, SLAConfig())
    assert g["verdict"] == "NO_GO"


def test_conditional_verdict():
    n = 500
    elapsed = [400] * int(n * 0.88) + [15000] * int(n * 0.12)
    assert len(elapsed) == n
    df = pd.DataFrame(
        {
            "timeStamp": np.arange(n) * 1000 + 1_700_000_000_000,
            "elapsed": elapsed,
            "label": ["T001_A"] * n,
            "responseCode": ["200"] * n,
            "success": [True] * n,
            "allThreads": [10] * n,
            "Latency": [200] * n,
            "Connect": [1] * n,
            "bytes": [100] * n,
            "sentBytes": [10] * n,
        }
    )
    k = KPIEngine().overall_kpis(df)
    tx = KPIEngine().per_transaction_kpis(df)
    b = KPIEngine().per_band_kpis(df)
    g = GoNoGoEngine().evaluate(k, tx, b, SLAConfig(sla_error=2.0, sla_p90=8000.0, sla_p95=4000.0))
    assert g["verdict"] in ("CONDITIONAL", "NO_GO")


def test_load_band_assignment():
    threads = pd.Series([25, 65])
    bands = pd.cut(
        threads.clip(lower=0),
        bins=JMeterLoader.LOAD_BINS,
        labels=JMeterLoader.LOAD_LABELS,
        include_lowest=True,
        right=True,
    )
    assert str(bands.iloc[0]) == "1–30"
    assert str(bands.iloc[1]) == "61–120"


def test_compare_transactions_resolved():
    t1 = pd.DataFrame(
        {
            "label": ["T1_X"],
            "n": [10],
            "mean_rt": [100.0],
            "median_rt": [100.0],
            "p75_rt": [100.0],
            "p90_rt": [200.0],
            "p95_rt": [200.0],
            "p99_rt": [200.0],
            "max_rt": [200.0],
            "error_rate": [50.0],
            "error_count": [5],
            "apdex": [0.5],
            "status": ["critical"],
            "sla_pass": [False],
        }
    )
    t2 = pd.DataFrame(
        {
            "label": ["T1_X"],
            "n": [10],
            "mean_rt": [100.0],
            "median_rt": [100.0],
            "p75_rt": [100.0],
            "p90_rt": [200.0],
            "p95_rt": [200.0],
            "p99_rt": [200.0],
            "max_rt": [200.0],
            "error_rate": [0.0],
            "error_count": [0],
            "apdex": [1.0],
            "status": ["healthy"],
            "sla_pass": [True],
        }
    )
    m = ComparisonEngine().compare_transactions(t1, t2)
    assert m.iloc[0]["change_status"] == "resolved"


def test_compare_transactions_regressed():
    t1 = pd.DataFrame(
        {
            "label": ["T1_X"],
            "n": [10],
            "mean_rt": [100.0],
            "median_rt": [100.0],
            "p75_rt": [100.0],
            "p90_rt": [1000.0],
            "p95_rt": [1100.0],
            "p99_rt": [1200.0],
            "max_rt": [1200.0],
            "error_rate": [0.0],
            "error_count": [0],
            "apdex": [1.0],
            "status": ["healthy"],
            "sla_pass": [True],
        }
    )
    t2 = pd.DataFrame(
        {
            "label": ["T1_X"],
            "n": [10],
            "mean_rt": [100.0],
            "median_rt": [100.0],
            "p75_rt": [100.0],
            "p90_rt": [2500.0],
            "p95_rt": [2600.0],
            "p99_rt": [2700.0],
            "max_rt": [2700.0],
            "error_rate": [0.0],
            "error_count": [0],
            "apdex": [1.0],
            "status": ["slow"],
            "sla_pass": [True],
        }
    )
    m = ComparisonEngine().compare_transactions(t1, t2)
    assert m.iloc[0]["change_status"] == "regressed"


def test_per_minute_tps():
    base = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp() * 1000)
    df = pd.DataFrame(
        {
            "timeStamp": [base + 100 * i for i in range(600)],
            "elapsed": [1] * 600,
            "label": ["x"] * 600,
            "responseCode": ["200"] * 600,
            "success": [True] * 600,
            "allThreads": [5] * 600,
            "Latency": [1] * 600,
            "Connect": [0] * 600,
            "bytes": [1] * 600,
            "sentBytes": [1] * 600,
        }
    )
    df["ts"] = pd.to_datetime(df["timeStamp"], unit="ms")
    df["minute"] = df["ts"].dt.floor("1min")
    pm = KPIEngine().per_minute_kpis(df)
    assert len(pm) >= 1
    assert abs(float(pm.iloc[0]["tps"]) - 10.0) < 0.15


def test_error_type_classification():
    from analyser.loader import _err_type_from_code

    assert _err_type_from_code("404") == "4xx"
    assert _err_type_from_code("504") == "5xx"


def test_rca_analytics_resolved():
    t1 = {"kpis": {"count_504": 5}, "error_analysis": {}, "throughput": {}, "transactions": pd.DataFrame(), "per_minute": pd.DataFrame()}
    t2 = {"kpis": {"count_504": 0}, "error_analysis": {}, "throughput": {}, "transactions": pd.DataFrame(), "per_minute": pd.DataFrame()}
    from analyser import rca as rca_mod

    rc = rca_mod.identify_rca_changes(t1, t2)
    assert any(x.get("rca_id") == "RCA-ANALYTICS" and x.get("t2_status") == "resolved" for x in rc)

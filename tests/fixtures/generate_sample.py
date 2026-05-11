#!/usr/bin/env python3
"""Generate synthetic JMeter CSVs for local testing."""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
import pandas as pd

COLUMNS = [
    "timeStamp",
    "elapsed",
    "label",
    "responseCode",
    "responseMessage",
    "threadName",
    "dataType",
    "success",
    "failureMessage",
    "bytes",
    "sentBytes",
    "grpThreads",
    "allThreads",
    "URL",
    "Filename",
    "Latency",
    "Encoding",
    "SampleCount",
    "ErrorCount",
    "Hostname",
    "IdleTime",
    "Connect",
]

RNG = random.Random(42)


def _row(ts: int, elapsed: int, label: str, code: str, ok: bool, vu: int) -> dict:
    lat = min(elapsed - 2, max(1, int(elapsed * 0.85)))
    return {
        "timeStamp": ts,
        "elapsed": elapsed,
        "label": label,
        "responseCode": code,
        "responseMessage": "OK" if ok else "Error",
        "threadName": f"tg 1-{vu}",
        "dataType": "text",
        "success": ok,
        "failureMessage": "" if ok else "bad",
        "bytes": 1200,
        "sentBytes": 200,
        "grpThreads": vu,
        "allThreads": vu,
        "URL": "http://x/",
        "Filename": "",
        "Latency": lat,
        "Encoding": "",
        "SampleCount": 1,
        "ErrorCount": 0 if ok else 1,
        "Hostname": "h1",
        "IdleTime": 0,
        "Connect": 5,
    }


def write_t1(path: Path) -> None:
    rows = []
    base = int(pd.Timestamp("2026-04-29 10:53:00", tz="UTC").timestamp() * 1000)
    ts = base
    # Approx 30 minutes synthetic
    for minute in range(30):
        vu = min(300, 20 + minute * 10)
        n = 40 + minute
        err_rate = 0.02 if vu < 60 else 0.025 if vu < 120 else min(0.05, 0.02 + (vu - 120) / 4000)
        mean_rt = 600 if vu < 60 else 1500 if vu < 120 else 4000 + vu * 30
        for _ in range(n):
            ok = RNG.random() > err_rate
            code = "200" if ok else ("504" if RNG.random() < 0.4 else "404")
            if ok:
                code = "200"
            elapsed = max(50, int(RNG.gauss(mean_rt, mean_rt * 0.25)))
            lbl = "T103_CustomerSearch" if not ok and code == "404" else "T101_GoToCustomer"
            rows.append(_row(ts, elapsed, lbl, code, ok, vu))
            ts += RNG.randint(100, 400)
    pd.DataFrame(rows, columns=COLUMNS).to_csv(path, index=False)


def write_t2(path: Path) -> None:
    rows = []
    base = int(pd.Timestamp("2026-04-30 19:03:00", tz="UTC").timestamp() * 1000)
    ts = base
    for minute in range(30):
        vu = min(300, 20 + minute * 10)
        n = 80 + minute * 2
        err_rate = 0.0 if vu < 60 else 0.001 if vu < 180 else min(0.015, 0.005 + vu / 20000)
        mean_rt = 350 if vu < 60 else 800 if vu < 180 else 1800
        for _ in range(n):
            ok = RNG.random() > err_rate
            code = "200"
            if not ok:
                code = "404"
                lbl = "T313_OpenLead"
            else:
                lbl = "T101_GoToCustomer"
            elapsed = max(40, int(RNG.gauss(mean_rt, mean_rt * 0.15)))
            rows.append(_row(ts, elapsed, lbl, code, ok, vu))
            ts += RNG.randint(80, 300)
    pd.DataFrame(rows, columns=COLUMNS).to_csv(path, index=False)


if __name__ == "__main__":
    out = Path(__file__).resolve().parents[2]
    t1 = out / "t1_sample.csv"
    t2 = out / "t2_sample.csv"
    write_t1(t1)
    write_t2(t2)
    print(f"Wrote {t1} and {t2}")

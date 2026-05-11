"""KPI computation for JMeter samples (vectorised pandas)."""

from __future__ import annotations

import numpy as np
import pandas as pd
from typing import List, Optional, Sequence, Tuple

from analyser.loader import JMeterLoader

SLA_P90_MS = 3000.0
SLA_ERROR_PCT = 1.0

# Latency decomposition (aligned with combined_load_report_analysis._latency_decomp_badge)
_LAT_INIT_APPQ_MS = 850.0
_LAT_DEV_APPQ = 0.25
_LAT_DEV_SAT = 0.40
_LAT_DEV_CRIT = 0.60
_LAT_TTFB_SAT_MS = 1200.0
_LAT_TTFB_CRIT_MS = 2000.0
_LAT_MEAN_RT_CRIT_MS = 8000.0


def _latency_decomp_diagnosis(
    ttfb_p90: float,
    mean_rt: float,
    band_index: int,
    prev_ttfb_p90: Optional[float],
) -> str:
    cur = float(ttfb_p90)
    mrt = float(mean_rt)
    rel_inc: Optional[float] = None
    if band_index > 0 and prev_ttfb_p90 is not None:
        prev = float(prev_ttfb_p90)
        rel_inc = (cur - prev) / max(prev, 1e-6)

    if (
        cur >= _LAT_TTFB_CRIT_MS
        or mrt > _LAT_MEAN_RT_CRIT_MS
        or (rel_inc is not None and rel_inc >= _LAT_DEV_CRIT)
    ):
        return "Critical"
    if cur >= _LAT_TTFB_SAT_MS or (rel_inc is not None and rel_inc >= _LAT_DEV_SAT):
        return "Saturating"
    if band_index == 0:
        return "App queuing" if cur > _LAT_INIT_APPQ_MS else "Healthy"
    if rel_inc is not None and rel_inc > _LAT_DEV_APPQ:
        return "App queuing"
    return "Healthy"

_RT_BUCKETS = [
    (0, 100, "0–100ms"),
    (100, 500, "100–500ms"),
    (500, 1000, "500ms–1s"),
    (1000, 3000, "1–3s"),
    (3000, 5000, "3–5s"),
    (5000, 10000, "5–10s"),
    (10000, 30000, "10–30s"),
    (30000, 60000, "30–60s"),
    (60000, 180000, "60–180s"),
    (180000, float("inf"), ">180s"),
]


def build_targeted_rt_heatmap_buckets(
    mean_target_ms: float = 2000.0,
    p90_target_ms: float = 3000.0,
) -> List[Tuple[float, float, str]]:
    """
    Bucket edges aligned with mean (green/amber to ~3s) and tail bands to 5s / 7s for P90-style SLA bands.
    Remaining coarse bins cover long tails; trim empty columns in the report layer.
    """
    tm = max(1000.0, float(mean_target_ms))
    _ = max(3000.0, float(p90_target_ms))  # reserved for future P90-shaped cuts
    raw_edges = [0.0, 100.0, 500.0, 1000.0, tm, 3000.0, 5000.0, 7000.0, 10000.0, 30000.0, 60000.0, 180000.0]
    edges = sorted({e for e in raw_edges if e >= 0})
    # De-duplicate adjacent equal after sort - use unique monotonic
    uniq: List[float] = []
    for e in edges:
        if not uniq or e > uniq[-1] + 1e-9:
            uniq.append(e)
    buckets: List[tuple] = []
    for i in range(len(uniq)):
        lo = uniq[i]
        hi = uniq[i + 1] if i + 1 < len(uniq) else float("inf")
        if hi == float("inf"):
            label = ">180s" if lo >= 180000 else f">{int(lo / 1000)}s"
            if lo >= 180000:
                label = ">180s"
            elif lo >= 60000:
                label = f"{int(lo / 1000)}–180s"
            else:
                label = f"{_fmt_ms_label(lo)}–∞"
        else:
            label = _bucket_label_pair(lo, hi)
        buckets.append((lo, hi, label))
    return buckets


def _fmt_ms_label(ms: float) -> str:
    if ms < 1000:
        return f"{int(ms)}ms"
    s = ms / 1000.0
    if abs(s - round(s)) < 0.05:
        return f"{int(round(s))}s"
    return f"{s:.1f}s"


def _bucket_label_pair(lo: float, hi: float) -> str:
    if hi <= 1000:
        return f"{int(lo)}–{int(hi)}ms"
    if lo < 1000 and hi <= 3000:
        return f"{int(lo)}ms–{_fmt_ms_label(hi)}"
    return f"{_fmt_ms_label(lo)}–{_fmt_ms_label(hi)}"


def _quantile_ms(s: pd.Series, q: float) -> float:
    if len(s) == 0:
        return 0.0
    return float(s.quantile(q))


def _apdex_scores(elapsed: pd.Series, t_ms: float = 3000.0) -> tuple[float, int, int, int]:
    e = elapsed.astype(float)
    sat = (e <= t_ms).sum()
    tol = ((e > t_ms) & (e <= 4 * t_ms)).sum()
    fru = (e > 4 * t_ms).sum()
    n = int(len(e))
    if n == 0:
        return 0.0, 0, 0, 0
    apdex = (sat + 0.5 * tol) / n
    return float(apdex), int(sat), int(tol), int(fru)


class KPIEngine:
    def _ensure_ts(self, df: pd.DataFrame) -> pd.DataFrame:
        if "ts" in df.columns:
            return df
        out = df.copy()
        ts = pd.to_datetime(out["timeStamp"], unit="ms", errors="coerce")
        if ts.isna().mean() > 0.5:
            ts = pd.to_datetime(out["timeStamp"], errors="coerce")
        out["ts"] = ts
        if "minute" not in out.columns:
            out["minute"] = out["ts"].dt.floor("1min")
        return out

    def overall_kpis(self, df: pd.DataFrame) -> dict:
        df = self._ensure_ts(df)
        n = len(df)
        if n == 0:
            return self._empty_overall()

        ts_min = df["ts"].min()
        ts_max = df["ts"].max()
        duration_sec = max((ts_max - ts_min).total_seconds(), 1e-6)
        duration_min = duration_sec / 60.0

        el = df["elapsed"].astype(float)
        succ = df["success"].astype(bool)
        err_count = int((~succ).sum())

        rc = df["responseCode"].astype(str)
        c404 = int(rc.eq("404").sum())
        c504 = int(rc.eq("504").sum())
        c502 = int(rc.eq("502").sum())
        nh = int(rc.str.contains("NoHttp", case=False, na=False).sum() | rc.str.contains("Connection", case=False, na=False).sum())

        apdex, _, _, _ = _apdex_scores(el, 3000)

        row = {
            "total_samples": int(n),
            "duration_min": float(duration_min),
            "duration_sec": float(duration_sec),
            "max_vu": float(df["allThreads"].max()),
            "min_vu": float(df["allThreads"].min()),
            "error_count": err_count,
            "error_rate_pct": float(100.0 * err_count / n),
            "count_404": c404,
            "count_504": c504,
            "count_502": c502,
            "count_nohttpresponse": nh,
            "mean_rt": float(el.mean()),
            "median_rt": float(el.median()),
            "p75_rt": _quantile_ms(el, 0.75),
            "p90_rt": _quantile_ms(el, 0.90),
            "p95_rt": _quantile_ms(el, 0.95),
            "p99_rt": _quantile_ms(el, 0.99),
            "max_rt": float(el.max()),
            "overall_tps": float(n / duration_sec),
            "apdex": apdex,
            "bandwidth_rx_mb": float(df["bytes"].astype(float).sum() / 1024 / 1024),
            "bandwidth_tx_mb": float(df["sentBytes"].astype(float).sum() / 1024 / 1024),
            "start_time": ts_min.isoformat() if pd.notna(ts_min) else "",
            "end_time": ts_max.isoformat() if pd.notna(ts_max) else "",
        }
        return row

    def _empty_overall(self) -> dict:
        return {
            "total_samples": 0,
            "duration_min": 0.0,
            "duration_sec": 0.0,
            "max_vu": 0.0,
            "min_vu": 0.0,
            "error_count": 0,
            "error_rate_pct": 0.0,
            "count_404": 0,
            "count_504": 0,
            "count_502": 0,
            "count_nohttpresponse": 0,
            "mean_rt": 0.0,
            "median_rt": 0.0,
            "p75_rt": 0.0,
            "p90_rt": 0.0,
            "p95_rt": 0.0,
            "p99_rt": 0.0,
            "max_rt": 0.0,
            "overall_tps": 0.0,
            "apdex": 0.0,
            "bandwidth_rx_mb": 0.0,
            "bandwidth_tx_mb": 0.0,
            "start_time": "",
            "end_time": "",
        }

    def per_minute_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._ensure_ts(df)
        if len(df) == 0:
            return pd.DataFrame(
                columns=[
                    "minute",
                    "max_threads",
                    "tps",
                    "mean_rt",
                    "median_rt",
                    "p90_rt",
                    "p95_rt",
                    "error_rate",
                    "error_count",
                    "count_404",
                    "count_504",
                ]
            )
        g = df.groupby("minute", dropna=False)
        sizes = g.size()
        err = (~df["success"]).groupby(df["minute"]).sum().reindex(sizes.index, fill_value=0)
        rc = df["responseCode"].astype(str)
        c404 = rc.eq("404").groupby(df["minute"]).sum().reindex(sizes.index, fill_value=0)
        c504 = rc.eq("504").groupby(df["minute"]).sum().reindex(sizes.index, fill_value=0)
        n_per = sizes.values.astype(float).clip(min=1)
        out = pd.DataFrame(
            {
                "minute": sizes.index,
                "max_threads": g["allThreads"].max().values,
                "tps": (sizes.values / 60.0),
                "mean_rt": g["elapsed"].mean().values,
                "median_rt": g["elapsed"].median().values,
                "p90_rt": g["elapsed"].quantile(0.9).values,
                "p95_rt": g["elapsed"].quantile(0.95).values,
                "error_count": err.values,
                "error_rate": 100.0 * err.values / n_per,
                "count_404": c404.values,
                "count_504": c504.values,
            }
        )
        return out.reset_index(drop=True)

    def per_band_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._ensure_ts(df)
        if len(df) == 0:
            return pd.DataFrame()
        if "load_band" not in df.columns:
            df = df.copy()
            df["load_band"] = pd.cut(
                df["allThreads"].clip(lower=0),
                bins=JMeterLoader.LOAD_BINS,
                labels=JMeterLoader.LOAD_LABELS,
                include_lowest=True,
                right=True,
            )

        df2 = df.dropna(subset=["load_band"])
        if len(df2) == 0:
            return pd.DataFrame()

        cov_rows = []
        for band, sub in df2.groupby("load_band", observed=True):
            mb = sub.groupby("minute", dropna=False).size()
            tps_vals = (mb / 60.0).astype(float)
            if len(tps_vals) == 0 or float(tps_vals.mean()) < 1e-12:
                cov = 0.0
            else:
                cov = float(tps_vals.std() / tps_vals.mean())

            cov_rows.append({"load_band": str(band), "tps_cov_tmp": cov})

        cov_map = {r["load_band"]: r["tps_cov_tmp"] for r in cov_rows}

        def band_block(sub: pd.DataFrame) -> dict:
            band = str(sub["load_band"].iloc[0])
            el = sub["elapsed"].astype(float)
            n = len(sub)
            err = int((~sub["success"]).sum())
            rc = sub["responseCode"].astype(str)
            apd, _, _, _ = _apdex_scores(el, 3000)
            return {
                "load_band": band,
                "samples": int(n),
                "mean_rt": float(el.mean()),
                "median_rt": float(el.median()),
                "p75_rt": _quantile_ms(el, 0.75),
                "p90_rt": _quantile_ms(el, 0.90),
                "p95_rt": _quantile_ms(el, 0.95),
                "p99_rt": _quantile_ms(el, 0.99),
                "max_rt": float(el.max()),
                "error_rate": float(100.0 * err / max(n, 1)),
                "error_count": err,
                "count_404": int(rc.eq("404").sum()),
                "count_504": int(rc.eq("504").sum()),
                "count_nohttpresponse": int(
                    rc.str.contains("NoHttp", case=False, na=False).sum()
                    + rc.str.contains("Connection", case=False, na=False).sum()
                ),
                "apdex": apd,
                "tps_mean": float(n / max((sub["ts"].max() - sub["ts"].min()).total_seconds(), 1e-6)),
                "tps_cov": cov_map.get(band, 0.0),
                "ttfb_median": float(sub["Latency"].astype(float).median()),
                "connect_median": float(sub["Connect"].astype(float).median()),
                "server_process_median": float((sub["elapsed"] - sub["Latency"]).astype(float).median()),
            }

        rows = [band_block(sub) for _, sub in df2.groupby("load_band", observed=True)]
        bands_order = list(JMeterLoader.LOAD_LABELS)
        frame = pd.DataFrame(rows)
        if len(frame) == 0:
            return frame
        frame["_ord"] = frame["load_band"].map({b: i for i, b in enumerate(bands_order)})
        frame = frame.sort_values("_ord").drop(columns=["_ord"])
        return frame.reset_index(drop=True)

    def per_transaction_kpis(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._ensure_ts(df)
        if "is_transaction" not in df.columns:
            df["is_transaction"] = True
        tx = df[df["is_transaction"]].copy()
        if len(tx) == 0:
            return pd.DataFrame(
                columns=[
                    "label",
                    "n",
                    "mean_rt",
                    "median_rt",
                    "p75_rt",
                    "p90_rt",
                    "p95_rt",
                    "p99_rt",
                    "max_rt",
                    "error_rate",
                    "error_count",
                    "apdex",
                    "status",
                    "sla_pass",
                ]
            )

        rows: list[dict] = []
        for label, sub in tx.groupby("label"):
            el = sub["elapsed"].astype(float)
            n = len(sub)
            err_c = int((~sub["success"]).sum())
            er = 100.0 * err_c / max(n, 1)
            p90 = _quantile_ms(el, 0.9)
            apd, _, _, _ = _apdex_scores(el, 3000)
            sla_pass = p90 <= SLA_P90_MS and er < SLA_ERROR_PCT
            if er > 10 or p90 > 30000:
                status = "critical"
            elif er > 2 or p90 > 10000:
                status = "warning"
            elif p90 > SLA_P90_MS:
                status = "slow"
            else:
                status = "healthy"

            rows.append(
                {
                    "label": str(label),
                    "n": int(n),
                    "mean_rt": float(el.mean()),
                    "median_rt": float(el.median()),
                    "p75_rt": _quantile_ms(el, 0.75),
                    "p90_rt": p90,
                    "p95_rt": _quantile_ms(el, 0.95),
                    "p99_rt": _quantile_ms(el, 0.99),
                    "max_rt": float(el.max()),
                    "error_rate": float(er),
                    "error_count": err_c,
                    "apdex": apd,
                    "status": status,
                    "sla_pass": bool(sla_pass),
                }
            )
        return pd.DataFrame(rows).sort_values("label").reset_index(drop=True)

    def error_analysis(self, df: pd.DataFrame) -> dict:
        df = self._ensure_ts(df)
        if "load_band" not in df.columns:
            df["load_band"] = pd.cut(
                df["allThreads"].clip(lower=0),
                bins=JMeterLoader.LOAD_BINS,
                labels=JMeterLoader.LOAD_LABELS,
                include_lowest=True,
                right=True,
            )
        if "is_transaction" not in df.columns:
            df["is_transaction"] = True
        if "err_type" not in df.columns:
            from analyser.loader import _err_type_from_code

            df["err_type"] = df["responseCode"].map(_err_type_from_code)
        n = len(df)
        if n == 0:
            return {
                "total_errors": 0,
                "client_4xx_count": 0,
                "server_5xx_count": 0,
                "connection_count": 0,
                "errors_by_band": pd.DataFrame(),
                "errors_by_transaction": pd.DataFrame(),
                "error_onset_minute": None,
                "error_onset_vu": None,
                "error_peak_minute": None,
                "error_peak_rate": 0.0,
            }

        fail = ~df["success"]
        et = df["err_type"]
        total_errors = int(fail.sum())

        client_4xx = int(et.eq("4xx").sum())
        server_5xx = int(et.eq("5xx").sum())
        conn = int(et.eq("connection").sum())

        def band_agg(sub: pd.DataFrame) -> dict:
            rc = sub["responseCode"].astype(str)
            f = ~sub["success"]
            return {
                "load_band": str(sub["load_band"].iloc[0]) if len(sub) else "",
                "total": int(f.sum()),
                "count_404": int(rc.eq("404").sum()),
                "count_504": int(rc.eq("504").sum()),
                "count_nohttpresponse": int(
                    rc.str.contains("NoHttp", case=False, na=False).sum()
                    + rc.str.contains("Connection", case=False, na=False).sum()
                ),
            }

        df_b = df.dropna(subset=["load_band"])
        ebands = pd.DataFrame([band_agg(s) for _, s in df_b.groupby("load_band", observed=True)])

        tx = df[df["is_transaction"] & (~df["success"])].copy()
        if len(tx):
            vc = tx.groupby("label").size()
            dom = []
            for lab in vc.index:
                sub = tx[tx["label"] == lab]
                et2 = sub["err_type"].value_counts().index[0] if len(sub) else "none"
                dom.append(str(et2))
            top = (
                pd.DataFrame(
                    {
                        "label": vc.index.astype(str),
                        "count": vc.values,
                        "pct_of_total": 100.0 * vc.values / max(total_errors, 1),
                        "dominant_type": dom,
                    }
                )
                .sort_values("count", ascending=False)
                .head(25)
            )
        else:
            top = pd.DataFrame(columns=["label", "count", "pct_of_total", "dominant_type"])

        pm = self.per_minute_kpis(df)
        onset_minute = None
        onset_vu = None
        peak_minute = None
        peak_rate = 0.0
        if len(pm):
            over1 = pm[pm["error_rate"] > 1.0]
            if len(over1):
                onset_minute = over1.iloc[0]["minute"]
                if hasattr(onset_minute, "isoformat"):
                    onset_minute = onset_minute.isoformat()
                mx = pm.loc[pm["error_rate"].idxmax()]
                peak_minute = mx["minute"]
                if hasattr(peak_minute, "isoformat"):
                    peak_minute = peak_minute.isoformat()
                peak_rate = float(mx["error_rate"])
                mint = pm.loc[pm["minute"] == (over1.iloc[0]["minute"])]
                if len(mint):
                    onset_vu = float(mint.iloc[0]["max_threads"])
            else:
                mx = pm.loc[pm["error_rate"].idxmax()]
                peak_minute = mx["minute"]
                if hasattr(peak_minute, "isoformat"):
                    peak_minute = peak_minute.isoformat()
                peak_rate = float(mx["error_rate"])

        return {
            "total_errors": total_errors,
            "client_4xx_count": client_4xx,
            "server_5xx_count": server_5xx,
            "connection_count": conn,
            "errors_by_band": ebands,
            "errors_by_transaction": top,
            "error_onset_minute": onset_minute,
            "error_onset_vu": onset_vu,
            "error_peak_minute": peak_minute,
            "error_peak_rate": peak_rate,
        }

    def throughput_analysis(self, df: pd.DataFrame) -> dict:
        df = self._ensure_ts(df)
        bands = self.per_band_kpis(df)
        if len(bands) == 0:
            return {
                "tps_by_band": pd.DataFrame(),
                "saturation_band": None,
                "collapse_detected": False,
                "scalability_type": "linear",
                "tps_cov_300vu": 0.0,
            }

        tb = bands[
            [
                "load_band",
                "samples",
                "tps_mean",
                "tps_cov",
            ]
        ].copy()
        tb["tps_max"] = tb["tps_mean"]
        tb["tps_min"] = tb["tps_mean"]

        sats = None
        prev = None
        for _, r in tb.iterrows():
            cur = float(r["tps_mean"])
            if prev is not None and prev > 1e-9:
                growth = (cur - prev) / prev
                if growth < 0.30:
                    sats = str(r["load_band"])
                    break
            prev = cur
        if sats is None and len(tb) > 0:
            sats = str(tb.iloc[-1]["load_band"])

        sat_row = tb[tb["load_band"] == sats] if sats else tb.head(0)
        sat_tps = float(sat_row.iloc[0]["tps_mean"]) if len(sat_row) else 0.0
        collapse = bool((tb["tps_mean"] < sat_tps * 0.95).any()) if sat_tps > 0 and len(tb) > 1 else False

        if len(tb) >= 2:
            first = float(tb.iloc[0]["tps_mean"])
            last = float(tb.iloc[-1]["tps_mean"])
            if last > first * 1.05:
                stype = "linear" if not collapse else "plateau"
            elif last < first * 0.95:
                stype = "negative"
            else:
                stype = "plateau"
        else:
            stype = "linear"

        hi = tb[tb["load_band"] == "241–300"]
        tps_cov_hi = float(hi.iloc[0]["tps_cov"]) if len(hi) else float(tb.iloc[-1]["tps_cov"])

        return {
            "tps_by_band": tb,
            "saturation_band": sats,
            "collapse_detected": collapse,
            "scalability_type": stype,
            "tps_cov_300vu": tps_cov_hi,
        }

    def apdex_by_band(self, df: pd.DataFrame, t: int = 3000) -> pd.DataFrame:
        df = self._ensure_ts(df)
        if "load_band" not in df.columns:
            df["load_band"] = pd.cut(
                df["allThreads"].clip(lower=0),
                bins=JMeterLoader.LOAD_BINS,
                labels=JMeterLoader.LOAD_LABELS,
                include_lowest=True,
                right=True,
            )
        df2 = df.dropna(subset=["load_band"])
        rows = []
        for band, sub in df2.groupby("load_band", observed=True):
            el = sub["elapsed"].astype(float)
            n = len(el)
            apd, sat, tol, fru = _apdex_scores(el, float(t))
            rows.append(
                {
                    "load_band": str(band),
                    "apdex": apd,
                    "satisfied_pct": 100.0 * sat / max(n, 1),
                    "tolerating_pct": 100.0 * tol / max(n, 1),
                    "frustrated_pct": 100.0 * fru / max(n, 1),
                }
            )
        return pd.DataFrame(rows)

    def rt_distribution_heatmap(
        self,
        df: pd.DataFrame,
        buckets: Optional[Sequence[Tuple[float, float, str]]] = None,
    ) -> pd.DataFrame:
        df = self._ensure_ts(df)
        if "load_band" not in df.columns:
            df["load_band"] = pd.cut(
                df["allThreads"].clip(lower=0),
                bins=JMeterLoader.LOAD_BINS,
                labels=JMeterLoader.LOAD_LABELS,
                include_lowest=True,
                right=True,
            )
        df2 = df.dropna(subset=["load_band"])
        bdef = list(buckets) if buckets is not None else list(_RT_BUCKETS)
        cols = [b[2] for b in bdef]
        rows_out = []

        for band, sub in df2.groupby("load_band", observed=True):
            el = sub["elapsed"].astype(float)
            n = len(el)
            rec: dict = {"load_band": str(band)}
            if n == 0:
                for c in cols:
                    rec[c] = 0.0
                rows_out.append(rec)
                continue
            for lo, hi, name in bdef:
                if hi == float("inf"):
                    cnt = int((el > lo).sum())
                else:
                    cnt = int(((el > lo) & (el <= hi)).sum())
                rec[name] = round(100.0 * cnt / n, 1)
            rows_out.append(rec)
        return pd.DataFrame(rows_out)

    def latency_decomposition(self, df: pd.DataFrame) -> pd.DataFrame:
        df = self._ensure_ts(df)
        if "load_band" not in df.columns:
            df["load_band"] = pd.cut(
                df["allThreads"].clip(lower=0),
                bins=JMeterLoader.LOAD_BINS,
                labels=JMeterLoader.LOAD_LABELS,
                include_lowest=True,
                right=True,
            )
        df2 = df.dropna(subset=["load_band"])
        rows = []
        for band, sub in df2.groupby("load_band", observed=True):
            lat = sub["Latency"].astype(float)
            conn = sub["Connect"].astype(float)
            el = sub["elapsed"].astype(float)
            server = el - lat
            ttfb_p90 = _quantile_ms(lat, 0.9)
            mean_rt = float(el.mean())

            rows.append(
                {
                    "load_band": str(band),
                    "connect_p90": _quantile_ms(conn, 0.9),
                    "ttfb_p90": ttfb_p90,
                    "elapsed_p90": _quantile_ms(el, 0.9),
                    "connect_median": float(conn.median()),
                    "ttfb_median": float(lat.median()),
                    "elapsed_median": float(el.median()),
                    "server_time_median": float(server.median()),
                    "mean_rt": mean_rt,
                    "diagnosis": "Healthy",
                }
            )

        bands_order = list(JMeterLoader.LOAD_LABELS)
        idx_map = {b: k for k, b in enumerate(bands_order)}
        rows_sorted = sorted(rows, key=lambda r: idx_map.get(str(r["load_band"]), 999))
        prev_ttfb: Optional[float] = None
        data_band_idx = 0
        for rec in rows_sorted:
            rec["diagnosis"] = _latency_decomp_diagnosis(
                float(rec["ttfb_p90"]),
                float(rec["mean_rt"]),
                data_band_idx,
                prev_ttfb,
            )
            prev_ttfb = float(rec["ttfb_p90"])
            data_band_idx += 1

        return pd.DataFrame(rows_sorted)

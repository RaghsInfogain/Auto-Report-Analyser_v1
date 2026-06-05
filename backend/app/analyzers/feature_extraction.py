"""
Observational feature extraction for JMeter latency — supplemental analytics only.

Primary metrics (mean, percentiles, error rate, SLA gates) must remain on the full,
unfiltered dataset in the analyzer. This module:

- Flags outliers for visibility (Tukey IQR fences) without removing samples.
- Derives robust summaries (trimmed / winsorized means) as optional comparisons only.

Nothing here modifies, censors, or replaces core calculations.
"""
from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Tuple

import numpy as np


def _tukey_mask(values: np.ndarray, k: float = 1.5) -> Tuple[np.ndarray, Dict[str, float]]:
    """
    Observational high/low outlier mask vs Tukey fences (inclusive of inner data).
    Returns (combined_flag bool array, fence metadata).
    """
    n = int(values.size)
    if n == 0:
        return np.array([], dtype=bool), {
            "q1_ms": float("nan"),
            "q3_ms": float("nan"),
            "iqr_ms": float("nan"),
            "lower_fence_ms": float("nan"),
            "upper_fence_ms": float("nan"),
        }
    q1, q3 = np.percentile(values, [25, 75])
    iqr = float(q3 - q1)
    lo = float(q1 - k * iqr)
    hi = float(q3 + k * iqr)
    low = values < lo
    high = values > hi
    meta = {
        "q1_ms": float(q1),
        "q3_ms": float(q3),
        "iqr_ms": iqr,
        "lower_fence_ms": lo,
        "upper_fence_ms": hi,
    }
    return (low | high), meta


def _trimmed_mean_ms(values: np.ndarray, proportion_each_tail: float) -> Optional[float]:
    if values.size == 0:
        return None
    p = float(proportion_each_tail)
    if p < 0 or p >= 0.5:
        return float(np.mean(values))
    try:
        from scipy.stats import trim_mean

        return float(trim_mean(values, proportiontocut=p))
    except ImportError:
        v = np.sort(values.astype(float, copy=False))
        k = int(np.floor(p * v.size))
        if k <= 0:
            return float(np.mean(v))
        return float(np.mean(v[k : v.size - k]))


def _winsorized_mean_ms(values: np.ndarray, lower_pct: float, upper_pct: float) -> Optional[float]:
    if values.size == 0:
        return None
    lp, up = float(lower_pct), float(upper_pct)
    if lp < 0 or up < 0 or lp + up >= 1.0:
        return float(np.mean(values))
    try:
        from scipy.stats.mstats import winsorize

        w = winsorize(values.astype(float, copy=False), limits=(lp, up))
        return float(np.mean(np.asarray(w, dtype=float)))
    except ImportError:
        v = values.astype(float, copy=False)
        lo_b = np.percentile(v, 100 * lp)
        hi_b = np.percentile(v, 100 * (1.0 - up))
        clipped = np.clip(v, lo_b, hi_b)
        return float(np.mean(clipped))


def extract_jmeter_latency_supplement(
    sample_times_ms: np.ndarray,
    *,
    total_requests_in_run: int,
    response_time_stat_row_count: int,
    primary_sample_time_stats: Mapping[str, Any],
    tukey_k: float = 1.5,
    trim_each_tail: float = 0.05,
    winsor_lower: float = 0.05,
    winsor_upper: float = 0.05,
) -> Dict[str, Any]:
    """
    Build supplemental payload from the same ``sample_times_ms`` array used for primary RT stats.

    ``primary_sample_time_stats`` is passed through only for cross-check / narrative hints;
    this function does not recompute official mean/percentiles (avoids drift).
    """
    arr = np.asarray(sample_times_ms, dtype=float)
    arr = arr[np.isfinite(arr)]

    mean_ref = primary_sample_time_stats.get("mean")
    p90_ref = primary_sample_time_stats.get("p90")

    outlier_mask, fence_meta = _tukey_mask(arr, k=tukey_k)
    n_out = int(np.sum(outlier_mask)) if arr.size else 0
    n_high = int(np.sum(arr > fence_meta["upper_fence_ms"])) if arr.size and np.isfinite(
        fence_meta["upper_fence_ms"]
    ) else 0
    n_low = int(np.sum(arr < fence_meta["lower_fence_ms"])) if arr.size and np.isfinite(
        fence_meta["lower_fence_ms"]
    ) else 0

    mean_exceeds_p90: Optional[bool] = None
    if isinstance(mean_ref, (int, float)) and isinstance(p90_ref, (int, float)):
        mean_exceeds_p90 = float(mean_ref) > float(p90_ref)

    trimmed = _trimmed_mean_ms(arr, trim_each_tail)
    winsor = _winsorized_mean_ms(arr, winsor_lower, winsor_upper)

    return {
        "schema_version": 1,
        "role": "supplemental_only",
        "disclaimer": {
            "primary_metrics": (
                "Official mean, percentiles, error rate, and SLA compliance are computed in "
                "JMeterAnalyzerV2 on the complete run — samples are not removed, capped, or "
                "filtered for outliers before those calculations."
            ),
            "this_block": (
                "Outlier counts are observational (Tukey IQR). Trimmed and winsorized means are "
                "analytical comparisons only and do not replace primary metrics or gates."
            ),
        },
        "populations": {
            "total_requests_in_run": int(total_requests_in_run),
            "rows_used_for_response_time_aggregates": int(response_time_stat_row_count),
            "note": (
                "Error rate and totals use every row in the run. Response-time mean and "
                "percentiles use the same passed row set as the analyzer (successful outcomes "
                "eligible for RT stats — see include_in_response_time_stats); that set is "
                "full for its definition and is not outlier-stripped."
            ),
        },
        "outlier_observations": {
            "method": "Tukey IQR fences",
            "k": float(tukey_k),
            "flags_applied_to": "same_response_time_rows_as_primary_stats",
            "sample_count": int(arr.size),
            "count_above_upper_fence": n_high,
            "count_below_lower_fence": n_low,
            "count_flagged_either_tail": n_out,
            "fraction_flagged": float(n_out / arr.size) if arr.size else 0.0,
            "fences_ms": fence_meta,
        },
        "distribution_shape_hints": {
            "primary_mean_ms": mean_ref,
            "primary_p90_ms": p90_ref,
            "mean_exceeds_p90": mean_exceeds_p90,
            "note": (
                "If mean > P90, a right tail of slower requests is likely elevating the average "
                "versus the bulk of requests — investigate tail separately; primary numbers "
                "still reflect all included RT rows."
            ),
        },
        "supplemental_robust_comparison": {
            "trimmed_mean_ms": trimmed,
            "trim_proportion_each_tail": float(trim_each_tail),
            "winsorized_mean_ms": winsor,
            "winsorize_limits": {
                "lower_tail_fraction": float(winsor_lower),
                "upper_tail_fraction": float(winsor_upper),
            },
            "interpretation": (
                "Robust means shrink the influence of extremes for comparison; they do not define "
                "SLA or release gates."
            ),
        },
    }


def extract_jmeter_feature_bundle(
    sample_times_ms: np.ndarray,
    *,
    total_samples: int,
    rt_row_count: int,
    primary_sample_time_stats: Mapping[str, Any],
) -> Dict[str, Any]:
    """Alias with naming aligned to analyzer call sites."""
    return extract_jmeter_latency_supplement(
        sample_times_ms,
        total_requests_in_run=total_samples,
        response_time_stat_row_count=rt_row_count,
        primary_sample_time_stats=primary_sample_time_stats,
    )

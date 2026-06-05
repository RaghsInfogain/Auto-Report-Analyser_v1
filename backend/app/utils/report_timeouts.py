"""HTTP/async wait budgets for run report generation (keep client timeouts in sync — see frontend api.ts)."""
from __future__ import annotations

# Hard caps so a single run cannot pin workers forever
REPORT_WAIT_MIN_SECONDS = 180.0
REPORT_WAIT_MAX_SECONDS = 21600.0  # 6 hours (very large JTL runs)

LARGE_RUN_BYTES = 500 * 1024 * 1024  # 500 MiB — user-requested threshold for longer waits
LARGE_RUN_HTML_ONLY_BYTES = 100 * 1024 * 1024  # 100 MiB — skip PDF/PPT above this size
LARGE_RUN_HTML_ONLY_RECORDS = 1_000_000  # skip PDF/PPT for very high sample counts


def should_skip_pdf_ppt_reports(total_bytes: int, total_records: int = 0) -> bool:
    """Large JMeter runs generate HTML only — PDF/PPT are too slow and memory-heavy."""
    if total_bytes >= LARGE_RUN_HTML_ONLY_BYTES:
        return True
    if total_records >= LARGE_RUN_HTML_ONLY_RECORDS:
        return True
    return False


def compute_report_wait_timeout_seconds(
    total_bytes: int, total_records: int = 0
) -> float:
    """
    Scale allowed wall time with on-disk / declared payload size.

    - Small runs: at least REPORT_WAIT_MIN_SECONDS.
    - Past 500 MiB: add ~3s per additional MiB (heavy parse + analyze + HTML).
    - Very large row counts extend the budget (use max record_count per run to avoid merged-file double count).
    """
    if total_bytes <= 0:
        t = REPORT_WAIT_MIN_SECONDS
    else:
        mb = total_bytes / (1024 * 1024)
        if mb <= 200:
            t = 180.0 + mb * 0.5
        elif mb <= 500:
            t = 280.0 + (mb - 200.0) * 1.2
        else:
            t = 640.0 + (mb - 500.0) * 4.0
        if mb > 10_000:
            t = max(t, 7200.0 + (mb - 10_000.0) * 0.5)

    if total_records > 2_000_000:
        t = max(t, 400.0 + total_records / 8000.0)

    return float(min(max(t, REPORT_WAIT_MIN_SECONDS), REPORT_WAIT_MAX_SECONDS))


def estimate_run_total_bytes(files) -> int:
    """Sum unique file_path sizes (avoids double-counting merged JMeter rows pointing at one path)."""
    import os

    total = 0
    seen: set[str] = set()
    for f in files:
        p = getattr(f, "file_path", None) or ""
        if not p or p in seen:
            continue
        seen.add(p)
        try:
            if os.path.isfile(p):
                total += int(os.path.getsize(p))
            else:
                total += int(getattr(f, "file_size", 0) or 0)
        except OSError:
            total += int(getattr(f, "file_size", 0) or 0)
    return total


def format_duration_human(seconds: float) -> str:
    """Human-readable duration for UI ETA labels."""
    s = int(max(0, round(seconds)))
    if s < 60:
        return f"~{s} sec"
    if s < 3600:
        m = max(1, s // 60)
        return f"~{m} min"
    h = s // 3600
    m = (s % 3600) // 60
    if m:
        return f"~{h}h {m}m"
    return f"~{h}h"


def estimate_run_max_record_count(files) -> int:
    """Best-effort row estimate: max(record_count) across files (avoids summing duplicate merged rows)."""
    m = 0
    for f in files:
        try:
            m = max(m, int(getattr(f, "record_count", None) or 0))
        except (TypeError, ValueError):
            continue
    return m

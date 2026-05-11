"""JMeter row outcome: align error counting with which samples are used for response-time stats."""
from typing import Any, Dict


def is_jmeter_error_outcome(d: Dict[str, Any]) -> bool:
    """
    True if this row is treated as a failed/errored request (same basis as error_rate):
    JMeter success is false, or HTTP 4xx/5xx (even if success flag is true in some exports).
    """
    if not d.get("success", True):
        return True
    rc = str((d.get("response_code") or "")).strip()
    if not rc:
        return False
    return rc[0] in ("4", "5")


def include_in_response_time_stats(d: Dict[str, Any]) -> bool:
    """
    Min/avg/percentiles/SLA buckets use only non-error rows so failing or HTTP-error
    samples (often elapsed=0) are not read as 'very fast' successes.
    """
    return not is_jmeter_error_outcome(d)

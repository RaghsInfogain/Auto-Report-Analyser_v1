"""Normalize and classify JMeter `url` field from JTL/CSV (handles literal \"null\" text)."""
from typing import Any

# Exports/BI tools often write missing URL as the word "null" instead of an empty cell.
_JMETER_PLACEHOLDER_URLS = frozenset(
    {"null", "none", "nan", "n/a", "-", "#n/a", "undefined", "nil"}
)


def normalize_jmeter_url_value(value: Any) -> str:
    """Return the URL string, or empty when the cell is empty or a null-like placeholder."""
    if value is None:
        return ""
    s = str(value).strip()
    if not s:
        return ""
    if s.lower() in _JMETER_PLACEHOLDER_URLS:
        return ""
    return s


def is_jmeter_transaction_controller_by_url(url: Any) -> bool:
    """True for Transaction Controller rows: no real HTTP URL on the JMeter sample record."""
    return normalize_jmeter_url_value(url) == ""

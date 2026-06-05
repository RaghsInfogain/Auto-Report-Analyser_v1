"""Tests for Lighthouse + Navigation Timing report v2."""
import json

from app.lighthouse_nav_report_v2.cwv_engine import CWVEngine
from app.lighthouse_nav_report_v2.nav_loader import NavTimingLoader
from app.lighthouse_nav_report_v2.verdict_engine import VerdictEngine


def test_classify_fcp_good():
    assert CWVEngine().classify("fcp", 1500) == "good"


def test_classify_lcp_poor():
    assert CWVEngine().classify("lcp", 5000) == "poor"


def test_apdex():
    assert CWVEngine().compute_apdex([1000, 2000, 500], 3000) == 1.0


def test_nav_none():
    assert NavTimingLoader().load(None) is None


def test_nav_load_minimal(tmp_path):
    p = tmp_path / "nav.json"
    p.write_text(
        json.dumps(
            [
                {
                    "pageUrl": "https://example.com/a",
                    "playwrightFullPageLoadTime": 2000,
                    "firstContentFulPaint": 1500,
                    "dnsLookupTime": 10,
                    "connectionTime": 50,
                    "firstInputDelay": 80,
                }
            ]
        ),
        encoding="utf-8",
    )
    rows = NavTimingLoader().load(str(p))
    assert rows and rows[0]["pageUrl"].startswith("https://example.com")
    agg = NavTimingLoader().compute_aggregates(rows)
    assert agg["page_count"] == 1
    assert agg["avg_pl"] == 2000.0


def test_verdict_no_go_zero_lcp():
    cwv = {
        "total_pages": 5,
        "avg_perf_score": 40,
        "avg_tbt": 500,
        "lcp_distribution": {"good": 0, "ni": 2, "poor": 3},
        "tbt_distribution": {"good": 1, "ni": 2, "poor": 2},
        "cls_distribution": {"good": 3, "ni": 1, "poor": 1},
    }
    opps = {"unused_js": {"avg_savings_kb": 50}}
    v = VerdictEngine().evaluate(cwv, opps, {"perf_score": 85, "tbt": 200})
    assert v["verdict"] == "NO_GO"


def test_verdict_go_perfect():
    cwv = {
        "total_pages": 4,
        "avg_perf_score": 92,
        "avg_tbt": 50,
        "lcp_distribution": {"good": 4, "ni": 0, "poor": 0},
        "tbt_distribution": {"good": 4, "ni": 0, "poor": 0},
        "cls_distribution": {"good": 4, "ni": 0, "poor": 0},
    }
    opps = {"unused_js": {"avg_savings_kb": 10}}
    v = VerdictEngine().evaluate(cwv, opps, {"perf_score": 85, "tbt": 200})
    assert v["verdict"] == "GO"

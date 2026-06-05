"""
Simplified and efficient JMeter analyzer
Fast, reliable, and produces comprehensive metrics
"""
import math
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from urllib.parse import urlparse

import numpy as np

from app.models.jmeter import JMeterMetrics
from app.utils.jmeter_url import is_jmeter_transaction_controller_by_url, normalize_jmeter_url_value
from app.utils.jmeter_outcome import is_jmeter_error_outcome, include_in_response_time_stats
from app.analyzers.feature_extraction import extract_jmeter_feature_bundle
from app.utils.jmeter_base_url import dominant_base_url_for_paths, dominant_origin_from_jmeter_rows


class JMeterAnalyzerV2:
    """Simplified JMeter analyzer with efficient calculations"""

    @staticmethod
    def _include_in_response_time_stats(d: Dict[str, Any]) -> bool:
        """Response-time stats use successful outcomes only (excludes 4xx/5xx, not just success=false)."""
        return include_in_response_time_stats(d)

    @staticmethod
    def _is_transaction_controller_row(d: Dict[str, Any]) -> bool:
        """JMeter transaction controllers use empty/missing URL; HTTP samplers have a URL.
        CSV often stores missing URL as the literal string \"null\" (not an empty cell)."""
        return is_jmeter_transaction_controller_by_url(d.get("url"))

    @staticmethod
    def _rows_for_response_time_aggregation(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Use passed transaction-controller rows when enough exist; otherwise all passed rows
        (standalone HTTP samples). Excludes HTTP error / failed outcomes.
        """
        tc_n = sum(1 for d in data if JMeterAnalyzerV2._is_transaction_controller_row(d))
        total = len(data) or 1
        prefer_tc = tc_n >= max(50, int(total * 0.03))
        out: List[Dict[str, Any]] = []
        for d in data:
            if not JMeterAnalyzerV2._include_in_response_time_stats(d):
                continue
            if prefer_tc:
                if JMeterAnalyzerV2._is_transaction_controller_row(d):
                    out.append(d)
            else:
                out.append(d)
        return out

    @staticmethod
    def _max_vu_and_peak_threshold(data: List[Dict[str, Any]]) -> Tuple[int, float]:
        vu_vals = [float(d["all_threads"]) for d in data if d.get("all_threads") is not None]
        if not vu_vals:
            return 0, 0.0
        mx = int(max(vu_vals))
        thr = max(1.0, mx * 0.85)
        return mx, thr

    @staticmethod
    def _vu_value_row(d: Dict[str, Any]) -> int:
        """Effective VU count for one row (all_threads preferred, then grp_threads)."""
        for k in ("all_threads", "allThreads", "grp_threads", "grpThreads"):
            v = d.get(k)
            if v is not None:
                try:
                    return int(float(v))
                except (TypeError, ValueError):
                    continue
        return 0

    @staticmethod
    def _resolve_parallel_vusers(
        data: List[Dict[str, Any]],
        parallel_peak_sources: Optional[List[Dict[str, Any]]],
        merged_source_filenames: Optional[List[str]],
    ) -> Tuple[int, List[Dict[str, Any]]]:
        """
        Combined peak VUsers for parallel JMeter result files = sum of max(allThreads) per file.

        Prefer ``parallel_peak_sources`` (pre-merge) when len>=2 — accurate even if
        ``_merge_source_idx`` is missing from saved CSV. Otherwise group merged rows by
        ``_merge_source_idx`` (requires 2+ distinct indices).
        """
        breakdown: List[Dict[str, Any]] = []

        if parallel_peak_sources and len(parallel_peak_sources) >= 2:
            total = 0
            for i, src in enumerate(parallel_peak_sources):
                pk = int(src.get("peak_vusers") or 0)
                total += pk
                fp = str(src.get("file_path") or "").strip()
                bu = dominant_base_url_for_paths([fp]) if fp else ""
                if not bu:
                    bu = dominant_origin_from_jmeter_rows(
                        [d for d in data if int(d.get("_merge_source_idx", i)) == i]
                    )
                breakdown.append(
                    {
                        "source_index": i,
                        "filename": str(src.get("filename") or f"Result file {i + 1}"),
                        "base_url": bu,
                        "peak_vusers": pk,
                    }
                )
            return total, breakdown

        by_idx: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for d in data:
            idx = 0
            if "_merge_source_idx" in d and d.get("_merge_source_idx") not in ("", None):
                try:
                    idx = int(float(d["_merge_source_idx"]))
                except (TypeError, ValueError):
                    idx = 0
            by_idx[idx].append(d)

        if len(by_idx) < 2:
            return 0, []

        total = 0
        names = merged_source_filenames or []
        for idx in sorted(by_idx.keys()):
            rows = by_idx[idx]
            peak = max((JMeterAnalyzerV2._vu_value_row(x) for x in rows), default=0)
            total += int(peak)
            fn = ""
            if names and 0 <= idx < len(names):
                fn = names[idx]
            breakdown.append(
                {
                    "source_index": idx,
                    "filename": fn or f"Result file {idx + 1}",
                    "base_url": dominant_origin_from_jmeter_rows(rows),
                    "peak_vusers": int(peak),
                }
            )
        return total, breakdown



    @staticmethod
    def _transaction_p90_sla_at_peak_load(
        data: List[Dict[str, Any]],
        transaction_stats: Dict[str, Any],
        peak_vu_threshold: float,
        sla_p90_ms: float = 3000.0,
    ) -> Dict[str, Any]:
        """Per-transaction P90 on passed samples in peak load (≥85% of max VU); fallback to full-run passed."""
        labels = sorted(transaction_stats.keys(), key=lambda x: (x or "").lower())
        passed_detail: List[Dict[str, Any]] = []
        n_pass = 0
        for label in labels:
            def _collect(use_peak: bool) -> List[float]:
                rows: List[float] = []
                for d in data:
                    if d.get("label") != label:
                        continue
                    if not JMeterAnalyzerV2._is_transaction_controller_row(d):
                        continue
                    if not JMeterAnalyzerV2._include_in_response_time_stats(d):
                        continue
                    if use_peak and peak_vu_threshold > 0:
                        av = d.get("all_threads")
                        if av is None or float(av) < peak_vu_threshold:
                            continue
                    st = d.get("sample_time")
                    if st is not None:
                        rows.append(float(st))
                return rows

            times = _collect(True)
            if len(times) < 3:
                times = _collect(False)
            if not times:
                passed_detail.append(
                    {"label": label, "p90_ms": None, "sla_pass": False, "n_samples": 0}
                )
                continue
            p90 = float(np.percentile(np.array(times, dtype=float), 90))
            ok = p90 < sla_p90_ms
            if ok:
                n_pass += 1
            passed_detail.append(
                {
                    "label": label,
                    "p90_ms": round(p90, 1),
                    "sla_pass": ok,
                    "n_samples": len(times),
                }
            )
        n_total = len(labels)
        pct = (100.0 * n_pass / n_total) if n_total else 0.0
        return {
            "sla_p90_ms": sla_p90_ms,
            "transactions_tested": n_total,
            "transactions_pass": n_pass,
            "transactions_fail": max(0, n_total - n_pass),
            "pass_rate_pct": round(pct, 2),
            "peak_vu_threshold": int(round(peak_vu_threshold)) if peak_vu_threshold else 0,
            "details": passed_detail,
        }

    @staticmethod
    def _strip_jmeter_thread_suffix(thread_name: str) -> str:
        """Strip JMeter's trailing ' 9-123' (thread iteration) from threadName."""
        if not thread_name:
            return ""
        s = str(thread_name).strip()
        if not s:
            return ""
        m = re.search(r"^(.+?)\s+\d+-\d+$", s)
        if m:
            return m.group(1).strip()
        return s

    @staticmethod
    def _is_generic_thread_group_label(name: str) -> bool:
        """True for default JMeter / meaningless thread group titles."""
        s = (name or "").strip().lower()
        if len(s) < 2:
            return True
        generics = (
            "thread group",
            "threadgroup",
            "tg",
            "users",
            "user",
            "load test",
            "scenario",
            "setup",
            "teardown",
            "set up thread group",
            "tear down thread group",
        )
        if s in generics:
            return True
        for g in ("thread group", "set up", "tear down"):
            if s == g or (s.startswith(g) and len(s) <= len(g) + 3):
                return True
        return False

    @staticmethod
    def _prettify_hostname_as_app_name(host: str) -> str:
        """Turn hostname (or first label) into a short display title."""
        if not host:
            return ""
        host = host.strip().lower().split(":")[0]
        first = host.split(".")[0]
        parts = [p for p in re.split(r"[-_]+", first) if p]
        if not parts:
            return host
        words: List[str] = []
        for p in parts:
            if len(p) <= 4 and p.isalpha():
                words.append(p.upper())
            else:
                words.append(p[:1].upper() + p[1:].lower())
        return " ".join(words)

    @staticmethod
    def infer_application_name_from_jmeter_data(data: List[Dict[str, Any]]) -> str:
        """
        Derive application name for report titles from JMeter rows:
        1) Most common user-defined thread group name (after stripping JMeter suffixes)
        2) Else most common HTTP host from URL column
        """
        if not data:
            return ""
        n = len(data)
        min_hits = max(15, min(500, n // 50))

        bases: List[str] = []
        for d in data:
            tn = d.get("thread_name") or d.get("threadName") or ""
            base = JMeterAnalyzerV2._strip_jmeter_thread_suffix(str(tn).strip())
            if not base:
                continue
            if " - " in base:
                base = base.split(" - ")[0].strip()
            if not base:
                continue
            bases.append(base)

        if bases:
            for name, cnt in Counter(bases).most_common(8):
                if cnt < min_hits:
                    break
                if JMeterAnalyzerV2._is_generic_thread_group_label(name):
                    continue
                return name.strip()

        hosts: List[str] = []
        for d in data:
            u = normalize_jmeter_url_value(d.get("url"))
            if not u:
                continue
            if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", u):
                u = "https://" + u.lstrip("/")
            try:
                host = urlparse(u).hostname
            except Exception:
                continue
            if (
                not host
                or host == "localhost"
                or re.match(r"^(\d{1,3}\.){3}\d{1,3}$", host)
            ):
                continue
            hosts.append(host.lower())

        if hosts:
            hc = Counter(hosts)
            best_host, cnt = hc.most_common(1)[0]
            if cnt >= min_hits or len(hc) == 1:
                return JMeterAnalyzerV2._prettify_hostname_as_app_name(best_host)

        return ""

    @staticmethod
    def _build_report_header(
        data: List[Dict[str, Any]],
        total_samples: int,
        duration_seconds: float,
        max_vu: int,
    ) -> Dict[str, Any]:
        """Titles and time window for HTML report; application name is inferred from JMeter rows."""
        application_name = JMeterAnalyzerV2.infer_application_name_from_jmeter_data(data)
        line1_date = datetime.now().strftime("%d %b %Y")
        t_start = ""
        t_end = ""
        tz_suffix = "IST"
        try:
            from zoneinfo import ZoneInfo

            tz = ZoneInfo("Asia/Kolkata")
            ts_list = [d.get("timestamp", 0) for d in data if d.get("timestamp")]
            if ts_list:
                t0 = datetime.fromtimestamp(min(ts_list) / 1000.0, tz=tz)
                t1 = datetime.fromtimestamp(max(ts_list) / 1000.0, tz=tz)
                t_start = t0.strftime("%H:%M")
                t_end = t1.strftime("%H:%M")
                line1_date = t0.strftime("%d %b %Y")
        except Exception:
            ts_list = [d.get("timestamp", 0) for d in data if d.get("timestamp")]
            if ts_list:
                t0 = datetime.fromtimestamp(min(ts_list) / 1000.0)
                t1 = datetime.fromtimestamp(max(ts_list) / 1000.0)
                t_start = t0.strftime("%H:%M")
                t_end = t1.strftime("%H:%M")
                line1_date = t0.strftime("%d %b %Y")

        dur_min = duration_seconds / 60.0 if duration_seconds else 0.0
        meta_parts = [
            "JMeter Results",
            f"{total_samples:,} samples",
        ]
        if dur_min > 0:
            meta_parts.append(f"{dur_min:.1f} min")
            if t_start and t_end:
                meta_parts.append(f"{t_start}–{t_end} {tz_suffix}")
        line1_parts = ["Performance Test Analysis Report"]
        if application_name:
            line1_parts.append(application_name)
        line1_parts.append(line1_date)
        line1 = " · ".join(line1_parts)
        return {
            "line1": line1,
            "line2": (
                f"Load Test: Stepped Up to {max_vu} Virtual Users"
                if max_vu
                else "Load Test Results"
            ),
            "line3": " · ".join(meta_parts),
            "application_name": application_name,
            "product": application_name,
            "environment": "",
            "report_date": line1_date,
            "time_start": t_start,
            "time_end": t_end,
            "timezone_label": tz_suffix,
        }
    
    @staticmethod
    def analyze(
        data: List[Dict[str, Any]],
        targets: Optional[Dict[str, float]] = None,
        application_display_name: Optional[str] = None,
        *,
        parallel_peak_sources: Optional[List[Dict[str, Any]]] = None,
        merged_source_filenames: Optional[List[str]] = None,
    ) -> JMeterMetrics:
        """
        Analyze JMeter data and return comprehensive metrics.
        targets: optional dict with keys availability_target, avg_response_time_target (ms),
                 error_rate_target (%), throughput_target, p95_target (ms), sla_compliance_target (%)
        application_display_name: if set, overrides inferred JMeter thread/host name in report titles.
        parallel_peak_sources: when 2+ JMeter files were merged, pass one dict per file with
            peak_vusers, filename, file_path — used for combined peak VUsers (sum) and reporting.
        merged_source_filenames: optional labels (same order as merge indices) when only merged CSV is loaded.
        """
        if not data:
            raise ValueError("No data provided for analysis")
        
        print(f"  Analyzing {len(data):,} records...")
        
        rt_rows = JMeterAnalyzerV2._rows_for_response_time_aggregation(data)
        # Extract arrays for efficient numpy operations (passed TC rows when present, else passed requests)
        sample_times = np.array(
            [d.get("sample_time", 0) for d in rt_rows if d.get("sample_time") is not None],
            dtype=float,
        )
        latencies = np.array(
            [d.get("latency", 0) for d in rt_rows if d.get("latency") is not None],
            dtype=float,
        )
        connect_times = np.array(
            [d.get("connect_time", 0) for d in rt_rows if d.get("connect_time") is not None],
            dtype=float,
        )

        # Calculate basic metrics
        total_samples = len(data)
        errors = sum(1 for d in data if is_jmeter_error_outcome(d))
        error_rate = (errors / total_samples) if total_samples > 0 else 0.0
        
        # Calculate duration and throughput
        timestamps = [d.get("timestamp", 0) for d in data if d.get("timestamp")]
        if timestamps:
            duration_seconds = (max(timestamps) - min(timestamps)) / 1000.0
            duration_hours = duration_seconds / 3600.0
            # Throughput (req/s) = successful samples only (exclude failed / HTTP error rows)
            passed_samples = total_samples - errors
            throughput = (
                passed_samples / duration_seconds if duration_seconds > 0 else 0.0
            )
        else:
            duration_seconds = 0.0
            duration_hours = 0.0
            throughput = 0.0
        
        # Response codes
        response_codes = Counter([str(d.get("response_code", "")) for d in data if d.get("response_code")])

        # Error breakdown by description (for failed samples: success=False or 4xx/5xx)
        error_by_description = defaultdict(int)
        for d in data:
            success = d.get("success", True)
            rc = str(d.get("response_code", "") or "")
            is_http_error = rc.startswith("4") or rc.startswith("5")
            if success is False or is_http_error:
                desc = (d.get("failure_message") or d.get("response_message") or "").strip()
                if not desc:
                    desc = f"HTTP {rc}" if rc else "Failed"
                # Truncate long messages for grouping
                if len(desc) > 200:
                    desc = desc[:197] + "..."
                error_by_description[desc] += 1
        error_by_description = dict(error_by_description)

        # Calculate percentiles efficiently
        sample_time_stats = JMeterAnalyzerV2._calculate_stats(sample_times)
        latency_stats = JMeterAnalyzerV2._calculate_stats(latencies)
        connect_time_stats = JMeterAnalyzerV2._calculate_stats(connect_times)
        
        # Analyze by label (transactions/requests)
        transaction_stats, request_stats = JMeterAnalyzerV2._analyze_by_label(data)

        max_vu, peak_thr = JMeterAnalyzerV2._max_vu_and_peak_threshold(data)
        multi_vu_sum, multi_vu_breakdown = JMeterAnalyzerV2._resolve_parallel_vusers(
            data, parallel_peak_sources, merged_source_filenames
        )
        header_vu = int(multi_vu_sum) if multi_vu_sum > 0 else int(max_vu)
        display_targets = JMeterAnalyzerV2._resolve_display_targets(targets)
        sla_p90_ms = float(display_targets.get("p95_percentile") or 3000)
        tx_sla_peak = JMeterAnalyzerV2._transaction_p90_sla_at_peak_load(
            data, transaction_stats, peak_thr, sla_p90_ms=sla_p90_ms
        )
        report_header = JMeterAnalyzerV2._build_report_header(
            data, total_samples, duration_seconds, header_vu
        )
        _disp = (application_display_name or "").strip()
        if _disp:
            report_header = dict(report_header)
            report_header["application_name"] = _disp
            report_header["product"] = _disp
            rd = str(report_header.get("report_date") or "").strip()
            line1_parts = ["Performance Test Analysis Report", _disp]
            if rd:
                line1_parts.append(rd)
            report_header["line1"] = " · ".join(line1_parts)
        
        # Calculate scores and grades
        _mean_ms = sample_time_stats.get("mean")
        avg_response_sec = (float(_mean_ms) / 1000.0) if isinstance(_mean_ms, (int, float)) else 0.0
        _p95_ms = sample_time_stats.get("p95")
        p95_response = float(_p95_ms) if isinstance(_p95_ms, (int, float)) else 0.0
        success_rate = ((total_samples - errors) / total_samples * 100) if total_samples > 0 else 0.0
        
        # SLA compliance (% of successful samples under each threshold) — same basis as RT aggregates
        passed_for_sla = list(rt_rows)
        n_passed_sla = len(passed_for_sla)
        if n_passed_sla > 0:
            sla_2s = sum(1 for d in passed_for_sla if d.get("sample_time", 0) < 2000)
            sla_3s = sum(1 for d in passed_for_sla if d.get("sample_time", 0) < 3000)
            sla_5s = sum(1 for d in passed_for_sla if d.get("sample_time", 0) < 5000)
            sla_compliance_2s_pct = (sla_2s / n_passed_sla * 100)
            sla_compliance_3s_pct = (sla_3s / n_passed_sla * 100)
            sla_compliance_5s_pct = (sla_5s / n_passed_sla * 100)
        else:
            sla_compliance_2s_pct = 0.0
            sla_compliance_3s_pct = 0.0
            sla_compliance_5s_pct = 0.0
        
        # Calculate scores (0-100) - use run targets if provided
        score_targets = JMeterAnalyzerV2._resolve_score_targets(targets)
        p95_response_sec = p95_response / 1000.0
        scores = JMeterAnalyzerV2._calculate_scores(
            success_rate, error_rate, avg_response_sec, p95_response_sec,
            throughput, sla_compliance_2s_pct,
            score_targets=score_targets
        )
        
        # Calculate grades
        overall_score = scores["overall"]
        grade, grade_class = JMeterAnalyzerV2._calculate_grade(overall_score)
        
        # Generate time series (simplified - sample if too large)
        time_series_data = JMeterAnalyzerV2._calculate_time_series(data, duration_seconds)
        
        # Response time distribution
        rt_distribution = JMeterAnalyzerV2._calculate_response_time_distribution(data)

        # Observational outliers + robust comparison metrics only (does not alter primary stats)
        feature_extraction = extract_jmeter_feature_bundle(
            sample_times,
            total_samples=total_samples,
            rt_row_count=len(rt_rows),
            primary_sample_time_stats=sample_time_stats,
        )
        
        # Critical issues and recommendations
        critical_issues = JMeterAnalyzerV2._identify_issues(
            error_rate * 100, avg_response_sec, sla_compliance_2s_pct, transaction_stats, request_stats
        )
        recommendations = JMeterAnalyzerV2._generate_recommendations(error_rate * 100, avg_response_sec, throughput)
        improvement_roadmap = JMeterAnalyzerV2._generate_roadmap(overall_score)
        
        # Grade descriptions
        grade_reasons = JMeterAnalyzerV2._build_grade_reasons(
            scores, avg_response_sec, success_rate,
            error_rate * 100, throughput, p95_response_sec,
            sla_compliance_2s_pct, grade, grade_class
        )
        
        # Skewness interpretation for response time with DYNAMIC root cause analysis
        response_time_skewness = sample_time_stats.get("skewness", 0)
        _p99_ms = sample_time_stats.get("p99")
        _max_ms = sample_time_stats.get("max")
        p99_response_sec = (float(_p99_ms) / 1000.0) if isinstance(_p99_ms, (int, float)) else 0.0
        max_response_sec = (float(_max_ms) / 1000.0) if isinstance(_max_ms, (int, float)) else 0.0
        skewness_interpretation = JMeterAnalyzerV2._interpret_skewness(
            response_time_skewness, 
            "response time",
            {
                "avg_response": avg_response_sec,
                "p95_response": p95_response_sec,
                "p99_response": p99_response_sec,
                "max_response": max_response_sec,
                "error_rate": error_rate * 100,
                "throughput": throughput,
                "transaction_stats": transaction_stats,
                "request_stats": request_stats,
                "response_codes": dict(response_codes),
                "sla_compliance": sla_compliance_2s_pct
            }
        )
        
        # Get business impact for the grade
        business_impact = JMeterAnalyzerV2._get_business_impact(grade)
        
        # Generate PHASED improvement plan to reach A+
        phased_improvement_plan = JMeterAnalyzerV2._generate_phased_improvement_plan(
            grade, overall_score, scores, avg_response_sec, error_rate * 100, 
            throughput, p95_response_sec, sla_compliance_2s_pct, 
            transaction_stats, request_stats
        )
        
        # Build summary
        summary = {
            "test_duration_hours": round(duration_hours, 2),
            "success_rate": round(success_rate, 2),
            "avg_throughput": round(throughput, 2),
            "sla_compliance_2s": round(sla_compliance_2s_pct, 2),
            "sla_compliance_3s": round(sla_compliance_3s_pct, 2),
            "sla_compliance_5s": round(sla_compliance_5s_pct, 2),
            "overall_score": round(overall_score, 2),
            "overall_grade": grade,
            "grade_class": grade_class,
            "overall_grade_description": {
                "grade": grade,
                "score": round(overall_score, 1),
                "title": JMeterAnalyzerV2._get_grade_title(grade),
                "description": JMeterAnalyzerV2._get_grade_description(grade),
                "score_range": JMeterAnalyzerV2._get_grade_range(grade),
                "class": grade_class
            },
            "business_impact": business_impact,
            "skewness_analysis": skewness_interpretation,
            "phased_improvement_plan": phased_improvement_plan,
            "grade_reasons": grade_reasons,
            "response_time_distribution": rt_distribution,
            "time_series_data": time_series_data,
            "transaction_stats": transaction_stats,
            "request_stats": request_stats,
            "error_by_description": error_by_description,
            "critical_issues": critical_issues,
            "recommendations": recommendations,
            "improvement_roadmap": improvement_roadmap,
            "scores": scores,
            "targets": display_targets,
            "max_concurrent_users": max_vu,
            "multi_source_peak_vusers_sum": int(multi_vu_sum),
            "multi_source_peak_breakdown": multi_vu_breakdown,
            "peak_load_vu_threshold": int(round(peak_thr)) if peak_thr else 0,
            "transaction_sla_p90_peak": tx_sla_peak,
            "report_header": report_header,
            "feature_extraction": feature_extraction,
        }
        
        return JMeterMetrics(
            total_samples=total_samples,
            total_errors=errors,
            error_rate=error_rate,
            throughput=throughput,
            latency=latency_stats,
            sample_time=sample_time_stats,
            connect_time=connect_time_stats,
            response_codes=dict(response_codes),
            labels={**transaction_stats, **request_stats},
            summary=summary
        )
    
    @staticmethod
    def _calculate_stats(values: np.ndarray) -> Dict[str, float]:
        """Calculate percentile statistics efficiently with skewness"""
        if len(values) == 0:
            # None = no successful samples — do not treat as 0 ms "excellent" latency
            return {
                "mean": None, "median": None, "p70": None, "p75": None, "p80": None,
                "p90": None, "p95": None, "p99": None, "min": None, "max": None,
                "std": None, "skewness": 0.0
            }
        
        # Calculate skewness using scipy's formula if available, else manual
        try:
            from scipy import stats as scipy_stats
            skewness = float(scipy_stats.skew(values))
        except ImportError:
            # Manual calculation: Pearson's moment coefficient of skewness
            mean = np.mean(values)
            std = np.std(values)
            if std > 0:
                skewness = float(np.mean(((values - mean) / std) ** 3))
            else:
                skewness = 0.0
        
        return {
            "mean": float(np.mean(values)),
            "median": float(np.median(values)),
            "p70": float(np.percentile(values, 70)),
            "p75": float(np.percentile(values, 75)),
            "p80": float(np.percentile(values, 80)),
            "p90": float(np.percentile(values, 90)),
            "p95": float(np.percentile(values, 95)),
            "p99": float(np.percentile(values, 99)),
            "min": float(np.min(values)),
            "max": float(np.max(values)),
            "std": float(np.std(values)),
            "skewness": skewness
        }
    
    @staticmethod
    def _interpret_skewness(skewness: float, metric_name: str = "response time", metrics: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Interpret skewness value and provide actionable insights based on ACTUAL data
        
        Skewness interpretation:
        - ~0: Normal distribution (symmetric)
        - >0: Right-skewed (positive skew) - most values low, some very high
        - <0: Left-skewed (negative skew) - most values high, some very low
        """
        if metrics is None:
            metrics = {}
        
        # Extract actual metrics for dynamic analysis
        avg_response = metrics.get("avg_response", 0)
        p95_response = metrics.get("p95_response", 0)
        p99_response = metrics.get("p99_response", 0)
        max_response = metrics.get("max_response", 0)
        error_rate = metrics.get("error_rate", 0)
        throughput = metrics.get("throughput", 0)
        transaction_stats = metrics.get("transaction_stats", {})
        request_stats = metrics.get("request_stats", {})
        response_codes = metrics.get("response_codes", {})
        sla_compliance = metrics.get("sla_compliance", 0)
        
        if abs(skewness) < 0.5:
            # Normal distribution - Ideal situation
            return {
                "type": "Normal Distribution",
                "skewness_value": round(skewness, 3),
                "shape": "Symmetric bell-shaped curve",
                "distribution_icon": "📊",
                "severity": "success",
                "observations": [
                    f"Most {metric_name}s are clustered around the average",
                    "Very few extreme slow requests",
                    "Balanced distribution across all percentiles"
                ],
                "interpretation": {
                    "status": "✅ System is stable",
                    "predictability": "✅ Predictable behavior",
                    "infrastructure": "✅ Infrastructure is properly tuned",
                    "performance_spikes": "✅ No major performance spikes"
                },
                "business_impact": "Optimal performance - users experience consistent response times"
            }
        elif skewness > 0.5:
            # Right-skewed (Positively skewed) - VERY COMMON in performance tests
            # Generate ACTUAL ROOT CAUSES based on performance behavior patterns
            severity = "critical" if skewness > 2 else ("danger" if skewness > 1 else "warning")
            
            # Generate root causes using pattern-based analysis (NO SYMPTOMS)
            root_causes = JMeterAnalyzerV2._generate_infrastructure_root_causes(
                avg_response, p95_response, p99_response, max_response,
                error_rate, throughput, sla_compliance, skewness
            )
            
            return {
                "type": "Positively Skewed (Right Skewed)",
                "skewness_value": round(skewness, 3),
                "shape": "Long tail on the right side",
                "distribution_icon": "⚠️",
                "severity": severity,
                "observations": [
                    f"Most {metric_name}s are fast (low values)",
                    f"Some {metric_name}s are extremely slow (high values)",
                    "Asymmetric distribution with outliers on the high end",
                    f"P95: {p95_response:.2f}s, P99: {p99_response:.2f}s, Max: {max_response:.2f}s"
                ],
                "interpretation": {
                    "bottlenecks": "⚠️ System has performance bottlenecks",
                    "user_experience": "⚠️ Some users experience very slow responses",
                    "consistency": "⚠️ Inconsistent performance across requests",
                    "tail_latency": "❌ High tail latency detected"
                },
                "possible_causes": root_causes,  # Pattern-based root causes (WHY)
                "business_impact": "Customer experience varies - majority get fast service, but some users face frustrating delays",
                "urgency": "High" if skewness > 1.5 else "Medium"
            }
        else:  # skewness < -0.5
            # Left-skewed (Negatively skewed) - Rare in performance tests
            return {
                "type": "Negatively Skewed (Left Skewed)",
                "skewness_value": round(skewness, 3),
                "shape": "Long tail on the left side",
                "distribution_icon": "🔍",
                "severity": "info",
                "observations": [
                    f"Most {metric_name}s are high",
                    f"Few {metric_name}s are exceptionally low",
                    "Uncommon pattern in performance testing"
                ],
                "interpretation": {
                    "status": "ℹ️ Unusual distribution pattern",
                    "investigation": "🔍 Requires investigation",
                    "data_quality": "⚠️ Check data quality and test configuration"
                },
                "possible_causes": [
                    "Caching effects - most requests served from cache",
                    "Load test warm-up period not excluded",
                    "Test configuration issues",
                    "Data sampling bias"
                ],
                "business_impact": "Unusual pattern - validate test methodology"
            }
    
    @staticmethod
    def _generate_infrastructure_root_causes(
        avg_response: float,
        p95_response: float, 
        p99_response: float,
        max_response: float,
        error_rate: float,
        throughput: float,
        sla_compliance: float,
        skewness: float
    ) -> List[str]:
        """
        Generate ACTUAL ROOT CAUSES based on performance behavior patterns
        Analyzes 20 performance patterns and returns 5-8 most relevant root causes
        
        Returns ROOT CAUSES (WHY), not symptoms or recommendations
        Updated: v3.0.8 - Pattern-based root cause detection
        """
        root_causes = []
        
        # Calculate key indicators
        p95_avg_ratio = p95_response / avg_response if avg_response > 0 else 0
        p99_avg_ratio = p99_response / avg_response if avg_response > 0 else 0
        
        # ========== PATTERN DETECTION ==========
        # Analyze data against 20 performance behavior patterns
        
        # PATTERN 5: P95/P99 very high but average normal (random spikes)
        if p95_avg_ratio > 4 or p99_avg_ratio > 5:
            root_causes.extend([
                "Slow third-party APIs causing intermittent delays",
                "DNS resolution delays",
                "Lock contention in database or application",
                "JVM Full Garbage Collection pauses",
                "Network jitter or packet loss"
            ])
        
        # PATTERN 6: Only specific transactions slow (e.g., login/search/checkout)
        # Detected by checking if some transactions are significantly slower
        if skewness > 1 and avg_response > 1:
            root_causes.extend([
                "Slow SQL queries in specific endpoints",
                "Missing database indexes on frequently queried tables",
                "Full table scans instead of indexed lookups",
                "External service call embedded in specific API",
                "Heavy serialization overhead in specific transaction"
            ])
        
        # PATTERN 10: Throughput stops increasing after certain users
        if throughput < 100 and avg_response > 1:
            root_causes.extend([
                "Thread pool size limit reached",
                "Database connection pool limit exhausted",
                "Request queue size limit hit",
                "Load balancer connection limit reached"
            ])
        
        # PATTERN 7: All transactions slow simultaneously
        if avg_response > 2 and sla_compliance < 70:
            root_causes.extend([
                "CPU saturation across all servers",
                "Disk I/O bottleneck on storage layer",
                "Network latency between application and database",
                "Infrastructure throttling or resource limits",
                "Autoscaling failed to trigger or insufficient"
            ])
        
        # PATTERN 8: CPU low but response time high (system waiting, not processing)
        if throughput < 75 and avg_response > 1.5:
            root_causes.extend([
                "Thread pool starvation - threads waiting for resources",
                "Database lock contention causing waits",
                "Blocking I/O operations not using async patterns",
                "Application waiting for external API responses",
                "Connection pool exhausted - waiting for available connections"
            ])
        
        # PATTERN 17: Database bottleneck indicators
        if p99_avg_ratio > 3 and skewness > 1:
            root_causes.extend([
                "Query optimizer choosing bad execution plan",
                "Missing or outdated table statistics",
                "Lock escalation from row to table level",
                "Heavy reporting queries running concurrently"
            ])
        
        # PATTERN 2: Performance degrades continuously over time
        if skewness > 1.5:
            root_causes.extend([
                "Memory leak - heap growing without bounds",
                "Database connection leak - connections not returned to pool",
                "Session accumulation - old sessions not cleared",
                "Cache filling without eviction policy",
                "File handles or socket connections not released"
            ])
        
        # PATTERN 4: System starts throwing errors
        if error_rate > 2:
            root_causes.extend([
                "Connection pool completely exhausted",
                "Thread pool completely exhausted",
                "Too many open file descriptors or sockets",
                "Rate limiting triggered by dependency",
                "External API failure cascading to application"
            ])
        
        # PATTERN 14: Sudden latency spikes
        if max_response > p95_response * 5:
            root_causes.extend([
                "Full Garbage Collection pause freezing application",
                "Container or pod restart during autoscaling",
                "Network routing change or failover event"
            ])
        
        # PATTERN 1: Linear increase in response time with load
        if avg_response > 1.5 and throughput < 100:
            root_causes.extend([
                "Insufficient server capacity for load",
                "Synchronous processing blocking threads",
                "No horizontal scaling configured",
                "Network bandwidth limitation reached"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_causes = []
        for cause in root_causes:
            if cause not in seen:
                seen.add(cause)
                unique_causes.append(cause)
        
        # Return top 5-8 most relevant root causes
        if not unique_causes:
            # Default causes if no patterns detected
            unique_causes = [
                "Query optimizer choosing bad execution plan",
                "Missing database indexes on frequently queried tables",
                "Thread pool size limit reached",
                "Database connection pool limit exhausted",
                "CPU saturation across all servers",
                "Memory leak - heap growing without bounds"
            ]
        
        return unique_causes[:8]
    
    @staticmethod
    def _analyze_by_label(data: List[Dict]) -> tuple:
        """Group by label: transaction controllers (URL empty/null) vs HTTP samples (URL set)."""
        transactions = defaultdict(list)
        requests = defaultdict(list)
        
        for d in data:
            label = d.get("label", "Unknown")
            if JMeterAnalyzerV2._is_transaction_controller_row(d):
                transactions[label].append(d)
            else:
                requests[label].append(d)
        
        def analyze_group(group_data: Dict[str, List]) -> Dict:
            stats = {}
            for label, items in group_data.items():
                response_times = [
                    d.get("sample_time", 0) for d in items
                    if d.get("sample_time") is not None and JMeterAnalyzerV2._include_in_response_time_stats(d)
                ]
                errors = sum(1 for d in items if is_jmeter_error_outcome(d))
                
                if response_times:
                    rt_stats = JMeterAnalyzerV2._calculate_stats(np.array(response_times, dtype=float))
                    stats[label] = {
                        "count": len(items),
                        "errors": errors,
                        "error_rate": (errors / len(items) * 100) if items else 0.0,
                        "avg_response": rt_stats["mean"],
                        "median": rt_stats["median"],
                        "p70": rt_stats["p70"],
                        "p75": rt_stats["p75"],
                        "p80": rt_stats["p80"],
                        "p90": rt_stats["p90"],
                        "p95": rt_stats["p95"],
                        "p99": rt_stats["p99"],
                        "min": rt_stats["min"],
                        "max": rt_stats["max"]
                    }
                else:
                    # No successful samples: do not use 0 ms as a "fast" result in reports
                    na = None
                    stats[label] = {
                        "count": len(items),
                        "errors": errors,
                        "error_rate": (errors / len(items) * 100) if items else 0.0,
                        "avg_response": na, "median": na, "p70": na, "p75": na, "p80": na,
                        "p90": na, "p95": na, "p99": na, "min": na, "max": na
                    }
            return stats
        
        return analyze_group(transactions), analyze_group(requests)
    
    @staticmethod
    def _resolve_score_targets(targets: Optional[Dict[str, float]]) -> Dict[str, float]:
        """Convert run targets (ms, %) to score calculation format (seconds, decimals)."""
        if not targets:
            return {
                "availability": 99,
                "avg_response_sec": 2,
                "error_rate": 0.01,  # 1% as decimal
                "throughput": 100,
                "p95_sec": 3,
                "sla_compliance": 95
            }
        return {
            "availability": float(targets.get("availability_target") or 99),
            "avg_response_sec": (float(targets.get("avg_response_time_target") or 2000)) / 1000.0,
            "error_rate": (float(targets.get("error_rate_target") or 1)) / 100.0,  # % to decimal
            "throughput": float(targets.get("throughput_target") or 100),
            "p95_sec": (float(targets.get("p95_target") or 3000)) / 1000.0,
            "sla_compliance": float(targets.get("sla_compliance_target") or 95)
        }

    @staticmethod
    def _resolve_display_targets(targets: Optional[Dict[str, float]]) -> Dict[str, float]:
        """Build targets dict for report display (availability, response_time ms, etc.)."""
        if not targets:
            return {
                "availability": 99,
                "response_time": 2000,
                "error_rate": 1,
                "throughput": 100,
                "p95_percentile": 3000,
                "sla_compliance": 95
            }
        return {
            "availability": float(targets.get("availability_target") or 99),
            "response_time": float(targets.get("avg_response_time_target") or 2000),
            "error_rate": float(targets.get("error_rate_target") or 1),
            "throughput": float(targets.get("throughput_target") or 100),
            "p95_percentile": float(targets.get("p95_target") or 3000),
            "sla_compliance": float(targets.get("sla_compliance_target") or 95)
        }

    @staticmethod
    def _calculate_scores(success_rate: float, error_rate: float, avg_response: float,
                          p95_response: float, throughput: float, sla_compliance: float,
                          score_targets: Optional[Dict[str, float]] = None) -> Dict[str, float]:
        """Calculate category scores (0-100). Uses score_targets when provided."""
        def score_metric(value: float, target: float, higher_better: bool) -> float:
            if higher_better:
                return min(100, max(0, (value / target) * 100)) if target > 0 else 0
            # Lower is better (error rate as decimal, latency in seconds).
            # value == 0 is best achievable (e.g. 0% errors) and must score 100, not 0.
            if value <= 0:
                return 100.0
            if target <= 0:
                return 0.0
            return min(100.0, max(0.0, (target / value) * 100.0))

        t = score_targets or JMeterAnalyzerV2._resolve_score_targets(None)
        availability_score = score_metric(success_rate, t["availability"], True)
        response_time_score = score_metric(avg_response, t["avg_response_sec"], False)
        error_rate_score = score_metric(error_rate, t["error_rate"], False)
        throughput_score = score_metric(throughput, t["throughput"], True)
        p95_score = score_metric(p95_response, t["p95_sec"], False)
        sla_score = score_metric(sla_compliance, t["sla_compliance"], True)
        
        performance_score = (response_time_score + p95_score) / 2
        reliability_score = (availability_score + error_rate_score) / 2
        ux_score = sla_score
        scalability_score = throughput_score
        
        overall = (
            performance_score * 0.30 +
            reliability_score * 0.25 +
            ux_score * 0.25 +
            scalability_score * 0.20
        )
        
        return {
            "availability": round(availability_score, 2),
            "response_time": round(response_time_score, 2),
            "error_rate": round(error_rate_score, 2),
            "throughput": round(throughput_score, 2),
            "p95_percentile": round(p95_score, 2),
            "sla_compliance": round(sla_score, 2),
            "performance": round(performance_score, 2),
            "reliability": round(reliability_score, 2),
            "user_experience": round(ux_score, 2),
            "scalability": round(scalability_score, 2),
            "overall": round(overall, 2)
        }
    
    @staticmethod
    def _calculate_grade(score: float) -> tuple:
        """Calculate grade from score"""
        if score >= 90:
            return "A+", "success"
        elif score >= 80:
            return "A", "success"
        elif score >= 75:
            return "B+", "warning"
        elif score >= 70:
            return "B", "warning"
        elif score >= 65:
            return "C+", "warning"
        elif score >= 60:
            return "C", "warning"
        elif score >= 50:
            return "D", "danger"
        else:
            return "F", "danger"
    
    @staticmethod
    def _calculate_time_series(data: List[Dict], duration: float) -> List[Dict]:
        """
        One row per time bucket (default: 1 minute) for reports/tables. Uses all JTL rows (no pre-sampling).
        Adds throughput_pass / throughput_fail (req/s) per bucket. Downsample to ~50–55 points for the main chart
        is done in the HTML generator.
        """
        if not data or duration <= 0:
            return []
        ts_list = [d.get("timestamp", 0) for d in data if d.get("timestamp")]
        if not ts_list:
            return []
        min_ts = min(ts_list)
        # Bucket size: 60s for tests ≥1 min; otherwise one bucket over the run
        bucket_sec = 60.0 if duration >= 60.0 else max(1e-6, float(duration))
        n_buckets = max(1, int(math.ceil(duration / bucket_sec)))

        intervals = defaultdict(lambda: {
            "response_times": [],
            "vusers": [],
            "pass_count": 0,
            "fail_count": 0,
            "by_label": defaultdict(lambda: {"response_times": [], "pass_count": 0, "fail_count": 0, "has_url": False})
        })

        for d in data:
            ts = d.get("timestamp", 0)
            if not ts:
                continue
            time_offset = (ts - min_ts) / 1000.0
            interval_idx = int(time_offset / bucket_sec)
            interval_idx = min(max(0, interval_idx), n_buckets - 1)

            interval = intervals[interval_idx]
            interval["time"] = interval_idx * bucket_sec
            label = d.get("label", "Unknown")

            if d.get("sample_time") and JMeterAnalyzerV2._include_in_response_time_stats(d):
                interval["response_times"].append(d.get("sample_time", 0))
            if d.get("all_threads") is not None:
                interval["vusers"].append(d.get("all_threads", 0))

            if is_jmeter_error_outcome(d):
                interval["fail_count"] += 1
            else:
                interval["pass_count"] += 1

            label_data = interval["by_label"][label]
            if d.get("sample_time") and JMeterAnalyzerV2._include_in_response_time_stats(d):
                label_data["response_times"].append(d.get("sample_time", 0))
            if is_jmeter_error_outcome(d):
                label_data["fail_count"] += 1
            else:
                label_data["pass_count"] += 1

            response_msg = d.get("response_message", "")
            is_transaction_controller = is_jmeter_transaction_controller_by_url(
                d.get("url")
            ) or ("Number of samples in transaction" in str(response_msg))
            if not is_transaction_controller:
                label_data["has_url"] = True

        time_series = []
        for idx in sorted(intervals.keys()):
            interval = intervals[idx]
            rt_values = interval["response_times"]
            vuser_values = interval["vusers"]
            p = interval["pass_count"]
            f = interval["fail_count"]
            tot = p + f
            by_label_data = {}
            for label, label_info in interval["by_label"].items():
                label_rt_values = label_info["response_times"]
                label_count = label_info["pass_count"] + label_info["fail_count"]
                by_label_data[label] = {
                    "avg_response_time": round(np.mean(label_rt_values) / 1000.0, 2) if label_rt_values else 0.0,
                    "throughput": label_count,
                    "has_url": label_info.get("has_url", False)
                }

            tput_total = (tot / bucket_sec) if bucket_sec > 0 else 0.0
            tput_pass = (p / bucket_sec) if bucket_sec > 0 else 0.0
            tput_fail = (f / bucket_sec) if bucket_sec > 0 else 0.0
            time_series.append({
                "time": round(interval["time"], 1),
                "bucket_seconds": round(bucket_sec, 3),
                "avg_response_time": round(np.mean(rt_values) / 1000.0, 2) if rt_values else 0.0,
                "vusers": round(float(np.mean(vuser_values)), 0) if vuser_values else 0.0,
                "throughput": round(tput_total, 2),
                "throughput_pass": round(tput_pass, 2),
                "throughput_fail": round(tput_fail, 2),
                "pass_count": p,
                "fail_count": f,
                "error_rate_pct": round(100.0 * f / tot, 2) if tot else 0.0,
                "by_label": by_label_data
            })

        return time_series
    
    @staticmethod
    def _calculate_response_time_distribution(data: List[Dict]) -> Dict[str, float]:
        """Distribution of response times among successful samples only (percent of passed samples per bucket)."""
        passed = [d for d in data if JMeterAnalyzerV2._include_in_response_time_stats(d)]
        total = len(passed)
        if total == 0:
            return {"under_1s": 0, "1_to_2s": 0, "2_to_3s": 0, "3_to_5s": 0, "5_to_10s": 0, "over_10s": 0}
        
        return {
            "under_1s": (sum(1 for d in passed if d.get("sample_time", 0) < 1000) / total * 100),
            "1_to_2s": (sum(1 for d in passed if 1000 <= d.get("sample_time", 0) < 2000) / total * 100),
            "2_to_3s": (sum(1 for d in passed if 2000 <= d.get("sample_time", 0) < 3000) / total * 100),
            "3_to_5s": (sum(1 for d in passed if 3000 <= d.get("sample_time", 0) < 5000) / total * 100),
            "5_to_10s": (sum(1 for d in passed if 5000 <= d.get("sample_time", 0) < 10000) / total * 100),
            "over_10s": (sum(1 for d in passed if d.get("sample_time", 0) >= 10000) / total * 100)
        }
    
    @staticmethod
    def _identify_issues(error_rate: float, avg_response: float, sla_compliance: float,
                        transaction_stats: Dict, request_stats: Dict) -> List[Dict]:
        """Identify all performance issues (critical, moderate, and minor)"""
        issues = []
        
        # Critical Issues (P0)
        if error_rate > 5:
            issues.append({
                "title": f"High Error Rate - {error_rate:.2f}%",
                "impact": f"{error_rate:.2f}% of requests failing",
                "affected": "System-wide",
                "priority": "P0 CRITICAL",
                "timeline": "1-2 weeks",
                "example": f"Error rate exceeds acceptable threshold of 5%",
                "recommendation": "Conduct root cause analysis, implement error handling improvements, and add monitoring",
                "business_benefit": "Improved system reliability and user trust"
            })
        
        if avg_response > 5:
            issues.append({
                "title": f"Very Slow Response Times - {avg_response:.1f}s Average",
                "impact": "Severely poor user experience",
                "affected": "System-wide",
                "priority": "P0 CRITICAL",
                "timeline": "2-4 weeks",
                "example": f"Average response time of {avg_response:.1f}s is unacceptable",
                "recommendation": "Optimize database queries, implement caching, reduce payload sizes, and scale infrastructure",
                "business_benefit": "Significantly improved user satisfaction and retention"
            })
        
        # High Priority Issues (P1)
        if 3 < avg_response <= 5:
            issues.append({
                "title": f"Slow Response Times - {avg_response:.1f}s Average",
                "impact": "Poor user experience",
                "affected": "System-wide",
                "priority": "P1 HIGH",
                "timeline": "2-4 weeks",
                "example": f"Average response time of {avg_response:.1f}s exceeds target of 2s",
                "recommendation": "Optimize slow endpoints, implement caching strategies, and review database performance",
                "business_benefit": "Improved user experience and reduced bounce rate"
            })
        
        if sla_compliance < 80:
            issues.append({
                "title": f"Low SLA Compliance - {sla_compliance:.1f}%",
                "impact": "Majority of requests not meeting SLA",
                "affected": "System-wide",
                "priority": "P1 HIGH",
                "timeline": "4-6 weeks",
                "example": f"Only {sla_compliance:.1f}% of requests meet 2s SLA target",
                "recommendation": "Identify and optimize slow transactions, improve infrastructure capacity",
                "business_benefit": "Better SLA compliance and customer satisfaction"
            })
        
        # Moderate Issues (P2)
        if 1 < error_rate <= 5:
            issues.append({
                "title": f"Elevated Error Rate - {error_rate:.2f}%",
                "impact": f"{error_rate:.2f}% of requests experiencing failures",
                "affected": "System-wide",
                "priority": "P2 MODERATE",
                "timeline": "4-6 weeks",
                "example": f"Error rate of {error_rate:.2f}% is above ideal threshold",
                "recommendation": "Review error logs, improve error handling, and enhance monitoring",
                "business_benefit": "Reduced error rate and improved system stability"
            })
        
        if 2 < avg_response <= 3:
            issues.append({
                "title": f"Moderate Response Times - {avg_response:.1f}s Average",
                "impact": "Response times could be improved",
                "affected": "System-wide",
                "priority": "P2 MODERATE",
                "timeline": "6-8 weeks",
                "example": f"Average response time of {avg_response:.1f}s is slightly above target",
                "recommendation": "Optimize key endpoints and consider performance tuning",
                "business_benefit": "Enhanced performance and user experience"
            })
        
        if 80 <= sla_compliance < 90:
            issues.append({
                "title": f"Moderate SLA Compliance - {sla_compliance:.1f}%",
                "impact": "SLA compliance below target",
                "affected": "System-wide",
                "priority": "P2 MODERATE",
                "timeline": "6-8 weeks",
                "example": f"SLA compliance of {sla_compliance:.1f}% is below 90% target",
                "recommendation": "Focus on optimizing slowest transactions and improving response time consistency",
                "business_benefit": "Improved SLA compliance and reliability"
            })
        
        # Check for slow transactions/requests
        all_stats = {**transaction_stats, **request_stats}
        for label, stats in all_stats.items():
            ar = stats.get("avg_response")
            if ar is None:
                continue
            avg_rt = float(ar) / 1000.0
            error_rate_label = stats.get('error_rate', 0)
            
            if avg_rt > 5:
                issues.append({
                    "title": f"Very Slow Transaction: {label} - {avg_rt:.1f}s",
                    "impact": "Severely impacts user experience for this transaction",
                    "affected": label,
                    "priority": "P1 HIGH",
                    "timeline": "2-4 weeks",
                    "example": f"Transaction '{label}' has average response time of {avg_rt:.1f}s",
                    "recommendation": f"Optimize transaction '{label}', review database queries, and consider caching",
                    "business_benefit": "Improved performance for specific user workflows"
                })
            elif avg_rt > 3:
                issues.append({
                    "title": f"Slow Transaction: {label} - {avg_rt:.1f}s",
                    "impact": "Impacts user experience for this transaction",
                    "affected": label,
                    "priority": "P2 MODERATE",
                    "timeline": "4-6 weeks",
                    "example": f"Transaction '{label}' has average response time of {avg_rt:.1f}s",
                    "recommendation": f"Review and optimize transaction '{label}' performance",
                    "business_benefit": "Better performance for specific user actions"
                })
            
            if error_rate_label > 10:
                issues.append({
                    "title": f"High Error Rate for {label} - {error_rate_label:.1f}%",
                    "impact": f"{error_rate_label:.1f}% of requests failing for this transaction",
                    "affected": label,
                    "priority": "P1 HIGH",
                    "timeline": "2-4 weeks",
                    "example": f"Transaction '{label}' has {error_rate_label:.1f}% error rate",
                    "recommendation": f"Investigate and fix errors in transaction '{label}'",
                    "business_benefit": "Improved reliability for specific transaction"
                })
        
        return issues  # Return all issues, not limited to 5
    
    @staticmethod
    def _generate_recommendations(error_rate: float, avg_response: float, throughput: float) -> List[Dict]:
        """Generate improvement recommendations"""
        recommendations = []
        
        if avg_response > 2:
            recommendations.append({
                "category": "Performance",
                "priority": "High",
                "items": [
                    "Optimize database queries",
                    "Implement caching",
                    "Reduce payload sizes"
                ]
            })
        
        if error_rate > 1:
            recommendations.append({
                "category": "Reliability",
                "priority": "Critical",
                "items": [
                    "Root cause analysis",
                    "Implement error handling",
                    "Add monitoring"
                ]
            })
        
        return recommendations
    
    @staticmethod
    def _generate_roadmap(current_score: float) -> List[Dict]:
        """Generate improvement roadmap"""
        target_score = 95
        gap = target_score - current_score
        
        return [
            {
                "phase": "Phase 1: Critical Fixes",
                "target_grade": "B+",
                "actions": ["Fix critical errors", "Optimize slow endpoints"],
                "expected_impact": f"Improve score by {min(20, gap):.0f} points"
            }
        ]
    
    @staticmethod
    def _build_grade_reasons(scores: Dict, avg_response: float, success_rate: float,
                            error_rate: float, throughput: float, p95: float,
                            sla_compliance: float, overall_grade: str, grade_class: str) -> Dict:
        """Build grade reasons dictionary"""
        return {
            "performance": {
                "grade": JMeterAnalyzerV2._calculate_grade(scores["performance"])[0],
                "score": scores["performance"],
                "reason": f"{avg_response:.1f}s avg, {p95:.1f}s 95th percentile",
                "class": JMeterAnalyzerV2._calculate_grade(scores["performance"])[1],
                "name": "Performance",
                "icon": "⚡",
                "description": "Response time performance",
                "weight": "30%"
            },
            "reliability": {
                "grade": JMeterAnalyzerV2._calculate_grade(scores["reliability"])[0],
                "score": scores["reliability"],
                "reason": f"{success_rate:.1f}% uptime, {error_rate:.2f}% error rate",
                "class": JMeterAnalyzerV2._calculate_grade(scores["reliability"])[1],
                "name": "Reliability",
                "icon": "🛡️",
                "description": "System stability",
                "weight": "25%"
            },
            "user_experience": {
                "grade": JMeterAnalyzerV2._calculate_grade(scores["user_experience"])[0],
                "score": scores["user_experience"],
                "reason": f"{sla_compliance:.1f}% meet 2-second SLA",
                "class": JMeterAnalyzerV2._calculate_grade(scores["user_experience"])[1],
                "name": "User Experience",
                "icon": "👥",
                "description": "SLA compliance",
                "weight": "25%"
            },
            "scalability": {
                "grade": JMeterAnalyzerV2._calculate_grade(scores["scalability"])[0],
                "score": scores["scalability"],
                "reason": f"{throughput:.1f} req/s throughput",
                "class": JMeterAnalyzerV2._calculate_grade(scores["scalability"])[1],
                "name": "Scalability",
                "icon": "📈",
                "description": "System capacity",
                "weight": "20%"
            }
        }
    
    @staticmethod
    def _get_grade_title(grade: str) -> str:
        """Get business-focused grade title"""
        titles = {
            "A+": "Business Accelerator",
            "A": "Production Ready",
            "B+": "Acceptable but Watch Closely",
            "B": "Customer Experience Risk",
            "C+": "Revenue Leakage State",
            "C": "Business Impact Warning",
            "D": "Business Critical Failure",
            "F": "Production Blocker"
        }
        return titles.get(grade, "Unknown")
    
    @staticmethod
    def _get_grade_description(grade: str) -> str:
        """Get comprehensive business-focused grade description"""
        descriptions = {
            "A+": "The application is not just stable — it is a competitive advantage. Pages feel instant, users trust the platform, leading to higher conversion rates and engagement.",
            "A": "System meets and slightly exceeds expected customer experience standards. Fast response with minor delays only under peak usage.",
            "B+": "Customers will use it… but they will notice slowness. Occasional slow pages and some frustration, especially for mobile users.",
            "B": (
                "Customers can complete journeys, but the experience is frustrating. "
                "Noticeable delays and page reload attempts lead to increased bounce rates."
            ),
            "C+": "The system is working… but customers are silently leaving. Slow checkout and timeout during payment cause major cart abandonment.",
            "C": "System has severe performance degradation. Multiple critical issues affecting user experience and revenue.",
            "D": "Launching this version will directly impact revenue and reputation. Users cannot complete journeys, experiencing frequent errors/timeouts.",
            "F": "System is experiencing critical failures equivalent to a production outage. Immediate intervention required."
        }
        return descriptions.get(grade, "Unknown")
    
    @staticmethod
    def _get_business_impact(grade: str) -> Dict[str, Any]:
        """Get comprehensive business impact and decision for each grade"""
        business_impacts = {
            "A+": {
                "score_range": "90-100",
                "executive_meaning": "The application is not just stable — it is a competitive advantage",
                "customer_impact": [
                    "Pages feel instant",
                    "Users trust the platform",
                    "High engagement",
                    "Positive brand perception"
                ],
                "business_outcome": [
                    "Higher conversion rate",
                    "Higher session duration",
                    "Increased repeat users",
                    "Better app store / customer ratings",
                    "Marketing campaigns can be safely scaled"
                ],
                "release_decision": "🟢 Immediate Release Approved",
                "operational_risk": "Very Low",
                "business_actions": [
                    "Launch promotions",
                    "High traffic events (sale, offers, campaigns)",
                    "New geography rollout"
                ],
                "tech_indicators": [
                    "Server CPU < 60%",
                    "No error spikes",
                    "P95 latency within SLA",
                    "Core Web Vitals (LCP, INP, CLS) in green"
                ]
            },
            "A": {
                "score_range": "80-89",
                "executive_meaning": "System meets and slightly exceeds expected customer experience standards",
                "customer_impact": [
                    "Fast response",
                    "Minor delays under peak usage only"
                ],
                "business_outcome": [
                    "Stable conversions",
                    "Good user retention",
                    "Safe for production traffic"
                ],
                "release_decision": "🟢 Release with Monitoring",
                "operational_risk": "Low",
                "risk_note": "If traffic increases suddenly (marketing, festive season), degradation may start",
                "business_actions": [
                    "Proceed with launch",
                    "Avoid aggressive marketing spike without scaling"
                ]
            },
            "B+": {
                "score_range": "75-79",
                "executive_meaning": "Customers will use it… but they will notice slowness",
                "customer_impact": [
                    "Occasional slow pages",
                    "Some frustration",
                    "Mobile users most affected"
                ],
                "business_outcome": [
                    "3–8% potential conversion drop",
                    "Cart abandonment increases",
                    "Customer support tickets rise"
                ],
                "release_decision": "🟡 Conditional Release (Business Approval Required)",
                "operational_risk": "Moderate",
                "tech_indicators": [
                    "P95 latency high",
                    "APIs slow under concurrency",
                    "Lighthouse score yellow",
                    "DB waits or connection pool saturation"
                ],
                "business_actions": [
                    "Release only if deadline critical",
                    "Avoid campaigns",
                    "Add war room monitoring"
                ]
            },
            "B": {
                "score_range": "70-74",
                "executive_meaning": "Customers can complete journeys, but the experience is frustrating",
                "customer_impact": [
                    "Noticeable delays",
                    "Page reload attempts",
                    "Mobile churn"
                ],
                "business_outcome": [
                    "Revenue leakage",
                    "Increased bounce rate",
                    "Poor customer reviews"
                ],
                "release_decision": "🟠 Release Only with Business Sign-Off",
                "operational_risk": "High during peak traffic",
                "business_translation": "This is not a technical issue anymore — this is a revenue impact condition",
                "business_actions": [
                    "Limit concurrent users",
                    "Use traffic throttling",
                    "Disable heavy features"
                ]
            },
            "C+": {
                "score_range": "65-69",
                "executive_meaning": "The system is working… but customers are silently leaving",
                "customer_impact": [
                    "Slow checkout",
                    "Timeout during payment",
                    "App appears unreliable"
                ],
                "business_outcome": [
                    "Major cart abandonment",
                    "Payment failures",
                    "Customer churn",
                    "Brand damage"
                ],
                "release_decision": "🔴 Release Not Recommended",
                "operational_risk": "Very High",
                "symptoms": [
                    "Spike in support calls",
                    "Payment complaints",
                    "Social media negativity"
                ],
                "real_interpretation": "The system is technically 'up' but commercially 'failing'"
            },
            "C": {
                "score_range": "60-64",
                "executive_meaning": "System is experiencing severe performance degradation",
                "customer_impact": [
                    "Frequent timeouts",
                    "Transaction failures",
                    "User abandonment"
                ],
                "business_outcome": [
                    "Direct revenue loss",
                    "Brand reputation damage",
                    "SLA breach risk"
                ],
                "release_decision": "🔴 Release Blocked - Critical Issues",
                "operational_risk": "Critical"
            },
            "D": {
                "score_range": "50-59",
                "executive_meaning": "Launching this version will directly impact revenue and reputation",
                "customer_impact": [
                    "Users cannot complete journeys",
                    "Errors/timeouts frequent"
                ],
                "business_outcome": [
                    "Direct revenue loss",
                    "SLA breach penalties",
                    "Possible contractual violations"
                ],
                "release_decision": "⛔ Release Blocked (Go-Live Stopper)",
                "operational_risk": "Critical",
                "symptoms": [
                    "Login failures",
                    "Checkout failures",
                    "API breakdowns",
                    "High 5xx errors"
                ],
                "management_translation": "This is equivalent to a partial production outage waiting to happen"
            },
            "F": {
                "score_range": "0-49",
                "executive_meaning": "Critical system failure - immediate intervention required",
                "customer_impact": [
                    "Service unavailable",
                    "Complete transaction failures"
                ],
                "business_outcome": [
                    "Complete revenue halt",
                    "Severe brand damage",
                    "Regulatory compliance issues"
                ],
                "release_decision": "⛔ PRODUCTION BLOCKER",
                "operational_risk": "Emergency"
            }
        }
        return business_impacts.get(grade, {
            "score_range": "Unknown",
            "executive_meaning": "Grade not recognized",
            "release_decision": "Unknown",
            "operational_risk": "Unknown"
        })
    
    @staticmethod
    def _get_grade_range(grade: str) -> str:
        """Get grade score range"""
        ranges = {
            "A+": "90-100",
            "A": "80-89",
            "B+": "75-79",
            "B": "70-74",
            "C+": "65-69",
            "C": "60-64",
            "D": "50-59",
            "F": "0-49"
        }
        return ranges.get(grade, "Unknown")
    
    @staticmethod
    def _generate_phased_improvement_plan(
        current_grade: str, 
        current_score: float,
        scores: Dict[str, float],
        avg_response: float,
        error_rate: float,
        throughput: float,
        p95_response: float,
        sla_compliance: float,
        transaction_stats: Dict,
        request_stats: Dict
    ) -> Dict[str, Any]:
        """
        Generate a PHASED improvement plan to reach A+ grade (90+)
        Plan is dynamically generated based on current weaknesses
        """
        
        # Calculate gap to A+ (90)
        target_score = 90
        score_gap = target_score - current_score
        
        if current_score >= 90:
            return {
                "current_grade": current_grade,
                "current_score": round(current_score, 1),
                "target_grade": "A+",
                "target_score": 90,
                "status": "🎉 Already at A+ Grade!",
                "message": "Congratulations! Your system is performing at optimal levels. Focus on maintaining this performance.",
                "maintenance_actions": [
                    "Continue monitoring key metrics",
                    "Maintain infrastructure capacity",
                    "Regular performance regression testing",
                    "Keep dependencies updated",
                    "Document current configuration as best practice"
                ]
            }
        
        # Identify weak areas that need improvement
        weak_areas = []
        if scores.get("performance", 0) < 85:
            weak_areas.append(("performance", scores.get("performance", 0), "Response time and P95 latency"))
        if scores.get("reliability", 0) < 85:
            weak_areas.append(("reliability", scores.get("reliability", 0), "Error rate and success rate"))
        if scores.get("user_experience", 0) < 85:
            weak_areas.append(("user_experience", scores.get("user_experience", 0), "SLA compliance"))
        if scores.get("scalability", 0) < 85:
            weak_areas.append(("scalability", scores.get("scalability", 0), "Throughput capacity"))
        
        # Sort by score (weakest first)
        weak_areas.sort(key=lambda x: x[1])
        
        # Find slowest transactions for specific actions
        all_transactions = {**transaction_stats, **request_stats}
        slowest_transactions = []
        if all_transactions:
            slowest_transactions = sorted(
                [
                    (
                        name,
                        float(stats["avg_response"]) / 1000.0,
                        (float(stats["p95"]) / 1000.0) if stats.get("p95") is not None else 0.0,
                    )
                    for name, stats in all_transactions.items()
                    if stats.get("avg_response") is not None
                ],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        
        # Generate phased plan
        phases = []
        
        # PHASE 1: Critical/Immediate (Week 1-2)
        phase1_actions = []
        phase1_impact = 0
        
        if error_rate > 1:
            phase1_actions.append({
                "action": "Fix Critical Errors",
                "detail": f"Reduce error rate from {error_rate:.1f}% to <1%",
                "steps": [
                    "Analyze error logs for top 5 error patterns",
                    "Fix HTTP 5xx errors (server-side failures)",
                    "Add retry logic for transient failures",
                    "Implement circuit breakers for failing dependencies"
                ],
                "expected_impact": "+5-8 points"
            })
            phase1_impact += 6.5
        
        if avg_response > 3:
            phase1_actions.append({
                "action": "Reduce Slowest API Response Times",
                "detail": f"Target: Bring average from {avg_response:.2f}s to <2s",
                "steps": [
                    f"Optimize slowest endpoint: {slowest_transactions[0][0] if slowest_transactions else 'N/A'} ({slowest_transactions[0][1]:.2f}s)" if slowest_transactions else "Identify and optimize slowest transactions",
                    "Add database query indexes",
                    "Enable database connection pooling",
                    "Implement response caching for read-heavy endpoints"
                ],
                "expected_impact": "+8-12 points"
            })
            phase1_impact += 10
        elif avg_response > 2:
            phase1_actions.append({
                "action": "Optimize Response Times",
                "detail": f"Target: Reduce average from {avg_response:.2f}s to <1.5s",
                "steps": [
                    f"Optimize top 3 slowest endpoints: {', '.join([t[0][:30] for t in slowest_transactions[:3]])}" if slowest_transactions else "Profile and optimize slow transactions",
                    "Review and optimize database queries",
                    "Add caching layer (Redis/Memcached)",
                    "Compress API responses"
                ],
                "expected_impact": "+5-8 points"
            })
            phase1_impact += 6.5
        
        if not phase1_actions:
            phase1_actions.append({
                "action": "Fine-tune Existing Performance",
                "detail": "Incremental optimizations to reach next grade",
                "steps": [
                    "Profile application for hotspots",
                    "Optimize database query execution plans",
                    "Review and reduce API payload sizes",
                    "Enable HTTP/2 or HTTP/3"
                ],
                "expected_impact": "+3-5 points"
            })
            phase1_impact += 4
        
        ts1 = min(90, round(current_score + phase1_impact, 1))
        gr1 = JMeterAnalyzerV2._calculate_grade(ts1)[0]
        phases.append({
            "phase": "Phase 1: Critical Fixes",
            "timeline": "Week 1-2",
            "priority": "🔴 High",
            "actions": phase1_actions,
            "target_score": ts1,
            "expected_grade": gr1,
            "expected_outcome": (
                "Address the highest-impact errors and slow paths first. "
                f"After fixes and a targeted rerun, overall health score should move toward ~{ts1} ({gr1}) "
                "(exact gain depends on environment and fixes shipped)."
            ),
        })
        
        # PHASE 2: Major Improvements (Week 3-4)
        phase2_actions = []
        phase2_impact = 0
        current_after_phase1 = min(90, current_score + phase1_impact)
        
        if current_after_phase1 < 90:
            if sla_compliance < 95:
                phase2_actions.append({
                    "action": "Improve SLA Compliance",
                    "detail": f"Increase SLA compliance from {sla_compliance:.1f}% to >95%",
                    "steps": [
                        "Set response time SLO targets per endpoint",
                        "Implement timeout controls",
                        "Add autoscaling rules for traffic spikes",
                        "Optimize middleware and authentication layers"
                    ],
                    "expected_impact": "+3-5 points"
                })
                phase2_impact += 4
            
            if p95_response > 3:
                phase2_actions.append({
                    "action": "Reduce Tail Latency (P95/P99)",
                    "detail": f"Bring P95 from {p95_response:.2f}s to <2.5s",
                    "steps": [
                        "Identify and fix P95+ outliers",
                        "Optimize database connection handling",
                        "Implement request queuing with priorities",
                        "Add APM tools to trace slow requests"
                    ],
                    "expected_impact": "+4-6 points"
                })
                phase2_impact += 5
            
            if throughput < 100:
                phase2_actions.append({
                    "action": "Increase System Throughput",
                    "detail": f"Scale from {throughput:.0f} to >100 req/s",
                    "steps": [
                        "Horizontal scaling - add more instances",
                        "Optimize thread pool configuration",
                        "Enable async processing for long-running tasks",
                        "Load balance across multiple nodes"
                    ],
                    "expected_impact": "+3-5 points"
                })
                phase2_impact += 4
            
            if not phase2_actions:
                phase2_actions.append({
                    "action": "Advanced Performance Optimization",
                    "detail": "Push performance to A+ level",
                    "steps": [
                        "Implement comprehensive caching strategy",
                        "Optimize JSON serialization/deserialization",
                        "Enable gzip/brotli compression",
                        "Reduce memory allocations and GC pressure"
                    ],
                    "expected_impact": "+2-4 points"
                })
                phase2_impact += 3
        
        ts2 = min(90, round(current_after_phase1 + phase2_impact, 1))
        gr2 = JMeterAnalyzerV2._calculate_grade(ts2)[0]
        phases.append({
            "phase": "Phase 2: Major Improvements",
            "timeline": "Week 3-4",
            "priority": "🟡 Medium",
            "actions": phase2_actions,
            "target_score": ts2,
            "expected_grade": gr2,
            "expected_outcome": (
                "Broaden improvements across SLA compliance, tail latency, and sustained throughput. "
                f"Indicative post-phase score ~{ts2} ({gr2}), confirmed by a full regression load test."
            ),
        })
        
        # PHASE 3: Fine-tuning & Excellence (Week 5-6)
        phase3_actions = []
        current_after_phase2 = min(90, current_after_phase1 + phase2_impact)
        
        if current_after_phase2 < 90:
            phase3_actions = [{
                "action": "Infrastructure & Architecture Optimization",
                "detail": "Achieve A+ grade through infrastructure excellence",
                "steps": [
                    "Implement CDN for static assets",
                    "Database read replicas for query distribution",
                    "Enable connection pooling and keep-alive",
                    "Implement rate limiting and request throttling",
                    "Add monitoring and alerting for proactive issue detection"
                ],
                "expected_impact": f"+{round(90 - current_after_phase2, 1)} points to reach A+"
            }]
        else:
            phase3_actions = [{
                "action": "Maintain A+ Performance",
                "detail": "Sustain peak performance levels",
                "steps": [
                    "Continuous monitoring and alerting",
                    "Regular load testing",
                    "Performance regression testing in CI/CD",
                    "Capacity planning and scaling strategies",
                    "Regular performance audits"
                ],
                "expected_impact": "Maintain 90+ score"
            }]
        
        if current_after_phase2 < 90:
            eo3 = (
                "Close remaining gaps to the A+ target using infrastructure, caching, and operational guardrails. "
                f"Goal: reach ~90 (A+) from the current ~{current_after_phase2:.1f} trajectory."
            )
        else:
            eo3 = (
                "Sustain A+ levels with monitoring, regression load testing, and capacity reviews so improvements do not erode."
            )
        phases.append({
            "phase": "Phase 3: Excellence & Sustainability",
            "timeline": "Week 5-6",
            "priority": "🟢 Low",
            "actions": phase3_actions,
            "target_score": 90,
            "expected_grade": "A+",
            "expected_outcome": eo3,
        })
        
        # Calculate total estimated improvement
        total_expected_improvement = phase1_impact + phase2_impact + (90 - current_after_phase2 if current_after_phase2 < 90 else 0)
        final_expected_score = min(95, current_score + total_expected_improvement)
        
        return {
            "current_grade": current_grade,
            "current_score": round(current_score, 1),
            "target_grade": "A+",
            "target_score": 90,
            "score_gap": round(score_gap, 1),
            "total_phases": len(phases),
            "estimated_timeline": "4-6 weeks",
            "phases": phases,
            "final_expected_score": round(final_expected_score, 1),
            "weak_areas": [{"area": area[2], "current_score": round(area[1], 1)} for area in weak_areas],
            "success_metrics": [
                "Average response time < 1.5s",
                "P95 response time < 2.5s",
                "Error rate < 0.5%",
                "Success rate > 99.5%",
                "Throughput > 100 req/s",
                "SLA compliance > 95%"
            ]
        }


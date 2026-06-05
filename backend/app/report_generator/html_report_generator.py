from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import html
import json
import re
import numpy as np
from app.parsers.jtl_parser_v2 import JTLParserV2
from app.report_generator.graph_analyzer import GraphAnalyzer
from app.report_generator.deep_assessment import build_deep_assessment, performance_grading_methodology_html
from app.report_generator.grade_narrative import format_performance_grade_release_line
from app.report_generator.deep_report_html import (
    render_deep_system_health_body,
    render_kpi_grid,
    render_key_findings_list,
    render_overall_health_section,
    render_report_top_header,
    render_resolution_plan,
    render_structured_issues,
)
from app.report_generator.report_navigation import (
    build_report_navigation_html,
    report_navigation_css,
    report_navigation_js,
)
from app.report_generator.report_theme_css import build_jmeter_report_css

class HTMLReportGenerator:
    """Generate comprehensive HTML reports matching OfficerTrack format"""
    
    @staticmethod
    def format_time(ms: float) -> str:
        """Format milliseconds to readable time"""
        if ms is None:
            return "N/A"
        if ms >= 1000:
            return f"{ms/1000:.2f}s"
        return f"{ms:.0f}ms"
    
    @staticmethod
    def get_status_badge(value: float, target: float, metric_type: str) -> tuple:
        """Get status badge based on target"""
        if metric_type == "lower":
            if value <= target:
                return "SUCCESS", "badge-success"
            elif value <= target * 1.5:
                return "MARGINAL", "badge-warning"
            else:
                return "FAIL", "badge-danger"
        else:  # higher
            if value >= target:
                return "SUCCESS", "badge-success"
            elif value >= target * 0.8:
                return "ACCEPTABLE", "badge-warning"
            else:
                return "FAIL", "badge-danger"
    
    @staticmethod
    def _sec_from_ms_field(ms: Any) -> Optional[float]:
        """Convert aggregate millisecond field to seconds, or None if no data."""
        if ms is None:
            return None
        try:
            return float(ms) / 1000.0
        except (TypeError, ValueError):
            return None

    @staticmethod
    def format_sec_or_na(sec: Optional[float], decimals: int = 1) -> str:
        """Format seconds for summary cards; None means no successful latency samples."""
        if sec is None:
            return "N/A"
        return f"{sec:.{decimals}f} s"
    
    @staticmethod
    def _generate_feature_extraction_panel(fe: Any) -> str:
        """
        Supplemental panel: observational outliers + robust means vs unchanged primary metrics.
        """
        if not fe or not isinstance(fe, dict):
            return ""
        disc = fe.get("disclaimer") or {}
        pop = fe.get("populations") or {}
        out = fe.get("outlier_observations") or {}
        hints = fe.get("distribution_shape_hints") or {}
        rob = fe.get("supplemental_robust_comparison") or {}
        fences = out.get("fences_ms") or {}

        def esc(x: Any) -> str:
            return html.escape(str(x)) if x is not None else ""

        def fmt_ms(v: Any) -> str:
            if v is None:
                return "—"
            try:
                return f"{float(v) / 1000.0:.3f}s ({float(v):,.0f} ms)"
            except (TypeError, ValueError):
                return esc(v)

        primary_line = esc(disc.get("primary_metrics", ""))
        block_line = esc(disc.get("this_block", ""))
        pop_note = esc(pop.get("note", ""))
        hint_note = esc(hints.get("note", ""))
        rob_note = esc(rob.get("interpretation", ""))

        wlim = rob.get("winsorize_limits") or {}
        trim_p = rob.get("trim_proportion_each_tail")

        m_gt_p90 = hints.get("mean_exceeds_p90")
        tail_callout = ""
        if m_gt_p90 is True:
            tail_callout = (
                '<p class="latency-analytics-callout"><strong>Shape signal:</strong> Mean response time is above the P90 — '
                "a minority of much slower requests is stretching the average. Primary metrics still include every eligible row; "
                "use supplemental means only as a comparison.</p>"
            )

        tr = pop.get("total_requests_in_run", "—")
        rw = pop.get("rows_used_for_response_time_aggregates", "—")
        tr_s = f"{tr:,}" if isinstance(tr, int) else esc(tr)
        rw_s = f"{rw:,}" if isinstance(rw, int) else esc(rw)

        return f'''
<section id="section-latency-analytics" class="section latency-analytics-section">
    <h2>Latency distribution analytics</h2>
    <p class="muted"><strong>Primary metrics</strong> in this report (mean, percentiles, SLA, error rate, scoring) use the full, unfiltered execution data for their definitions. Nothing here replaces those values.</p>
    <div class="latency-analytics-disclaimer">
        <p><strong>Raw / official statistics:</strong> {primary_line}</p>
        <p><strong>This section:</strong> {block_line}</p>
    </div>
    <p class="muted small">{pop_note}</p>
    <ul class="latency-analytics-meta">
        <li>Total requests in run: <strong>{tr_s}</strong></li>
        <li>Rows used for response-time aggregates (same as primary): <strong>{rw_s}</strong></li>
    </ul>
    <h3>Observational outliers (Tukey IQR)</h3>
    <p class="muted small">Flagged samples are counted for visibility only — they are <em>not</em> removed from mean, percentiles, or SLA.</p>
    <table class="latency-analytics-table">
        <tbody>
            <tr><td>Method</td><td>{esc(out.get("method", ""))} (k={esc(out.get("k", ""))})</td></tr>
            <tr><td>RT rows analyzed</td><td>{out.get("sample_count", 0):,}</td></tr>
            <tr><td>Above upper fence</td><td>{out.get("count_above_upper_fence", 0):,}</td></tr>
            <tr><td>Below lower fence</td><td>{out.get("count_below_lower_fence", 0):,}</td></tr>
            <tr><td>Total flagged either tail</td><td>{out.get("count_flagged_either_tail", 0):,} ({100.0 * float(out.get("fraction_flagged") or 0):.2f}%)</td></tr>
            <tr><td>Lower fence</td><td>{fmt_ms(fences.get("lower_fence_ms"))}</td></tr>
            <tr><td>Upper fence</td><td>{fmt_ms(fences.get("upper_fence_ms"))}</td></tr>
        </tbody>
    </table>
    <h3>Distribution hints (vs primary stats)</h3>
    <table class="latency-analytics-table">
        <tbody>
            <tr><td>Primary mean (official)</td><td>{fmt_ms(hints.get("primary_mean_ms"))}</td></tr>
            <tr><td>Primary P90 (official)</td><td>{fmt_ms(hints.get("primary_p90_ms"))}</td></tr>
        </tbody>
    </table>
    {tail_callout}
    <p class="muted small">{hint_note}</p>
    <h3>Supplemental robust comparison only</h3>
    <p class="muted small">{rob_note}</p>
    <table class="latency-analytics-table">
        <tbody>
            <tr><td>Trimmed mean ({trim_p if trim_p is not None else "—"} / tail)</td><td>{fmt_ms(rob.get("trimmed_mean_ms"))}</td></tr>
            <tr><td>Winsorized mean (limits {esc(wlim.get("lower_tail_fraction"))} / {esc(wlim.get("upper_tail_fraction"))} tails)</td><td>{fmt_ms(rob.get("winsorized_mean_ms"))}</td></tr>
        </tbody>
    </table>
</section>'''

    @staticmethod
    def generate_jmeter_html_report(
        metrics: Dict[str, Any],
        filename: str = "performance_report.html",
        progress_callback=None
    ) -> str:
        """Generate a comprehensive HTML report for JMeter results"""
        
        def update_progress(percent: int, message: str):
            """Helper to update progress if callback provided"""
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except:
                    pass
        
        update_progress(5, "Extracting metrics...")

        import os

        def _raw_rows_for_combined_report(m: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
            rec = m.get("jmeter_raw_records")
            if isinstance(rec, list) and rec:
                return rec
            pth = (m.get("summary") or {}).get("_jmeter_raw_source_path")
            if pth and os.path.isfile(str(pth)):
                try:
                    return JTLParserV2.parse(str(pth))
                except Exception:
                    return None
            return None

        raw_for_layout = _raw_rows_for_combined_report(metrics)
        if raw_for_layout:
            from app.report_generator.combined_load_report_analysis import build_combined_load_report_payload
            from app.report_generator.combined_load_report_html import render_combined_load_report_html

            update_progress(12, "Building combined load report payload…")
            payload = build_combined_load_report_payload(raw_for_layout, metrics)
            return render_combined_load_report_html(payload, progress_callback=progress_callback)

        # Extract metrics
        total_samples = metrics.get("total_samples", 0)
        error_rate_pct = metrics.get("error_rate", 0) * 100
        throughput = metrics.get("throughput", 0)
        
        summary = metrics.get("summary", {})
        success_rate = summary.get("success_rate", 0)
        test_duration_hours = summary.get("test_duration_hours", 0)
        
        sample_time = metrics.get("sample_time", {})
        avg_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("mean"))
        p70_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("p70"))
        p80_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("p80"))
        p90_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("p90"))
        p95_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("p95"))
        p99_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("p99"))
        median_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("median"))
        max_response = HTMLReportGenerator._sec_from_ms_field(sample_time.get("max"))
        
        scores = summary.get("scores", {})
        overall_score = summary.get("overall_score", 0)
        overall_grade = summary.get("overall_grade", "N/A")
        grade_class = summary.get("grade_class", "warning")
        grade_reasons = summary.get("grade_reasons", {})
        overall_grade_description = summary.get("overall_grade_description", {})
        
        sla_compliance_2s = summary.get("sla_compliance_2s", 0)
        sla_compliance_3s = summary.get("sla_compliance_3s", 0)
        sla_compliance_5s = summary.get("sla_compliance_5s", 0)
        
        response_time_dist = summary.get("response_time_distribution", {})
        transaction_stats = summary.get("transaction_stats", {})
        request_stats = summary.get("request_stats", {})
        all_issues = summary.get("critical_issues", [])  # Now contains all issues, not just critical
        recommendations = summary.get("recommendations", [])
        improvement_roadmap = summary.get("improvement_roadmap", [])
        
        response_codes = metrics.get("response_codes", {})
        targets = summary.get("targets", {})
        
        # Check if this is a consolidated report
        file_info = summary.get("file_info", [])
        consolidated_files = summary.get("consolidated_from_files", [])
        file_count = summary.get("file_count", 1)
        is_consolidated = file_count > 1
        
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Generate grade color
        grade_bg_color = "#fee2e2" if grade_class == "danger" else "#fef3c7" if grade_class == "warning" else "#dcfce7"
        grade_border_color = "var(--danger-color)" if grade_class == "danger" else "var(--warning-color)" if grade_class == "warning" else "var(--success-color)"
        
        update_progress(10, "Generating HTML sections...")
        
        # Generate HTML sections with progress updates
        update_progress(15, "Generating CSS...")
        css_content = HTMLReportGenerator._generate_css()
        
        update_progress(20, "Generating executive summary...")
        skewness_analysis = summary.get("skewness_analysis", {})
        business_impact = summary.get("business_impact", {})
        deep_ctx = build_deep_assessment(metrics)
        ds_chart = HTMLReportGenerator._downsample_time_series_for_system_behaviour_chart(
            summary.get("time_series_data", [])
        )
        if not ds_chart:
            ds_chart = [
                {
                    "avg_response_time": 0.0,
                    "vusers": 0.0,
                    "throughput_pass": float(metrics.get("throughput") or 0),
                    "throughput": float(metrics.get("throughput") or 0),
                    "error_rate_pct": float(metrics.get("error_rate") or 0) * 100.0,
                }
            ]
        chart_labels = [float(i) for i in range(len(ds_chart))]
        chart_rt = [float(d.get("avg_response_time") or 0) for d in ds_chart]
        chart_vu = [float(d.get("vusers") or 0) for d in ds_chart]
        chart_tps = [
            float(d.get("throughput_pass") or d.get("throughput") or 0) for d in ds_chart
        ]
        chart_err = []
        for d in ds_chart:
            er = d.get("error_rate_pct")
            if er is None:
                p = int(d.get("pass_count", 0))
                f = int(d.get("fail_count", 0))
                er = (100.0 * f / (p + f)) if (p + f) else 0.0
            chart_err.append(float(er))
        deep_section_html = render_deep_system_health_body(
            deep_ctx, chart_labels, chart_rt, chart_vu, chart_tps, chart_err
        )
        exec_summary = HTMLReportGenerator._generate_executive_summary(
            overall_grade,
            overall_score,
            success_rate,
            avg_response,
            error_rate_pct,
            throughput,
            p95_response,
            sla_compliance_2s,
            summary,
            skewness_analysis,
            business_impact,
            deep_context=deep_ctx,
            report_header=summary.get("report_header") or {},
            overall_grade_description=overall_grade_description,
        )
        
        update_progress(30, "Generating performance scorecard...")
        scorecard = HTMLReportGenerator._generate_performance_scorecard(overall_grade, overall_score, grade_reasons, scores, targets, success_rate, avg_response, error_rate_pct, throughput, p95_response, sla_compliance_2s, grade_bg_color, grade_border_color, overall_grade_description)
        
        update_progress(40, "Generating test overview...")
        test_overview = HTMLReportGenerator._generate_test_overview(total_samples, test_duration_hours, throughput, success_rate)
        
        feature_panel = HTMLReportGenerator._generate_feature_extraction_panel(
            summary.get("feature_extraction")
        )
        
        update_progress(50, "Generating performance tables...")
        tx_sla_detail = (summary.get("transaction_sla_p90_peak") or {}).get("details") or []
        sla_by_label = {str(d.get("label")): d.get("sla_pass") for d in tx_sla_detail}
        perf_tables = HTMLReportGenerator._generate_performance_tables(
            transaction_stats, request_stats, sla_by_label=sla_by_label
        )
        
        update_progress(60, "Generating system behaviour graph...")
        system_graph, graph_analysis = HTMLReportGenerator._generate_system_behaviour_graph(
            summary.get("time_series_data", []),
            progress_callback=lambda p, m: update_progress(60 + int(p * 0.15), f"Graph: {m}"),
        )
        if not graph_analysis:
            graph_analysis = {}
        graph_analysis.setdefault("distribution_analysis", {})

        update_progress(75, "Generating additional graphs...")
        additional_graphs = HTMLReportGenerator._generate_additional_graphs(summary.get("time_series_data", []), transaction_stats, request_stats, metrics, progress_callback=lambda p, m: update_progress(75 + int(p * 0.10), f"Additional: {m}"))
        
        update_progress(85, "Generating issues...")
        issues_html = render_structured_issues(deep_ctx.get("structured_issues") or [])
        resolution_plan_html = render_resolution_plan(deep_ctx.get("optimization_plan") or [])
        
        update_progress(89, "Generating action plan...")
        phased_plan = summary.get("phased_improvement_plan", {})
        action_plan = HTMLReportGenerator._generate_phased_action_plan(phased_plan, overall_grade)
        
        update_progress(91, "Generating success metrics...")
        success_metrics = HTMLReportGenerator._generate_success_metrics(avg_response, p95_response, error_rate_pct, success_rate, sla_compliance_2s, throughput)
        
        update_progress(93, "Generating final conclusion...")
        final_conclusion = HTMLReportGenerator._generate_final_conclusion(
            overall_grade,
            overall_score,
            success_rate,
            avg_response,
            error_rate_pct,
            throughput,
            p95_response,
            sla_compliance_2s,
            all_issues,
            improvement_roadmap,
            summary,
            deep_context=deep_ctx,
        )
        
        update_progress(95, "Generating footer...")
        footer = HTMLReportGenerator._generate_footer(current_date)
        
        update_progress(97, "Generating JavaScript...")
        javascript = HTMLReportGenerator._generate_javascript(response_time_dist, response_codes)
        
        update_progress(99, "Assembling final HTML...")
        
        consolidated_report_line = (f'<p style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748b;"><strong>Consolidated Report:</strong> {file_count} file(s) analyzed</p>' if is_consolidated else '')

        jmeter_nav_items = [
            ("section-executive-summary", "Executive summary"),
            ("section-scorecard", "Performance scorecard"),
            ("section-deep-assessment", "Deep system health"),
        ]
        jmeter_nav_items.extend(
            [
                ("section-test-overview", "Test overview"),
                ("section-latency-analytics", "Latency analytics"),
                ("section-performance-summary", "Performance summary"),
                ("section-system-behaviour", "System behaviour"),
                ("section-issues", "Issues"),
                ("section-resolution-plan", "Resolution plan"),
                ("section-action-plan", "Action plan"),
                ("section-success-metrics", "Success metrics"),
                ("section-final-conclusion", "Final conclusion"),
                ("section-next-steps", "Next steps"),
            ]
        )
        jmeter_nav_html = build_report_navigation_html(jmeter_nav_items, title="On this page")
        
        report_hdr = dict(summary.get("report_header") or {})
        if not report_hdr.get("line1"):
            dur_min = (summary.get("test_duration_hours") or 0) * 60.0
            report_hdr = {
                "line1": "Performance Test Analysis Report",
                "line2": "JMeter load test results",
                "line3": (
                    f"JMeter Results · {total_samples:,} samples · {dur_min:.1f} min"
                    if total_samples
                    else f"Generated · {current_date}"
                ),
            }
        pdf_button_html = '''<button onclick="window.print()" class="pdf-button no-print" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.75rem 1.5rem; border-radius: 8px; font-weight: 600; font-size: 0.95rem; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4); transition: all 0.2s;">
                    <span style="font-size: 1.2rem;">📄</span>
                    Save as PDF
                </button>'''
        page_title_header_html = render_report_top_header(
            report_hdr,
            consolidated_extra_html=consolidated_report_line,
            pdf_button_html=pdf_button_html,
        )

        # Generate HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Test Analysis Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    {css_content}
    {report_navigation_css()}
</head>
<body>
{jmeter_nav_html}
<div class="report-main-with-nav">
    {page_title_header_html}

    <div class="container">
        
        {HTMLReportGenerator._generate_consolidated_files_info(file_info, consolidated_files) if is_consolidated else ''}
        
        <!-- Executive Summary -->
        {exec_summary}
        
        <!-- Performance Scorecard with Grading -->
        {scorecard}

        <!-- Deep System Health Assessment (replaces legacy enhanced health block) -->
        {deep_section_html}
        
        <!-- Test Overview -->
        {test_overview}
        
        {feature_panel}
        
        <!-- Performance Summary Tables -->
        {perf_tables}
        
        <!-- Overall System Behaviour Graph -->
        {system_graph}
        
        <!-- Additional Performance Graphs -->
        {additional_graphs}
        
        <!-- Issues -->
        {issues_html}

        {resolution_plan_html}
        
        <!-- Recommended Action Plan -->
        {action_plan}
        
        <!-- Success Metrics & Targets -->
        {success_metrics}
        
        <!-- Final Conclusion -->
        {final_conclusion}
        
        <!-- Next Steps & Footer -->
        {footer}
        
    </div>

    {javascript}
{report_navigation_js()}
</div>
</body>
</html>'''
        
        return html
    
    @staticmethod
    def _generate_css() -> str:
        """Generate CSS styles (shared BusinessNext theme; comparative reports reuse this)."""
        return build_jmeter_report_css()

    
    @staticmethod
    def _generate_executive_summary(
        grade: str,
        score: float,
        success_rate: float,
        avg_response: Optional[float],
        error_rate: float,
        throughput: float,
        p95_response: Optional[float],
        sla_compliance: float,
        summary: dict,
        skewness_analysis: dict = None,
        business_impact: dict = None,
        deep_context: dict = None,
        report_header: dict = None,
        overall_grade_description: dict = None,
    ) -> str:
        """Generate executive summary section with key findings, skewness interpretation, and release framing."""
        
        # Get business impact data if available
        if not business_impact:
            business_impact = {}
        
        # Determine status using business impact
        release_decision = business_impact.get("release_decision", "")
        executive_meaning = business_impact.get("executive_meaning", "")
        operational_risk = business_impact.get("operational_risk", "Unknown")

        ogd = overall_grade_description if isinstance(overall_grade_description, dict) else {}
        t_ogd = str(ogd.get("title") or "").strip()
        d_ogd = str(ogd.get("description") or "").strip()
        grade_narrative = None
        if t_ogd or d_ogd:
            try:
                sc = float(score)
            except (TypeError, ValueError):
                sc = 0.0
            grade_narrative = format_performance_grade_release_line(str(grade), sc, t_ogd, d_ogd)

        # Determine status color and message from business impact
        if grade in ["A+", "A"]:
            status_color = "#10b981"
            status_icon = "✅"
            status_text = release_decision or "APPROVED"
            status_message = grade_narrative or executive_meaning or "The application demonstrates excellent performance and stability. Ready for full production deployment."
        elif grade in ["B+", "B"]:
            status_color = "#f59e0b"
            status_icon = "⚠️"
            status_text = release_decision or "CONDITIONAL APPROVAL"
            status_message = grade_narrative or executive_meaning or "The application is stable but requires performance improvements. Recommended approach: Limited rollout with monitoring."
        else:
            status_color = "#ef4444"
            status_icon = "❌"
            status_text = release_decision or "RELEASE NOT RECOMMENDED"
            status_message = grade_narrative or executive_meaning or "The application demonstrates stability but exhibits critical performance issues requiring immediate attention."

        deep_mode = bool(deep_context)
        hdr_block = ""
        kpi_block = ""
        ovh_block = ""
        if deep_mode:
            kpi_block = render_kpi_grid(deep_context.get("kpi_cards") or [])
            ovh_block = render_overall_health_section(deep_context.get("overall_health_cards") or [])

        if deep_mode:
            kfi = list(deep_context.get("key_findings_items") or [])
            if not kfi and deep_context.get("key_paragraphs"):
                kfi = [{"text": p, "tone": "neutral"} for p in (deep_context.get("key_paragraphs") or [])]
            findings_wrapper = render_key_findings_list(kfi)
        else:
            key_findings = []
            if avg_response is None:
                key_findings.append("❌ <strong>No response time signal:</strong> There are no successful requests with measurable latency in this run (only failures or HTTP errors, or all excluded). A zero or missing average is <strong>not</strong> evidence of a fast system.")
            elif avg_response <= 2.0:
                key_findings.append(f"✅ <strong>Excellent Response Time:</strong> Average response time of {avg_response:.2f}s meets industry standards for optimal user experience.")
            elif avg_response <= 5.0:
                key_findings.append(f"⚠️ <strong>Moderate Response Time:</strong> Average response time of {avg_response:.2f}s is acceptable but has room for improvement to enhance user satisfaction.")
            else:
                key_findings.append(f"❌ <strong>Slow Response Time:</strong> Average response time of {avg_response:.2f}s exceeds acceptable thresholds and may impact user experience.")
            if error_rate < 1.0:
                key_findings.append(f"✅ <strong>Low Error Rate:</strong> Error rate of {error_rate:.2f}% indicates high system reliability and stability.")
            elif error_rate < 5.0:
                key_findings.append(f"⚠️ <strong>Moderate Error Rate:</strong> Error rate of {error_rate:.2f}% suggests some reliability concerns that should be addressed.")
            else:
                key_findings.append(f"❌ <strong>High Error Rate:</strong> Error rate of {error_rate:.2f}% indicates significant reliability issues requiring immediate attention.")
            if throughput >= 100:
                key_findings.append(f"✅ <strong>High Throughput:</strong> System processes {throughput:.0f} requests/second, demonstrating good capacity and scalability.")
            elif throughput >= 50:
                key_findings.append(f"⚠️ <strong>Moderate Throughput:</strong> System processes {throughput:.0f} requests/second, which is acceptable but could be optimized for higher loads.")
            else:
                key_findings.append(f"❌ <strong>Low Throughput:</strong> System processes only {throughput:.0f} requests/second, indicating potential scalability limitations.")
            if sla_compliance >= 95:
                key_findings.append(f"✅ <strong>Excellent SLA Compliance:</strong> {sla_compliance:.1f}% of requests meet the 2-second SLA target, ensuring consistent user experience.")
            elif sla_compliance >= 80:
                key_findings.append(f"⚠️ <strong>Moderate SLA Compliance:</strong> {sla_compliance:.1f}% of requests meet the 2-second SLA target, indicating room for improvement.")
            else:
                key_findings.append(f"❌ <strong>Poor SLA Compliance:</strong> Only {sla_compliance:.1f}% of requests meet the 2-second SLA target, requiring immediate optimization.")
            if success_rate >= 99:
                key_findings.append(f"✅ <strong>High Success Rate:</strong> {success_rate:.1f}% success rate demonstrates excellent system reliability.")
            elif success_rate >= 95:
                key_findings.append(f"⚠️ <strong>Moderate Success Rate:</strong> {success_rate:.1f}% success rate is acceptable but could be improved.")
            else:
                key_findings.append(f"❌ <strong>Low Success Rate:</strong> {success_rate:.1f}% success rate indicates significant reliability issues.")
            kfi_legacy = []
            for finding in key_findings:
                tone = "neutral"
                if finding.strip().startswith("❌"):
                    tone = "bad"
                elif finding.strip().startswith("⚠️"):
                    tone = "warn"
                elif finding.strip().startswith("✅"):
                    tone = "ok"
                body = re.sub(r"^(✅|⚠️|❌)\s*", "", finding, count=1)
                kfi_legacy.append({"text": body.strip(), "tone": tone, "html": True})
            findings_wrapper = render_key_findings_list(kfi_legacy)

        summary_grid_html = "" if deep_mode else f'''
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">{success_rate:.1f}%</div>
                    <div>Success Rate</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{HTMLReportGenerator.format_sec_or_na(avg_response)}</div>
                    <div>Avg Response Time</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{error_rate:.2f}%</div>
                    <div>Error Rate</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{throughput:.0f}/s</div>
                    <div>Throughput</div>
                </div>
            </div>'''
        
        # Generate skewness analysis section with HORIZONTAL CARDS
        skewness_html = ""
        if skewness_analysis:
            skew_type = skewness_analysis.get("type", "Unknown")
            skew_value = skewness_analysis.get("skewness_value", 0)
            skew_icon = skewness_analysis.get("distribution_icon", "📊")
            skew_shape = skewness_analysis.get("shape", "")
            observations = skewness_analysis.get("observations", [])
            interpretation = skewness_analysis.get("interpretation", {})
            possible_causes = skewness_analysis.get("possible_causes", [])
            business_impact_text = skewness_analysis.get("business_impact", "")
            
            observations_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">{obs}</li>' for obs in observations])
            interpretation_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">{key}: {value}</li>' for key, value in interpretation.items()])
            causes_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">{cause}</li>' for cause in possible_causes]) if possible_causes else ""
            causes_block = (f'''<div style="background: #fef2f2; padding: 1rem; border-radius: 8px; border: 1px solid #fca5a5;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #b91c1c; font-size: 0.95rem;">⚠️ Possible Root Causes</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            {causes_html}
                        </ul>
                    </div>''' if causes_html else '')
            business_impact_block = (
                f'<div style="margin-top: 1rem; padding: 1rem; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 6px;"><p style="margin: 0;"><strong>🎯 Business Impact:</strong> {business_impact_text}</p></div>'
                if (business_impact_text and not deep_mode)
                else ""
            )
            
            skewness_html = f'''
            <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem; color: var(--text-primary);">
                <h3 style="color: var(--primary-color); margin-top: 0; margin-bottom: 1rem;">{skew_icon} Statistical Distribution Analysis</h3>
                <div style="background: #f8fafc; padding: 1rem; border-radius: 6px; border-left: 4px solid var(--primary-color); margin-bottom: 1rem;">
                    <p style="margin: 0 0 0.5rem 0;"><strong>Distribution Type:</strong> {skew_type}</p>
                    <p style="margin: 0 0 0.5rem 0;"><strong>Skewness Value:</strong> {skew_value}</p>
                    <p style="margin: 0;"><strong>Shape:</strong> {skew_shape}</p>
                </div>
                
                <!-- Horizontal Cards -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1rem; margin-top: 1rem;">
                    <!-- Observations Card -->
                    <div style="background: #f0f9ff; padding: 1rem; border-radius: 8px; border: 1px solid #bae6fd;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #0369a1; font-size: 0.95rem;">📈 Observations</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            {observations_html}
                        </ul>
                    </div>
                    
                    <!-- Interpretation Card -->
                    <div style="background: #fefce8; padding: 1rem; border-radius: 8px; border: 1px solid #fde047;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #a16207; font-size: 0.95rem;">💡 Interpretation</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            {interpretation_html}
                        </ul>
                    </div>
                    
                    <!-- Possible Root Causes Card -->
                    {causes_block}
                </div>
                
                {business_impact_block}
            </div>'''
        
        # Generate business impact section with HORIZONTAL CARDS
        business_impact_html = ""
        if business_impact and not deep_mode:
            customer_impact = business_impact.get("customer_impact", [])
            business_outcome = business_impact.get("business_outcome", [])
            business_actions = business_impact.get("business_actions", [])
            tech_indicators = business_impact.get("tech_indicators", [])
            risk_note = business_impact.get("risk_note", "")
            business_translation = business_impact.get("business_translation", "")
            
            customer_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">✓ {item}</li>' for item in customer_impact]) if customer_impact else ""
            outcome_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">✓ {item}</li>' for item in business_outcome]) if business_outcome else ""
            actions_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">→ {item}</li>' for item in business_actions]) if business_actions else ""
            tech_html = ''.join([f'<li style="margin-bottom: 0.5rem; line-height: 1.4;">• {item}</li>' for item in tech_indicators]) if tech_indicators else ""
            customer_block = ('''<!-- Customer Impact Card -->
                    <div style="background: #f0fdf4; padding: 1rem; border-radius: 8px; border: 1px solid #86efac;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #166534; font-size: 0.95rem;">👥 Customer Impact</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            ''' + customer_html + '''
                        </ul>
                    </div>''' if customer_html else '')
            outcome_block = ('''<!-- Business Outcomes Card -->
                    <div style="background: #eff6ff; padding: 1rem; border-radius: 8px; border: 1px solid #93c5fd;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #1e40af; font-size: 0.95rem;">📊 Business Outcomes</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            ''' + outcome_html + '''
                        </ul>
                    </div>''' if outcome_html else '')
            actions_block = ('''<!-- Recommended Actions Card -->
                    <div style="background: #fef3c7; padding: 1rem; border-radius: 8px; border: 1px solid #fcd34d;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #92400e; font-size: 0.95rem;">🎯 Recommended Actions</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            ''' + actions_html + '''
                        </ul>
                    </div>''' if actions_html else '')
            tech_block = ('''<!-- Technical Indicators Card -->
                    <div style="background: #f5f3ff; padding: 1rem; border-radius: 8px; border: 1px solid #c4b5fd;">
                        <p style="font-weight: 700; margin: 0 0 0.75rem 0; color: #5b21b6; font-size: 0.95rem;">🔧 Technical Indicators</p>
                        <ul style="margin: 0; padding-left: 1.2rem; font-size: 0.875rem;">
                            ''' + tech_html + '''
                        </ul>
                    </div>''' if tech_html else '')
            risk_note_block = (f'<div style="margin-top: 1rem; padding: 1rem; background: #fef3c7; border-left: 4px solid #f59e0b; border-radius: 6px;"><p style="margin: 0;"><strong>⚠️ Risk Note:</strong> {risk_note}</p></div>' if risk_note else '')
            business_translation_block = (f'<div style="margin-top: 1rem; padding: 1rem; background: #dbeafe; border-left: 4px solid #3b82f6; border-radius: 6px;"><p style="margin: 0;"><strong>💬 Business Translation:</strong> {business_translation}</p></div>' if business_translation else '')
            
            business_impact_html = f'''
            <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem; color: var(--text-primary);">
                <h3 style="color: var(--primary-color); margin-top: 0; margin-bottom: 1rem;">💼 Business Impact & Release Decision</h3>
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <p style="margin: 0 0 0.5rem 0; font-size: 0.9rem; opacity: 0.9;">Release Decision</p>
                    <p style="margin: 0; font-size: 1.4rem; font-weight: 700;">{release_decision}</p>
                    <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem;">Operational Risk: <strong>{operational_risk}</strong></p>
                </div>
                
                <!-- Horizontal Cards -->
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 1rem;">
                    {customer_block}
                    
                    {outcome_block}
                    
                    {actions_block}
                    
                    {tech_block}
                </div>
                
                {risk_note_block}
                {business_translation_block}
            </div>'''
        
        findings_outer_style = (
            "background: #ffffff; padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem; color: #0f172a; border: 1px solid #e5e7eb;"
            if deep_mode
            else "background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem; color: var(--text-primary);"
        )
        findings_h3_color = "var(--color-text-primary)" if deep_mode else "var(--primary-color)"
        findings_box = f'''
            <div style="{findings_outer_style}">
                <h3 style="color: {findings_h3_color}; margin-top: 0;">Key Findings</h3>
                {findings_wrapper}
            </div>'''

        if deep_mode:
            return f'''
        <div id="section-executive-summary" style="background:#ffffff;border:1px solid #e5e7eb;border-radius:10px;padding:2rem;margin:2rem 0;color:#0f172a;box-shadow:0 1px 2px rgba(0,0,0,0.04);">
            <h2 style="color: #0f172a; border-bottom: 1px solid #e5e7eb; padding-bottom: 0.5rem; margin-top: 0; font-size: 1.25rem; font-weight: 600;">Executive Summary</h2>
            <div class="alert" style="background: #f8fafc; border: 1px solid #e5e7eb; color: #0f172a;">
                <h3 style="color: {status_color}; margin-top:0;">{status_icon} {status_text}</h3>
                <p style="margin:0;"><strong>{status_message}</strong></p>
            </div>
            {summary_grid_html}
            {kpi_block}
            {findings_box}
            {ovh_block}
            {skewness_html}
        </div>'''

        return f'''
        <div class="executive-summary" id="section-executive-summary">
            <h2 style="color: white; border-bottom: 2px solid white;">Executive Summary</h2>
            <div class="alert" style="background: rgba(255, 255, 255, 0.1); border-color: white; color: white;">
                <h3 style="color: {status_color};">{status_icon} {status_text}</h3>
                <p><strong>{status_message}</strong></p>
            </div>
            {summary_grid_html}
            {hdr_block}
            {kpi_block}
            {findings_box}
            {ovh_block}
            {business_impact_html}
            {skewness_html}
        </div>'''
    
    @staticmethod
    def _generate_performance_scorecard(grade: str, score: float, grade_reasons: dict, scores: dict, 
                                       targets: dict, success_rate: float, avg_response: Optional[float], 
                                       error_rate: float, throughput: float, p95_response: Optional[float], 
                                       sla_compliance: float, grade_bg_color: str, grade_border_color: str,
                                       overall_grade_description: dict = None) -> str:
        """Generate performance scorecard with grading analysis"""
        ar, pr = avg_response, p95_response
        avg_result_cell = f"{ar:.1f} sec" if ar is not None else "N/A"
        avg_badge_class = (
            "badge-success" if ar is not None and ar < 2 else
            "badge-warning" if ar is not None and ar < 5 else "badge-danger"
        )
        avg_badge_text = (
            "✅ PASS" if ar is not None and ar < 2 else
            "⚠️ MARGINAL" if ar is not None and ar < 5 else
            ("❌ FAIL" if ar is not None else "N/A")
        )
        p95_result_cell = f"{pr:.1f} sec" if pr is not None else "N/A"
        p95_badge_class = (
            "badge-success" if pr is not None and pr < 3 else
            "badge-warning" if pr is not None and pr < 10 else "badge-danger"
        )
        p95_badge_text = (
            "✅ PASS" if pr is not None and pr < 3 else
            "⚠️ MARGINAL" if pr is not None and pr < 10 else
            ("❌ FAIL" if pr is not None else "N/A")
        )
        
        perf_reason = grade_reasons.get("performance", {})
        rel_reason = grade_reasons.get("reliability", {})
        ux_reason = grade_reasons.get("user_experience", {})
        scale_reason = grade_reasons.get("scalability", {})
        
        # Get overall grade description - one liner
        grade_title = overall_grade_description.get("title", "Performance Assessment") if overall_grade_description else "Performance Assessment"
        grade_range = overall_grade_description.get("score_range", "") if overall_grade_description else ""
        
        # Get one-liner descriptions for each category grade
        def get_grade_one_liner(cat_grade):
            one_liners = {
                "A+": "Exceptional - Exceeds all expectations",
                "A": "Excellent - Strong performance",
                "B+": "Good - Meets most standards",
                "B": "Above Average - Minor gaps",
                "C+": "Average - Needs improvement",
                "C": "Below Average - Significant issues",
                "D": "Poor - Critical problems",
                "F": "Failing - Immediate action needed"
            }
            return one_liners.get(cat_grade, "N/A")
        
        methodology_body = performance_grading_methodology_html(grade)
        return f'''
        <div class="section" id="section-scorecard">
            <div style="display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between; gap: 0.75rem; margin-bottom: 0.5rem;">
              <h2 style="margin: 0;">🎯 Performance Scorecard & Grading Analysis</h2>
              <button type="button" class="no-print" onclick="document.getElementById('gradingMethodModal').style.display='flex'"
                style="background:#f1f5f9;border:1px solid #cbd5e1;color:#0f172a;padding:0.45rem 0.9rem;border-radius:8px;font-size:0.85rem;font-weight:600;cursor:pointer;">
                Performance grading methodology
              </button>
            </div>
            <div id="gradingMethodModal" class="no-print" onclick="if(event.target===this)this.style.display='none'"
              style="display:none;position:fixed;inset:0;background:rgba(15,23,42,0.45);z-index:9999;align-items:center;justify-content:center;padding:1rem;">
              <div onclick="event.stopPropagation()" style="background:white;max-width:720px;width:100%;max-height:90vh;overflow:auto;border-radius:12px;padding:1.5rem;box-shadow:0 25px 50px rgba(0,0,0,0.2);">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:0.5rem;">
                  <h3 style="margin:0;">Performance grading methodology</h3>
                  <button type="button" onclick="document.getElementById('gradingMethodModal').style.display='none'"
                    style="border:none;background:#f1f5f9;border-radius:8px;padding:0.35rem 0.65rem;cursor:pointer;font-weight:700;">✕</button>
                </div>
                {methodology_body}
              </div>
            </div>
            
            <!-- Overall Grade Display with One-Liner -->
            <div style="text-align: center; background: linear-gradient(135deg, {grade_bg_color}, #fef3c7); padding: 1.5rem; border-radius: 12px; margin: 1rem 0; border: 3px solid {grade_border_color};">
                <h1 style="color: {grade_border_color}; font-size: 2.5rem; margin: 0;">OVERALL GRADE: {grade}</h1>
                <p style="font-size: 1.2rem; font-weight: 600; color: var(--text-primary); margin: 0.3rem 0;">{grade_title}</p>
                <p style="font-size: 0.95rem; color: var(--text-secondary); margin: 0.3rem 0;">Score: {score:.0f}/100 | Range: {grade_range}</p>
            </div>

            <!-- Grade Breakdown Cards - Grade at TOP -->
            <div class="metrics-grid">
                <div class="metric-card {perf_reason.get('class', 'warning')}" style="padding: 1rem;">
                    <!-- Grade at TOP -->
                    <div style="text-align: center; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--{perf_reason.get('class', 'warning')}-color);">
                        <div style="font-size: 2rem; font-weight: 700; color: var(--{perf_reason.get('class', 'warning')}-color);">{perf_reason.get('grade', 'N/A')}</div>
                        <div style="font-size: 0.7rem; color: var(--text-secondary);">{get_grade_one_liner(perf_reason.get('grade', 'N/A'))}</div>
                    </div>
                    <!-- Category Info -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <span style="font-size: 0.9rem; font-weight: 600;">{perf_reason.get('icon', '⚡')} {perf_reason.get('name', 'Performance')}</span>
                        <span style="font-size: 0.65rem; background: var(--background-light); padding: 2px 6px; border-radius: 4px;">{perf_reason.get('weight', '30%')} | {perf_reason.get('score', 0)}/100</span>
                    </div>
                    <div style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">{perf_reason.get('reason', 'N/A')}</div>
                </div>
                
                <div class="metric-card {rel_reason.get('class', 'warning')}" style="padding: 1rem;">
                    <!-- Grade at TOP -->
                    <div style="text-align: center; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--{rel_reason.get('class', 'warning')}-color);">
                        <div style="font-size: 2rem; font-weight: 700; color: var(--{rel_reason.get('class', 'warning')}-color);">{rel_reason.get('grade', 'N/A')}</div>
                        <div style="font-size: 0.7rem; color: var(--text-secondary);">{get_grade_one_liner(rel_reason.get('grade', 'N/A'))}</div>
                    </div>
                    <!-- Category Info -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <span style="font-size: 0.9rem; font-weight: 600;">{rel_reason.get('icon', '🛡️')} {rel_reason.get('name', 'Reliability')}</span>
                        <span style="font-size: 0.65rem; background: var(--background-light); padding: 2px 6px; border-radius: 4px;">{rel_reason.get('weight', '25%')} | {rel_reason.get('score', 0)}/100</span>
                    </div>
                    <div style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">{rel_reason.get('reason', 'N/A')}</div>
                </div>
                
                <div class="metric-card {ux_reason.get('class', 'warning')}" style="padding: 1rem;">
                    <!-- Grade at TOP -->
                    <div style="text-align: center; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--{ux_reason.get('class', 'warning')}-color);">
                        <div style="font-size: 2rem; font-weight: 700; color: var(--{ux_reason.get('class', 'warning')}-color);">{ux_reason.get('grade', 'N/A')}</div>
                        <div style="font-size: 0.7rem; color: var(--text-secondary);">{get_grade_one_liner(ux_reason.get('grade', 'N/A'))}</div>
                    </div>
                    <!-- Category Info -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <span style="font-size: 0.9rem; font-weight: 600;">{ux_reason.get('icon', '👥')} {ux_reason.get('name', 'User Experience')}</span>
                        <span style="font-size: 0.65rem; background: var(--background-light); padding: 2px 6px; border-radius: 4px;">{ux_reason.get('weight', '25%')} | {ux_reason.get('score', 0)}/100</span>
                    </div>
                    <div style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">{ux_reason.get('reason', 'N/A')}</div>
                </div>
                
                <div class="metric-card {scale_reason.get('class', 'warning')}" style="padding: 1rem;">
                    <!-- Grade at TOP -->
                    <div style="text-align: center; margin-bottom: 0.5rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--{scale_reason.get('class', 'warning')}-color);">
                        <div style="font-size: 2rem; font-weight: 700; color: var(--{scale_reason.get('class', 'warning')}-color);">{scale_reason.get('grade', 'N/A')}</div>
                        <div style="font-size: 0.7rem; color: var(--text-secondary);">{get_grade_one_liner(scale_reason.get('grade', 'N/A'))}</div>
                    </div>
                    <!-- Category Info -->
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem;">
                        <span style="font-size: 0.9rem; font-weight: 600;">{scale_reason.get('icon', '📈')} {scale_reason.get('name', 'Scalability')}</span>
                        <span style="font-size: 0.65rem; background: var(--background-light); padding: 2px 6px; border-radius: 4px;">{scale_reason.get('weight', '20%')} | {scale_reason.get('score', 0)}/100</span>
                    </div>
                    <div style="font-size: 0.8rem; font-weight: 500; color: var(--text-primary);">{scale_reason.get('reason', 'N/A')}</div>
                </div>
            </div>

            <!-- Detailed Scorecard Table -->
            <div style="margin: 2rem 0;">
                <h3>📋 Detailed Performance Metrics</h3>
                <div style="overflow-x: auto;">
                    <table class="endpoint-table">
                        <thead>
                            <tr>
                                <th>Metric</th>
                                <th>Result</th>
                                <th>Target</th>
                                <th>Status</th>
                                <th>Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="font-weight: 600;">Availability</td>
                                <td style="text-align: center;">{success_rate:.1f}%</td>
                                <td style="text-align: center;">{targets.get('availability', 99)}%</td>
                                <td style="text-align: center;">
                                    <span class="status-badge {'badge-success' if success_rate >= 99 else 'badge-warning' if success_rate >= 95 else 'badge-danger'}">
                                        {'✅ PASS' if success_rate >= 99 else '⚠️ MARGINAL' if success_rate >= 95 else '❌ FAIL'}
                                    </span>
                                </td>
                                <td style="text-align: center; font-weight: 600;">{scores.get('availability', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="font-weight: 600;">Avg Response Time</td>
                                <td style="text-align: center;">{avg_result_cell}</td>
                                <td style="text-align: center;">&lt;{targets.get('response_time', 2000)/1000:.0f} sec</td>
                                <td style="text-align: center;">
                                    <span class="status-badge {avg_badge_class}">{avg_badge_text}</span>
                                </td>
                                <td style="text-align: center; font-weight: 600;">{scores.get('response_time', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="font-weight: 600;">Error Rate</td>
                                <td style="text-align: center;">{error_rate:.2f}%</td>
                                <td style="text-align: center;">&lt;{targets.get('error_rate', 1)}%</td>
                                <td style="text-align: center;">
                                    <span class="status-badge {'badge-success' if error_rate < 1 else 'badge-warning' if error_rate < 3 else 'badge-danger'}">
                                        {'✅ PASS' if error_rate < 1 else '⚠️ MARGINAL' if error_rate < 3 else '❌ FAIL'}
                                    </span>
                                </td>
                                <td style="text-align: center; font-weight: 600;">{scores.get('error_rate', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="font-weight: 600;">Throughput</td>
                                <td style="text-align: center;">{throughput:.1f}/s</td>
                                <td style="text-align: center;">{targets.get('throughput', 100)}/s</td>
                                <td style="text-align: center;">
                                    <span class="status-badge {'badge-success' if throughput >= 100 else 'badge-warning'}">
                                        {'✅ PASS' if throughput >= 100 else '⚠️ ACCEPTABLE'}
                                    </span>
                                </td>
                                <td style="text-align: center; font-weight: 600;">{scores.get('throughput', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">95th Percentile</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{p95_result_cell}</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">&lt;{targets.get('p95_percentile', 3000)/1000:.0f} sec</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {p95_badge_class}">{p95_badge_text}</span>
                                </td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center; font-weight: 600;">{scores.get('p95_percentile', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">SLA Compliance</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{sla_compliance:.1f}%</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">&gt;{targets.get('sla_compliance', 95)}%</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {'badge-success' if sla_compliance >= 95 else 'badge-warning' if sla_compliance >= 80 else 'badge-danger'}">
                                        {'✅ PASS' if sla_compliance >= 95 else '⚠️ MARGINAL' if sla_compliance >= 80 else '❌ CRITICAL'}
                                    </span>
                                </td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center; font-weight: 600;">{scores.get('sla_compliance', 0):.0f}/100</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_consolidated_files_info(file_info: List[Dict], consolidated_files: List[str]) -> str:
        """Generate section showing consolidated files information"""
        if not file_info and not consolidated_files:
            return ""
        
        # Use file_info if available, otherwise use consolidated_files
        files_to_display = file_info if file_info else [{"filename": f, "samples": 0, "errors": 0, "throughput": 0} for f in consolidated_files]
        
        files_html = ""
        for idx, file_data in enumerate(files_to_display, 1):
            filename = file_data.get("filename", f"File_{idx}")
            samples = file_data.get("samples", 0)
            errors = file_data.get("errors", 0)
            throughput = file_data.get("throughput", 0)
            error_rate = (errors / samples * 100) if samples > 0 else 0
            
            files_html += f'''
                    <tr>
                        <td>{filename}</td>
                        <td style="text-align: center;">{samples:,}</td>
                        <td style="text-align: center;">{errors:,}</td>
                        <td style="text-align: center;">{error_rate:.2f}%</td>
                        <td style="text-align: center;">{throughput:.2f}</td>
                    </tr>
            '''
        
        return f'''
        <div class="section" id="section-consolidated-files">
            <h2>📁 Consolidated Files Analysis</h2>
            <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 4px solid #0ea5e9; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem;">
                <p style="margin: 0; font-size: 1rem; line-height: 1.6; color: var(--text-primary);">
                    This report consolidates analysis from <strong>{len(files_to_display)} file(s)</strong>. 
                    All metrics, graphs, and findings below represent the combined performance data from all files.
                </p>
            </div>
            
            <table class="endpoint-table">
                <thead>
                    <tr>
                        <th>File Name</th>
                        <th>Samples</th>
                        <th>Errors</th>
                        <th>Error Rate</th>
                        <th>Throughput (req/s)</th>
                    </tr>
                </thead>
                <tbody>
                    {files_html}
                </tbody>
            </table>
        </div>
        '''
    
    @staticmethod
    def _generate_test_overview(total_samples: int, test_duration: float, throughput: float, success_rate: float) -> str:
        """Generate test overview section"""
        peak_users = int(throughput * 5) if throughput > 0 else 0  # Estimate
        data_processed_gb = (total_samples * 5) / 1024  # Rough estimate
        
        return f'''
        <div class="section" id="section-test-overview">
            <h2>📊 Test Overview</h2>
            <div class="metrics-grid">
                <div class="metric-card success">
                    <div class="metric-value success">{total_samples:,}</div>
                    <div class="metric-label">Total Requests</div>
                </div>
                <div class="metric-card success">
                    <div class="metric-value success">{test_duration:.2f}</div>
                    <div class="metric-label">Hours Tested</div>
                </div>
                <div class="metric-card {'success' if success_rate >= 99 else 'warning'}">
                    <div class="metric-value {'success' if success_rate >= 99 else 'warning'}">{peak_users}</div>
                    <div class="metric-label">Estimated Peak Users</div>
                </div>
                <div class="metric-card success">
                    <div class="metric-value success">{data_processed_gb:.1f} GB</div>
                    <div class="metric-label">Data Processed (Est.)</div>
                </div>
            </div>
            
            <div class="two-column">
                <div>
                    <h3>Test Configuration</h3>
                    <ul style="list-style-position: inside;">
                        <li><strong>Total Samples:</strong> {total_samples:,}</li>
                        <li><strong>Test Duration:</strong> {test_duration:.2f} hours</li>
                        <li><strong>Average Throughput:</strong> {throughput:.1f} req/s</li>
                        <li><strong>Success Rate:</strong> {success_rate:.2f}%</li>
                    </ul>
                </div>
                <div>
                    <h3>Test Objectives</h3>
                    <ul style="list-style-position: inside;">
                        <li>Validate system performance under load</li>
                        <li>Identify performance bottlenecks</li>
                        <li>Assess scalability and stability</li>
                        <li>Verify SLA compliance</li>
                    </ul>
                </div>
            </div>
        </div>'''
    
    @staticmethod
    def _get_response_time_color(value_seconds: float) -> str:
        """Get color class for response time based on thresholds"""
        if value_seconds < 2.0:
            return 'success'  # Green
        elif value_seconds < 5.0:
            return 'warning'  # Yellow
        else:
            return 'danger'  # Red
    
    @staticmethod
    def _get_error_rate_color(error_rate: float) -> str:
        """Get color class for error rate based on thresholds"""
        if error_rate < 1.0:
            return 'success'  # Green
        elif error_rate < 5.0:
            return 'warning'  # Yellow
        else:
            return 'danger'  # Red
    
    @staticmethod
    def _get_cell_style(value_seconds: float, metric_type: str = 'response_time') -> str:
        """Get inline style for cell based on value and metric type"""
        if metric_type == 'response_time':
            color_class = HTMLReportGenerator._get_response_time_color(value_seconds)
        elif metric_type == 'error_rate':
            color_class = HTMLReportGenerator._get_error_rate_color(value_seconds)
        else:
            return ''
        
        color_map = {
            'success': 'color: #059669; font-weight: 600;',
            'warning': 'color: #d97706; font-weight: 600;',
            'danger': 'color: #dc2626; font-weight: 700;'
        }
        return color_map.get(color_class, '')
    
    @staticmethod
    def _format_stat_ms_as_sec(ms_value) -> str:
        """Format stored millisecond stat for table; None means no successful samples (not '0.00s good')."""
        if ms_value is None:
            return "N/A"
        try:
            return f"{float(ms_value) / 1000.0:.2f}s"
        except (TypeError, ValueError):
            return "N/A"
    
    @staticmethod
    def _get_rt_stat_cell_style_ms(ms_value) -> str:
        """SLA color only when a real RT exists; neutral style for N/A."""
        if ms_value is None:
            return "color: #64748b; font-style: italic;"
        try:
            return HTMLReportGenerator._get_cell_style(float(ms_value) / 1000.0)
        except (TypeError, ValueError):
            return "color: #64748b; font-style: italic;"
    
    @staticmethod
    def _generate_performance_tables(
        transaction_stats: dict,
        request_stats: dict,
        sla_by_label: Optional[Dict[str, bool]] = None,
    ) -> str:
        """Transaction Performance table: URL-empty transaction controllers only, sorted by name A→Z."""
        _ = request_stats
        sla_by_label = sla_by_label or {}
        all_stats = dict(transaction_stats)

        def generate_table(stats: dict, title: str) -> str:
            if not stats:
                return (
                    "<p><em>No transaction controller data (samples with empty URL) available "
                    "for this report.</em></p>"
                )

            sorted_stats = sorted(
                stats.items(), key=lambda item: (item[0] or "").lower()
            )

            rows = ""
            for label, data in sorted_stats:
                min_resp = data.get("min")
                avg_resp = data.get("avg_response")
                median = data.get("median")
                p75 = data.get("p75")
                p90 = data.get("p90")
                p95 = data.get("p95")
                max_resp = data.get("max")
                error_rate = data.get('error_rate', 0) or 0
                count = data.get('count', 0) or 0
                
                min_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(min_resp)
                avg_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(avg_resp)
                median_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(median)
                p75_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(p75)
                p90_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(p90)
                p95_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(p95)
                max_style = HTMLReportGenerator._get_rt_stat_cell_style_ms(max_resp)
                error_style = HTMLReportGenerator._get_cell_style(error_rate, 'error_rate')
                
                p90_ms = p90
                sla_pass = sla_by_label.get(label)
                if sla_pass is True:
                    sla_cell = '<span style="color:#059669;font-weight:700;">PASS</span>'
                elif sla_pass is False:
                    sla_cell = '<span style="color:#dc2626;font-weight:700;">FAIL</span>'
                else:
                    if isinstance(p90_ms, (int, float)) and p90_ms < 3000:
                        sla_cell = '<span style="color:#059669;">PASS</span>'
                    elif p90_ms is None:
                        sla_cell = '<span style="color:#64748b;">—</span>'
                    else:
                        sla_cell = '<span style="color:#dc2626;">FAIL</span>'

                rows += f'''
                <tr>
                    <td style="font-weight: 600;">{label}</td>
                    <td style="text-align: center; {min_style}">{HTMLReportGenerator._format_stat_ms_as_sec(min_resp)}</td>
                    <td style="text-align: center; {avg_style}"><strong>{HTMLReportGenerator._format_stat_ms_as_sec(avg_resp)}</strong></td>
                    <td style="text-align: center; {median_style}">{HTMLReportGenerator._format_stat_ms_as_sec(median)}</td>
                    <td style="text-align: center; {p75_style}">{HTMLReportGenerator._format_stat_ms_as_sec(p75)}</td>
                    <td style="text-align: center; {p90_style}">{HTMLReportGenerator._format_stat_ms_as_sec(p90)}</td>
                    <td style="text-align: center; {p95_style}">{HTMLReportGenerator._format_stat_ms_as_sec(p95)}</td>
                    <td style="text-align: center; {max_style}">{HTMLReportGenerator._format_stat_ms_as_sec(max_resp)}</td>
                    <td style="text-align: center;">{count:,}</td>
                    <td style="text-align: center; {error_style}">{error_rate:.2f}%</td>
                    <td style="text-align: center;">{sla_cell}</td>
                </tr>'''
            
            return f'''
            <h3>{title}</h3>
            <div style="margin-bottom: 1rem; padding: 1rem; background: var(--background-light); border-radius: 8px; font-size: 0.9rem;">
                <strong>Color Coding:</strong> 
                <span style="color: #059669;">Green</span> = Within SLA (Response Time &lt; 2s, Error Rate &lt; 1%), 
                <span style="color: #d97706;">Yellow</span> = Warning (Response Time 2-5s, Error Rate 1-5%), 
                <span style="color: #dc2626;">Red</span> = Violating SLA (Response Time &gt; 5s, Error Rate &gt; 5%)
            </div>
            <div style="overflow-x: auto; max-width: 100%; -webkit-overflow-scrolling: touch;">
                <table class="endpoint-table" style="width: 100%; max-width: 100%; table-layout: auto; font-size: 0.8rem;">
                    <thead>
                        <tr>
                            <th>Endpoint/Transaction</th>
                            <th style="text-align: center;">Min</th>
                            <th style="text-align: center;">Avg</th>
                            <th style="text-align: center;">50 pct</th>
                            <th style="text-align: center;">75 pct</th>
                            <th style="text-align: center;">90 pct</th>
                            <th style="text-align: center;">95 pct</th>
                            <th style="text-align: center;">Max</th>
                            <th style="text-align: center;">Calls</th>
                            <th style="text-align: center;">Error Rate</th>
                            <th style="text-align: center;">SLA (P90)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>'''
        
        return f'''
        <div class="section" id="section-performance-summary" style="max-width: 100%; overflow: hidden;">
            <h2>📊 Performance Summary</h2>
            {generate_table(all_stats, "📋 Transaction Performance")}
        </div>'''
    
    @staticmethod
    def _generate_recommendations_html(recommendations: List[str]) -> str:
        """Generate HTML for recommendations section"""
        if not recommendations:
            return ''
        
        rec_items = ''.join([f'<li style="margin-bottom: 0.5rem;">{rec}</li>' for rec in recommendations])
        return f'''<div style="padding: 1rem; background: #fef3c7; border-left: 4px solid #d97706; border-radius: 4px;">
                    <h4 style="color: var(--text-primary); margin-bottom: 0.75rem;">💡 Recommendations</h4>
                    <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                        {rec_items}
                    </ul>
                </div>'''
    
    @staticmethod
    def _format_time_hhmmss(seconds: float) -> str:
        """Convert seconds to HH:MM:SS format"""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    @staticmethod
    def _abbreviate_label(label: str, max_length: int = 12) -> str:
        """Abbreviate transaction/request label for table display"""
        if len(label) <= max_length:
            return label
        # Try to abbreviate intelligently
        # If it has underscores or dashes, use first part
        if '_' in label:
            parts = label.split('_')
            if len(parts[0]) <= max_length:
                return parts[0]
        if '-' in label:
            parts = label.split('-')
            if len(parts[0]) <= max_length:
                return parts[0]
        # Otherwise, truncate with ellipsis
        return label[:max_length-1] + '…'
    
    @staticmethod
    def _detect_outliers_iqr(values: List[float]) -> tuple:
        """Detect outliers using Interquartile Range (IQR) method
        Returns: (lower_bound, upper_bound, outlier_mask)
        """
        if not values or len(values) < 4:
            return (0, float('inf'), [False] * len(values))
        
        values_array = np.array(values)
        q1 = np.percentile(values_array, 25)
        q3 = np.percentile(values_array, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        # Ensure lower bound is not negative for response times and throughput
        lower_bound = max(0, lower_bound)
        
        outlier_mask = (values_array < lower_bound) | (values_array > upper_bound)
        
        return (lower_bound, upper_bound, outlier_mask.tolist())
    
    @staticmethod
    def _filter_outliers(data_points: List[dict], value_key: str = 'y') -> List[dict]:
        """Filter outliers from data points using IQR method"""
        if not data_points or len(data_points) < 4:
            return data_points
        
        values = [point[value_key] for point in data_points]
        _, _, outlier_mask = HTMLReportGenerator._detect_outliers_iqr(values)
        
        # Return only non-outlier points
        filtered_points = [point for point, is_outlier in zip(data_points, outlier_mask) if not is_outlier]
        
        return filtered_points
    
    @staticmethod
    def _normalize_time_series_row(d: dict) -> dict:
        """Ensure throughput_pass / throughput_fail exist (legacy series had only total throughput)."""
        r = dict(d)
        tot = float(r.get("throughput", 0) or 0)
        tf = float(r.get("throughput_fail", 0) or 0)
        if r.get("throughput_pass") is not None:
            r["throughput_pass"] = float(r["throughput_pass"] or 0)
        else:
            r["throughput_pass"] = max(0.0, tot - tf)
        r["throughput_fail"] = tf
        return r

    @staticmethod
    def _downsample_time_series_for_system_behaviour_chart(
        time_series_data: List[dict], target_points: int = 55
    ) -> List[dict]:
        """Averages consecutive minute (or bucket) rows into at most target_points (~50–60) for the main chart."""
        if not time_series_data:
            return []
        norm = [HTMLReportGenerator._normalize_time_series_row(d) for d in time_series_data]
        n = len(norm)
        if n <= target_points:
            return norm
        out: List[dict] = []
        for b in range(target_points):
            i0 = int(b * n / target_points)
            i1 = int((b + 1) * n / target_points) if b < target_points - 1 else n
            chunk = norm[i0:i1]
            if not chunk:
                continue

            def mean_key(key: str) -> float:
                vals = [float(c.get(key) or 0) for c in chunk]
                return sum(vals) / len(vals)

            out.append({
                "time": round(mean_key("time"), 1),
                "avg_response_time": round(mean_key("avg_response_time"), 3),
                "vusers": round(mean_key("vusers"), 0),
                "throughput": round(mean_key("throughput"), 2),
                "throughput_pass": round(mean_key("throughput_pass"), 2),
                "throughput_fail": round(mean_key("throughput_fail"), 2),
                "pass_count": int(sum(int(c.get("pass_count") or 0) for c in chunk)),
                "fail_count": int(sum(int(c.get("fail_count") or 0) for c in chunk)),
                "error_rate_pct": round(mean_key("error_rate_pct"), 2),
            })
        return out

    @staticmethod
    def _generate_graph_data_table(time_series_data: List[dict] = None) -> str:
        """Minute- (or bucket-) level table: one row per interval; all rows shown with scroll."""
        if not time_series_data or len(time_series_data) == 0:
            return '<p style="color: var(--text-secondary); font-size: 0.9rem;">No time-series data available</p>'

        table_rows = ""
        for d in time_series_data:
            d = HTMLReportGenerator._normalize_time_series_row(d)
            time_formatted = HTMLReportGenerator._format_time_hhmmss(d["time"])
            tp = d.get("throughput", 0) or 0
            tpp = d.get("throughput_pass", 0) or 0
            tpf = d.get("throughput_fail", 0) or 0
            err_pct = d.get("error_rate_pct")
            if err_pct is None:
                p, f = int(d.get("pass_count") or 0), int(d.get("fail_count") or 0)
                err_pct = round(100.0 * f / (p + f), 2) if (p + f) else 0.0
            table_rows += f"""
            <tr>
                <td style="padding: 0.5rem; text-align: center;">{time_formatted}</td>
                <td style="padding: 0.5rem; text-align: center;">{d['avg_response_time']:.2f}</td>
                <td style="padding: 0.5rem; text-align: center;">{d['vusers']:.0f}</td>
                <td style="padding: 0.5rem; text-align: center;">{tp:.2f}</td>
                <td style="padding: 0.5rem; text-align: center;">{tpp:.2f}</td>
                <td style="padding: 0.5rem; text-align: center;">{tpf:.2f}</td>
                <td style="padding: 0.5rem; text-align: center;">{err_pct:.2f}%</td>
            </tr>
            """

        return f"""
            <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                <p style="font-size: 0.8rem; color: var(--text-secondary); margin: 0 0 0.5rem 0;">
                    One row per time bucket (typically 1 minute). The line chart uses ~50–55 averaged points.
                </p>
                <div style="overflow-y: auto; max-height: 500px;">
                    <table class="endpoint-table" style="font-size: 0.85rem;">
                        <thead style="position: sticky; top: 0; z-index: 10;">
                            <tr>
                                <th>Time (from start)</th>
                                <th>Avg RT (s)</th>
                                <th>VUsers</th>
                                <th>Total tput (r/s)</th>
                                <th>Pass tput (r/s)</th>
                                <th>Fail tput (r/s)</th>
                                <th>Error %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        """
    
    @staticmethod
    def _generate_graph_analysis_html(graph_analysis: Dict[str, Any], time_series_data: List[dict] = None) -> str:
        """Single correlated view: response time, throughput, pass/fail load, and reliability together."""
        distribution_analysis = graph_analysis.get("distribution_analysis", {}) or {}
        rt_unified = distribution_analysis.get("unified_understanding", "") or ""
        rt_stats = distribution_analysis.get("statistics", {}) or {}
        rt_dist_type = distribution_analysis.get("distribution_type", "unknown") or "unknown"

        tp_analysis_block = graph_analysis.get("throughput_distribution_analysis", {}) or {}
        tp_unified = tp_analysis_block.get("unified_understanding", "") or ""
        tp_stats = tp_analysis_block.get("statistics", {}) or {}
        tp_dist_type = tp_analysis_block.get("distribution_type", "unknown") or "unknown"

        if not rt_unified:
            analysis_text = graph_analysis.get("analysis", "Analysis not available.")
            sentences = analysis_text.split(". ")
            rt_unified = ". ".join(sentences[:3]) + "." if len(sentences) >= 3 else analysis_text

        pattern_text = graph_analysis.get("analysis", "") or ""
        sc = graph_analysis.get("system_correlation") or {}
        unified_bullets = sc.get("insights", []) or []
        unified_summary = sc.get("unified_summary", "")

        rt_stats_html = HTMLReportGenerator._generate_distribution_stats_html(rt_stats, "Response time (chart intervals)") if rt_stats else ""
        tp_stats_html = HTMLReportGenerator._generate_distribution_stats_html(tp_stats, "Total throughput (chart intervals)") if tp_stats else ""

        dist_badge_colors = {
            "normal": "#10b981",
            "right_skewed": "#f59e0b",
            "left_skewed": "#ef4444",
            "multi_modal": "#8b5cf6",
            "high_variance": "#f97316",
        }
        rt_badge_color = dist_badge_colors.get(rt_dist_type, "#6b7280")
        tp_badge_color = dist_badge_colors.get(tp_dist_type, "#6b7280")
        meta_badges = []
        if rt_dist_type != "unknown":
            meta_badges.append(
                f'<span style="padding: 0.35rem 0.75rem; background: {rt_badge_color}; color: white; border-radius: 10px; font-size: 0.8rem; font-weight: 600;">RT dist: {rt_dist_type.replace("_", " ")}</span>'
            )
        if tp_dist_type != "unknown":
            meta_badges.append(
                f'<span style="padding: 0.35rem 0.75rem; background: {tp_badge_color}; color: white; border-radius: 10px; font-size: 0.8rem; font-weight: 600;">TP dist: {tp_dist_type.replace("_", " ")}</span>'
            )
        meta_row = f'<div style="display: flex; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 1rem;">{"".join(meta_badges)}</div>' if meta_badges else ""

        combined_stats_row = f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.25rem;">{rt_stats_html or "<div></div>"}{tp_stats_html or "<div></div>"}</div>'

        bullets_html = ""
        if unified_bullets:
            li = "".join(
                f'<li style="margin-bottom: 0.6rem; line-height: 1.6;">{b}</li>'
                for b in unified_bullets
            )
            bullets_html = f"""
            <div style="padding: 1.25rem; background: #f8fafc; border-radius: 8px; border-left: 4px solid #0ea5e9; margin-top: 1rem;">
                <h5 style="margin: 0 0 0.75rem 0; font-size: 1.05rem;">Scalability, responsiveness, and reliability (correlated view)</h5>
                <ul style="margin: 0; padding-left: 1.25rem; font-size: 0.95rem;">{li}</ul>
            </div>
            """

        extra_pattern = ""
        if pattern_text and len(pattern_text) > 40:
            extra_pattern = f"""
            <div style="padding: 1rem; background: #fffbeb; border-radius: 6px; margin-top: 1rem; font-size: 0.95rem; line-height: 1.7;">
                <strong>Load pattern narrative:</strong> {pattern_text}
            </div>
            """

        stat_line = ""
        st = sc.get("statistics") or {}
        if st:
            stat_line = (
                '<p style="font-size: 0.9rem; color: var(--text-secondary); margin: 0.5rem 0 0 0;">'
                f"Interval-avg: response {st.get('avg_response', '—')}s · total tput {st.get('avg_throughput', '—')} req/s · "
                f"pass tput {st.get('avg_throughput_pass', '—')} · fail tput {st.get('avg_throughput_fail', '—')} · "
                f"vusers {st.get('avg_vusers', '—')} · mean interval error {st.get('avg_error_rate_interval', '—')}%</p>"
            )

        return f"""
            <div style="margin-bottom: 2rem;">
                <div style="padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%); border-radius: 8px; border: 2px solid #e5e7eb;">
                    <h3 style="margin: 0 0 0.5rem 0; color: var(--text-primary); font-size: 1.25rem; font-weight: 600;">Performance analysis (response time × throughput × errors)</h3>
                    <p style="margin: 0 0 1rem 0; color: var(--text-secondary); font-size: 0.95rem; line-height: 1.6;">
                        {unified_summary or "Throughput, successful throughput, and failure throughput are read together with average response time and virtual users. Rising load with falling pass-throughput, rising fail-throughput, or rising interval error % typically signals capacity or reliability risk—not an isolated 'slow' or 'low tput' issue."}
                    </p>
                    {meta_row}
                    <div style="padding: 1.25rem; background: white; border-radius: 8px; border: 1px solid #e2e8f0; margin-bottom: 1rem;">
                        <p style="margin: 0; line-height: 1.8; font-size: 0.98rem;"><strong>Distribution snapshot:</strong> {rt_unified}</p>
                        {("<p style='margin: 0.75rem 0 0 0; line-height: 1.8; font-size: 0.98rem;'><strong>Throughput shape:</strong> " + tp_unified + "</p>") if tp_unified else ""}
                    </div>
                    {combined_stats_row}
                    {stat_line}
                    {extra_pattern}
                    {bullets_html}
                </div>
            </div>
        """
    
    @staticmethod
    def _generate_additional_graphs(time_series_data: List[dict], transaction_stats: dict, request_stats: dict, metrics: Dict[str, Any], progress_callback=None) -> str:
        """Generate additional performance graphs"""
        if not time_series_data:
            return ''
        
        def update_progress(percent: int, message: str):
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except:
                    pass
        
        # Add progress logging
        print(f"  Generating additional graphs with {len(time_series_data):,} data points...")
        update_progress(10, "Starting additional graphs...")
        
        graphs_html = []
        
        # Graph 1: Response Time Under Load (X=Threads, Y=Response Time)
        print(f"    Generating Graph 1: Response Time Under Load...")
        update_progress(20, "Graph 1: Response Time Under Load...")
        graphs_html.append(HTMLReportGenerator._generate_response_time_under_load_graph(time_series_data))
        
        # Graph 2: Response Time Over Time by Transaction
        print(f"    Generating Graph 2: Response Time Over Time...")
        update_progress(40, "Graph 2: Response Time Over Time...")
        graphs_html.append(HTMLReportGenerator._generate_response_time_by_transaction_graph(time_series_data, transaction_stats, request_stats))
        
        # Graph 3: Throughput Over Time by Transaction vs VUsers
        print(f"    Generating Graph 3: Throughput Over Time...")
        update_progress(60, "Graph 3: Throughput Over Time...")
        graphs_html.append(HTMLReportGenerator._generate_throughput_by_transaction_graph(time_series_data, transaction_stats, request_stats))
        
        # Graph 4: Throughput PASS and Fail Over Time
        print(f"    Generating Graph 4: Pass/Fail Over Time...")
        update_progress(80, "Graph 4: Pass/Fail Over Time...")
        graphs_html.append(HTMLReportGenerator._generate_pass_fail_over_time_graph(time_series_data))
        
        # Graph 5: Error Analysis By Description
        print(f"    Generating Graph 5: Error Analysis...")
        update_progress(95, "Graph 5: Error Analysis...")
        graphs_html.append(HTMLReportGenerator._generate_error_analysis_graph(metrics))
        
        print(f"  All additional graphs generated")
        update_progress(100, "Additional graphs complete")
        return '\n'.join(graphs_html)
    
    @staticmethod
    def _generate_graph_observation(data_points: List[dict], graph_type: str) -> str:
        """Generate graph observation based on data trend analysis with health assessment parameters"""
        if not data_points or len(data_points) < 2:
            return '<p style="color: var(--text-secondary); font-size: 0.9rem;">Insufficient data for trend analysis.</p>'
        
        observations = []
        
        if graph_type == "response_time_under_load":
            # Analyze response time vs threads correlation
            threads = [d.get('threads', 0) for d in data_points]
            response_times = [d.get('response_time', 0) for d in data_points]
            if len(threads) > 1:
                # Calculate trend
                first_half_avg = sum(response_times[:len(response_times)//2]) / (len(response_times)//2)
                second_half_avg = sum(response_times[len(response_times)//2:]) / (len(response_times) - len(response_times)//2)
                avg_rt = sum(response_times) / len(response_times)
                rt_variance = sum((x - avg_rt) ** 2 for x in response_times) / len(response_times)
                rt_std = rt_variance ** 0.5
                cv = rt_std / avg_rt if avg_rt > 0 else 0
                
                if second_half_avg > first_half_avg * 1.2:
                    observations.append(f"Response time increases significantly as thread count increases (from {first_half_avg:.2f}s to {second_half_avg:.2f}s), indicating potential capacity constraints. System stability: Variable - resources may be insufficient at higher loads.")
                elif second_half_avg > first_half_avg * 1.1:
                    observations.append(f"Response time shows moderate increase with higher thread counts, suggesting some scalability limitations. System stability: Mostly stable with occasional bottlenecks.")
                else:
                    observations.append(f"Response time remains relatively stable across different thread counts (CV: {cv:.2%}), indicating good scalability. System stability: Stable and well-balanced. Current resources appear sufficient with minimal contention or queuing issues.")
        
        elif graph_type == "response_time_by_transaction":
            response_times = [d.get('response_time', 0) for d in data_points]
            if response_times:
                avg_rt = sum(response_times) / len(response_times)
                rt_variance = sum((x - avg_rt) ** 2 for x in response_times) / len(response_times)
                rt_std = rt_variance ** 0.5
                cv = rt_std / avg_rt if avg_rt > 0 else 0
                if cv < 0.2:
                    observations.append(f"Response time trends show consistent behavior over time (CV: {cv:.2%}). System stability: Stable. Resources are sufficient with no significant contention issues.")
                else:
                    observations.append(f"Response time shows variability over time (CV: {cv:.2%}), indicating inconsistent performance. System stability: Variable. May require resource optimization to reduce contention.")
        
        elif graph_type == "throughput_by_transaction":
            throughput = [d.get('throughput', 0) for d in data_points]
            if throughput:
                avg_tp = sum(throughput) / len(throughput)
                tp_variance = sum((x - avg_tp) ** 2 for x in throughput) / len(throughput)
                tp_std = tp_variance ** 0.5
                cv = tp_std / avg_tp if avg_tp > 0 else 0
                if cv < 0.2:
                    observations.append(f"Throughput patterns show consistent capacity and efficiency over time (CV: {cv:.2%}). System demonstrates stable performance with adequate resource allocation.")
                else:
                    observations.append(f"Throughput shows variability (CV: {cv:.2%}), suggesting inconsistent system capacity. May indicate resource contention or queuing issues at certain times.")
        
        elif graph_type == "pass_fail":
            pass_counts = [d.get('pass_count', 0) for d in data_points]
            fail_counts = [d.get('fail_count', 0) for d in data_points]
            total_fails = sum(fail_counts)
            total_passes = sum(pass_counts)
            if total_fails > 0:
                fail_rate = (total_fails / (total_passes + total_fails)) * 100
                if fail_rate > 5:
                    observations.append(f"High failure rate of {fail_rate:.1f}% indicates significant reliability issues requiring immediate attention. System stability: Unstable. Resources may be insufficient with frequent contention and queuing issues.")
                elif fail_rate > 1:
                    observations.append(f"Moderate failure rate of {fail_rate:.1f}% suggests some reliability concerns. System stability: Mostly stable but occasional bottlenecks may occur.")
                else:
                    observations.append(f"Low failure rate of {fail_rate:.1f}% demonstrates good system reliability. System stability: Stable and well-balanced. Resources are sufficient with minimal contention.")
            else:
                observations.append("No failures detected, indicating excellent system reliability. System stability: Highly stable and well-balanced. Resources are sufficient with no contention or queuing issues.")
        
        elif graph_type == "error_analysis":
            total_errors = sum(d.get('count', 0) for d in data_points)
            if total_errors > 0:
                observations.append(f"Error distribution analysis shows {total_errors} total errors. This indicates system reliability concerns that require attention. System stability: Variable. Resources may need optimization to handle error conditions better.")
            else:
                observations.append("No errors detected in the analysis. System demonstrates excellent reliability and error handling. System stability: Stable with no error-related contention issues.")
        
        if not observations:
            observations.append("Data analysis indicates normal system behavior patterns with stable performance.")
        
        return '<ul style="margin: 0; padding-left: 1.5rem; color: var(--text-secondary); font-size: 0.9rem; line-height: 1.6;">' + \
               ''.join([f'<li style="margin-bottom: 0.5rem;">{obs}</li>' for obs in observations]) + \
               '</ul>'
    
    @staticmethod
    def _generate_response_time_under_load_graph(time_series_data: List[dict]) -> str:
        """Graph 1: Response Time Under Load - X=Threads, Y=Response Time with 50/50 layout"""
        if not time_series_data:
            return ''
        
        # Group by threads (vusers) and calculate average response time
        threads_data = {}
        for d in time_series_data:
            threads = int(d.get('vusers', 0))
            if threads not in threads_data:
                threads_data[threads] = []
            threads_data[threads].append(d.get('avg_response_time', 0))
        
        # Calculate average response time per thread count
        threads_sorted = sorted(threads_data.keys())
        threads_list = threads_sorted
        avg_response_per_thread = [sum(threads_data[t]) / len(threads_data[t]) for t in threads_list]
        
        # Prepare data for table
        table_data = [{'threads': t, 'response_time': rt} for t, rt in zip(threads_list, avg_response_per_thread)]
        table_rows = ''.join([f'''
            <tr>
                <td style="padding: 0.5rem; text-align: center;">{d['threads']}</td>
                <td style="padding: 0.5rem; text-align: center;">{d['response_time']:.2f}s</td>
            </tr>''' for d in table_data[:20]])  # Limit to 20 rows
        
        # Generate observation
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "response_time_under_load")
        
        threads_json = json.dumps(threads_list)
        response_times_json = json.dumps(avg_response_per_thread)
        
        return f'''
        <div class="section">
            <h2>📈 Response Time Under Load</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Response time performance as load (threads) increases, showing how the system handles increasing user concurrency.
            </p>
            
            <!-- Graph and Data Table Side by Side (50/50) -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                <!-- Left: Graph (50%) -->
                <div class="chart-container" style="height: 400px;">
                    <canvas id="responseTimeUnderLoadChart"></canvas>
                </div>
                
                <!-- Right: Graph Data Table (50%) -->
                <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                    <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                    <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                        <div style="overflow-y: auto; max-height: 350px;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                                <thead style="position: sticky; top: 0; z-index: 10;">
                                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Threads</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Response Time (s)</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {table_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Graph Observation -->
            <div style="padding: 1.5rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; border-left: 4px solid #2563eb;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">🔍 Graph Observation</h4>
                {observation}
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('responseTimeUnderLoadChart');
            if (!ctx) return;
            
            const threads = {threads_json};
            const responseTimes = {response_times_json};
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: threads.map(t => t + ' threads'),
                    datasets: [{{
                        label: 'Avg Response Time (s)',
                        data: responseTimes,
                        borderColor: 'rgba(37, 99, 235, 1)',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        pointRadius: 4,
                        pointHoverRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        datalabels: {{ display: false }}
                    }},
                    scales: {{
                        x: {{
                            title: {{ display: true, text: 'Threads (VUsers)' }},
                            grid: {{ display: true }}
                        }},
                        y: {{
                            title: {{ display: true, text: 'Response Time (s)' }},
                            beginAtZero: true,
                            grid: {{ display: true }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        '''
    
    @staticmethod
    def _generate_response_time_by_transaction_graph(time_series_data: List[dict], transaction_stats: dict, request_stats: dict) -> str:
        """Graph 2: Response Time Over Time by Transaction - X=Time, Y1=Avg Response Time (multiple lines), Y2=Threads with 50/50 layout"""
        if not time_series_data:
            return ''
        
        time_labels = [HTMLReportGenerator._format_time_hhmmss(d['time']) for d in time_series_data]
        vusers = [d['vusers'] for d in time_series_data]
        
        # Collect all unique transaction/request labels that actually have data in time series
        # PRIORITY: Show transaction controllers (URL=NULL) if they exist, else show requests (URL!=NULL)
        transaction_controllers = set()  # Labels with URL=NULL
        requests_with_url = set()  # Labels with URL!=NULL
        
        for d in time_series_data:
            by_label = d.get('by_label', {})
            for label, label_info in by_label.items():
                if label_info.get('has_url', False):
                    requests_with_url.add(label)
                else:
                    transaction_controllers.add(label)
        
        # Decide which labels to show: prioritize transaction controllers
        if transaction_controllers:
            all_labels = sorted(list(transaction_controllers))
            print(f"  Using {len(all_labels)} transaction controllers (URL=NULL) for graph")
        elif requests_with_url:
            all_labels = sorted(list(requests_with_url))
            print(f"  Using {len(all_labels)} requests (URL!=NULL) for graph")
        else:
            # Fallback for backward compatibility (if no URL info available)
            all_labels = set()
            for d in time_series_data:
                by_label = d.get('by_label', {})
                all_labels.update(by_label.keys())
            if not all_labels:
                all_labels.update(transaction_stats.keys())
                all_labels.update(request_stats.keys())
            all_labels = sorted(list(all_labels))
            print(f"  Using {len(all_labels)} labels (no URL filtering) for graph")
        
        # Generate color palette for multiple lines
        colors = [
            'rgba(37, 99, 235, 1)',   # Blue
            'rgba(16, 185, 129, 1)',  # Green
            'rgba(245, 158, 11, 1)',  # Orange
            'rgba(239, 68, 68, 1)',   # Red
            'rgba(139, 92, 246, 1)',  # Purple
            'rgba(236, 72, 153, 1)',  # Pink
            'rgba(14, 165, 233, 1)',  # Sky
            'rgba(34, 197, 94, 1)',   # Emerald
            'rgba(251, 146, 60, 1)',  # Orange
            'rgba(168, 85, 247, 1)'   # Violet
        ]
        
        # Build datasets for each transaction/request and store color mapping
        datasets = []
        label_colors = {}  # Store color for each label for table headers
        for idx, label in enumerate(all_labels):
            # Extract response time data for this label over time as line points
            # Collect all data points first (including zeros if transaction exists in that interval)
            label_scatter_data = []
            for d in time_series_data:
                by_label = d.get('by_label', {})
                # Check if this label has data in this time interval
                if label in by_label:
                    label_data = by_label[label]
                    rt_value = label_data.get('avg_response_time', 0.0)
                    # Only add point if there's actual data (value > 0)
                    if rt_value > 0:
                        label_scatter_data.append({
                            'x': d['time'],
                            'y': rt_value
                        })
            
            # Filter outliers using IQR method
            if len(label_scatter_data) >= 4:
                label_scatter_data = HTMLReportGenerator._filter_outliers(label_scatter_data, value_key='y')
            
            color = colors[idx % len(colors)]
            label_colors[label] = color
            datasets.append({
                'label': label,
                'data': label_scatter_data,
                'borderColor': color,
                'backgroundColor': color.replace('1)', '0.2)'),  # Transparent fill
                'fill': False,
                'tension': 0.3,  # Smooth lines
                'yAxisID': 'y',
                'pointRadius': 3,
                'pointHoverRadius': 6,
                'showLine': True  # Show lines connecting points for each label
            })
        
        # Prepare data for table (sample every Nth point, show all transactions)
        sample_rate = max(1, len(time_series_data) // 20)
        sampled_data = time_series_data[::sample_rate][:20]
        
        # Build table header with colored transaction columns (abbreviated names)
        table_header = '<th style="padding: 0.75rem; text-align: center; font-weight: 600; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; white-space: nowrap;">Time</th>'
        for label in all_labels:
            color = label_colors[label]
            abbrev_label = HTMLReportGenerator._abbreviate_label(label, max_length=10)
            table_header += f'<th style="padding: 0.75rem; text-align: center; font-weight: 600; background: {color}; color: white; white-space: nowrap; min-width: 80px;" title="{label}">{abbrev_label}</th>'
        table_header += '<th style="padding: 0.75rem; text-align: center; font-weight: 600; background: rgba(245, 158, 11, 1); color: white; white-space: nowrap;">Threads</th>'
        
        # Build table rows with all transactions
        # Only show rows where at least one transaction has data (not all zeros)
        table_rows = ''
        for d in sampled_data:
            time_str = HTMLReportGenerator._format_time_hhmmss(d['time'])
            by_label = d.get('by_label', {})
            
            # Build row with time, then each transaction value, then threads
            row_cells = f'<td style="padding: 0.5rem; text-align: center;">{time_str}</td>'
            has_data = False
            for label in all_labels:
                # Only show value if transaction has data in this interval
                if label in by_label:
                    label_data = by_label[label]
                    rt = label_data.get('avg_response_time', 0.0)
                    if rt > 0:
                        has_data = True
                        row_cells += f'<td style="padding: 0.5rem; text-align: center;">{rt:.2f}s</td>'
                    else:
                        row_cells += f'<td style="padding: 0.5rem; text-align: center; color: #999;">-</td>'
                else:
                    row_cells += f'<td style="padding: 0.5rem; text-align: center; color: #999;">-</td>'
            row_cells += f'<td style="padding: 0.5rem; text-align: center;">{d["vusers"]:.0f}</td>'
            
            # Only add row if there's at least some data (not all dashes)
            if has_data:
                table_rows += f'<tr>{row_cells}</tr>'
        
        # Generate observation
        table_data = [{'time': d['time'], 'response_time': d['avg_response_time']} for d in sampled_data]
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "response_time_by_transaction")
        
        time_labels_json = json.dumps(time_labels)
        vusers_scatter_json = json.dumps([{'x': d['time'], 'y': d['vusers']} for d in time_series_data])
        datasets_json = json.dumps(datasets)
        
        return f'''
        <div class="section">
            <h2>📈 Response Time Over Time by Transaction</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Response time trends for different transactions/requests over time, with thread count overlay.
            </p>
            
            <!-- Graph (100% width) -->
            <div style="margin-bottom: 1.5rem;">
                <div class="chart-container" style="height: 400px; width: 100%;">
                    <canvas id="responseTimeByTransactionChart"></canvas>
                </div>
            </div>
            
            <!-- Graph Data Table (100% width below graph) -->
            <div style="padding: 1rem; background: var(--background-light); border-radius: 8px; margin-bottom: 1.5rem;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                    <div style="overflow-x: auto; overflow-y: auto; max-height: 400px;">
                        <table style="width: auto; min-width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                            <thead style="position: sticky; top: 0; z-index: 10;">
                                <tr>
                                    {table_header}
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Graph Observation -->
            <div style="padding: 1.5rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; border-left: 4px solid #2563eb;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">🔍 Graph Observation</h4>
                {observation}
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('responseTimeByTransactionChart');
            if (!ctx) return;
            
            const timeLabels = {time_labels_json};
            const vusersScatter = {vusers_scatter_json};
            const datasets = {datasets_json};
            
            // Add threads as scatter plot (can optionally show as line)
            datasets.push({{
                label: 'Threads (VUsers)',
                data: vusersScatter,
                borderColor: 'rgba(245, 158, 11, 1)',
                backgroundColor: 'rgba(245, 158, 11, 0.3)',
                borderWidth: 1,
                pointRadius: 3,
                pointHoverRadius: 5,
                yAxisID: 'y1',
                showLine: true,
                tension: 0.4
            }});
            
            new Chart(ctx, {{
                type: 'scatter',
                data: {{
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        datalabels: {{ display: false }}
                    }},
                    scales: {{
                        x: {{
                            type: 'linear',
                            position: 'bottom',
                            title: {{ display: true, text: 'Time (seconds)' }},
                            grid: {{ display: true }},
                            ticks: {{
                                callback: function(value) {{
                                    const hours = Math.floor(value / 3600);
                                    const minutes = Math.floor((value % 3600) / 60);
                                    const secs = Math.floor(value % 60);
                                    return hours > 0 ? `${{hours}}:${{String(minutes).padStart(2, '0')}}:${{String(secs).padStart(2, '0')}}` : `${{minutes}}:${{String(secs).padStart(2, '0')}}`;
                                }}
                            }}
                        }},
                        y: {{
                            type: 'linear',
                            position: 'left',
                            title: {{ display: true, text: 'Avg Response Time (s)' }},
                            beginAtZero: true,
                            grid: {{ display: true }}
                        }},
                        y1: {{
                            type: 'linear',
                            position: 'right',
                            title: {{ display: true, text: 'Threads' }},
                            beginAtZero: true,
                            grid: {{ display: false }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        '''
    
    @staticmethod
    def _generate_throughput_by_transaction_graph(time_series_data: List[dict], transaction_stats: dict, request_stats: dict) -> str:
        """Graph 3: Throughput Over Time by Transaction vs VUsers - X=Time, Y1=Throughput, Y2=Threads with 50/50 layout"""
        if not time_series_data:
            return ''
        
        time_labels = [HTMLReportGenerator._format_time_hhmmss(d['time']) for d in time_series_data]
        vusers = [d['vusers'] for d in time_series_data]
        
        # Collect all unique transaction/request labels that actually have data in time series
        # PRIORITY: Show transaction controllers (URL=NULL) if they exist, else show requests (URL!=NULL)
        transaction_controllers = set()  # Labels with URL=NULL
        requests_with_url = set()  # Labels with URL!=NULL
        
        for d in time_series_data:
            by_label = d.get('by_label', {})
            for label, label_info in by_label.items():
                if label_info.get('has_url', False):
                    requests_with_url.add(label)
                else:
                    transaction_controllers.add(label)
        
        # Decide which labels to show: prioritize transaction controllers
        if transaction_controllers:
            all_labels = sorted(list(transaction_controllers))
            print(f"  Using {len(all_labels)} transaction controllers (URL=NULL) for throughput graph")
        elif requests_with_url:
            all_labels = sorted(list(requests_with_url))
            print(f"  Using {len(all_labels)} requests (URL!=NULL) for throughput graph")
        else:
            # Fallback for backward compatibility (if no URL info available)
            all_labels = set()
            for d in time_series_data:
                by_label = d.get('by_label', {})
                all_labels.update(by_label.keys())
            if not all_labels:
                all_labels.update(transaction_stats.keys())
                all_labels.update(request_stats.keys())
            all_labels = sorted(list(all_labels))
            print(f"  Using {len(all_labels)} labels (no URL filtering) for throughput graph")
        
        # Generate color palette for multiple lines
        colors = [
            'rgba(37, 99, 235, 1)',   # Blue
            'rgba(16, 185, 129, 1)',  # Green
            'rgba(245, 158, 11, 1)',  # Orange
            'rgba(239, 68, 68, 1)',   # Red
            'rgba(139, 92, 246, 1)',  # Purple
            'rgba(236, 72, 153, 1)',  # Pink
            'rgba(14, 165, 233, 1)',  # Sky
            'rgba(34, 197, 94, 1)',   # Emerald
            'rgba(251, 146, 60, 1)',  # Orange
            'rgba(168, 85, 247, 1)'   # Violet
        ]
        
        # Build datasets for each transaction/request and store color mapping
        datasets = []
        label_colors = {}  # Store color for each label for table headers
        for idx, label in enumerate(all_labels):
            # Extract throughput data for this label over time as line points
            # Collect all data points first (including zeros if transaction exists in that interval)
            label_scatter_data = []
            for d in time_series_data:
                by_label = d.get('by_label', {})
                # Check if this label has data in this time interval
                if label in by_label:
                    label_data = by_label[label]
                    tp_value = label_data.get('throughput', 0)
                    # Only add point if there's actual data (value > 0)
                    if tp_value > 0:
                        label_scatter_data.append({
                            'x': d['time'],
                            'y': tp_value
                        })
            
            # Filter outliers using IQR method
            if len(label_scatter_data) >= 4:
                label_scatter_data = HTMLReportGenerator._filter_outliers(label_scatter_data, value_key='y')
            
            color = colors[idx % len(colors)]
            label_colors[label] = color
            datasets.append({
                'label': label,
                'data': label_scatter_data,
                'borderColor': color,
                'backgroundColor': color.replace('1)', '0.2)'),  # Transparent fill
                'fill': False,
                'tension': 0.3,  # Smooth lines
                'yAxisID': 'y',
                'pointRadius': 3,
                'pointHoverRadius': 6,
                'showLine': True  # Show lines connecting points for each label
            })
        
        # Prepare data for table (sample every Nth point, show all transactions)
        sample_rate = max(1, len(time_series_data) // 20)
        sampled_data = time_series_data[::sample_rate][:20]
        
        # Build table header with colored transaction columns (abbreviated names)
        table_header = '<th style="padding: 0.75rem; text-align: center; font-weight: 600; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; white-space: nowrap;">Time</th>'
        for label in all_labels:
            color = label_colors[label]
            abbrev_label = HTMLReportGenerator._abbreviate_label(label, max_length=10)
            table_header += f'<th style="padding: 0.75rem; text-align: center; font-weight: 600; background: {color}; color: white; white-space: nowrap; min-width: 80px;" title="{label}">{abbrev_label}</th>'
        table_header += '<th style="padding: 0.75rem; text-align: center; font-weight: 600; background: rgba(245, 158, 11, 1); color: white; white-space: nowrap;">Threads</th>'
        
        # Build table rows with all transactions
        # Only show rows where at least one transaction has data (not all zeros)
        table_rows = ''
        for d in sampled_data:
            time_str = HTMLReportGenerator._format_time_hhmmss(d['time'])
            by_label = d.get('by_label', {})
            
            # Build row with time, then each transaction value, then threads
            row_cells = f'<td style="padding: 0.5rem; text-align: center;">{time_str}</td>'
            has_data = False
            for label in all_labels:
                # Only show value if transaction has data in this interval
                if label in by_label:
                    label_data = by_label[label]
                    tp = label_data.get('throughput', 0)
                    if tp > 0:
                        has_data = True
                        row_cells += f'<td style="padding: 0.5rem; text-align: center;">{int(tp)}</td>'  # Show count as integer
                    else:
                        row_cells += f'<td style="padding: 0.5rem; text-align: center; color: #999;">-</td>'
                else:
                    row_cells += f'<td style="padding: 0.5rem; text-align: center; color: #999;">-</td>'
            row_cells += f'<td style="padding: 0.5rem; text-align: center;">{d["vusers"]:.0f}</td>'
            
            # Only add row if there's at least some data (not all dashes)
            if has_data:
                table_rows += f'<tr>{row_cells}</tr>'
        
        # Generate observation
        table_data = [{'time': d['time'], 'throughput': d['throughput']} for d in sampled_data]
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "throughput_by_transaction")
        
        time_labels_json = json.dumps(time_labels)
        vusers_scatter_json = json.dumps([{'x': d['time'], 'y': d['vusers']} for d in time_series_data])
        datasets_json = json.dumps(datasets)
        
        return f'''
        <div class="section">
            <h2>📈 Sample Count Over Time by Transaction vs VUsers</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Number of samples (executions) for each transaction controller over time, compared with virtual user load.
            </p>
            
            <!-- Graph (100% width) -->
            <div style="margin-bottom: 1.5rem;">
                <div class="chart-container" style="height: 400px; width: 100%;">
                    <canvas id="throughputByTransactionChart"></canvas>
                </div>
            </div>
            
            <!-- Graph Data Table (100% width below graph) -->
            <div style="padding: 1rem; background: var(--background-light); border-radius: 8px; margin-bottom: 1.5rem;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                    <div style="overflow-x: auto; overflow-y: auto; max-height: 400px;">
                        <table style="width: auto; min-width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                            <thead style="position: sticky; top: 0; z-index: 10;">
                                <tr>
                                    {table_header}
                                </tr>
                            </thead>
                            <tbody>
                                {table_rows}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
            
            <!-- Graph Observation -->
            <div style="padding: 1.5rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; border-left: 4px solid #2563eb;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">🔍 Graph Observation</h4>
                {observation}
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('throughputByTransactionChart');
            if (!ctx) return;
            
            const timeLabels = {time_labels_json};
            const vusersScatter = {vusers_scatter_json};
            const datasets = {datasets_json};
            
            // Add threads as scatter plot (can optionally show as line)
            datasets.push({{
                label: 'Threads (VUsers)',
                data: vusersScatter,
                borderColor: 'rgba(245, 158, 11, 1)',
                backgroundColor: 'rgba(245, 158, 11, 0.3)',
                borderWidth: 1,
                pointRadius: 3,
                pointHoverRadius: 5,
                yAxisID: 'y1',
                showLine: true,
                tension: 0.4
            }});
            
            new Chart(ctx, {{
                type: 'scatter',
                data: {{
                    datasets: datasets
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        datalabels: {{ display: false }}
                    }},
                    scales: {{
                        x: {{
                            type: 'linear',
                            position: 'bottom',
                            title: {{ display: true, text: 'Time (seconds)' }},
                            grid: {{ display: true }},
                            ticks: {{
                                callback: function(value) {{
                                    const hours = Math.floor(value / 3600);
                                    const minutes = Math.floor((value % 3600) / 60);
                                    const secs = Math.floor(value % 60);
                                    return hours > 0 ? `${{hours}}:${{String(minutes).padStart(2, '0')}}:${{String(secs).padStart(2, '0')}}` : `${{minutes}}:${{String(secs).padStart(2, '0')}}`;
                                }}
                            }}
                        }},
                        y: {{
                            type: 'linear',
                            position: 'left',
                            title: {{ display: true, text: 'Sample Count' }},
                            beginAtZero: true,
                            grid: {{ display: true }}
                        }},
                        y1: {{
                            type: 'linear',
                            position: 'right',
                            title: {{ display: true, text: 'Threads' }},
                            beginAtZero: true,
                            grid: {{ display: false }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        '''
    
    @staticmethod
    def _generate_pass_fail_over_time_graph(time_series_data: List[dict]) -> str:
        """Graph 4: Throughput PASS and Fail Over Time - X=Time, Y1=Pass/Fail counts, Y2=Threads with 50/50 layout"""
        if not time_series_data:
            return ''
        
        time_labels = [HTMLReportGenerator._format_time_hhmmss(d['time']) for d in time_series_data]
        pass_counts = [d.get('pass_count', 0) for d in time_series_data]
        fail_counts = [d.get('fail_count', 0) for d in time_series_data]
        vusers = [d['vusers'] for d in time_series_data]
        
        # Prepare data for table
        sample_rate = max(1, len(time_series_data) // 20)
        sampled_data = time_series_data[::sample_rate][:20]
        table_rows = ''.join([f'''
            <tr>
                <td style="padding: 0.5rem; text-align: center;">{HTMLReportGenerator._format_time_hhmmss(d['time'])}</td>
                <td style="padding: 0.5rem; text-align: center;">{d.get('pass_count', 0)}</td>
                <td style="padding: 0.5rem; text-align: center;">{d.get('fail_count', 0)}</td>
                <td style="padding: 0.5rem; text-align: center;">{d['vusers']:.0f}</td>
            </tr>''' for d in sampled_data])
        
        # Generate observation
        table_data = [{'time': d['time'], 'pass_count': d.get('pass_count', 0), 'fail_count': d.get('fail_count', 0)} for d in sampled_data]
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "pass_fail")
        
        time_labels_json = json.dumps(time_labels)
        pass_counts_json = json.dumps(pass_counts)
        fail_counts_json = json.dumps(fail_counts)
        vusers_json = json.dumps(vusers)
        
        return f'''
        <div class="section">
            <h2>📈 Throughput PASS and Fail Over Time</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Pass and fail transaction counts over time with thread count overlay.
            </p>
            
            <!-- Graph and Data Table Side by Side (50/50) -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                <!-- Left: Graph (50%) -->
                <div class="chart-container" style="height: 400px;">
                    <canvas id="passFailOverTimeChart"></canvas>
                </div>
                
                <!-- Right: Graph Data Table (50%) -->
                <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                    <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                    <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                        <div style="overflow-y: auto; max-height: 350px;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                                <thead style="position: sticky; top: 0; z-index: 10;">
                                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Time</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Pass Count</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Fail Count</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Threads</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {table_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- Graph Observation -->
            <div style="padding: 1.5rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; border-left: 4px solid #2563eb;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">🔍 Graph Observation</h4>
                {observation}
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('passFailOverTimeChart');
            if (!ctx) return;
            
            const timeLabels = {time_labels_json};
            const passCounts = {pass_counts_json};
            const failCounts = {fail_counts_json};
            const vusers = {vusers_json};
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: timeLabels,
                    datasets: [{{
                        label: 'Pass Count',
                        data: passCounts,
                        borderColor: 'rgba(16, 185, 129, 1)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y',
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }}, {{
                        label: 'Fail Count',
                        data: failCounts,
                        borderColor: 'rgba(239, 68, 68, 1)',
                        backgroundColor: 'rgba(239, 68, 68, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y',
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }}, {{
                        label: 'Threads (VUsers)',
                        data: vusers,
                        borderColor: 'rgba(245, 158, 11, 1)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        borderDash: [5, 5],
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y1',
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        datalabels: {{ display: false }}
                    }},
                    scales: {{
                        x: {{
                            title: {{ display: true, text: 'Time' }},
                            grid: {{ display: true }}
                        }},
                        y: {{
                            type: 'linear',
                            position: 'left',
                            title: {{ display: true, text: 'Transaction Count' }},
                            beginAtZero: true,
                            grid: {{ display: true }}
                        }},
                        y1: {{
                            type: 'linear',
                            position: 'right',
                            title: {{ display: true, text: 'Threads' }},
                            beginAtZero: true,
                            grid: {{ display: false }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        '''
    
    @staticmethod
    def _generate_error_analysis_graph(metrics: Dict[str, Any]) -> str:
        """Graph 5: Error Analysis By Description - uses error_by_description (failed samples) or HTTP 4xx/5xx."""
        response_codes = metrics.get('response_codes', {})
        error_codes = {k: v for k, v in response_codes.items() if str(k).startswith(('4', '5'))}
        summary = metrics.get('summary', {})
        error_by_description = summary.get('error_by_description') or {}

        # Prefer error_by_description (all failed samples with message/code); fallback to HTTP 4xx/5xx only
        if error_by_description:
            # Sort by count descending; use description as label
            sorted_errors = sorted(error_by_description.items(), key=lambda x: x[1], reverse=True)
            error_labels = [desc for desc, _ in sorted_errors]
            error_counts = [count for _, count in sorted_errors]
            use_description_table = True
        elif error_codes:
            error_labels = list(error_codes.keys())
            error_counts = list(error_codes.values())
            use_description_table = False
        else:
            # No errors at all
            return f'''
        <div class="section">
            <h2>📈 Error Analysis By Description</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Error distribution analysis by response code and description.
            </p>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                <div class="chart-container" style="height: 400px;">
                    <canvas id="errorAnalysisChart"></canvas>
                </div>
                <div style="padding: 1rem; background: var(--background-light); border-radius: 8px; display: flex; align-items: center; justify-content: center;">
                    <p style="text-align: center; color: var(--text-secondary);">
                        <em>No errors detected in this test run.</em>
                    </p>
                </div>
            </div>
            <div style="padding: 1.5rem; background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); border-radius: 8px; border-left: 4px solid #10b981;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">🔍 Graph Observation</h4>
                <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">No errors detected, indicating excellent system reliability and error handling.</p>
            </div>
        </div>
        '''

        if use_description_table:
            table_rows = ''.join([f'''
            <tr>
                <td style="padding: 0.5rem; max-width: 320px; overflow: hidden; text-overflow: ellipsis; word-wrap: break-word;">{html.escape(desc)}</td>
                <td style="padding: 0.5rem; text-align: center;">{count}</td>
            </tr>''' for desc, count in sorted_errors])
            table_header = '''
                                <thead style="position: sticky; top: 0; z-index: 10;">
                                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                        <th style="padding: 0.75rem; text-align: left; font-weight: 600;">Description</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Count</th>
                                    </tr>
                                </thead>'''
        else:
            table_rows = ''.join([f'''
            <tr>
                <td style="padding: 0.5rem; text-align: center;">{code}</td>
                <td style="padding: 0.5rem; text-align: center;">{count}</td>
                <td style="padding: 0.5rem; text-align: center;">{"Client Error" if str(code).startswith("4") else "Server Error"}</td>
            </tr>''' for code, count in zip(error_labels, error_counts)])
            table_header = '''
                                <thead style="position: sticky; top: 0; z-index: 10;">
                                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Error Code</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Count</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Type</th>
                                    </tr>
                                </thead>'''

        table_data = [{'code': d if not use_description_table else d, 'count': c} for d, c in (zip(error_labels, error_counts) if not use_description_table else sorted_errors)]
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "error_analysis")
        # Chart labels: truncate long descriptions for display
        chart_labels = [f"{d[:30]}..." if len(str(d)) > 30 else str(d) for d in error_labels]
        error_labels_json = json.dumps(chart_labels)
        error_counts_json = json.dumps(error_counts)

        return f'''
        <div class="section">
            <h2>📈 Error Analysis By Description</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Error distribution by description (failure message / response code) showing frequency of different error types.
            </p>

            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                <div class="chart-container" style="height: 400px;">
                    <canvas id="errorAnalysisChart"></canvas>
                </div>
                <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                    <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                    <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                        <div style="overflow-y: auto; max-height: 350px;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                                {table_header}
                                <tbody>
                                    {table_rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

            <div style="padding: 1.5rem; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 8px; border-left: 4px solid #2563eb;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">🔍 Graph Observation</h4>
                {observation}
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('errorAnalysisChart');
            if (!ctx) return;
            
            const errorLabels = {error_labels_json};
            const errorCounts = {error_counts_json};
            
            new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: errorLabels,
                    datasets: [{{
                        label: 'Error Count',
                        data: errorCounts,
                        backgroundColor: [
                            'rgba(239, 68, 68, 0.8)',
                            'rgba(220, 38, 38, 0.8)',
                            'rgba(185, 28, 28, 0.8)',
                            'rgba(153, 27, 27, 0.8)'
                        ],
                        borderColor: [
                            'rgba(239, 68, 68, 1)',
                            'rgba(220, 38, 38, 1)',
                            'rgba(185, 28, 28, 1)',
                            'rgba(153, 27, 27, 1)'
                        ],
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {{
                        legend: {{ display: false }},
                        datalabels: {{
                            display: true,
                            anchor: 'end',
                            align: 'top',
                            formatter: (value) => value
                        }}
                    }},
                    scales: {{
                        x: {{
                            title: {{ display: true, text: 'Error Type' }},
                            grid: {{ display: false }}
                        }},
                        y: {{
                            title: {{ display: true, text: 'Error Count' }},
                            beginAtZero: true,
                            grid: {{ display: true }}
                        }}
                    }}
                }}
            }});
        }});
        </script>
        '''
    
    @staticmethod
    def _generate_statistical_analysis_points(stats: Dict[str, Any], metric_type: str = "response_time") -> List[str]:
        """
        Generate analysis points based on statistical summary
        metric_type: "response_time" or "throughput"
        Returns list of analysis bullet points
        """
        if not stats:
            return []
        
        mean = stats.get('mean', 0)
        median = stats.get('median', 0)
        std_dev = stats.get('std_deviation', 0)
        variance = stats.get('variance', 0)
        cv = stats.get('coefficient_of_variation', 0)  # Already as decimal
        skewness = stats.get('skewness', 0)
        
        points = []
        unit = "s" if metric_type == "response_time" else " req/s"
        metric_name = "response time" if metric_type == "response_time" else "throughput"
        MetricName = "Response Time" if metric_type == "response_time" else "Throughput"
        
        # Point 1: Median vs Mean comparison
        if median < mean:
            points.append(
                f"The median {metric_name} ({median:.2f}{unit}) is lower than the mean ({mean:.2f}{unit}), "
                f"indicating that most requests are served quickly, but a small number of very slow requests "
                f"significantly increase the overall average."
            )
        elif median > mean:
            points.append(
                f"The median {metric_name} ({median:.2f}{unit}) is higher than the mean ({mean:.2f}{unit}), "
                f"indicating that most requests experience slower performance, with some very fast outliers "
                f"pulling down the average."
            )
        else:
            points.append(
                f"The median and mean {metric_name} are similar ({mean:.2f}{unit}), indicating a relatively "
                f"symmetric distribution with consistent performance across requests."
            )
        
        # Point 2: Standard Deviation analysis
        if std_dev > mean:
            points.append(
                f"The very high standard deviation ({std_dev:.2f}{unit}) compared to the mean shows that "
                f"{metric_name}s are highly dispersed, meaning users experience widely different performance."
            )
        elif std_dev > mean * 0.5:
            points.append(
                f"The standard deviation ({std_dev:.2f}{unit}) is close to the mean, indicating moderate "
                f"variability but not extreme instability."
            )
        else:
            points.append(
                f"The standard deviation ({std_dev:.2f}{unit}) is relatively low compared to the mean, "
                f"indicating consistent and predictable performance."
            )
        
        # Point 3: Variance analysis
        if variance > mean * mean:
            points.append(
                f"The large variance ({variance:.2f}) confirms that the system has extreme fluctuations "
                f"rather than stable, predictable behavior."
            )
        elif variance > (mean * mean) * 0.25:
            points.append(
                f"The variance ({variance:.2f}) suggests that {metric_name}s fluctuate, but within a "
                f"reasonable and controllable range."
            )
        else:
            points.append(
                f"The low variance ({variance:.2f}) indicates stable and consistent system behavior "
                f"with minimal fluctuations."
            )
        
        # Point 4: Coefficient of Variation
        cv_pct = cv * 100  # Convert to percentage for display
        if cv > 2.0:
            points.append(
                f"A Coefficient of Variation of {cv_pct:.2f}% means the system is severely unstable; "
                f"performance varies more than twice the average {metric_name}, which is a critical reliability risk."
            )
        elif cv > 1.0:
            points.append(
                f"A Coefficient of Variation of {cv_pct:.2f}% indicates noticeable variability, but it is "
                f"far more stable than a chaotic system; this level is typical of systems under mixed or real-world load."
            )
        elif cv > 0.5:
            points.append(
                f"A Coefficient of Variation of {cv_pct:.2f}% indicates moderate variability, showing some "
                f"inconsistency but within acceptable limits for most applications."
            )
        else:
            points.append(
                f"A Coefficient of Variation of {cv_pct:.2f}% indicates very stable and consistent performance, "
                f"with minimal variation around the mean."
            )
        
        # Point 5: Skewness analysis
        if skewness > 2.0:
            points.append(
                f"The extremely high skewness ({skewness:.2f}) indicates a heavy right-tailed distribution, "
                f"meaning a small percentage of requests take disproportionately long to complete."
            )
        elif skewness > 1.0:
            points.append(
                f"The high skewness ({skewness:.2f}) shows a right-skewed distribution, with some slower "
                f"requests creating a noticeable tail in the performance distribution."
            )
        elif skewness > 0.5:
            points.append(
                f"The skewness of {skewness:.2f} shows a mild right skew, meaning a few slower responses exist, "
                f"but there is no severe long-tail latency problem."
            )
        elif skewness < -0.5:
            points.append(
                f"The negative skewness ({skewness:.2f}) indicates a left-skewed distribution, where most "
                f"requests are relatively slow with some fast outliers."
            )
        else:
            points.append(
                f"The skewness of {skewness:.2f} indicates a relatively symmetric distribution, suggesting "
                f"balanced performance without significant outliers in either direction."
            )
        
        # Point 6-9: Perspective-based analysis
        # Responsiveness perspective
        if metric_type == "response_time":
            if median < 1.0:
                points.append(
                    f"From a responsiveness perspective, the system is generally fast, with most users getting "
                    f"responses in under a second."
                )
            elif median < 2.0:
                points.append(
                    f"From a responsiveness perspective, the system appears fast for most users but is "
                    f"occasionally very slow, creating inconsistent interaction times."
                )
            else:
                points.append(
                    f"From a responsiveness perspective, the system feels fast for many users but suddenly "
                    f"very slow for others."
                )
        else:  # throughput
            if mean > 100:
                points.append(
                    f"From a responsiveness perspective, the system handles high request volumes effectively, "
                    f"processing most requests quickly."
                )
            elif mean > 50:
                points.append(
                    f"From a responsiveness perspective, the system shows good throughput capacity but with "
                    f"some variability in processing rates."
                )
            else:
                points.append(
                    f"From a responsiveness perspective, the system shows limited throughput capacity, "
                    f"indicating potential bottlenecks or resource constraints."
                )
        
        # Reliability perspective
        if cv > 1.0:
            points.append(
                f"From a reliability perspective, performance cannot be trusted because {metric_name}s change "
                f"drastically between users and over time."
            )
        elif cv > 0.5:
            points.append(
                f"From a reliability perspective, performance is mostly consistent, with some variation but "
                f"no extreme unpredictability."
            )
        else:
            points.append(
                f"From a reliability perspective, performance is highly consistent and predictable, "
                f"building user trust in the application."
            )
        
        # Scalability perspective
        if skewness > 1.0 or cv > 1.0:
            if metric_type == "response_time":
                points.append(
                    f"From a scalability perspective, these long-tail delays will worsen as load increases, "
                    f"leading to queuing, thread exhaustion, and cascading slowdowns."
                )
            else:
                points.append(
                    f"From a scalability perspective, the high variability in throughput will become more "
                    f"pronounced under increased load, leading to inconsistent performance and potential failures."
                )
        else:
            points.append(
                f"From a scalability perspective, the system is likely to handle increased load reasonably well, "
                f"as there is no heavy tail to amplify delays."
            )
        
        # User experience perspective
        if cv > 1.0 or skewness > 1.0:
            if metric_type == "response_time":
                points.append(
                    f"From a user experience perspective, even though many users see fast responses, the very "
                    f"slow outliers dominate perception, causing frustration, retries, and loss of trust in the application."
                )
            else:
                points.append(
                    f"From a user experience perspective, the inconsistent throughput creates unpredictable "
                    f"user experiences, leading to frustration and potential abandonment during slow periods."
                )
        else:
            points.append(
                f"From a user experience perspective, the system will feel smooth and responsive, with only "
                f"occasional slow interactions that most users will tolerate."
            )
        
        return points
    
    @staticmethod
    def _generate_distribution_stats_html(stats: Dict[str, Any], metric_label: str = "Response Time") -> str:
        """Generate HTML for distribution statistics"""
        if not stats:
            return ''
        
        unit = "s" if "Response" in metric_label else " req/s"
        
        return f'''
            <div style="padding: 1rem; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                <h5 style="margin: 0 0 0.75rem 0; color: var(--text-primary); font-size: 0.95rem; font-weight: 600;">{metric_label} Statistical Summary</h5>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.85rem;">
                    <div><strong>Mean:</strong> {stats.get('mean', 0):.2f}{unit}</div>
                    <div><strong>Median:</strong> {stats.get('median', 0):.2f}{unit}</div>
                    <div><strong>Std Deviation:</strong> {stats.get('std_deviation', 0):.2f}{unit}</div>
                    <div><strong>Variance:</strong> {stats.get('variance', 0):.2f}</div>
                    <div><strong>Coefficient of Variation:</strong> {stats.get('coefficient_of_variation', 0):.2%}</div>
                    <div><strong>Skewness:</strong> {stats.get('skewness', 0):.2f}</div>
                </div>
            </div>
        '''
    
    @staticmethod
    def _generate_business_answers_html(
        business_answers: Dict[str, Dict[str, Any]],
        show_outer_title: bool = True,
    ) -> str:
        """HTML for the four distribution-based diagnostic cards. Omit outer 🎯 title when embedded under Quick diagnostic."""
        if not business_answers:
            return ""
        esc = html.escape
        answer_colors = {
            "YES": "#10b981",
            "MOSTLY": "#f59e0b",
            "PARTIALLY": "#f59e0b",
            "NO": "#ef4444",
            "VARIABLE": "#8b5cf6",
            "MINIMAL": "#10b981",
        }
        question_labels = {
            "stability": "1. System is Stable and Well Balanced",
            "resource_sufficiency": "2. Current Resources (CPU, Memory, Threads, DB connections) are Sufficient",
            "contention": "3. Contention or Queuing Issues",
            "bottlenecks": "4. Occasional Bottlenecks",
        }
        questions_html = ""
        for key, label in question_labels.items():
            if key not in business_answers:
                continue
            answer_data = business_answers[key]
            answer = esc(str(answer_data.get("answer", "UNKNOWN")))
            confidence = esc(str(answer_data.get("confidence", "Medium")))
            explanation = esc(str(answer_data.get("explanation", "")))
            answer_raw = str(answer_data.get("answer", "UNKNOWN"))
            answer_color = answer_colors.get(answer_raw, "#6b7280")
            if answer_raw.startswith("YES"):
                answer_color = "#10b981" if answer_raw == "YES" else "#f59e0b"
            elif answer_raw.startswith("NO"):
                answer_color = "#ef4444"
            questions_html += f'''
                    <div style="margin-top: 0.75rem; padding: 0.75rem; background: white; border-radius: 6px; border-left: 3px solid {answer_color};">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                            <h5 style="margin: 0; color: var(--text-primary); font-size: 0.9rem; font-weight: 600;">{esc(label)}</h5>
                            <div style="display: flex; align-items: center; gap: 0.5rem;">
                                <span style="padding: 0.2rem 0.6rem; background: {answer_color}; color: white; border-radius: 10px; font-size: 0.7rem; font-weight: 600;">
                                    {answer}
                                </span>
                                <span style="padding: 0.2rem 0.5rem; background: #e5e7eb; color: var(--text-secondary); border-radius: 6px; font-size: 0.65rem;">
                                    {confidence}
                                </span>
                            </div>
                        </div>
                        <p style="margin: 0; color: var(--text-secondary); font-size: 0.8rem; line-height: 1.5;">{explanation}</p>
                    </div>
                '''
        title_html = (
            '<h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.05rem; font-weight: 600;">🎯 System Health Assessment</h4>'
            if show_outer_title
            else ""
        )
        return f'''
            <div style="margin-top: 1.5rem; padding: 1.5rem; background: linear-gradient(135deg, #f3f4f6 0%, #ffffff 100%); border-radius: 8px; border: 2px solid #e5e7eb;">
                {title_html}
                {questions_html}
            </div>
        '''
    
    @staticmethod
    def _generate_enhanced_system_health_html(assessment: Dict[str, Any]) -> str:
        """Full-width System Health Assessment (Enhanced) block."""
        if not assessment:
            return ""
        esc = html.escape
        badges = assessment.get("badges") or {}
        subtitle = esc(str(assessment.get("subtitle") or ""))

        def badge_cell(label: str, value: str) -> str:
            return f'''
                <div style="padding: 0.75rem 1rem; background: white; border-radius: 8px; border: 1px solid #e5e7eb; text-align: center;">
                    <div style="font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.04em;">{esc(label)}</div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #1e293b; margin-top: 0.25rem;">{value}</div>
                </div>'''

        hdr = f'''
        <div style="padding: 1.75rem; background: linear-gradient(135deg, #eef2ff 0%, #ffffff 100%); border-radius: 12px; border: 2px solid #6366f1; margin-bottom: 1.5rem;">
            <h3 style="margin: 0 0 0.5rem 0; color: #312e81; font-size: 1.35rem;">🎯 System Health Assessment (Enhanced)</h3>
            <p style="margin: 0; color: #475569; font-size: 0.95rem; line-height: 1.55;">{subtitle}</p>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-top: 1.25rem;">
                {badge_cell("Stability", esc(str(badges.get("stability", "—"))))}
                {badge_cell("Variability", esc(str(badges.get("variability", "—"))))}
                {badge_cell("Overall behavior", esc(str(badges.get("overall", "—"))))}
                {badge_cell("Variability index (P99/P50)", esc(str(badges.get("vi", "—"))))}
            </div>
            <p style="margin: 1rem 0 0 0; font-size: 0.9rem; color: #334155;">
                Errors {badges.get("errors_pct", 0):.3f}% · TP {badges.get("tp_rps", 0):.2f} req/s
            </p>
        </div>'''

        parts = [hdr]
        for sec in assessment.get("sections") or []:
            n = sec.get("n", "")
            title = esc(str(sec.get("title") or ""))
            body = str(sec.get("body") or "")
            u = sec.get("understanding")
            imp = sec.get("impact")
            res = sec.get("resolution")
            block = (
                f'<div style="margin-bottom: 1.15rem; padding: 1rem 1.1rem; background: #f8fafc; border-radius: 8px; border-left: 4px solid #6366f1;">'
                f'<strong style="color: #1e293b;">{n}. {title}</strong>'
            )
            if sec.get("embed_recommendations"):
                rec = assessment.get("recommendations") or {}
                imm = "".join(f"<li>{esc(x)}</li>" for x in rec.get("immediate") or [])
                med = "".join(f"<li>{esc(x)}</li>" for x in rec.get("medium") or [])
                lon = "".join(f"<li>{esc(x)}</li>" for x in rec.get("long") or [])
                block += (
                    f'<div style="margin: 0.5rem 0 0 0; color: #334155;">'
                    f'<p style="font-weight:600;margin:0.5rem 0 0.25rem 0;">Immediate</p><ul class="inner-list" style="margin-top:0.2rem;">{imm}</ul>'
                    f'<p style="font-weight:600;margin:0.75rem 0 0.25rem 0;">Medium-term</p><ul class="inner-list" style="margin-top:0.2rem;">{med}</ul>'
                    f'<p style="font-weight:600;margin:0.75rem 0 0.25rem 0;">Long-term</p><ul class="inner-list" style="margin-top:0.2rem;">{lon}</ul>'
                    f"</div>"
                )
            elif sec.get("embed_bottleneck_table"):
                bmap = assessment.get("bottleneck_mapping") or []
                if bmap:
                    rows = ""
                    for b in bmap:
                        rows += (
                            f"<tr><td>{esc(b.get('symptom', ''))}</td><td>{esc(b.get('evidence', ''))}</td>"
                            f"<td>{esc(b.get('root_cause', ''))}</td><td>{esc(b.get('recommendation', ''))}</td></tr>"
                        )
                    block += (
                        f'<div style="overflow-x:auto; margin-top:0.5rem;"><table class="endpoint-table" style="font-size:0.85rem;">'
                        f'<thead><tr><th>Symptom</th><th>Evidence</th><th>Root cause (hypothesis)</th><th>Recommendation</th></tr></thead>'
                        f"<tbody>{rows}</tbody></table></div>"
                    )
                else:
                    block += (
                        '<p style="margin: 0.5rem 0 0 0; color: #64748b; font-size: 0.9rem;">'
                        "No bottleneck mapping rows for this run (distribution did not meet pattern thresholds).</p>"
                    )
            elif body:
                block += (
                    f'<p style="margin: 0.4rem 0 0 0; color: #334155; line-height: 1.65;">{esc(body)}</p>'
                )
            if u:
                block += (
                    f'<p style="margin: 0.65rem 0 0 0; font-size: 0.9rem; line-height: 1.6;">'
                    f'<span style="color:#4338ca;font-weight:600;">What this means — </span>'
                    f'<span style="color:#475569;">{esc(str(u))}</span></p>'
                )
            if imp:
                block += (
                    f'<p style="margin: 0.45rem 0 0 0; font-size: 0.9rem; line-height: 1.6;">'
                    f'<span style="color:#b45309;font-weight:600;">Impact — </span>'
                    f'<span style="color:#475569;">{esc(str(imp))}</span></p>'
                )
            if res:
                block += (
                    f'<p style="margin: 0.45rem 0 0 0; font-size: 0.9rem; line-height: 1.6;">'
                    f'<span style="color:#047857;font-weight:600;">How to address — </span>'
                    f'<span style="color:#475569;">{esc(str(res))}</span></p>'
                )
            block += "</div>"
            parts.append(block)

        ba = assessment.get("business_answers") or {}
        ba_html = HTMLReportGenerator._generate_business_answers_html(ba, show_outer_title=False)
        if ba_html.strip():
            parts.append(
                '<div style="margin-top: 1.25rem;">'
                '<h4 style="margin: 0 0 0.75rem 0; color: #1e293b; font-size: 1.05rem; font-weight: 600;">'
                "Quick diagnostic (distribution-based)</h4>"
                f"{ba_html}"
                "</div>"
            )

        slow = assessment.get("api_slowest") or []
        if slow:
            rows = ""
            for r in slow:
                rows += (
                    f"<tr><td>{esc(str(r.get('label', '')))}</td>"
                    f"<td style='text-align:right'>{r.get('avg_ms', 0):.0f}</td>"
                    f"<td style='text-align:right'>{r.get('p95_ms', 0):.0f}</td>"
                    f"<td style='text-align:right'>{r.get('p99_ms', 0):.0f}</td>"
                    f"<td style='text-align:right'>{r.get('error_pct', 0):.2f}%</td></tr>"
                )
            parts.append(
                f'''<h4 style="margin: 1.25rem 0 0.5rem 0;">Top slowest by P95 (ms)</h4>
                <div style="overflow-x:auto;"><table class="endpoint-table" style="font-size:0.88rem;">
                <thead><tr><th>Label</th><th>Avg (ms)</th><th>P95</th><th>P99</th><th>Error %</th></tr></thead>
                <tbody>{rows}</tbody></table></div>'''
            )

        uns = assessment.get("api_unstable") or []
        if uns:
            rows = ""
            for r in uns:
                rows += (
                    f"<tr><td>{esc(str(r.get('label', '')))}</td>"
                    f"<td style='text-align:right'>{r.get('error_pct', 0):.2f}%</td>"
                    f"<td style='text-align:right'>{r.get('p95_avg', 0):.2f}</td>"
                    f"<td style='text-align:right'>{r.get('samples', 0)}</td></tr>"
                )
            parts.append(
                f'''<h4 style="margin: 1.25rem 0 0.5rem 0;">Unstable labels (error % / P95÷Avg)</h4>
                <div style="overflow-x:auto;"><table class="endpoint-table" style="font-size:0.88rem;">
                <thead><tr><th>Label</th><th>Error %</th><th>P95/Avg</th><th>Samples</th></tr></thead>
                <tbody>{rows}</tbody></table></div>'''
            )

        inner = "\n".join(parts)
        return f'<div style="padding: 1.5rem; background: var(--card-background); border-radius: 10px; border: 1px solid var(--border-color);">{inner}</div>'

    @staticmethod
    def _analyze_system_performance(time_series_data: List[dict]) -> dict:
        """Correlate response time, pass/fail throughput, vusers, and interval error % for one narrative."""
        if not time_series_data or len(time_series_data) < 2:
            return {
                "performance_status": "Insufficient Data",
                "insights": ["Not enough data points for analysis"],
                "unified_summary": "Need at least two time buckets to assess behaviour under load.",
                "correlations": {},
                "recommendations": [],
                "statistics": {},
            }
        
        # Extract metrics
        response_times = [d['avg_response_time'] for d in time_series_data]
        vusers = [d['vusers'] for d in time_series_data]
        throughput = [d['throughput'] for d in time_series_data]
        tput_pass = [float(d.get("throughput_pass", d.get("throughput", 0)) or 0) for d in time_series_data]
        tput_fail = [float(d.get("throughput_fail", 0) or 0) for d in time_series_data]
        err_interval = []
        for d in time_series_data:
            er = d.get("error_rate_pct")
            if er is None:
                p, f = int(d.get("pass_count", 0)), int(d.get("fail_count", 0))
                er = (100.0 * f / (p + f)) if (p + f) else 0.0
            err_interval.append(float(er))
        
        # Calculate statistics
        avg_response = sum(response_times) / len(response_times) if response_times else 0
        max_response = max(response_times) if response_times else 0
        min_response = min(response_times) if response_times else 0
        response_variance = sum((x - avg_response) ** 2 for x in response_times) / len(response_times) if response_times else 0
        response_stability = "Stable" if response_variance < (avg_response * 0.2) ** 2 else "Variable"
        
        avg_throughput = sum(throughput) / len(throughput) if throughput else 0
        max_throughput = max(throughput) if throughput else 0
        min_throughput = min(throughput) if throughput else 0
        throughput_variance = sum((x - avg_throughput) ** 2 for x in throughput) / len(throughput) if throughput else 0
        throughput_stability = "Stable" if throughput_variance < (avg_throughput * 0.2) ** 2 else "Variable"
        
        avg_vusers = sum(vusers) / len(vusers) if vusers else 0
        max_vusers = max(vusers) if vusers else 0
        avg_tput_pass = sum(tput_pass) / len(tput_pass) if tput_pass else 0.0
        avg_tput_fail = sum(tput_fail) / len(tput_fail) if tput_fail else 0.0
        avg_err_int = sum(err_interval) / len(err_interval) if err_interval else 0.0
        
        def calculate_correlation(x, y):
            if len(x) != len(y) or len(x) < 2:
                return 0
            n = len(x)
            sum_x = sum(x)
            sum_y = sum(y)
            sum_xy = sum(x[i] * y[i] for i in range(n))
            sum_x2 = sum(x[i] ** 2 for i in range(n))
            sum_y2 = sum(y[i] ** 2 for i in range(n))
            numerator = n * sum_xy - sum_x * sum_y
            denominator = ((n * sum_x2 - sum_x ** 2) * (n * sum_y2 - sum_y ** 2)) ** 0.5
            return numerator / denominator if denominator != 0 else 0
        
        corr_response_vusers = calculate_correlation(vusers, response_times)
        corr_response_throughput = calculate_correlation(throughput, response_times)
        corr_vusers_throughput = calculate_correlation(vusers, throughput)
        corr_vusers_err = calculate_correlation(vusers, err_interval)
        corr_response_err = calculate_correlation(response_times, err_interval)
        corr_vusers_tput_fail = calculate_correlation(vusers, tput_fail)
        
        # Analyze trends
        response_trend = "Increasing" if response_times[-1] > response_times[0] * 1.1 else "Decreasing" if response_times[-1] < response_times[0] * 0.9 else "Stable"
        throughput_trend = "Increasing" if throughput[-1] > throughput[0] * 1.1 else "Decreasing" if throughput[-1] < throughput[0] * 0.9 else "Stable"
        
        # Generate insights
        insights = []
        performance_status = "Good"
        recommendations = []
        
        # Responsiveness (avg RT) + capacity (throughput) + reliability (error / fail tput) together
        if avg_response < 2.0:
            insights.append(
                f"✅ <strong>Responsiveness:</strong> Mean interval response time {avg_response:.2f}s (favourable). "
                f"Pass throughput {avg_tput_pass:.1f} req/s, fail throughput {avg_tput_fail:.1f} req/s, mean interval error {avg_err_int:.1f}%."
            )
        elif avg_response < 5.0:
            insights.append(
                f"⚠️ <strong>Responsiveness:</strong> Mean interval response {avg_response:.2f}s (elevated). "
                f"Pass {avg_tput_pass:.1f} req/s, fail {avg_tput_fail:.1f} req/s, mean interval error {avg_err_int:.1f}%."
            )
            performance_status = "Moderate"
        else:
            insights.append(
                f"❌ <strong>Responsiveness:</strong> Mean interval response {avg_response:.2f}s (poor). "
                f"Pass {avg_tput_pass:.1f} req/s, fail {avg_tput_fail:.1f} req/s, mean interval error {avg_err_int:.1f}%."
            )
            performance_status = "Poor"
        
        if response_stability == "Stable":
            insights.append("✅ <strong>Stability of latency:</strong> Intervals show relatively consistent response times (low variance around the mean).")
        else:
            insights.append(
                f"⚠️ <strong>Stability of latency:</strong> High variance in interval response times (var={response_variance:.2f})—jitter often coincides with saturation or error bursts."
            )
            if performance_status == "Good":
                performance_status = "Moderate"
        
        if avg_tput_pass > 0 and avg_tput_fail / max(avg_tput_pass, 0.01) < 0.05 and avg_err_int < 2.0:
            insights.append("✅ <strong>Reliability:</strong> Fail throughput and interval errors stay low—good sign for dependability at this load profile.")
        elif avg_tput_fail > 1 or avg_err_int > 5:
            insights.append(
                f"❌ <strong>Reliability:</strong> Substantial fail-side load (fail tput {avg_tput_fail:.1f} req/s, mean interval error {avg_err_int:.1f}%). "
                "Investigate before treating latency in isolation."
            )
            if performance_status != "Poor":
                performance_status = "Moderate"
        elif avg_err_int > 1:
            insights.append(
                f"⚠️ <strong>Reliability:</strong> Mean interval error {avg_err_int:.1f}% with fail tput {avg_tput_fail:.1f} req/s—errors may be driving perceived slowness."
            )
        
        if avg_throughput < 20 and max_vusers > 5:
            insights.append("⚠️ <strong>Scalability signal:</strong> Low total req/s for the active thread count—check whether the tool or app is throttling, queuing, or error-limited.")
            if performance_status == "Good":
                performance_status = "Moderate"
        
        # Correlation analysis
        if corr_response_vusers > 0.7:
            insights.append(
                f"⚠️ <strong>Load vs latency:</strong> Strong positive correlation of response time with vusers (r≈{corr_response_vusers:.2f})—responsiveness tightens with concurrency (capacity headroom may be low)."
            )
            recommendations.append("Review scaling, pools, and saturation before adding load.")
            if performance_status == "Good":
                performance_status = "Moderate"
        elif corr_response_vusers < -0.2:
            insights.append(
                f"ℹ️ <strong>Load vs latency:</strong> r≈{corr_response_vusers:.2f} (latency falls as vusers rise in-window)—often ramp/warm-up; interpret with pass/fail tput, not vusers alone."
            )
        else:
            insights.append(
                f"ℹ️ <strong>Load vs latency:</strong> r≈{corr_response_vusers:.2f} between vusers and mean interval response—moderate coupling is normal for ramp tests."
            )
        
        if corr_vusers_tput_fail > 0.5 and avg_tput_fail > 0.1:
            insights.append(
                f"❌ <strong>Errors follow load:</strong> Fail throughput rises with vusers (r≈{corr_vusers_tput_fail:.2f})—reliability stress under parallel users."
            )
            performance_status = "Moderate" if performance_status == "Good" else performance_status
        if corr_vusers_err > 0.4:
            insights.append(
                f"❌ <strong>Interval error % vs vusers:</strong> r≈{corr_vusers_err:.2f}—failures become more common as concurrency increases (not independent of 'speed')."
            )
            if performance_status == "Good":
                performance_status = "Moderate"
        
        if abs(corr_response_err) > 0.4:
            insights.append(
                f"ℹ️ <strong>Latency vs error mix:</strong> r≈{corr_response_err:.2f} between interval error % and response time—timeouts/failures may inflate or distort mean latency; triage errors first."
            )
        
        if corr_vusers_throughput > 0.7:
            insights.append(
                f"✅ <strong>Scalability (goodput):</strong> Total req/s tracks vusers (r≈{corr_vusers_throughput:.2f})—the generator and system move load together; confirm pass tput, not only nominal r/s."
            )
        elif corr_vusers_throughput < 0.3 and max_vusers > 10:
            insights.append(
                f"⚠️ <strong>Scalability:</strong> Total throughput weakly follows vusers (r≈{corr_vusers_throughput:.2f})—bottlenecks, client limits, or errors may be capping work completed."
            )
            recommendations.append("Check client thread limits, think-time, and server-side throttling; correlate with fail tput.")
        
        # Trend analysis
        if response_trend == "Increasing" and max_response > avg_response * 1.5:
            insights.append(f"⚠️ <strong>Degrading Performance:</strong> Response time shows an increasing trend, with peak values reaching {max_response:.2f}s. System performance is degrading over time.")
            recommendations.append("Investigate memory leaks, resource exhaustion, or database connection pool issues.")
            if performance_status != "Poor":
                performance_status = "Moderate"
        
        if throughput_trend == "Decreasing":
            insights.append(
                "❌ <strong>Trend:</strong> Total req/s drifts down over the run—pair with pass/fail tput and error % to tell exhaustion vs failing requests."
            )
            recommendations.append("Check for resource leaks, pool limits, or rising failure rate.")
            performance_status = "Poor"
        
        if performance_status == "Good":
            insights.append(
                "✅ <strong>Synthesis:</strong> Interval metrics and correlations look healthy for responsiveness, scalability, and low error share—continue monitoring in production-like conditions."
            )
        elif performance_status == "Moderate":
            insights.append(
                "⚠️ <strong>Synthesis:</strong> At least one of responsiveness, goodput (pass tput), or interval reliability is strained—triage errors and saturation together."
            )
        else:
            insights.append(
                "❌ <strong>Synthesis:</strong> Significant issues across latency, throughput quality, and/or error behaviour—treat as a system-level load/reliability problem."
            )
        
        unified_summary = (
            f"Over {len(time_series_data)} time buckets: mean interval response {avg_response:.2f}s; "
            f"mean total {avg_throughput:.1f} req/s (pass {avg_tput_pass:.1f}, fail {avg_tput_fail:.1f}); "
            f"mean vusers {avg_vusers:.0f} (max {max_vusers:.0f}); mean interval error {avg_err_int:.1f}%. "
            "A responsive system at scale shows pass throughput growing with vusers, low fail throughput, and stable interval errors; interpret RT together with these signals."
        )
        
        return {
            "performance_status": performance_status,
            "insights": insights,
            "unified_summary": unified_summary,
            "correlations": {
                "response_vusers": round(corr_response_vusers, 3),
                "response_throughput": round(corr_response_throughput, 3),
                "vusers_throughput": round(corr_vusers_throughput, 3),
                "vusers_error_rate": round(corr_vusers_err, 3),
                "response_error_rate": round(corr_response_err, 3),
                "vusers_fail_throughput": round(corr_vusers_tput_fail, 3),
            },
            "statistics": {
                "avg_response": round(avg_response, 2),
                "max_response": round(max_response, 2),
                "avg_throughput": round(avg_throughput, 2),
                "avg_throughput_pass": round(avg_tput_pass, 2),
                "avg_throughput_fail": round(avg_tput_fail, 2),
                "max_throughput": round(max_throughput, 2),
                "avg_vusers": round(avg_vusers, 1),
                "max_vusers": round(max_vusers, 1),
                "avg_error_rate_interval": round(avg_err_int, 2),
            },
            "recommendations": recommendations,
        }
    
    @staticmethod
    def _generate_system_behaviour_graph(
        time_series_data: List[dict], progress_callback=None
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate Overall System Behaviour graph with dual Y-axes. Returns (html, graph_analysis dict)."""
        if not time_series_data:
            return (
                """
        <div class="section" id="section-system-behaviour">
            <h2>📈 Overall System Behaviour</h2>
            <p><em>Time-series data not available for this test.</em></p>
        </div>""",
                {},
            )
        
        def update_progress(percent: int, message: str):
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except:
                    pass
        
        # GraphAnalyzer only needs a coarse series (same as chart: ~50–60 points).
        # Cap to 60 to keep analysis fast and avoid pathological CPU on long tests.
        original_count = len(time_series_data)
        max_points_analysis = 60
        if original_count > max_points_analysis:
            sample_rate = max(1, int(np.ceil(original_count / max_points_analysis)))
            sampled_data = time_series_data[::sample_rate][:max_points_analysis]
            print(
                f"  Sampling time_series for GraphAnalyzer: {original_count:,} -> {len(sampled_data):,} points"
            )
        else:
            sampled_data = time_series_data
        
        # Analyze performance (basic correlation analysis)
        update_progress(20, "Analyzing system performance...")
        analysis = HTMLReportGenerator._analyze_system_performance(time_series_data)
        
        # Advanced graph pattern analysis (use sampled data for speed)
        # Add timeout protection - use threading with timeout
        update_progress(40, f"Running GraphAnalyzer on {len(sampled_data):,} data points...")
        print(f"  Running GraphAnalyzer on {len(sampled_data):,} data points...")
        
        graph_analysis = None
        try:
            from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
            
            # Run GraphAnalyzer in a thread with 30 second timeout (increased from 20)
            # If it times out, we'll use a simplified analysis
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(GraphAnalyzer.analyze_graph_patterns, sampled_data)
                try:
                    graph_analysis = future.result(timeout=30)
                    print(f"  ✓ GraphAnalyzer completed successfully")
                    
                    # Ensure throughput_distribution_analysis exists, if not create empty one
                    if 'throughput_distribution_analysis' not in graph_analysis:
                        print(f"  ⚠️ Throughput distribution analysis missing, creating empty one")
                        graph_analysis['throughput_distribution_analysis'] = {
                            "distribution_type": "unknown",
                            "interpretation": "Throughput analysis not available.",
                            "unified_understanding": "Throughput distribution analysis could not be completed.",
                            "statistics": {}
                        }
                    
                except FutureTimeoutError:
                    print(f"  ⚠️ GraphAnalyzer timed out after 30 seconds, using fallback")
                    future.cancel()
                    graph_analysis = {
                        "analysis": "Graph analysis timed out - using simplified analysis.",
                        "test_type": "Unknown",
                        "disturbances": [],
                        "stability": "Unknown",
                        "capacity_assessment": "Unknown",
                        "distribution_analysis": {
                            "distribution_type": "unknown",
                            "unified_understanding": "Analysis timed out - insufficient data for comprehensive analysis.",
                            "statistics": {}
                        },
                        "throughput_distribution_analysis": {
                            "distribution_type": "unknown",
                            "unified_understanding": "Throughput analysis timed out.",
                            "statistics": {}
                        }
                    }
        except Exception as e:
            print(f"  ⚠️ GraphAnalyzer failed: {e}, using fallback")
            import traceback
            traceback.print_exc()
            # Use fallback analysis with both distribution analyses
            graph_analysis = {
                "analysis": f"Graph analysis unavailable: {str(e)}",
                "test_type": "Unknown",
                "disturbances": [],
                "stability": "Unknown",
                "capacity_assessment": "Unknown",
                "distribution_analysis": {
                    "distribution_type": "unknown",
                    "unified_understanding": f"Response time analysis unavailable: {str(e)}",
                    "statistics": {}
                },
                "throughput_distribution_analysis": {
                    "distribution_type": "unknown",
                    "unified_understanding": f"Throughput analysis unavailable: {str(e)}",
                    "statistics": {}
                }
            }
        
        if not isinstance(graph_analysis, dict):
            graph_analysis = {}
        graph_analysis["system_correlation"] = analysis
        
        update_progress(80, "Preparing graph data (~55 point chart from bucketed series)...")
        
        chart_data = HTMLReportGenerator._downsample_time_series_for_system_behaviour_chart(time_series_data, 55)
        time_labels = [HTMLReportGenerator._format_time_hhmmss(d["time"]) for d in chart_data]
        avg_response_times = [d["avg_response_time"] for d in chart_data]
        vusers = [d["vusers"] for d in chart_data]
        tput_pass = [float(d.get("throughput_pass", 0) or 0) for d in chart_data]
        tput_fail = [float(d.get("throughput_fail", 0) or 0) for d in chart_data]
        
        time_labels_json = json.dumps(time_labels)
        avg_response_times_json = json.dumps(avg_response_times)
        vusers_json = json.dumps(vusers)
        tput_pass_json = json.dumps(tput_pass)
        tput_fail_json = json.dumps(tput_fail)
        
        # Generate graph data table HTML
        table_html = HTMLReportGenerator._generate_graph_data_table(time_series_data)
        
        return f'''
        <div class="section" id="section-system-behaviour">
            <h2>📈 Overall System Behaviour</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                <strong>Left axis:</strong> average response time (successful samples) per interval.
                <strong>Right (inner):</strong> pass throughput and fail throughput (requests per second) on load.
                <strong>Right (outer):</strong> virtual users. The line chart uses about 50–55 downsampled points (averages of adjacent table buckets);
                the table lists full bucket-level (typically 1 minute) data.
            </p>
            
            <!-- Graph and Data Table Side by Side (50/50) -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
                <!-- Left: Graph (50%) -->
                <div class="chart-container" style="height: 500px;">
                    <canvas id="systemBehaviourChart"></canvas>
                </div>
                
                <!-- Right: Graph Data Table (50%) -->
                <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                    <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                    {table_html}
                </div>
            </div>
            
            <div style="margin-top: 2rem; padding: 1.5rem; background: var(--background-light); border-radius: 8px;">
                <h3 style="color: var(--primary-color); margin-bottom: 1rem;">📖 Graph Understanding & Performance Analysis</h3>
                
                <!-- Comprehensive Graph Analysis with 50/50 layout -->
                {HTMLReportGenerator._generate_graph_analysis_html(graph_analysis, time_series_data)}
            </div>
        </div>
        
        <script>
        document.addEventListener('DOMContentLoaded', function() {{
            const ctx = document.getElementById('systemBehaviourChart');
            if (!ctx) return;
            
            const timeLabels = {time_labels_json};
            const avgResponseTimes = {avg_response_times_json};
            const vusers = {vusers_json};
            const tputPass = {tput_pass_json};
            const tputFail = {tput_fail_json};
            
            const maxResponse = Math.max(...avgResponseTimes, 0.01);
            const maxTput = Math.max(1, ...tputPass, ...tputFail);
            const maxVu = Math.max(1, ...vusers);
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: timeLabels,
                    datasets: [{{
                        label: 'Avg response time (s, passed samples)',
                        data: avgResponseTimes,
                        borderColor: 'rgba(37, 99, 235, 1)',
                        backgroundColor: 'rgba(37, 99, 235, 0.08)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        yAxisID: 'y',
                        pointRadius: 2
                    }}, {{
                        label: 'Pass throughput (req/s)',
                        data: tputPass,
                        borderColor: 'rgba(16, 185, 129, 1)',
                        backgroundColor: 'rgba(16, 185, 129, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        yAxisID: 'y1',
                        pointRadius: 2
                    }}, {{
                        label: 'Fail throughput (req/s)',
                        data: tputFail,
                        borderColor: 'rgba(220, 38, 38, 1)',
                        backgroundColor: 'rgba(220, 38, 38, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        yAxisID: 'y1',
                        pointRadius: 2,
                        borderDash: [4, 4]
                    }}, {{
                        label: 'VUsers (threads)',
                        data: vusers,
                        borderColor: 'rgba(124, 58, 237, 1)',
                        backgroundColor: 'rgba(124, 58, 237, 0.05)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.35,
                        yAxisID: 'y2',
                        pointRadius: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    interaction: {{ mode: 'index', intersect: false }},
                    plugins: {{
                        datalabels: {{ display: false }},
                        legend: {{
                            display: true,
                            position: 'top',
                            labels: {{ font: {{ size: 11 }}, usePointStyle: true, padding: 10 }}
                        }},
                        title: {{
                            display: true,
                            text: 'Response time & throughput (pass/fail) vs load (~55 averaged points)',
                            font: {{ size: 16, weight: 'bold' }},
                            padding: {{ bottom: 12 }}
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    const lab = context.dataset.label || '';
                                    if (lab.indexOf('response') >= 0 || lab.indexOf('Response') >= 0)
                                        return lab + ': ' + context.parsed.y.toFixed(2) + 's';
                                    if (lab.indexOf('VUsers') >= 0)
                                        return lab + ': ' + Math.round(context.parsed.y);
                                    return lab + ': ' + context.parsed.y.toFixed(2) + ' req/s';
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            title: {{ display: true, text: 'Elapsed time from test start (seconds)', font: {{ size: 13, weight: 'bold' }} }},
                            grid: {{ color: 'rgba(0, 0, 0, 0.05)' }}
                        }},
                        y: {{
                            type: 'linear',
                            position: 'left',
                            title: {{ display: true, text: 'Avg response time (s)', font: {{ size: 13, weight: 'bold' }} }},
                            beginAtZero: true,
                            suggestedMax: maxResponse * 1.15,
                            grid: {{ color: 'rgba(0, 0, 0, 0.06)' }}
                        }},
                        y1: {{
                            type: 'linear',
                            position: 'right',
                            title: {{ display: true, text: 'Throughput pass / fail (req/s)', font: {{ size: 13, weight: 'bold' }} }},
                            beginAtZero: true,
                            suggestedMax: maxTput * 1.15,
                            grid: {{ drawOnChartArea: false }}
                        }},
                        y2: {{
                            type: 'linear',
                            position: 'right',
                            title: {{ display: true, text: 'Virtual users', font: {{ size: 13, weight: 'bold' }} }},
                            beginAtZero: true,
                            suggestedMax: maxVu * 1.1,
                            offset: true,
                            grid: {{ drawOnChartArea: false }}
                        }}
                    }}
                }}
            }});
        }});
        </script>''', graph_analysis
    
    @staticmethod
    def _generate_issues(issues: List[dict]) -> str:
        """Generate issues section in tabular format (includes all issues: critical, moderate, and minor)"""
        if not issues:
            return '''
        <div class="section" id="section-issues">
            <h2>⚠️ Issues</h2>
            <div class="alert alert-success">
                <strong>✅ NO ISSUES IDENTIFIED:</strong> The system is performing well with no concerns identified.
            </div>
        </div>'''
        
        # Consolidate similar issues
        def normalize_issue_title(title: str) -> str:
            """Normalize issue titles to group similar issues together"""
            title_lower = title.lower()
            import re
            # Group slow transactions by response time ranges
            if "slow transaction" in title_lower or "very slow transaction" in title_lower:
                # Extract response time from title (format: "Slow Transaction: NAME - X.Xs")
                # Look for pattern like "16.0s" or "18.0s" in the title
                time_match = re.search(r'(\d+\.?\d*)\s*s', title)
                if time_match:
                    response_time = float(time_match.group(1))
                    # Group into ranges: 0-5s, 5-10s, 10-15s, 15-20s, 20-25s, 25-30s, 30+
                    if response_time < 5:
                        return "Slow Transaction Between 0s-5s"
                    elif response_time < 10:
                        return "Slow Transaction Between 5s-10s"
                    elif response_time < 15:
                        return "Slow Transaction Between 10s-15s"
                    elif response_time < 20:
                        return "Slow Transaction Between 15s-20s"
                    elif response_time < 25:
                        return "Slow Transaction Between 20s-25s"
                    elif response_time < 30:
                        return "Slow Transaction Between 25s-30s"
                    else:
                        return "Slow Transaction Above 30s"
                # Fallback: if no time found, group all together
                return "Slow Transaction"
            # Group high error rate issues by error rate ranges
            elif "high error rate" in title_lower or "elevated error rate" in title_lower:
                # Extract error rate from title (format: "High Error Rate for NAME - X.X%")
                # Look for pattern like "83.4%" in the title
                error_rate_match = re.search(r'(\d+\.?\d*)\s*%', title)
                if error_rate_match:
                    error_rate = float(error_rate_match.group(1))
                    # Group into ranges: 0-20%, 20-50%, 50-80%, 80-90%, 90-100%
                    if error_rate < 20:
                        return "High Error Rate 0-20%"
                    elif error_rate < 50:
                        return "High Error Rate 20-50%"
                    elif error_rate < 80:
                        return "High Error Rate 50-80%"
                    elif error_rate < 90:
                        return "High Error Rate 80-90%"
                    else:
                        return "High Error Rate 90-100%"
                # Fallback: if no percentage found, group all together
                return "High Error Rate"
            return title
        
        # Group issues by normalized title
        consolidated_issues = {}
        for issue in issues:
            normalized_title = normalize_issue_title(issue.get('title', 'Unknown Issue'))
            if normalized_title not in consolidated_issues:
                consolidated_issues[normalized_title] = {
                    'title': normalized_title,
                    'issues': [],
                    'priority': issue.get('priority', 'UNKNOWN'),
                    'impact': issue.get('impact', 'N/A'),
                    'recommendation': issue.get('recommendation', issue.get('fix', 'Review and address the issue')),
                    'business_benefit': issue.get('business_benefit', 'Improved system reliability and user experience')
                }
            consolidated_issues[normalized_title]['issues'].append(issue)
        
        # Determine highest priority for consolidated issue
        priority_order = {'P0': 0, 'P1': 1, 'P2': 2, 'P3': 3}
        for normalized_title, consolidated in consolidated_issues.items():
            priorities = [i.get('priority', 'UNKNOWN') for i in consolidated['issues']]
            # Get highest priority (lowest number)
            highest_priority = min(priorities, key=lambda p: priority_order.get(p[:2], 999))
            consolidated['priority'] = highest_priority
        
        # Categorize consolidated issues by priority
        critical_issues = [c for c in consolidated_issues.values() if c['priority'].startswith('P0')]
        high_issues = [c for c in consolidated_issues.values() if c['priority'].startswith('P1')]
        moderate_issues = [c for c in consolidated_issues.values() if c['priority'].startswith('P2')]
        other_issues = [c for c in consolidated_issues.values() if not c['priority'].startswith(('P0', 'P1', 'P2'))]
        
        # Generate table rows with priority-based styling
        table_rows = ""
        for consolidated in consolidated_issues.values():
            title = consolidated['title']
            impact = consolidated['impact']
            priority = consolidated['priority']
            recommendation = consolidated['recommendation']
            business_benefit = consolidated['business_benefit']
            occurrences = len(consolidated['issues'])
            
            # Build example text showing occurrences
            if occurrences == 1:
                example_text = consolidated['issues'][0].get('example', consolidated['issues'][0].get('affected', 'N/A'))
            else:
                import re
                # For slow transactions, extract transaction name and time from title
                if "Slow Transaction" in title or "Very Slow Transaction" in title:
                    # Extract transaction details from titles (format: "Slow Transaction: NAME - X.Xs")
                    transaction_examples = []
                    for issue in consolidated['issues']:
                        issue_title = issue.get('title', '')
                        # Extract transaction name and time (e.g., "TC06_CE_08_Logout - 16.0s")
                        if ":" in issue_title and "-" in issue_title:
                            # Get part after colon and before end
                            transaction_part = issue_title.split(":", 1)[1].strip()
                            transaction_examples.append(transaction_part)
                        else:
                            # Fallback to example or affected
                            transaction_examples.append(issue.get('example', issue.get('affected', '')))
                    
                    # Remove empty items and join
                    transaction_examples = [t for t in transaction_examples if t]
                    if transaction_examples:
                        example_text = ", ".join(transaction_examples)
                    else:
                        example_text = f"Occurred {occurrences} time(s)"
                # For high error rate issues, extract transaction name and error rate, sort by worst first
                elif "High Error Rate" in title or "Elevated Error Rate" in title:
                    transaction_examples_with_rate = []
                    for issue in consolidated['issues']:
                        issue_title = issue.get('title', '')
                        # Extract transaction name and error rate (e.g., "TC03_AC_02_R03_Login_UTILITY.ROUTINE_Menu-2 - 83.4%")
                        if "for" in issue_title and "-" in issue_title:
                            # Format: "High Error Rate for NAME - X.X%"
                            parts = issue_title.split("for", 1)
                            if len(parts) > 1:
                                transaction_part = parts[1].strip()
                                transaction_examples_with_rate.append((transaction_part, issue_title))
                        elif ":" in issue_title and "-" in issue_title:
                            # Alternative format: "High Error Rate: NAME - X.X%"
                            transaction_part = issue_title.split(":", 1)[1].strip()
                            transaction_examples_with_rate.append((transaction_part, issue_title))
                        else:
                            # Fallback
                            transaction_examples_with_rate.append((issue.get('example', issue.get('affected', '')), issue_title))
                    
                    # Sort by error rate (extract percentage and sort descending - worst first)
                    def extract_error_rate(item):
                        title_text = item[1] if isinstance(item, tuple) else item
                        error_match = re.search(r'(\d+\.?\d*)\s*%', title_text)
                        return float(error_match.group(1)) if error_match else 0.0
                    
                    transaction_examples_with_rate.sort(key=extract_error_rate, reverse=True)
                    
                    # Take only the transaction part (first element of tuple) and limit to 5-6 worst
                    transaction_examples = [item[0] if isinstance(item, tuple) else item for item in transaction_examples_with_rate[:6]]
                    
                    # Remove empty items and join
                    transaction_examples = [t for t in transaction_examples if t]
                    if transaction_examples:
                        example_text = ", ".join(transaction_examples)
                    else:
                        example_text = f"Occurred {occurrences} time(s)"
                else:
                    # For other issues, show count and list of affected items
                    affected_items = [i.get('affected', i.get('example', '')) for i in consolidated['issues']]
                    unique_items = list(dict.fromkeys([item for item in affected_items if item]))  # Preserve order, remove duplicates
                    if unique_items:
                        if len(unique_items) <= 3:
                            example_text = f"Occurred {occurrences} time(s): {', '.join(unique_items)}"
                        else:
                            example_text = f"Occurred {occurrences} time(s): {', '.join(unique_items[:3])} (+{len(unique_items)-3} more)"
                    else:
                        example_text = f"Occurred {occurrences} time(s)"
            
            # Color code based on priority
            if priority.startswith('P0'):
                priority_color = '#dc2626'  # Red for critical
            elif priority.startswith('P1'):
                priority_color = '#ea580c'  # Orange for high
            elif priority.startswith('P2'):
                priority_color = '#ca8a04'  # Yellow for moderate
            else:
                priority_color = '#6b7280'  # Gray for other
            
            table_rows += f'''
            <tr>
                <td style="padding: 1rem; font-weight: 600; color: var(--text-primary); word-wrap: break-word; max-width: 200px;">{title}</td>
                <td style="padding: 1rem; color: var(--text-secondary); word-wrap: break-word; max-width: 250px;">{example_text}</td>
                <td style="padding: 1rem; color: var(--text-secondary); word-wrap: break-word; max-width: 200px;">{impact}</td>
                <td style="padding: 1rem; color: var(--text-secondary); word-wrap: break-word; max-width: 250px;">{recommendation}</td>
                <td style="padding: 1rem; color: var(--text-secondary); word-wrap: break-word; max-width: 200px;">{business_benefit}</td>
                <td style="padding: 1rem; color: {priority_color}; font-weight: 600;">{priority}</td>
            </tr>'''
        
        # Generate alert message based on issue severity
        total_original_issues = len(issues)
        total_consolidated = len(consolidated_issues)
        if critical_issues:
            alert_class = "alert-danger"
            alert_text = f"<strong>IMMEDIATE ACTION REQUIRED:</strong> {len(critical_issues)} critical issue{'s' if len(critical_issues) > 1 else ''} identified. "
        elif high_issues:
            alert_class = "alert-warning"
            alert_text = f"<strong>HIGH PRIORITY:</strong> {len(high_issues)} high priority issue{'s' if len(high_issues) > 1 else ''} identified. "
        else:
            alert_class = "alert-info"
            alert_text = f"<strong>ISSUES IDENTIFIED:</strong> {total_consolidated} issue{'s' if total_consolidated > 1 else ''} identified for review. "
        
        if total_original_issues > total_consolidated:
            alert_text += f"({total_original_issues} total occurrence{'s' if total_original_issues > 1 else ''} consolidated into {total_consolidated} unique issue{'s' if total_consolidated > 1 else ''})"
        
        return f'''
        <div class="section" id="section-issues">
            <h2>⚠️ Issues</h2>
            <div class="alert {alert_class}">
                {alert_text}
            </div>
            
            <div style="overflow-x: auto; margin-top: 1.5rem;">
                <table class="endpoint-table" style="width: 100%; max-width: 100%; border-collapse: collapse; table-layout: auto; word-wrap: break-word; overflow-wrap: break-word;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                            <th style="padding: 1rem; text-align: left; font-weight: 600; word-wrap: break-word; max-width: 200px;">Issue</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600; word-wrap: break-word; max-width: 250px;">Example of Issue</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600; word-wrap: break-word; max-width: 200px;">Impact</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600; word-wrap: break-word; max-width: 250px;">Recommendation</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600; word-wrap: break-word; max-width: 200px;">Business Benefit</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Priority</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_business_impact(error_rate: float, avg_response: Optional[float]) -> str:
        """Generate business impact assessment"""
        perf_word = (
            "Unknown"
            if avg_response is None
            else ("Poor" if avg_response > 5 else "Moderate")
        )
        perf_snip = (
            "N/A (no successful latency samples)"
            if avg_response is None
            else f"{avg_response:.1f}s avg"
        )
        abandon = (
            "High"
            if avg_response is not None and avg_response > 5
            else ("Medium" if avg_response is not None else "Elevated")
        )
        return f'''
        <div class="section" id="section-business-impact">
            <h2>💰 Business Impact Assessment</h2>
            <div style="background: linear-gradient(135deg, #f0f9ff, #e0f2fe); border-radius: 12px; padding: 2rem; margin: 1rem 0;">
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; text-align: center;">
                    <div style="background: white; padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">Significant</div>
                        <div style="color: var(--text-secondary);">Investment Required</div>
                    </div>
                    <div style="background: white; padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);">6 Months</div>
                        <div style="color: var(--text-secondary);">Timeline to A+</div>
                    </div>
                    <div style="background: white; padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);">High</div>
                        <div style="color: var(--text-secondary);">Expected ROI</div>
                    </div>
                    <div style="background: white; padding: 1rem; border-radius: 8px;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--success-color);">2-4 Months</div>
                        <div style="color: var(--text-secondary);">Payback Period</div>
                    </div>
                </div>
                
                <div style="margin-top: 2rem;">
                    <h4 style="margin-bottom: 1rem;">Cost of Inaction (Current State)</h4>
                    <ul>
                        <li><strong>{'High' if error_rate > 5 else 'Moderate'} Error Rate ({error_rate:.2f}%):</strong> {'Major' if error_rate > 5 else 'Moderate'} revenue loss from failed operations and user frustration</li>
                        <li><strong>{perf_word} Performance ({perf_snip}):</strong> {'Significant' if (avg_response or 0) > 5 else 'Moderate'} productivity loss affecting user efficiency</li>
                        <li><strong>Support Overhead:</strong> {'Increased' if error_rate > 3 else 'Moderate'} operational costs due to performance issues</li>
                        <li><strong>User Abandonment Risk:</strong> {abandon} opportunity cost from customer dissatisfaction</li>
                    </ul>
                </div>
                
                <div style="margin-top: 2rem;">
                    <h4 style="margin-bottom: 1rem;">Benefits of Optimization</h4>
                    <ul>
                        <li><strong>Improved Reliability:</strong> Substantial revenue increase through reliable operations</li>
                        <li><strong>Fast Performance:</strong> Major productivity gains improving user satisfaction</li>
                        <li><strong>Reduced Support:</strong> Significant operational savings through improved reliability</li>
                        <li><strong>User Retention:</strong> Valuable customer base protection and growth opportunities</li>
                    </ul>
                </div>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_phased_action_plan(phased_plan: Dict[str, Any], current_grade: str) -> str:
        """Generate PHASED improvement plan to reach A+ grade"""
        if not phased_plan or not phased_plan.get("phases"):
            return HTMLReportGenerator._generate_action_plan([], current_grade)
        
        current_score = phased_plan.get("current_score", 0)
        target_score = phased_plan.get("target_score", 90)
        score_gap = phased_plan.get("score_gap", 0)
        phases = phased_plan.get("phases", [])
        final_expected_score = phased_plan.get("final_expected_score", 90)
        estimated_timeline = phased_plan.get("estimated_timeline", "4-6 weeks")
        weak_areas = phased_plan.get("weak_areas", [])
        success_metrics = phased_plan.get("success_metrics", [])
        
        # Generate overview header
        overview_html = f'''
        <div style="background: linear-gradient(135deg, #ede9fe, #f5f3ff); border: 2px solid #a78bfa; border-radius: 12px; padding: 1.5rem; margin-bottom: 2rem;">
            <h3 style="margin: 0 0 1rem 0; color: #5b21b6;">📈 Improvement Roadmap to A+ Grade</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem;">
                <div>
                    <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">Current Status</p>
                    <p style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 700; color: #5b21b6;">{current_grade} ({current_score}/100)</p>
                </div>
                <div>
                    <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">Target Grade</p>
                    <p style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 700; color: #10b981;">A+ (90+/100)</p>
                </div>
                <div>
                    <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">Score Gap</p>
                    <p style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 700; color: #f59e0b;">{score_gap} points</p>
                </div>
                <div>
                    <p style="margin: 0; font-size: 0.875rem; color: #6b7280;">Estimated Timeline</p>
                    <p style="margin: 0.25rem 0 0 0; font-size: 1.5rem; font-weight: 700; color: #3b82f6;">{estimated_timeline}</p>
                </div>
            </div>
        </div>'''
        
        # Generate weak areas if any
        weak_areas_html = ""
        if weak_areas:
            weak_items = ''.join([f'<li style="margin-bottom: 0.5rem;"><strong>{area["area"]}:</strong> {area["current_score"]}/100</li>' for area in weak_areas])
            weak_areas_html = f'''
            <div style="background: #fef3c7; border-left: 4px solid #f59e0b; padding: 1rem; border-radius: 0 8px 8px 0; margin-bottom: 1.5rem;">
                <p style="margin: 0 0 0.5rem 0; font-weight: 700; color: #92400e;">⚠️ Focus Areas (Weakest Performance)</p>
                <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem;">
                    {weak_items}
                </ul>
            </div>'''
        
        # Tabular: phase summary + action detail (replaces card layout)
        def _esc(s: Any) -> str:
            if s is None:
                return ""
            return html.escape(str(s))
        
        summary_rows: List[str] = []
        detail_rows: List[str] = []
        for i, phase_data in enumerate(phases, 1):
            phase_name = phase_data.get("phase", "Phase")
            timeline = phase_data.get("timeline", "—")
            priority = phase_data.get("priority", "—")
            actions = phase_data.get("actions", [])
            target_score = phase_data.get("target_score", 0)
            expected_grade = phase_data.get("expected_grade", "—")
            n_act = len(actions)
            theme = " · ".join(
                a.get("action", "").strip() for a in actions[:4] if a.get("action")
            )
            if n_act > 4:
                theme = f"{theme} …" if theme else "…"
            summary_rows.append(
                f'''<tr>
                    <td style="text-align: center; font-weight: 600;">{i}</td>
                    <td style="font-weight: 600; color: var(--primary-color);">{_esc(phase_name)}</td>
                    <td style="text-align: center; white-space: nowrap;">{_esc(timeline)}</td>
                    <td style="text-align: center;">{_esc(priority)}</td>
                    <td style="text-align: center; font-weight: 600;">{html.escape(str(target_score))}</td>
                    <td style="text-align: center;">{_esc(expected_grade)}</td>
                    <td style="text-align: center;">{n_act}</td>
                    <td style="font-size: 0.82rem; color: #374151; max-width: 320px;">{_esc(theme) or "—"}</td>
                </tr>'''
            )
            priority_color = "#ef4444" if "High" in str(priority) else "#f59e0b" if "Medium" in str(priority) else "#10b981"
            for action in actions:
                action_title = action.get("action", "—")
                action_detail = action.get("detail", "")
                steps = action.get("steps", [])
                impact = action.get("expected_impact", "—")
                steps_li = "".join(
                    f'<li style="margin-bottom: 0.25rem;">{_esc(s)}</li>' for s in steps
                )
                steps_html = f'<ol style="margin: 0.25rem 0 0; padding-left: 1.25rem; font-size: 0.8rem; line-height: 1.45;">{steps_li}</ol>' if steps else "—"
                detail_rows.append(
                    f'''<tr>
                    <td style="font-weight: 600; border-left: 4px solid {priority_color}; white-space: nowrap;">{_esc(phase_name)}</td>
                    <td style="font-weight: 600;">{_esc(action_title)}</td>
                    <td style="font-size: 0.82rem; color: #4b5563; max-width: 280px;">{_esc(action_detail) or "—"}</td>
                    <td style="text-align: center; font-size: 0.82rem; color: #166534; font-weight: 600;">{_esc(impact)}</td>
                    <td style="vertical-align: top;">{steps_html}</td>
                </tr>'''
                )
        
        phases_html = f'''
            <div style="overflow-x: auto; margin-bottom: 1.5rem; -webkit-overflow-scrolling: touch;">
                <table class="endpoint-table" style="width: 100%; min-width: 720px; font-size: 0.88rem;">
                    <thead>
                        <tr>
                            <th style="width: 2.2rem; text-align: center;">#</th>
                            <th>Phase</th>
                            <th style="text-align: center;">Timeline</th>
                            <th style="text-align: center;">Priority</th>
                            <th style="text-align: center;">Target score</th>
                            <th style="text-align: center;">Expected grade</th>
                            <th style="text-align: center;">Actions</th>
                            <th>Focus (action themes)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(summary_rows)}
                    </tbody>
                </table>
            </div>
            <h4 style="margin: 0 0 0.75rem 0; color: var(--text-primary); font-size: 1rem;">Planned actions &amp; steps</h4>
            <div style="overflow-x: auto; margin-bottom: 0.5rem; -webkit-overflow-scrolling: touch;">
                <table class="endpoint-table" style="width: 100%; min-width: 800px; font-size: 0.85rem;">
                    <thead>
                        <tr>
                            <th style="white-space: nowrap;">Phase</th>
                            <th>Action</th>
                            <th>Detail</th>
                            <th style="text-align: center; width: 6rem;">Impact</th>
                            <th>Implementation steps</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(detail_rows)}
                    </tbody>
                </table>
            </div>'''
        
        # Generate success metrics
        success_metrics_html = ''.join([f'<li style="margin-bottom: 0.5rem;">✓ {metric}</li>' for metric in success_metrics])
        
        return f'''
        <div class="section" id="section-action-plan">
            <h2>🚀 Recommended Action Plan</h2>
            <p style="font-size: 1rem; color: #4b5563; margin-bottom: 1.5rem;">
                <strong>Performance Optimization Plan alignment</strong> — Phased remediation matches the optimization roadmap (immediate fixes → architecture → scale proof). The tables below expand phases into concrete engineering actions and score targets.
            </p>
            
            {overview_html}
            {weak_areas_html}
            
            <h3 style="margin: 2rem 0 1rem 0; color: var(--text-primary);">📋 Implementation Phases</h3>
            {phases_html}
            
            <div style="background: linear-gradient(135deg, #dcfce7, #f0fdf4); border: 2px solid #86efac; border-radius: 12px; padding: 1.5rem; margin-top: 2rem;">
                <h3 style="margin: 0 0 1rem 0; color: #166534;">🎯 A+ Grade Success Criteria</h3>
                <p style="margin: 0 0 0.75rem 0; color: #374151;">Once all phases are complete, your system will meet these benchmarks:</p>
                <ul style="margin: 0; padding-left: 1.5rem; font-size: 0.9rem; color: #166534;">
                    {success_metrics_html}
                </ul>
                <div style="background: white; padding: 1rem; border-radius: 8px; margin-top: 1rem; border-left: 4px solid #10b981;">
                    <p style="margin: 0; font-weight: 600; color: #166534;">
                        🎉 Expected Final Score: <span style="font-size: 1.2rem;">{final_expected_score}/100 (Grade A+)</span>
                    </p>
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #f0fdf4, #ecfdf5); border-left: 4px solid var(--success-color); padding: 1.5rem; border-radius: 0 8px 8px 0; margin-top: 2rem;">
                <h3>Deployment Recommendation</h3>
                <p><strong>✅ RECOMMENDED:</strong> {'Full production deployment with monitoring' if current_grade in ['A+', 'A'] else 'Gradual rollout with performance monitoring while implementing improvements' if current_grade in ['B+', 'B'] else 'Limited production rollout while implementing critical fixes'}</p>
                <ul>
                    <li>{'Deploy to full user base' if current_grade in ['A+', 'A'] else 'Deploy to limited user base initially (10-20%)' if current_grade in ['B+', 'B', 'C+'] else 'Deploy to pilot users only (<5%)'}</li>
                    <li>Implement comprehensive monitoring and alerting</li>
                    <li>Execute improvement phases in parallel with production</li>
                    <li>{'Maintain performance standards' if current_grade in ['A+', 'A'] else 'Gradual scale-up after each phase completion'}</li>
                    <li>Regular performance reviews and regression testing</li>
                </ul>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_action_plan(roadmap: List[dict], current_grade: str) -> str:
        """Generate recommended action plan in tabular format (LEGACY - kept for backward compatibility)"""
        if not roadmap:
            return f'''
        <div class="section" id="section-action-plan">
            <h2>🚀 Recommended Action Plan</h2>
            <p>No specific action plan generated. Consider standard performance optimization strategies.</p>
        </div>'''
    
    @staticmethod
    def _generate_final_conclusion(
        grade: str,
        score: float,
        success_rate: float,
        avg_response: Optional[float],
        error_rate: float,
        throughput: float,
        p95_response: Optional[float],
        sla_compliance: float,
        all_issues: List[dict],
        improvement_roadmap: List[dict],
        summary: dict,
        deep_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate final conclusion section."""
        if deep_context:
            hdr = summary.get("report_header") or {}
            env_line = html.escape(
                f"{hdr.get('product', 'Application')} {hdr.get('environment', '')} environment".strip()
            )
            return f'''
        <div class="section" id="section-final-conclusion" style="background:#fdfcfa;">
            <h2 style="letter-spacing:0.05em;color:#334155;">Final conclusion &amp; next steps</h2>
            <div style="padding:1.25rem 1.35rem;border-radius:12px;border:1px solid #e8dfd0;background:white;line-height:1.65;font-size:0.98rem;color:#1e293b;">
              <p style="margin:0 0 0.85rem 0;">The {env_line} demonstrates adequate performance only below ~60 concurrent users in many stepped tests (baseline zone P90 often near ~1s; error rate commonly ~2% or lower in that band). Beyond ~120 users, the system frequently enters a degraded state driven by compounding factors: broken or contested URL/routing resolution (HTTP 404 clusters), upstream or analytics saturation (HTTP 504 or timeout walls), and synchronous blocking on long-running workflows.</p>
              <p style="margin:0 0 0.5rem 0;"><strong>What is working:</strong> Login/Auth and low-error navigation paths often remain within SLA and are suitable anchors for post-fix regression comparisons.</p>
              <p style="margin:0 0 0.85rem 0;"><strong>What must be fixed before production:</strong> Transactions with very high error rates or chronic timeout dependencies should be cleared before material production traffic. Treat dominant 404/504 patterns as release blockers until reproduced, fixed, and re-tested.</p>
              <p style="margin:0 0 0.5rem 0;"><strong>Recommended next steps:</strong></p>
              <ol style="margin:0;padding-left:1.25rem;">
                <li style="margin-bottom:0.35rem;">Raise SEV-1 defects for top routing/404 patterns within 24 hours where error share is material.</li>
                <li style="margin-bottom:0.35rem;">Architecture review of the heaviest shared backends (e.g. rendering or analytics-style services) early in the remediation window.</li>
                <li style="margin-bottom:0.35rem;">Re-run a targeted regression (e.g. ~60 users) after Phase 1 fixes to confirm error bursts are eliminated before scaling load again.</li>
                <li style="margin-bottom:0.35rem;">Full stepped load to peak concurrency after mid-term fixes to validate production readiness.</li>
              </ol>
              <p style="margin:1rem 0 0.5rem 0;"><strong>Engineering quality posture:</strong> Performance-test the application for every material change. After each release, run a complete end-to-end performance cycle (baseline → load → soak or regression) so latency, errors, and capacity move together. <em>Advantage:</em> you catch regressions before customers do, shorten root-cause time with comparable runs, and keep SLAs predictable as code and infrastructure evolve.</p>
            </div>
        </div>'''

        ar_txt = f"{avg_response:.2f}s" if avg_response is not None else "N/A (no successful latency samples)"
        # Generate conclusion write-up
        if grade in ["A+", "A"]:
            conclusion_text = f"The performance assessment reveals an excellent system with a grade of {grade} (Score: {score:.0f}/100). The application demonstrates strong performance metrics including a {success_rate:.1f}% success rate, {ar_txt} average response time, and {throughput:.0f} requests/second throughput. The system is well-optimized and ready for production deployment with minimal concerns."
        elif grade in ["B+", "B"]:
            conclusion_text = f"The performance assessment indicates a good system with a grade of {grade} (Score: {score:.0f}/100). While the application shows acceptable performance with {success_rate:.1f}% success rate and {ar_txt} average response time, there are opportunities for optimization to achieve excellence. The system can be deployed with monitoring while implementing recommended improvements."
        else:
            conclusion_text = f"The performance assessment reveals a system requiring attention with a grade of {grade} (Score: {score:.0f}/100). The application shows {success_rate:.1f}% success rate and {ar_txt} average response time, indicating areas that need improvement. Immediate action is recommended to address critical issues before full production deployment."
        
        # Key Strengths
        strengths = []
        if success_rate >= 99:
            strengths.append(f"High success rate of {success_rate:.1f}% demonstrates excellent system reliability")
        if avg_response is not None and avg_response <= 2.0:
            strengths.append(f"Fast average response time of {avg_response:.2f}s ensures optimal user experience")
        if error_rate < 1.0:
            strengths.append(f"Low error rate of {error_rate:.2f}% indicates robust error handling")
        if throughput >= 100:
            strengths.append(f"High throughput of {throughput:.0f} req/s shows good system capacity")
        if sla_compliance >= 95:
            strengths.append(f"Excellent SLA compliance of {sla_compliance:.1f}% meets performance targets")
        if not strengths:
            strengths.append("System demonstrates basic functionality and stability")
        
        # Areas of Improvement
        improvements = []
        if avg_response is None:
            improvements.append("Restore successful requests to obtain meaningful response-time metrics (address failures and HTTP errors first)")
        elif avg_response > 2.0:
            improvements.append(f"Optimize response time from {avg_response:.2f}s to target <2s for better user experience")
        if error_rate > 1.0:
            improvements.append(f"Reduce error rate from {error_rate:.2f}% to target <1% for improved reliability")
        if throughput < 100:
            improvements.append(f"Increase throughput from {throughput:.0f} req/s to handle higher loads")
        if sla_compliance < 95:
            improvements.append(f"Improve SLA compliance from {sla_compliance:.1f}% to target 95%+")
        critical_issues = [i for i in all_issues if i.get('priority', '').startswith('P0')]
        if critical_issues:
            improvements.append(f"Address {len(critical_issues)} critical issue(s) identified in the assessment")
        if all_issues and not critical_issues:
            improvements.append(f"Address {len(all_issues)} issue(s) identified in the assessment")
        if not improvements:
            improvements.append("Continue monitoring and maintain current performance standards")
        
        # Recommended Immediate Actions
        immediate_actions = []
        critical_issues = [i for i in all_issues if i.get('priority', '').startswith('P0')]
        if critical_issues:
            immediate_actions.append(f"Address {len(critical_issues)} critical issue(s) identified in the assessment (see Issues section)")
        elif all_issues:
            immediate_actions.append(f"Review {len(all_issues)} issue(s) identified in the assessment (see Issues section)")
        if error_rate > 5.0:
            immediate_actions.append("Implement error handling improvements to reduce error rate")
        if avg_response is not None and avg_response > 5.0:
            immediate_actions.append("Optimize slow endpoints and database queries to improve response time")
        if sla_compliance < 80:
            immediate_actions.append("Implement performance optimizations to improve SLA compliance")
        if not immediate_actions:
            immediate_actions.append("Continue monitoring system performance and maintain current standards")
        
        # Success Metrics
        _ar_for_target = avg_response if avg_response is not None else 2.0
        success_metrics = [
            f"Maintain success rate above {max(95, success_rate * 0.95):.1f}%",
            f"Achieve average response time below {max(2.0, _ar_for_target * 0.8):.2f}s",
            f"Reduce error rate to below {max(1.0, error_rate * 0.5):.2f}%",
            f"Increase throughput to {max(100, throughput * 1.2):.0f}+ req/s",
            f"Achieve SLA compliance of {min(95, sla_compliance + 10):.1f}%+"
        ]
        if avg_response is None:
            success_metrics[1] = "Obtain successful requests with measurable latency, then target average response time under 2.0s"
        
        strengths_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{s}</li>' for s in strengths])
        improvements_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{i}</li>' for i in improvements])
        actions_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{a}</li>' for a in immediate_actions])
        metrics_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{m}</li>' for m in success_metrics])
        
        return f'''
        <div class="section" id="section-final-conclusion">
            <h2>📋 Final Conclusion</h2>
            
            <div style="background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%); padding: 2rem; border-radius: 8px; border: 2px solid #e5e7eb; margin-bottom: 2rem;">
                <h3 style="color: var(--primary-color); margin-top: 0;">Conclusion</h3>
                <p style="font-size: 1.05rem; line-height: 1.8; color: var(--text-primary); text-align: justify;">
                    {conclusion_text}
                </p>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem;">
                <div style="background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%); padding: 1.5rem; border-radius: 8px; border-left: 4px solid #10b981;">
                    <h4 style="color: #059669; margin-top: 0;">✅ Key Strengths</h4>
                    <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                        {strengths_html}
                    </ul>
                </div>
                
                <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 1.5rem; border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <h4 style="color: #d97706; margin-top: 0;">🔧 Areas of Improvement</h4>
                    <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                        {improvements_html}
                    </ul>
                </div>
            </div>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
                <div style="background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%); padding: 1.5rem; border-radius: 8px; border-left: 4px solid #ef4444;">
                    <h4 style="color: #dc2626; margin-top: 0;">⚡ Recommended Immediate Actions</h4>
                    <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                        {actions_html}
                    </ul>
                </div>
                
                <div style="background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); padding: 1.5rem; border-radius: 8px; border-left: 4px solid #2563eb;">
                    <h4 style="color: #1d4ed8; margin-top: 0;">🎯 Success Metrics</h4>
                    <ul style="margin: 0; padding-left: 1.5rem; color: var(--text-primary);">
                        {metrics_html}
                    </ul>
                </div>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_success_metrics(avg_response: Optional[float], p95_response: Optional[float], error_rate: float, 
                                  success_rate: float, sla_compliance: float, throughput: float) -> str:
        """Generate success metrics and targets"""
        if avg_response is not None:
            target_3m_avg = max(2.0, avg_response * 0.6)
            target_6m_avg = max(0.8, avg_response * 0.3)
            cur_avg_cell = f"{avg_response:.1f} sec"
        else:
            target_3m_avg, target_6m_avg = 2.0, 1.0
            cur_avg_cell = "N/A"
        if p95_response is not None:
            target_3m_p95 = max(5.0, p95_response * 0.4)
            target_6m_p95 = max(2.5, p95_response * 0.2)
            cur_p95_cell = f"{p95_response:.1f} sec"
        else:
            target_3m_p95, target_6m_p95 = 5.0, 3.0
            cur_p95_cell = "N/A"
        target_3m_error = max(0.8, error_rate * 0.4)
        target_6m_error = 0.3
        publish_success_current = success_rate
        target_3m_sla = min(95, sla_compliance + 20)
        target_6m_sla = 95
        target_3m_throughput = throughput * 1.5
        target_6m_throughput = max(180, throughput * 2.5)
        
        return f'''
        <div class="section" id="section-success-metrics">
            <h2>🎯 Success Metrics & Targets</h2>
            <h3>6-Month Performance Targets</h3>
            <table class="endpoint-table">
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th style="text-align: center;">Current</th>
                        <th style="text-align: center;">3-Month Target</th>
                        <th style="text-align: center;">6-Month Target</th>
                        <th style="text-align: center;">Industry Standard</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>Avg Response Time</strong></td>
                        <td style="text-align: center;">{cur_avg_cell}</td>
                        <td style="text-align: center;">{target_3m_avg:.1f} sec</td>
                        <td style="text-align: center;">{target_6m_avg:.1f} sec</td>
                        <td style="text-align: center;">&lt;2 sec</td>
                    </tr>
                    <tr>
                        <td><strong>95th Percentile</strong></td>
                        <td style="text-align: center;">{cur_p95_cell}</td>
                        <td style="text-align: center;">{target_3m_p95:.1f} sec</td>
                        <td style="text-align: center;">{target_6m_p95:.1f} sec</td>
                        <td style="text-align: center;">&lt;3 sec</td>
                    </tr>
                    <tr>
                        <td><strong>Error Rate</strong></td>
                        <td style="text-align: center;">{error_rate:.2f}%</td>
                        <td style="text-align: center;">{target_3m_error:.1f}%</td>
                        <td style="text-align: center;">{target_6m_error:.1f}%</td>
                        <td style="text-align: center;">&lt;0.5%</td>
                    </tr>
                    <tr>
                        <td><strong>Success Rate</strong></td>
                        <td style="text-align: center;">{publish_success_current:.1f}%</td>
                        <td style="text-align: center;">99%</td>
                        <td style="text-align: center;">99.5%</td>
                        <td style="text-align: center;">&gt;99%</td>
                    </tr>
                    <tr>
                        <td><strong>SLA Compliance</strong></td>
                        <td style="text-align: center;">{sla_compliance:.1f}%</td>
                        <td style="text-align: center;">{target_3m_sla:.0f}%</td>
                        <td style="text-align: center;">{target_6m_sla:.0f}%</td>
                        <td style="text-align: center;">&gt;95%</td>
                    </tr>
                    <tr>
                        <td><strong>Throughput</strong></td>
                        <td style="text-align: center;">{throughput:.0f}/s</td>
                        <td style="text-align: center;">{target_3m_throughput:.0f}/s</td>
                        <td style="text-align: center;">{target_6m_throughput:.0f}/s</td>
                        <td style="text-align: center;">150/s</td>
                    </tr>
                </tbody>
            </table>
        </div>'''
    
    @staticmethod
    def _generate_footer(report_date: str) -> str:
        """Generate next steps and footer"""
        return f'''
        <div class="section" id="section-next-steps">
            <h2>📞 Next Steps & Contacts</h2>
            <div class="two-column">
                <div>
                    <h3>Immediate Actions Required</h3>
                    <ul style="list-style-position: inside;">
                        <li>✅ Executive review and approval of action plan</li>
                        <li>✅ Resource allocation for performance improvements</li>
                        <li>✅ Production deployment strategy decision</li>
                        <li>✅ Weekly progress review schedule</li>
                    </ul>
                </div>
                <div>
                    <h3>Reporting Schedule</h3>
                    <ul style="list-style-position: inside;">
                        <li><strong>Daily:</strong> Critical fix progress updates</li>
                        <li><strong>Weekly:</strong> Performance metrics review</li>
                        <li><strong>Monthly:</strong> Business impact assessment</li>
                        <li><strong>Quarterly:</strong> Strategic roadmap review</li>
                    </ul>
                </div>
            </div>
            
            <div class="alert alert-success" style="margin-top: 2rem;">
                <h4>Key Takeaway</h4>
                <p>This performance assessment provides a comprehensive view of the system's current state and a clear roadmap for improvement. By following the recommended action plan, the organization can achieve excellent performance while delivering superior user experience and maximizing business value.</p>
            </div>
            
            <div style="text-align: center; margin-top: 2rem; padding: 1.5rem; border-top: 2px solid var(--border-color); background: var(--background-light); border-radius: 8px;">
                <p style="margin: 0.5rem 0;"><strong>Report Generated:</strong> {report_date}</p>
                <p style="margin: 0.5rem 0;"><strong>Generated By:</strong> Raghvendra Kumar</p>
                <p style="margin: 0.5rem 0;"><strong>Classification:</strong> Internal</p>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_javascript(response_time_dist: dict, response_codes: dict) -> str:
        """Generate Chart.js JavaScript"""
        # Response time distribution data
        under_1s = response_time_dist.get('under_1s', 0)
        one_to_2s = response_time_dist.get('1_to_2s', 0)
        two_to_3s = response_time_dist.get('2_to_3s', 0)
        three_to_5s = response_time_dist.get('3_to_5s', 0)
        five_to_10s = response_time_dist.get('5_to_10s', 0)
        over_10s = response_time_dist.get('over_10s', 0)
        
        # Response codes data
        code_200 = response_codes.get('200', 0)
        code_201 = response_codes.get('201', 0)
        code_400 = response_codes.get('400', 0)
        code_500 = response_codes.get('500', 0)
        code_502 = response_codes.get('502', 0)
        
        return f'''
    <script>
        // Datalabels plugin: register but keep point labels off by default (avoids clutter on line charts)
        if (window.ChartDataLabels) {{
            Chart.register(ChartDataLabels);
            Chart.defaults.set('plugins.datalabels', {{ display: false }});
        }}
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        
        console.log('Performance report loaded successfully');
        console.log('Response time distribution:', {{
            'under_1s': {under_1s:.2f},
            '1_to_2s': {one_to_2s:.2f},
            '2_to_3s': {two_to_3s:.2f},
            '3_to_5s': {three_to_5s:.2f},
            '5_to_10s': {five_to_10s:.2f},
            'over_10s': {over_10s:.2f}
        }});
    </script>'''
    
    @staticmethod
    def generate_web_vitals_html_report(metrics: Dict[str, Any], filename: str = "web_vitals_report.html") -> str:
        """Generate HTML report for Web Vitals metrics (editorial tabbed layout, same chrome as JMeter / Lighthouse)."""
        from app.report_generator.csv_web_vitals_report_html import render_csv_web_vitals_editorial_html

        return render_csv_web_vitals_editorial_html(metrics, filename)
    
    @staticmethod
    def generate_ui_performance_html_report(metrics: Dict[str, Any], filename: str = "ui_performance_report.html") -> str:
        """Generate HTML report for UI Performance metrics"""
        current_date = datetime.now().strftime("%B %d, %Y")
        total_samples = metrics.get("total_samples", 0)
        
        dns = metrics.get("dns_lookup_time", {})
        conn = metrics.get("connection_time", {})
        ssl = metrics.get("ssl_time", {})
        ttfb = metrics.get("time_to_first_byte", {})
        download = metrics.get("content_download_time", {})
        dom = metrics.get("dom_processing_time", {})
        page_load = metrics.get("page_load_time", {})
        full_load = metrics.get("full_page_load_time", {})
        summary = metrics.get("summary", {})
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>UI Performance Report</title>
    <style>
        :root {{
            --primary: #9b59b6;
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --text: #2c3e50;
            --bg: #f8f9fa;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .header {{ text-align: center; padding: 2rem; background: linear-gradient(135deg, var(--primary), #8e44ad); color: white; border-radius: 12px; margin-bottom: 2rem; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1.5rem; margin: 2rem 0; }}
        .metric-card {{ background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 4px solid var(--primary); text-align: center; }}
        .metric-card h3 {{ font-size: 0.9rem; color: #666; margin-bottom: 0.5rem; }}
        .metric-card .value {{ font-size: 1.8rem; font-weight: 700; color: var(--primary); }}
        .metric-card .unit {{ font-size: 0.9rem; color: #888; }}
        .section {{ background: white; border-radius: 12px; padding: 2rem; margin: 2rem 0; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
        .section h2 {{ color: var(--primary); margin-bottom: 1.5rem; border-bottom: 2px solid var(--primary); padding-bottom: 0.5rem; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid #eee; }}
        th {{ background: var(--bg); font-weight: 600; }}
        .footer {{ text-align: center; padding: 1.5rem; background: white; border-radius: 12px; margin-top: 2rem; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 UI Performance Report</h1>
            <p>Page Load Timing Analysis | {current_date}</p>
            <p style="margin-top: 0.5rem;">Total Samples: {total_samples:,}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <h3>DNS Lookup</h3>
                <div class="value">{dns.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>Connection Time</h3>
                <div class="value">{conn.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>SSL/TLS Time</h3>
                <div class="value">{ssl.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>Time to First Byte</h3>
                <div class="value">{ttfb.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>Content Download</h3>
                <div class="value">{download.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>DOM Processing</h3>
                <div class="value">{dom.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>Page Load Time</h3>
                <div class="value">{page_load.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
            <div class="metric-card">
                <h3>Full Page Load</h3>
                <div class="value">{full_load.get('mean', 0) or 0:.0f}</div>
                <div class="unit">ms</div>
            </div>
        </div>
        
        <div class="section">
            <h2>📊 Detailed Statistics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Mean</th>
                        <th>Median</th>
                        <th>P95</th>
                        <th>P99</th>
                        <th>Min</th>
                        <th>Max</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>DNS Lookup</strong></td>
                        <td>{dns.get('mean', 0) or 0:.0f}ms</td>
                        <td>{dns.get('median', 0) or 0:.0f}ms</td>
                        <td>{dns.get('p95', 0) or 0:.0f}ms</td>
                        <td>{dns.get('p99', 0) or 0:.0f}ms</td>
                        <td>{dns.get('min', 0) or 0:.0f}ms</td>
                        <td>{dns.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>Connection Time</strong></td>
                        <td>{conn.get('mean', 0) or 0:.0f}ms</td>
                        <td>{conn.get('median', 0) or 0:.0f}ms</td>
                        <td>{conn.get('p95', 0) or 0:.0f}ms</td>
                        <td>{conn.get('p99', 0) or 0:.0f}ms</td>
                        <td>{conn.get('min', 0) or 0:.0f}ms</td>
                        <td>{conn.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>SSL/TLS Time</strong></td>
                        <td>{ssl.get('mean', 0) or 0:.0f}ms</td>
                        <td>{ssl.get('median', 0) or 0:.0f}ms</td>
                        <td>{ssl.get('p95', 0) or 0:.0f}ms</td>
                        <td>{ssl.get('p99', 0) or 0:.0f}ms</td>
                        <td>{ssl.get('min', 0) or 0:.0f}ms</td>
                        <td>{ssl.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>Time to First Byte</strong></td>
                        <td>{ttfb.get('mean', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('median', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('p95', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('p99', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('min', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>Content Download</strong></td>
                        <td>{download.get('mean', 0) or 0:.0f}ms</td>
                        <td>{download.get('median', 0) or 0:.0f}ms</td>
                        <td>{download.get('p95', 0) or 0:.0f}ms</td>
                        <td>{download.get('p99', 0) or 0:.0f}ms</td>
                        <td>{download.get('min', 0) or 0:.0f}ms</td>
                        <td>{download.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>DOM Processing</strong></td>
                        <td>{dom.get('mean', 0) or 0:.0f}ms</td>
                        <td>{dom.get('median', 0) or 0:.0f}ms</td>
                        <td>{dom.get('p95', 0) or 0:.0f}ms</td>
                        <td>{dom.get('p99', 0) or 0:.0f}ms</td>
                        <td>{dom.get('min', 0) or 0:.0f}ms</td>
                        <td>{dom.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>Page Load Time</strong></td>
                        <td>{page_load.get('mean', 0) or 0:.0f}ms</td>
                        <td>{page_load.get('median', 0) or 0:.0f}ms</td>
                        <td>{page_load.get('p95', 0) or 0:.0f}ms</td>
                        <td>{page_load.get('p99', 0) or 0:.0f}ms</td>
                        <td>{page_load.get('min', 0) or 0:.0f}ms</td>
                        <td>{page_load.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>Full Page Load</strong></td>
                        <td>{full_load.get('mean', 0) or 0:.0f}ms</td>
                        <td>{full_load.get('median', 0) or 0:.0f}ms</td>
                        <td>{full_load.get('p95', 0) or 0:.0f}ms</td>
                        <td>{full_load.get('p99', 0) or 0:.0f}ms</td>
                        <td>{full_load.get('min', 0) or 0:.0f}ms</td>
                        <td>{full_load.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            <p><strong>Report Generated:</strong> {current_date}</p>
            <p><strong>Generated By:</strong> Raghvendra Kumar</p>
            <p><strong>Classification:</strong> Internal</p>
        </div>
    </div>
</body>
</html>'''

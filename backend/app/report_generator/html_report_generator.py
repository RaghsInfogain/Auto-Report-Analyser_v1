from typing import Dict, Any, List
from datetime import datetime
import json
from app.report_generator.graph_analyzer import GraphAnalyzer

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
        
        # Extract metrics
        total_samples = metrics.get("total_samples", 0)
        error_rate_pct = metrics.get("error_rate", 0) * 100
        throughput = metrics.get("throughput", 0)
        
        summary = metrics.get("summary", {})
        success_rate = summary.get("success_rate", 0)
        test_duration_hours = summary.get("test_duration_hours", 0)
        
        sample_time = metrics.get("sample_time", {})
        avg_response = sample_time.get("mean", 0) / 1000  # Convert to seconds
        p70_response = sample_time.get("p70", 0) / 1000
        p80_response = sample_time.get("p80", 0) / 1000
        p90_response = sample_time.get("p90", 0) / 1000
        p95_response = sample_time.get("p95", 0) / 1000
        p99_response = sample_time.get("p99", 0) / 1000
        median_response = sample_time.get("median", 0) / 1000
        max_response = sample_time.get("max", 0) / 1000
        
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
        critical_issues = summary.get("critical_issues", [])
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
        exec_summary = HTMLReportGenerator._generate_executive_summary(overall_grade, overall_score, success_rate, avg_response, error_rate_pct, throughput, p95_response, sla_compliance_2s, summary)
        
        update_progress(30, "Generating performance scorecard...")
        scorecard = HTMLReportGenerator._generate_performance_scorecard(overall_grade, overall_score, grade_reasons, scores, targets, success_rate, avg_response, error_rate_pct, throughput, p95_response, sla_compliance_2s, grade_bg_color, grade_border_color, overall_grade_description)
        
        update_progress(40, "Generating test overview...")
        test_overview = HTMLReportGenerator._generate_test_overview(total_samples, test_duration_hours, throughput, success_rate)
        
        update_progress(50, "Generating performance tables...")
        perf_tables = HTMLReportGenerator._generate_performance_tables(transaction_stats, request_stats)
        
        update_progress(60, "Generating system behaviour graph...")
        system_graph = HTMLReportGenerator._generate_system_behaviour_graph(summary.get("time_series_data", []), progress_callback=lambda p, m: update_progress(60 + int(p * 0.15), f"Graph: {m}"))
        
        update_progress(75, "Generating additional graphs...")
        additional_graphs = HTMLReportGenerator._generate_additional_graphs(summary.get("time_series_data", []), transaction_stats, request_stats, metrics, progress_callback=lambda p, m: update_progress(75 + int(p * 0.10), f"Additional: {m}"))
        
        update_progress(85, "Generating critical issues...")
        critical_issues_html = HTMLReportGenerator._generate_critical_issues(critical_issues)
        
        update_progress(87, "Generating business impact...")
        business_impact = HTMLReportGenerator._generate_business_impact(error_rate_pct, avg_response)
        
        update_progress(89, "Generating action plan...")
        action_plan = HTMLReportGenerator._generate_action_plan(improvement_roadmap, overall_grade)
        
        update_progress(91, "Generating success metrics...")
        success_metrics = HTMLReportGenerator._generate_success_metrics(avg_response, p95_response, error_rate_pct, success_rate, sla_compliance_2s, throughput)
        
        update_progress(93, "Generating final conclusion...")
        final_conclusion = HTMLReportGenerator._generate_final_conclusion(overall_grade, overall_score, success_rate, avg_response, error_rate_pct, throughput, p95_response, sla_compliance_2s, critical_issues, improvement_roadmap, summary)
        
        update_progress(95, "Generating footer...")
        footer = HTMLReportGenerator._generate_footer(current_date)
        
        update_progress(97, "Generating JavaScript...")
        javascript = HTMLReportGenerator._generate_javascript(response_time_dist, response_codes)
        
        update_progress(99, "Assembling final HTML...")
        
        # Generate HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Assessment Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    {css_content}
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="container">
            <h1>Performance Assessment Report</h1>
            <p>Load Testing Results & Executive Analysis | {current_date}</p>
            {f'<p style="margin-top: 0.5rem; font-size: 0.9rem; color: #64748b;"><strong>Consolidated Report:</strong> {file_count} file(s) analyzed</p>' if is_consolidated else ''}
        </div>
    </div>

    <div class="container">
        
        {HTMLReportGenerator._generate_consolidated_files_info(file_info, consolidated_files) if is_consolidated else ''}
        
        <!-- Executive Summary -->
        {exec_summary}
        
        <!-- Performance Scorecard with Grading -->
        {scorecard}
        
        <!-- Test Overview -->
        {test_overview}
        
        <!-- Performance Summary Tables -->
        {perf_tables}
        
        <!-- Overall System Behaviour Graph -->
        {system_graph}
        
        <!-- Additional Performance Graphs -->
        {additional_graphs}
        
        <!-- Critical Issues -->
        {critical_issues_html}
        
        <!-- Business Impact Assessment -->
        {business_impact}
        
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
</body>
</html>'''
        
        return html
    
    @staticmethod
    def _generate_css() -> str:
        """Generate CSS styles"""
        return '''<style>
        :root {
            --primary-color: #2563eb;
            --success-color: #059669;
            --warning-color: #d97706;
            --danger-color: #dc2626;
            --secondary-color: #64748b;
            --background-light: #f8fafc;
            --card-background: #ffffff;
            --text-primary: #1e293b;
            --text-secondary: #64748b;
            --border-color: #e2e8f0;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--background-light);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), #3b82f6);
            color: white;
            padding: 2rem 0;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .header p {
            font-size: 1.2rem;
            opacity: 0.9;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }

        .section {
            background: var(--card-background);
            margin: 2rem 0;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
            border: 1px solid var(--border-color);
        }

        .section h2 {
            color: var(--primary-color);
            font-size: 1.8rem;
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 2px solid var(--primary-color);
        }

        .section h3 {
            color: var(--text-primary);
            font-size: 1.4rem;
            margin: 1.5rem 0 1rem 0;
        }

        .status-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.9rem;
            margin: 0.25rem;
        }

        .badge-success { background: var(--success-color); color: white; }
        .badge-warning { background: var(--warning-color); color: white; }
        .badge-danger { background: var(--danger-color); color: white; }
        .badge-info { background: var(--primary-color); color: white; }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 1rem;
            margin: 1.5rem 0;
        }

        .metric-card {
            background: var(--card-background);
            border: 2px solid var(--border-color);
            border-radius: 10px;
            padding: 0.8rem;
            text-align: left;
            transition: transform 0.2s, box-shadow 0.2s;
            min-height: 140px;
            display: flex;
            flex-direction: column;
        }

        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }

        .metric-card.success { border-color: var(--success-color); background: linear-gradient(135deg, rgba(16, 185, 129, 0.05), transparent); }
        .metric-card.warning { border-color: var(--warning-color); background: linear-gradient(135deg, rgba(245, 158, 11, 0.05), transparent); }
        .metric-card.danger { border-color: var(--danger-color); background: linear-gradient(135deg, rgba(239, 68, 68, 0.05), transparent); }

        .metric-value {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .metric-value.success { color: var(--success-color); }
        .metric-value.warning { color: var(--warning-color); }
        .metric-value.danger { color: var(--danger-color); }

        .metric-label {
            color: var(--text-secondary);
            font-weight: 500;
            text-transform: uppercase;
            font-size: 0.9rem;
        }

        .chart-container {
            position: relative;
            height: 400px;
            margin: 2rem 0;
        }

        .two-column {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 2rem;
            align-items: start;
        }

        .issue-item {
            background: #fef2f2;
            border-left: 4px solid var(--danger-color);
            padding: 1rem;
            margin: 1rem 0;
            border-radius: 0 8px 8px 0;
        }

        .issue-item h4 {
            color: var(--danger-color);
            margin-bottom: 0.5rem;
        }

        .endpoint-table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }

        .endpoint-table th,
        .endpoint-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        .endpoint-table th {
            background: var(--background-light);
            font-weight: 600;
            color: var(--text-primary);
        }

        .endpoint-table tr:hover {
            background: var(--background-light);
        }

        .action-timeline {
            position: relative;
            padding: 1rem 0;
        }

        .timeline-item {
            position: relative;
            padding: 1rem 0 1rem 3rem;
            border-left: 2px solid var(--border-color);
        }

        .timeline-item::before {
            content: '';
            position: absolute;
            left: -6px;
            top: 1.5rem;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--primary-color);
        }

        .timeline-item.danger::before { background: var(--danger-color); }
        .timeline-item.warning::before { background: var(--warning-color); }
        .timeline-item.success::before { background: var(--success-color); }

        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border: 1px solid;
        }

        .alert-danger {
            background: #fef2f2;
            border-color: var(--danger-color);
            color: #991b1b;
        }

        .alert-warning {
            background: #fffbeb;
            border-color: var(--warning-color);
            color: #92400e;
        }

        .alert-success {
            background: #f0fdf4;
            border-color: var(--success-color);
            color: #166534;
        }

        .executive-summary {
            background: linear-gradient(135deg, #1e40af, #3b82f6);
            color: white;
            padding: 2rem;
            border-radius: 12px;
            margin: 2rem 0;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1rem;
            margin: 1rem 0;
        }

        .summary-item {
            text-align: center;
            padding: 1rem;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 8px;
        }

        .summary-value {
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background: var(--border-color);
            border-radius: 10px;
            overflow: hidden;
            margin: 0.5rem 0;
        }

        .progress-fill {
            height: 100%;
            transition: width 0.3s ease;
        }

        .progress-success { background: var(--success-color); }
        .progress-warning { background: var(--warning-color); }
        .progress-danger { background: var(--danger-color); }

        @media (max-width: 768px) {
            .header h1 { font-size: 2rem; }
            .two-column { grid-template-columns: 1fr; }
            .metrics-grid { grid-template-columns: repeat(2, 1fr); }
        }
        
        @media (max-width: 600px) {
            .metrics-grid { grid-template-columns: 1fr; }
        }
    </style>'''
    
    @staticmethod
    def _generate_executive_summary(grade: str, score: float, success_rate: float, avg_response: float, error_rate: float, throughput: float, p95_response: float, sla_compliance: float, summary: dict) -> str:
        """Generate executive summary section with key findings"""
        # Determine status color and message
        if grade in ["A+", "A"]:
            status_color = "#10b981"
            status_icon = "✅"
            status_text = "APPROVED"
            status_message = "The application demonstrates excellent performance and stability. Ready for full production deployment."
        elif grade in ["B+", "B"]:
            status_color = "#f59e0b"
            status_icon = "⚠️"
            status_text = "CONDITIONAL APPROVAL"
            status_message = "The application is stable but requires performance improvements. Recommended approach: Limited rollout with monitoring."
        else:
            status_color = "#ef4444"
            status_icon = "⚠️"
            status_text = "CAUTIONARY APPROVAL"
            status_message = "The application demonstrates stability but exhibits critical performance issues requiring immediate attention. Recommended approach: Limited production rollout while implementing critical fixes."
        
        # Generate key findings
        key_findings = []
        
        # Performance findings
        if avg_response <= 2.0:
            key_findings.append(f"✅ <strong>Excellent Response Time:</strong> Average response time of {avg_response:.2f}s meets industry standards for optimal user experience.")
        elif avg_response <= 5.0:
            key_findings.append(f"⚠️ <strong>Moderate Response Time:</strong> Average response time of {avg_response:.2f}s is acceptable but has room for improvement to enhance user satisfaction.")
        else:
            key_findings.append(f"❌ <strong>Slow Response Time:</strong> Average response time of {avg_response:.2f}s exceeds acceptable thresholds and may impact user experience.")
        
        # Reliability findings
        if error_rate < 1.0:
            key_findings.append(f"✅ <strong>Low Error Rate:</strong> Error rate of {error_rate:.2f}% indicates high system reliability and stability.")
        elif error_rate < 5.0:
            key_findings.append(f"⚠️ <strong>Moderate Error Rate:</strong> Error rate of {error_rate:.2f}% suggests some reliability concerns that should be addressed.")
        else:
            key_findings.append(f"❌ <strong>High Error Rate:</strong> Error rate of {error_rate:.2f}% indicates significant reliability issues requiring immediate attention.")
        
        # Throughput findings
        if throughput >= 100:
            key_findings.append(f"✅ <strong>High Throughput:</strong> System processes {throughput:.0f} requests/second, demonstrating good capacity and scalability.")
        elif throughput >= 50:
            key_findings.append(f"⚠️ <strong>Moderate Throughput:</strong> System processes {throughput:.0f} requests/second, which is acceptable but could be optimized for higher loads.")
        else:
            key_findings.append(f"❌ <strong>Low Throughput:</strong> System processes only {throughput:.0f} requests/second, indicating potential scalability limitations.")
        
        # SLA compliance findings
        if sla_compliance >= 95:
            key_findings.append(f"✅ <strong>Excellent SLA Compliance:</strong> {sla_compliance:.1f}% of requests meet the 2-second SLA target, ensuring consistent user experience.")
        elif sla_compliance >= 80:
            key_findings.append(f"⚠️ <strong>Moderate SLA Compliance:</strong> {sla_compliance:.1f}% of requests meet the 2-second SLA target, indicating room for improvement.")
        else:
            key_findings.append(f"❌ <strong>Poor SLA Compliance:</strong> Only {sla_compliance:.1f}% of requests meet the 2-second SLA target, requiring immediate optimization.")
        
        # Success rate findings
        if success_rate >= 99:
            key_findings.append(f"✅ <strong>High Success Rate:</strong> {success_rate:.1f}% success rate demonstrates excellent system reliability.")
        elif success_rate >= 95:
            key_findings.append(f"⚠️ <strong>Moderate Success Rate:</strong> {success_rate:.1f}% success rate is acceptable but could be improved.")
        else:
            key_findings.append(f"❌ <strong>Low Success Rate:</strong> {success_rate:.1f}% success rate indicates significant reliability issues.")
        
        findings_html = ''.join([f'<li style="margin-bottom: 0.75rem; line-height: 1.6;">{finding}</li>' for finding in key_findings])
        
        return f'''
        <div class="executive-summary">
            <h2 style="color: white; border-bottom: 2px solid white;">Executive Summary</h2>
            <div class="alert" style="background: rgba(255, 255, 255, 0.1); border-color: white; color: white;">
                <h3 style="color: {status_color};">{status_icon} {status_text}</h3>
                <p><strong>{status_message}</strong></p>
            </div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value">{success_rate:.1f}%</div>
                    <div>Success Rate</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value">{avg_response:.1f}s</div>
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
            </div>
            <div style="background: rgba(255, 255, 255, 0.95); padding: 1.5rem; border-radius: 8px; margin-top: 1.5rem; color: var(--text-primary);">
                <h3 style="color: var(--primary-color); margin-top: 0;">🔍 Key Findings</h3>
                <ul style="margin: 0; padding-left: 1.5rem;">
                    {findings_html}
                </ul>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_performance_scorecard(grade: str, score: float, grade_reasons: dict, scores: dict, 
                                       targets: dict, success_rate: float, avg_response: float, 
                                       error_rate: float, throughput: float, p95_response: float, 
                                       sla_compliance: float, grade_bg_color: str, grade_border_color: str,
                                       overall_grade_description: dict = None) -> str:
        """Generate performance scorecard with grading analysis"""
        
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
        
        return f'''
        <div class="section">
            <h2>🎯 Performance Scorecard & Grading Analysis</h2>
            
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
                    <table style="width: 100%; border-collapse: collapse; margin: 1rem 0;">
                        <thead style="background: var(--background-light);">
                            <tr>
                                <th style="padding: 1rem; text-align: left; border: 1px solid var(--border-color);">Metric</th>
                                <th style="padding: 1rem; text-align: center; border: 1px solid var(--border-color);">Result</th>
                                <th style="padding: 1rem; text-align: center; border: 1px solid var(--border-color);">Target</th>
                                <th style="padding: 1rem; text-align: center; border: 1px solid var(--border-color);">Status</th>
                                <th style="padding: 1rem; text-align: center; border: 1px solid var(--border-color);">Score</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">Availability</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{success_rate:.1f}%</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{targets.get('availability', 99)}%</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {'badge-success' if success_rate >= 99 else 'badge-warning' if success_rate >= 95 else 'badge-danger'}">
                                        {'✅ PASS' if success_rate >= 99 else '⚠️ MARGINAL' if success_rate >= 95 else '❌ FAIL'}
                                    </span>
                                </td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center; font-weight: 600;">{scores.get('availability', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">Avg Response Time</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{avg_response:.1f} sec</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">&lt;{targets.get('response_time', 2000)/1000:.0f} sec</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {'badge-success' if avg_response < 2 else 'badge-warning' if avg_response < 5 else 'badge-danger'}">
                                        {'✅ PASS' if avg_response < 2 else '⚠️ MARGINAL' if avg_response < 5 else '❌ FAIL'}
                                    </span>
                                </td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center; font-weight: 600;">{scores.get('response_time', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">Error Rate</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{error_rate:.2f}%</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">&lt;{targets.get('error_rate', 1)}%</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {'badge-success' if error_rate < 1 else 'badge-warning' if error_rate < 3 else 'badge-danger'}">
                                        {'✅ PASS' if error_rate < 1 else '⚠️ MARGINAL' if error_rate < 3 else '❌ FAIL'}
                                    </span>
                                </td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center; font-weight: 600;">{scores.get('error_rate', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">Throughput</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{throughput:.1f}/s</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{targets.get('throughput', 100)}/s</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {'badge-success' if throughput >= 100 else 'badge-warning'}">
                                        {'✅ PASS' if throughput >= 100 else '⚠️ ACCEPTABLE'}
                                    </span>
                                </td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center; font-weight: 600;">{scores.get('throughput', 0):.0f}/100</td>
                            </tr>
                            <tr>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); font-weight: 600;">95th Percentile</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">{p95_response:.1f} sec</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">&lt;{targets.get('p95_percentile', 3000)/1000:.0f} sec</td>
                                <td style="padding: 1rem; border: 1px solid var(--border-color); text-align: center;">
                                    <span class="status-badge {'badge-success' if p95_response < 3 else 'badge-warning' if p95_response < 10 else 'badge-danger'}">
                                        {'✅ PASS' if p95_response < 3 else '⚠️ MARGINAL' if p95_response < 10 else '❌ FAIL'}
                                    </span>
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

            <!-- Performance Grading Scale & Methodology -->
            <div style="background: var(--background-light); padding: 1.5rem; border-radius: 8px; margin: 2rem 0;">
                <h3>📏 Performance Grading Scale & Methodology</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 1rem; margin: 1rem 0;">
                    <div style="background: #dcfce7; padding: 1rem; border-radius: 6px; border-left: 4px solid #16a34a;">
                        <strong>A+ (90-100):</strong> Exceptional<br>
                        <small>Industry leading performance</small>
                    </div>
                    <div style="background: #f0fdf4; padding: 1rem; border-radius: 6px; border-left: 4px solid #22c55e;">
                        <strong>A (80-89):</strong> Excellent<br>
                        <small>Exceeds industry standards</small>
                    </div>
                    <div style="background: #fefce8; padding: 1rem; border-radius: 6px; border-left: 4px solid #eab308;">
                        <strong>B+ (75-79):</strong> Good<br>
                        <small>Meets industry standards</small>
                    </div>
                    <div style="background: #fffbeb; padding: 1rem; border-radius: 6px; border-left: 4px solid #f59e0b;">
                        <strong>B (70-74):</strong> Acceptable<br>
                        <small>Minor improvements needed</small>
                    </div>
                    <div style="background: #fef3c7; padding: 1rem; border-radius: 6px; border-left: 4px solid #d97706;">
                        <strong>C+ (65-69):</strong> Marginal{'← CURRENT' if grade == 'C+' else ''}<br>
                        <small>Significant issues present</small>
                    </div>
                    <div style="background: #fee2e2; padding: 1rem; border-radius: 6px; border-left: 4px solid #dc2626;">
                        <strong>D (50-59):</strong> Critical<br>
                        <small>Immediate action required</small>
                    </div>
                </div>
                
                <div style="background: white; padding: 1.5rem; border-radius: 8px; border: 2px solid var(--primary-color); margin: 1rem 0;">
                    <h4 style="color: var(--primary-color); margin: 0 0 1rem 0;">🔍 Why This Scorecard Matters</h4>
                    <p style="margin: 0.5rem 0;"><strong>Weighted Scoring:</strong> Each metric is weighted based on business impact - Performance (30%), Reliability (25%), User Experience (25%), Scalability (20%)</p>
                    <p style="margin: 0.5rem 0;"><strong>Industry Benchmarks:</strong> Targets based on enterprise SaaS standards and user experience research</p>
                    <p style="margin: 0.5rem 0;"><strong>Business Impact:</strong> Current grade indicates performance state and required actions</p>
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
                        <td style="padding: 0.75rem; border-bottom: 1px solid #e2e8f0;">{filename}</td>
                        <td style="padding: 0.75rem; text-align: center; border-bottom: 1px solid #e2e8f0;">{samples:,}</td>
                        <td style="padding: 0.75rem; text-align: center; border-bottom: 1px solid #e2e8f0;">{errors:,}</td>
                        <td style="padding: 0.75rem; text-align: center; border-bottom: 1px solid #e2e8f0;">{error_rate:.2f}%</td>
                        <td style="padding: 0.75rem; text-align: center; border-bottom: 1px solid #e2e8f0;">{throughput:.2f}</td>
                    </tr>
            '''
        
        return f'''
        <div class="section">
            <h2>📁 Consolidated Files Analysis</h2>
            <div style="background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-left: 4px solid #0ea5e9; padding: 1.5rem; border-radius: 8px; margin-bottom: 1.5rem;">
                <p style="margin: 0; font-size: 1rem; line-height: 1.6; color: var(--text-primary);">
                    This report consolidates analysis from <strong>{len(files_to_display)} file(s)</strong>. 
                    All metrics, graphs, and findings below represent the combined performance data from all files.
                </p>
            </div>
            
            <table class="endpoint-table" style="width: 100%; border-collapse: collapse; margin-top: 1rem;">
                <thead>
                    <tr style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white;">
                        <th style="padding: 0.75rem; text-align: left; font-weight: 600;">File Name</th>
                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Samples</th>
                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Errors</th>
                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Error Rate</th>
                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Throughput (req/s)</th>
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
        <div class="section">
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
    def _generate_performance_tables(transaction_stats: dict, request_stats: dict) -> str:
        """Generate performance summary tables for transactions and requests"""
        
        def generate_table(stats: dict, title: str) -> str:
            if not stats:
                return f"<p><em>No {title.lower()} data available</em></p>"
            
            # Sort by average response time (slowest first)
            sorted_stats = sorted(stats.items(), key=lambda x: x[1].get('avg_response', 0) or 0, reverse=True)
            
            rows = ""
            for label, data in sorted_stats[:15]:  # Top 15
                min_resp = data.get('min', 0) or 0
                avg_resp = data.get('avg_response', 0) or 0
                median = data.get('median', 0) or 0
                p75 = data.get('p75', 0) or 0
                p90 = data.get('p90', 0) or 0
                p95 = data.get('p95', 0) or 0
                max_resp = data.get('max', 0) or 0
                error_rate = data.get('error_rate', 0) or 0
                count = data.get('count', 0) or 0
                
                # Convert to seconds for color coding
                min_sec = min_resp / 1000
                avg_sec = avg_resp / 1000
                median_sec = median / 1000
                p75_sec = p75 / 1000
                p90_sec = p90 / 1000
                p95_sec = p95 / 1000
                max_sec = max_resp / 1000
                
                # Get styles for each metric
                min_style = HTMLReportGenerator._get_cell_style(min_sec)
                avg_style = HTMLReportGenerator._get_cell_style(avg_sec)
                median_style = HTMLReportGenerator._get_cell_style(median_sec)
                p75_style = HTMLReportGenerator._get_cell_style(p75_sec)
                p90_style = HTMLReportGenerator._get_cell_style(p90_sec)
                p95_style = HTMLReportGenerator._get_cell_style(p95_sec)
                max_style = HTMLReportGenerator._get_cell_style(max_sec)
                error_style = HTMLReportGenerator._get_cell_style(error_rate, 'error_rate')
                
                rows += f'''
                <tr>
                    <td style="font-weight: 600;">{label}</td>
                    <td style="text-align: center; {min_style}">{min_sec:.2f}s</td>
                    <td style="text-align: center; {avg_style}"><strong>{avg_sec:.2f}s</strong></td>
                    <td style="text-align: center; {median_style}">{median_sec:.2f}s</td>
                    <td style="text-align: center; {p75_style}">{p75_sec:.2f}s</td>
                    <td style="text-align: center; {p90_style}">{p90_sec:.2f}s</td>
                    <td style="text-align: center; {p95_style}">{p95_sec:.2f}s</td>
                    <td style="text-align: center; {max_style}">{max_sec:.2f}s</td>
                    <td style="text-align: center;">{count:,}</td>
                    <td style="text-align: center; {error_style}">{error_rate:.2f}%</td>
                </tr>'''
            
            return f'''
            <h3>{title}</h3>
            <div style="margin-bottom: 1rem; padding: 1rem; background: var(--background-light); border-radius: 8px; font-size: 0.9rem;">
                <strong>Color Coding:</strong> 
                <span style="color: #059669;">Green</span> = Within SLA (Response Time &lt; 2s, Error Rate &lt; 1%), 
                <span style="color: #d97706;">Yellow</span> = Warning (Response Time 2-5s, Error Rate 1-5%), 
                <span style="color: #dc2626;">Red</span> = Violating SLA (Response Time &gt; 5s, Error Rate &gt; 5%)
            </div>
            <div style="overflow-x: auto;">
                <table class="endpoint-table">
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
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
            </div>'''
        
        return f'''
        <div class="section">
            <h2>📊 Performance Summary</h2>
            {generate_table(transaction_stats, "📋 Transaction Performance")}
            <div style="margin-top: 2rem;"></div>
            {generate_table(request_stats, "🔗 API Request Performance")}
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
    def _generate_graph_data_table(time_series_data: List[dict] = None) -> str:
        """Generate HTML for graph data table"""
        if not time_series_data or len(time_series_data) == 0:
            return '<p style="color: var(--text-secondary); font-size: 0.9rem;">No time-series data available</p>'
        
        # Sample data points for table (show every Nth point to keep table manageable)
        sample_rate = max(1, len(time_series_data) // 20)  # Show ~20 rows max
        sampled_data = time_series_data[::sample_rate]
        
        table_rows = ''
        for d in sampled_data[:20]:  # Limit to 20 rows
            time_formatted = HTMLReportGenerator._format_time_hhmmss(d['time'])
            table_rows += f'''
            <tr>
                <td style="padding: 0.5rem; text-align: center;">{time_formatted}</td>
                <td style="padding: 0.5rem; text-align: center;">{d['avg_response_time']:.2f}s</td>
                <td style="padding: 0.5rem; text-align: center;">{d['vusers']:.0f}</td>
                <td style="padding: 0.5rem; text-align: center;">{d['throughput']:.2f}</td>
            </tr>
            '''
        
        return f'''
            <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                <div style="overflow-y: auto; max-height: 500px;">
                    <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                        <thead style="position: sticky; top: 0; z-index: 10;">
                            <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Time</th>
                                <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Avg Response Time (s)</th>
                                <th style="padding: 0.75rem; text-align: center; font-weight: 600;">VUsers</th>
                                <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Throughput (req/s)</th>
                            </tr>
                        </thead>
                        <tbody>
                            {table_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        '''
    
    @staticmethod
    def _generate_graph_analysis_html(graph_analysis: Dict[str, Any], time_series_data: List[dict] = None) -> str:
        """Generate HTML for unified graph understanding and performance analysis section"""
        
        # Get unified understanding from distribution analysis
        distribution_analysis = graph_analysis.get('distribution_analysis', {})
        unified_understanding = distribution_analysis.get('unified_understanding', '')
        stats = distribution_analysis.get('statistics', {})
        business_answers = distribution_analysis.get('business_answers', {})
        dist_type = distribution_analysis.get('distribution_type', 'unknown')
        
        # If unified understanding is not available, generate it from graph pattern analysis
        if not unified_understanding:
            analysis_text = graph_analysis.get('analysis', 'Analysis not available.')
            # Use first part of analysis as fallback
            sentences = analysis_text.split('. ')
            unified_understanding = '. '.join(sentences[:3]) + '.' if len(sentences) >= 3 else analysis_text
        
        # Generate statistical summary HTML
        stats_html = HTMLReportGenerator._generate_distribution_stats_html(stats) if stats else ''
        
        # Generate business answers HTML (compact version)
        business_answers_html = ''
        if business_answers:
            business_answers_html = HTMLReportGenerator._generate_business_answers_html(business_answers)
        
        # Distribution type badge color
        dist_badge_colors = {
            'normal': '#10b981',  # green
            'right_skewed': '#f59e0b',  # amber
            'left_skewed': '#ef4444',  # red
            'multi_modal': '#8b5cf6',  # purple
            'high_variance': '#f97316',  # orange
        }
        badge_color = dist_badge_colors.get(dist_type, '#6b7280')
        
        return f'''
            <div style="margin-bottom: 2rem;">
                <div style="padding: 2rem; background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%); border-radius: 8px; border: 2px solid #e5e7eb; box-shadow: 0 2px 8px rgba(0,0,0,0.05);">
                    <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.5rem;">
                        <h3 style="margin: 0; color: var(--text-primary); font-size: 1.3rem; font-weight: 600;">📊 Graph Understanding and Performance Analysis</h3>
                        {f'<span style="padding: 0.5rem 1rem; background: {badge_color}; color: white; border-radius: 12px; font-size: 0.85rem; font-weight: 600; text-transform: uppercase;">{dist_type.replace("_", " ")}</span>' if dist_type != 'unknown' else ''}
                    </div>
                    
                    <!-- Unified Understanding -->
                    <div style="padding: 1.5rem; background: white; border-radius: 6px; border-left: 4px solid {badge_color}; margin-bottom: 1.5rem;">
                        <p style="margin: 0; color: var(--text-primary); font-size: 1rem; line-height: 1.8; text-align: justify;">
                            {unified_understanding}
                        </p>
                    </div>
                    
                    <!-- Statistical Summary -->
                    {stats_html}
                    
                </div>
            </div>
        '''
    
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
        
        # Collect all unique transaction/request labels
        all_labels = set()
        for d in time_series_data:
            by_label = d.get('by_label', {})
            all_labels.update(by_label.keys())
        
        # Combine transaction and request stats to get all labels
        all_labels.update(transaction_stats.keys())
        all_labels.update(request_stats.keys())
        all_labels = sorted(list(all_labels))  # Sort for consistent ordering
        
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
            # Extract response time data for this label over time as scatter points
            label_scatter_data = []
            for d in time_series_data:
                by_label = d.get('by_label', {})
                label_data = by_label.get(label, {})
                label_scatter_data.append({
                    'x': d['time'],
                    'y': label_data.get('avg_response_time', 0.0)
                })
            
            color = colors[idx % len(colors)]
            label_colors[label] = color
            datasets.append({
                'label': label,
                'data': label_scatter_data,
                'borderColor': color,
                'backgroundColor': color,
                'yAxisID': 'y',
                'pointRadius': 4,
                'pointHoverRadius': 6,
                'showLine': False
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
        table_rows = ''
        for d in sampled_data:
            time_str = HTMLReportGenerator._format_time_hhmmss(d['time'])
            by_label = d.get('by_label', {})
            
            # Build row with time, then each transaction value, then threads
            row_cells = f'<td style="padding: 0.5rem; text-align: center;">{time_str}</td>'
            for label in all_labels:
                label_data = by_label.get(label, {})
                rt = label_data.get('avg_response_time', 0.0)
                row_cells += f'<td style="padding: 0.5rem; text-align: center;">{rt:.2f}s</td>'
            row_cells += f'<td style="padding: 0.5rem; text-align: center;">{d["vusers"]:.0f}</td>'
            
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
        
        # Collect all unique transaction/request labels
        all_labels = set()
        for d in time_series_data:
            by_label = d.get('by_label', {})
            all_labels.update(by_label.keys())
        
        # Combine transaction and request stats to get all labels
        all_labels.update(transaction_stats.keys())
        all_labels.update(request_stats.keys())
        all_labels = sorted(list(all_labels))  # Sort for consistent ordering
        
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
            # Extract throughput data for this label over time as scatter points
            label_scatter_data = []
            for d in time_series_data:
                by_label = d.get('by_label', {})
                label_data = by_label.get(label, {})
                label_scatter_data.append({
                    'x': d['time'],
                    'y': label_data.get('throughput', 0.0)
                })
            
            color = colors[idx % len(colors)]
            label_colors[label] = color
            datasets.append({
                'label': label,
                'data': label_scatter_data,
                'borderColor': color,
                'backgroundColor': color,
                'yAxisID': 'y',
                'pointRadius': 4,
                'pointHoverRadius': 6,
                'showLine': False
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
        table_rows = ''
        for d in sampled_data:
            time_str = HTMLReportGenerator._format_time_hhmmss(d['time'])
            by_label = d.get('by_label', {})
            
            # Build row with time, then each transaction value, then threads
            row_cells = f'<td style="padding: 0.5rem; text-align: center;">{time_str}</td>'
            for label in all_labels:
                label_data = by_label.get(label, {})
                tp = label_data.get('throughput', 0.0)
                row_cells += f'<td style="padding: 0.5rem; text-align: center;">{tp:.2f}</td>'
            row_cells += f'<td style="padding: 0.5rem; text-align: center;">{d["vusers"]:.0f}</td>'
            
            table_rows += f'<tr>{row_cells}</tr>'
        
        # Generate observation
        table_data = [{'time': d['time'], 'throughput': d['throughput']} for d in sampled_data]
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "throughput_by_transaction")
        
        time_labels_json = json.dumps(time_labels)
        vusers_scatter_json = json.dumps([{'x': d['time'], 'y': d['vusers']} for d in time_series_data])
        datasets_json = json.dumps(datasets)
        
        return f'''
        <div class="section">
            <h2>📈 Throughput Over Time by Transaction vs VUsers</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Throughput trends for transactions/requests over time compared with virtual user load.
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
                            title: {{ display: true, text: 'Throughput (req/s)' }},
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
        """Graph 5: Error Analysis By Description over time and on threads with 50/50 layout"""
        # Extract error information from metrics
        response_codes = metrics.get('response_codes', {})
        error_codes = {k: v for k, v in response_codes.items() if str(k).startswith(('4', '5'))}
        
        if not error_codes:
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
        
        error_labels = list(error_codes.keys())
        error_counts = list(error_codes.values())
        
        # Prepare data for table
        table_rows = ''.join([f'''
            <tr>
                <td style="padding: 0.5rem; text-align: center;">{code}</td>
                <td style="padding: 0.5rem; text-align: center;">{count}</td>
                <td style="padding: 0.5rem; text-align: center;">{"Client Error" if str(code).startswith("4") else "Server Error"}</td>
            </tr>''' for code, count in zip(error_labels, error_counts)])
        
        # Generate observation
        table_data = [{'code': code, 'count': count} for code, count in zip(error_labels, error_counts)]
        observation = HTMLReportGenerator._generate_graph_observation(table_data, "error_analysis")
        
        error_labels_json = json.dumps([f"Error {code}" for code in error_labels])
        error_counts_json = json.dumps(error_counts)
        
        return f'''
        <div class="section">
            <h2>📈 Error Analysis By Description</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                Error distribution by response code showing frequency of different error types.
            </p>
            
            <!-- Graph and Data Table Side by Side (50/50) -->
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
                <!-- Left: Graph (50%) -->
                <div class="chart-container" style="height: 400px;">
                    <canvas id="errorAnalysisChart"></canvas>
                </div>
                
                <!-- Right: Graph Data Table (50%) -->
                <div style="padding: 1rem; background: var(--background-light); border-radius: 8px;">
                    <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.1rem;">📊 Graph Data</h4>
                    <div style="background: white; border-radius: 6px; overflow: hidden; position: relative;">
                        <div style="overflow-y: auto; max-height: 350px;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 0.85rem;">
                                <thead style="position: sticky; top: 0; z-index: 10;">
                                    <tr style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white;">
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Error Code</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Count</th>
                                        <th style="padding: 0.75rem; text-align: center; font-weight: 600;">Type</th>
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
    def _generate_distribution_stats_html(stats: Dict[str, Any]) -> str:
        """Generate HTML for distribution statistics"""
        if not stats:
            return ''
        
        return f'''
            <div style="margin-top: 1rem; padding: 1rem; background: white; border-radius: 6px; border: 1px solid #e5e7eb;">
                <h5 style="margin: 0 0 0.75rem 0; color: var(--text-primary); font-size: 0.95rem; font-weight: 600;">Statistical Summary</h5>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; font-size: 0.85rem;">
                    <div><strong>Mean:</strong> {stats.get('mean', 0):.2f}s</div>
                    <div><strong>Median:</strong> {stats.get('median', 0):.2f}s</div>
                    <div><strong>Std Deviation:</strong> {stats.get('std_deviation', 0):.2f}s</div>
                    <div><strong>Variance:</strong> {stats.get('variance', 0):.2f}</div>
                    <div><strong>Coefficient of Variation:</strong> {stats.get('coefficient_of_variation', 0):.2%}</div>
                    <div><strong>Skewness:</strong> {stats.get('skewness', 0):.2f}</div>
                </div>
            </div>
        '''
    
    @staticmethod
    def _generate_business_answers_html(business_answers: Dict[str, Dict[str, Any]]) -> str:
        """Generate HTML for business questions answers"""
        if not business_answers:
            return ''
        
        # Answer color mapping
        answer_colors = {
            'YES': '#10b981',  # green
            'MOSTLY': '#f59e0b',  # amber
            'PARTIALLY': '#f59e0b',  # amber
            'NO': '#ef4444',  # red
            'VARIABLE': '#8b5cf6',  # purple
            'MINIMAL': '#10b981',  # green
        }
        
        # Question labels
        question_labels = {
            'stability': '1. System is Stable and Well Balanced',
            'resource_sufficiency': '2. Current Resources (CPU, Memory, Threads, DB connections) are Sufficient',
            'contention': '3. Contention or Queuing Issues',
            'bottlenecks': '4. Occasional Bottlenecks'
        }
        
        questions_html = ''
        for key, label in question_labels.items():
            if key in business_answers:
                answer_data = business_answers[key]
                answer = answer_data.get('answer', 'UNKNOWN')
                confidence = answer_data.get('confidence', 'Medium')
                explanation = answer_data.get('explanation', '')
                
                answer_color = answer_colors.get(answer, '#6b7280')
                if answer.startswith('YES'):
                    answer_color = '#10b981' if answer == 'YES' else '#f59e0b'
                elif answer.startswith('NO'):
                    answer_color = '#ef4444'
                
                questions_html += f'''
                    <div style="margin-top: 0.75rem; padding: 0.75rem; background: white; border-radius: 6px; border-left: 3px solid {answer_color};">
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.4rem;">
                            <h5 style="margin: 0; color: var(--text-primary); font-size: 0.9rem; font-weight: 600;">{label}</h5>
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
        
        return f'''
            <div style="margin-top: 1.5rem; padding: 1.5rem; background: linear-gradient(135deg, #f3f4f6 0%, #ffffff 100%); border-radius: 8px; border: 2px solid #e5e7eb;">
                <h4 style="margin: 0 0 1rem 0; color: var(--text-primary); font-size: 1.05rem; font-weight: 600;">🎯 System Health Assessment</h4>
                {questions_html}
            </div>
        '''
    
    @staticmethod
    def _analyze_system_performance(time_series_data: List[dict]) -> dict:
        """Analyze time-series data and generate performance insights based on correlations"""
        if not time_series_data or len(time_series_data) < 2:
            return {
                "performance_status": "Insufficient Data",
                "insights": ["Not enough data points for analysis"],
                "correlations": {},
                "recommendations": []
            }
        
        # Extract metrics
        response_times = [d['avg_response_time'] for d in time_series_data]
        vusers = [d['vusers'] for d in time_series_data]
        throughput = [d['throughput'] for d in time_series_data]
        
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
        
        # Calculate correlations (simple linear correlation)
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
        
        # Analyze trends
        response_trend = "Increasing" if response_times[-1] > response_times[0] * 1.1 else "Decreasing" if response_times[-1] < response_times[0] * 0.9 else "Stable"
        throughput_trend = "Increasing" if throughput[-1] > throughput[0] * 1.1 else "Decreasing" if throughput[-1] < throughput[0] * 0.9 else "Stable"
        
        # Generate insights
        insights = []
        performance_status = "Good"
        recommendations = []
        
        # Response time analysis
        if avg_response < 2.0:
            insights.append(f"✅ <strong>Excellent Response Time:</strong> Average response time is {avg_response:.2f}s, which is well within acceptable limits (< 2s).")
        elif avg_response < 5.0:
            insights.append(f"⚠️ <strong>Moderate Response Time:</strong> Average response time is {avg_response:.2f}s. While acceptable, there's room for improvement.")
            performance_status = "Moderate"
        else:
            insights.append(f"❌ <strong>Poor Response Time:</strong> Average response time is {avg_response:.2f}s, which exceeds acceptable thresholds. Performance optimization is needed.")
            performance_status = "Poor"
        
        # Response time stability
        if response_stability == "Stable":
            insights.append(f"✅ <strong>Stable Performance:</strong> Response times remain consistent throughout the test, indicating good system stability.")
        else:
            insights.append(f"⚠️ <strong>Variable Performance:</strong> Response times fluctuate significantly (variance: {response_variance:.2f}), suggesting inconsistent system behavior.")
            if performance_status == "Good":
                performance_status = "Moderate"
        
        # Throughput analysis
        if avg_throughput > 100:
            insights.append(f"✅ <strong>High Throughput:</strong> System processes {avg_throughput:.1f} requests/second on average, indicating good capacity.")
        elif avg_throughput > 50:
            insights.append(f"⚠️ <strong>Moderate Throughput:</strong> System processes {avg_throughput:.1f} requests/second. Consider optimization for higher loads.")
        else:
            insights.append(f"❌ <strong>Low Throughput:</strong> System processes only {avg_throughput:.1f} requests/second, which may limit scalability.")
            if performance_status != "Poor":
                performance_status = "Moderate"
        
        # Correlation analysis
        if corr_response_vusers > 0.7:
            insights.append(f"⚠️ <strong>High Correlation (Response Time ↔ VUsers):</strong> Response time increases significantly as user load increases (correlation: {corr_response_vusers:.2f}). This suggests the system is reaching capacity limits.")
            recommendations.append("Consider horizontal scaling or performance optimization to handle increased user load.")
            if performance_status == "Good":
                performance_status = "Moderate"
        elif corr_response_vusers > 0.3:
            insights.append(f"ℹ️ <strong>Moderate Correlation (Response Time ↔ VUsers):</strong> Response time shows some dependency on user load (correlation: {corr_response_vusers:.2f}).")
        else:
            insights.append(f"✅ <strong>Low Correlation (Response Time ↔ VUsers):</strong> Response time remains relatively stable regardless of user load (correlation: {corr_response_vusers:.2f}), indicating good scalability.")
        
        if corr_response_throughput < -0.5:
            insights.append(f"❌ <strong>Negative Correlation (Response Time ↔ Throughput):</strong> As throughput increases, response time decreases (correlation: {corr_response_throughput:.2f}), which is unusual and may indicate data quality issues.")
        elif corr_response_throughput > 0.5:
            insights.append(f"⚠️ <strong>Positive Correlation (Response Time ↔ Throughput):</strong> Higher throughput correlates with higher response times (correlation: {corr_response_throughput:.2f}), suggesting system stress under load.")
            if performance_status == "Good":
                performance_status = "Moderate"
        else:
            insights.append(f"✅ <strong>Low Correlation (Response Time ↔ Throughput):</strong> Response time is independent of throughput (correlation: {corr_response_throughput:.2f}), indicating efficient request processing.")
        
        if corr_vusers_throughput > 0.7:
            insights.append(f"✅ <strong>Strong Correlation (VUsers ↔ Throughput):</strong> Throughput scales well with user load (correlation: {corr_vusers_throughput:.2f}), showing good system scalability.")
        elif corr_vusers_throughput < 0.3:
            insights.append(f"⚠️ <strong>Weak Correlation (VUsers ↔ Throughput):</strong> Throughput doesn't scale proportionally with user load (correlation: {corr_vusers_throughput:.2f}), which may indicate bottlenecks.")
            recommendations.append("Investigate system bottlenecks that prevent throughput from scaling with user load.")
        
        # Trend analysis
        if response_trend == "Increasing" and max_response > avg_response * 1.5:
            insights.append(f"⚠️ <strong>Degrading Performance:</strong> Response time shows an increasing trend, with peak values reaching {max_response:.2f}s. System performance is degrading over time.")
            recommendations.append("Investigate memory leaks, resource exhaustion, or database connection pool issues.")
            if performance_status != "Poor":
                performance_status = "Moderate"
        
        if throughput_trend == "Decreasing":
            insights.append(f"❌ <strong>Declining Throughput:</strong> System throughput is decreasing over time, indicating potential resource exhaustion or bottlenecks.")
            recommendations.append("Check for resource leaks, database connection issues, or server capacity limits.")
            performance_status = "Poor"
        
        # Overall assessment
        if performance_status == "Good":
            insights.append(f"✅ <strong>Overall Assessment:</strong> System demonstrates excellent performance with stable response times, good throughput, and healthy correlations between metrics.")
        elif performance_status == "Moderate":
            insights.append(f"⚠️ <strong>Overall Assessment:</strong> System performance is acceptable but shows areas for improvement. Monitor closely and consider optimizations.")
        else:
            insights.append(f"❌ <strong>Overall Assessment:</strong> System performance requires immediate attention. Critical issues identified that impact user experience.")
        
        return {
            "performance_status": performance_status,
            "insights": insights,
            "correlations": {
                "response_vusers": round(corr_response_vusers, 3),
                "response_throughput": round(corr_response_throughput, 3),
                "vusers_throughput": round(corr_vusers_throughput, 3)
            },
            "statistics": {
                "avg_response": round(avg_response, 2),
                "max_response": round(max_response, 2),
                "avg_throughput": round(avg_throughput, 2),
                "max_throughput": round(max_throughput, 2),
                "avg_vusers": round(avg_vusers, 1),
                "max_vusers": round(max_vusers, 1)
            },
            "recommendations": recommendations
        }
    
    @staticmethod
    def _generate_system_behaviour_graph(time_series_data: List[dict], progress_callback=None) -> str:
        """Generate Overall System Behaviour graph with dual Y-axes"""
        if not time_series_data:
            return '''
        <div class="section">
            <h2>📈 Overall System Behaviour</h2>
            <p><em>Time-series data not available for this test.</em></p>
        </div>'''
        
        def update_progress(percent: int, message: str):
            if progress_callback:
                try:
                    progress_callback(percent, message)
                except:
                    pass
        
        # Optimize: Sample data if too large (max 500 points for analysis)
        # This prevents GraphAnalyzer from hanging on large datasets
        original_count = len(time_series_data)
        if original_count > 500:
            # Sample every Nth point to get ~500 points
            sample_rate = max(1, original_count // 500)
            sampled_data = time_series_data[::sample_rate]
            print(f"  Sampling time_series_data: {original_count:,} -> {len(sampled_data):,} points for analysis")
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
            
            # Run GraphAnalyzer in a thread with 20 second timeout
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(GraphAnalyzer.analyze_graph_patterns, sampled_data)
                try:
                    graph_analysis = future.result(timeout=20)
                    print(f"  GraphAnalyzer completed")
                except FutureTimeoutError:
                    print(f"  ⚠️ GraphAnalyzer timed out after 20 seconds, using fallback")
                    future.cancel()
                    graph_analysis = {
                        "analysis": "Graph analysis timed out - using simplified analysis.",
                        "test_type": "Unknown",
                        "disturbances": [],
                        "stability": "Unknown",
                        "capacity_assessment": "Unknown"
                    }
        except Exception as e:
            print(f"  ⚠️ GraphAnalyzer failed: {e}, using fallback")
            import traceback
            traceback.print_exc()
            # Use fallback analysis
            graph_analysis = {
                "analysis": f"Graph analysis unavailable: {str(e)}",
                "test_type": "Unknown",
                "disturbances": [],
                "stability": "Unknown",
                "capacity_assessment": "Unknown"
            }
        
        update_progress(80, "Preparing graph data...")
        
        # Prepare data for JavaScript
        time_labels = [HTMLReportGenerator._format_time_hhmmss(d['time']) for d in time_series_data]
        avg_response_times = [d['avg_response_time'] for d in time_series_data]
        vusers = [d['vusers'] for d in time_series_data]
        throughput = [d['throughput'] for d in time_series_data]
        
        # Format as JSON for JavaScript
        time_labels_json = json.dumps(time_labels)
        avg_response_times_json = json.dumps(avg_response_times)
        vusers_json = json.dumps(vusers)
        throughput_json = json.dumps(throughput)
        
        # Generate graph data table HTML
        table_html = HTMLReportGenerator._generate_graph_data_table(time_series_data)
        
        return f'''
        <div class="section">
            <h2>📈 Overall System Behaviour</h2>
            <p style="margin-bottom: 1rem; color: var(--text-secondary);">
                System performance metrics over time showing how response time, throughput, and user load interact during the test.
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
            const throughput = {throughput_json};
            
            // Calculate max values for scaling
            const maxResponse = Math.max(...avgResponseTimes, 1);
            const maxThroughput = Math.max(...throughput, 1);
            
            new Chart(ctx, {{
                type: 'line',
                data: {{
                    labels: timeLabels,
                    datasets: [{{
                        label: 'Avg Response Time (s)',
                        data: avgResponseTimes,
                        borderColor: 'rgba(37, 99, 235, 1)',
                        backgroundColor: 'rgba(37, 99, 235, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y',
                        pointRadius: 2,
                        pointHoverRadius: 4
                    }}, {{
                        label: 'VUsers',
                        data: vusers,
                        borderColor: 'rgba(245, 158, 11, 1)',
                        backgroundColor: 'rgba(245, 158, 11, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        yAxisID: 'y',
                        pointRadius: 2,
                        pointHoverRadius: 4,
                        borderDash: [5, 5]
                    }}, {{
                        label: 'Throughput (req/s)',
                        data: throughput,
                        borderColor: 'rgba(16, 185, 129, 1)',
                        backgroundColor: 'rgba(16, 185, 129, 0.1)',
                        borderWidth: 2,
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
                    interaction: {{
                        mode: 'index',
                        intersect: false
                    }},
                    plugins: {{
                        legend: {{
                            display: true,
                            position: 'top',
                            labels: {{
                                font: {{ size: 12 }},
                                usePointStyle: true,
                                padding: 15
                            }}
                        }},
                        title: {{
                            display: true,
                            text: 'Average Response Time vs VUsers vs Throughput Over Time',
                            font: {{ size: 18, weight: 'bold' }},
                            padding: {{ bottom: 20 }}
                        }},
                        datalabels: {{
                            display: false
                        }},
                        tooltip: {{
                            callbacks: {{
                                label: function(context) {{
                                    let label = context.dataset.label || '';
                                    if (label) {{
                                        label += ': ';
                                    }}
                                    if (context.dataset.label.includes('Response Time')) {{
                                        label += context.parsed.y.toFixed(2) + 's';
                                    }} else if (context.dataset.label.includes('Throughput')) {{
                                        label += context.parsed.y.toFixed(2) + ' req/s';
                                    }} else if (context.dataset.label.includes('VUsers')) {{
                                        label += Math.round(context.parsed.y) + ' users';
                                    }} else {{
                                        label += Math.round(context.parsed.y);
                                    }}
                                    return label;
                                }}
                            }}
                        }}
                    }},
                    scales: {{
                        x: {{
                            title: {{
                                display: true,
                                text: 'Time (seconds)',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            grid: {{
                                display: true,
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }},
                        y: {{
                            type: 'linear',
                            position: 'left',
                            title: {{
                                display: true,
                                text: 'Response Time (s) / VUsers',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            beginAtZero: true,
                            max: Math.max(maxResponse * 1.1, 10),
                            grid: {{
                                display: true,
                                color: 'rgba(0, 0, 0, 0.05)'
                            }}
                        }},
                        y1: {{
                            type: 'linear',
                            position: 'right',
                            title: {{
                                display: true,
                                text: 'Throughput (req/s)',
                                font: {{ size: 14, weight: 'bold' }}
                            }},
                            beginAtZero: true,
                            max: Math.max(maxThroughput * 1.1, 10),
                            grid: {{
                                drawOnChartArea: false
                            }}
                        }}
                    }}
                }}
            }});
        }});
        </script>'''
    
    @staticmethod
    def _generate_critical_issues(issues: List[dict]) -> str:
        """Generate critical issues section in tabular format"""
        if not issues:
            return '''
        <div class="section">
            <h2>🔴 Critical Issues</h2>
            <div class="alert alert-success">
                <strong>✅ NO CRITICAL ISSUES IDENTIFIED:</strong> The system is performing well with no major concerns.
            </div>
        </div>'''
        
        # Generate table rows
        table_rows = ""
        for i, issue in enumerate(issues, 1):
            title = issue.get('title', 'Unknown Issue')
            impact = issue.get('impact', 'N/A')
            affected = issue.get('affected', 'N/A')
            example = issue.get('example', affected)  # Use affected as example if example not provided
            recommendation = issue.get('recommendation', issue.get('fix', 'Review and address the issue'))
            business_benefit = issue.get('business_benefit', 'Improved system reliability and user experience')
            
            table_rows += f'''
            <tr>
                <td style="padding: 1rem; font-weight: 600; color: var(--text-primary);">{title}</td>
                <td style="padding: 1rem; color: var(--text-secondary);">{example}</td>
                <td style="padding: 1rem; color: var(--text-secondary);">{impact}</td>
                <td style="padding: 1rem; color: var(--text-secondary);">{recommendation}</td>
                <td style="padding: 1rem; color: var(--text-secondary);">{business_benefit}</td>
            </tr>'''
        
        return f'''
        <div class="section">
            <h2>🔴 Critical Issues</h2>
            <div class="alert alert-danger">
                <strong>IMMEDIATE ACTION REQUIRED:</strong> {len(issues)} critical issue{'s' if len(issues) > 1 else ''} {'are' if len(issues) > 1 else 'is'} severely impacting business operations and user experience.
            </div>
            
            <div style="overflow-x: auto; margin-top: 1.5rem;">
                <table class="endpoint-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%); color: white;">
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Issue</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Example of Issue</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Impact</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Recommendation</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Business Benefit</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_business_impact(error_rate: float, avg_response: float) -> str:
        """Generate business impact assessment"""
        return f'''
        <div class="section">
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
                        <li><strong>{'Poor' if avg_response > 5 else 'Moderate'} Performance ({avg_response:.1f}s avg):</strong> {'Significant' if avg_response > 5 else 'Moderate'} productivity loss affecting user efficiency</li>
                        <li><strong>Support Overhead:</strong> {'Increased' if error_rate > 3 else 'Moderate'} operational costs due to performance issues</li>
                        <li><strong>User Abandonment Risk:</strong> {'High' if avg_response > 5 else 'Medium'} opportunity cost from customer dissatisfaction</li>
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
    def _generate_action_plan(roadmap: List[dict], current_grade: str) -> str:
        """Generate recommended action plan in tabular format"""
        if not roadmap:
            return f'''
        <div class="section">
            <h2>🚀 Recommended Action Plan</h2>
            <p>No specific action plan generated. Consider standard performance optimization strategies.</p>
        </div>'''
        
        # Generate table rows
        table_rows = ""
        for i, phase in enumerate(roadmap, 1):
            phase_name = phase.get('phase', f'Phase {i}')
            target_grade = phase.get('target_grade', 'N/A')
            improvements = phase.get('improvements', [])
            actions = '; '.join(improvements) if improvements else 'Review and optimize system performance'
            expected_impact = phase.get('expected_impact', 'Improved system performance and reliability')
            
            table_rows += f'''
            <tr>
                <td style="padding: 1rem; font-weight: 600; color: var(--text-primary);">{phase_name}</td>
                <td style="padding: 1rem; text-align: center; color: var(--text-secondary);">{target_grade}</td>
                <td style="padding: 1rem; color: var(--text-secondary);">{actions}</td>
                <td style="padding: 1rem; color: var(--text-secondary);">{expected_impact}</td>
            </tr>'''
        
        return f'''
        <div class="section">
            <h2>🚀 Recommended Action Plan</h2>
            <div style="overflow-x: auto; margin-top: 1.5rem;">
                <table class="endpoint-table" style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%); color: white;">
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Phase</th>
                            <th style="padding: 1rem; text-align: center; font-weight: 600;">Target Grade</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Actions</th>
                            <th style="padding: 1rem; text-align: left; font-weight: 600;">Expected Impact</th>
                        </tr>
                    </thead>
                    <tbody>
                        {table_rows}
                    </tbody>
                </table>
            </div>
            
            <div style="background: linear-gradient(135deg, #f0fdf4, #ecfdf5); border-left: 4px solid var(--success-color); padding: 1.5rem; border-radius: 0 8px 8px 0; margin-top: 2rem;">
                <h3>Deployment Recommendation</h3>
                <p><strong>✅ RECOMMENDED:</strong> {'Full production deployment with monitoring' if current_grade in ['A+', 'A'] else 'Gradual rollout with performance monitoring while implementing improvements' if current_grade in ['B+', 'B'] else 'Limited production rollout while implementing critical fixes'}</p>
                <ul>
                    <li>{'Deploy to full user base' if current_grade in ['A+', 'A'] else 'Deploy to limited user base initially' if current_grade in ['B+', 'B', 'C+'] else 'Deploy to pilot users only'}</li>
                    <li>Implement comprehensive monitoring and alerting</li>
                    <li>{'Maintain performance standards' if current_grade in ['A+', 'A'] else 'Gradual scale-up with continuous monitoring'}</li>
                    <li>Regular performance reviews and optimization</li>
                </ul>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_final_conclusion(grade: str, score: float, success_rate: float, avg_response: float, 
                                   error_rate: float, throughput: float, p95_response: float, 
                                   sla_compliance: float, critical_issues: List[dict], 
                                   improvement_roadmap: List[dict], summary: dict) -> str:
        """Generate final conclusion section"""
        # Generate conclusion write-up
        if grade in ["A+", "A"]:
            conclusion_text = f"The performance assessment reveals an excellent system with a grade of {grade} (Score: {score:.0f}/100). The application demonstrates strong performance metrics including a {success_rate:.1f}% success rate, {avg_response:.2f}s average response time, and {throughput:.0f} requests/second throughput. The system is well-optimized and ready for production deployment with minimal concerns."
        elif grade in ["B+", "B"]:
            conclusion_text = f"The performance assessment indicates a good system with a grade of {grade} (Score: {score:.0f}/100). While the application shows acceptable performance with {success_rate:.1f}% success rate and {avg_response:.2f}s average response time, there are opportunities for optimization to achieve excellence. The system can be deployed with monitoring while implementing recommended improvements."
        else:
            conclusion_text = f"The performance assessment reveals a system requiring attention with a grade of {grade} (Score: {score:.0f}/100). The application shows {success_rate:.1f}% success rate and {avg_response:.2f}s average response time, indicating areas that need improvement. Immediate action is recommended to address critical issues before full production deployment."
        
        # Key Strengths
        strengths = []
        if success_rate >= 99:
            strengths.append(f"High success rate of {success_rate:.1f}% demonstrates excellent system reliability")
        if avg_response <= 2.0:
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
        if avg_response > 2.0:
            improvements.append(f"Optimize response time from {avg_response:.2f}s to target <2s for better user experience")
        if error_rate > 1.0:
            improvements.append(f"Reduce error rate from {error_rate:.2f}% to target <1% for improved reliability")
        if throughput < 100:
            improvements.append(f"Increase throughput from {throughput:.0f} req/s to handle higher loads")
        if sla_compliance < 95:
            improvements.append(f"Improve SLA compliance from {sla_compliance:.1f}% to target 95%+")
        if critical_issues:
            improvements.append(f"Address {len(critical_issues)} critical issue(s) identified in the assessment")
        if not improvements:
            improvements.append("Continue monitoring and maintain current performance standards")
        
        # Recommended Immediate Actions
        immediate_actions = []
        if critical_issues:
            immediate_actions.append("Address critical issues identified in the assessment (see Critical Issues section)")
        if error_rate > 5.0:
            immediate_actions.append("Implement error handling improvements to reduce error rate")
        if avg_response > 5.0:
            immediate_actions.append("Optimize slow endpoints and database queries to improve response time")
        if sla_compliance < 80:
            immediate_actions.append("Implement performance optimizations to improve SLA compliance")
        if not immediate_actions:
            immediate_actions.append("Continue monitoring system performance and maintain current standards")
        
        # Success Metrics
        success_metrics = [
            f"Maintain success rate above {max(95, success_rate * 0.95):.1f}%",
            f"Achieve average response time below {max(2.0, avg_response * 0.8):.2f}s",
            f"Reduce error rate to below {max(1.0, error_rate * 0.5):.2f}%",
            f"Increase throughput to {max(100, throughput * 1.2):.0f}+ req/s",
            f"Achieve SLA compliance of {min(95, sla_compliance + 10):.1f}%+"
        ]
        
        strengths_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{s}</li>' for s in strengths])
        improvements_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{i}</li>' for i in improvements])
        actions_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{a}</li>' for a in immediate_actions])
        metrics_html = ''.join([f'<li style="margin-bottom: 0.5rem;">{m}</li>' for m in success_metrics])
        
        return f'''
        <div class="section">
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
    def _generate_success_metrics(avg_response: float, p95_response: float, error_rate: float, 
                                  success_rate: float, sla_compliance: float, throughput: float) -> str:
        """Generate success metrics and targets"""
        # Calculate targets
        target_3m_avg = max(2.0, avg_response * 0.6)
        target_6m_avg = max(0.8, avg_response * 0.3)
        target_3m_p95 = max(5.0, p95_response * 0.4)
        target_6m_p95 = max(2.5, p95_response * 0.2)
        target_3m_error = max(0.8, error_rate * 0.4)
        target_6m_error = 0.3
        publish_success_current = success_rate
        target_3m_sla = min(95, sla_compliance + 20)
        target_6m_sla = 95
        target_3m_throughput = throughput * 1.5
        target_6m_throughput = max(180, throughput * 2.5)
        
        return f'''
        <div class="section">
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
                        <td style="text-align: center;">{avg_response:.1f} sec</td>
                        <td style="text-align: center;">{target_3m_avg:.1f} sec</td>
                        <td style="text-align: center;">{target_6m_avg:.1f} sec</td>
                        <td style="text-align: center;">&lt;2 sec</td>
                    </tr>
                    <tr>
                        <td><strong>95th Percentile</strong></td>
                        <td style="text-align: center;">{p95_response:.1f} sec</td>
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
        <div class="section">
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
        // Suppress Chart.js datalabels registration error
        if (window.ChartDataLabels) {{
            Chart.register(ChartDataLabels);
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
        """Generate HTML report for Web Vitals metrics"""
        current_date = datetime.now().strftime("%B %d, %Y")
        total_samples = metrics.get("total_samples", 0)
        
        lcp = metrics.get("lcp", {})
        fid = metrics.get("fid", {})
        cls = metrics.get("cls", {})
        fcp = metrics.get("fcp", {})
        ttfb = metrics.get("ttfb", {})
        summary = metrics.get("summary", {})
        
        def get_score_class(metric, value):
            if metric == "lcp":
                return "success" if value <= 2500 else "warning" if value <= 4000 else "danger"
            elif metric == "fid":
                return "success" if value <= 100 else "warning" if value <= 300 else "danger"
            elif metric == "cls":
                return "success" if value <= 0.1 else "warning" if value <= 0.25 else "danger"
            elif metric == "fcp":
                return "success" if value <= 1800 else "warning" if value <= 3000 else "danger"
            elif metric == "ttfb":
                return "success" if value <= 800 else "warning" if value <= 1800 else "danger"
            return "warning"
        
        lcp_mean = lcp.get("mean", 0) or 0
        fid_mean = fid.get("mean", 0) or 0
        cls_mean = cls.get("mean", 0) or 0
        fcp_mean = fcp.get("mean", 0) or 0
        ttfb_mean = ttfb.get("mean", 0) or 0
        
        return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Web Vitals Performance Report</title>
    <style>
        :root {{
            --primary: #3498db;
            --success: #27ae60;
            --warning: #f39c12;
            --danger: #e74c3c;
            --text: #2c3e50;
            --bg: #f8f9fa;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
        .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem; }}
        .header {{ text-align: center; padding: 2rem; background: linear-gradient(135deg, var(--primary), #2980b9); color: white; border-radius: 12px; margin-bottom: 2rem; }}
        .header h1 {{ font-size: 2.5rem; margin-bottom: 0.5rem; }}
        .metrics-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 1.5rem; margin: 2rem 0; }}
        .metric-card {{ background: white; border-radius: 12px; padding: 1.5rem; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 4px solid var(--primary); }}
        .metric-card.success {{ border-left-color: var(--success); }}
        .metric-card.warning {{ border-left-color: var(--warning); }}
        .metric-card.danger {{ border-left-color: var(--danger); }}
        .metric-card h3 {{ font-size: 1rem; color: #666; margin-bottom: 0.5rem; }}
        .metric-card .value {{ font-size: 2rem; font-weight: 700; }}
        .metric-card .value.success {{ color: var(--success); }}
        .metric-card .value.warning {{ color: var(--warning); }}
        .metric-card .value.danger {{ color: var(--danger); }}
        .metric-card .target {{ font-size: 0.85rem; color: #888; margin-top: 0.5rem; }}
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
            <h1>⚡ Web Vitals Performance Report</h1>
            <p>Core Web Vitals Analysis | {current_date}</p>
            <p style="margin-top: 0.5rem;">Total Samples: {total_samples:,}</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card {get_score_class('lcp', lcp_mean)}">
                <h3>LCP (Largest Contentful Paint)</h3>
                <div class="value {get_score_class('lcp', lcp_mean)}">{lcp_mean:.0f}ms</div>
                <div class="target">Target: ≤ 2500ms</div>
            </div>
            <div class="metric-card {get_score_class('fid', fid_mean)}">
                <h3>FID (First Input Delay)</h3>
                <div class="value {get_score_class('fid', fid_mean)}">{fid_mean:.0f}ms</div>
                <div class="target">Target: ≤ 100ms</div>
            </div>
            <div class="metric-card {get_score_class('cls', cls_mean)}">
                <h3>CLS (Cumulative Layout Shift)</h3>
                <div class="value {get_score_class('cls', cls_mean)}">{cls_mean:.3f}</div>
                <div class="target">Target: ≤ 0.1</div>
            </div>
            <div class="metric-card {get_score_class('fcp', fcp_mean)}">
                <h3>FCP (First Contentful Paint)</h3>
                <div class="value {get_score_class('fcp', fcp_mean)}">{fcp_mean:.0f}ms</div>
                <div class="target">Target: ≤ 1800ms</div>
            </div>
            <div class="metric-card {get_score_class('ttfb', ttfb_mean)}">
                <h3>TTFB (Time to First Byte)</h3>
                <div class="value {get_score_class('ttfb', ttfb_mean)}">{ttfb_mean:.0f}ms</div>
                <div class="target">Target: ≤ 800ms</div>
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
                        <td><strong>LCP</strong></td>
                        <td>{lcp.get('mean', 0) or 0:.0f}ms</td>
                        <td>{lcp.get('median', 0) or 0:.0f}ms</td>
                        <td>{lcp.get('p95', 0) or 0:.0f}ms</td>
                        <td>{lcp.get('p99', 0) or 0:.0f}ms</td>
                        <td>{lcp.get('min', 0) or 0:.0f}ms</td>
                        <td>{lcp.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>FID</strong></td>
                        <td>{fid.get('mean', 0) or 0:.0f}ms</td>
                        <td>{fid.get('median', 0) or 0:.0f}ms</td>
                        <td>{fid.get('p95', 0) or 0:.0f}ms</td>
                        <td>{fid.get('p99', 0) or 0:.0f}ms</td>
                        <td>{fid.get('min', 0) or 0:.0f}ms</td>
                        <td>{fid.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>CLS</strong></td>
                        <td>{cls.get('mean', 0) or 0:.3f}</td>
                        <td>{cls.get('median', 0) or 0:.3f}</td>
                        <td>{cls.get('p95', 0) or 0:.3f}</td>
                        <td>{cls.get('p99', 0) or 0:.3f}</td>
                        <td>{cls.get('min', 0) or 0:.3f}</td>
                        <td>{cls.get('max', 0) or 0:.3f}</td>
                    </tr>
                    <tr>
                        <td><strong>FCP</strong></td>
                        <td>{fcp.get('mean', 0) or 0:.0f}ms</td>
                        <td>{fcp.get('median', 0) or 0:.0f}ms</td>
                        <td>{fcp.get('p95', 0) or 0:.0f}ms</td>
                        <td>{fcp.get('p99', 0) or 0:.0f}ms</td>
                        <td>{fcp.get('min', 0) or 0:.0f}ms</td>
                        <td>{fcp.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                    <tr>
                        <td><strong>TTFB</strong></td>
                        <td>{ttfb.get('mean', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('median', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('p95', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('p99', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('min', 0) or 0:.0f}ms</td>
                        <td>{ttfb.get('max', 0) or 0:.0f}ms</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📈 Performance Distribution</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Good ✅</th>
                        <th>Needs Improvement ⚠️</th>
                        <th>Poor ❌</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><strong>LCP</strong></td>
                        <td>{summary.get('lcp_good', 0)}</td>
                        <td>{summary.get('lcp_needs_improvement', 0)}</td>
                        <td>{summary.get('lcp_poor', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>FID</strong></td>
                        <td>{summary.get('fid_good', 0)}</td>
                        <td>{summary.get('fid_needs_improvement', 0)}</td>
                        <td>{summary.get('fid_poor', 0)}</td>
                    </tr>
                    <tr>
                        <td><strong>CLS</strong></td>
                        <td>{summary.get('cls_good', 0)}</td>
                        <td>{summary.get('cls_needs_improvement', 0)}</td>
                        <td>{summary.get('cls_poor', 0)}</td>
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

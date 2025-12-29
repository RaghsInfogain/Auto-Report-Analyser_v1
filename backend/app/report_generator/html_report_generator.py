from typing import Dict, Any, List
from datetime import datetime
import json

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
        filename: str = "performance_report.html"
    ) -> str:
        """Generate a comprehensive HTML report for JMeter results"""
        
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
        
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # Generate grade color
        grade_bg_color = "#fee2e2" if grade_class == "danger" else "#fef3c7" if grade_class == "warning" else "#dcfce7"
        grade_border_color = "var(--danger-color)" if grade_class == "danger" else "var(--warning-color)" if grade_class == "warning" else "var(--success-color)"
        
        # Generate HTML
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Assessment Report</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-datalabels@2.2.0/dist/chartjs-plugin-datalabels.min.js"></script>
    {HTMLReportGenerator._generate_css()}
</head>
<body>
    <!-- Header -->
    <div class="header">
        <div class="container">
            <h1>Performance Assessment Report</h1>
            <p>Load Testing Results & Executive Analysis | {current_date}</p>
        </div>
    </div>

    <div class="container">
        
        <!-- Executive Summary -->
        {HTMLReportGenerator._generate_executive_summary(overall_grade, success_rate, avg_response, error_rate_pct, throughput)}
        
        <!-- Performance Scorecard with Grading -->
        {HTMLReportGenerator._generate_performance_scorecard(overall_grade, overall_score, grade_reasons, scores, targets, success_rate, avg_response, error_rate_pct, throughput, p95_response, sla_compliance_2s, grade_bg_color, grade_border_color, overall_grade_description)}
        
        <!-- Test Overview -->
        {HTMLReportGenerator._generate_test_overview(total_samples, test_duration_hours, throughput, success_rate)}
        
        <!-- Performance Summary Tables -->
        {HTMLReportGenerator._generate_performance_tables(transaction_stats, request_stats)}
        
        <!-- Critical Issues -->
        {HTMLReportGenerator._generate_critical_issues(critical_issues)}
        
        <!-- Business Impact Assessment -->
        {HTMLReportGenerator._generate_business_impact(error_rate_pct, avg_response)}
        
        <!-- Recommended Action Plan -->
        {HTMLReportGenerator._generate_action_plan(improvement_roadmap, overall_grade)}
        
        <!-- Success Metrics & Targets -->
        {HTMLReportGenerator._generate_success_metrics(avg_response, p95_response, error_rate_pct, success_rate, sla_compliance_2s, throughput)}
        
        <!-- Next Steps & Footer -->
        {HTMLReportGenerator._generate_footer(current_date)}
        
    </div>

    {HTMLReportGenerator._generate_javascript(response_time_dist, response_codes)}
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
    def _generate_executive_summary(grade: str, success_rate: float, avg_response: float, error_rate: float, throughput: float) -> str:
        """Generate executive summary section"""
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
    def _generate_performance_tables(transaction_stats: dict, request_stats: dict) -> str:
        """Generate performance summary tables for transactions and requests"""
        
        def generate_table(stats: dict, title: str) -> str:
            if not stats:
                return f"<p><em>No {title.lower()} data available</em></p>"
            
            # Sort by average response time (slowest first)
            sorted_stats = sorted(stats.items(), key=lambda x: x[1].get('avg_response', 0) or 0, reverse=True)
            
            rows = ""
            for label, data in sorted_stats[:15]:  # Top 15
                avg_resp = data.get('avg_response', 0)
                p70 = data.get('p70', 0)
                p80 = data.get('p80', 0)
                p90 = data.get('p90', 0)
                p95 = data.get('p95', 0)
                error_rate = data.get('error_rate', 0)
                count = data.get('count', 0)
                
                # Highlight high error rates
                error_style = 'color: var(--danger-color); font-weight: bold;' if error_rate > 5 else ''
                
                rows += f'''
                <tr>
                    <td>{label}</td>
                    <td style="text-align: center;"><strong>{avg_resp/1000:.2f}s</strong></td>
                    <td style="text-align: center;">{p70/1000:.2f}s</td>
                    <td style="text-align: center;">{p80/1000:.2f}s</td>
                    <td style="text-align: center;">{p90/1000:.2f}s</td>
                    <td style="text-align: center;">{p95/1000:.2f}s</td>
                    <td style="text-align: center; {error_style}">{error_rate:.2f}%</td>
                    <td style="text-align: center;">{count:,}</td>
                </tr>'''
            
            return f'''
            <h3>{title}</h3>
            <div style="overflow-x: auto;">
                <table class="endpoint-table">
                    <thead>
                        <tr>
                            <th>Endpoint/Transaction</th>
                            <th style="text-align: center;">Avg Response</th>
                            <th style="text-align: center;">70th %ile</th>
                            <th style="text-align: center;">80th %ile</th>
                            <th style="text-align: center;">90th %ile</th>
                            <th style="text-align: center;">95th %ile</th>
                            <th style="text-align: center;">Error Rate</th>
                            <th style="text-align: center;">Calls</th>
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
    def _generate_critical_issues(issues: List[dict]) -> str:
        """Generate critical issues section"""
        if not issues:
            return '''
        <div class="section">
            <h2>🔴 Critical Issues</h2>
            <div class="alert alert-success">
                <strong>✅ NO CRITICAL ISSUES IDENTIFIED:</strong> The system is performing well with no major concerns.
            </div>
        </div>'''
        
        issue_items = ""
        for i, issue in enumerate(issues, 1):
            issue_items += f'''
            <li class="issue-item">
                <h4>Issue #{i}: {issue.get('title', 'Unknown Issue')}</h4>
                <p><strong>Impact:</strong> {issue.get('impact', 'N/A')}</p>
                <p><strong>Affected:</strong> {issue.get('affected', 'N/A')}</p>
                <p><strong>Fix Timeline:</strong> {issue.get('timeline', 'N/A')} | <strong>Priority:</strong> {issue.get('priority', 'N/A')}</p>
            </li>'''
        
        return f'''
        <div class="section">
            <h2>🔴 Critical Issues</h2>
            <div class="alert alert-danger">
                <strong>IMMEDIATE ACTION REQUIRED:</strong> {len(issues)} critical issue{'s' if len(issues) > 1 else ''} {'are' if len(issues) > 1 else 'is'} severely impacting business operations and user experience.
            </div>
            
            <ul class="issues-list" style="list-style: none;">
                {issue_items}
            </ul>
            
            <!-- Path to Improve Grade -->
            <div style="background: linear-gradient(135deg, #f0f9ff, #e0f2fe); border: 2px solid var(--primary-color); border-radius: 12px; padding: 2rem; margin: 2rem 0;">
                <h3 style="color: var(--primary-color); margin: 0 0 1rem 0;">🎯 Path to Improve Grade</h3>
                <p style="margin-bottom: 1rem;">To achieve an A+ grade and ensure optimal performance, follow the improvement roadmap outlined in the Recommended Action Plan section below. Focus on:</p>
                <ul style="margin-left: 2rem;">
                    <li><strong>Phase 1:</strong> Fix critical bugs and performance bottlenecks (Week 1-4)</li>
                    <li><strong>Phase 2:</strong> Implement optimization and caching strategies (Week 4-12)</li>
                    <li><strong>Phase 3:</strong> Achieve excellence through advanced monitoring and scaling (Week 12-24)</li>
                </ul>
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
        """Generate recommended action plan"""
        timeline_items = ""
        for phase in roadmap:
            phase_name = phase.get('phase', 'Phase')
            timeline = phase.get('timeline', 'TBD')
            target_grade = phase.get('target_grade', 'N/A')
            improvements = phase.get('improvements', [])
            expected_impact = phase.get('expected_impact', 'N/A')
            
            # Determine class based on phase
            item_class = "danger" if "Critical" in phase_name else "warning" if "Optimization" in phase_name else "success"
            
            improvement_list = "".join([f"<li>{imp}</li>" for imp in improvements])
            
            timeline_items += f'''
            <div class="timeline-item {item_class}">
                <h4>{phase_name} ({timeline})</h4>
                <p><strong>Target Grade:</strong> {target_grade}</p>
                <ul>
                    {improvement_list}
                </ul>
                <strong>Expected Impact:</strong> {expected_impact}
            </div>'''
        
        return f'''
        <div class="section">
            <h2>🚀 Recommended Action Plan</h2>
            <div class="action-timeline">
                {timeline_items if timeline_items else '<p>No specific action plan generated. Consider standard performance optimization strategies.</p>'}
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
        
        // Note: Charts are not rendered in this version
        // The HTML structure is designed to be easily extended with Chart.js visualizations
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

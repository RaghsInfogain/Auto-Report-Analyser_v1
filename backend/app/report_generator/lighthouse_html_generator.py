"""
Lighthouse HTML Report Generator
Generates comprehensive HTML reports for Lighthouse performance analysis
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta


class LighthouseHTMLGenerator:
    """Generate HTML reports for Lighthouse analysis"""
    
    @staticmethod
    def generate_full_report(analysis: Dict[str, Any], filename: str = "lighthouse_report.html") -> str:
        """Generate complete HTML report"""
        metrics = analysis.get("metrics", {})
        grades = analysis.get("grades", {})
        overall_grade = analysis.get("overall_grade", {})
        issues = analysis.get("issues", [])
        recommendations = analysis.get("recommendations", {})
        business_impact = analysis.get("business_impact", {})
        aiml_results = analysis.get("aiml_results", {})
        metadata = analysis.get("report_metadata", {})
        
        test_overview = analysis.get("test_overview", {})
        page_data = analysis.get("page_data", [])
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Performance Test Analysis Report</title>
    {LighthouseHTMLGenerator._generate_css()}
</head>
<body>
    <div class="container">
        {LighthouseHTMLGenerator._generate_header(metadata)}
        {LighthouseHTMLGenerator._generate_executive_summary(metrics, grades, overall_grade, issues)}
        {LighthouseHTMLGenerator._generate_performance_scorecard(metrics, grades, overall_grade)}
        {LighthouseHTMLGenerator._generate_test_overview(test_overview, metadata)}
        {LighthouseHTMLGenerator._generate_detailed_metrics_table(page_data)}
        {LighthouseHTMLGenerator._generate_issues_table(issues, page_data)}
        {LighthouseHTMLGenerator._generate_optimization_roadmap(recommendations)}
        {LighthouseHTMLGenerator._generate_business_impact(business_impact)}
        {LighthouseHTMLGenerator._generate_monitoring_maintenance()}
        {LighthouseHTMLGenerator._generate_aiml_appendix(aiml_results)}
        {LighthouseHTMLGenerator._generate_final_conclusion(metrics, grades, overall_grade)}
        {LighthouseHTMLGenerator._generate_report_details(metadata)}
    </div>
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
            padding: 1rem 0;
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 0 1rem;
        }

        .header {
            background: linear-gradient(135deg, var(--primary-color), #3b82f6);
            color: white;
            padding: 2rem;
            text-align: center;
            border-radius: 12px;
            margin-bottom: 2rem;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
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
            margin: 1.5rem 0;
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

        .summary-label {
            font-size: 0.9rem;
            opacity: 0.9;
        }

        .grade-badge {
            display: inline-block;
            padding: 0.5rem 1.5rem;
            border-radius: 20px;
            font-weight: 700;
            font-size: 1.2rem;
            margin: 0.5rem;
        }

        .grade-a { background: var(--success-color); color: white; }
        .grade-b { background: #3b82f6; color: white; }
        .grade-c { background: var(--warning-color); color: white; }
        .grade-d { background: #f59e0b; color: white; }
        .grade-e { background: #ef4444; color: white; }
        .grade-f { background: var(--danger-color); color: white; }
        
        .scorecard-card {
            background: var(--card-background);
            border: 2px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        
        .scorecard-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }
        
        .scorecard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 1.5rem 0;
        }
        
        .grade-card {
            background: var(--card-background);
            border: 2px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .risk-card {
            padding: 1.5rem;
            border-radius: 8px;
            margin: 1.5rem 0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.9rem;
        }

        table th,
        table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        table th {
            background: var(--background-light);
            font-weight: 600;
            color: var(--text-primary);
        }

        table tr:hover {
            background: var(--background-light);
        }

        .status-good { color: var(--success-color); font-weight: 600; }
        .status-warning { color: var(--warning-color); font-weight: 600; }
        .status-poor { color: var(--danger-color); font-weight: 600; }
        .status-critical { color: #991b1b; font-weight: 700; }

        .severity-low { background: #d1fae5; color: #065f46; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-medium { background: #fef3c7; color: #92400e; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-high { background: #fee2e2; color: #991b1b; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-critical { background: #fecaca; color: #7f1d1d; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 700; }

        .alert {
            padding: 1rem;
            border-radius: 8px;
            margin: 1rem 0;
            border-left: 4px solid;
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

        .phase-section {
            margin: 1.5rem 0;
            padding: 1rem;
            background: var(--background-light);
            border-radius: 8px;
        }

        .footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 2px solid var(--border-color);
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.9rem;
        }

        @media (max-width: 768px) {
            .header h1 { font-size: 2rem; }
            .summary-grid { grid-template-columns: 1fr; }
            table { font-size: 0.8rem; }
        }
    </style>'''
    
    @staticmethod
    def _generate_header(metadata: Dict[str, Any]) -> str:
        """Generate report header"""
        return f'''<div class="header">
            <h1>Performance Test Analysis Report</h1>
            <p>User Experience Monitoring Analysis</p>
        </div>'''
    
    @staticmethod
    def _generate_executive_summary(metrics: Dict[str, Any], grades: Dict[str, Any], overall_grade: Dict[str, Any], issues: List[Dict[str, Any]]) -> str:
        """Generate executive summary section"""
        perf_score = metrics.get("performance_score", 0)
        loading_grade = grades.get("loading", {}).get("grade", "N/A")
        interactivity_grade = grades.get("interactivity", {}).get("grade", "N/A")
        visual_grade = grades.get("visual_stability", {}).get("grade", "N/A")
        overall_score = overall_grade.get("score", 0)
        overall_letter = overall_grade.get("letter_grade", "N/A")
        
        # Business risk assessment
        if overall_score < 20:
            risk_level = "CRITICAL"
            risk_message = "⚠️ <strong>URGENT:</strong> Performance is critically poor. Immediate action required to prevent significant business impact."
        elif overall_score < 40:
            risk_level = "HIGH"
            risk_message = "⚠️ Performance is poor and requires immediate attention to avoid negative business impact."
        elif overall_score < 60:
            risk_level = "MEDIUM"
            risk_message = "Performance needs improvement to meet industry standards and user expectations."
        else:
            risk_level = "LOW"
            risk_message = "Performance is acceptable but can be optimized further."
        
        # Get detailed grade info
        loading_score = grades.get("loading", {}).get("score", 0)
        loading_metric = grades.get("loading", {}).get("metric", 0)
        loading_name = grades.get("loading", {}).get("metric_name", "LCP")
        
        interactivity_score = grades.get("interactivity", {}).get("score", 0)
        interactivity_metric = grades.get("interactivity", {}).get("metric", 0)
        interactivity_name = grades.get("interactivity", {}).get("metric_name", "TBT")
        
        visual_score = grades.get("visual_stability", {}).get("score", 0)
        visual_metric = grades.get("visual_stability", {}).get("metric", 0)
        visual_name = grades.get("visual_stability", {}).get("metric_name", "CLS")
        
        # Enhanced risk messages
        if overall_score < 20:
            risk_message = "⚠️ <strong>URGENT:</strong> Performance is critically poor. Immediate action required to prevent significant business impact. User experience is severely compromised, leading to high bounce rates, poor conversion, and potential revenue loss."
        elif overall_score < 40:
            risk_message = "⚠️ Performance is poor and requires immediate attention to avoid negative business impact. Users are experiencing significant delays and frustration, which will impact engagement and conversions."
        elif overall_score < 60:
            risk_message = "Performance needs improvement to meet industry standards and user expectations. While functional, the experience could be significantly enhanced to improve user satisfaction and business metrics."
        else:
            risk_message = "Performance is acceptable and meets most industry standards. Optimization opportunities exist to further enhance user experience and achieve best-in-class performance."
        
        # Grade explanations
        def get_grade_explanation(grade: str, metric_name: str, metric_value: float) -> str:
            if grade == "A":
                return f"Excellent performance. {metric_name} of {metric_value:.1f}{'s' if metric_name == 'LCP' else 'ms' if metric_name == 'TBT' else ''} meets best-in-class standards."
            elif grade == "B":
                return f"Good performance. {metric_name} of {metric_value:.1f}{'s' if metric_name == 'LCP' else 'ms' if metric_name == 'TBT' else ''} is within acceptable range with room for optimization."
            elif grade == "C":
                return f"Acceptable performance. {metric_name} of {metric_value:.1f}{'s' if metric_name == 'LCP' else 'ms' if metric_name == 'TBT' else ''} needs improvement to meet optimal standards."
            elif grade == "D":
                return f"Below average performance. {metric_name} of {metric_value:.1f}{'s' if metric_name == 'LCP' else 'ms' if metric_name == 'TBT' else ''} requires immediate optimization."
            elif grade == "E":
                return f"Poor performance. {metric_name} of {metric_value:.1f}{'s' if metric_name == 'LCP' else 'ms' if metric_name == 'TBT' else ''} significantly impacts user experience."
            else:
                return f"Critical performance issue. {metric_name} of {metric_value:.1f}{'s' if metric_name == 'LCP' else 'ms' if metric_name == 'TBT' else ''} requires urgent remediation."
        
        # Key findings
        key_findings = []
        if loading_grade in ["D", "E", "F"]:
            key_findings.append(f"Loading performance ({loading_grade}) is below acceptable standards with {loading_name} of {loading_metric:.1f}{'s' if loading_name == 'LCP' else 'ms'}")
        if interactivity_grade in ["D", "E", "F"]:
            key_findings.append(f"Interactivity ({interactivity_grade}) needs improvement with {interactivity_name} of {interactivity_metric:.0f}ms")
        if visual_grade in ["D", "E", "F"]:
            key_findings.append(f"Visual stability ({visual_grade}) requires attention with {visual_name} of {visual_metric:.3f}")
        if len(issues) > 0:
            key_findings.append(f"{len(issues)} critical performance issue(s) identified requiring immediate action")
        if overall_score >= 80:
            key_findings.append("Overall performance meets industry standards")
        if not key_findings:
            key_findings.append("Performance metrics are within acceptable ranges")
        
        return f'''<div class="executive-summary">
            <h2>Executive Summary</h2>
            
            <!-- Business Risk Level Card -->
            <div class="risk-card" style="background: {"#fef2f2" if risk_level in ["CRITICAL", "HIGH"] else "#fffbeb" if risk_level == "MEDIUM" else "#f0fdf4"}; border-left: 4px solid {"#dc2626" if risk_level in ["CRITICAL", "HIGH"] else "#d97706" if risk_level == "MEDIUM" else "#059669"}; padding: 1.5rem; border-radius: 8px; margin: 1.5rem 0;">
                <h3 style="margin-top: 0; color: {"#991b1b" if risk_level in ["CRITICAL", "HIGH"] else "#92400e" if risk_level == "MEDIUM" else "#166534"};">
                    Business Risk Level: <span style="font-size: 1.5rem;">{risk_level}</span>
                </h3>
                <p style="margin: 0.5rem 0 0 0; font-size: 1.1rem; color: {"#991b1b" if risk_level in ["CRITICAL", "HIGH"] else "#92400e" if risk_level == "MEDIUM" else "#166534"};">{risk_message}</p>
            </div>
            
            <!-- Category Cards -->
            <div class="summary-grid" style="margin-top: 2rem;">
                <div class="category-card" style="background: rgba(255, 255, 255, 0.15); border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div class="grade-badge grade-{loading_grade.lower()}" style="font-size: 2rem; margin-bottom: 1rem;">{loading_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: white;">Loading Experience</h3>
                    <div style="font-size: 1.5rem; font-weight: 700; color: white; margin: 0.5rem 0;">{loading_score:.0f}/100</div>
                    <p style="margin: 0.5rem 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 0.9rem;">{get_grade_explanation(loading_grade, loading_name, loading_metric)}</p>
                </div>
                
                <div class="category-card" style="background: rgba(255, 255, 255, 0.15); border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div class="grade-badge grade-{interactivity_grade.lower()}" style="font-size: 2rem; margin-bottom: 1rem;">{interactivity_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: white;">Interactivity Experience</h3>
                    <div style="font-size: 1.5rem; font-weight: 700; color: white; margin: 0.5rem 0;">{interactivity_score:.0f}/100</div>
                    <p style="margin: 0.5rem 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 0.9rem;">{get_grade_explanation(interactivity_grade, interactivity_name, interactivity_metric)}</p>
                </div>
                
                <div class="category-card" style="background: rgba(255, 255, 255, 0.15); border: 2px solid rgba(255, 255, 255, 0.3); border-radius: 12px; padding: 1.5rem; text-align: center;">
                    <div class="grade-badge grade-{visual_grade.lower()}" style="font-size: 2rem; margin-bottom: 1rem;">{visual_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: white;">Visual Stability</h3>
                    <div style="font-size: 1.5rem; font-weight: 700; color: white; margin: 0.5rem 0;">{visual_score:.0f}/100</div>
                    <p style="margin: 0.5rem 0 0 0; color: rgba(255, 255, 255, 0.9); font-size: 0.9rem;">{get_grade_explanation(visual_grade, visual_name, visual_metric)}</p>
                </div>
            </div>
            
            <!-- Key Findings -->
            <div style="margin-top: 2rem; padding: 1.5rem; background: rgba(255, 255, 255, 0.15); border-radius: 8px;">
                <h3 style="margin-top: 0; color: white;">Key Findings</h3>
                <ul style="margin: 1rem 0 0 0; padding-left: 1.5rem; color: rgba(255, 255, 255, 0.95);">
                    {''.join(f'<li style="margin: 0.5rem 0;">{finding}</li>' for finding in key_findings)}
                </ul>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_performance_scorecard(metrics: Dict[str, Any], grades: Dict[str, Any], overall_grade: Dict[str, Any]) -> str:
        """Generate Performance Scorecard and Grading Analysis section"""
        overall_score = overall_grade.get("score", 0)
        overall_letter = overall_grade.get("letter_grade", "N/A")
        perf_score = metrics.get("performance_score", 0)
        
        # Overall grade interpretation
        def get_overall_grade_meaning(grade: str, score: float) -> str:
            if grade == "A":
                return "System performance is excellent and meets best-in-class standards. User experience is optimal with fast loading, responsive interactivity, and stable visuals."
            elif grade == "B":
                return "System performance is good and meets industry standards. Minor optimizations can further enhance user experience."
            elif grade == "C":
                return "System performance is acceptable but needs improvement. Optimization is recommended to meet optimal user experience standards."
            elif grade == "D":
                return "System performance is below average. Immediate optimization required to improve user experience and meet industry standards."
            elif grade == "E":
                return "System performance is poor. Significant optimization required to prevent negative business impact and user frustration."
            else:
                return "System performance is critical. Urgent remediation required to prevent severe business impact and user abandonment."
        
        # Grade ranges
        grade_ranges = {
            "A": "90-100",
            "B": "80-89",
            "C": "70-79",
            "D": "60-69",
            "E": "40-59",
            "F": "0-39"
        }
        
        # Get category details
        loading_grade = grades.get("loading", {}).get("grade", "N/A")
        loading_score = grades.get("loading", {}).get("score", 0)
        loading_weight = "50%"
        
        interactivity_grade = grades.get("interactivity", {}).get("grade", "N/A")
        interactivity_score = grades.get("interactivity", {}).get("score", 0)
        interactivity_weight = "30%"
        
        visual_grade = grades.get("visual_stability", {}).get("grade", "N/A")
        visual_score = grades.get("visual_stability", {}).get("score", 0)
        visual_weight = "20%"
        
        # Grade meanings
        grade_meanings = {
            "A": "Excellent - Best-in-class performance",
            "B": "Good - Meets industry standards",
            "C": "Acceptable - Needs improvement",
            "D": "Below Average - Requires optimization",
            "E": "Poor - Significant issues",
            "F": "Critical - Urgent remediation needed"
        }
        
        return f'''<div class="section">
            <h2>Performance Scorecard and Grading Analysis</h2>
            
            <!-- Overall Grade Card -->
            <div class="scorecard-card" style="border: 3px solid {"var(--success-color)" if overall_letter == "A" else "#3b82f6" if overall_letter == "B" else "var(--warning-color)" if overall_letter == "C" else "#f59e0b" if overall_letter == "D" else "#ef4444" if overall_letter == "E" else "var(--danger-color)"}; margin-bottom: 2rem;">
                <div class="grade-badge grade-{overall_letter.lower()}" style="font-size: 3rem; margin-bottom: 1rem;">{overall_letter}</div>
                <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Overall Grade</h3>
                <p style="margin: 0.5rem 0; color: var(--text-secondary);">{get_overall_grade_meaning(overall_letter, overall_score)}</p>
                <div style="margin-top: 1rem;">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--primary-color);">{overall_score:.1f}/100</div>
                    <div style="color: var(--text-secondary); margin-top: 0.5rem;">Score Range: {grade_ranges.get(overall_letter, "N/A")}</div>
                </div>
            </div>
            
            <!-- Category Cards -->
            <div class="scorecard-grid">
                <div class="scorecard-card">
                    <div class="grade-badge grade-{loading_grade.lower()}" style="font-size: 1.5rem; margin-bottom: 1rem;">{loading_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Loading Experience</h3>
                    <p style="margin: 0.5rem 0; color: var(--text-secondary); font-size: 0.9rem;">{grade_meanings.get(loading_grade, "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">{loading_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem;">Weightage: {loading_weight}</div>
                    </div>
                </div>
                
                <div class="scorecard-card">
                    <div class="grade-badge grade-{interactivity_grade.lower()}" style="font-size: 1.5rem; margin-bottom: 1rem;">{interactivity_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Interactivity Experience</h3>
                    <p style="margin: 0.5rem 0; color: var(--text-secondary); font-size: 0.9rem;">{grade_meanings.get(interactivity_grade, "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">{interactivity_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem;">Weightage: {interactivity_weight}</div>
                    </div>
                </div>
                
                <div class="scorecard-card">
                    <div class="grade-badge grade-{visual_grade.lower()}" style="font-size: 1.5rem; margin-bottom: 1rem;">{visual_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Visual Stability</h3>
                    <p style="margin: 0.5rem 0; color: var(--text-secondary); font-size: 0.9rem;">{grade_meanings.get(visual_grade, "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color);">{visual_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem;">Weightage: {visual_weight}</div>
                    </div>
                </div>
                
                <div class="scorecard-card">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--primary-color); margin-bottom: 1rem;">{perf_score:.0f}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Performance Score</h3>
                    <p style="margin: 0.5rem 0; color: var(--text-secondary); font-size: 0.9rem;">Lighthouse Performance Score</p>
                    <div style="color: var(--text-secondary); margin-top: 1rem;">Range: 0-100</div>
                </div>
            </div>
            
            <!-- Performance Grading and Scaling & Methodology -->
            <h3 style="margin-top: 2rem;">Performance Grading and Scaling & Methodology</h3>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin: 1.5rem 0;">
                <div class="grade-card" style="border-color: var(--success-color);">
                    <div class="grade-badge grade-a" style="font-size: 1.2rem; margin-bottom: 0.5rem;">A</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Score Range: 90-100</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Excellent - Best-in-class performance</div>
                </div>
                <div class="grade-card" style="border-color: #3b82f6;">
                    <div class="grade-badge grade-b" style="font-size: 1.2rem; margin-bottom: 0.5rem;">B</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Score Range: 80-89</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Good - Meets industry standards</div>
                </div>
                <div class="grade-card" style="border-color: var(--warning-color);">
                    <div class="grade-badge grade-c" style="font-size: 1.2rem; margin-bottom: 0.5rem;">C</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Score Range: 70-79</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Acceptable - Needs improvement</div>
                </div>
                <div class="grade-card" style="border-color: #f59e0b;">
                    <div class="grade-badge grade-d" style="font-size: 1.2rem; margin-bottom: 0.5rem;">D</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Score Range: 60-69</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Below Average - Requires optimization</div>
                </div>
                <div class="grade-card" style="border-color: #ef4444;">
                    <div class="grade-badge grade-e" style="font-size: 1.2rem; margin-bottom: 0.5rem;">E</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Score Range: 40-59</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Poor - Significant issues</div>
                </div>
                <div class="grade-card" style="border-color: var(--danger-color);">
                    <div class="grade-badge grade-f" style="font-size: 1.2rem; margin-bottom: 0.5rem;">F</div>
                    <div style="font-weight: 600; margin-bottom: 0.5rem;">Score Range: 0-39</div>
                    <div style="font-size: 0.9rem; color: var(--text-secondary);">Critical - Urgent remediation needed</div>
                </div>
            </div>
            
            <!-- Why This Scorecard Matters -->
            <div style="margin-top: 2rem; padding: 1.5rem; background: var(--background-light); border-radius: 8px; border-left: 4px solid var(--primary-color);">
                <h3 style="margin-top: 0; color: var(--primary-color);">Why This Scorecard Matters</h3>
                <ul style="margin: 1rem 0 0 0; padding-left: 1.5rem;">
                    <li style="margin: 0.5rem 0;"><strong>Weighted Scoring:</strong> Each metric is weighted based on business impact. Loading Experience (50%) has the highest weight as it directly affects first impressions, followed by Interactivity (30%) and Visual Stability (20%).</li>
                    <li style="margin: 0.5rem 0;"><strong>Industry Benchmarks:</strong> Targets are based on enterprise SaaS standards and user experience research. These benchmarks reflect real-world user expectations and industry best practices.</li>
                    <li style="margin: 0.5rem 0;"><strong>Business Impact:</strong> Current grade indicates performance state and required actions. Lower grades signal immediate optimization needs to prevent revenue loss, user churn, and negative brand perception.</li>
                </ul>
            </div>
        </div>'''
    
    @staticmethod
    def _generate_test_overview(test_overview: Dict[str, Any], metadata: Dict[str, Any]) -> str:
        """Generate Test Overview section with cards"""
        total_pages = test_overview.get("total_pages", 1)
        test_duration = test_overview.get("test_duration", "N/A")
        avg_page_components = test_overview.get("avg_page_components", "N/A")
        avg_data_processed = test_overview.get("avg_data_processed", "N/A")
        test_config = test_overview.get("test_config", [])
        test_objectives = test_overview.get("test_objectives", [])
        
        return f'''<div class="section">
            <h2>Test Overview</h2>
            
            <!-- Overview Cards -->
            <div class="scorecard-grid">
                <div class="scorecard-card">
                    <div style="font-size: 2.5rem; font-weight: 700; color: var(--primary-color); margin-bottom: 0.5rem;">{total_pages}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Total Pages</h3>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Pages analyzed</p>
                </div>
                
                <div class="scorecard-card">
                    <div style="font-size: 2.5rem; font-weight: 700; color: var(--primary-color); margin-bottom: 0.5rem;">{test_duration}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Test Duration</h3>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Time taken for analysis</p>
                </div>
                
                <div class="scorecard-card">
                    <div style="font-size: 2.5rem; font-weight: 700; color: var(--primary-color); margin-bottom: 0.5rem;">{avg_page_components}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Average Page Components</h3>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Average DOM elements per page</p>
                </div>
                
                <div class="scorecard-card">
                    <div style="font-size: 2.5rem; font-weight: 700; color: var(--primary-color); margin-bottom: 0.5rem;">{avg_data_processed}</div>
                    <h3 style="margin: 0.5rem 0; color: var(--text-primary);">Average Data Processed</h3>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 0.9rem;">Average data size per page</p>
                </div>
            </div>
            
            <!-- Test Configuration -->
            <h3 style="margin-top: 2rem;">Test Configuration</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li style="margin: 0.5rem 0;">{config}</li>' for config in test_config) if test_config else '<li>Default Lighthouse configuration</li>'}
            </ul>
            
            <!-- Test Objectives -->
            <h3 style="margin-top: 2rem;">Test Objectives</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li style="margin: 0.5rem 0;">{objective}</li>' for objective in test_objectives)}
            </ul>
        </div>'''
    
    @staticmethod
    def _get_metric_color(value: float, metric_name: str) -> str:
        """Get color (green/amber/red) based on Lighthouse standards"""
        if metric_name.lower() == "fcp":
            if value <= 1.8:
                return "green"
            elif value <= 3.0:
                return "amber"
            else:
                return "red"
        elif metric_name.lower() == "lcp":
            if value <= 2.5:
                return "green"
            elif value <= 4.0:
                return "amber"
            else:
                return "red"
        elif metric_name.lower() == "speed_index":
            if value <= 3.4:
                return "green"
            elif value <= 5.8:
                return "amber"
            else:
                return "red"
        elif metric_name.lower() == "tbt":
            if value <= 200:
                return "green"
            elif value <= 600:
                return "amber"
            else:
                return "red"
        elif metric_name.lower() == "cls":
            if value <= 0.10:
                return "green"
            elif value <= 0.25:
                return "amber"
            else:
                return "red"
        elif metric_name.lower() == "tti":
            if value <= 3.8:
                return "green"
            elif value <= 7.3:
                return "amber"
            else:
                return "red"
        return "gray"
    
    @staticmethod
    def _generate_detailed_metrics_table(page_data: List[Dict[str, Any]]) -> str:
        """Generate detailed performance metrics table with Page column and color coding"""
        from app.analyzers.lighthouse_analyzer import LighthouseAnalyzer
        
        # Define targets and calculate scores
        def get_metric_score(metric_name: str, value: float) -> float:
            """Calculate score (0-100) for a metric"""
            if metric_name.lower() == "fcp":
                if value <= 1.8:
                    return 100
                elif value <= 3.0:
                    return 80 - ((value - 1.8) / 1.2) * 20
                else:
                    return max(0, 60 - ((value - 3.0) / 2.0) * 60)
            elif metric_name.lower() == "lcp":
                if value <= 2.5:
                    return 100
                elif value <= 4.0:
                    return 80 - ((value - 2.5) / 1.5) * 20
                else:
                    return max(0, 60 - ((value - 4.0) / 8.0) * 60)
            elif metric_name.lower() == "speed_index":
                if value <= 3.4:
                    return 100
                elif value <= 5.8:
                    return 80 - ((value - 3.4) / 2.4) * 20
                else:
                    return max(0, 60 - ((value - 5.8) / 6.2) * 60)
            elif metric_name.lower() == "tbt":
                if value <= 200:
                    return 100
                elif value <= 600:
                    return 80 - ((value - 200) / 400) * 20
                else:
                    return max(0, 60 - ((value - 600) / 1400) * 60)
            elif metric_name.lower() == "cls":
                if value <= 0.10:
                    return 100
                elif value <= 0.25:
                    return 80 - ((value - 0.10) / 0.15) * 20
                else:
                    return max(0, 60 - ((value - 0.25) / 0.25) * 60)
            elif metric_name.lower() == "tti":
                if value <= 3.8:
                    return 100
                elif value <= 7.3:
                    return 80 - ((value - 3.8) / 3.5) * 20
                else:
                    return max(0, 60 - ((value - 7.3) / 2.7) * 60)
            return 0
        
        if not page_data:
            return '''<div class="section">
                <h2>Detailed Performance Metrics</h2>
                <p>No page data available.</p>
            </div>'''
        
        rows = ""
        for page in page_data:
            url = page.get("url", "Unknown Page")
            # Shorten URL for display
            display_url = url if len(url) <= 50 else url[:47] + "..."
            
            fcp = page.get("fcp", 0)
            lcp = page.get("lcp", 0)
            speed_index = page.get("speed_index", 0)
            tbt = page.get("tbt", 0)
            cls = page.get("cls", 0)
            tti = page.get("tti", 0)
            
            # Get colors
            fcp_color = LighthouseHTMLGenerator._get_metric_color(fcp, "fcp")
            lcp_color = LighthouseHTMLGenerator._get_metric_color(lcp, "lcp")
            si_color = LighthouseHTMLGenerator._get_metric_color(speed_index, "speed_index")
            tbt_color = LighthouseHTMLGenerator._get_metric_color(tbt, "tbt")
            cls_color = LighthouseHTMLGenerator._get_metric_color(cls, "cls")
            tti_color = LighthouseHTMLGenerator._get_metric_color(tti, "tti")
            
            # Get status
            from app.analyzers.lighthouse_analyzer import LighthouseAnalyzer
            overall_status = LighthouseAnalyzer._get_metric_status(lcp, "lcp")
            status_text = overall_status['status']
            
            # Calculate overall score (average of all metrics)
            fcp_score = get_metric_score("fcp", fcp)
            lcp_score = get_metric_score("lcp", lcp)
            si_score = get_metric_score("speed_index", speed_index)
            tbt_score = get_metric_score("tbt", tbt)
            cls_score = get_metric_score("cls", cls)
            tti_score = get_metric_score("tti", tti)
            avg_score = (fcp_score + lcp_score + si_score + tbt_score + cls_score + tti_score) / 6
            
            # Color mapping
            color_map = {
                "green": "var(--success-color)",
                "amber": "var(--warning-color)",
                "red": "var(--danger-color)",
                "gray": "var(--text-secondary)"
            }
            
            rows += f'''
                <tr>
                    <td><strong title="{url}">{display_url}</strong></td>
                    <td style="color: {color_map.get(fcp_color, 'black')}; font-weight: 600;">{fcp:.1f}s</td>
                    <td style="color: {color_map.get(lcp_color, 'black')}; font-weight: 600;">{lcp:.1f}s</td>
                    <td style="color: {color_map.get(si_color, 'black')}; font-weight: 600;">{speed_index:.1f}s</td>
                    <td style="color: {color_map.get(tbt_color, 'black')}; font-weight: 600;">{tbt:.0f}ms</td>
                    <td style="color: {color_map.get(cls_color, 'black')}; font-weight: 600;">{cls:.3f}</td>
                    <td style="color: {color_map.get(tti_color, 'black')}; font-weight: 600;">{tti:.1f}s</td>
                    <td class="status-{status_text.replace('✅ ', '').replace('⚠️ ', '').replace('❌ ', '').lower().replace(' ', '-')}">{status_text}</td>
                    <td style="color: {"var(--success-color)" if avg_score >= 80 else "var(--warning-color)" if avg_score >= 60 else "var(--danger-color)"}; font-weight: 700;">{avg_score:.0f}/100</td>
                </tr>'''
        
        return f'''<div class="section">
            <h2>Detailed Performance Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Page</th>
                        <th>FCP</th>
                        <th>LCP</th>
                        <th>Speed Index</th>
                        <th>TBT</th>
                        <th>CLS</th>
                        <th>TTI</th>
                        <th>Status</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <p style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                <strong>Color Coding:</strong> <span style="color: var(--success-color);">Green</span> = Good, 
                <span style="color: var(--warning-color);">Amber</span> = Needs Improvement, 
                <span style="color: var(--danger-color);">Red</span> = Poor
            </p>
        </div>'''
    
    @staticmethod
    def _generate_key_metrics_table(metrics: Dict[str, Any]) -> str:
        """Generate key performance metrics table"""
        from app.analyzers.lighthouse_analyzer import LighthouseAnalyzer
        
        metric_data = [
            {
                "name": "First Contentful Paint (FCP)",
                "value": f"{metrics.get('fcp', 0):.1f}s",
                "standard": "< 1.8s (Good), 1.8-3.0s (Needs Improvement), > 3.0s (Poor)",
                "status": LighthouseAnalyzer._get_metric_status(metrics.get('fcp', 0), "fcp")
            },
            {
                "name": "Largest Contentful Paint (LCP)",
                "value": f"{metrics.get('lcp', 0):.1f}s",
                "standard": "< 2.5s (Good), 2.5-4.0s (Needs Improvement), > 4.0s (Poor)",
                "status": LighthouseAnalyzer._get_metric_status(metrics.get('lcp', 0), "lcp")
            },
            {
                "name": "Speed Index",
                "value": f"{metrics.get('speed_index', 0):.1f}s",
                "standard": "< 3.4s (Good), 3.4-5.8s (Needs Improvement), > 5.8s (Poor)",
                "status": LighthouseAnalyzer._get_metric_status(metrics.get('speed_index', 0), "speed_index")
            },
            {
                "name": "Total Blocking Time (TBT)",
                "value": f"{metrics.get('tbt', 0):.0f}ms",
                "standard": "< 200ms (Good), 200-600ms (Needs Improvement), > 600ms (Poor)",
                "status": LighthouseAnalyzer._get_metric_status(metrics.get('tbt', 0), "tbt")
            },
            {
                "name": "Cumulative Layout Shift (CLS)",
                "value": f"{metrics.get('cls', 0):.3f}",
                "standard": "< 0.10 (Good), 0.10-0.25 (Needs Improvement), > 0.25 (Poor)",
                "status": LighthouseAnalyzer._get_metric_status(metrics.get('cls', 0), "cls")
            },
            {
                "name": "Time to Interactive (TTI)",
                "value": f"{metrics.get('tti', 0):.1f}s",
                "standard": "< 3.8s (Good), 3.8-7.3s (Needs Improvement), > 7.3s (Poor)",
                "status": LighthouseAnalyzer._get_metric_status(metrics.get('tti', 0), "tti")
            }
        ]
        
        rows = ""
        for metric in metric_data:
            status = metric["status"]
            severity_class = f"severity-{status['severity'].lower()}"
            rows += f'''
                <tr>
                    <td><strong>{metric['name']}</strong></td>
                    <td>{metric['value']}</td>
                    <td>{metric['standard']}</td>
                    <td class="status-{status['status'].replace('✅ ', '').replace('⚠️ ', '').replace('❌ ', '').lower().replace(' ', '-')}">{status['status']}</td>
                    <td><span class="{severity_class}">{status['severity']}</span></td>
                </tr>'''
        
        perf_score = metrics.get("performance_score", 0)
        
        return f'''<div class="section">
            <h2>Key Performance Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Current Value</th>
                        <th>Industry Standard</th>
                        <th>Status</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <p style="margin-top: 1rem;"><strong>Performance Score:</strong> {perf_score:.0f}/100</p>
        </div>'''
    
    @staticmethod
    def _generate_issues_table(issues: List[Dict[str, Any]], page_data: List[Dict[str, Any]]) -> str:
        """Generate critical issues table with Impacted Pages column"""
        if not issues:
            return '''<div class="section">
                <h2>Issues Identified</h2>
                <p>✅ No critical issues identified. Performance metrics are within acceptable ranges.</p>
            </div>'''
        
        rows = ""
        for issue in issues:
            # Determine impacted pages based on issue type
            impacted_pages = []
            issue_name = issue.get('issue', '').lower()
            
            # Map issues to pages based on metrics
            for page in page_data:
                page_url = page.get("url", "Unknown")
                should_include = False
                
                if "lcp" in issue_name or "loading" in issue_name:
                    if page.get("lcp", 0) > 4.0:
                        should_include = True
                elif "tbt" in issue_name or "blocking" in issue_name or "interactivity" in issue_name:
                    if page.get("tbt", 0) > 600:
                        should_include = True
                elif "cls" in issue_name or "layout" in issue_name or "visual" in issue_name:
                    if page.get("cls", 0) > 0.25:
                        should_include = True
                elif "speed" in issue_name:
                    if page.get("speed_index", 0) > 5.8:
                        should_include = True
                else:
                    # General issue - include all pages
                    should_include = True
                
                if should_include:
                    short_url = page_url if len(page_url) <= 40 else page_url[:37] + "..."
                    impacted_pages.append(short_url)
            
            # If no specific pages, show "All Pages"
            if not impacted_pages:
                impacted_pages = ["All Pages"]
            
            impacted_pages_str = ", ".join(impacted_pages[:3])
            if len(impacted_pages) > 3:
                impacted_pages_str += f" (+{len(impacted_pages) - 3} more)"
            
            rows += f'''
                <tr>
                    <td><strong>{issue.get('issue', 'N/A')}</strong></td>
                    <td>{impacted_pages_str}</td>
                    <td>{issue.get('example', 'N/A')}</td>
                    <td>{issue.get('impact', 'N/A')}</td>
                    <td>{issue.get('recommendation', 'N/A')}</td>
                    <td>{issue.get('business_benefit', 'N/A')}</td>
                </tr>'''
        
        return f'''<div class="section">
            <h2>Issues Identified</h2>
            <table>
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Impacted Pages</th>
                        <th>Example</th>
                        <th>Impact</th>
                        <th>Recommendation</th>
                        <th>Business Benefit</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>'''
    
    @staticmethod
    def _generate_optimization_roadmap(recommendations: Dict[str, Any]) -> str:
        """Generate performance optimization roadmap in tabular format"""
        phases = [
            recommendations.get("phase_1", {}),
            recommendations.get("phase_2", {}),
            recommendations.get("phase_3", {})
        ]
        
        rows = ""
        phase_num = 1
        
        for phase in phases:
            if not phase:
                continue
            
            phase_name = phase.get("name", f"Phase {phase_num}")
            tasks = phase.get("tasks", [])
            expected_impact = phase.get("expected_impact", "N/A")
            
            # Estimate expected grade improvement
            if phase_num == 1:
                expected_grade = "B-C"
            elif phase_num == 2:
                expected_grade = "A-B"
            else:
                expected_grade = "A"
            
            for task in tasks:
                rows += f'''
                    <tr>
                        <td>{phase_name}</td>
                        <td>{task.get('task', 'N/A')}</td>
                        <td>{task.get('effort', 'N/A')}</td>
                        <td>{task.get('expected_impact', 'N/A')}</td>
                        <td>{task.get('owner', 'N/A')}</td>
                        <td>{expected_impact}</td>
                        <td>{expected_grade}</td>
                    </tr>'''
            
            phase_num += 1
        
        if not rows:
            # Default tasks if no recommendations
            rows = '''
                    <tr>
                        <td>Phase 1 (Week 1-2)</td>
                        <td>Enable text compression (gzip/brotli)</td>
                        <td>Low</td>
                        <td>Reduce file sizes by 30-50%</td>
                        <td>DevOps</td>
                        <td>15-25% improvement in LCP and TBT</td>
                        <td>B-C</td>
                    </tr>
                    <tr>
                        <td>Phase 2 (Week 3-6)</td>
                        <td>Defer non-critical JavaScript</td>
                        <td>Medium</td>
                        <td>Reduce TBT by 25-35%</td>
                        <td>Frontend Team</td>
                        <td>20-30% improvement in overall performance score</td>
                        <td>A-B</td>
                    </tr>
                    <tr>
                        <td>Phase 3 (Week 7-12)</td>
                        <td>Implement code splitting and tree shaking</td>
                        <td>High</td>
                        <td>Reduce bundle size by 30-40%</td>
                        <td>Frontend Team</td>
                        <td>30-40% improvement in all metrics, achieve grade A/B</td>
                        <td>A</td>
                    </tr>'''
        
        return f'''<div class="section">
            <h2>Performance Optimization Roadmap</h2>
            <table>
                <thead>
                    <tr>
                        <th>Phase</th>
                        <th>Task</th>
                        <th>Effort Spent</th>
                        <th>Expected Impact</th>
                        <th>Owner</th>
                        <th>Expected Overall Impact</th>
                        <th>Expected Grade</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>'''
    
    @staticmethod
    def _generate_business_impact(business_impact: Dict[str, Any]) -> str:
        """Generate business impact projections with Understanding column"""
        revenue = business_impact.get("revenue_impact", {})
        seo = business_impact.get("seo_impact", {})
        cost_benefit = business_impact.get("cost_benefit", {})
        
        def get_understanding(metric_name: str, value: Any) -> str:
            """Generate understanding text for metrics"""
            if metric_name == "Bounce Rate":
                if isinstance(value, (int, float)) and value > 50:
                    return "High bounce rate indicates poor user engagement. Immediate optimization needed to reduce abandonment and improve user retention."
                elif isinstance(value, (int, float)) and value > 30:
                    return "Moderate bounce rate suggests some user engagement issues. Optimization can help improve retention and conversions."
                else:
                    return "Acceptable bounce rate. Further optimization can still improve user engagement and session depth."
            elif metric_name == "Conversion Rate Lift":
                if isinstance(value, (int, float)) and value > 0:
                    return f"Positive lift of {value}% indicates improved user experience leading to better conversions. Continue optimization to maximize gains."
                elif isinstance(value, (int, float)) and value < 0:
                    return f"Negative impact of {abs(value)}% suggests performance issues are hurting conversions. Urgent optimization required."
                else:
                    return "No significant change. Optimization efforts should focus on improving Core Web Vitals to drive conversion improvements."
            elif metric_name == "Avg Session Duration":
                return "Session duration reflects user engagement. Longer sessions indicate better content relevance and user satisfaction. Target: > 2 minutes."
            elif metric_name == "Page Views per Session":
                return "Higher page views indicate better navigation and content discovery. Target: > 3 pages per session for optimal engagement."
            elif metric_name == "Revenue Impact":
                return "Revenue impact quantifies the financial benefit of performance improvements. Positive values indicate potential revenue gains from optimization."
            elif metric_name == "Core Web Vitals Pass":
                return "Passing Core Web Vitals is essential for SEO ranking. Google uses these metrics as ranking signals, directly impacting organic visibility."
            elif metric_name == "Ranking Factor":
                return "Performance is a key ranking factor. Better Core Web Vitals scores can improve search rankings and organic traffic."
            elif metric_name == "Organic Traffic Impact":
                return "Improved performance can lead to higher search rankings, resulting in increased organic traffic and reduced dependency on paid advertising."
            elif metric_name == "Total Investment":
                return "Investment required for performance optimization. Typically includes development time, tooling, and infrastructure improvements."
            elif metric_name == "Bandwidth Savings":
                return "Optimization reduces data transfer, lowering bandwidth costs and improving performance for users on slower connections."
            elif metric_name == "ROI":
                return "Return on investment measures the financial benefit relative to optimization costs. Positive ROI indicates cost-effective improvements."
            elif metric_name == "Payback Period":
                return "Time required to recover optimization investment through improved performance and business metrics. Shorter periods indicate better value."
            return "Metric indicates performance impact on business outcomes."
        
        revenue_rows = ""
        if revenue:
            for key, value in revenue.items():
                metric_name = key.replace('_', ' ').title()
                understanding = get_understanding(metric_name, value)
                revenue_rows += f'''
                        <tr>
                            <td><strong>{metric_name}</strong></td>
                            <td>{value}</td>
                            <td>{understanding}</td>
                        </tr>'''
        else:
            revenue_rows = '''
                    <tr><td>Bounce Rate</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Conversion Rate Lift</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Avg Session Duration</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Page Views per Session</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Revenue Impact</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>'''
        
        seo_rows = ""
        if seo:
            for key, value in seo.items():
                metric_name = key.replace('_', ' ').title()
                understanding = get_understanding(metric_name, value)
                seo_rows += f'''
                        <tr>
                            <td><strong>{metric_name}</strong></td>
                            <td>{value}</td>
                            <td>{understanding}</td>
                        </tr>'''
        else:
            seo_rows = '''
                    <tr><td>Core Web Vitals Pass</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Ranking Factor</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Organic Traffic Impact</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>'''
        
        cost_benefit_rows = ""
        if cost_benefit:
            for key, value in cost_benefit.items():
                metric_name = key.replace('_', ' ').title()
                understanding = get_understanding(metric_name, value)
                cost_benefit_rows += f'''
                        <tr>
                            <td><strong>{metric_name}</strong></td>
                            <td>{value}</td>
                            <td>{understanding}</td>
                        </tr>'''
        else:
            cost_benefit_rows = '''
                    <tr><td>Total Investment</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Bandwidth Savings</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>ROI</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>
                    <tr><td>Payback Period</td><td>N/A</td><td>Metric indicates performance impact on business outcomes.</td></tr>'''
        
        return f'''<div class="section">
            <h2>Business Impact Projections</h2>
            
            <h3>Revenue Impact Analysis</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Current/Projected</th>
                        <th>Understanding</th>
                    </tr>
                </thead>
                <tbody>
                    {revenue_rows}
                </tbody>
            </table>
            
            <h3>SEO & Organic Traffic Impact</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Status</th>
                        <th>Understanding</th>
                    </tr>
                </thead>
                <tbody>
                    {seo_rows}
                </tbody>
            </table>
            
            <h3>Cost-Benefit Analysis</h3>
            <table>
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Value</th>
                        <th>Understanding</th>
                    </tr>
                </thead>
                <tbody>
                    {cost_benefit_rows}
                </tbody>
            </table>
        </div>'''
    
    @staticmethod
    def _generate_monitoring_maintenance() -> str:
        """Generate monitoring and maintenance section"""
        return '''<div class="section">
            <h2>Next Steps for Monitoring and Maintenance</h2>
            
            <h3>Immediate Setup</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                <li>Real User Monitoring (RUM) - Set up tools like Google Analytics, New Relic, or Datadog</li>
                <li>Lighthouse CI - Integrate into CI/CD pipeline for automated performance testing</li>
                <li>WebPageTest - Schedule regular synthetic monitoring</li>
                <li>APM Tools - Configure Application Performance Monitoring</li>
                <li>Performance Alerts - Set up alerts for threshold violations</li>
            </ul>
            
            <h3>Ongoing Monitoring Strategy</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Frequency</th>
                        <th>Threshold</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>LCP</td><td>Daily</td><td>&lt; 2.5s</td><td>Alert if exceeded</td></tr>
                    <tr><td>TBT</td><td>Daily</td><td>&lt; 200ms</td><td>Alert if exceeded</td></tr>
                    <tr><td>CLS</td><td>Daily</td><td>&lt; 0.10</td><td>Alert if exceeded</td></tr>
                    <tr><td>Performance Score</td><td>Weekly</td><td>&gt; 90</td><td>Review if below</td></tr>
                </tbody>
            </table>
            
            <h3>Performance Budget Framework</h3>
            <table>
                <thead>
                    <tr>
                        <th>Resource</th>
                        <th>Budget</th>
                        <th>Current</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>JavaScript Size</td><td>&lt; 200KB</td><td>Monitor</td><td>Track</td></tr>
                    <tr><td>CSS Size</td><td>&lt; 50KB</td><td>Monitor</td><td>Track</td></tr>
                    <tr><td>Image Size</td><td>&lt; 500KB</td><td>Monitor</td><td>Track</td></tr>
                    <tr><td>Total Page Weight</td><td>&lt; 1MB</td><td>Monitor</td><td>Track</td></tr>
                </tbody>
            </table>
            
            <h3>Monthly Review Process</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                <li>Review performance trends and identify regressions</li>
                <li>Analyze user feedback and support tickets related to performance</li>
                <li>Update performance budgets based on business requirements</li>
                <li>Review and prioritize optimization opportunities</li>
                <li>Share performance metrics with stakeholders</li>
            </ul>
        </div>'''
    
    @staticmethod
    def _generate_aiml_appendix(aiml_results: Dict[str, Any]) -> str:
        """Generate AIML modeling appendix"""
        if not aiml_results:
            return '''<div class="section">
                <h2>AIML Modeling Appendix</h2>
                <p>AIML modeling was not performed for this analysis.</p>
            </div>'''
        
        data_sources = aiml_results.get("data_sources", "N/A")
        features = aiml_results.get("features_used", [])
        models = aiml_results.get("models", {})
        predictions = aiml_results.get("predictions", {})
        comparison = aiml_results.get("comparison", {})
        assumptions = aiml_results.get("assumptions", [])
        
        return f'''<div class="section">
            <h2>AIML Modeling Appendix</h2>
            
            <h3>Data Sources</h3>
            <p>{data_sources}</p>
            
            <h3>Feature Set</h3>
            <p><strong>Features Used:</strong> {', '.join(features) if isinstance(features, list) else features}</p>
            <p><strong>Feature Engineering:</strong> {aiml_results.get('feature_engineering', 'N/A')}</p>
            
            <h3>Model Types and Performance</h3>
            <table>
                <thead>
                    <tr>
                        <th>Model Type</th>
                        <th>Model Name</th>
                        <th>Metric</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td rowspan="2">Classification</td><td>Logistic Regression</td><td>Accuracy</td><td>{models.get('classification', {}).get('logistic_regression', {}).get('accuracy', 'N/A')}</td></tr>
                    <tr><td>Logistic Regression</td><td>F1 Score</td><td>{models.get('classification', {}).get('logistic_regression', {}).get('f1_score', 'N/A')}</td></tr>
                    <tr><td rowspan="2">Classification</td><td>Random Forest</td><td>Accuracy</td><td>{models.get('classification', {}).get('random_forest', {}).get('accuracy', 'N/A')}</td></tr>
                    <tr><td>Random Forest</td><td>F1 Score</td><td>{models.get('classification', {}).get('random_forest', {}).get('f1_score', 'N/A')}</td></tr>
                    <tr><td>Regression</td><td>Ridge</td><td>RMSE</td><td>{models.get('regression', {}).get('ridge', {}).get('rmse', 'N/A')}</td></tr>
                    <tr><td>Regression</td><td>Gradient Boosting</td><td>RMSE</td><td>{models.get('regression', {}).get('gradient_boosting', {}).get('rmse', 'N/A')}</td></tr>
                    <tr><td rowspan="2">Neural Network</td><td>MLP Regressor</td><td>Architecture</td><td>{models.get('neural_network', {}).get('architecture', 'N/A')}</td></tr>
                    <tr><td>MLP Regressor</td><td>RMSE</td><td>{models.get('neural_network', {}).get('rmse', 'N/A')}</td></tr>
                </tbody>
            </table>
            
            <h3>Predictions</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Predicted Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Predicted Grade</td><td>{predictions.get('predicted_grade', 'N/A')}</td></tr>
                    <tr><td>NN Predicted Score</td><td>{predictions.get('predicted_score_nn', 'N/A')}</td></tr>
                    <tr><td>Predicted Bounce Rate</td><td>{predictions.get('predicted_bounce_rate', 'N/A')}%</td></tr>
                    <tr><td>Predicted Conversion Lift</td><td>{predictions.get('predicted_conversion_lift', 'N/A')}%</td></tr>
                </tbody>
            </table>
            
            <h3>Comparison: Weighted Formula vs Neural Network</h3>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Score</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Weighted Formula</td><td>{comparison.get('weighted_formula_score', 'N/A')}</td></tr>
                    <tr><td>Neural Network Prediction</td><td>{comparison.get('nn_predicted_score', 'N/A')}</td></tr>
                    <tr><td>Difference</td><td>{comparison.get('difference', 'N/A')}</td></tr>
                </tbody>
            </table>
            
            <h3>Assumptions and Limitations</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li>{assumption}</li>' for assumption in assumptions)}
            </ul>
        </div>'''
    
    @staticmethod
    def _generate_final_conclusion(metrics: Dict[str, Any], grades: Dict[str, Any], overall_grade: Dict[str, Any]) -> str:
        """Generate final conclusion"""
        overall_score = overall_grade.get("score", 0)
        overall_letter = overall_grade.get("letter_grade", "N/A")
        
        # Key takeaways
        takeaways = []
        if overall_score >= 80:
            takeaways.append("Performance is strong and meets industry standards")
        elif overall_score >= 60:
            takeaways.append("Performance is acceptable but has room for improvement")
        else:
            takeaways.append("Performance requires immediate attention and optimization")
        
        if grades.get("loading", {}).get("grade") in ["A", "B"]:
            takeaways.append("Loading experience is good")
        else:
            takeaways.append("Loading experience needs improvement")
        
        if grades.get("interactivity", {}).get("grade") in ["A", "B"]:
            takeaways.append("Interactivity is responsive")
        else:
            takeaways.append("Interactivity needs optimization to reduce blocking time")
        
        if grades.get("visual_stability", {}).get("grade") in ["A", "B"]:
            takeaways.append("Visual stability is good with minimal layout shifts")
        else:
            takeaways.append("Visual stability needs improvement to reduce layout shifts")
        
        # Strengths
        strengths = []
        if grades.get("loading", {}).get("grade") in ["A", "B"]:
            strengths.append("Fast loading times")
        if grades.get("interactivity", {}).get("grade") in ["A", "B"]:
            strengths.append("Responsive interactivity")
        if grades.get("visual_stability", {}).get("grade") in ["A", "B"]:
            strengths.append("Stable visual layout")
        if not strengths:
            strengths.append("Baseline established for improvement")
        
        # Areas for improvement
        improvements = []
        if grades.get("loading", {}).get("grade") not in ["A", "B"]:
            improvements.append("Optimize Largest Contentful Paint (LCP)")
        if grades.get("interactivity", {}).get("grade") not in ["A", "B"]:
            improvements.append("Reduce Total Blocking Time (TBT)")
        if grades.get("visual_stability", {}).get("grade") not in ["A", "B"]:
            improvements.append("Minimize Cumulative Layout Shift (CLS)")
        if not improvements:
            improvements.append("Continue monitoring and maintain current performance levels")
        
        # Immediate actions
        actions = [
            "Review and prioritize issues identified in this report",
            "Implement Phase 1 optimization tasks",
            "Set up performance monitoring and alerts",
            "Establish performance budgets and review process"
        ]
        
        return f'''<div class="section">
            <h2>Final Conclusion</h2>
            
            <p>The performance analysis reveals an overall grade of <strong>{overall_letter}</strong> with a score of <strong>{overall_score:.1f}/100</strong>. 
            {'The performance meets industry standards' if overall_score >= 70 else 'The performance requires optimization to meet industry standards'}.</p>
            
            <h3>Key Takeaways</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li>{takeaway}</li>' for takeaway in takeaways)}
            </ul>
            
            <h3>Key Strengths</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li>{strength}</li>' for strength in strengths)}
            </ul>
            
            <h3>Areas for Improvement</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li>{improvement}</li>' for improvement in improvements)}
            </ul>
            
            <h3>Recommended Immediate Actions</h3>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                {''.join(f'<li>{action}</li>' for action in actions)}
            </ul>
            
            <h3>Success Metrics</h3>
            <p>Target metrics for optimal performance:</p>
            <ul style="margin-left: 2rem; margin-top: 1rem;">
                <li>LCP &lt; 2.5s</li>
                <li>TBT &lt; 200ms</li>
                <li>CLS &lt; 0.10</li>
                <li>Performance Score &gt; 90/100</li>
            </ul>
        </div>'''
    
    @staticmethod
    def _generate_report_details(metadata: Dict[str, Any]) -> str:
        """Generate report details footer"""
        report_date = metadata.get("report_date", datetime.now().strftime("%Y-%m-%d"))
        next_review = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        prepared_by = metadata.get("prepared_by", "Raghvendra Kumar")
        
        return f'''<div class="footer">
            <p><strong>Report Date:</strong> {report_date}</p>
            <p><strong>Next Review Scheduled:</strong> {next_review}</p>
            <p><strong>Prepared By:</strong> {prepared_by}</p>
            <p><strong>Document Classification:</strong> Internal</p>
            <p><strong>Distribution:</strong> Performance Team, Development Team, Product Management</p>
        </div>'''

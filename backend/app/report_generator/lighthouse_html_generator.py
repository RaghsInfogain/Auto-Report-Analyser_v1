"""
Lighthouse HTML Report Generator
Generates comprehensive HTML reports for Lighthouse performance analysis
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import html


class LighthouseHTMLGenerator:
    """Generate HTML reports for Lighthouse analysis"""
    
    @staticmethod
    def generate_full_report(analysis: Dict[str, Any], filename: str = "lighthouse_report.html") -> str:
        """Generate complete HTML report"""
        try:
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
            
            # Debug: Log page_data info
            print(f"  📊 HTML Generator: page_data count = {len(page_data) if page_data else 0}")
            print(f"  📊 HTML Generator: analysis keys = {list(analysis.keys())}")
            if page_data and len(page_data) > 0:
                print(f"  📊 HTML Generator: First page keys = {list(page_data[0].keys()) if isinstance(page_data[0], dict) else 'Not a dict'}")
                print(f"  📊 HTML Generator: First page data = {page_data[0] if isinstance(page_data[0], dict) else 'Not a dict'}")
                # Check if metrics are present
                first_page = page_data[0] if isinstance(page_data[0], dict) else {}
                print(f"  📊 HTML Generator: First page fcp = {first_page.get('fcp', 'MISSING')}")
                print(f"  📊 HTML Generator: First page lcp = {first_page.get('lcp', 'MISSING')}")
                print(f"  📊 HTML Generator: First page page_title = {first_page.get('page_title', 'MISSING')}")
                print(f"  📊 HTML Generator: First page url = {first_page.get('url', 'MISSING')}")
            
            # Ensure page_data is a list
            if not isinstance(page_data, list):
                print(f"  ⚠️  Warning: page_data is not a list, converting...")
                if page_data:
                    page_data = [page_data]
                else:
                    page_data = []
            
            # Generate sections with error handling and logging
            sections = []
            section_names = []
            
            print(f"\n  📄 HTML REPORT GENERATION: Starting section generation...")
            print(f"  {'='*60}")
            
            try:
                print(f"  [1/12] Generating Header...")
                sections.append(LighthouseHTMLGenerator._generate_header(metadata))
                section_names.append("Header")
                print(f"      ✓ Header generated")
            except Exception as e:
                print(f"      ✗ Error generating header: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Header</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Header (Error)")
            
            try:
                print(f"  [2/12] Generating Executive Summary...")
                sections.append(LighthouseHTMLGenerator._generate_executive_summary(metrics, grades, overall_grade, issues))
                section_names.append("Executive Summary")
                print(f"      ✓ Executive Summary generated")
            except Exception as e:
                print(f"      ✗ Error generating executive summary: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Executive Summary</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Executive Summary (Error)")
            
            try:
                print(f"  [3/12] Generating Performance Scorecard...")
                sections.append(LighthouseHTMLGenerator._generate_performance_scorecard(metrics, grades, overall_grade))
                section_names.append("Performance Scorecard")
                print(f"      ✓ Performance Scorecard generated")
            except Exception as e:
                print(f"      ✗ Error generating performance scorecard: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Performance Scorecard</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Performance Scorecard (Error)")
            
            try:
                print(f"  [4/12] Generating Test Overview...")
                sections.append(LighthouseHTMLGenerator._generate_test_overview(test_overview, metadata))
                section_names.append("Test Overview")
                print(f"      ✓ Test Overview generated")
            except Exception as e:
                print(f"      ✗ Error generating test overview: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Test Overview</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Test Overview (Error)")
            
            try:
                print(f"  [5/12] Generating Detailed Performance Metrics...")
                sections.append(LighthouseHTMLGenerator._generate_detailed_metrics_table(page_data))
                section_names.append("Detailed Performance Metrics")
                print(f"      ✓ Detailed Performance Metrics generated ({len(page_data)} pages)")
            except Exception as e:
                print(f"      ✗ Error generating detailed metrics table: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Detailed Performance Metrics</h2><p>Error generating table: {str(e)}<br>Page data: {len(page_data) if page_data else 0} pages</p></div>")
                section_names.append("Detailed Performance Metrics (Error)")
            
            try:
                print(f"  [6/12] Generating Issues Identified...")
                sections.append(LighthouseHTMLGenerator._generate_issues_table(issues, page_data))
                section_names.append("Issues Identified")
                print(f"      ✓ Issues Identified generated ({len(issues)} issues)")
            except Exception as e:
                print(f"      ✗ Error generating issues table: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Issues Identified</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Issues Identified (Error)")
            
            try:
                print(f"  [7/12] Generating Performance Optimization Roadmap...")
                sections.append(LighthouseHTMLGenerator._generate_optimization_roadmap(recommendations))
                section_names.append("Performance Optimization Roadmap")
                print(f"      ✓ Performance Optimization Roadmap generated")
            except Exception as e:
                print(f"      ✗ Error generating optimization roadmap: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Performance Optimization Roadmap</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Performance Optimization Roadmap (Error)")
            
            try:
                print(f"  [8/12] Generating Business Impact Projections...")
                sections.append(LighthouseHTMLGenerator._generate_business_impact(business_impact))
                section_names.append("Business Impact Projections")
                print(f"      ✓ Business Impact Projections generated")
            except Exception as e:
                print(f"      ✗ Error generating business impact: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Business Impact Projections</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Business Impact Projections (Error)")
            
            try:
                print(f"  [9/12] Generating Monitoring and Maintenance...")
                sections.append(LighthouseHTMLGenerator._generate_monitoring_maintenance())
                section_names.append("Monitoring and Maintenance")
                print(f"      ✓ Monitoring and Maintenance generated")
            except Exception as e:
                print(f"      ✗ Error generating monitoring maintenance: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Monitoring and Maintenance</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Monitoring and Maintenance (Error)")
            
            try:
                print(f"  [10/12] Generating AIML Modeling Appendix...")
                sections.append(LighthouseHTMLGenerator._generate_aiml_appendix(aiml_results))
                section_names.append("AIML Modeling Appendix")
                print(f"      ✓ AIML Modeling Appendix generated")
            except Exception as e:
                print(f"      ✗ Error generating AIML appendix: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>AIML Modeling Appendix</h2><p>Error: {str(e)}</p></div>")
                section_names.append("AIML Modeling Appendix (Error)")
            
            try:
                print(f"  [11/12] Generating Final Conclusion...")
                sections.append(LighthouseHTMLGenerator._generate_final_conclusion(metrics, grades, overall_grade))
                section_names.append("Final Conclusion")
                print(f"      ✓ Final Conclusion generated")
            except Exception as e:
                print(f"      ✗ Error generating final conclusion: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Final Conclusion</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Final Conclusion (Error)")
            
            try:
                print(f"  [12/12] Generating Report Details...")
                sections.append(LighthouseHTMLGenerator._generate_report_details(metadata))
                section_names.append("Report Details")
                print(f"      ✓ Report Details generated")
            except Exception as e:
                print(f"      ✗ Error generating report details: {e}")
                import traceback
                traceback.print_exc()
                sections.append(f"<div class='section'><h2>Report Details</h2><p>Error: {str(e)}</p></div>")
                section_names.append("Report Details (Error)")
            
            print(f"\n  ✓ All sections generated: {len(sections)} sections")
            print(f"  Sections: {', '.join(section_names)}")
            
            # Verify all critical sections are present
            critical_sections = [
                "Issues Identified",
                "Performance Optimization Roadmap",
                "Business Impact Projections",
                "Next Steps for Monitoring and Maintenance",
                "AIML Modeling Appendix",
                "Final Conclusion"
            ]
            
            print(f"\n  🔍 Verifying critical sections in generated HTML:")
            all_sections_html = ''.join(sections)
            for section_name in critical_sections:
                if section_name in all_sections_html:
                    print(f"      ✓ {section_name} present")
                else:
                    print(f"      ⚠️  {section_name} not found in HTML (may be in error state)")
            
            print(f"  {'='*60}\n")
            
            # Combine all sections
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
        {all_sections_html}
    </div>
</body>
</html>'''
            
            # Final verification
            print(f"  📊 Final HTML size: {len(html):,} characters")
            print(f"  📊 Sections count: {len(sections)}")
            
            return html
        except Exception as e:
            print(f"  ✗ Critical error in generate_full_report: {e}")
            import traceback
            traceback.print_exc()
            # Return a minimal error report
            return f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Report Generation Error</title>
</head>
<body>
    <h1>Report Generation Error</h1>
    <p>An error occurred while generating the report: {str(e)}</p>
    <pre>{traceback.format_exc()}</pre>
</body>
</html>'''
    
    @staticmethod
    def _generate_css() -> str:
        """Generate CSS styles"""
        return '''<style>
        :root {
            --primary-color: #6c5ce7;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --background-light: #f5f5f5;
            --card-background: #ffffff;
            --text-primary: #333;
            --text-secondary: #666;
            --border-color: #e0e0e0;
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
            background: white;
            margin: 1.5rem 0;
            padding: 1.5rem;
            border-radius: 4px;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
            border: 1px solid #e0e0e0;
        }

        .section h2 {
            color: #333;
            font-size: 1.125rem;
            font-weight: 600;
            margin: 0 0 1.5rem 0;
            padding-bottom: 1rem;
            border-bottom: 1px solid #e0e0e0;
        }

        .section h3 {
            color: #333;
            font-size: 1rem;
            font-weight: 600;
            margin: 1.5rem 0 1rem 0;
        }

        .executive-summary {
            background: white;
            color: #333;
            padding: 1.5rem;
            border-radius: 4px;
            margin: 1.5rem 0;
            border: 1px solid #e0e0e0;
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
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
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
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-weight: 500;
            font-size: 0.75rem;
            margin: 0.5rem;
        }

        .grade-a { background: #d4edda; color: #155724; }
        .grade-b { background: #d1ecf1; color: #0c5460; }
        .grade-c { background: #fff3cd; color: #856404; }
        .grade-d { background: #f8d7da; color: #721c24; }
        .grade-e { background: #f8d7da; color: #721c24; }
        .grade-f { background: #f8d7da; color: #721c24; }
        
        .scorecard-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 1.5rem;
            text-align: center;
            transition: box-shadow 0.2s;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            word-wrap: break-word;
            overflow-wrap: break-word;
            /* Removed overflow: hidden to prevent content from being cut off */
        }
        
        .scorecard-card:hover {
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }
        
        .scorecard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin: 1.5rem 0;
        }
        
        .card-value {
            font-size: 1.5rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.5rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.2;
            max-width: 100%;
        }
        
        .card-value-large {
            font-size: 1.25rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 0.5rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.2;
            max-width: 100%;
        }
        
        @media (max-width: 768px) {
            .card-value {
                font-size: 2rem;
            }
            .card-value-large {
                font-size: 1.4rem;
            }
            .scorecard-card {
                min-height: 120px;
            }
            .category-card {
                min-height: 180px;
            }
        }
        
        /* Ensure long text values wrap */
        .scorecard-card > * {
            max-width: 100%;
        }
        
        .category-card > * {
            max-width: 100%;
        }
        
        .card-title {
            margin: 0.5rem 0;
            color: #333;
            font-size: 0.875rem;
            font-weight: 600;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        
        .card-description {
            margin: 0;
            color: #666;
            font-size: 0.875rem;
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.4;
        }
        
        .category-card {
            background: #f8f9fa;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 1.5rem;
            text-align: center;
            word-wrap: break-word;
            overflow-wrap: break-word;
            overflow: hidden;
            min-height: 150px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .category-card p {
            word-wrap: break-word;
            overflow-wrap: break-word;
            line-height: 1.4;
            max-width: 100%;
        }
        
        .grade-card {
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            padding: 1rem;
            margin: 0.5rem 0;
        }
        
        .risk-card {
            padding: 1.5rem;
            border-radius: 4px;
            margin: 1.5rem 0;
            background: white;
            border: 1px solid #e0e0e0;
        }

        table {
            width: 100%;
            border-collapse: collapse;
            margin: 1rem 0;
            font-size: 0.875rem;
            background: white;
            border: 1px solid #e0e0e0;
        }

        table th,
        table td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
            vertical-align: middle;
        }

        table thead {
            background: #f8f9fa;
            border-bottom: 2px solid #e0e0e0;
        }

        table th {
            font-weight: 600;
            color: #666;
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            padding: 0.75rem 1rem;
        }

        table td {
            color: #333;
            padding: 1rem;
        }

        table tbody tr {
            transition: background 0.2s;
            background: white;
        }

        table tbody tr:hover {
            background: #f8f9fa;
        }

        table tbody tr:last-child td {
            border-bottom: none;
        }

        .status-good { 
            color: #059669; 
            font-weight: 600; 
            background: #d1fae5; 
            padding: 0.25rem 0.5rem; 
            border-radius: 4px; 
            display: inline-block;
        }
        .status-warning { 
            color: #d97706; 
            font-weight: 600; 
            background: #fef3c7; 
            padding: 0.25rem 0.5rem; 
            border-radius: 4px; 
            display: inline-block;
        }
        .status-poor { 
            color: #dc2626; 
            font-weight: 600; 
            background: #fee2e2; 
            padding: 0.25rem 0.5rem; 
            border-radius: 4px; 
            display: inline-block;
        }
        .status-critical { 
            color: #991b1b; 
            font-weight: 700; 
            background: #fecaca; 
            padding: 0.25rem 0.5rem; 
            border-radius: 4px; 
            display: inline-block;
        }

        .severity-low { background: #d1fae5; color: #065f46; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-medium { background: #fef3c7; color: #92400e; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-high { background: #fee2e2; color: #991b1b; padding: 0.25rem 0.5rem; border-radius: 4px; }
        .severity-critical { background: #fecaca; color: #7f1d1d; padding: 0.25rem 0.5rem; border-radius: 4px; font-weight: 700; }

        .alert {
            padding: 1rem;
            border-radius: 4px;
            margin: 1rem 0;
            border-left: 4px solid;
        }

        .alert-danger {
            background: #fee2e2;
            border-color: #ef4444;
            color: #991b1b;
        }

        .alert-warning {
            background: #fef3c7;
            border-color: #f59e0b;
            color: #92400e;
        }

        .phase-section {
            margin: 1.5rem 0;
            padding: 1rem;
            background: #f8f9fa;
            border-radius: 4px;
            border: 1px solid #e0e0e0;
        }

        .footer {
            margin-top: 3rem;
            padding-top: 2rem;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #666;
            font-size: 0.875rem;
        }

        @media (max-width: 768px) {
            .header h1 { font-size: 1.25rem; }
            .summary-grid { grid-template-columns: 1fr; }
            .scorecard-grid { grid-template-columns: 1fr; }
            table { font-size: 0.75rem; }
            .card-value {
                font-size: 1.25rem;
            }
            .card-value-large {
                font-size: 1rem;
            }
            .scorecard-card {
                min-height: 100px;
            }
            .category-card {
                min-height: 120px;
            }
        }
    </style>'''
    
    @staticmethod
    def _generate_header(metadata: Dict[str, Any]) -> str:
        """Generate report header"""
        return f'''<div class="header">
            <h1>Performance Test Analysis Report</h1>
            <p style="font-size: 0.875rem; color: #666; margin-top: 0.5rem;">User Experience Monitoring Analysis</p>
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
        
        # Get detailed grade info - FIXED: Use score_value for scores, score for metric values
        loading_info = grades.get("loading", {})
        loading_score = loading_info.get("score_value", 0)  # This is the 0-100 score
        loading_metric = loading_info.get("score", 0)  # This is the actual LCP value in seconds
        loading_name = "LCP"
        
        interactivity_info = grades.get("interactivity", {})
        interactivity_score = interactivity_info.get("score_value", 0)  # This is the 0-100 score
        interactivity_metric = interactivity_info.get("score", 0)  # This is the actual TBT value in milliseconds
        interactivity_name = "TBT"
        
        visual_info = grades.get("visual_stability", {})
        visual_score = visual_info.get("score_value", 0)  # This is the 0-100 score
        visual_metric = visual_info.get("score", 0)  # This is the actual CLS value
        visual_name = "CLS"
        
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
            
            <!-- Category Cards - FIXED: Dark text on light backgrounds for visibility -->
            <div class="summary-grid" style="margin-top: 2rem;">
                <div class="category-card" style="background: white; border: 1px solid #e0e0e0; padding: 1.5rem; border-radius: 8px;">
                    <div class="grade-badge grade-{loading_grade.lower()}" style="font-size: 2rem; margin-bottom: 1rem;">{loading_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: #333; font-weight: 600; word-wrap: break-word; overflow-wrap: break-word;">Loading Experience</h3>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #6c5ce7; margin: 0.5rem 0;">{loading_score:.0f}/100</div>
                    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.85rem; line-height: 1.4; word-wrap: break-word; overflow-wrap: break-word;">{get_grade_explanation(loading_grade, loading_name, loading_metric)}</p>
                </div>
                
                <div class="category-card" style="background: white; border: 1px solid #e0e0e0; padding: 1.5rem; border-radius: 8px;">
                    <div class="grade-badge grade-{interactivity_grade.lower()}" style="font-size: 2rem; margin-bottom: 1rem;">{interactivity_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: #333; font-weight: 600; word-wrap: break-word; overflow-wrap: break-word;">Interactivity Experience</h3>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #6c5ce7; margin: 0.5rem 0;">{interactivity_score:.0f}/100</div>
                    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.85rem; line-height: 1.4; word-wrap: break-word; overflow-wrap: break-word;">{get_grade_explanation(interactivity_grade, interactivity_name, interactivity_metric)}</p>
                </div>
                
                <div class="category-card" style="background: white; border: 1px solid #e0e0e0; padding: 1.5rem; border-radius: 8px;">
                    <div class="grade-badge grade-{visual_grade.lower()}" style="font-size: 2rem; margin-bottom: 1rem;">{visual_grade}</div>
                    <h3 style="margin: 0.5rem 0; color: #333; font-weight: 600; word-wrap: break-word; overflow-wrap: break-word;">Visual Stability</h3>
                    <div style="font-size: 1.5rem; font-weight: 700; color: #6c5ce7; margin: 0.5rem 0;">{visual_score:.0f}/100</div>
                    <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 0.85rem; line-height: 1.4; word-wrap: break-word; overflow-wrap: break-word;">{get_grade_explanation(visual_grade, visual_name, visual_metric)}</p>
                </div>
            </div>
            
            <!-- Key Findings - FIXED: Dark text on light background -->
            <div style="margin-top: 2rem; padding: 1.5rem; background: #f8f9fa; border: 1px solid #e0e0e0; border-radius: 8px;">
                <h3 style="margin-top: 0; color: #333; font-weight: 600;">Key Findings</h3>
                <ul style="margin: 1rem 0 0 0; padding-left: 1.5rem; color: #666;">
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
        
        # Get category details - FIXED: Use score_value for scores (0-100)
        loading_grade = grades.get("loading", {}).get("grade", "N/A")
        loading_score = grades.get("loading", {}).get("score_value", 0)  # 0-100 score
        loading_weight = "50%"
        
        interactivity_grade = grades.get("interactivity", {}).get("grade", "N/A")
        interactivity_score = grades.get("interactivity", {}).get("score_value", 0)  # 0-100 score
        interactivity_weight = "30%"
        
        visual_grade = grades.get("visual_stability", {}).get("grade", "N/A")
        visual_score = grades.get("visual_stability", {}).get("score_value", 0)  # 0-100 score
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
                <h3 class="card-title">Overall Grade</h3>
                <p class="card-description" style="margin: 0.5rem 0;">{get_overall_grade_meaning(overall_letter, overall_score)}</p>
                <div style="margin-top: 1rem;">
                    <div style="font-size: 2rem; font-weight: 700; color: var(--primary-color); word-wrap: break-word;">{overall_score:.1f}/100</div>
                    <div style="color: var(--text-secondary); margin-top: 0.5rem; word-wrap: break-word;">Score Range: {grade_ranges.get(overall_letter, "N/A")}</div>
                </div>
            </div>
            
            <!-- Category Cards -->
            <div class="scorecard-grid">
                <div class="scorecard-card">
                    <div class="grade-badge grade-{loading_grade.lower()}" style="font-size: 1.5rem; margin-bottom: 1rem;">{loading_grade}</div>
                    <h3 class="card-title">Loading Experience</h3>
                    <p class="card-description">{grade_meanings.get(loading_grade, "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color); word-wrap: break-word;">{loading_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem; word-wrap: break-word;">Weightage: {loading_weight}</div>
                    </div>
                </div>
                
                <div class="scorecard-card">
                    <div class="grade-badge grade-{interactivity_grade.lower()}" style="font-size: 1.5rem; margin-bottom: 1rem;">{interactivity_grade}</div>
                    <h3 class="card-title">Interactivity Experience</h3>
                    <p class="card-description">{grade_meanings.get(interactivity_grade, "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color); word-wrap: break-word;">{interactivity_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem; word-wrap: break-word;">Weightage: {interactivity_weight}</div>
                    </div>
                </div>
                
                <div class="scorecard-card">
                    <div class="grade-badge grade-{visual_grade.lower()}" style="font-size: 1.5rem; margin-bottom: 1rem;">{visual_grade}</div>
                    <h3 class="card-title">Visual Stability</h3>
                    <p class="card-description">{grade_meanings.get(visual_grade, "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color); word-wrap: break-word;">{visual_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem; word-wrap: break-word;">Weightage: {visual_weight}</div>
                    </div>
                </div>
                
                <div class="scorecard-card">
                    <div class="grade-badge grade-{"a" if perf_score >= 90 else "b" if perf_score >= 80 else "c" if perf_score >= 70 else "d" if perf_score >= 60 else "e" if perf_score >= 40 else "f"}" style="font-size: 1.5rem; margin-bottom: 1rem;">{"A" if perf_score >= 90 else "B" if perf_score >= 80 else "C" if perf_score >= 70 else "D" if perf_score >= 60 else "E" if perf_score >= 40 else "F"}</div>
                    <h3 class="card-title">Performance Score</h3>
                    <p class="card-description">{grade_meanings.get("A" if perf_score >= 90 else "B" if perf_score >= 80 else "C" if perf_score >= 70 else "D" if perf_score >= 60 else "E" if perf_score >= 40 else "F", "N/A")}</p>
                    <div style="margin-top: 1rem;">
                        <div style="font-size: 1.5rem; font-weight: 700; color: var(--primary-color); word-wrap: break-word;">{perf_score:.0f}/100</div>
                        <div style="color: var(--text-secondary); margin-top: 0.5rem; word-wrap: break-word;">Range: 0-100</div>
                    </div>
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
        page_components = test_overview.get("page_components", "N/A")
        data_processed = test_overview.get("data_processed", "N/A")
        test_config = test_overview.get("test_config", [])
        test_objectives = test_overview.get("test_objectives", [])
        
        return f'''<div class="section">
            <h2>Test Overview</h2>
            
            <!-- Overview Cards -->
            <div class="scorecard-grid">
                <div class="scorecard-card">
                    <div class="card-value">{total_pages}</div>
                    <h3 class="card-title">Total Pages</h3>
                    <p class="card-description">Pages analyzed</p>
                </div>
                
                <div class="scorecard-card">
                    <div class="card-value-large">{test_duration}</div>
                    <h3 class="card-title">Test Duration</h3>
                    <p class="card-description">Time taken for analysis</p>
                </div>
                
                <div class="scorecard-card">
                    <div class="card-value-large">{page_components}</div>
                    <h3 class="card-title">Page Components</h3>
                    <p class="card-description">Total page components across all pages</p>
                </div>
                
                <div class="scorecard-card">
                    <div class="card-value-large">{data_processed}</div>
                    <h3 class="card-title">Data Processed</h3>
                    <p class="card-description">Total data size across all pages</p>
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
        
        # Ensure page_data is a list
        if not isinstance(page_data, list):
            print(f"  ⚠️  Warning: page_data is not a list in _generate_detailed_metrics_table")
            if page_data:
                page_data = [page_data]
            else:
                return '''<div class="section">
                    <h2>Detailed Performance Metrics</h2>
                    <p>No page data available.</p>
                </div>'''
        
        rows = ""
        print(f"  📊 Generating table for {len(page_data)} pages")
        for idx, page in enumerate(page_data, 1):
            try:
                # Debug: Log each page's metrics
                if isinstance(page, dict):
                    print(f"    Page {idx}: URL={page.get('url', 'N/A')[:50]}..., LCP={page.get('lcp', 0)*1000:.0f}ms, FCP={page.get('fcp', 0)*1000:.0f}ms, TBT={page.get('tbt', 0):.0f}ms, Title={page.get('page_title', 'N/A')[:30]}")
                
                # Safely get values with defaults
                url = page.get("url", f"Page {idx}") if isinstance(page, dict) else f"Page {idx}"
                page_title = page.get("page_title", "") if isinstance(page, dict) else ""
                
                # Use run number if available for better identification
                run_number = page.get("_run_number", "") if isinstance(page, dict) else ""
                if run_number and run_number not in url:
                    display_url = f"{url} ({run_number})"
                else:
                    display_url = url
                
                # Shorten URL for display but preserve uniqueness
                if len(display_url) > 50:
                    # Show first part and last part to preserve uniqueness
                    display_url = display_url[:30] + "..." + display_url[-17:] if len(display_url) > 47 else display_url[:47] + "..."
                
                # Use page title if available and valid, otherwise use URL
                # Clean page_title - remove any problematic characters
                if page_title:
                    page_title = str(page_title).strip()
                    # Remove trailing backticks, quotes, or incomplete strings
                    page_title = page_title.rstrip("`'\"")
                    # If title looks incomplete or problematic, use URL instead
                    if len(page_title) < 3 or page_title.endswith(" a`") or "`" in page_title:
                        page_title = ""
                
                page_name_display = page_title if page_title and len(page_title) > 2 else display_url
                if len(page_name_display) > 50:
                    page_name_display = page_name_display[:47] + "..."
                
                # Safely extract metrics with type checking
                fcp = float(page.get("fcp", 0)) if isinstance(page, dict) else 0
                lcp = float(page.get("lcp", 0)) if isinstance(page, dict) else 0
                speed_index = float(page.get("speed_index", 0)) if isinstance(page, dict) else 0
                tbt = float(page.get("tbt", 0)) if isinstance(page, dict) else 0
                cls = float(page.get("cls", 0)) if isinstance(page, dict) else 0
                tti = float(page.get("tti", 0)) if isinstance(page, dict) else 0
                
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
                
                # Color mapping with proper contrast
                def get_metric_style(color_name, value):
                    """Get styled metric with proper contrast"""
                    if color_name == "green":
                        return f'<span style="color: #059669; font-weight: 600; background: #d1fae5; padding: 0.2rem 0.4rem; border-radius: 4px; display: inline-block;">{value}</span>'
                    elif color_name == "amber":
                        return f'<span style="color: #d97706; font-weight: 600; background: #fef3c7; padding: 0.2rem 0.4rem; border-radius: 4px; display: inline-block;">{value}</span>'
                    elif color_name == "red":
                        return f'<span style="color: #dc2626; font-weight: 600; background: #fee2e2; padding: 0.2rem 0.4rem; border-radius: 4px; display: inline-block;">{value}</span>'
                    else:
                        return f'<span style="color: #666; font-weight: 500;">{value}</span>'
                
                # Format values correctly
                fcp_display = f"{fcp:.2f}s" if fcp > 0 else "N/A"
                lcp_display = f"{lcp:.2f}s" if lcp > 0 else "N/A"
                si_display = f"{speed_index:.2f}s" if speed_index > 0 else "N/A"
                tbt_display = f"{tbt:.0f}ms" if tbt > 0 else "N/A"
                cls_display = f"{cls:.3f}" if cls >= 0 else "N/A"
                tti_display = f"{tti:.2f}s" if tti > 0 else "N/A"
                
                # Status class
                status_class = "good" if lcp <= 2.5 and tbt <= 200 and cls <= 0.10 else "warning" if lcp <= 4.0 and tbt <= 600 and cls <= 0.25 else "poor"
                
                # Score color
                if avg_score >= 80:
                    score_style = 'color: #059669; font-weight: 700; background: #d1fae5; padding: 0.2rem 0.4rem; border-radius: 4px; display: inline-block;'
                elif avg_score >= 60:
                    score_style = 'color: #d97706; font-weight: 700; background: #fef3c7; padding: 0.2rem 0.4rem; border-radius: 4px; display: inline-block;'
                else:
                    score_style = 'color: #dc2626; font-weight: 700; background: #fee2e2; padding: 0.2rem 0.4rem; border-radius: 4px; display: inline-block;'
                
                rows += f'''
                    <tr>
                        <td><strong style="color: #333;" title="{url}">{page_name_display}</strong><br><small style="color: #666; font-size: 0.75rem;">{display_url}</small></td>
                        <td>{get_metric_style(fcp_color, fcp_display)}</td>
                        <td>{get_metric_style(lcp_color, lcp_display)}</td>
                        <td>{get_metric_style(si_color, si_display)}</td>
                        <td>{get_metric_style(tbt_color, tbt_display)}</td>
                        <td>{get_metric_style(cls_color, cls_display)}</td>
                        <td>{get_metric_style(tti_color, tti_display)}</td>
                        <td><span class="status-{status_class}">{status_text}</span></td>
                        <td><span style="{score_style}">{avg_score:.0f}/100</span></td>
                    </tr>'''
            except Exception as e:
                print(f"  ✗ Error processing page {idx} in detailed metrics table: {e}")
                import traceback
                traceback.print_exc()
                # Add error row
                rows += f'''
                    <tr>
                        <td colspan="9" style="color: var(--danger-color);">Error processing page {idx}: {str(e)}</td>
                    </tr>'''
        
        return f'''<div class="section">
            <h2>Detailed Performance Metrics</h2>
            <table>
                <thead>
                    <tr>
                        <th>Page Name</th>
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
        try:
            # Ensure issues is a list
            if not isinstance(issues, list):
                issues = []
            
            if not issues:
                return '''<div class="section">
                <h2>Issues Identified</h2>
                <p>✅ No critical issues identified. Performance metrics are within acceptable ranges.</p>
            </div>'''
            
            # Ensure page_data is a list
            if not isinstance(page_data, list):
                page_data = []
            
            rows = ""
            for idx, issue in enumerate(issues, 1):
                try:
                    # Use impacted_pages from analyzer if available (already calculated correctly)
                    impacted_pages_list = issue.get("impacted_pages", [])
                    
                    if not isinstance(impacted_pages_list, list):
                        impacted_pages_list = []
                    
                    if not impacted_pages_list:
                        # Fallback: calculate from page data based on issue type
                        issue_name = str(issue.get('issue', '')).lower()
                        for page in page_data:
                            try:
                                page_title = page.get("page_title", "") or page.get("url", "Unknown")
                                if not page_title:
                                    page_title = "Unknown"
                                
                                should_include = False
                                
                                # Check metrics based on issue type
                                if "lcp" in issue_name or "loading" in issue_name or "largest contentful" in issue_name:
                                    lcp_val = float(page.get("lcp", 0) or 0)
                                    if lcp_val > 4.0:
                                        should_include = True
                                elif "tbt" in issue_name or "blocking" in issue_name or "interactivity" in issue_name:
                                    tbt_val = float(page.get("tbt", 0) or 0)
                                    if tbt_val > 600:
                                        should_include = True
                                elif "cls" in issue_name or "layout" in issue_name or "visual" in issue_name:
                                    cls_val = float(page.get("cls", 0) or 0)
                                    if cls_val > 0.25:
                                        should_include = True
                                elif "speed" in issue_name or "speed index" in issue_name:
                                    si_val = float(page.get("speed_index", 0) or 0)
                                    if si_val > 5.8:
                                        should_include = True
                                
                                if should_include and page_title not in impacted_pages_list:
                                    impacted_pages_list.append(str(page_title))
                            except Exception as page_error:
                                print(f"      ⚠️  Error processing page in issue {idx}: {page_error}")
                                continue
                    
                    # Format impacted pages for display
                    if not impacted_pages_list:
                        impacted_pages_str = f"All {len(page_data)} Pages" if page_data else "All Pages"
                    else:
                        unique_pages = list(dict.fromkeys([str(p) for p in impacted_pages_list]))
                        displayed = unique_pages[:3]
                        impacted_pages_str = ", ".join([p[:40] + "..." if len(p) > 40 else p for p in displayed])
                        if len(unique_pages) > 3:
                            impacted_pages_str += f" (+{len(unique_pages) - 3} more)"
                    
                    # Get severity for styling
                    severity = str(issue.get('severity', 'Medium')).lower()
                    severity_class = f"severity-{severity}"
                    
                    # Escape HTML in text fields to prevent issues
                    import html
                    issue_text = html.escape(str(issue.get('issue', 'N/A')))
                    impact_text = html.escape(str(issue.get('impact', 'N/A')))
                    recommendation_text = html.escape(str(issue.get('recommendation', 'N/A')))
                    # Also escape impacted_pages_str
                    impacted_pages_str = html.escape(impacted_pages_str)
                    
                    rows += f'''
                <tr>
                    <td style="color: #333; font-weight: 600;">{issue_text}</td>
                    <td style="color: #666; font-size: 0.875rem;">{impacted_pages_str}</td>
                    <td style="color: #666;">{impact_text}</td>
                    <td style="color: #666;">{recommendation_text}</td>
                    <td><span class="{severity_class}">{severity.title()}</span></td>
                </tr>'''
                except Exception as issue_error:
                    print(f"      ⚠️  Error processing issue {idx}: {issue_error}")
                    import traceback
                    traceback.print_exc()
                    # Add error row instead of failing
                    rows += f'''
                <tr>
                    <td colspan="5" style="color: #dc2626;">Error processing issue: {str(issue_error)}</td>
                </tr>'''
                    continue
            
            return f'''<div class="section">
            <h2>Issues Identified</h2>
            <table>
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Impacted Pages</th>
                        <th>Impact</th>
                        <th>Recommendation</th>
                        <th>Severity</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
            <p style="margin-top: 1rem; font-size: 0.9rem; color: var(--text-secondary);">
                <strong>Total Issues:</strong> {len(issues)}
            </p>
        </div>'''
        except Exception as e:
            print(f"      ✗ Critical error in _generate_issues_table: {e}")
            import traceback
            traceback.print_exc()
            # Return a minimal issues section instead of failing completely
            return f'''<div class="section">
            <h2>Issues Identified</h2>
            <p style="color: #dc2626;">Error generating issues table: {str(e)}</p>
            <p>Please check the backend logs for more details.</p>
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
        if not isinstance(features, list):
            features = []
        models = aiml_results.get("models", {})
        predictions = aiml_results.get("predictions", {})
        comparison = aiml_results.get("comparison", {})
        
        # Default assumptions if not provided - ensure it's always a list
        assumptions_raw = aiml_results.get("assumptions", [
            "Models trained on synthetic data based on Lighthouse thresholds",
            "Predictions are estimates and should be validated with real-world data",
            "Performance may vary based on actual user behavior and network conditions"
        ])
        
        # Convert assumptions to list if it's a string
        if isinstance(assumptions_raw, str):
            # If it's a string, split by newlines or make it a single-item list
            if '\n' in assumptions_raw:
                assumptions = [line.strip() for line in assumptions_raw.split('\n') if line.strip()]
            else:
                assumptions = [assumptions_raw]
        elif isinstance(assumptions_raw, list):
            assumptions = assumptions_raw
        else:
            assumptions = [str(assumptions_raw)]
        
        # Format assumptions as paragraphs instead of bullet points
        assumptions_html = ''.join(f'<p style="margin-bottom: 0.75rem; line-height: 1.6;">{html.escape(str(assumption))}</p>' for assumption in assumptions)
        
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
                        <th>Understanding</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Classification</td>
                        <td>Logistic Regression</td>
                        <td>Accuracy</td>
                        <td>{models.get('classification', {}).get('accuracy', 'N/A') if isinstance(models.get('classification', {}), dict) else 'N/A'}</td>
                        <td>Accuracy measures how often the model correctly predicts performance grades. Higher values (closer to 1.0) indicate better model performance.</td>
                    </tr>
                    <tr>
                        <td>Classification</td>
                        <td>Logistic Regression</td>
                        <td>F1 Score</td>
                        <td>{models.get('classification', {}).get('f1_score', 'N/A') if isinstance(models.get('classification', {}), dict) else 'N/A'}</td>
                        <td>F1 Score balances precision and recall, providing a single metric that considers both false positives and false negatives.</td>
                    </tr>
                    <tr>
                        <td>Regression</td>
                        <td>Ridge</td>
                        <td>RMSE</td>
                        <td>{models.get('regression', {}).get('rmse', 'N/A') if isinstance(models.get('regression', {}), dict) else 'N/A'}</td>
                        <td>RMSE (Root Mean Squared Error) measures prediction error. Lower RMSE values indicate more accurate predictions. Ridge regression prevents overfitting by penalizing large coefficients.</td>
                    </tr>
                    <tr>
                        <td>Neural Network</td>
                        <td>MLP Regressor</td>
                        <td>Architecture</td>
                        <td>{models.get('neural_network', {}).get('architecture', 'N/A') if isinstance(models.get('neural_network', {}), dict) else 'N/A'}</td>
                        <td>Neural Network architecture shows the number of hidden layers and neurons. Lower RMSE indicates the network has learned complex patterns in the data.</td>
                    </tr>
                </tbody>
            </table>
            
            <h3>Predictions</h3>
            <table>
                <thead>
                    <tr>
                        <th>Metric</th>
                        <th>Predicted Value</th>
                        <th>Understanding</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Predicted Grade</td><td>{predictions.get('predicted_grade', 'N/A')}</td><td>The AI model's prediction of the overall performance grade (A-F) based on current metrics. This helps validate the rule-based grading system and provides a data-driven perspective on performance classification.</td></tr>
                    <tr><td>Predicted Score</td><td>{predictions.get('predicted_score', 'N/A')}</td><td>The model's predicted overall performance score (0-100). This represents the model's learned understanding of how metrics combine to create an overall score, potentially capturing non-linear relationships.</td></tr>
                    <tr><td>Predicted Bounce Rate</td><td>{predictions.get('bounce_rate', 'N/A')}%</td><td>Estimated percentage of users who leave the site immediately. Higher bounce rates indicate poor user experience. This prediction helps quantify the business impact of current performance issues.</td></tr>
                    <tr><td>Predicted Conversion Lift</td><td>{predictions.get('conversion_lift', 'N/A')}%</td><td>Expected improvement in conversion rate if performance is optimized. Positive values indicate potential revenue gains. This metric helps prioritize optimization efforts based on expected business impact.</td></tr>
                </tbody>
            </table>
            
            <h3>Comparison: Weighted Formula vs Neural Network</h3>
            <table>
                <thead>
                    <tr>
                        <th>Method</th>
                        <th>Score</th>
                        <th>Understanding</th>
                    </tr>
                </thead>
                <tbody>
                    <tr><td>Weighted Formula</td><td>{comparison.get('weighted_formula', 'N/A')}</td><td>Rule-based calculation using predefined weights (Loading 50%, Interactivity 30%, Visual Stability 20%). This method is transparent, interpretable, and based on industry standards. It provides a consistent, explainable score.</td></tr>
                    <tr><td>Neural Network Prediction</td><td>{comparison.get('neural_network', 'N/A')}</td><td>AI model's learned prediction based on patterns in training data. The neural network can capture complex, non-linear relationships between metrics that the formula might miss. This provides a data-driven alternative perspective.</td></tr>
                    <tr><td>Difference</td><td>{comparison.get('difference', 'N/A')}</td><td>The difference between the two methods. Small differences (&lt;5 points) indicate agreement. Larger differences suggest the neural network has identified patterns not captured by the weighted formula, which may warrant further investigation.</td></tr>
                </tbody>
            </table>
            
            <h3>Assumptions and Limitations</h3>
            <div style="margin-top: 1rem;">
                {assumptions_html}
            </div>
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

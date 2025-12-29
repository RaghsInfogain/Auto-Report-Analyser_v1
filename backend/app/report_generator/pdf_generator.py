"""Enhanced PDF report generator matching HTML report structure"""
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from typing import Dict, Any, List
from datetime import datetime
import io

class PDFReportGenerator:
    """Generate comprehensive PDF reports matching HTML report structure"""
    
    @staticmethod
    def get_grade_color(grade: str) -> colors.Color:
        """Get color for grade"""
        grade = grade.upper().replace('+', 'PLUS')
        if grade in ['A+', 'APLUS', 'A']:
            return colors.HexColor('#059669')
        elif grade in ['B+', 'BPLUS', 'B']:
            return colors.HexColor('#d97706')
        else:
            return colors.HexColor('#dc2626')
    
    @staticmethod
    def generate_jmeter_pdf_report(metrics: Dict[str, Any]) -> bytes:
        """Generate a comprehensive PDF report matching HTML structure"""
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=30,
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        heading1_style = ParagraphStyle(
            'CustomHeading1',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold'
        )
        
        heading2_style = ParagraphStyle(
            'CustomHeading2',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1e293b'),
            spaceAfter=10,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        )
        
        body_style = ParagraphStyle(
            'CustomBody',
            parent=styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            alignment=TA_JUSTIFY
        )
        
        # Extract all metrics
        summary = metrics.get("summary", {})
        overall_grade = summary.get("overall_grade", "N/A")
        overall_score = summary.get("overall_score", 0)
        success_rate = summary.get("success_rate", 0)
        
        sample_time = metrics.get("sample_time", {})
        avg_response = sample_time.get("mean", 0) / 1000
        p70 = sample_time.get("p70", 0) / 1000
        p80 = sample_time.get("p80", 0) / 1000
        p90 = sample_time.get("p90", 0) / 1000
        p95 = sample_time.get("p95", 0) / 1000
        p99 = sample_time.get("p99", 0) / 1000
        median = sample_time.get("median", 0) / 1000
        max_time = sample_time.get("max", 0) / 1000
        
        error_rate = metrics.get("error_rate", 0) * 100
        throughput = metrics.get("throughput", 0)
        total_samples = metrics.get("total_samples", 0)
        test_duration = summary.get("test_duration_hours", 0)
        
        sla_2s = summary.get("sla_compliance_2s", 0)
        sla_3s = summary.get("sla_compliance_3s", 0)
        sla_5s = summary.get("sla_compliance_5s", 0)
        
        grade_reasons = summary.get("grade_reasons", {})
        overall_grade_description = summary.get("overall_grade_description", {})
        critical_issues = summary.get("critical_issues", [])
        recommendations = summary.get("recommendations", [])
        improvement_roadmap = summary.get("improvement_roadmap", [])
        transaction_stats = summary.get("transaction_stats", {})
        request_stats = summary.get("request_stats", {})
        
        scores = summary.get("scores", {})
        targets = summary.get("targets", {})
        
        current_date = datetime.now().strftime("%B %d, %Y")
        
        # ==================== HEADER ====================
        elements.append(Paragraph("Performance Assessment Report", title_style))
        elements.append(Paragraph(f"Load Testing Results & Executive Analysis | {current_date}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # ==================== EXECUTIVE SUMMARY ====================
        elements.append(Paragraph("📊 Executive Summary", heading1_style))
        
        status_text = "CAUTIONARY APPROVAL" if overall_grade in ['C+', 'C', 'D'] else "CONDITIONAL APPROVAL" if overall_grade in ['B+', 'B'] else "APPROVED"
        elements.append(Paragraph(f"<b>Status: {status_text}</b>", body_style))
        
        summary_data = [
            ["Metric", "Value"],
            ["Success Rate", f"{success_rate:.1f}%"],
            ["Avg Response Time", f"{avg_response:.2f}s"],
            ["Error Rate", f"{error_rate:.2f}%"],
            ["Throughput", f"{throughput:.1f} req/s"],
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # ==================== PERFORMANCE SCORECARD ====================
        elements.append(PageBreak())
        elements.append(Paragraph("🎯 Performance Scorecard & Grading Analysis", heading1_style))
        
        grade_color = PDFReportGenerator.get_grade_color(overall_grade)
        grade_title = overall_grade_description.get("title", "Performance Assessment")
        grade_range = overall_grade_description.get("score_range", "")
        
        elements.append(Paragraph(
            f"<para align='center' backColor='#fef3c7' borderColor='{grade_color}' borderWidth='3' borderPadding='10'>"
            f"<b><font size='24' color='{grade_color}'>OVERALL GRADE: {overall_grade}</font></b><br/>"
            f"<font size='12'><b>{grade_title}</b></font><br/>"
            f"<font size='10'>Score: {overall_score:.0f}/100 | Range: {grade_range}</font></para>",
            styles['Normal']
        ))
        elements.append(Spacer(1, 0.15*inch))
        
        # Helper for grade one-liners
        def get_grade_one_liner(cat_grade):
            one_liners = {
                "A+": "Exceptional", "A": "Excellent", "B+": "Good", "B": "Above Avg",
                "C+": "Average", "C": "Below Avg", "D": "Poor", "F": "Failing"
            }
            return one_liners.get(cat_grade, "N/A")
        
        # Grade breakdown with one-liners
        elements.append(Paragraph("Grade Breakdown by Category", heading2_style))
        grade_data = [
            ["Category", "Grade", "Status", "Score", "Metrics"],
        ]
        
        for cat_key, cat_name in [("performance", "Performance"), ("reliability", "Reliability"), 
                                   ("user_experience", "User Experience"), ("scalability", "Scalability")]:
            gr = grade_reasons.get(cat_key, {})
            icon = gr.get("icon", "")
            weight = gr.get("weight", "")
            cat_grade = gr.get("grade", "N/A")
            grade_data.append([
                f"{icon} {cat_name} ({weight})",
                cat_grade,
                get_grade_one_liner(cat_grade),
                f"{gr.get('score', 0):.0f}",
                gr.get("reason", "N/A")
            ])
        
        grade_table = Table(grade_data, colWidths=[1.8*inch, 0.5*inch, 0.8*inch, 0.5*inch, 2.3*inch])
        grade_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (3, -1), 'CENTER'),
            ('ALIGN', (4, 0), (4, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(grade_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Detailed metrics table
        elements.append(Paragraph("📋 Detailed Performance Metrics", heading2_style))
        
        def get_status(value, target, lower_is_better=True):
            if lower_is_better:
                if value <= target:
                    return "✓ PASS"
                elif value <= target * 1.5:
                    return "⚠ MARGINAL"
                else:
                    return "✗ FAIL"
            else:
                if value >= target:
                    return "✓ PASS"
                elif value >= target * 0.8:
                    return "⚠ ACCEPTABLE"
                else:
                    return "✗ FAIL"
        
        metrics_data = [
            ["Metric", "Result", "Target", "Status", "Score"],
            ["Availability", f"{success_rate:.1f}%", f"{targets.get('availability', 99)}%", 
             get_status(success_rate, 99, False), f"{scores.get('availability', 0):.0f}/100"],
            ["Avg Response", f"{avg_response:.2f}s", "<2s", 
             get_status(avg_response, 2), f"{scores.get('response_time', 0):.0f}/100"],
            ["Error Rate", f"{error_rate:.2f}%", "<1%", 
             get_status(error_rate, 1), f"{scores.get('error_rate', 0):.0f}/100"],
            ["Throughput", f"{throughput:.1f}/s", "100/s", 
             get_status(throughput, 100, False), f"{scores.get('throughput', 0):.0f}/100"],
            ["95th Percentile", f"{p95:.2f}s", "<3s", 
             get_status(p95, 3), f"{scores.get('p95_percentile', 0):.0f}/100"],
            ["SLA Compliance", f"{sla_2s:.1f}%", ">95%", 
             get_status(sla_2s, 95, False), f"{scores.get('sla_compliance', 0):.0f}/100"],
        ]
        
        metrics_table = Table(metrics_data, colWidths=[1.3*inch, 1.2*inch, 1*inch, 1.2*inch, 1*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # Performance Grading Scale
        elements.append(Paragraph("📏 Performance Grading Scale & Methodology", heading2_style))
        grading_text = """
        <b>A+ (90-100):</b> Exceptional - Industry leading performance<br/>
        <b>A (80-89):</b> Excellent - Exceeds industry standards<br/>
        <b>B+ (75-79):</b> Good - Meets industry standards<br/>
        <b>B (70-74):</b> Acceptable - Minor improvements needed<br/>
        <b>C+ (65-69):</b> Marginal - Significant issues present<br/>
        <b>D (50-59):</b> Critical - Immediate action required<br/>
        <br/>
        <b>Weighted Scoring:</b> Performance (30%), Reliability (25%), User Experience (25%), Scalability (20%)
        """
        elements.append(Paragraph(grading_text, body_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # ==================== TEST OVERVIEW ====================
        elements.append(PageBreak())
        elements.append(Paragraph("📊 Test Overview", heading1_style))
        
        test_data = [
            ["Metric", "Value"],
            ["Total Requests", f"{total_samples:,}"],
            ["Test Duration", f"{test_duration:.2f} hours"],
            ["Average Throughput", f"{throughput:.1f} req/s"],
            ["Success Rate", f"{success_rate:.2f}%"],
            ["Median Response", f"{median:.2f}s"],
            ["90th Percentile", f"{p90:.2f}s"],
            ["95th Percentile", f"{p95:.2f}s"],
            ["99th Percentile", f"{p99:.2f}s"],
            ["Max Response", f"{max_time:.2f}s"],
        ]
        
        test_table = Table(test_data, colWidths=[2.5*inch, 2.5*inch])
        test_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(test_table)
        elements.append(Spacer(1, 0.2*inch))
        
        # ==================== PERFORMANCE SUMMARY TABLES ====================
        elements.append(PageBreak())
        elements.append(Paragraph("📊 Performance Summary", heading1_style))
        
        def create_performance_table(stats_dict: dict, title: str) -> List:
            """Create a performance table from stats"""
            table_elements = []
            table_elements.append(Paragraph(title, heading2_style))
            
            if not stats_dict:
                table_elements.append(Paragraph("No data available", body_style))
                return table_elements
            
            # Sort by avg response time
            sorted_stats = sorted(stats_dict.items(), key=lambda x: x[1].get('avg_response', 0) or 0, reverse=True)[:10]
            
            perf_data = [
                ["Endpoint", "Avg", "70%", "80%", "90%", "95%", "Error%", "Calls"]
            ]
            
            for label, data in sorted_stats:
                avg = data.get('avg_response', 0)
                perf_data.append([
                    label[:30] + '...' if len(label) > 30 else label,
                    f"{avg/1000:.2f}s" if avg else "N/A",
                    f"{data.get('p70', 0)/1000:.2f}s",
                    f"{data.get('p80', 0)/1000:.2f}s",
                    f"{data.get('p90', 0)/1000:.2f}s",
                    f"{data.get('p95', 0)/1000:.2f}s",
                    f"{data.get('error_rate', 0):.2f}%",
                    f"{data.get('count', 0):,}"
                ])
            
            perf_table = Table(perf_data, colWidths=[2*inch, 0.6*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.5*inch, 0.6*inch, 0.6*inch])
            perf_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 7),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ]))
            table_elements.append(perf_table)
            return table_elements
        
        # Add transaction table
        for elem in create_performance_table(transaction_stats, "📋 Transaction Performance (Top 10 Slowest)"):
            elements.append(elem)
        elements.append(Spacer(1, 0.15*inch))
        
        # Add request table
        for elem in create_performance_table(request_stats, "🔗 API Request Performance (Top 10 Slowest)"):
            elements.append(elem)
        elements.append(Spacer(1, 0.2*inch))
        
        # ==================== CRITICAL ISSUES ====================
        if critical_issues:
            elements.append(PageBreak())
            elements.append(Paragraph("🔴 Critical Issues", heading1_style))
            elements.append(Paragraph(
                f"<b>IMMEDIATE ACTION REQUIRED:</b> {len(critical_issues)} critical issue(s) identified.",
                body_style
            ))
            elements.append(Spacer(1, 0.1*inch))
            
            for i, issue in enumerate(critical_issues[:5], 1):
                issue_text = f"""
                <b>Issue #{i}: {issue.get('title', 'Unknown')}</b><br/>
                <b>Impact:</b> {issue.get('impact', 'N/A')}<br/>
                <b>Affected:</b> {issue.get('affected', 'N/A')}<br/>
                <b>Priority:</b> {issue.get('priority', 'N/A')} | <b>Timeline:</b> {issue.get('timeline', 'N/A')}
                """
                elements.append(Paragraph(issue_text, body_style))
                elements.append(Spacer(1, 0.1*inch))
        
        # ==================== BUSINESS IMPACT ====================
        elements.append(PageBreak())
        elements.append(Paragraph("💰 Business Impact Assessment", heading1_style))
        
        impact_data = [
            ["Aspect", "Assessment"],
            ["Investment Required", "Significant (6 months)"],
            ["Timeline to A+", "6 Months"],
            ["Expected ROI", "High (First year)"],
            ["Payback Period", "2-4 Months"],
        ]
        
        impact_table = Table(impact_data, colWidths=[2.5*inch, 3*inch])
        impact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(impact_table)
        elements.append(Spacer(1, 0.2*inch))
        
        elements.append(Paragraph("<b>Cost of Inaction:</b>", body_style))
        cost_text = f"""
        • Error Rate ({error_rate:.2f}%): {'Major' if error_rate > 5 else 'Moderate'} revenue loss from failed operations<br/>
        • Poor Performance ({avg_response:.1f}s avg): {'Significant' if avg_response > 5 else 'Moderate'} productivity loss<br/>
        • Support Overhead: {'Increased' if error_rate > 3 else 'Moderate'} operational costs<br/>
        • User Abandonment Risk: {'High' if avg_response > 5 else 'Medium'} opportunity cost
        """
        elements.append(Paragraph(cost_text, body_style))
        elements.append(Spacer(1, 0.1*inch))
        
        # ==================== RECOMMENDED ACTION PLAN ====================
        elements.append(PageBreak())
        elements.append(Paragraph("🚀 Recommended Action Plan", heading1_style))
        
        if improvement_roadmap:
            for phase in improvement_roadmap:
                phase_title = phase.get('phase', 'Phase')
                timeline = phase.get('timeline', 'TBD')
                target = phase.get('target_grade', 'N/A')
                
                elements.append(Paragraph(f"<b>{phase_title}</b> ({timeline}) → Target: {target}", heading2_style))
                
                improvements = phase.get('improvements', [])
                for imp in improvements[:4]:
                    elements.append(Paragraph(f"• {imp}", body_style))
                
                elements.append(Paragraph(f"<i>Expected Impact: {phase.get('expected_impact', 'N/A')}</i>", body_style))
                elements.append(Spacer(1, 0.1*inch))
        
        # ==================== SUCCESS METRICS ====================
        elements.append(PageBreak())
        elements.append(Paragraph("🎯 Success Metrics & Targets", heading1_style))
        
        target_3m_avg = max(2.0, avg_response * 0.6)
        target_6m_avg = max(0.8, avg_response * 0.3)
        
        success_data = [
            ["Metric", "Current", "3-Month Target", "6-Month Target", "Industry Std"],
            ["Avg Response", f"{avg_response:.1f}s", f"{target_3m_avg:.1f}s", f"{target_6m_avg:.1f}s", "<2s"],
            ["95th Percentile", f"{p95:.1f}s", f"{max(5.0, p95*0.4):.1f}s", f"{max(2.5, p95*0.2):.1f}s", "<3s"],
            ["Error Rate", f"{error_rate:.2f}%", f"{max(0.8, error_rate*0.4):.1f}%", "0.3%", "<0.5%"],
            ["Success Rate", f"{success_rate:.1f}%", "99%", "99.5%", ">99%"],
            ["SLA Compliance", f"{sla_2s:.1f}%", f"{min(95, sla_2s+20):.0f}%", "95%", ">95%"],
            ["Throughput", f"{throughput:.0f}/s", f"{throughput*1.5:.0f}/s", f"{max(180, throughput*2.5):.0f}/s", "150/s"],
        ]
        
        success_table = Table(success_data, colWidths=[1.2*inch, 0.9*inch, 1*inch, 1*inch, 0.9*inch])
        success_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2563eb')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(success_table)
        
        # ==================== FOOTER ====================
        elements.append(Spacer(1, 0.3*inch))
        footer_text = f"""
        <para align='center'>
        <b>Report Generated:</b> {current_date}<br/>
        <b>Generated By:</b> Raghvendra Kumar<br/>
        <b>Classification:</b> Internal
        </para>
        """
        elements.append(Paragraph(footer_text, body_style))
        
        # Build PDF
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    @staticmethod
    def generate_web_vitals_pdf_report(metrics: Dict[str, Any], filename: str = "web_vitals_report") -> bytes:
        """Generate PDF report for Web Vitals metrics"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=30)
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24, 
                                     textColor=colors.HexColor('#3498db'), spaceAfter=20, alignment=TA_CENTER)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14,
                                       textColor=colors.HexColor('#3498db'), spaceAfter=10, spaceBefore=15)
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=10, spaceAfter=8)
        
        current_date = datetime.now().strftime("%B %d, %Y")
        total_samples = metrics.get("total_samples", 0)
        
        lcp = metrics.get("lcp", {})
        fid = metrics.get("fid", {})
        cls_data = metrics.get("cls", {})
        fcp = metrics.get("fcp", {})
        ttfb = metrics.get("ttfb", {})
        summary = metrics.get("summary", {})
        
        # Title
        elements.append(Paragraph("⚡ Web Vitals Performance Report", title_style))
        elements.append(Paragraph(f"Core Web Vitals Analysis | {current_date} | Samples: {total_samples:,}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary metrics
        elements.append(Paragraph("📊 Core Web Vitals Summary", heading_style))
        summary_data = [
            ["Metric", "Value", "Target", "Status"],
            ["LCP (Largest Contentful Paint)", f"{lcp.get('mean', 0) or 0:.0f}ms", "≤ 2500ms", 
             "✓ Good" if (lcp.get('mean', 0) or 0) <= 2500 else "⚠ Needs Work" if (lcp.get('mean', 0) or 0) <= 4000 else "✗ Poor"],
            ["FID (First Input Delay)", f"{fid.get('mean', 0) or 0:.0f}ms", "≤ 100ms",
             "✓ Good" if (fid.get('mean', 0) or 0) <= 100 else "⚠ Needs Work" if (fid.get('mean', 0) or 0) <= 300 else "✗ Poor"],
            ["CLS (Cumulative Layout Shift)", f"{cls_data.get('mean', 0) or 0:.3f}", "≤ 0.1",
             "✓ Good" if (cls_data.get('mean', 0) or 0) <= 0.1 else "⚠ Needs Work" if (cls_data.get('mean', 0) or 0) <= 0.25 else "✗ Poor"],
            ["FCP (First Contentful Paint)", f"{fcp.get('mean', 0) or 0:.0f}ms", "≤ 1800ms",
             "✓ Good" if (fcp.get('mean', 0) or 0) <= 1800 else "⚠ Needs Work" if (fcp.get('mean', 0) or 0) <= 3000 else "✗ Poor"],
            ["TTFB (Time to First Byte)", f"{ttfb.get('mean', 0) or 0:.0f}ms", "≤ 800ms",
             "✓ Good" if (ttfb.get('mean', 0) or 0) <= 800 else "⚠ Needs Work" if (ttfb.get('mean', 0) or 0) <= 1800 else "✗ Poor"],
        ]
        
        table = Table(summary_data, colWidths=[2.5*inch, 1.2*inch, 1.2*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3498db')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Performance distribution
        elements.append(Paragraph("📈 Performance Distribution", heading_style))
        dist_data = [
            ["Metric", "Good ✓", "Needs Improvement ⚠", "Poor ✗"],
            ["LCP", str(summary.get('lcp_good', 0)), str(summary.get('lcp_needs_improvement', 0)), str(summary.get('lcp_poor', 0))],
            ["FID", str(summary.get('fid_good', 0)), str(summary.get('fid_needs_improvement', 0)), str(summary.get('fid_poor', 0))],
            ["CLS", str(summary.get('cls_good', 0)), str(summary.get('cls_needs_improvement', 0)), str(summary.get('cls_poor', 0))],
        ]
        
        dist_table = Table(dist_data, colWidths=[1.5*inch, 1.5*inch, 1.8*inch, 1.2*inch])
        dist_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#27ae60')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(dist_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        elements.append(Paragraph(f"<para align='center'><b>Report Generated:</b> {current_date} | <b>Generated By:</b> Raghvendra Kumar | <b>Classification:</b> Internal</para>", body_style))
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    
    @staticmethod
    def generate_ui_performance_pdf_report(metrics: Dict[str, Any], filename: str = "ui_performance_report") -> bytes:
        """Generate PDF report for UI Performance metrics"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=30)
        
        elements = []
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24,
                                     textColor=colors.HexColor('#9b59b6'), spaceAfter=20, alignment=TA_CENTER)
        heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=14,
                                       textColor=colors.HexColor('#9b59b6'), spaceAfter=10, spaceBefore=15)
        body_style = ParagraphStyle('CustomBody', parent=styles['Normal'], fontSize=10, spaceAfter=8)
        
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
        
        # Title
        elements.append(Paragraph("🎯 UI Performance Report", title_style))
        elements.append(Paragraph(f"Page Load Timing Analysis | {current_date} | Samples: {total_samples:,}", styles['Normal']))
        elements.append(Spacer(1, 0.3*inch))
        
        # Summary metrics
        elements.append(Paragraph("📊 Performance Metrics Summary", heading_style))
        summary_data = [
            ["Metric", "Mean", "Median", "P95", "P99"],
            ["DNS Lookup", f"{dns.get('mean', 0) or 0:.0f}ms", f"{dns.get('median', 0) or 0:.0f}ms", f"{dns.get('p95', 0) or 0:.0f}ms", f"{dns.get('p99', 0) or 0:.0f}ms"],
            ["Connection Time", f"{conn.get('mean', 0) or 0:.0f}ms", f"{conn.get('median', 0) or 0:.0f}ms", f"{conn.get('p95', 0) or 0:.0f}ms", f"{conn.get('p99', 0) or 0:.0f}ms"],
            ["SSL/TLS Time", f"{ssl.get('mean', 0) or 0:.0f}ms", f"{ssl.get('median', 0) or 0:.0f}ms", f"{ssl.get('p95', 0) or 0:.0f}ms", f"{ssl.get('p99', 0) or 0:.0f}ms"],
            ["Time to First Byte", f"{ttfb.get('mean', 0) or 0:.0f}ms", f"{ttfb.get('median', 0) or 0:.0f}ms", f"{ttfb.get('p95', 0) or 0:.0f}ms", f"{ttfb.get('p99', 0) or 0:.0f}ms"],
            ["Content Download", f"{download.get('mean', 0) or 0:.0f}ms", f"{download.get('median', 0) or 0:.0f}ms", f"{download.get('p95', 0) or 0:.0f}ms", f"{download.get('p99', 0) or 0:.0f}ms"],
            ["DOM Processing", f"{dom.get('mean', 0) or 0:.0f}ms", f"{dom.get('median', 0) or 0:.0f}ms", f"{dom.get('p95', 0) or 0:.0f}ms", f"{dom.get('p99', 0) or 0:.0f}ms"],
            ["Page Load Time", f"{page_load.get('mean', 0) or 0:.0f}ms", f"{page_load.get('median', 0) or 0:.0f}ms", f"{page_load.get('p95', 0) or 0:.0f}ms", f"{page_load.get('p99', 0) or 0:.0f}ms"],
            ["Full Page Load", f"{full_load.get('mean', 0) or 0:.0f}ms", f"{full_load.get('median', 0) or 0:.0f}ms", f"{full_load.get('p95', 0) or 0:.0f}ms", f"{full_load.get('p99', 0) or 0:.0f}ms"],
        ]
        
        table = Table(summary_data, colWidths=[1.5*inch, 1*inch, 1*inch, 1*inch, 1*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#9b59b6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Footer
        elements.append(Paragraph(f"<para align='center'><b>Report Generated:</b> {current_date} | <b>Generated By:</b> Raghvendra Kumar | <b>Classification:</b> Internal</para>", body_style))
        
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

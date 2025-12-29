from typing import Dict, List, Any
from datetime import datetime
import json

class ReportBuilder:
    """Builder for comprehensive performance reports"""
    
    @staticmethod
    def generate_comprehensive_report(
        web_vitals_results: Dict[str, Any] = None,
        jmeter_results: Dict[str, Any] = None,
        ui_performance_results: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Generate a comprehensive report combining all analyses"""
        
        report = {
            "report_id": f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "generated_at": datetime.now().isoformat(),
            "sections": []
        }
        
        # Executive Summary
        executive_summary = ReportBuilder._create_executive_summary(
            web_vitals_results, jmeter_results, ui_performance_results
        )
        report["sections"].append({
            "title": "Executive Summary",
            "type": "summary",
            "content": executive_summary
        })
        
        # Web Vitals Section
        if web_vitals_results:
            report["sections"].append({
                "title": "Web Vitals Analysis",
                "type": "web_vitals",
                "content": web_vitals_results
            })
        
        # JMeter Section
        if jmeter_results:
            report["sections"].append({
                "title": "JMeter Test Results",
                "type": "jmeter",
                "content": jmeter_results
            })
        
        # UI Performance Section
        if ui_performance_results:
            report["sections"].append({
                "title": "UI Performance Analysis",
                "type": "ui_performance",
                "content": ui_performance_results
            })
        
        # Recommendations
        recommendations = ReportBuilder._generate_recommendations(
            web_vitals_results, jmeter_results, ui_performance_results
        )
        report["sections"].append({
            "title": "Recommendations",
            "type": "recommendations",
            "content": recommendations
        })
        
        return report
    
    @staticmethod
    def _create_executive_summary(
        web_vitals: Dict = None,
        jmeter: Dict = None,
        ui_performance: Dict = None
    ) -> Dict:
        """Create executive summary"""
        summary = {
            "overview": "Performance analysis report covering Web Vitals, Load Testing, and UI Performance metrics.",
            "categories_analyzed": [],
            "key_metrics": {}
        }
        
        if web_vitals:
            summary["categories_analyzed"].append("Web Vitals")
            if "lcp" in web_vitals and web_vitals["lcp"].get("mean"):
                summary["key_metrics"]["LCP"] = f"{web_vitals['lcp']['mean']:.2f}ms"
            if "fid" in web_vitals and web_vitals["fid"].get("mean"):
                summary["key_metrics"]["FID"] = f"{web_vitals['fid']['mean']:.2f}ms"
        
        if jmeter:
            summary["categories_analyzed"].append("JMeter Load Tests")
            if "throughput" in jmeter:
                summary["key_metrics"]["Throughput"] = f"{jmeter['throughput']:.2f} req/s"
            if "error_rate" in jmeter:
                summary["key_metrics"]["Error Rate"] = f"{jmeter['error_rate']*100:.2f}%"
        
        if ui_performance:
            summary["categories_analyzed"].append("UI Performance")
            if "full_page_load_time" in ui_performance and ui_performance["full_page_load_time"].get("mean"):
                summary["key_metrics"]["Avg Page Load"] = f"{ui_performance['full_page_load_time']['mean']:.2f}ms"
        
        return summary
    
    @staticmethod
    def _generate_recommendations(
        web_vitals: Dict = None,
        jmeter: Dict = None,
        ui_performance: Dict = None
    ) -> List[str]:
        """Generate recommendations based on analysis"""
        recommendations = []
        
        if web_vitals:
            if web_vitals.get("lcp", {}).get("mean", 0) > 4000:
                recommendations.append("LCP is poor (>4000ms). Consider optimizing images, reducing server response time, and eliminating render-blocking resources.")
            if web_vitals.get("fid", {}).get("mean", 0) > 300:
                recommendations.append("FID is poor (>300ms). Consider reducing JavaScript execution time and breaking up long tasks.")
            if web_vitals.get("cls", {}).get("mean", 0) > 0.25:
                recommendations.append("CLS is poor (>0.25). Ensure size attributes on images and videos, and avoid inserting content above existing content.")
        
        if jmeter:
            if jmeter.get("error_rate", 0) > 0.05:
                recommendations.append(f"High error rate ({jmeter['error_rate']*100:.2f}%). Investigate server stability and resource constraints.")
            if jmeter.get("latency", {}).get("p95", 0) > 2000:
                recommendations.append("95th percentile latency is high. Consider optimizing database queries and reducing server processing time.")
        
        if ui_performance:
            if ui_performance.get("dns_lookup_time", {}).get("mean", 0) > 100:
                recommendations.append("DNS lookup time is high. Consider using DNS prefetching or CDN.")
            if ui_performance.get("connection_time", {}).get("mean", 0) > 500:
                recommendations.append("Connection time is high. Consider using HTTP/2 and connection pooling.")
        
        if not recommendations:
            recommendations.append("Overall performance metrics are within acceptable ranges. Continue monitoring.")
        
        return recommendations













"""
Simplified and efficient JMeter analyzer
Fast, reliable, and produces comprehensive metrics
"""
import numpy as np
from typing import List, Dict, Any
from collections import Counter, defaultdict
from app.models.jmeter import JMeterMetrics


class JMeterAnalyzerV2:
    """Simplified JMeter analyzer with efficient calculations"""
    
    @staticmethod
    def analyze(data: List[Dict[str, Any]]) -> JMeterMetrics:
        """
        Analyze JMeter data and return comprehensive metrics
        Simplified, fast, and reliable
        """
        if not data:
            raise ValueError("No data provided for analysis")
        
        print(f"  Analyzing {len(data):,} records...")
        
        # Extract arrays for efficient numpy operations
        sample_times = np.array([d.get("sample_time", 0) for d in data if d.get("sample_time") is not None], dtype=float)
        latencies = np.array([d.get("latency", 0) for d in data if d.get("latency") is not None], dtype=float)
        connect_times = np.array([d.get("connect_time", 0) for d in data if d.get("connect_time") is not None], dtype=float)
        
        # Calculate basic metrics
        total_samples = len(data)
        errors = sum(1 for d in data if not d.get("success", True) or 
                    (d.get("response_code") and str(d.get("response_code", "")).startswith(("4", "5"))))
        error_rate = (errors / total_samples) if total_samples > 0 else 0.0
        
        # Calculate duration and throughput
        timestamps = [d.get("timestamp", 0) for d in data if d.get("timestamp")]
        if timestamps:
            duration_seconds = (max(timestamps) - min(timestamps)) / 1000.0
            duration_hours = duration_seconds / 3600.0
            throughput = total_samples / duration_seconds if duration_seconds > 0 else 0.0
        else:
            duration_seconds = 0.0
            duration_hours = 0.0
            throughput = 0.0
        
        # Response codes
        response_codes = Counter([str(d.get("response_code", "")) for d in data if d.get("response_code")])
        
        # Calculate percentiles efficiently
        sample_time_stats = JMeterAnalyzerV2._calculate_stats(sample_times)
        latency_stats = JMeterAnalyzerV2._calculate_stats(latencies)
        connect_time_stats = JMeterAnalyzerV2._calculate_stats(connect_times)
        
        # Analyze by label (transactions/requests)
        transaction_stats, request_stats = JMeterAnalyzerV2._analyze_by_label(data)
        
        # Calculate scores and grades
        avg_response_sec = sample_time_stats.get("mean", 0) / 1000.0
        p95_response = sample_time_stats.get("p95", 0)
        success_rate = ((total_samples - errors) / total_samples * 100) if total_samples > 0 else 0.0
        
        # SLA compliance
        sla_2s = sum(1 for d in data if d.get("sample_time", 0) < 2000)
        sla_3s = sum(1 for d in data if d.get("sample_time", 0) < 3000)
        sla_5s = sum(1 for d in data if d.get("sample_time", 0) < 5000)
        sla_compliance_2s_pct = (sla_2s / total_samples * 100) if total_samples > 0 else 0.0
        sla_compliance_3s_pct = (sla_3s / total_samples * 100) if total_samples > 0 else 0.0
        sla_compliance_5s_pct = (sla_5s / total_samples * 100) if total_samples > 0 else 0.0
        
        # Calculate scores (0-100)
        scores = JMeterAnalyzerV2._calculate_scores(
            success_rate, error_rate, avg_response_sec, p95_response / 1000.0,
            throughput, sla_compliance_2s_pct
        )
        
        # Calculate grades
        overall_score = scores["overall"]
        grade, grade_class = JMeterAnalyzerV2._calculate_grade(overall_score)
        
        # Generate time series (simplified - sample if too large)
        time_series_data = JMeterAnalyzerV2._calculate_time_series(data, duration_seconds)
        
        # Response time distribution
        rt_distribution = JMeterAnalyzerV2._calculate_response_time_distribution(data)
        
        # Critical issues and recommendations
        critical_issues = JMeterAnalyzerV2._identify_issues(
            error_rate * 100, avg_response_sec, sla_compliance_2s_pct, transaction_stats, request_stats
        )
        recommendations = JMeterAnalyzerV2._generate_recommendations(error_rate * 100, avg_response_sec, throughput)
        improvement_roadmap = JMeterAnalyzerV2._generate_roadmap(overall_score)
        
        # Grade descriptions
        grade_reasons = JMeterAnalyzerV2._build_grade_reasons(scores, avg_response_sec, success_rate, 
                                                               error_rate * 100, throughput, p95_response / 1000.0,
                                                               sla_compliance_2s_pct, grade, grade_class)
        
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
            "grade_reasons": grade_reasons,
            "response_time_distribution": rt_distribution,
            "time_series_data": time_series_data,
            "transaction_stats": transaction_stats,
            "request_stats": request_stats,
            "critical_issues": critical_issues,
            "recommendations": recommendations,
            "improvement_roadmap": improvement_roadmap,
            "scores": scores,
            "targets": {
                "availability": 99,
                "response_time": 2000,
                "error_rate": 1,
                "throughput": 100,
                "p95_percentile": 3000,
                "sla_compliance": 95
            }
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
        """Calculate percentile statistics efficiently"""
        if len(values) == 0:
            return {
                "mean": 0.0, "median": 0.0, "p70": 0.0, "p75": 0.0, "p80": 0.0,
                "p90": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0
            }
        
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
            "max": float(np.max(values))
        }
    
    @staticmethod
    def _analyze_by_label(data: List[Dict]) -> tuple:
        """Analyze data grouped by label (transactions vs requests)"""
        transactions = defaultdict(list)
        requests = defaultdict(list)
        
        for d in data:
            label = d.get("label", "Unknown")
            # Simple heuristic: transactions start with "T" or don't start with "api"
            if label.startswith("T") or not label.startswith("api"):
                transactions[label].append(d)
            else:
                requests[label].append(d)
        
        def analyze_group(group_data: Dict[str, List]) -> Dict:
            stats = {}
            for label, items in group_data.items():
                response_times = [d.get("sample_time", 0) for d in items if d.get("sample_time") is not None]
                errors = sum(1 for d in items if not d.get("success", True))
                
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
                    stats[label] = {
                        "count": len(items),
                        "errors": errors,
                        "error_rate": (errors / len(items) * 100) if items else 0.0,
                        "avg_response": 0.0, "median": 0.0, "p70": 0.0, "p75": 0.0, "p80": 0.0,
                        "p90": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0
                    }
            return stats
        
        return analyze_group(transactions), analyze_group(requests)
    
    @staticmethod
    def _calculate_scores(success_rate: float, error_rate: float, avg_response: float,
                          p95_response: float, throughput: float, sla_compliance: float) -> Dict[str, float]:
        """Calculate category scores (0-100)"""
        def score_metric(value: float, target: float, higher_better: bool) -> float:
            if higher_better:
                return min(100, max(0, (value / target) * 100)) if target > 0 else 0
            else:
                return min(100, max(0, (target / value) * 100)) if value > 0 else 0
        
        availability_score = score_metric(success_rate, 99, True)
        response_time_score = score_metric(avg_response, 2, False)
        error_rate_score = score_metric(error_rate, 1, False)
        throughput_score = score_metric(throughput, 100, True)
        p95_score = score_metric(p95_response, 3, False)
        sla_score = score_metric(sla_compliance, 95, True)
        
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
    def _calculate_time_series(data: List[Dict], duration: float, max_points: int = 500) -> List[Dict]:
        """Calculate time series data - sample if too large, including per-transaction/request data"""
        if not data or duration <= 0:
            return []
        
        # Sample data if too large
        if len(data) > max_points * 2:
            step = len(data) // max_points
            sampled_data = data[::step]
        else:
            sampled_data = data
        
        interval_size = max(1.0, duration / max_points)
        intervals = defaultdict(lambda: {
            "response_times": [], 
            "vusers": [], 
            "pass_count": 0, 
            "fail_count": 0,
            "by_label": defaultdict(lambda: {"response_times": [], "pass_count": 0, "fail_count": 0})
        })
        
        timestamps = [d.get("timestamp", 0) for d in sampled_data if d.get("timestamp")]
        if not timestamps:
            return []
        
        min_ts = min(timestamps)
        
        for d in sampled_data:
            ts = d.get("timestamp", 0)
            if not ts:
                continue
            
            time_offset = (ts - min_ts) / 1000.0
            interval_idx = int(time_offset / interval_size)
            
            interval = intervals[interval_idx]
            interval["time"] = interval_idx * interval_size
            
            label = d.get("label", "Unknown")
            
            # Overall metrics
            if d.get("sample_time"):
                interval["response_times"].append(d.get("sample_time", 0))
            if d.get("all_threads"):
                interval["vusers"].append(d.get("all_threads", 0))
            
            if not d.get("success", True):
                interval["fail_count"] += 1
            else:
                interval["pass_count"] += 1
            
            # Per-label (transaction/request) metrics
            label_data = interval["by_label"][label]
            if d.get("sample_time"):
                label_data["response_times"].append(d.get("sample_time", 0))
            if not d.get("success", True):
                label_data["fail_count"] += 1
            else:
                label_data["pass_count"] += 1
        
        time_series = []
        for idx in sorted(intervals.keys()):
            interval = intervals[idx]
            rt_values = interval["response_times"]
            vuser_values = interval["vusers"]
            
            # Calculate per-transaction/request response times and throughput
            by_label_data = {}
            for label, label_info in interval["by_label"].items():
                label_rt_values = label_info["response_times"]
                label_total = label_info["pass_count"] + label_info["fail_count"]
                by_label_data[label] = {
                    "avg_response_time": round(np.mean(label_rt_values) / 1000.0, 2) if label_rt_values else 0.0,
                    "throughput": round(label_total / interval_size, 2) if interval_size > 0 else 0.0
                }
            
            time_series.append({
                "time": round(interval["time"], 1),
                "avg_response_time": round(np.mean(rt_values) / 1000.0, 2) if rt_values else 0.0,
                "vusers": round(np.mean(vuser_values), 0) if vuser_values else 0.0,
                "throughput": round((interval["pass_count"] + interval["fail_count"]) / interval_size, 2) if interval_size > 0 else 0.0,
                "pass_count": interval["pass_count"],
                "fail_count": interval["fail_count"],
                "by_label": by_label_data
            })
        
        return time_series
    
    @staticmethod
    def _calculate_response_time_distribution(data: List[Dict]) -> Dict[str, float]:
        """Calculate response time distribution buckets"""
        total = len(data)
        if total == 0:
            return {"under_1s": 0, "1_to_2s": 0, "2_to_3s": 0, "3_to_5s": 0, "5_to_10s": 0, "over_10s": 0}
        
        return {
            "under_1s": (sum(1 for d in data if d.get("sample_time", 0) < 1000) / total * 100),
            "1_to_2s": (sum(1 for d in data if 1000 <= d.get("sample_time", 0) < 2000) / total * 100),
            "2_to_3s": (sum(1 for d in data if 2000 <= d.get("sample_time", 0) < 3000) / total * 100),
            "3_to_5s": (sum(1 for d in data if 3000 <= d.get("sample_time", 0) < 5000) / total * 100),
            "5_to_10s": (sum(1 for d in data if 5000 <= d.get("sample_time", 0) < 10000) / total * 100),
            "over_10s": (sum(1 for d in data if d.get("sample_time", 0) >= 10000) / total * 100)
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
            avg_rt = stats.get('avg_response', 0) / 1000.0  # Convert to seconds
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
        """Get grade title"""
        titles = {
            "A+": "Exceptional Performance",
            "A": "Excellent Performance",
            "B+": "Good Performance",
            "B": "Above Average",
            "C+": "Average Performance",
            "C": "Below Average",
            "D": "Poor Performance",
            "F": "Critical - Failing"
        }
        return titles.get(grade, "Unknown")
    
    @staticmethod
    def _get_grade_description(grade: str) -> str:
        """Get grade description"""
        descriptions = {
            "A+": "System exceeds all performance expectations",
            "A": "System meets or exceeds most performance benchmarks",
            "B+": "System performs well under normal conditions",
            "B": "System is functional but has noticeable performance gaps",
            "C+": "System meets minimum requirements but struggles under load",
            "C": "System has multiple performance issues",
            "D": "System fails to meet basic performance standards",
            "F": "System is experiencing severe performance problems"
        }
        return descriptions.get(grade, "Unknown")
    
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


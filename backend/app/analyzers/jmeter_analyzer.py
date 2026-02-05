import numpy as np
from typing import List, Dict, Tuple, Any
from app.models.jmeter import JMeterMetrics
from collections import Counter, defaultdict
from datetime import datetime

class JMeterAnalyzer:
    """Analyzer for JMeter test results with comprehensive metrics and grading"""
    
    # Grade definitions with descriptions
    GRADE_DEFINITIONS = {
        "A+": {
            "score_range": "90-100",
            "title": "Exceptional Performance",
            "description": "System exceeds all performance expectations. Response times are blazing fast, error rates are negligible, and the system handles load with ease. Ready for production at scale.",
            "class": "success"
        },
        "A": {
            "score_range": "80-89",
            "title": "Excellent Performance",
            "description": "System meets or exceeds most performance benchmarks. Minor optimizations may yield further improvements, but overall performance is strong and reliable.",
            "class": "success"
        },
        "B+": {
            "score_range": "75-79",
            "title": "Good Performance",
            "description": "System performs well under normal conditions. Some areas need attention to reach optimal levels. Recommended for production with monitoring.",
            "class": "warning"
        },
        "B": {
            "score_range": "70-74",
            "title": "Above Average",
            "description": "System is functional but has noticeable performance gaps. Several optimizations recommended before heavy production use.",
            "class": "warning"
        },
        "C+": {
            "score_range": "65-69",
            "title": "Average Performance",
            "description": "System meets minimum requirements but struggles under load. Significant improvements needed for reliable operation.",
            "class": "warning"
        },
        "C": {
            "score_range": "60-64",
            "title": "Below Average",
            "description": "System has multiple performance issues affecting user experience. Major optimizations required before production deployment.",
            "class": "warning"
        },
        "D": {
            "score_range": "50-59",
            "title": "Poor Performance",
            "description": "System fails to meet basic performance standards. Critical issues must be addressed. Not recommended for production use.",
            "class": "danger"
        },
        "F": {
            "score_range": "0-49",
            "title": "Critical - Failing",
            "description": "System is experiencing severe performance problems. Immediate intervention required. Production deployment should be halted until issues are resolved.",
            "class": "danger"
        }
    }
    
    # Category definitions with descriptions
    CATEGORY_DEFINITIONS = {
        "performance": {
            "name": "Performance",
            "icon": "⚡",
            "description": "Measures how fast the system responds to requests. Evaluates average response time and 95th percentile latency against industry benchmarks.",
            "weight": "30%",
            "metrics": ["Average Response Time", "95th Percentile Latency"],
            "targets": {
                "excellent": "< 1 second average response",
                "good": "1-2 seconds average response",
                "acceptable": "2-3 seconds average response",
                "poor": "> 3 seconds average response"
            }
        },
        "reliability": {
            "name": "Reliability",
            "icon": "🛡️",
            "description": "Assesses system stability and dependability. Measures success rate and error frequency to ensure consistent operation under various conditions.",
            "weight": "25%",
            "metrics": ["Success Rate", "Error Rate"],
            "targets": {
                "excellent": "> 99.9% uptime, < 0.1% errors",
                "good": "> 99% uptime, < 1% errors",
                "acceptable": "> 95% uptime, < 5% errors",
                "poor": "< 95% uptime or > 5% errors"
            }
        },
        "user_experience": {
            "name": "User Experience",
            "icon": "👥",
            "description": "Evaluates end-user satisfaction through SLA compliance. Tracks percentage of requests completing within acceptable time thresholds (2 seconds).",
            "weight": "25%",
            "metrics": ["SLA Compliance (< 2s)", "Response Time Distribution"],
            "targets": {
                "excellent": "> 95% requests under 2 seconds",
                "good": "> 90% requests under 2 seconds",
                "acceptable": "> 80% requests under 2 seconds",
                "poor": "< 80% requests under 2 seconds"
            }
        },
        "scalability": {
            "name": "Scalability",
            "icon": "📈",
            "description": "Measures system capacity to handle concurrent load. Evaluates throughput and ability to maintain performance as request volume increases.",
            "weight": "20%",
            "metrics": ["Throughput (req/s)", "Concurrent Handling"],
            "targets": {
                "excellent": "> 200 req/s with stable response",
                "good": "100-200 req/s with stable response",
                "acceptable": "50-100 req/s with stable response",
                "poor": "< 50 req/s or degrading performance"
            }
        }
    }
    
    @staticmethod
    def calculate_grade(score: float) -> Tuple[str, str]:
        """Calculate letter grade from score"""
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
    def get_grade_description(grade: str) -> dict:
        """Get full description for a grade"""
        return JMeterAnalyzer.GRADE_DEFINITIONS.get(grade, JMeterAnalyzer.GRADE_DEFINITIONS["F"])
    
    @staticmethod
    def get_category_description(category: str) -> dict:
        """Get full description for a category"""
        return JMeterAnalyzer.CATEGORY_DEFINITIONS.get(category, {})
    
    @staticmethod
    def score_metric(value: float, target: float, metric_type: str) -> int:
        """Score a metric out of 100 based on target"""
        if metric_type == "lower_is_better":  # For error rates, response times
            if value <= target:
                return 100
            elif value <= target * 2:
                return max(0, int(100 - ((value - target) / target) * 100))
            else:
                return max(0, int(50 - ((value - target * 2) / target) * 25))
        else:  # higher_is_better - For throughput, availability
            if value >= target:
                return 100
            else:
                return max(0, int((value / target) * 100))
    
    @staticmethod
    def _calculate_time_series(data: List[Dict], duration_seconds: float) -> List[Dict]:
        """Calculate time-series data grouped by time intervals - Optimized for large datasets"""
        if not data or duration_seconds <= 0:
            return []
        
        # Optimize: Sample data if too large (process max 50k records for time series)
        max_records = 50000
        if len(data) > max_records:
            # Sample evenly across the dataset
            step = len(data) // max_records
            data = data[::step]
        
        # Determine interval size (aim for 50-100 data points)
        num_intervals = min(100, max(20, int(duration_seconds / 10)))  # 10-second intervals, max 100 points
        interval_size = duration_seconds / num_intervals
        
        # Get min timestamp - optimized
        timestamps = [d.get("timestamp") for d in data if d.get("timestamp")]
        if not timestamps:
            return []
        
        min_timestamp = min(timestamps)
        
        # Group data by time intervals - use defaultdict for better performance
        from collections import defaultdict
        intervals = defaultdict(lambda: {
            "response_times": [],
            "vusers": [],
            "pass_count": 0,
            "fail_count": 0,
            "total_count": 0
        })
        
        # Process data in batches for better memory efficiency
        for d in data:
            timestamp = d.get("timestamp")
            if not timestamp:
                continue
            
            # Calculate which interval this data point belongs to
            time_offset = (timestamp - min_timestamp) / 1000  # Convert to seconds
            interval_index = int(time_offset / interval_size)
            
            interval = intervals[interval_index]
            if "time" not in interval:
                interval["time"] = interval_index * interval_size
            
            interval["total_count"] += 1
            
            # Add response time
            sample_time = d.get("sample_time")
            if sample_time is not None:
                interval["response_times"].append(sample_time)
            
            # Add VUsers (all_threads)
            all_threads = d.get("all_threads")
            if all_threads is not None:
                interval["vusers"].append(all_threads)
            
            # Count pass/fail
            if d.get("success") is False or (d.get("response_code") and str(d.get("response_code")).startswith(("4", "5"))):
                interval["fail_count"] += 1
            else:
                interval["pass_count"] += 1
        
        # Calculate metrics for each interval - optimized with numpy
        time_series = []
        sorted_indices = sorted(intervals.keys())
        for idx in sorted_indices:
            interval = intervals[idx]
            # Use numpy for faster calculations
            avg_response = float(np.mean(interval["response_times"]) / 1000) if interval["response_times"] else 0.0
            avg_vusers = float(np.mean(interval["vusers"])) if interval["vusers"] else 0.0
            throughput = float(interval["total_count"] / interval_size) if interval_size > 0 else 0.0
            
            time_series.append({
                "time": round(interval["time"], 1),
                "avg_response_time": round(avg_response, 2),
                "vusers": round(avg_vusers, 0),
                "throughput": round(throughput, 2),
                "pass_count": interval["pass_count"],
                "fail_count": interval["fail_count"]
            })
        
        return time_series
    
    @staticmethod
    def calculate_percentile_stats(values):
        """Calculate comprehensive percentile statistics"""
        if not values:
            return {
                "mean": None, "median": None, 
                "p70": None, "p75": None, "p80": None, "p90": None, "p95": None, "p99": None,
                "min": None, "max": None
            }
        arr = np.array(values)
        return {
            "mean": float(np.mean(arr)),
            "median": float(np.median(arr)),
            "p70": float(np.percentile(arr, 70)),
            "p75": float(np.percentile(arr, 75)),
            "p80": float(np.percentile(arr, 80)),
            "p90": float(np.percentile(arr, 90)),
            "p95": float(np.percentile(arr, 95)),
            "p99": float(np.percentile(arr, 99)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr))
        }
    
    @staticmethod
    def identify_critical_issues(metrics: dict, endpoint_stats: dict) -> List[dict]:
        """Identify critical performance issues"""
        issues = []
        
        # Issue 1: High error rate
        error_rate = metrics.get("error_rate_pct", 0)
        if error_rate > 5:
            issues.append({
                "title": f"High Error Rate - {error_rate:.2f}%",
                "impact": f"{error_rate:.2f}% of requests failing, directly affecting user experience and business operations",
                "affected": "System-wide or specific endpoints with high failure rates",
                "priority": "P0 CRITICAL",
                "timeline": "1-2 weeks"
            })
        
        # Issue 2: Slow response times
        avg_response_sec = metrics.get("avg_response_sec", 0)
        if avg_response_sec > 3:
            issues.append({
                "title": f"Slow Response Times - {avg_response_sec:.1f}s Average",
                "impact": "Poor user experience, productivity loss, and potential user abandonment",
                "affected": "System-wide performance degradation",
                "priority": "P0 CRITICAL" if avg_response_sec > 5 else "P1 HIGH",
                "timeline": "2-4 weeks"
            })
        
        # Issue 3: Identify slowest endpoints
        slowest_endpoints = sorted(endpoint_stats.items(), 
                                   key=lambda x: x[1].get("avg_response", 0), 
                                   reverse=True)[:3]
        
        for endpoint, stats in slowest_endpoints:
            avg_resp = stats.get("avg_response", 0) / 1000  # Convert to seconds
            if avg_resp > 10:
                issues.append({
                    "title": f"Critical Endpoint Performance - {endpoint}",
                    "impact": f"{avg_resp:.1f}s average response time making functionality unusable",
                    "affected": endpoint,
                    "priority": "P0 CRITICAL",
                    "timeline": "1-2 weeks"
                })
        
        # Issue 4: SLA compliance
        sla_compliance = metrics.get("sla_compliance_pct", 100)
        if sla_compliance < 80:
            issues.append({
                "title": f"Low SLA Compliance - {sla_compliance:.1f}%",
                "impact": "Majority of requests not meeting performance expectations",
                "affected": "System-wide SLA violations",
                "priority": "P1 HIGH",
                "timeline": "4-6 weeks"
            })
        
        return issues[:5]  # Return top 5 issues
    
    @staticmethod
    def generate_recommendations(metrics: dict, grade: str) -> List[dict]:
        """Generate improvement recommendations based on performance"""
        recommendations = []
        
        # Performance recommendations
        avg_response_sec = metrics.get("avg_response_sec", 0)
        if avg_response_sec > 2:
            recommendations.append({
                "category": "Performance",
                "priority": "High",
                "items": [
                    "Implement database query optimization and indexing",
                    "Add Redis caching layer for frequently accessed data",
                    "Optimize API endpoints and reduce payload sizes",
                    "Implement CDN for static assets"
                ]
            })
        
        # Reliability recommendations
        error_rate = metrics.get("error_rate_pct", 0)
        if error_rate > 1:
            recommendations.append({
                "category": "Reliability",
                "priority": "Critical",
                "items": [
                    "Root cause analysis of failing endpoints",
                    "Implement circuit breakers and retry mechanisms",
                    "Add comprehensive error handling and logging",
                    "Set up real-time error monitoring and alerting"
                ]
            })
        
        # Scalability recommendations
        throughput = metrics.get("throughput", 0)
        if throughput < 100:
            recommendations.append({
                "category": "Scalability",
                "priority": "Medium",
                "items": [
                    "Implement horizontal scaling with load balancing",
                    "Use asynchronous processing for heavy operations",
                    "Optimize connection pooling and resource management",
                    "Consider microservices architecture for bottleneck areas"
                ]
            })
        
        # Monitoring recommendations
        recommendations.append({
            "category": "Monitoring & Observability",
            "priority": "High",
            "items": [
                "Implement APM (Application Performance Monitoring)",
                "Set up distributed tracing for request flows",
                "Create real-time dashboards for key metrics",
                "Establish automated performance regression testing"
            ]
        })
        
        return recommendations
    
    @staticmethod
    def calculate_improvement_roadmap(current_grade: str, current_score: float) -> List[dict]:
        """Calculate improvement roadmap to achieve A+ grade"""
        target_score = 95  # A+ grade
        score_gap = target_score - current_score
        
        phases = [
            {
                "phase": "Phase 1: Critical Fixes",
                "timeline": "Week 1-4",
                "target_grade": "B",
                "target_score": 75,
                "impact_points": min(10, score_gap * 0.3),
                "improvements": [
                    "Fix critical bugs and errors causing failures",
                    "Optimize slowest endpoints and database queries",
                    "Implement basic caching mechanisms",
                    "Add timeouts and circuit breakers"
                ],
                "expected_impact": "Core functionality restored, error rate reduced"
            },
            {
                "phase": "Phase 2: Performance Optimization",
                "timeline": "Week 4-12",
                "target_grade": "A-",
                "target_score": 85,
                "impact_points": min(12, score_gap * 0.4),
                "improvements": [
                    "Database layer optimization with compound indexes",
                    "Implement Redis caching and CDN",
                    "API optimization and async processing",
                    "Infrastructure scaling and load balancing"
                ],
                "expected_impact": "40-50% response time improvement"
            },
            {
                "phase": "Phase 3: Excellence Optimization",
                "timeline": "Week 12-24",
                "target_grade": "A+",
                "target_score": 95,
                "impact_points": min(10, score_gap * 0.3),
                "improvements": [
                    "High availability architecture with multi-zone deployment",
                    "Advanced monitoring and predictive analytics",
                    "Frontend optimization and progressive loading",
                    "Automated performance testing in CI/CD"
                ],
                "expected_impact": "Industry-leading performance and reliability"
            }
        ]
        
        return phases
    
    @staticmethod
    def analyze(data: List[Dict]) -> JMeterMetrics:
        """Analyze JMeter data and return comprehensive metrics"""
        if not data:
            raise ValueError("No data provided for analysis")
        
        # Extract metrics
        latency_values = [d.get("latency") for d in data if d.get("latency") is not None]
        sample_time_values = [d.get("sample_time") for d in data if d.get("sample_time") is not None]
        connect_time_values = [d.get("connect_time") for d in data if d.get("connect_time") is not None]
        
        # Calculate errors
        errors = sum(1 for d in data if d.get("success") is False or 
                    (d.get("response_code") and str(d.get("response_code")).startswith(("4", "5"))))
        
        # Calculate test duration
        if data and data[0].get("timestamp"):
            timestamps = [d.get("timestamp") for d in data if d.get("timestamp")]
            if timestamps:
                duration_seconds = (max(timestamps) - min(timestamps)) / 1000
                duration_hours = duration_seconds / 3600
                throughput = len(data) / duration_seconds if duration_seconds > 0 else 0
            else:
                duration_seconds = 0
                duration_hours = 0
                throughput = 0
        else:
            duration_seconds = 0
            duration_hours = 0
            throughput = 0
        
        # Response codes distribution
        response_codes = Counter([str(d.get("response_code")) for d in data if d.get("response_code")])
        
        # Separate transactions vs requests
        # Transactions typically start with "T" and requests with "api/"
        transactions = {}
        requests = {}
        
        for d in data:
            label = d.get("label") or "Unknown"
            is_transaction = label.startswith("T") or not label.startswith("api")
            target_dict = transactions if is_transaction else requests
            
            if label not in target_dict:
                target_dict[label] = []
            target_dict[label].append(d)
        
        def analyze_endpoint_group(endpoint_data: dict) -> dict:
            """Analyze a group of endpoints (transactions or requests)"""
            endpoint_stats = {}
            for label, items in endpoint_data.items():
                response_times = [d.get("sample_time") for d in items if d.get("sample_time") is not None]
                label_errors = sum(1 for d in items if d.get("success") is False)
                
                stats = JMeterAnalyzer.calculate_percentile_stats(response_times)
                endpoint_stats[label] = {
                    "count": len(items),
                    "errors": label_errors,
                    "error_rate": (label_errors / len(items) * 100) if items else 0,
                    "avg_response": stats.get("mean"),
                    "median": stats.get("median"),
                    "p70": stats.get("p70"),
                    "p75": stats.get("p75"),
                    "p80": stats.get("p80"),
                    "p90": stats.get("p90"),
                    "p95": stats.get("p95"),
                    "p99": stats.get("p99"),
                    "min": stats.get("min"),
                    "max": stats.get("max")
                }
            return endpoint_stats
        
        transaction_stats = analyze_endpoint_group(transactions)
        request_stats = analyze_endpoint_group(requests)
        
        # Calculate comprehensive statistics
        response_time_stats = JMeterAnalyzer.calculate_percentile_stats(sample_time_values)
        
        # Calculate metrics for scoring
        avg_response = response_time_stats.get("mean", 0)
        avg_response_sec = avg_response / 1000 if avg_response else 0
        p95_response = response_time_stats.get("p95", 0)
        success_rate = (len(data) - errors) / len(data) * 100 if data else 0
        error_rate_pct = (errors / len(data) * 100) if data else 0
        
        # Calculate scores (out of 100)
        availability_score = JMeterAnalyzer.score_metric(success_rate, 99, "higher_is_better")
        response_time_score = JMeterAnalyzer.score_metric(avg_response_sec, 2, "lower_is_better")
        error_rate_score = JMeterAnalyzer.score_metric(error_rate_pct, 1, "lower_is_better")
        throughput_score = JMeterAnalyzer.score_metric(throughput, 100, "higher_is_better")
        p95_score = JMeterAnalyzer.score_metric(p95_response / 1000, 3, "lower_is_better")
        
        # SLA Compliance (requests < 2 seconds)
        sla_compliant_2s = sum(1 for d in data if d.get("sample_time", 0) < 2000)
        sla_compliant_3s = sum(1 for d in data if d.get("sample_time", 0) < 3000)
        sla_compliant_5s = sum(1 for d in data if d.get("sample_time", 0) < 5000)
        
        sla_compliance_2s_pct = (sla_compliant_2s / len(data) * 100) if data else 0
        sla_compliance_3s_pct = (sla_compliant_3s / len(data) * 100) if data else 0
        sla_compliance_5s_pct = (sla_compliant_5s / len(data) * 100) if data else 0
        
        sla_score = JMeterAnalyzer.score_metric(sla_compliance_2s_pct, 95, "higher_is_better")
        
        # Weighted category scores
        performance_score = (response_time_score + p95_score) / 2
        reliability_score = (availability_score + error_rate_score) / 2
        user_experience_score = sla_score
        scalability_score = throughput_score
        
        # Calculate individual grades
        perf_grade, perf_class = JMeterAnalyzer.calculate_grade(performance_score)
        rel_grade, rel_class = JMeterAnalyzer.calculate_grade(reliability_score)
        ux_grade, ux_class = JMeterAnalyzer.calculate_grade(user_experience_score)
        scale_grade, scale_class = JMeterAnalyzer.calculate_grade(scalability_score)
        
        # Weighted overall score
        overall_score = (
            performance_score * 0.30 +
            reliability_score * 0.25 +
            user_experience_score * 0.25 +
            scalability_score * 0.20
        )
        
        grade, grade_class = JMeterAnalyzer.calculate_grade(overall_score)
        
        # Prepare metrics dictionary for issue identification
        metrics_for_analysis = {
            "error_rate_pct": error_rate_pct,
            "avg_response_sec": avg_response_sec,
            "sla_compliance_pct": sla_compliance_2s_pct,
            "throughput": throughput
        }
        
        # All endpoint stats for issue identification
        all_endpoint_stats = {**transaction_stats, **request_stats}
        
        # Generate critical issues and recommendations
        critical_issues = JMeterAnalyzer.identify_critical_issues(metrics_for_analysis, all_endpoint_stats)
        recommendations = JMeterAnalyzer.generate_recommendations(metrics_for_analysis, grade)
        improvement_roadmap = JMeterAnalyzer.calculate_improvement_roadmap(grade, overall_score)
        
        # Get grade and category descriptions
        overall_grade_info = JMeterAnalyzer.get_grade_description(grade)
        perf_category = JMeterAnalyzer.get_category_description("performance")
        rel_category = JMeterAnalyzer.get_category_description("reliability")
        ux_category = JMeterAnalyzer.get_category_description("user_experience")
        scale_category = JMeterAnalyzer.get_category_description("scalability")
        
        # Grade reasons for cards with full descriptions
        grade_reasons = {
            "performance": {
                "grade": perf_grade,
                "score": round(performance_score, 1),
                "reason": f"{avg_response_sec:.1f}s avg, {p95_response/1000:.1f}s 95th percentile",
                "class": perf_class,
                "name": perf_category.get("name", "Performance"),
                "icon": perf_category.get("icon", "⚡"),
                "description": perf_category.get("description", ""),
                "weight": perf_category.get("weight", "30%"),
                "metrics": perf_category.get("metrics", []),
                "targets": perf_category.get("targets", {}),
                "grade_info": JMeterAnalyzer.get_grade_description(perf_grade)
            },
            "reliability": {
                "grade": rel_grade,
                "score": round(reliability_score, 1),
                "reason": f"{success_rate:.1f}% uptime, {error_rate_pct:.2f}% error rate",
                "class": rel_class,
                "name": rel_category.get("name", "Reliability"),
                "icon": rel_category.get("icon", "🛡️"),
                "description": rel_category.get("description", ""),
                "weight": rel_category.get("weight", "25%"),
                "metrics": rel_category.get("metrics", []),
                "targets": rel_category.get("targets", {}),
                "grade_info": JMeterAnalyzer.get_grade_description(rel_grade)
            },
            "user_experience": {
                "grade": ux_grade,
                "score": round(user_experience_score, 1),
                "reason": f"{sla_compliance_2s_pct:.1f}% meet 2-second SLA target",
                "class": ux_class,
                "name": ux_category.get("name", "User Experience"),
                "icon": ux_category.get("icon", "👥"),
                "description": ux_category.get("description", ""),
                "weight": ux_category.get("weight", "25%"),
                "metrics": ux_category.get("metrics", []),
                "targets": ux_category.get("targets", {}),
                "grade_info": JMeterAnalyzer.get_grade_description(ux_grade)
            },
            "scalability": {
                "grade": scale_grade,
                "score": round(scalability_score, 1),
                "reason": f"{throughput:.1f} req/s throughput",
                "class": scale_class,
                "name": scale_category.get("name", "Scalability"),
                "icon": scale_category.get("icon", "📈"),
                "description": scale_category.get("description", ""),
                "weight": scale_category.get("weight", "20%"),
                "metrics": scale_category.get("metrics", []),
                "targets": scale_category.get("targets", {}),
                "grade_info": JMeterAnalyzer.get_grade_description(scale_grade)
            }
        }
        
        # Overall grade description
        overall_grade_description = {
            "grade": grade,
            "score": round(overall_score, 1),
            "title": overall_grade_info.get("title", ""),
            "description": overall_grade_info.get("description", ""),
            "score_range": overall_grade_info.get("score_range", ""),
            "class": grade_class
        }
        
        # Response time distribution for charts
        rt_distribution = {
            "under_1s": sum(1 for d in data if d.get("sample_time", 0) < 1000) / len(data) * 100 if data else 0,
            "1_to_2s": sum(1 for d in data if 1000 <= d.get("sample_time", 0) < 2000) / len(data) * 100 if data else 0,
            "2_to_3s": sum(1 for d in data if 2000 <= d.get("sample_time", 0) < 3000) / len(data) * 100 if data else 0,
            "3_to_5s": sum(1 for d in data if 3000 <= d.get("sample_time", 0) < 5000) / len(data) * 100 if data else 0,
            "5_to_10s": sum(1 for d in data if 5000 <= d.get("sample_time", 0) < 10000) / len(data) * 100 if data else 0,
            "over_10s": sum(1 for d in data if d.get("sample_time", 0) >= 10000) / len(data) * 100 if data else 0,
        }
        
        # Calculate time-series data for system behaviour graph
        time_series_data = JMeterAnalyzer._calculate_time_series(data, duration_seconds)
        
        metrics = JMeterMetrics(
            total_samples=len(data),
            total_errors=errors,
            error_rate=errors / len(data) if data else 0,
            throughput=throughput,
            latency=JMeterAnalyzer.calculate_percentile_stats(latency_values),
            sample_time=response_time_stats,
            connect_time=JMeterAnalyzer.calculate_percentile_stats(connect_time_values),
            response_codes=dict(response_codes),
            labels={**transaction_stats, **request_stats},
            summary={
                "test_duration_hours": round(duration_hours, 2),
                "success_rate": success_rate,
                "avg_throughput": throughput,
                "sla_compliance_2s": sla_compliance_2s_pct,
                "sla_compliance_3s": sla_compliance_3s_pct,
                "sla_compliance_5s": sla_compliance_5s_pct,
                "overall_score": round(overall_score, 2),
                "overall_grade": grade,
                "grade_class": grade_class,
                "overall_grade_description": overall_grade_description,
                "grade_reasons": grade_reasons,
                "response_time_distribution": rt_distribution,
                "time_series_data": time_series_data,
                "transaction_stats": transaction_stats,
                "request_stats": request_stats,
                "critical_issues": critical_issues,
                "recommendations": recommendations,
                "improvement_roadmap": improvement_roadmap,
                "scores": {
                    "availability": availability_score,
                    "response_time": response_time_score,
                    "error_rate": error_rate_score,
                    "throughput": throughput_score,
                    "p95_percentile": p95_score,
                    "sla_compliance": sla_score,
                    "performance": round(performance_score, 2),
                    "reliability": round(reliability_score, 2),
                    "user_experience": round(user_experience_score, 2),
                    "scalability": round(scalability_score, 2)
                },
                "targets": {
                    "availability": 99,
                    "response_time": 2000,
                    "error_rate": 1,
                    "throughput": 100,
                    "p95_percentile": 3000,
                    "sla_compliance": 95
                }
            }
        )
        
        return metrics
    
    @staticmethod
    def consolidate_metrics(all_metrics: List[Dict[str, Any]], filenames: List[str] = None) -> Dict[str, Any]:
        """
        Consolidate metrics from multiple JMeter files into a single metrics object
        Combines all data points, recalculates statistics, and merges findings
        """
        if not all_metrics:
            raise ValueError("No metrics provided for consolidation")
        
        if len(all_metrics) == 1:
            # Single file, return as-is
            return all_metrics[0]
        
        filenames = filenames or [f"File_{i+1}" for i in range(len(all_metrics))]
        
        # Initialize consolidated values
        consolidated = {
            "total_samples": 0,
            "total_errors": 0,
            "error_rate": 0,
            "throughput": 0,
            "response_codes": Counter(),
            "transaction_stats": {},
            "request_stats": {},
            "time_series_data": [],
            "critical_issues": [],
            "recommendations": [],
            "improvement_roadmap": [],
            "all_sample_times": [],
            "all_latency_values": [],
            "all_connect_times": [],
            "all_response_codes": [],
            "test_duration_seconds": 0,
            "file_info": []
        }
        
        # Collect data from all files
        for idx, metrics in enumerate(all_metrics):
            consolidated["total_samples"] += metrics.get("total_samples", 0)
            consolidated["total_errors"] += metrics.get("total_errors", 0)
            
            # Collect response codes
            response_codes = metrics.get("response_codes", {})
            if isinstance(response_codes, dict):
                for code, count in response_codes.items():
                    consolidated["response_codes"][code] = consolidated["response_codes"].get(code, 0) + count
            
            # Merge transaction stats
            transaction_stats = metrics.get("summary", {}).get("transaction_stats", {})
            for label, stats in transaction_stats.items():
                if label not in consolidated["transaction_stats"]:
                    consolidated["transaction_stats"][label] = {
                        "count": 0,
                        "errors": 0,
                        "response_times": [],
                        "file_sources": []
                    }
                consolidated["transaction_stats"][label]["count"] += stats.get("count", 0)
                consolidated["transaction_stats"][label]["errors"] += stats.get("errors", 0)
                consolidated["transaction_stats"][label]["file_sources"].append(filenames[idx] if idx < len(filenames) else f"File_{idx+1}")
            
            # Merge request stats
            request_stats = metrics.get("summary", {}).get("request_stats", {})
            for label, stats in request_stats.items():
                if label not in consolidated["request_stats"]:
                    consolidated["request_stats"][label] = {
                        "count": 0,
                        "errors": 0,
                        "response_times": [],
                        "file_sources": []
                    }
                consolidated["request_stats"][label]["count"] += stats.get("count", 0)
                consolidated["request_stats"][label]["errors"] += stats.get("errors", 0)
                consolidated["request_stats"][label]["file_sources"].append(filenames[idx] if idx < len(filenames) else f"File_{idx+1}")
            
            # Collect time series data
            time_series = metrics.get("summary", {}).get("time_series_data", [])
            for ts_point in time_series:
                # Add file identifier to time series data
                ts_point_copy = ts_point.copy()
                ts_point_copy["source_file"] = filenames[idx] if idx < len(filenames) else f"File_{idx+1}"
                consolidated["time_series_data"].append(ts_point_copy)
            
            # Collect critical issues (with file source)
            critical_issues = metrics.get("summary", {}).get("critical_issues", [])
            for issue in critical_issues:
                issue_copy = issue.copy()
                issue_copy["source_file"] = filenames[idx] if idx < len(filenames) else f"File_{idx+1}"
                consolidated["critical_issues"].append(issue_copy)
            
            # Collect recommendations (deduplicate)
            recommendations = metrics.get("summary", {}).get("recommendations", [])
            for rec in recommendations:
                if rec not in consolidated["recommendations"]:
                    consolidated["recommendations"].append(rec)
            
            # Collect improvement roadmap (merge phases)
            roadmap = metrics.get("summary", {}).get("improvement_roadmap", [])
            consolidated["improvement_roadmap"].extend(roadmap)
            
            # Collect sample times, latency, connect times for percentile recalculation
            sample_time = metrics.get("sample_time", {})
            latency = metrics.get("latency", {})
            connect_time = metrics.get("connect_time", {})
            
            # Store file info
            consolidated["file_info"].append({
                "filename": filenames[idx] if idx < len(filenames) else f"File_{idx+1}",
                "samples": metrics.get("total_samples", 0),
                "errors": metrics.get("total_errors", 0),
                "throughput": metrics.get("throughput", 0)
            })
        
        # Recalculate error rate
        consolidated["error_rate"] = consolidated["total_errors"] / consolidated["total_samples"] if consolidated["total_samples"] > 0 else 0
        
        # Sort and merge time series data by time
        if consolidated["time_series_data"]:
            consolidated["time_series_data"].sort(key=lambda x: x.get("time", 0))
            # Merge overlapping time points
            merged_time_series = JMeterAnalyzer._merge_time_series_data(consolidated["time_series_data"])
            consolidated["time_series_data"] = merged_time_series
        
        # Recalculate transaction/request stats with consolidated data
        for label, stats in consolidated["transaction_stats"].items():
            # Recalculate error rate
            stats["error_rate"] = (stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0
        
        for label, stats in consolidated["request_stats"].items():
            # Recalculate error rate
            stats["error_rate"] = (stats["errors"] / stats["count"] * 100) if stats["count"] > 0 else 0
        
        # Use first file's structure as base and update with consolidated data
        base_metrics = all_metrics[0].copy()
        
        # Update with consolidated values
        base_metrics["total_samples"] = consolidated["total_samples"]
        base_metrics["total_errors"] = consolidated["total_errors"]
        base_metrics["error_rate"] = consolidated["error_rate"]
        
        # Calculate weighted average throughput
        total_duration = sum(info.get("samples", 0) / max(info.get("throughput", 1), 1) for info in consolidated["file_info"] if info.get("throughput", 0) > 0)
        if total_duration > 0:
            base_metrics["throughput"] = consolidated["total_samples"] / total_duration
        else:
            # Fallback to average
            base_metrics["throughput"] = sum(info.get("throughput", 0) for info in consolidated["file_info"]) / len(consolidated["file_info"]) if consolidated["file_info"] else 0
        
        # Update response codes
        base_metrics["response_codes"] = dict(consolidated["response_codes"])
        
        # Update summary with consolidated data
        summary = base_metrics.get("summary", {}).copy()
        summary["transaction_stats"] = consolidated["transaction_stats"]
        summary["request_stats"] = consolidated["request_stats"]
        summary["time_series_data"] = consolidated["time_series_data"]
        summary["critical_issues"] = consolidated["critical_issues"]
        summary["recommendations"] = consolidated["recommendations"]
        summary["improvement_roadmap"] = consolidated["improvement_roadmap"]
        summary["file_info"] = consolidated["file_info"]
        summary["file_count"] = len(all_metrics)
        summary["consolidated_from_files"] = filenames
        
        # Recalculate success rate
        summary["success_rate"] = ((consolidated["total_samples"] - consolidated["total_errors"]) / consolidated["total_samples"] * 100) if consolidated["total_samples"] > 0 else 0
        
        # Recalculate test duration (sum of all test durations or max)
        test_durations = [m.get("summary", {}).get("test_duration_hours", 0) for m in all_metrics]
        summary["test_duration_hours"] = max(test_durations) if test_durations else 0
        
        # Recalculate SLA compliance based on consolidated sample times
        # For now, use weighted average from individual files
        sla_compliances_2s = [m.get("summary", {}).get("sla_compliance_2s", 0) for m in all_metrics]
        sla_compliances_3s = [m.get("summary", {}).get("sla_compliance_3s", 0) for m in all_metrics]
        sla_compliances_5s = [m.get("summary", {}).get("sla_compliance_5s", 0) for m in all_metrics]
        
        # Weighted average by sample count
        total_samples_for_sla = sum(m.get("total_samples", 0) for m in all_metrics)
        if total_samples_for_sla > 0:
            summary["sla_compliance_2s"] = sum(m.get("summary", {}).get("sla_compliance_2s", 0) * m.get("total_samples", 0) for m in all_metrics) / total_samples_for_sla
            summary["sla_compliance_3s"] = sum(m.get("summary", {}).get("sla_compliance_3s", 0) * m.get("total_samples", 0) for m in all_metrics) / total_samples_for_sla
            summary["sla_compliance_5s"] = sum(m.get("summary", {}).get("sla_compliance_5s", 0) * m.get("total_samples", 0) for m in all_metrics) / total_samples_for_sla
        else:
            summary["sla_compliance_2s"] = sum(sla_compliances_2s) / len(sla_compliances_2s) if sla_compliances_2s else 0
            summary["sla_compliance_3s"] = sum(sla_compliances_3s) / len(sla_compliances_3s) if sla_compliances_3s else 0
            summary["sla_compliance_5s"] = sum(sla_compliances_5s) / len(sla_compliances_5s) if sla_compliances_5s else 0
        
        # Recalculate response time statistics using weighted averages
        # Since we don't have raw data, use weighted average of percentiles from each file
        sample_time_weights = []
        sample_time_stats = []
        
        for metrics in all_metrics:
            file_samples = metrics.get("total_samples", 0)
            if file_samples > 0:
                sample_time = metrics.get("sample_time", {})
                if sample_time and sample_time.get("mean") is not None:
                    sample_time_weights.append(file_samples)
                    sample_time_stats.append(sample_time)
        
        if sample_time_stats and sample_time_weights:
            # Calculate weighted average for each percentile
            total_weight = sum(sample_time_weights)
            consolidated_sample_time = {}
            
            # For each percentile, calculate weighted average
            percentiles = ["mean", "median", "p70", "p75", "p80", "p90", "p95", "p99", "min", "max"]
            for p in percentiles:
                weighted_sum = sum(stat.get(p, 0) * weight for stat, weight in zip(sample_time_stats, sample_time_weights) if stat.get(p) is not None)
                count = sum(1 for stat in sample_time_stats if stat.get(p) is not None)
                if count > 0:
                    consolidated_sample_time[p] = weighted_sum / sum(w for stat, w in zip(sample_time_stats, sample_time_weights) if stat.get(p) is not None)
                else:
                    consolidated_sample_time[p] = None
            
            # For min/max, use actual min/max across all files
            consolidated_sample_time["min"] = min(stat.get("min", float('inf')) for stat in sample_time_stats if stat.get("min") is not None)
            consolidated_sample_time["max"] = max(stat.get("max", 0) for stat in sample_time_stats if stat.get("max") is not None)
            
            base_metrics["sample_time"] = consolidated_sample_time
            # Update summary with new avg response time
            summary["avg_response_time"] = consolidated_sample_time.get("mean", 0) / 1000 if consolidated_sample_time.get("mean") else 0
        else:
            # Fallback to first file's sample_time
            base_metrics["sample_time"] = all_metrics[0].get("sample_time", {})
        
        # Recalculate overall score and grade based on consolidated metrics
        # Use the scoring logic from JMeterAnalyzer
        consolidated_metrics_for_scoring = {
            "total_samples": consolidated["total_samples"],
            "total_errors": consolidated["total_errors"],
            "error_rate": consolidated["error_rate"],
            "throughput": base_metrics["throughput"],
            "sample_time": base_metrics.get("sample_time", {}),
            "summary": summary
        }
        
        # Recalculate grade (simplified - use existing logic)
        # For now, use weighted average of individual scores
        scores = [m.get("summary", {}).get("overall_score", 0) for m in all_metrics]
        sample_counts = [m.get("total_samples", 0) for m in all_metrics]
        total_samples_for_score = sum(sample_counts)
        if total_samples_for_score > 0:
            summary["overall_score"] = sum(score * count for score, count in zip(scores, sample_counts)) / total_samples_for_score
        else:
            summary["overall_score"] = sum(scores) / len(scores) if scores else 0
        
        # Determine grade from score
        grade, grade_class = JMeterAnalyzer.calculate_grade(summary["overall_score"])
        summary["overall_grade"] = grade
        summary["grade_class"] = grade_class
        
        # Get grade description
        grade_info = JMeterAnalyzer.GRADE_DEFINITIONS.get(grade, {})
        summary["overall_grade_description"] = {
            "grade": grade,
            "score": round(summary["overall_score"], 1),
            "title": grade_info.get("title", ""),
            "description": grade_info.get("description", ""),
            "score_range": grade_info.get("score_range", ""),
            "class": grade_class
        }
        
        # Recalculate grade reasons (simplified - use weighted approach)
        # For now, use first file's grade reasons
        summary["grade_reasons"] = all_metrics[0].get("summary", {}).get("grade_reasons", {})
        
        # Recalculate response time distribution using weighted average from individual files
        rt_distributions = [m.get("summary", {}).get("response_time_distribution", {}) for m in all_metrics]
        sample_counts_for_dist = [m.get("total_samples", 0) for m in all_metrics]
        total_samples_for_dist = sum(sample_counts_for_dist)
        
        if rt_distributions and total_samples_for_dist > 0:
            rt_distribution = {}
            for key in ["under_1s", "1_to_2s", "2_to_3s", "3_to_5s", "5_to_10s", "over_10s"]:
                weighted_sum = sum(dist.get(key, 0) * count for dist, count in zip(rt_distributions, sample_counts_for_dist) if dist.get(key) is not None)
                rt_distribution[key] = weighted_sum / total_samples_for_dist
            summary["response_time_distribution"] = rt_distribution
        else:
            # Fallback to first file's distribution
            summary["response_time_distribution"] = all_metrics[0].get("summary", {}).get("response_time_distribution", {})
        
        base_metrics["summary"] = summary
        
        return base_metrics
    
    @staticmethod
    def _merge_time_series_data(time_series_data: List[Dict]) -> List[Dict]:
        """Merge time series data points that are close in time"""
        if not time_series_data:
            return []
        
        # Group by time intervals (round to nearest second)
        time_groups = defaultdict(list)
        for point in time_series_data:
            time_key = round(point.get("time", 0))
            time_groups[time_key].append(point)
        
        # Merge points in the same time interval
        merged = []
        for time_key in sorted(time_groups.keys()):
            points = time_groups[time_key]
            if len(points) == 1:
                merged.append(points[0])
            else:
                # Merge multiple points at same time
                merged_point = {
                    "time": time_key,
                    "avg_response_time": sum(p.get("avg_response_time", 0) for p in points) / len(points),
                    "vusers": sum(p.get("vusers", 0) for p in points) / len(points),
                    "throughput": sum(p.get("throughput", 0) for p in points),
                    "pass_count": sum(p.get("pass_count", 0) for p in points),
                    "fail_count": sum(p.get("fail_count", 0) for p in points),
                    "total_count": sum(p.get("total_count", 0) for p in points),
                    "source_files": list(set(p.get("source_file", "Unknown") for p in points))
                }
                merged.append(merged_point)
        
        return merged
    
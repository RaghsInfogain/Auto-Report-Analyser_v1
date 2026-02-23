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
        
        # Skewness interpretation for response time with DYNAMIC root cause analysis
        response_time_skewness = sample_time_stats.get("skewness", 0)
        skewness_interpretation = JMeterAnalyzerV2._interpret_skewness(
            response_time_skewness, 
            "response time",
            {
                "avg_response": avg_response_sec,
                "p95_response": p95_response / 1000.0,
                "p99_response": sample_time_stats.get("p99", 0) / 1000.0,
                "max_response": sample_time_stats.get("max", 0) / 1000.0,
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
            throughput, p95_response / 1000.0, sla_compliance_2s_pct, 
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
        """Calculate percentile statistics efficiently with skewness"""
        if len(values) == 0:
            return {
                "mean": 0.0, "median": 0.0, "p70": 0.0, "p75": 0.0, "p80": 0.0,
                "p90": 0.0, "p95": 0.0, "p99": 0.0, "min": 0.0, "max": 0.0,
                "std": 0.0, "skewness": 0.0
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
            # DYNAMIC ROOT CAUSE ANALYSIS based on actual data
            severity = "critical" if skewness > 2 else ("danger" if skewness > 1 else "warning")
            
            # Analyze actual data to identify specific root causes
            root_causes = []
            evidence = []
            
            # 1. Analyze response time patterns
            if p99_response > avg_response * 3:
                root_causes.append("Severe tail latency - 99th percentile is {}x slower than average".format(round(p99_response / avg_response, 1)))
                evidence.append("P99: {:.2f}s vs Avg: {:.2f}s".format(p99_response, avg_response))
            
            if max_response > p95_response * 2:
                root_causes.append("Extreme outliers detected - Maximum response time is {}x the 95th percentile".format(round(max_response / p95_response, 1)))
                evidence.append("Max: {:.2f}s vs P95: {:.2f}s".format(max_response, p95_response))
            
            # 2. Check error rate correlation
            if error_rate > 1:
                root_causes.append("High error rate ({:.1f}%) correlates with slow responses - indicates system overload or failures".format(error_rate))
                evidence.append("Error rate: {:.1f}%".format(error_rate))
                
                # Check for specific error codes
                if response_codes:
                    error_codes = {code: count for code, count in response_codes.items() if code.startswith(('4', '5'))}
                    if error_codes:
                        most_common_error = max(error_codes.items(), key=lambda x: x[1])
                        root_causes.append("Most common error: HTTP {} ({} occurrences) - suggests specific failure pattern".format(most_common_error[0], most_common_error[1]))
            
            # 3. Analyze throughput
            if throughput < 50:
                root_causes.append("Low throughput ({:.1f} req/s) suggests resource bottleneck or connection pool exhaustion".format(throughput))
                evidence.append("Throughput: {:.1f} req/s".format(throughput))
            
            # 4. Check SLA compliance
            if sla_compliance < 80:
                root_causes.append("Only {:.1f}% requests meet 2s SLA - indicates widespread performance degradation".format(sla_compliance))
                evidence.append("SLA compliance: {:.1f}%".format(sla_compliance))
            
            # 5. Analyze slowest transactions
            if transaction_stats or request_stats:
                all_transactions = {**transaction_stats, **request_stats}
                if all_transactions:
                    slow_transactions = [(name, stats) for name, stats in all_transactions.items() 
                                       if stats.get("avg_response", 0) > avg_response * 1.5]
                    if slow_transactions:
                        slow_transactions.sort(key=lambda x: x[1].get("avg_response", 0), reverse=True)
                        top_slow = slow_transactions[0]
                        root_causes.append("Slowest transaction: '{}' ({:.2f}s avg) is {}x slower than overall average".format(
                            top_slow[0], top_slow[1].get("avg_response", 0) / 1000.0, 
                            round(top_slow[1].get("avg_response", 0) / (avg_response * 1000), 1)))
                    
                    # Check for high error rate transactions
                    error_transactions = [(name, stats) for name, stats in all_transactions.items() 
                                        if stats.get("error_rate", 0) > 5]
                    if error_transactions:
                        top_error = max(error_transactions, key=lambda x: x[1].get("error_rate", 0))
                        root_causes.append("Transaction '{}' has {:.1f}% error rate - specific endpoint issue".format(
                            top_error[0], top_error[1].get("error_rate", 0)))
            
            # Add comprehensive infrastructure-level root causes
            infrastructure_causes = JMeterAnalyzerV2._generate_infrastructure_root_causes(
                avg_response, p95_response, p99_response, max_response,
                error_rate, throughput, sla_compliance, skewness
            )
            
            # Combine data-driven and infrastructure causes
            if root_causes:
                # Have specific data-driven causes, add infrastructure analysis
                root_causes.extend(infrastructure_causes)
            else:
                # No specific causes found, use infrastructure analysis
                root_causes = infrastructure_causes
            
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
                "possible_causes": root_causes,  # DYNAMIC based on actual data
                "evidence": evidence,  # Supporting data points
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
        Generate root causes based on SYMPTOM PATTERNS matching real-world performance issues
        Returns 5-8 most relevant causes based on actual symptoms detected in the data
        """
        detected_issues = []
        
        # Calculate key indicators
        p95_avg_ratio = p95_response / avg_response if avg_response > 0 else 0
        p99_avg_ratio = p99_response / avg_response if avg_response > 0 else 0
        
        # ========== 1. DATABASE BOTTLENECKS (60-70% of real issues) ==========
        # Symptoms: Only some transactions slow, gradual increase, high tail latency
        if (p99_avg_ratio > 3 or avg_response > 1.5) and skewness > 1:
            detected_issues.append({
                "category": "🗄️ **Database Bottleneck** (Most Common - 60-70% of performance issues)",
                "diagnosis": "Application slowness caused by database queries, not application code",
                "symptoms": "Some transactions slower than others, gradual performance degradation",
                "causes": [
                    "**Slow SQL Queries**: Analyze slow query logs and identify queries taking >500ms",
                    "**Missing Indexes**: Add indexes on WHERE, JOIN, and ORDER BY columns",
                    "**Table Scans**: Optimize queries doing full table scans (EXPLAIN PLAN)",
                    "**Lock Contention**: Monitor row/table locking and deadlocks",
                    "**Connection Leaks**: Ensure connections are properly closed after use",
                    "**Large Result Sets**: Implement pagination for queries returning 1000+ rows"
                ]
            })
        
        # ========== 2. EXTERNAL DEPENDENCY FAILURES ==========
        # Key Indicator: P95 very high but avg normal (external service latency)
        if p95_avg_ratio > 4 or (p99_avg_ratio > 5 and avg_response < 2):
            detected_issues.append({
                "category": "🌐 **External Dependency Failure** (Third-party services)",
                "diagnosis": "Random slowness indicates external service latency issues",
                "symptoms": "P95 latency very high but average latency normal - classic external dependency sign",
                "causes": [
                    "**Slow Third-Party APIs**: Payment gateway, SMS, OTP, SSO, credit score services",
                    "**No Timeout Handling**: Add connection and read timeouts (5-10 seconds)",
                    "**No Circuit Breaker**: Implement circuit breaker pattern to fail fast",
                    "**Synchronous Calls**: Use async/non-blocking calls for external services",
                    "**No Retry Logic**: Add exponential backoff retry with max attempts"
                ]
            })
        
        # ========== 3. APPLICATION SERVER / THREAD POOL EXHAUSTION ==========
        # Symptoms: Throughput plateaus, response time spikes, requests queue
        if throughput < 100 and avg_response > 1.5 and error_rate < 5:
            detected_issues.append({
                "category": "⚙️ **Application Server / Thread Pool Exhaustion**",
                "diagnosis": "90% of enterprise apps fail due to thread/connection pool misconfiguration",
                "symptoms": "Throughput stops increasing, response time spikes, CPU not fully utilized",
                "causes": [
                    "**Thread Pool Exhaustion**: Increase max threads (check active vs max threads)",
                    "**Connection Pool Exhaustion**: Tune database connection pool (min: 10, max: 50-100)",
                    "**Blocking Synchronous Calls**: Convert blocking I/O to async/await patterns",
                    "**Session Locking**: Review session management and locking mechanisms",
                    "**Request Queue Size**: Increase queue size or add more worker processes"
                ]
            })
        
        # ========== 4. INFRASTRUCTURE / RESOURCE SATURATION ==========
        # Symptoms: All transactions slow, linear increase with users, system collapses under load
        if avg_response > 2 and sla_compliance < 70 and throughput < 75:
            detected_issues.append({
                "category": "💻 **Infrastructure Resource Saturation**",
                "diagnosis": "OS/VM/Container resource exhaustion rather than code inefficiency",
                "symptoms": "All transactions slow (not specific pages), system collapses under concurrency",
                "causes": [
                    "**CPU Saturation**: Monitor CPU usage (should be <70%), consider vertical scaling",
                    "**Memory Exhaustion**: Check memory usage, identify memory leaks (heap dumps)",
                    "**Disk I/O Wait**: Monitor disk I/O (iostat), use SSD instead of HDD",
                    "**Insufficient Autoscaling**: Configure autoscaling rules based on CPU/memory",
                    "**Noisy Neighbor VM**: Very common in cloud - request dedicated instances"
                ]
            })
        
        # ========== 5. CACHING PROBLEMS ==========
        # Symptoms: Performance degrades over time, DB CPU high
        if avg_response > 2 and throughput < 100:
            detected_issues.append({
                "category": "⚡ **Caching Problems** (Can reduce response time from 3s → 200ms)",
                "diagnosis": "Missing or misconfigured caching layer causing excessive database load",
                "symptoms": "Performance degrades over time, database CPU very high",
                "causes": [
                    "**Cache Disabled**: Enable Redis/Memcached for read-heavy operations",
                    "**Wrong Cache TTL**: Set appropriate TTL (15-60 minutes for static data)",
                    "**Cache Stampede**: Implement cache warming to prevent thundering herd",
                    "**CDN Not Configured**: Use CDN for static assets (images, CSS, JS)"
                ]
            })
        
        # ========== 6. MEMORY LEAKS ==========
        # Symptoms: Test starts good, degrades after 30-60 min, restart fixes
        if skewness > 1.5 and avg_response > 1.5:
            detected_issues.append({
                "category": "🔧 **Memory Leak Detection**",
                "diagnosis": "Memory steadily increases → GC frequency increases → response time increases",
                "symptoms": "System degrades after 30-60 minutes, restart fixes everything",
                "causes": [
                    "**Objects Not Released**: Review object lifecycle and ensure proper disposal",
                    "**Session Accumulation**: Clear expired sessions regularly",
                    "**Static Collections**: Avoid unbounded static collections (Map, List)",
                    "**Heap Analysis**: Take heap dumps and analyze with profiler"
                ]
            })
        
        # ========== 7. LOAD BALANCER / TRAFFIC DISTRIBUTION ==========
        # Symptoms: Some users fast, some slow, uneven distribution
        if error_rate > 2 and skewness > 2:
            detected_issues.append({
                "category": "⚖️ **Load Balancer / Traffic Distribution Issues**",
                "diagnosis": "Uneven load distribution causing inconsistent user experience",
                "symptoms": "Some users fast, some extremely slow, random failures",
                "causes": [
                    "**Sticky Session Misconfiguration**: Review session affinity settings",
                    "**Uneven Load Distribution**: Change algorithm (round-robin vs least-connections)",
                    "**Health Check Wrong**: Verify health check endpoints are accurate",
                    "**Session Replication**: Optimize session replication across nodes"
                ]
            })
        
        # ========== 8. CONFIGURATION & CAPACITY PLANNING ==========
        # Always relevant if performance is poor
        if avg_response > 1.5 or throughput < 100 or sla_compliance < 85:
            detected_issues.append({
                "category": "📊 **Configuration & Capacity Planning**",
                "diagnosis": "System configuration not tuned for expected load",
                "symptoms": "System underperforming despite adequate code quality",
                "causes": [
                    "**JVM Settings**: Tune heap size (Xms=Xmx), GC algorithm (G1GC for low latency)",
                    "**Instance Size**: Increase CPU/RAM or use compute-optimized instances",
                    "**Too Many Microservice Hops**: Reduce service-to-service calls",
                    "**Improper Autoscaling Rules**: Set thresholds: scale at 60-70% CPU/memory"
                ]
            })
        
        # ========== FORMAT OUTPUT (TOP 5-8 MOST RELEVANT) ==========
        output = []
        
        # Sort by priority (Database and External Deps usually first)
        priority_order = ["Database", "External", "Application Server", "Infrastructure", "Caching", "Memory", "Load Balancer", "Configuration"]
        detected_issues.sort(key=lambda x: next((i for i, p in enumerate(priority_order) if p in x["category"]), 99))
        
        # Take top 5-8 issues (but at least database if detected)
        selected_issues = detected_issues[:min(6, len(detected_issues))]
        
        for issue in selected_issues:
            output.append(f"\n{issue['category']}")
            output.append(f"   📋 **Diagnosis**: {issue['diagnosis']}")
            output.append(f"   🔍 **Symptoms**: {issue['symptoms']}")
            output.append(f"   🔧 **Root Causes**:")
            for cause in issue['causes']:
                output.append(f"      • {cause}")
        
        # If no specific issues detected, provide general guidance
        if not output:
            output = [
                "\n⚙️ **General Performance Optimization**",
                "   📋 **Diagnosis**: System requires standard performance tuning",
                "   🔧 **Root Causes**:",
                "      • **Database Optimization**: Review slow queries and add missing indexes",
                "      • **Connection Pooling**: Tune database and HTTP connection pools",
                "      • **Caching Strategy**: Implement Redis/Memcached for read-heavy operations",
                "      • **Thread Pool Sizing**: Increase application server thread pool",
                "      • **Resource Monitoring**: Enable APM to identify specific bottlenecks"
            ]
        
        return output
    
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
            "B": "Customers can complete journeys, but experience is frustrating. Noticeable delays and page reload attempts lead to increased bounce rates.",
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
                "executive_meaning": "Customers can complete journeys, but experience is frustrating",
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
                [(name, stats.get("avg_response", 0) / 1000.0, stats.get("p95", 0) / 1000.0) 
                 for name, stats in all_transactions.items()],
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
        
        phases.append({
            "phase": "Phase 1: Critical Fixes",
            "timeline": "Week 1-2",
            "priority": "🔴 High",
            "actions": phase1_actions,
            "target_score": min(90, round(current_score + phase1_impact, 1)),
            "expected_grade": JMeterAnalyzerV2._calculate_grade(min(90, current_score + phase1_impact))[0]
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
        
        phases.append({
            "phase": "Phase 2: Major Improvements",
            "timeline": "Week 3-4",
            "priority": "🟡 Medium",
            "actions": phase2_actions,
            "target_score": min(90, round(current_after_phase1 + phase2_impact, 1)),
            "expected_grade": JMeterAnalyzerV2._calculate_grade(min(90, current_after_phase1 + phase2_impact))[0]
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
        
        phases.append({
            "phase": "Phase 3: Excellence & Sustainability",
            "timeline": "Week 5-6",
            "priority": "🟢 Low",
            "actions": phase3_actions,
            "target_score": 90,
            "expected_grade": "A+"
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


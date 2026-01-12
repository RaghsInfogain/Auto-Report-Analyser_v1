"""
Lighthouse Performance Analyzer
Analyzes Lighthouse JSON data, grades performance, and performs AIML modeling
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Optional sklearn imports for AIML modeling
try:
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, f1_score, mean_squared_error
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("Warning: scikit-learn not available. AIML modeling will be disabled.")


class LighthouseAnalyzer:
    """Analyzer for Lighthouse JSON data with grading and AIML modeling"""
    
    @staticmethod
    def analyze(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main analysis method
        Returns comprehensive analysis with grades, scores, and AIML predictions
        """
        # Extract metrics
        metrics = LighthouseAnalyzer._extract_metrics(data)
        
        # Grade categories
        grades = LighthouseAnalyzer._grade_categories(metrics)
        
        # Calculate overall grade
        overall_grade = LighthouseAnalyzer._calculate_overall_grade(grades, metrics)
        
        # Identify issues
        issues = LighthouseAnalyzer._identify_issues(metrics, data.get("audits", {}))
        
        # Generate recommendations
        recommendations = LighthouseAnalyzer._generate_recommendations(issues)
        
        # Business impact projections
        business_impact = LighthouseAnalyzer._generate_business_impact(metrics, grades)
        
        # Feature engineering for AIML
        features = LighthouseAnalyzer._feature_engineer(metrics, data.get("audits", {}))
        
        # Perform AIML modeling
        aiml_results = LighthouseAnalyzer._perform_aiml_modeling(features, metrics, grades, overall_grade)
        
        # Extract page-level data and test overview info
        page_data = data.get("_page_data", [])
        if not page_data:
            # Single page - extract from current data
            page_url = data.get("finalUrl") or data.get("requestedUrl") or data.get("url", "Unknown Page")
            page_data = [{
                "url": page_url,
                "fcp": metrics.get("fcp", 0),
                "lcp": metrics.get("lcp", 0),
                "speed_index": metrics.get("speed_index", 0),
                "tbt": metrics.get("tbt", 0),
                "cls": metrics.get("cls", 0),
                "tti": metrics.get("tti", 0),
                "performance_score": metrics.get("performance_score", 0)
            }]
        
        # Calculate test overview stats
        total_pages = len(page_data)
        test_duration = "N/A"  # Lighthouse doesn't provide test duration directly
        avg_page_components = "N/A"  # Would need to calculate from DOM nodes
        avg_data_processed = "N/A"  # Would need to calculate from network requests
        
        # Extract test configuration from Lighthouse data
        test_config = []
        if data.get("configSettings"):
            settings = data["configSettings"]
            test_config.append(f"Device: {settings.get('emulatedFormFactor', 'Desktop')}")
            test_config.append(f"Network: {settings.get('throttling', {}).get('rttMs', 'N/A')}ms RTT")
            test_config.append(f"CPU: {settings.get('throttling', {}).get('cpuSlowdownMultiplier', 'N/A')}x slowdown")
        
        test_objectives = [
            "Measure Core Web Vitals (LCP, FID/INP, CLS)",
            "Assess loading performance (FCP, Speed Index)",
            "Evaluate interactivity (TBT, TTI)",
            "Identify performance optimization opportunities",
            "Provide actionable recommendations for improvement"
        ]
        
        return {
            "metrics": metrics,
            "grades": grades,
            "overall_grade": overall_grade,
            "issues": issues,
            "recommendations": recommendations,
            "business_impact": business_impact,
            "aiml_results": aiml_results,
            "page_data": page_data,
            "test_overview": {
                "total_pages": total_pages,
                "test_duration": test_duration,
                "avg_page_components": avg_page_components,
                "avg_data_processed": avg_data_processed,
                "test_config": test_config,
                "test_objectives": test_objectives
            },
            "report_metadata": {
                "report_date": datetime.now().strftime("%Y-%m-%d"),
                "prepared_by": "Raghvendra Kumar",
                "document_version": "1.0",
                "application": "Lighthouse Performance Test Analysis"
            }
        }
    
    @staticmethod
    def _extract_metrics(data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract key metrics from Lighthouse data"""
        audits = data.get("audits", {})
        categories = data.get("categories", {})
        performance = categories.get("performance", {})
        
        # Extract metrics (convert ms to seconds where needed)
        fcp_audit = audits.get("first-contentful-paint", {})
        lcp_audit = audits.get("largest-contentful-paint", {})
        speed_index_audit = audits.get("speed-index", {})
        tbt_audit = audits.get("total-blocking-time", {})
        cls_audit = audits.get("cumulative-layout-shift", {})
        tti_audit = audits.get("interactive", {})
        
        # Performance score (0-1 to 0-100)
        perf_score = performance.get("score", 0)
        if perf_score and perf_score <= 1:
            perf_score = perf_score * 100
        
        # Check for merged metrics
        merged_metrics = data.get("_merged_metrics", {})
        merged_p75 = data.get("_merged_metrics_p75", {})
        
        metrics = {
            "fcp": (merged_metrics.get("fcp") or fcp_audit.get("numericValue", 0)) / 1000,  # ms to seconds
            "lcp": (merged_metrics.get("lcp") or lcp_audit.get("numericValue", 0)) / 1000,  # ms to seconds
            "speed_index": (merged_metrics.get("speed_index") or speed_index_audit.get("numericValue", 0)) / 1000,  # ms to seconds
            "tbt": tbt_audit.get("numericValue", 0),  # Keep in ms
            "cls": cls_audit.get("numericValue", 0),  # Unitless
            "tti": (merged_metrics.get("tti") or tti_audit.get("numericValue", 0)) / 1000,  # ms to seconds
            "performance_score": merged_metrics.get("performance_score") or perf_score,
            "fcp_p75": (merged_p75.get("fcp") or fcp_audit.get("numericValue", 0)) / 1000 if merged_p75 else None,
            "lcp_p75": (merged_p75.get("lcp") or lcp_audit.get("numericValue", 0)) / 1000 if merged_p75 else None,
            "speed_index_p75": (merged_p75.get("speed_index") or speed_index_audit.get("numericValue", 0)) / 1000 if merged_p75 else None,
            "tbt_p75": merged_p75.get("tbt") if merged_p75 else None,
            "cls_p75": merged_p75.get("cls") if merged_p75 else None,
            "tti_p75": (merged_p75.get("tti") or tti_audit.get("numericValue", 0)) / 1000 if merged_p75 else None,
        }
        
        return metrics
    
    @staticmethod
    def _grade_category(metric_value: float, metric_type: str) -> Dict[str, Any]:
        """
        Grade a category based on metric value
        metric_type: 'lcp', 'tbt', 'cls'
        """
        if metric_type == "lcp":
            if metric_value <= 2.5:
                return {"grade": "A", "score": 100}
            elif metric_value <= 4.0:
                return {"grade": "B", "score": 80}
            elif metric_value <= 6.0:
                return {"grade": "C", "score": 60}
            elif metric_value <= 8.0:
                return {"grade": "D", "score": 40}
            elif metric_value <= 12.0:
                return {"grade": "E", "score": 20}
            else:
                return {"grade": "F", "score": 0}
        
        elif metric_type == "tbt":
            if metric_value <= 200:
                return {"grade": "A", "score": 100}
            elif metric_value <= 400:
                return {"grade": "B", "score": 80}
            elif metric_value <= 600:
                return {"grade": "C", "score": 60}
            elif metric_value <= 1000:
                return {"grade": "D", "score": 40}
            elif metric_value <= 2000:
                return {"grade": "E", "score": 20}
            else:
                return {"grade": "F", "score": 0}
        
        elif metric_type == "cls":
            if metric_value <= 0.10:
                return {"grade": "A", "score": 100}
            elif metric_value <= 0.15:
                return {"grade": "B", "score": 80}
            elif metric_value <= 0.25:
                return {"grade": "C", "score": 60}
            elif metric_value <= 0.35:
                return {"grade": "D", "score": 40}
            elif metric_value <= 0.50:
                return {"grade": "E", "score": 20}
            else:
                return {"grade": "F", "score": 0}
        
        return {"grade": "N/A", "score": 0}
    
    @staticmethod
    def _grade_categories(metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Grade all three categories"""
        loading = LighthouseAnalyzer._grade_category(metrics["lcp"], "lcp")
        interactivity = LighthouseAnalyzer._grade_category(metrics["tbt"], "tbt")
        visual_stability = LighthouseAnalyzer._grade_category(metrics["cls"], "cls")
        
        return {
            "loading": {
                **loading,
                "metric": metrics["lcp"],
                "metric_name": "LCP"
            },
            "interactivity": {
                **interactivity,
                "metric": metrics["tbt"],
                "metric_name": "TBT"
            },
            "visual_stability": {
                **visual_stability,
                "metric": metrics["cls"],
                "metric_name": "CLS"
            }
        }
    
    @staticmethod
    def _calculate_overall_grade(grades: Dict[str, Any], metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate weighted overall page grade"""
        # Linear scaling for sub-scores
        lcp = metrics["lcp"]
        loading_sub = max(0, min(100, 100 - ((lcp - 2.5) / (12.0 - 2.5)) * 100)) if lcp <= 12.0 else 0
        
        tbt = metrics["tbt"]
        interactivity_sub = max(0, min(100, 100 - ((tbt - 200) / (2000 - 200)) * 100)) if tbt <= 2000 else 0
        
        cls = metrics["cls"]
        visual_sub = max(0, min(100, 100 - ((cls - 0.10) / (0.50 - 0.10)) * 100)) if cls <= 0.50 else 0
        
        # Weighted composite
        overall_score = 0.50 * loading_sub + 0.30 * interactivity_sub + 0.20 * visual_sub
        
        # Letter grade
        if overall_score >= 90:
            letter_grade = "A"
        elif overall_score >= 80:
            letter_grade = "B"
        elif overall_score >= 70:
            letter_grade = "C"
        elif overall_score >= 60:
            letter_grade = "D"
        elif overall_score >= 40:
            letter_grade = "E"
        else:
            letter_grade = "F"
        
        return {
            "score": round(overall_score, 1),
            "letter_grade": letter_grade,
            "sub_scores": {
                "loading": round(loading_sub, 1),
                "interactivity": round(interactivity_sub, 1),
                "visual_stability": round(visual_sub, 1)
            },
            "category_grades": {
                "loading": grades["loading"]["grade"],
                "interactivity": grades["interactivity"]["grade"],
                "visual_stability": grades["visual_stability"]["grade"]
            }
        }
    
    @staticmethod
    def _get_metric_status(metric_value: float, metric_name: str) -> Dict[str, Any]:
        """Get status and severity for a metric based on industry standards"""
        standards = {
            "fcp": {"good": 1.8, "needs_improvement": 3.0},
            "lcp": {"good": 2.5, "needs_improvement": 4.0},
            "speed_index": {"good": 3.4, "needs_improvement": 5.8},
            "tbt": {"good": 200, "needs_improvement": 600},
            "cls": {"good": 0.10, "needs_improvement": 0.25},
            "tti": {"good": 3.8, "needs_improvement": 7.3}
        }
        
        # Convert TBT from ms to seconds for comparison if needed
        if metric_name == "tbt":
            metric_value_ms = metric_value
        else:
            metric_value_ms = metric_value * 1000 if metric_value < 10 else metric_value
        
        std = standards.get(metric_name.lower(), {})
        good_threshold = std.get("good", 0)
        needs_improvement_threshold = std.get("needs_improvement", 0)
        
        # Special handling for CLS (unitless)
        if metric_name.lower() == "cls":
            if metric_value <= good_threshold:
                return {"status": "✅ Good", "severity": "Low"}
            elif metric_value <= needs_improvement_threshold:
                return {"status": "⚠️ Needs Improvement", "severity": "Medium"}
            elif metric_value > 0.50:
                return {"status": "❌ Critical", "severity": "Critical"}
            else:
                return {"status": "❌ Poor", "severity": "High"}
        
        # For time-based metrics
        if metric_name.lower() == "tbt":
            compare_value = metric_value_ms
        else:
            compare_value = metric_value  # Already in seconds
        
        if compare_value <= good_threshold:
            return {"status": "✅ Good", "severity": "Low"}
        elif compare_value <= needs_improvement_threshold:
            return {"status": "⚠️ Needs Improvement", "severity": "Medium"}
        else:
            # Check for critical thresholds
            if metric_name.lower() == "lcp" and compare_value > 12.0:
                return {"status": "❌ Critical", "severity": "Critical"}
            elif metric_name.lower() == "tbt" and metric_value_ms > 2000:
                return {"status": "❌ Critical", "severity": "Critical"}
            else:
                return {"status": "❌ Poor", "severity": "High"}
    
    @staticmethod
    def _identify_issues(metrics: Dict[str, Any], audits: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify critical issues based on thresholds"""
        issues = []
        
        # Excessive Main Thread Blocking
        if metrics["tbt"] > 600:
            severity = "Critical" if metrics["tbt"] > 2000 else "High"
            issues.append({
                "issue": "Excessive Main Thread Blocking",
                "example": f"Total Blocking Time is {metrics['tbt']:.0f}ms",
                "impact": "Blocks user interactions, causing poor responsiveness",
                "recommendation": "Optimize JavaScript execution, use code splitting, defer non-critical scripts, implement Web Workers for heavy computations",
                "business_benefit": "Improve user engagement and reduce bounce rate by 15-25%"
            })
        
        # Extremely Slow LCP
        if metrics["lcp"] > 4.0:
            severity = "Critical" if metrics["lcp"] > 12.0 else "High"
            issues.append({
                "issue": "Extremely Slow Largest Contentful Paint",
                "example": f"LCP is {metrics['lcp']:.1f}s (target: <2.5s)",
                "impact": "Users perceive slow page loading, leading to abandonment",
                "recommendation": "Optimize images, preload critical resources, improve server response time, use CDN, implement resource hints",
                "business_benefit": "Reduce bounce rate by 20-30% and improve conversion rate by 10-15%"
            })
        
        # Poor Speed Index
        if metrics["speed_index"] > 5.8:
            severity = "Critical" if metrics["speed_index"] > 12.0 else "High"
            issues.append({
                "issue": "Poor Speed Index",
                "example": f"Speed Index is {metrics['speed_index']:.1f}s (target: <3.4s)",
                "impact": "Visual content loads slowly, poor perceived performance",
                "recommendation": "Optimize above-the-fold content, reduce render-blocking resources, improve critical rendering path, use lazy loading",
                "business_benefit": "Improve user satisfaction and reduce abandonment by 15-20%"
            })
        
        # Server Response Time
        ttfb_audit = audits.get("server-response-time", {})
        if ttfb_audit.get("numericValue", 0) > 500:
            issues.append({
                "issue": "Slow Server Response Time",
                "example": f"TTFB is {ttfb_audit.get('numericValue', 0):.0f}ms (target: <500ms)",
                "impact": "Delays initial page load, affects all subsequent metrics",
                "recommendation": "Optimize server performance, use CDN, enable HTTP/2 or HTTP/3, implement caching, reduce server processing time",
                "business_benefit": "Improve initial load perception and reduce time-to-interactive by 20-30%"
            })
        
        # Third-Party Script Impact
        third_party_audit = audits.get("third-party-summary", {})
        if third_party_audit.get("details") and third_party_audit.get("details", {}).get("items"):
            total_time = sum(item.get("mainThreadTime", 0) for item in third_party_audit["details"]["items"])
            if total_time > 1000:  # More than 1 second
                issues.append({
                    "issue": "High Third-Party Script Impact",
                    "example": f"Third-party scripts consume {total_time:.0f}ms of main thread time",
                    "impact": "Third-party scripts block main thread, delaying interactivity",
                    "recommendation": "Defer third-party scripts, load asynchronously, use iframe isolation, implement resource prioritization, audit and remove unnecessary scripts",
                    "business_benefit": "Improve interactivity and reduce TBT by 30-40%"
                })
        
        # Network Resource Inefficiencies
        failing_audits = []
        if audits.get("unminified-css", {}).get("score", 1) < 1:
            failing_audits.append("Unminified CSS")
        if audits.get("unminified-javascript", {}).get("score", 1) < 1:
            failing_audits.append("Unminified JavaScript")
        if audits.get("uses-text-compression", {}).get("score", 1) < 1:
            failing_audits.append("Missing Text Compression")
        if audits.get("uses-long-cache-ttl", {}).get("score", 1) < 1:
            failing_audits.append("Suboptimal Cache TTL")
        
        if failing_audits:
            issues.append({
                "issue": "Network Resource Inefficiencies",
                "example": f"Failing audits: {', '.join(failing_audits)}",
                "impact": "Larger file sizes increase load time and bandwidth costs",
                "recommendation": "Minify CSS/JS, enable gzip/brotli compression, set appropriate cache headers, optimize asset delivery",
                "business_benefit": "Reduce bandwidth costs by 30-50% and improve load time by 15-25%"
            })
        
        return issues
    
    @staticmethod
    def _generate_recommendations(issues: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate phased optimization roadmap"""
        phases = {
            "phase_1": {
                "name": "Phase 1 (Week 1-2)",
                "tasks": [],
                "expected_impact": "15-25% improvement in LCP and TBT"
            },
            "phase_2": {
                "name": "Phase 2 (Week 3-6)",
                "tasks": [],
                "expected_impact": "20-30% improvement in overall performance score"
            },
            "phase_3": {
                "name": "Phase 3 (Week 7-12)",
                "tasks": [],
                "expected_impact": "30-40% improvement in all metrics, achieve grade A/B"
            }
        }
        
        # Categorize issues into phases
        for issue in issues:
            issue_name = issue["issue"].lower()
            if "server" in issue_name or "ttfb" in issue_name or "compression" in issue_name:
                phases["phase_1"]["tasks"].append({
                    "task": issue["recommendation"].split(",")[0].strip(),
                    "effort": "Low-Medium",
                    "expected_impact": "Immediate improvement in initial load",
                    "owner": "DevOps/Backend Team"
                })
            elif "third-party" in issue_name or "blocking" in issue_name:
                phases["phase_2"]["tasks"].append({
                    "task": issue["recommendation"].split(",")[0].strip(),
                    "effort": "Medium",
                    "expected_impact": "Improve interactivity metrics",
                    "owner": "Frontend Team"
                })
            else:
                phases["phase_3"]["tasks"].append({
                    "task": issue["recommendation"].split(",")[0].strip(),
                    "effort": "Medium-High",
                    "expected_impact": "Long-term optimization",
                    "owner": "Performance Team"
                })
        
        # Add default tasks if no issues
        if not any(phase["tasks"] for phase in phases.values()):
            phases["phase_1"]["tasks"] = [
                {"task": "Enable text compression (gzip/brotli)", "effort": "Low", "expected_impact": "Reduce file sizes by 30-50%", "owner": "DevOps"},
                {"task": "Optimize server response time", "effort": "Medium", "expected_impact": "Improve TTFB by 20-30%", "owner": "Backend Team"}
            ]
            phases["phase_2"]["tasks"] = [
                {"task": "Defer non-critical JavaScript", "effort": "Medium", "expected_impact": "Reduce TBT by 25-35%", "owner": "Frontend Team"},
                {"task": "Optimize images and implement lazy loading", "effort": "Medium", "expected_impact": "Improve LCP by 20-30%", "owner": "Frontend Team"}
            ]
            phases["phase_3"]["tasks"] = [
                {"task": "Implement code splitting and tree shaking", "effort": "High", "expected_impact": "Reduce bundle size by 30-40%", "owner": "Frontend Team"},
                {"task": "Set up performance monitoring and budgets", "effort": "Medium", "expected_impact": "Prevent regressions", "owner": "Performance Team"}
            ]
        
        return phases
    
    @staticmethod
    def _generate_business_impact(metrics: Dict[str, Any], grades: Dict[str, Any]) -> Dict[str, Any]:
        """Generate business impact projections"""
        # Estimate bounce rate based on LCP (industry data: LCP > 4s = ~30% bounce)
        lcp = metrics["lcp"]
        if lcp <= 2.5:
            estimated_bounce = 10
            conversion_lift = 0
        elif lcp <= 4.0:
            estimated_bounce = 20
            conversion_lift = 5
        elif lcp <= 6.0:
            estimated_bounce = 30
            conversion_lift = 10
        else:
            estimated_bounce = 45
            conversion_lift = 20
        
        # Estimate session duration based on TBT
        tbt = metrics["tbt"]
        if tbt <= 200:
            session_duration = 180  # seconds
        elif tbt <= 600:
            session_duration = 120
        else:
            session_duration = 60
        
        # Estimate page views per session
        page_views = max(1, int(session_duration / 30))
        
        return {
            "revenue_impact": {
                "bounce_rate": estimated_bounce,
                "conversion_rate_lift": conversion_lift,
                "avg_session_duration": session_duration,
                "page_views_per_session": page_views,
                "revenue_impact": f"{conversion_lift}% potential increase"
            },
            "seo_impact": {
                "core_web_vitals_pass": grades["loading"]["grade"] in ["A", "B"] and grades["interactivity"]["grade"] in ["A", "B"] and grades["visual_stability"]["grade"] in ["A", "B"],
                "ranking_factor": "Positive" if metrics["performance_score"] > 70 else "Negative",
                "organic_traffic_impact": "10-15% increase" if metrics["performance_score"] > 80 else "5-10% decrease"
            },
            "cost_benefit": {
                "total_investment": "$5,000 - $15,000",
                "bandwidth_savings": "30-50% reduction",
                "roi": "200-400% over 12 months",
                "payback_period": "3-6 months"
            }
        }
    
    @staticmethod
    def _feature_engineer(metrics: Dict[str, Any], audits: Dict[str, Any]) -> Dict[str, Any]:
        """Create features for AIML modeling"""
        features = {
            # Raw metrics
            "lcp": metrics["lcp"],
            "fcp": metrics["fcp"],
            "speed_index": metrics["speed_index"],
            "tbt": metrics["tbt"],
            "cls": metrics["cls"],
            "tti": metrics["tti"],
            "performance_score": metrics["performance_score"],
            
            # Ratios
            "lcp_fcp_ratio": metrics["lcp"] / metrics["fcp"] if metrics["fcp"] > 0 else 0,
            "tbt_tti_ratio": metrics["tbt"] / (metrics["tti"] * 1000) if metrics["tti"] > 0 else 0,
            "speed_index_lcp_ratio": metrics["speed_index"] / metrics["lcp"] if metrics["lcp"] > 0 else 0,
            
            # Flags
            "third_party_heavy": 1 if audits.get("third-party-summary", {}).get("score", 1) < 0.5 else 0,
            "compression_missing": 1 if audits.get("uses-text-compression", {}).get("score", 1) < 1 else 0,
            "cache_suboptimal": 1 if audits.get("uses-long-cache-ttl", {}).get("score", 1) < 1 else 0,
        }
        
        # Log transforms
        features["log_lcp"] = np.log1p(metrics["lcp"])
        features["log_tbt"] = np.log1p(metrics["tbt"])
        features["log_tti"] = np.log1p(metrics["tti"])
        
        return features
    
    @staticmethod
    def _perform_aiml_modeling(
        features: Dict[str, Any],
        metrics: Dict[str, Any],
        grades: Dict[str, Any],
        overall_grade: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform AIML modeling with synthetic data"""
        if not SKLEARN_AVAILABLE:
            return {
                "data_sources": "AIML modeling unavailable - scikit-learn not installed",
                "features_used": list(features.keys()),
                "feature_engineering": "Raw metrics, ratios, flags, log transforms",
                "models": {},
                "predictions": {},
                "comparison": {
                    "weighted_formula_score": overall_grade.get("score", 0),
                    "nn_predicted_score": "N/A",
                    "difference": "N/A"
                },
                "assumptions": [
                    "scikit-learn package is required for AIML modeling",
                    "Install with: pip install scikit-learn"
                ]
            }
        
        # Generate synthetic training data
        synthetic_data = LighthouseAnalyzer._generate_synthetic_data(1000)
        
        # Prepare features and targets
        feature_cols = ["lcp", "fcp", "speed_index", "tbt", "cls", "tti", "performance_score",
                       "lcp_fcp_ratio", "tbt_tti_ratio", "speed_index_lcp_ratio",
                       "third_party_heavy", "compression_missing", "cache_suboptimal",
                       "log_lcp", "log_tbt", "log_tti"]
        
        X_synthetic = synthetic_data[feature_cols].values
        y_grade_synthetic = synthetic_data["grade_numeric"].values
        y_score_synthetic = synthetic_data["overall_score"].values
        y_bounce_synthetic = synthetic_data["bounce_rate"].values
        y_conversion_synthetic = synthetic_data["conversion_rate"].values
        
        # Split data
        X_train, X_val, y_grade_train, y_grade_val = train_test_split(
            X_synthetic, y_grade_synthetic, test_size=0.2, random_state=42
        )
        _, _, y_score_train, y_score_val = train_test_split(
            X_synthetic, y_score_synthetic, test_size=0.2, random_state=42
        )
        _, _, y_bounce_train, y_bounce_val = train_test_split(
            X_synthetic, y_bounce_synthetic, test_size=0.2, random_state=42
        )
        _, _, y_conversion_train, y_conversion_val = train_test_split(
            X_synthetic, y_conversion_synthetic, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        # 1. Classification: Predict grade
        lr_classifier = LogisticRegression(max_iter=1000, random_state=42)
        lr_classifier.fit(X_train_scaled, y_grade_train)
        y_grade_pred = lr_classifier.predict(X_val_scaled)
        grade_accuracy = accuracy_score(y_grade_val, y_grade_pred)
        grade_f1 = f1_score(y_grade_val, y_grade_pred, average='weighted')
        
        rf_classifier = RandomForestClassifier(n_estimators=100, random_state=42)
        rf_classifier.fit(X_train, y_grade_train)
        y_grade_pred_rf = rf_classifier.predict(X_val)
        grade_accuracy_rf = accuracy_score(y_grade_val, y_grade_pred_rf)
        grade_f1_rf = f1_score(y_grade_val, y_grade_pred_rf, average='weighted')
        
        # 2. Regression: Predict overall score
        ridge_regressor = Ridge(alpha=1.0, random_state=42)
        ridge_regressor.fit(X_train_scaled, y_score_train)
        y_score_pred = ridge_regressor.predict(X_val_scaled)
        score_rmse = np.sqrt(mean_squared_error(y_score_val, y_score_pred))
        
        gb_regressor = GradientBoostingRegressor(n_estimators=100, random_state=42)
        gb_regressor.fit(X_train, y_score_train)
        y_score_pred_gb = gb_regressor.predict(X_val)
        score_rmse_gb = np.sqrt(mean_squared_error(y_score_val, y_score_pred_gb))
        
        # 3. Neural Network: Predict overall score
        from sklearn.neural_network import MLPRegressor
        nn_regressor = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500, random_state=42)
        nn_regressor.fit(X_train_scaled, y_score_train)
        y_score_pred_nn = nn_regressor.predict(X_val_scaled)
        score_rmse_nn = np.sqrt(mean_squared_error(y_score_val, y_score_pred_nn))
        
        # 4. Business metrics regression
        bounce_regressor = Ridge(alpha=1.0, random_state=42)
        bounce_regressor.fit(X_train_scaled, y_bounce_train)
        y_bounce_pred = bounce_regressor.predict(X_val_scaled)
        bounce_rmse = np.sqrt(mean_squared_error(y_bounce_val, y_bounce_pred))
        
        conversion_regressor = Ridge(alpha=1.0, random_state=42)
        conversion_regressor.fit(X_train_scaled, y_conversion_train)
        y_conversion_pred = conversion_regressor.predict(X_val_scaled)
        conversion_rmse = np.sqrt(mean_squared_error(y_conversion_val, y_conversion_pred))
        
        # Predict for current data
        current_features = np.array([[features.get(col, 0) for col in feature_cols]])
        current_features_scaled = scaler.transform(current_features)
        
        predicted_grade = lr_classifier.predict(current_features_scaled)[0]
        predicted_score_nn = nn_regressor.predict(current_features_scaled)[0]
        predicted_bounce = bounce_regressor.predict(current_features_scaled)[0]
        predicted_conversion = conversion_regressor.predict(current_features_scaled)[0]
        
        return {
            "data_sources": "Synthetic data generated from Lighthouse thresholds",
            "features_used": feature_cols,
            "feature_engineering": "Raw metrics, ratios, flags, log transforms",
            "models": {
                "classification": {
                    "logistic_regression": {
                        "accuracy": round(grade_accuracy, 3),
                        "f1_score": round(grade_f1, 3)
                    },
                    "random_forest": {
                        "accuracy": round(grade_accuracy_rf, 3),
                        "f1_score": round(grade_f1_rf, 3)
                    }
                },
                "regression": {
                    "ridge": {
                        "rmse": round(score_rmse, 2)
                    },
                    "gradient_boosting": {
                        "rmse": round(score_rmse_gb, 2)
                    }
                },
                "neural_network": {
                    "architecture": "2 hidden layers (64, 32 neurons)",
                    "rmse": round(score_rmse_nn, 2)
                },
                "business_metrics": {
                    "bounce_rate_rmse": round(bounce_rmse, 2),
                    "conversion_rate_rmse": round(conversion_rmse, 2)
                }
            },
            "predictions": {
                "predicted_grade": ["F", "E", "D", "C", "B", "A"][int(predicted_grade)],
                "predicted_score_nn": round(predicted_score_nn, 1),
                "predicted_bounce_rate": round(predicted_bounce, 1),
                "predicted_conversion_lift": round(predicted_conversion, 1)
            },
            "comparison": {
                "weighted_formula_score": overall_grade["score"],
                "nn_predicted_score": round(predicted_score_nn, 1),
                "difference": round(abs(overall_grade["score"] - predicted_score_nn), 1)
            },
            "assumptions": [
                "Synthetic data generated based on Lighthouse thresholds and industry benchmarks",
                "Models trained on 1000 synthetic samples with 80/20 train/validation split",
                "Feature engineering includes raw metrics, ratios, flags, and log transforms",
                "Business impact predictions are estimates based on industry research"
            ]
        }
    
    @staticmethod
    def _generate_synthetic_data(num_samples: int = 1000) -> pd.DataFrame:
        """Generate synthetic training data based on Lighthouse thresholds"""
        np.random.seed(42)
        
        data = []
        for _ in range(num_samples):
            # Generate realistic metrics
            lcp = np.random.lognormal(mean=1.5, sigma=0.8)
            fcp = lcp * np.random.uniform(0.3, 0.7)
            speed_index = lcp * np.random.uniform(0.8, 1.5)
            tbt = np.random.lognormal(mean=4.5, sigma=1.0) * 100  # ms
            cls = np.random.exponential(0.1)
            tti = lcp * np.random.uniform(1.2, 2.0)
            perf_score = np.random.uniform(30, 100)
            
            # Calculate ratios
            lcp_fcp_ratio = lcp / fcp if fcp > 0 else 0
            tbt_tti_ratio = tbt / (tti * 1000) if tti > 0 else 0
            speed_index_lcp_ratio = speed_index / lcp if lcp > 0 else 0
            
            # Flags
            third_party_heavy = np.random.choice([0, 1], p=[0.7, 0.3])
            compression_missing = np.random.choice([0, 1], p=[0.8, 0.2])
            cache_suboptimal = np.random.choice([0, 1], p=[0.7, 0.3])
            
            # Calculate grade (0=F, 1=E, 2=D, 3=C, 4=B, 5=A)
            if lcp <= 2.5 and tbt <= 200 and cls <= 0.10:
                grade_numeric = 5
            elif lcp <= 4.0 and tbt <= 400 and cls <= 0.15:
                grade_numeric = 4
            elif lcp <= 6.0 and tbt <= 600 and cls <= 0.25:
                grade_numeric = 3
            elif lcp <= 8.0 and tbt <= 1000 and cls <= 0.35:
                grade_numeric = 2
            elif lcp <= 12.0 and tbt <= 2000 and cls <= 0.50:
                grade_numeric = 1
            else:
                grade_numeric = 0
            
            # Calculate overall score
            loading_sub = max(0, min(100, 100 - ((lcp - 2.5) / (12.0 - 2.5)) * 100)) if lcp <= 12.0 else 0
            interactivity_sub = max(0, min(100, 100 - ((tbt - 200) / (2000 - 200)) * 100)) if tbt <= 2000 else 0
            visual_sub = max(0, min(100, 100 - ((cls - 0.10) / (0.50 - 0.10)) * 100)) if cls <= 0.50 else 0
            overall_score = 0.50 * loading_sub + 0.30 * interactivity_sub + 0.20 * visual_sub
            
            # Business metrics (synthetic)
            bounce_rate = 10 + (lcp - 2.5) * 3 if lcp > 2.5 else 10
            conversion_rate = 5 - (lcp - 2.5) * 0.5 if lcp > 2.5 else 5
            
            data.append({
                "lcp": lcp,
                "fcp": fcp,
                "speed_index": speed_index,
                "tbt": tbt,
                "cls": cls,
                "tti": tti,
                "performance_score": perf_score,
                "lcp_fcp_ratio": lcp_fcp_ratio,
                "tbt_tti_ratio": tbt_tti_ratio,
                "speed_index_lcp_ratio": speed_index_lcp_ratio,
                "third_party_heavy": third_party_heavy,
                "compression_missing": compression_missing,
                "cache_suboptimal": cache_suboptimal,
                "log_lcp": np.log1p(lcp),
                "log_tbt": np.log1p(tbt),
                "log_tti": np.log1p(tti),
                "grade_numeric": grade_numeric,
                "overall_score": overall_score,
                "bounce_rate": bounce_rate,
                "conversion_rate": conversion_rate
            })
        
        return pd.DataFrame(data)

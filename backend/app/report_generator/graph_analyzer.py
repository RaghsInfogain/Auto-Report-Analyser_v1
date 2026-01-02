"""
Advanced Graph Analysis Model for Performance Test Results

This module provides sophisticated analysis of time-series performance data
to identify patterns, disturbances, and system behavior characteristics.
"""

from typing import Dict, Any, List, Tuple, Optional
import numpy as np
from collections import deque


class GraphAnalyzer:
    """Advanced analyzer for performance graph data"""
    
    @staticmethod
    def analyze_graph_patterns(time_series_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Comprehensive analysis of graph patterns including:
        - Constant-load test detection
        - Performance disturbance identification
        - Backend bottleneck detection
        - System stability assessment
        - Capacity limit analysis
        """
        if not time_series_data or len(time_series_data) < 10:
            return {
                "analysis": "Insufficient data points for comprehensive analysis.",
                "test_type": "Unknown",
                "disturbances": [],
                "stability": "Unknown",
                "capacity_assessment": "Unknown"
            }
        
        # Extract time-series arrays
        times = np.array([d['time'] for d in time_series_data])
        response_times = np.array([d['avg_response_time'] for d in time_series_data])
        vusers = np.array([d['vusers'] for d in time_series_data])
        throughput = np.array([d['throughput'] for d in time_series_data])
        pass_counts = np.array([d.get('pass_count', 0) for d in time_series_data])
        fail_counts = np.array([d.get('fail_count', 0) for d in time_series_data])
        
        # 1. Detect test type (constant-load vs ramp-up vs spike)
        test_type = GraphAnalyzer._detect_test_type(vusers, times)
        
        # 2. Identify steady performance periods
        steady_periods = GraphAnalyzer._identify_steady_periods(
            response_times, throughput, vusers, times
        )
        
        # 3. Detect performance disturbances
        disturbances = GraphAnalyzer._detect_disturbances(
            response_times, throughput, vusers, times
        )
        
        # 4. Analyze disturbance patterns (backend bottlenecks vs load issues)
        bottleneck_analysis = GraphAnalyzer._analyze_bottleneck_patterns(
            disturbances, response_times, throughput, vusers, times
        )
        
        # 5. Assess system stability
        stability_assessment = GraphAnalyzer._assess_stability(
            response_times, throughput, vusers, steady_periods, disturbances
        )
        
        # 6. Capacity limit assessment
        capacity_assessment = GraphAnalyzer._assess_capacity_limits(
            response_times, throughput, vusers, disturbances
        )
        
        # 7. Response time distribution analysis (AI/ML Feature Engineering)
        distribution_analysis = GraphAnalyzer._analyze_response_time_distribution(response_times)
        
        # 8. Generate comprehensive analysis text
        analysis_text = GraphAnalyzer._generate_analysis_text(
            test_type, steady_periods, disturbances, bottleneck_analysis,
            stability_assessment, capacity_assessment,
            response_times, throughput, vusers, times
        )
        
        return {
            "analysis": analysis_text,
            "test_type": test_type,
            "steady_periods": steady_periods,
            "disturbances": disturbances,
            "bottleneck_analysis": bottleneck_analysis,
            "stability": stability_assessment,
            "capacity_assessment": capacity_assessment,
            "distribution_analysis": distribution_analysis,
            "statistics": {
                "avg_response_time": float(np.mean(response_times)),
                "avg_throughput": float(np.mean(throughput)),
                "avg_vusers": float(np.mean(vusers)),
                "test_duration_seconds": float(times[-1] - times[0])
            }
        }
    
    @staticmethod
    def _detect_test_type(vusers: np.ndarray, times: np.ndarray) -> str:
        """Detect the type of load test based on VUsers pattern"""
        if len(vusers) < 5:
            return "Unknown"
        
        # Calculate coefficient of variation (CV) for VUsers
        vuser_mean = np.mean(vusers)
        vuser_std = np.std(vusers)
        cv = vuser_std / vuser_mean if vuser_mean > 0 else 0
        
        # Check if VUsers are relatively constant (CV < 0.15)
        if cv < 0.15:
            return "constant_load"
        
        # Check if VUsers are increasing
        if vusers[-1] > vusers[0] * 1.5:
            return "ramp_up"
        
        # Check if VUsers have spikes
        vuser_max = np.max(vusers)
        vuser_median = np.median(vusers)
        if vuser_max > vuser_median * 2:
            return "spike_test"
        
        return "variable_load"
    
    @staticmethod
    def _identify_steady_periods(
        response_times: np.ndarray,
        throughput: np.ndarray,
        vusers: np.ndarray,
        times: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Identify periods of steady performance"""
        steady_periods = []
        
        if len(response_times) < 10:
            return steady_periods
        
        # Use rolling window to detect stability
        window_size = min(10, len(response_times) // 5)
        if window_size < 3:
            return steady_periods
        
        i = 0
        while i < len(response_times) - window_size:
            window_rt = response_times[i:i+window_size]
            window_tp = throughput[i:i+window_size]
            window_vu = vusers[i:i+window_size]
            
            # Calculate coefficients of variation
            rt_cv = np.std(window_rt) / np.mean(window_rt) if np.mean(window_rt) > 0 else 0
            tp_cv = np.std(window_tp) / np.mean(window_tp) if np.mean(window_tp) > 0 else 0
            vu_cv = np.std(window_vu) / np.mean(window_vu) if np.mean(window_vu) > 0 else 0
            
            # Consider steady if all CVs are low
            if rt_cv < 0.2 and tp_cv < 0.2 and vu_cv < 0.15:
                start_idx = i
                # Extend the period forward
                while i < len(response_times) - window_size:
                    next_window_rt = response_times[i+1:i+window_size+1]
                    next_window_tp = throughput[i+1:i+window_size+1]
                    next_window_vu = vusers[i+1:i+window_size+1]
                    
                    next_rt_cv = np.std(next_window_rt) / np.mean(next_window_rt) if np.mean(next_window_rt) > 0 else 0
                    next_tp_cv = np.std(next_window_tp) / np.mean(next_window_tp) if np.mean(next_window_tp) > 0 else 0
                    next_vu_cv = np.std(next_window_vu) / np.mean(next_window_vu) if np.mean(next_window_vu) > 0 else 0
                    
                    if next_rt_cv < 0.2 and next_tp_cv < 0.2 and next_vu_cv < 0.15:
                        i += 1
                    else:
                        break
                
                end_idx = i + window_size
                if end_idx - start_idx >= window_size:
                    steady_periods.append({
                        "start_time": float(times[start_idx]),
                        "end_time": float(times[min(end_idx, len(times)-1)]),
                        "duration": float(times[min(end_idx, len(times)-1)] - times[start_idx]),
                        "avg_response_time": float(np.mean(response_times[start_idx:end_idx])),
                        "avg_throughput": float(np.mean(throughput[start_idx:end_idx])),
                        "avg_vusers": float(np.mean(vusers[start_idx:end_idx]))
                    })
            else:
                i += 1
        
        return steady_periods
    
    @staticmethod
    def _detect_disturbances(
        response_times: np.ndarray,
        throughput: np.ndarray,
        vusers: np.ndarray,
        times: np.ndarray
    ) -> List[Dict[str, Any]]:
        """Detect performance disturbances (throughput drops + response time spikes)"""
        disturbances = []
        
        if len(response_times) < 5:
            return disturbances
        
        # Calculate baseline metrics (median of first 20% and last 20% of data)
        baseline_start = max(1, len(response_times) // 5)
        baseline_end = len(response_times) - max(1, len(response_times) // 5)
        
        baseline_rt = np.median(response_times[baseline_start:baseline_end])
        baseline_tp = np.median(throughput[baseline_start:baseline_end])
        
        # Use rolling window to detect anomalies
        window_size = 3
        for i in range(window_size, len(response_times) - window_size):
            # Check for response time spike
            current_rt = np.mean(response_times[i-window_size:i+window_size])
            rt_spike = current_rt > baseline_rt * 1.3  # 30% increase
            
            # Check for throughput drop
            current_tp = np.mean(throughput[i-window_size:i+window_size])
            tp_drop = current_tp < baseline_tp * 0.85  # 15% decrease
            
            # Check if VUsers remain relatively constant (not a load issue)
            current_vu = np.mean(vusers[i-window_size:i+window_size])
            baseline_vu = np.median(vusers[baseline_start:baseline_end])
            vu_stable = abs(current_vu - baseline_vu) / baseline_vu < 0.2 if baseline_vu > 0 else True
            
            # Disturbance detected if: RT spike + TP drop + stable VUsers
            if rt_spike and tp_drop and vu_stable:
                # Check if this is part of an existing disturbance
                is_new = True
                for dist in disturbances:
                    if abs(times[i] - dist['peak_time']) < 300:  # Within 5 minutes
                        is_new = False
                        # Update if this is a more severe disturbance
                        if current_rt > dist['peak_response_time']:
                            dist['peak_time'] = float(times[i])
                            dist['peak_response_time'] = float(current_rt)
                            dist['min_throughput'] = min(dist['min_throughput'], float(current_tp))
                        break
                
                if is_new:
                    # Find the extent of the disturbance
                    start_idx = i
                    end_idx = i
                    
                    # Look backward for start
                    for j in range(i, max(0, i-30), -1):
                        if response_times[j] <= baseline_rt * 1.1 and throughput[j] >= baseline_tp * 0.9:
                            start_idx = j
                            break
                    
                    # Look forward for end
                    for j in range(i, min(len(response_times), i+30)):
                        if response_times[j] <= baseline_rt * 1.1 and throughput[j] >= baseline_tp * 0.9:
                            end_idx = j
                            break
                    
                    disturbances.append({
                        "start_time": float(times[start_idx]),
                        "peak_time": float(times[i]),
                        "end_time": float(times[end_idx]),
                        "duration": float(times[end_idx] - times[start_idx]),
                        "peak_response_time": float(current_rt),
                        "baseline_response_time": float(baseline_rt),
                        "min_throughput": float(current_tp),
                        "baseline_throughput": float(baseline_tp),
                        "vusers_during": float(current_vu),
                        "severity": "high" if current_rt > baseline_rt * 1.5 else "medium"
                    })
        
        return disturbances
    
    @staticmethod
    def _analyze_bottleneck_patterns(
        disturbances: List[Dict[str, Any]],
        response_times: np.ndarray,
        throughput: np.ndarray,
        vusers: np.ndarray,
        times: np.ndarray
    ) -> Dict[str, Any]:
        """Analyze if disturbances indicate backend bottlenecks vs network/load issues"""
        if not disturbances:
            return {
                "type": "none",
                "confidence": 0.0,
                "indicators": []
            }
        
        indicators = []
        backend_bottleneck_score = 0
        
        for dist in disturbances:
            # Indicator 1: VUsers remain constant during disturbance
            dist_start_idx = np.argmin(np.abs(times - dist['start_time']))
            dist_end_idx = np.argmin(np.abs(times - dist['end_time']))
            
            if dist_start_idx < len(vusers) and dist_end_idx < len(vusers):
                vu_during = np.mean(vusers[dist_start_idx:dist_end_idx])
                vu_baseline = np.median(vusers)
                vu_change = abs(vu_during - vu_baseline) / vu_baseline if vu_baseline > 0 else 0
                
                if vu_change < 0.2:
                    indicators.append("VUsers remained constant during disturbance")
                    backend_bottleneck_score += 2
            
            # Indicator 2: Quick recovery after disturbance
            recovery_time = dist['end_time'] - dist['peak_time']
            if recovery_time < 300:  # Less than 5 minutes
                indicators.append("Quick recovery after disturbance")
                backend_bottleneck_score += 1
            
            # Indicator 3: Throughput drops more than response time increases
            rt_increase = (dist['peak_response_time'] - dist['baseline_response_time']) / dist['baseline_response_time']
            tp_decrease = (dist['baseline_throughput'] - dist['min_throughput']) / dist['baseline_throughput']
            
            if tp_decrease > rt_increase * 0.8:
                indicators.append("Throughput drop exceeds response time increase")
                backend_bottleneck_score += 1
        
        # Determine type
        if backend_bottleneck_score >= 3:
            bottleneck_type = "backend_bottleneck"
            confidence = min(0.95, 0.6 + (backend_bottleneck_score - 3) * 0.1)
        elif backend_bottleneck_score >= 1:
            bottleneck_type = "possible_backend_bottleneck"
            confidence = 0.5 + (backend_bottleneck_score - 1) * 0.1
        else:
            bottleneck_type = "unknown"
            confidence = 0.3
        
        return {
            "type": bottleneck_type,
            "confidence": confidence,
            "indicators": indicators,
            "score": backend_bottleneck_score
        }
    
    @staticmethod
    def _assess_stability(
        response_times: np.ndarray,
        throughput: np.ndarray,
        vusers: np.ndarray,
        steady_periods: List[Dict[str, Any]],
        disturbances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess overall system stability"""
        total_duration = len(response_times)
        
        # Calculate steady period coverage
        steady_coverage = sum(p['duration'] for p in steady_periods) / (response_times[-1] - response_times[0]) if len(response_times) > 1 else 0
        
        # Calculate disturbance impact
        disturbance_count = len(disturbances)
        total_disturbance_time = sum(d['duration'] for d in disturbances)
        
        # Calculate variance
        rt_cv = np.std(response_times) / np.mean(response_times) if np.mean(response_times) > 0 else 0
        tp_cv = np.std(throughput) / np.mean(throughput) if np.mean(throughput) > 0 else 0
        
        # Determine stability level
        if steady_coverage > 0.8 and disturbance_count == 0:
            stability_level = "highly_stable"
        elif steady_coverage > 0.6 and disturbance_count <= 2:
            stability_level = "stable"
        elif steady_coverage > 0.4 and disturbance_count <= 4:
            stability_level = "moderately_stable"
        else:
            stability_level = "unstable"
        
        return {
            "level": stability_level,
            "steady_coverage": steady_coverage,
            "disturbance_count": disturbance_count,
            "total_disturbance_time": total_disturbance_time,
            "response_time_cv": rt_cv,
            "throughput_cv": tp_cv
        }
    
    @staticmethod
    def _assess_capacity_limits(
        response_times: np.ndarray,
        throughput: np.ndarray,
        vusers: np.ndarray,
        disturbances: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess if system is operating near capacity limits"""
        # Check correlation between VUsers and response time
        if len(vusers) > 5 and np.std(vusers) > 0:
            correlation = np.corrcoef(vusers, response_times)[0, 1]
        else:
            correlation = 0
        
        # Check if disturbances occur even at constant load
        constant_load_disturbances = sum(1 for d in disturbances if d.get('vusers_during', 0) > 0)
        
        # Check response time variance
        rt_variance = np.var(response_times)
        rt_mean = np.mean(response_times)
        rt_cv = np.sqrt(rt_variance) / rt_mean if rt_mean > 0 else 0
        
        # Determine capacity assessment
        if correlation > 0.7:
            capacity_status = "at_capacity"
            message = "System shows strong correlation between load and response time, indicating capacity limits."
        elif constant_load_disturbances > 0:
            capacity_status = "near_capacity"
            message = "System experiences disturbances even at constant load, suggesting operation near capacity limits."
        elif rt_cv > 0.3:
            capacity_status = "variable_performance"
            message = "System shows variable performance, indicating potential capacity constraints."
        else:
            capacity_status = "within_capacity"
            message = "System appears to be operating well within capacity limits."
        
        return {
            "status": capacity_status,
            "message": message,
            "vuser_response_correlation": correlation,
            "constant_load_disturbances": constant_load_disturbances,
            "response_time_cv": rt_cv
        }
    
    @staticmethod
    def _generate_analysis_text(
        test_type: str,
        steady_periods: List[Dict[str, Any]],
        disturbances: List[Dict[str, Any]],
        bottleneck_analysis: Dict[str, Any],
        stability_assessment: Dict[str, Any],
        capacity_assessment: Dict[str, Any],
        response_times: np.ndarray,
        throughput: np.ndarray,
        vusers: np.ndarray,
        times: np.ndarray
    ) -> str:
        """Generate comprehensive analysis text matching the user's requirements"""
        
        # Calculate key metrics
        avg_response = np.mean(response_times)
        avg_throughput = np.mean(throughput)
        avg_vusers = np.mean(vusers)
        
        # Build analysis text
        analysis_parts = []
        
        # Test type and load description
        if test_type == "constant_load":
            analysis_parts.append(
                f"The graph shows a constant-load test with {avg_vusers:.0f} virtual users"
            )
        else:
            analysis_parts.append(
                f"The graph shows a {test_type.replace('_', '-')} test with an average of {avg_vusers:.0f} virtual users"
            )
        
        # Steady performance description
        if steady_periods:
            main_steady = max(steady_periods, key=lambda p: p['duration'])
            analysis_parts.append(
                f"where the system performs steadily for most of the run, maintaining an average response time of about {avg_response:.1f} seconds and a throughput of around {avg_throughput:.1f} requests per second"
            )
        else:
            analysis_parts.append(
                f"where the system maintains an average response time of about {avg_response:.1f} seconds and a throughput of around {avg_throughput:.1f} requests per second"
            )
        
        # Disturbance description
        if disturbances:
            dist_times = [f"{d['peak_time']:.0f} seconds" for d in disturbances[:2]]
            if len(disturbances) == 1:
                analysis_parts.append(
                    f"However, at {dist_times[0]}, there is a clear performance disturbance where throughput drops sharply while response time spikes, even though the user load remains unchanged"
                )
            elif len(disturbances) == 2:
                analysis_parts.append(
                    f"However, at two points ({dist_times[0]} and {dist_times[1]}), there are clear performance disturbances where throughput drops sharply while response time spikes, even though the user load remains unchanged"
                )
            else:
                analysis_parts.append(
                    f"However, at multiple points (including {dist_times[0]} and {dist_times[1]}), there are clear performance disturbances where throughput drops sharply while response time spikes, even though the user load remains unchanged"
                )
        else:
            analysis_parts.append(
                "The system maintains consistent performance throughout the test duration"
            )
        
        # Bottleneck analysis
        if bottleneck_analysis['type'] == "backend_bottleneck":
            analysis_parts.append(
                "This pattern indicates temporary backend bottlenecks—such as garbage collection, database slowdowns, thread pool saturation, or external service delays—rather than a network or load-generation issue"
            )
        elif bottleneck_analysis['type'] == "possible_backend_bottleneck":
            analysis_parts.append(
                "This pattern suggests possible backend bottlenecks—such as garbage collection, database slowdowns, or resource contention—rather than a network or load-generation issue"
            )
        
        # Recovery and stability assessment
        if disturbances:
            recovery_times = [d['end_time'] - d['peak_time'] for d in disturbances]
            avg_recovery = np.mean(recovery_times) if recovery_times else 0
            
            if avg_recovery < 300:  # Less than 5 minutes
                analysis_parts.append(
                    "Since the system recovers quickly after each dip and does not show a gradual degradation, it is generally stable"
                )
            else:
                analysis_parts.append(
                    "The system shows some recovery after disturbances, indicating moderate stability"
                )
        else:
            analysis_parts.append(
                "The system demonstrates excellent stability with no significant disturbances"
            )
        
        # Capacity limit assessment
        if capacity_assessment['status'] in ["at_capacity", "near_capacity"]:
            analysis_parts.append(
                "but operating close to its capacity limit, meaning that even small internal hiccups can cause noticeable performance impacts and higher user load would likely lead to more serious slowdowns"
            )
        elif capacity_assessment['status'] == "variable_performance":
            analysis_parts.append(
                "with some variability in performance, suggesting that the system may benefit from optimization to handle higher loads more consistently"
            )
        else:
            analysis_parts.append(
                "and operating well within capacity limits, indicating good headroom for increased load"
            )
        
        return ". ".join(analysis_parts) + "."
    
    @staticmethod
    def _analyze_response_time_distribution(response_times: np.ndarray) -> Dict[str, Any]:
        """
        Analyze response time distribution using statistical methods.
        Detects distribution type (Normal, Right-Skewed, Left-Skewed, Multi-modal)
        and generates business value interpretations.
        """
        if len(response_times) < 10:
            return {
                "distribution_type": "insufficient_data",
                "interpretation": "Insufficient data points for distribution analysis.",
                "statistics": {}
            }
        
        # Calculate basic statistics
        mean_rt = float(np.mean(response_times))
        median_rt = float(np.median(response_times))
        std_rt = float(np.std(response_times))
        variance_rt = float(np.var(response_times))
        cv = std_rt / mean_rt if mean_rt > 0 else 0  # Coefficient of Variation
        
        # Calculate skewness (measure of asymmetry)
        # Positive skewness = right tail longer (right-skewed)
        # Negative skewness = left tail longer (left-skewed)
        # Near zero = symmetric (normal distribution)
        n = len(response_times)
        if n > 2 and std_rt > 0:
            skewness = float((n / ((n - 1) * (n - 2))) * np.sum(((response_times - mean_rt) / std_rt) ** 3))
        else:
            skewness = 0.0
        
        # Calculate kurtosis (measure of tail heaviness)
        if n > 3 and std_rt > 0:
            kurtosis = float((n * (n + 1) / ((n - 1) * (n - 2) * (n - 3))) * 
                           np.sum(((response_times - mean_rt) / std_rt) ** 4) - 
                           3 * (n - 1) ** 2 / ((n - 2) * (n - 3)))
        else:
            kurtosis = 0.0
        
        # Detect multi-modal distribution using histogram analysis
        # If data has multiple peaks, it's multi-modal
        hist, bin_edges = np.histogram(response_times, bins=min(20, max(5, n // 10)))
        # Find peaks (local maxima)
        peaks = []
        for i in range(1, len(hist) - 1):
            if hist[i] > hist[i-1] and hist[i] > hist[i+1] and hist[i] > np.max(hist) * 0.3:
                peaks.append(i)
        
        is_multimodal = len(peaks) > 1
        
        # Determine distribution type
        distribution_type = GraphAnalyzer._classify_distribution(
            skewness, kurtosis, mean_rt, median_rt, std_rt, cv, is_multimodal
        )
        
        # Generate business value interpretation
        interpretation = GraphAnalyzer._generate_distribution_interpretation(
            distribution_type, skewness, kurtosis, mean_rt, median_rt, std_rt, cv, variance_rt
        )
        
        # Generate business questions answers
        business_answers = GraphAnalyzer._answer_business_questions(
            distribution_type, skewness, kurtosis, mean_rt, median_rt, std_rt, cv, variance_rt
        )
        
        # Generate unified system understanding
        unified_understanding = GraphAnalyzer._generate_unified_system_understanding(
            distribution_type, mean_rt, median_rt, std_rt, variance_rt, cv, skewness, kurtosis
        )
        
        return {
            "distribution_type": distribution_type,
            "interpretation": interpretation,
            "business_answers": business_answers,
            "unified_understanding": unified_understanding,
            "statistics": {
                "mean": mean_rt,
                "median": median_rt,
                "std_deviation": std_rt,
                "variance": variance_rt,
                "coefficient_of_variation": cv,
                "skewness": skewness,
                "kurtosis": kurtosis,
                "is_multimodal": is_multimodal
            }
        }
    
    @staticmethod
    def _classify_distribution(
        skewness: float, kurtosis: float, mean: float, median: float, 
        std: float, cv: float, is_multimodal: bool
    ) -> str:
        """Classify the distribution type based on statistical measures"""
        if is_multimodal:
            return "multi_modal"
        
        # Normal distribution: skewness near 0, kurtosis near 0
        if abs(skewness) < 0.5 and abs(kurtosis) < 1.0:
            # Check if mean and median are close (characteristic of normal distribution)
            if abs(mean - median) / mean < 0.1 if mean > 0 else True:
                return "normal"
        
        # Right-skewed: positive skewness, mean > median
        if skewness > 0.5 and mean > median * 1.1:
            return "right_skewed"
        
        # Left-skewed: negative skewness, mean < median
        if skewness < -0.5 and mean < median * 0.9:
            return "left_skewed"
        
        # High variance (high CV) suggests unstable distribution
        if cv > 0.5:
            return "high_variance"
        
        # Default to normal if criteria not met
        return "normal"
    
    @staticmethod
    def _generate_distribution_interpretation(
        dist_type: str, skewness: float, kurtosis: float, mean: float, 
        median: float, std: float, cv: float, variance: float
    ) -> str:
        """Generate business value interpretation based on distribution type"""
        
        interpretations = {
            "normal": (
                f"Normal Distribution Detected: The response time distribution follows a normal (bell-shaped) pattern. "
                f"Since most requests have similar response times with very few slow and fast outliers, this indicates "
                f"the system is stable and predictable. The system is well-balanced with sufficient resources "
                f"(CPU, Memory, threads, DB connections). There are no contention or queuing issues. "
                f"Users experience consistent performance, leading to predictable user experience and reliable "
                f"application behavior. This distribution suggests optimal resource allocation and efficient "
                f"system design. Mean: {mean:.2f}s, Std Dev: {std:.2f}s, CV: {cv:.2%}."
            ),
            "right_skewed": (
                f"Right-Skewed Distribution Detected: The response time distribution is right-skewed (tail extends to the right), "
                f"meaning most requests are fast, but there are significant outliers with slow response times. "
                f"This pattern indicates occasional performance degradation or resource contention. "
                f"While the majority of users experience good performance (median: {median:.2f}s), some requests "
                f"experience delays (mean: {mean:.2f}s > median). This suggests: (1) Occasional resource bottlenecks "
                f"(database locks, thread pool exhaustion, memory pressure), (2) Inconsistent performance that may "
                f"frustrate users during peak times, (3) Need for optimization in specific areas causing slow outliers. "
                f"Business Impact: Most users are satisfied, but a subset experiences poor performance, which can "
                f"lead to user complaints and potential churn. Skewness: {skewness:.2f}, CV: {cv:.2%}."
            ),
            "left_skewed": (
                f"Left-Skewed Distribution Detected: The response time distribution is left-skewed (tail extends to the left), "
                f"meaning most requests are relatively slow, but there are some very fast outliers. "
                f"This unusual pattern suggests: (1) System is generally operating at high load with most requests "
                f"experiencing delays, (2) Only a small subset of requests (possibly cached or simple operations) "
                f"complete quickly, (3) Potential capacity constraints where the system struggles to maintain "
                f"optimal performance. Business Impact: Most users experience slower than optimal performance, "
                f"indicating the system may be operating near capacity limits. This requires immediate attention "
                f"to improve overall user experience. Mean: {mean:.2f}s, Median: {median:.2f}s, Skewness: {skewness:.2f}."
            ),
            "multi_modal": (
                f"Multi-Modal Distribution Detected: The response time distribution shows multiple distinct peaks, "
                f"indicating the system operates in different performance modes. This pattern suggests: "
                f"(1) Different types of requests (simple vs complex operations) with distinct performance characteristics, "
                f"(2) System behavior changes under different conditions (e.g., cached vs non-cached, different endpoints), "
                f"(3) Potential performance tiers or service levels. Business Impact: The system shows inconsistent "
                f"behavior patterns, which can make performance prediction difficult. Users may experience varying "
                f"performance depending on the type of operation they perform. This suggests the need for request "
                f"categorization and targeted optimization. Variance: {variance:.2f}, Std Dev: {std:.2f}s."
            ),
            "high_variance": (
                f"High Variance Distribution Detected: The response time distribution shows high variability "
                f"(Coefficient of Variation: {cv:.2%} > 50%). This indicates: (1) Unpredictable system performance "
                f"with significant fluctuations, (2) Inconsistent resource availability or allocation, "
                f"(3) Potential issues with load balancing, caching, or resource contention. "
                f"Business Impact: Users experience highly variable performance, making it difficult to set "
                f"reliable expectations. This inconsistency can lead to user frustration and reduced trust "
                f"in the application. The high variance suggests the system needs optimization to achieve "
                f"more consistent performance. Mean: {mean:.2f}s, Std Dev: {std:.2f}s, Variance: {variance:.2f}."
            ),
            "insufficient_data": (
                "Insufficient data points for distribution analysis. More data is needed to determine "
                "the response time distribution pattern."
            )
        }
        
        return interpretations.get(dist_type, interpretations["normal"])
    
    @staticmethod
    def _answer_business_questions(
        dist_type: str, skewness: float, kurtosis: float, mean: float,
        median: float, std: float, cv: float, variance: float
    ) -> Dict[str, Dict[str, Any]]:
        """
        Answer specific business questions based on distribution analysis:
        1. Is system stable and well balanced?
        2. Are current resources sufficient?
        3. Are there contention or queuing issues?
        4. Are there occasional bottlenecks?
        """
        answers = {}
        
        # Question 1: System Stability and Balance
        if dist_type == "normal" and abs(skewness) < 0.5 and cv < 0.3:
            answers["stability"] = {
                "answer": "YES",
                "confidence": "High",
                "explanation": "The normal distribution with low variance indicates the system is stable and well-balanced. Most requests have similar response times with minimal outliers, suggesting consistent resource allocation and predictable behavior."
            }
        elif dist_type == "right_skewed" and cv < 0.4:
            answers["stability"] = {
                "answer": "MOSTLY",
                "confidence": "Medium",
                "explanation": "The system shows moderate stability. While most requests perform well, occasional slow outliers indicate some instability. The system is reasonably balanced but could benefit from optimization."
            }
        elif dist_type == "left_skewed" or dist_type == "high_variance":
            answers["stability"] = {
                "answer": "NO",
                "confidence": "High",
                "explanation": "The distribution pattern indicates system instability. High variance or left-skewed distribution suggests inconsistent performance and poor resource balance."
            }
        else:
            answers["stability"] = {
                "answer": "PARTIALLY",
                "confidence": "Medium",
                "explanation": "The system shows mixed stability characteristics. Some periods are stable, but overall performance is variable."
            }
        
        # Question 2: Resource Sufficiency
        if dist_type == "normal" and cv < 0.25 and abs(mean - median) / mean < 0.1:
            answers["resource_sufficiency"] = {
                "answer": "YES",
                "confidence": "High",
                "explanation": "Current resources (CPU, Memory, Threads, DB connections) are sufficient. The normal distribution with low variance indicates adequate resource allocation without contention. The system has sufficient capacity to handle the current load efficiently."
            }
        elif dist_type == "right_skewed" and cv < 0.35:
            answers["resource_sufficiency"] = {
                "answer": "MOSTLY",
                "confidence": "Medium",
                "explanation": "Resources are mostly sufficient, but occasional bottlenecks suggest some resource constraints. While the majority of requests are handled well, slow outliers indicate occasional resource contention or insufficient capacity in specific areas."
            }
        elif dist_type == "left_skewed" or (dist_type == "high_variance" and cv > 0.5):
            answers["resource_sufficiency"] = {
                "answer": "NO",
                "confidence": "High",
                "explanation": "Current resources appear insufficient. The distribution pattern suggests resource constraints, with most requests experiencing delays. Consider scaling up CPU, Memory, Threads, or DB connections to improve performance."
            }
        elif dist_type == "multi_modal":
            answers["resource_sufficiency"] = {
                "answer": "VARIABLE",
                "confidence": "Medium",
                "explanation": "Resource sufficiency varies by request type. Some operations have sufficient resources while others are constrained. This suggests uneven resource allocation or different resource requirements for different operation types."
            }
        else:
            answers["resource_sufficiency"] = {
                "answer": "MOSTLY",
                "confidence": "Medium",
                "explanation": "Resources are generally sufficient, but performance variability suggests some areas may need attention."
            }
        
        # Question 3: Contention or Queuing Issues
        if dist_type == "normal" and cv < 0.2:
            answers["contention"] = {
                "answer": "NO",
                "confidence": "High",
                "explanation": "No significant contention or queuing issues detected. The normal distribution with low variance indicates smooth resource access without bottlenecks. Threads, DB connections, and other resources are not experiencing contention."
            }
        elif dist_type == "right_skewed" and skewness > 1.0:
            answers["contention"] = {
                "answer": "YES - OCCASIONAL",
                "confidence": "Medium-High",
                "explanation": "Occasional contention or queuing issues are present. The right-skewed distribution with significant outliers suggests periodic resource contention (thread pool exhaustion, DB connection pool saturation, or memory pressure) causing some requests to queue."
            }
        elif dist_type == "left_skewed" or (dist_type == "high_variance" and cv > 0.4):
            answers["contention"] = {
                "answer": "YES - FREQUENT",
                "confidence": "High",
                "explanation": "Frequent contention or queuing issues detected. The distribution pattern indicates ongoing resource contention. Requests are frequently queuing due to insufficient threads, DB connections, or other resources. This requires immediate attention."
            }
        elif dist_type == "multi_modal":
            answers["contention"] = {
                "answer": "YES - SELECTIVE",
                "confidence": "Medium",
                "explanation": "Contention issues are selective, affecting specific operation types. The multi-modal distribution suggests some request types experience queuing while others do not, indicating uneven resource allocation or different contention points."
            }
        else:
            answers["contention"] = {
                "answer": "MINIMAL",
                "confidence": "Medium",
                "explanation": "Minimal contention detected. Some occasional queuing may occur, but it's not a significant issue."
            }
        
        # Question 4: Occasional Bottlenecks
        if dist_type == "normal" and cv < 0.25:
            answers["bottlenecks"] = {
                "answer": "NO",
                "confidence": "High",
                "explanation": "No occasional bottlenecks detected. The consistent normal distribution indicates smooth operation without performance bottlenecks. The system handles load evenly without significant slowdowns."
            }
        elif dist_type == "right_skewed" and skewness > 0.5:
            answers["bottlenecks"] = {
                "answer": "YES - OCCASIONAL",
                "confidence": "High",
                "explanation": "Occasional bottlenecks are present. The right-skewed distribution with slow outliers indicates periodic bottlenecks (garbage collection pauses, database lock contention, external service delays, or thread pool saturation) affecting a subset of requests."
            }
        elif dist_type == "left_skewed":
            answers["bottlenecks"] = {
                "answer": "YES - FREQUENT",
                "confidence": "High",
                "explanation": "Frequent bottlenecks detected. The left-skewed distribution indicates ongoing performance bottlenecks affecting most requests. The system is consistently experiencing slowdowns, suggesting systemic bottlenecks that need immediate resolution."
            }
        elif dist_type == "high_variance" and cv > 0.4:
            answers["bottlenecks"] = {
                "answer": "YES - VARIABLE",
                "confidence": "Medium-High",
                "explanation": "Variable bottlenecks are present. High variance indicates inconsistent performance with frequent but unpredictable bottlenecks. This suggests multiple bottleneck points or intermittent resource constraints."
            }
        elif dist_type == "multi_modal":
            answers["bottlenecks"] = {
                "answer": "YES - SELECTIVE",
                "confidence": "Medium",
                "explanation": "Selective bottlenecks affecting specific operation types. The multi-modal distribution suggests bottlenecks occur for certain request types while others perform well, indicating targeted optimization is needed."
            }
        else:
            answers["bottlenecks"] = {
                "answer": "MINIMAL",
                "confidence": "Medium",
                "explanation": "Minimal bottlenecks detected. Some occasional slowdowns may occur, but they are not significant enough to impact overall system performance."
            }
        
        return answers
    
    @staticmethod
    def _generate_unified_system_understanding(
        dist_type: str, mean: float, median: float, std: float, 
        variance: float, cv: float, skewness: float, kurtosis: float
    ) -> str:
        """
        Generate unified system understanding based on statistical summary.
        Combines distribution analysis and performance insights into a single,
        cohesive interpretation similar to the example provided.
        """
        # Build the understanding paragraph by paragraph
        
        # 1. Overall system responsiveness assessment
        if dist_type == "normal" and cv < 0.1 and abs(skewness) < 0.5:
            responsiveness = "The system demonstrates stable, predictable, and reliable responsiveness."
        elif dist_type == "normal" and cv < 0.2:
            responsiveness = "The system demonstrates generally stable and predictable responsiveness."
        elif dist_type == "right_skewed" and cv < 0.15:
            responsiveness = "The system demonstrates mostly stable responsiveness with occasional variations."
        elif dist_type == "right_skewed" and cv < 0.3:
            responsiveness = "The system shows moderate responsiveness with some variability."
        else:
            responsiveness = "The system shows variable responsiveness that requires attention."
        
        # 2. Response time consistency description
        mean_str = f"{mean:.2f}" if mean < 10 else f"{mean:.1f}"
        median_str = f"{median:.2f}" if median < 10 else f"{median:.1f}"
        
        if abs(mean - median) / mean < 0.05 if mean > 0 else True:
            consistency = f"Response times are consistently around {mean_str} seconds"
        elif abs(mean - median) / mean < 0.1:
            consistency = f"Response times are generally around {mean_str} seconds (median: {median_str}s)"
        else:
            consistency = f"Response times average {mean_str} seconds (median: {median_str}s)"
        
        # 3. Variability assessment
        if cv < 0.05:
            variability = "with minimal variability"
        elif cv < 0.1:
            variability = "with low variability"
        elif cv < 0.2:
            variability = "with moderate variability"
        elif cv < 0.3:
            variability = "with noticeable variability"
        else:
            variability = "with high variability"
        
        # 4. Relative dispersion (CV) description
        if cv < 0.05:
            dispersion = ", low relative dispersion"
        elif cv < 0.1:
            dispersion = ", relatively low dispersion"
        elif cv < 0.2:
            dispersion = ", moderate relative dispersion"
        else:
            dispersion = ", high relative dispersion"
        
        # 5. Skewness interpretation
        if abs(skewness) < 0.3:
            skew_desc = ", and symmetric distribution indicating balanced performance"
        elif 0.3 <= skewness < 0.7:
            skew_desc = ", and slight right skewness indicating rare slow responses"
        elif 0.7 <= skewness < 1.2:
            skew_desc = ", and moderate right skewness indicating occasional slow responses"
        elif skewness >= 1.2:
            skew_desc = ", and significant right skewness indicating frequent slow responses"
        elif -0.7 <= skewness < -0.3:
            skew_desc = ", and slight left skewness indicating rare fast responses"
        elif skewness < -0.7:
            skew_desc = ", and significant left skewness indicating most responses are slower than optimal"
        else:
            skew_desc = ""
        
        # 6. Overall health assessment
        if dist_type == "normal" and cv < 0.1 and abs(skewness) < 0.5:
            health = "Overall, the system appears healthy and well-tuned, suitable for meeting performance SLAs."
        elif dist_type == "normal" and cv < 0.2:
            health = "Overall, the system appears generally healthy and suitable for production use with minor optimizations."
        elif dist_type == "right_skewed" and cv < 0.2:
            health = "Overall, the system is functional but would benefit from optimization to reduce occasional slow responses."
        elif dist_type == "right_skewed" and cv < 0.3:
            health = "Overall, the system shows acceptable performance but requires attention to improve consistency."
        elif dist_type == "left_skewed" or (dist_type == "high_variance" and cv > 0.4):
            health = "Overall, the system requires immediate attention to address performance issues and improve stability."
        else:
            health = "Overall, the system performance needs optimization to achieve consistent, reliable behavior."
        
        # Combine into unified understanding
        understanding = f"{responsiveness} {consistency} {variability}{dispersion}{skew_desc}. {health}"
        
        return understanding



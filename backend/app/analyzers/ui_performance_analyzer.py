import numpy as np
from typing import List, Dict
from app.models.ui_performance import UIPerformanceMetrics

class UIPerformanceAnalyzer:
    """Analyzer for UI Performance timing data"""
    
    @staticmethod
    def analyze(data: List[Dict]) -> UIPerformanceMetrics:
        """Analyze UI Performance data and return aggregated metrics"""
        if not data:
            raise ValueError("No data provided for analysis")
        
        def extract_values(key):
            return [d.get(key) for d in data if d.get(key) is not None]
        
        def calculate_stats(values):
            if not values:
                return {"mean": None, "median": None, "p95": None, "p99": None, "min": None, "max": None}
            arr = np.array(values)
            return {
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "p95": float(np.percentile(arr, 95)),
                "p99": float(np.percentile(arr, 99)),
                "min": float(np.min(arr)),
                "max": float(np.max(arr))
            }
        
        metrics = UIPerformanceMetrics(
            total_samples=len(data),
            dns_lookup_time=calculate_stats(extract_values("dns_lookup_time")),
            connection_time=calculate_stats(extract_values("connection_time")),
            ssl_time=calculate_stats(extract_values("ssl_time")),
            time_to_first_byte=calculate_stats(extract_values("time_to_first_byte")),
            content_download_time=calculate_stats(extract_values("content_download_time")),
            dom_processing_time=calculate_stats(extract_values("dom_processing_time")),
            page_load_time=calculate_stats(extract_values("page_load_time")),
            full_page_load_time=calculate_stats(extract_values("full_page_load_time")),
            summary={
                "avg_dns_lookup": calculate_stats(extract_values("dns_lookup_time")).get("mean"),
                "avg_connection": calculate_stats(extract_values("connection_time")).get("mean"),
                "avg_page_load": calculate_stats(extract_values("page_load_time")).get("mean"),
                "avg_full_load": calculate_stats(extract_values("full_page_load_time")).get("mean"),
            }
        )
        
        return metrics













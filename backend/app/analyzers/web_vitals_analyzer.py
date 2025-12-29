import numpy as np
from typing import List, Dict
from app.models.web_vitals import WebVitalsMetrics

class WebVitalsAnalyzer:
    """Analyzer for Web Vitals data"""
    
    @staticmethod
    def analyze(data: List[Dict]) -> WebVitalsMetrics:
        """Analyze Web Vitals data and return aggregated metrics"""
        if not data:
            raise ValueError("No data provided for analysis")
        
        # Extract metrics
        lcp_values = [d.get("lcp") for d in data if d.get("lcp") is not None]
        fid_values = [d.get("fid") for d in data if d.get("fid") is not None]
        cls_values = [d.get("cls") for d in data if d.get("cls") is not None]
        fcp_values = [d.get("fcp") for d in data if d.get("fcp") is not None]
        ttfb_values = [d.get("ttfb") for d in data if d.get("ttfb") is not None]
        inp_values = [d.get("inp") for d in data if d.get("inp") is not None]
        
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
        
        metrics = WebVitalsMetrics(
            total_samples=len(data),
            lcp=calculate_stats(lcp_values),
            fid=calculate_stats(fid_values),
            cls=calculate_stats(cls_values),
            fcp=calculate_stats(fcp_values),
            ttfb=calculate_stats(ttfb_values),
            inp=calculate_stats(inp_values) if inp_values else None,
            summary={
                "lcp_good": sum(1 for v in lcp_values if v <= 2500),
                "lcp_needs_improvement": sum(1 for v in lcp_values if 2500 < v <= 4000),
                "lcp_poor": sum(1 for v in lcp_values if v > 4000),
                "fid_good": sum(1 for v in fid_values if v <= 100),
                "fid_needs_improvement": sum(1 for v in fid_values if 100 < v <= 300),
                "fid_poor": sum(1 for v in fid_values if v > 300),
                "cls_good": sum(1 for v in cls_values if v <= 0.1),
                "cls_needs_improvement": sum(1 for v in cls_values if 0.1 < v <= 0.25),
                "cls_poor": sum(1 for v in cls_values if v > 0.25),
            }
        )
        
        return metrics













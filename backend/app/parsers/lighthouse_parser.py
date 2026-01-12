"""
Lighthouse JSON Parser
Handles parsing and merging of Lighthouse JSON files
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import statistics


class LighthouseParser:
    """Parser for Lighthouse JSON files with multi-file merge support"""
    
    @staticmethod
    def parse(file_path: str) -> Dict[str, Any]:
        """
        Parse a single Lighthouse JSON file
        Returns the parsed Lighthouse data structure
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Lighthouse file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate Lighthouse schema
        LighthouseParser._validate_lighthouse_schema(data)
        
        return data
    
    @staticmethod
    def parse_multiple(file_paths: List[str]) -> Dict[str, Any]:
        """
        Parse and merge multiple Lighthouse JSON files using STATISTICAL AGGREGATION.
        
        This is DIFFERENT from JMeter merging:
        - JMeter: Concatenates all time-series records (simple list extension)
        - Lighthouse: Aggregates metrics across multiple page reports:
          * Numeric metrics: Uses MEDIAN for robustness
          * Audit scores: Uses WORST score for risk awareness
          * Page-level data: Preserved for per-page analysis
        
        Args:
            file_paths: List of paths to Lighthouse JSON files
            
        Returns:
            Consolidated Lighthouse JSON with aggregated metrics
        """
        if not file_paths:
            raise ValueError("No file paths provided")
        
        if len(file_paths) == 1:
            return LighthouseParser.parse(file_paths[0])
        
        # Parse all files
        parsed_files = []
        for file_path in file_paths:
            try:
                data = LighthouseParser.parse(file_path)
                parsed_files.append(data)
            except Exception as e:
                print(f"⚠️  Warning: Failed to parse {file_path}: {e}")
                continue
        
        if not parsed_files:
            raise ValueError("No valid Lighthouse files could be parsed")
        
        if len(parsed_files) == 1:
            return parsed_files[0]
        
        # Merge multiple files
        return LighthouseParser._merge_lighthouse_data(parsed_files)
    
    @staticmethod
    def _validate_lighthouse_schema(data: Dict[str, Any]) -> None:
        """Validate that the data has a basic Lighthouse structure"""
        if not isinstance(data, dict):
            raise ValueError("Lighthouse data must be a JSON object")
        
        if "audits" not in data:
            raise ValueError("Lighthouse data must contain 'audits' field")
        
        if "categories" not in data:
            raise ValueError("Lighthouse data must contain 'categories' field")
        
        if "performance" not in data.get("categories", {}):
            raise ValueError("Lighthouse data must contain 'categories.performance' field")
    
    @staticmethod
    def _merge_lighthouse_data(parsed_files: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Merge multiple Lighthouse JSON files
        - Numeric metrics: use median, also compute P75
        - Audits: prefer worst score, store aggregate stats
        - Track page URLs for page-level reporting
        """
        # Use first file as base structure
        merged = parsed_files[0].copy()
        
        # Extract numeric metrics from all files
        metrics_data = {
            "fcp": [],
            "lcp": [],
            "speed_index": [],
            "tbt": [],
            "cls": [],
            "tti": [],
            "performance_score": []
        }
        
        # Track page-level data
        page_data = []
        
        # Extract audit scores
        audit_scores = {}
        audit_numeric_values = {}
        
        for data in parsed_files:
            # Extract page URL
            page_url = data.get("finalUrl") or data.get("requestedUrl") or data.get("url", "Unknown Page")
            
            # Extract page metrics
            audits = data.get("audits", {})
            categories = data.get("categories", {})
            performance = categories.get("performance", {})
            
            fcp_audit = audits.get("first-contentful-paint", {})
            lcp_audit = audits.get("largest-contentful-paint", {})
            speed_index_audit = audits.get("speed-index", {})
            tbt_audit = audits.get("total-blocking-time", {})
            cls_audit = audits.get("cumulative-layout-shift", {})
            tti_audit = audits.get("interactive", {})
            perf_score = performance.get("score", 0)
            if perf_score and perf_score <= 1:
                perf_score = perf_score * 100
            
            # Extract numeric values from audits
            fcp_value = fcp_audit.get("numericValue", 0) if fcp_audit else 0
            lcp_value = lcp_audit.get("numericValue", 0) if lcp_audit else 0
            speed_index_value = speed_index_audit.get("numericValue", 0) if speed_index_audit else 0
            tbt_value = tbt_audit.get("numericValue", 0) if tbt_audit else 0
            cls_value = cls_audit.get("numericValue", 0) if cls_audit else 0
            tti_value = tti_audit.get("numericValue", 0) if tti_audit else 0
            
            # Store page-level data
            page_data.append({
                "url": page_url,
                "fcp": fcp_value / 1000 if fcp_value else 0,
                "lcp": lcp_value / 1000 if lcp_value else 0,
                "speed_index": speed_index_value / 1000 if speed_index_value else 0,
                "tbt": tbt_value,
                "cls": cls_value,
                "tti": tti_value / 1000 if tti_value else 0,
                "performance_score": perf_score if perf_score else 0
            })
            
            # Collect metrics for aggregation
            if fcp_value:
                metrics_data["fcp"].append(fcp_value)
            if lcp_value:
                metrics_data["lcp"].append(lcp_value)
            if speed_index_value:
                metrics_data["speed_index"].append(speed_index_value)
            if tbt_value:
                metrics_data["tbt"].append(tbt_value)
            if cls_value:
                metrics_data["cls"].append(cls_value)
            if tti_value:
                metrics_data["tti"].append(tti_value)
            if perf_score:
                metrics_data["performance_score"].append(perf_score)
            
            # Collect audit scores and numeric values
            for audit_id, audit_data in audits.items():
                if audit_id not in audit_scores:
                    audit_scores[audit_id] = []
                    audit_numeric_values[audit_id] = []
                
                if audit_data.get("score") is not None:
                    audit_scores[audit_id].append(audit_data["score"])
                
                if audit_data.get("numericValue") is not None:
                    audit_numeric_values[audit_id].append(audit_data["numericValue"])
        
        # Compute merged metrics (median and P75)
        merged_metrics = {}
        merged_metrics_p75 = {}
        
        for metric_name, values in metrics_data.items():
            if values:
                merged_metrics[metric_name] = statistics.median(values)
                if len(values) > 1:
                    sorted_values = sorted(values)
                    p75_index = int(len(sorted_values) * 0.75)
                    merged_metrics_p75[metric_name] = sorted_values[p75_index]
                else:
                    merged_metrics_p75[metric_name] = values[0]
        
        # Update merged audits with median/worst scores
        merged_audits = merged.get("audits", {}).copy()
        
        for audit_id, scores in audit_scores.items():
            if audit_id in merged_audits:
                # Use worst score (lowest) for risk awareness
                if scores:
                    worst_score = min(scores)
                    merged_audits[audit_id]["score"] = worst_score
                    
                    # Store aggregate stats
                    if audit_id in audit_numeric_values and audit_numeric_values[audit_id]:
                        numeric_vals = audit_numeric_values[audit_id]
                        merged_audits[audit_id]["numericValue"] = statistics.median(numeric_vals)
                        merged_audits[audit_id]["_aggregate_stats"] = {
                            "median": statistics.median(numeric_vals),
                            "p75": sorted(numeric_vals)[int(len(numeric_vals) * 0.75)] if len(numeric_vals) > 1 else numeric_vals[0],
                            "min": min(numeric_vals),
                            "max": max(numeric_vals)
                        }
        
        # Update merged data
        merged["audits"] = merged_audits
        
        # Update performance score
        if merged_metrics.get("performance_score"):
            perf_cat = merged.get("categories", {}).get("performance", {})
            perf_cat["score"] = merged_metrics["performance_score"] / 100  # Convert back to 0-1
            merged["categories"]["performance"] = perf_cat
        
        # Store merged metrics and P75 in metadata
        merged["_merged_metrics"] = merged_metrics
        merged["_merged_metrics_p75"] = merged_metrics_p75
        merged["_merge_info"] = {
            "file_count": len(parsed_files),
            "merge_method": "median_for_metrics_worst_score_for_audits"
        }
        
        # Store page-level data for reporting
        merged["_page_data"] = page_data
        
        return merged

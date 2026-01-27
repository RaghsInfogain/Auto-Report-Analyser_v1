"""
Enhanced Lighthouse JSON Parser
Comprehensive parsing with robust error handling, validation, and metric extraction
"""
import json
import copy
from typing import List, Dict, Any, Optional
from pathlib import Path
import statistics
from datetime import datetime


class LighthouseParser:
    """Enhanced parser for Lighthouse JSON files with comprehensive metric extraction"""
    
    # Core Web Vitals thresholds
    LCP_GOOD = 2.5  # seconds
    LCP_POOR = 4.0  # seconds
    FCP_GOOD = 1.8  # seconds
    FCP_POOR = 3.0  # seconds
    TBT_GOOD = 200  # milliseconds
    TBT_POOR = 600  # milliseconds
    CLS_GOOD = 0.10
    CLS_POOR = 0.25
    
    @staticmethod
    def parse(file_path: str) -> Dict[str, Any]:
        """
        Parse a single Lighthouse JSON file with comprehensive validation
        Returns structured data with all metrics and metadata
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Lighthouse file not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in file {file_path.name}: {e}")
        
        # Validate structure
        if not isinstance(raw_data, dict):
            raise ValueError("Invalid Lighthouse JSON: root must be an object")
        
        if "audits" not in raw_data:
            raise ValueError("Invalid Lighthouse JSON: missing 'audits' field")
        
        # Extract comprehensive page data
        page_data = LighthouseParser._extract_comprehensive_page_data(
            raw_data, file_path.name, 1
        )
        
        # Extract additional insights
        insights = LighthouseParser._extract_insights(raw_data)
        
        # Create result structure
        result = {
            "_page_data": [page_data],
            "_parsed_metrics": {
                "fcp": page_data["fcp"],
                "lcp": page_data["lcp"],
                "speed_index": page_data["speed_index"],
                "tbt": page_data["tbt"],
                "cls": page_data["cls"],
                "tti": page_data["tti"],
                "performance_score": page_data["performance_score"]
            },
            "_test_overview": {
                "total_pages": 1,
                "test_duration": page_data["test_duration"],
                "page_components": page_data["total_elements"],
                "total_bytes": page_data["total_bytes"],
                "network_requests": page_data.get("network_requests", 0),
                "dom_size": page_data.get("dom_size", 0)
            },
            "_insights": insights,
            "_metadata": {
                "lighthouse_version": raw_data.get("lighthouseVersion", "Unknown"),
                "fetch_time": raw_data.get("fetchTime", ""),
                "user_agent": raw_data.get("userAgent", ""),
                "environment": raw_data.get("environment", {})
            }
        }
        
        # Preserve original structure for reference
        for key in ["audits", "categories", "configSettings", "finalUrl", "requestedUrl", "url", "title"]:
            if key in raw_data:
                result[key] = copy.deepcopy(raw_data[key])
        
        return result
    
    @staticmethod
    def _extract_comprehensive_page_data(
        lighthouse_data: Dict[str, Any], 
        file_name: str, 
        file_index: int
    ) -> Dict[str, Any]:
        """
        Extract comprehensive page data including all metrics and additional insights
        """
        # Extract URL with multiple fallbacks
        page_url = (
            lighthouse_data.get("finalUrl") or 
            lighthouse_data.get("requestedUrl") or 
            lighthouse_data.get("url") or 
            f"Page {file_index}"
        )
        
        # Enhanced title extraction
        page_title = LighthouseParser._extract_page_title(lighthouse_data, page_url, file_index)
        
        # Extract audits
        audits = lighthouse_data.get("audits", {})
        
        # Extract Core Web Vitals and key metrics
        metrics = LighthouseParser._extract_core_metrics(audits)
        
        # Extract performance score
        perf_score = LighthouseParser._extract_performance_score(lighthouse_data)
        
        # Extract resource information
        resource_info = LighthouseParser._extract_resource_info(audits)
        
        # Extract render-blocking resources
        render_blocking = LighthouseParser._extract_render_blocking(audits)
        
        # Extract network information
        network_info = LighthouseParser._extract_network_info(audits)
        
        # Calculate test duration (use the longest meaningful metric)
        test_duration = max(
            metrics["lcp"],
            metrics["speed_index"],
            metrics["fcp"],
            metrics.get("tti", 0)
        )
        
        # Create comprehensive page entry
        page_entry = {
            # Basic info
            "url": str(page_url),
            "page_title": str(page_title),
            
            # Core Web Vitals
            "fcp": float(metrics["fcp"]),
            "lcp": float(metrics["lcp"]),
            "cls": float(metrics["cls"]),
            "tbt": float(metrics["tbt"]),
            
            # Additional metrics
            "speed_index": float(metrics["speed_index"]),
            "tti": float(metrics.get("tti", 0)),
            "performance_score": float(perf_score),
            
            # Resource metrics
            "total_elements": int(resource_info["total_elements"]),
            "total_bytes": int(resource_info["total_bytes"]),
            "network_requests": int(network_info["requests"]),
            "dom_size": int(network_info["dom_size"]),
            
            # Performance insights
            "render_blocking_resources": int(render_blocking["count"]),
            "render_blocking_time": float(render_blocking["time"]),
            
            # Test metadata
            "test_duration": float(test_duration),
            "_file_index": int(file_index),
            "_file_name": str(file_name),
            
            # Metric statuses (for quick reference)
            "lcp_status": LighthouseParser._get_metric_status(metrics["lcp"], "lcp"),
            "fcp_status": LighthouseParser._get_metric_status(metrics["fcp"], "fcp"),
            "tbt_status": LighthouseParser._get_metric_status(metrics["tbt"], "tbt"),
            "cls_status": LighthouseParser._get_metric_status(metrics["cls"], "cls"),
        }
        
        return page_entry
    
    @staticmethod
    def _extract_page_title(
        lighthouse_data: Dict[str, Any], 
        page_url: str, 
        file_index: int
    ) -> str:
        """Extract and clean page title from multiple sources"""
        # Try direct title
        title = lighthouse_data.get("title", "")
        
        # Try document-title audit - but be careful about displayValue
        if not title:
            audits = lighthouse_data.get("audits", {})
            doc_title_audit = audits.get("document-title", {})
            if doc_title_audit:
                # Prefer "title" field, avoid "displayValue" which might be like "Document has a `<title>` element"
                title = doc_title_audit.get("title", "")
                # Only use displayValue if it doesn't look like a description
                if not title:
                    display_value = doc_title_audit.get("displayValue", "")
                    # Check if displayValue is actually a title (not a description)
                    if display_value and "Document has a" not in display_value and len(display_value) < 100:
                        title = display_value
        
        # Fallback to URL
        if not title:
            url_parts = str(page_url).split("/")
            title = url_parts[-1] if url_parts[-1] else (url_parts[-2] if len(url_parts) > 1 else f"Page {file_index}")
            if "?" in title:
                title = title.split("?")[0]
        
        # Clean title - remove problematic text
        title = str(title).strip().rstrip("`'\"")
        # Remove common Lighthouse audit descriptions
        if "Document has a" in title or "has a `<title>`" in title:
            title = ""
        if len(title) > 100:
            title = title[:100] + "..."
        
        # If still no valid title, use URL
        if not title or len(title) < 3:
            url_parts = str(page_url).split("/")
            title = url_parts[-1] if url_parts[-1] else f"Page {file_index}"
            if "?" in title:
                title = title.split("?")[0]
        
        return title
    
    @staticmethod
    def _extract_core_metrics(audits: Dict[str, Any]) -> Dict[str, float]:
        """Extract Core Web Vitals and key performance metrics"""
        # Helper to safely extract numeric value
        def get_numeric_value(audit_key: str, default: float = 0.0) -> float:
            audit = audits.get(audit_key, {})
            if not audit:
                return default
            value = audit.get("numericValue", default)
            return float(value) if value is not None else default
        
        # Extract all metrics
        fcp_ms = get_numeric_value("first-contentful-paint", 0)
        lcp_ms = get_numeric_value("largest-contentful-paint", 0)
        speed_index_ms = get_numeric_value("speed-index", 0)
        tbt_ms = get_numeric_value("total-blocking-time", 0)
        cls_value = get_numeric_value("cumulative-layout-shift", 0)
        tti_ms = get_numeric_value("interactive", 0)
        
        # Convert to appropriate units
        return {
            "fcp": fcp_ms / 1000.0,  # seconds
            "lcp": lcp_ms / 1000.0,  # seconds
            "speed_index": speed_index_ms / 1000.0,  # seconds
            "tbt": tbt_ms,  # milliseconds
            "cls": cls_value,  # unitless
            "tti": tti_ms / 1000.0  # seconds
        }
    
    @staticmethod
    def _extract_performance_score(lighthouse_data: Dict[str, Any]) -> float:
        """Extract and normalize performance score"""
        categories = lighthouse_data.get("categories", {})
        performance = categories.get("performance", {})
        score = performance.get("score")
        
        if score is None:
            return 0.0
        
        # Normalize to 0-100
        if score <= 1.0:
            return float(score * 100.0)
        return float(score)
    
    @staticmethod
    def _extract_resource_info(audits: Dict[str, Any]) -> Dict[str, int]:
        """Extract resource summary information"""
        resource_summary = audits.get("resource-summary", {})
        total_elements = 0
        total_bytes = 0
        
        if resource_summary and "details" in resource_summary:
            details = resource_summary.get("details", {})
            items = details.get("items", [])
            for item in items:
                total_elements += int(item.get("requestCount", 0))
                total_bytes += int(item.get("transferSize", 0))
        
        return {
            "total_elements": total_elements,
            "total_bytes": total_bytes
        }
    
    @staticmethod
    def _extract_render_blocking(audits: Dict[str, Any]) -> Dict[str, Any]:
        """Extract render-blocking resources information"""
        render_blocking = audits.get("render-blocking-resources", {})
        
        count = 0
        total_time = 0.0
        
        if render_blocking and "details" in render_blocking:
            details = render_blocking.get("details", {})
            items = details.get("items", [])
            count = len(items)
            # Sum up render blocking time (if available)
            for item in items:
                # Estimate based on resource size or use a default
                total_time += 100.0  # Default estimate per resource
        
        return {
            "count": count,
            "time": total_time
        }
    
    @staticmethod
    def _extract_network_info(audits: Dict[str, Any]) -> Dict[str, int]:
        """Extract network-related information"""
        network_requests = audits.get("network-requests", {})
        dom_size_audit = audits.get("dom-size", {})
        
        requests = 0
        if network_requests and "details" in network_requests:
            items = network_requests.get("details", {}).get("items", [])
            requests = len(items)
        
        dom_size = 0
        if dom_size_audit:
            dom_size = int(dom_size_audit.get("numericValue", 0))
        
        return {
            "requests": requests,
            "dom_size": dom_size
        }
    
    @staticmethod
    def _extract_insights(lighthouse_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract additional insights from Lighthouse data"""
        audits = lighthouse_data.get("audits", {})
        
        insights = {
            "opportunities": [],
            "diagnostics": [],
            "passed_audits": 0,
            "failed_audits": 0
        }
        
        # Count opportunities and diagnostics
        for audit_key, audit_data in audits.items():
            if not isinstance(audit_data, dict):
                continue
            
            score = audit_data.get("score")
            if score is None:
                continue
            
            if score < 1.0:
                insights["failed_audits"] += 1
                # Check if it's an opportunity
                if audit_data.get("details", {}).get("type") == "opportunity":
                    insights["opportunities"].append({
                        "id": audit_key,
                        "title": audit_data.get("title", audit_key),
                        "score": score
                    })
            else:
                insights["passed_audits"] += 1
        
        return insights
    
    @staticmethod
    def _get_metric_status(value: float, metric_name: str) -> str:
        """Get status string for a metric"""
        if metric_name.lower() == "lcp":
            if value <= LighthouseParser.LCP_GOOD:
                return "Good"
            elif value <= LighthouseParser.LCP_POOR:
                return "Needs Improvement"
            else:
                return "Poor"
        elif metric_name.lower() == "fcp":
            if value <= LighthouseParser.FCP_GOOD:
                return "Good"
            elif value <= LighthouseParser.FCP_POOR:
                return "Needs Improvement"
            else:
                return "Poor"
        elif metric_name.lower() == "tbt":
            if value <= LighthouseParser.TBT_GOOD:
                return "Good"
            elif value <= LighthouseParser.TBT_POOR:
                return "Needs Improvement"
            else:
                return "Poor"
        elif metric_name.lower() == "cls":
            if value <= LighthouseParser.CLS_GOOD:
                return "Good"
            elif value <= LighthouseParser.CLS_POOR:
                return "Needs Improvement"
            else:
                return "Poor"
        return "Unknown"
    
    @staticmethod
    def parse_multiple(file_paths: List[str]) -> Dict[str, Any]:
        """
        Parse multiple Lighthouse JSON files independently
        Returns consolidated data with all pages and aggregated metrics
        """
        if not file_paths:
            raise ValueError("No file paths provided")
        
        if len(file_paths) == 1:
            return LighthouseParser.parse(file_paths[0])
        
        # Track unique files
        seen_paths = set()
        all_page_data = []
        base_structure = None
        all_insights = []
        
        print(f"\n{'='*60}")
        print(f"📊 Parsing {len(file_paths)} Lighthouse files...")
        print(f"{'='*60}\n")
        
        for idx, file_path in enumerate(file_paths, 1):
            try:
                file_path_obj = Path(file_path)
                file_abs_path = str(file_path_obj.absolute())
                file_name = file_path_obj.name
                
                # Check for duplicates
                if file_abs_path in seen_paths:
                    print(f"  ⚠️  Skipping duplicate: {file_name}")
                    continue
                seen_paths.add(file_abs_path)
                
                # Validate file
                if not file_path_obj.exists() or not file_path_obj.is_file():
                    print(f"  ⚠️  Invalid file: {file_name}")
                    continue
                
                print(f"  [{idx}/{len(file_paths)}] Parsing: {file_name}")
                
                # Read and parse
                with open(file_path_obj, 'r', encoding='utf-8') as f:
                    file_data = json.load(f)
                
                if not isinstance(file_data, dict) or "audits" not in file_data:
                    print(f"    ⚠️  Invalid structure, skipping")
                    continue
                
                # Extract page data
                page_entry = LighthouseParser._extract_comprehensive_page_data(
                    file_data, file_name, idx
                )
                
                # Log extracted values
                print(f"    ✓ LCP={page_entry['lcp']*1000:.0f}ms, "
                      f"FCP={page_entry['fcp']*1000:.0f}ms, "
                      f"TBT={page_entry['tbt']:.0f}ms, "
                      f"CLS={page_entry['cls']:.3f}, "
                      f"Score={page_entry['performance_score']:.0f}")
                
                # Extract insights
                insights = LighthouseParser._extract_insights(file_data)
                all_insights.append(insights)
                
                # Add to list
                all_page_data.append(copy.deepcopy(page_entry))
                
                # Store first file's structure
                if idx == 1:
                    base_structure = copy.deepcopy(file_data)
                    for key in ["_page_data", "_parsed_metrics", "_test_overview", "_insights"]:
                        if key in base_structure:
                            del base_structure[key]
                
            except json.JSONDecodeError as e:
                print(f"  ✗ JSON error in {file_name}: {e}")
                continue
            except Exception as e:
                print(f"  ✗ Error parsing {file_name}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if not all_page_data:
            raise ValueError("No valid Lighthouse files could be parsed")
        
        if not base_structure:
            raise ValueError("No valid base structure available")
        
        print(f"\n  ✓ Successfully parsed {len(all_page_data)} pages")
        
        # Calculate aggregated metrics (use median for robustness)
        aggregated_metrics = LighthouseParser._aggregate_metrics(all_page_data)
        
        # Calculate test overview
        test_overview = LighthouseParser._calculate_test_overview(all_page_data)
        
        # Aggregate insights
        aggregated_insights = LighthouseParser._aggregate_insights(all_insights)
        
        # Build final result
        result = copy.deepcopy(base_structure)
        result["_page_data"] = all_page_data
        result["_parsed_metrics"] = aggregated_metrics
        result["_test_overview"] = test_overview
        result["_insights"] = aggregated_insights
        
        # Validation summary
        print(f"\n  🔍 Validation Summary:")
        print(f"    Total pages: {len(all_page_data)}")
        print(f"    Unique LCP values: {len(set([round(p['lcp'], 2) for p in all_page_data]))}")
        print(f"    Aggregated LCP: {aggregated_metrics['lcp']*1000:.0f}ms")
        print(f"    Aggregated Performance Score: {aggregated_metrics['performance_score']:.1f}")
        
        return result
    
    @staticmethod
    def _aggregate_metrics(page_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Aggregate metrics across all pages using median (robust to outliers)"""
        all_fcp = [p["fcp"] for p in page_data if p["fcp"] > 0]
        all_lcp = [p["lcp"] for p in page_data if p["lcp"] > 0]
        all_speed_index = [p["speed_index"] for p in page_data if p["speed_index"] > 0]
        all_tbt = [p["tbt"] for p in page_data if p["tbt"] > 0]
        all_cls = [p["cls"] for p in page_data if p["cls"] > 0]
        all_tti = [p["tti"] for p in page_data if p["tti"] > 0]
        all_perf_scores = [p["performance_score"] for p in page_data if p["performance_score"] > 0]
        
        return {
            "fcp": statistics.median(all_fcp) if all_fcp else 0.0,
            "lcp": statistics.median(all_lcp) if all_lcp else 0.0,
            "speed_index": statistics.median(all_speed_index) if all_speed_index else 0.0,
            "tbt": statistics.median(all_tbt) if all_tbt else 0.0,
            "cls": statistics.median(all_cls) if all_cls else 0.0,
            "tti": statistics.median(all_tti) if all_tti else 0.0,
            "performance_score": statistics.median(all_perf_scores) if all_perf_scores else 0.0
        }
    
    @staticmethod
    def _calculate_test_overview(page_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate test overview from all pages"""
        test_durations = [p["test_duration"] for p in page_data if p["test_duration"] > 0]
        total_elements = sum(p["total_elements"] for p in page_data)
        total_bytes = sum(p["total_bytes"] for p in page_data)
        total_requests = sum(p.get("network_requests", 0) for p in page_data)
        total_dom_size = sum(p.get("dom_size", 0) for p in page_data)
        
        return {
            "total_pages": len(page_data),
            "test_duration": sum(test_durations) if test_durations else 0.0,
            "page_components": total_elements,
            "total_bytes": total_bytes,
            "network_requests": total_requests,
            "dom_size": total_dom_size
        }
    
    @staticmethod
    def _aggregate_insights(insights_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate insights from all files"""
        total_passed = sum(i.get("passed_audits", 0) for i in insights_list)
        total_failed = sum(i.get("failed_audits", 0) for i in insights_list)
        
        # Collect unique opportunities
        all_opportunities = {}
        for insights in insights_list:
            for opp in insights.get("opportunities", []):
                opp_id = opp.get("id")
                if opp_id and opp_id not in all_opportunities:
                    all_opportunities[opp_id] = opp
        
        return {
            "total_passed_audits": total_passed,
            "total_failed_audits": total_failed,
            "opportunities": list(all_opportunities.values()),
            "audit_pass_rate": round((total_passed / (total_passed + total_failed) * 100), 1) if (total_passed + total_failed) > 0 else 0.0
        }

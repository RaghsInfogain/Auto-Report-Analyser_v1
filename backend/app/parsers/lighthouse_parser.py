"""
Lighthouse JSON Parser - Clean Implementation
Handles parsing of single and multiple Lighthouse JSON files
"""
import json
from typing import List, Dict, Any
from pathlib import Path


class LighthouseParser:
    """Parser for Lighthouse JSON files"""
    
    @staticmethod
    def parse(file_path: str) -> Dict[str, Any]:
        """
        Parse a single Lighthouse JSON file
        Returns parsed data with page-level information
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Lighthouse file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate basic Lighthouse structure
        if not isinstance(data, dict):
            raise ValueError("Invalid Lighthouse JSON: root must be an object")
        
        if "audits" not in data:
            raise ValueError("Invalid Lighthouse JSON: missing 'audits' field")
        
        # Extract page URL
        page_url = data.get("finalUrl") or data.get("requestedUrl") or data.get("url", "Unknown Page")
        
        # Extract page title
        page_title = data.get("title", "")
        if not page_title:
            audits = data.get("audits", {})
            document_title_audit = audits.get("document-title", {})
            if document_title_audit:
                page_title = document_title_audit.get("title", "") or document_title_audit.get("displayValue", "")
        if not page_title:
            # Fallback: extract from URL
            url_parts = page_url.split("/")
            page_title = url_parts[-1] if url_parts[-1] else (url_parts[-2] if len(url_parts) > 1 else "Unknown Page")
            if "?" in page_title:
                page_title = page_title.split("?")[0]
        
        # Clean page title
        if page_title:
            page_title = str(page_title).strip().rstrip("`'\"")
        
        # Extract metrics from audits
        audits = data.get("audits", {})
        
        # Extract numeric values (in milliseconds)
        fcp_audit = audits.get("first-contentful-paint", {})
        lcp_audit = audits.get("largest-contentful-paint", {})
        speed_index_audit = audits.get("speed-index", {})
        tbt_audit = audits.get("total-blocking-time", {})
        cls_audit = audits.get("cumulative-layout-shift", {})
        tti_audit = audits.get("interactive", {})
        
        # Get numeric values (in milliseconds)
        fcp_ms = fcp_audit.get("numericValue", 0) if fcp_audit else 0
        lcp_ms = lcp_audit.get("numericValue", 0) if lcp_audit else 0
        speed_index_ms = speed_index_audit.get("numericValue", 0) if speed_index_audit else 0
        tbt_ms = tbt_audit.get("numericValue", 0) if tbt_audit else 0
        cls_value = cls_audit.get("numericValue", 0) if cls_audit else 0
        tti_ms = tti_audit.get("numericValue", 0) if tti_audit else 0
        
        # Convert to seconds where appropriate
        fcp = fcp_ms / 1000 if fcp_ms else 0
        lcp = lcp_ms / 1000 if lcp_ms else 0
        speed_index = speed_index_ms / 1000 if speed_index_ms else 0
        tti = tti_ms / 1000 if tti_ms else 0
        # TBT and CLS stay in original units (ms and unitless)
        tbt = tbt_ms
        cls = cls_value
        
        # Extract performance score
        categories = data.get("categories", {})
        performance = categories.get("performance", {})
        perf_score = performance.get("score", 0)
        if perf_score and perf_score <= 1:
            perf_score = perf_score * 100
        
        # Extract test duration (use LCP, Speed Index, or FCP as fallback)
        test_duration = lcp if lcp > 0 else (speed_index if speed_index > 0 else fcp)
        
        # Extract resource summary
        resource_summary = audits.get("resource-summary", {})
        total_elements = 0
        total_bytes = 0
        
        if resource_summary and "details" in resource_summary:
            details = resource_summary.get("details", {})
            items = details.get("items", [])
            for item in items:
                total_elements += item.get("requestCount", 0)
                total_bytes += item.get("transferSize", 0)
        
        # Create page data entry
        page_data = {
            "url": page_url,
            "page_title": page_title,
            "fcp": fcp,
            "lcp": lcp,
            "speed_index": speed_index,
            "tbt": tbt,
            "cls": cls,
            "tti": tti,
            "performance_score": perf_score,
            "test_duration": test_duration,
            "total_elements": total_elements,
            "total_bytes": total_bytes
        }
        
        # Store in data structure
        data["_page_data"] = [page_data]
        data["_parsed_metrics"] = {
            "fcp": fcp,
            "lcp": lcp,
            "speed_index": speed_index,
            "tbt": tbt,
            "cls": cls,
            "tti": tti,
            "performance_score": perf_score
        }
        
        return data
    
    @staticmethod
    def parse_multiple(file_paths: List[str]) -> Dict[str, Any]:
        """
        Parse multiple Lighthouse JSON files
        Returns consolidated data with all pages
        CRITICAL: Each file is parsed completely independently to avoid data duplication
        """
        if not file_paths:
            raise ValueError("No file paths provided")
        
        if len(file_paths) == 1:
            return LighthouseParser.parse(file_paths[0])
        
        # Parse all files - CRITICAL: Parse each file completely independently
        all_page_data = []
        first_file_data = None  # Store first file's structure for base
        
        for idx, file_path in enumerate(file_paths, 1):
            try:
                file_path_obj = Path(file_path)
                file_name = file_path_obj.name
                file_abs_path = str(file_path_obj.absolute())
                
                print(f"  Parsing file {idx}/{len(file_paths)}: {file_name}")
                print(f"    Full path: {file_abs_path}")
                
                # Add timeout protection for file reading
                import signal
                import sys
                
                # CRITICAL: Validate file path is unique
                if idx > 1:
                    prev_paths = [str(Path(fp).absolute()) for fp in file_paths[:idx-1]]
                    if file_abs_path in prev_paths:
                        print(f"    ⚠️  WARNING: Duplicate file path detected! This file was already parsed.")
                        print(f"    Previous paths: {prev_paths}")
                
                # CRITICAL: Parse each file independently - create fresh data structure
                if not file_path_obj.exists():
                    print(f"    ⚠️  Warning: File not found: {file_abs_path}")
                    continue
                
                # Validate file is readable
                if not file_path_obj.is_file():
                    print(f"    ⚠️  Warning: Path is not a file: {file_abs_path}")
                    continue
                
                # Read file fresh each time - CRITICAL: Read the actual file, not a cached version
                print(f"    → Reading file from disk...")
                try:
                    with open(file_path_obj, 'r', encoding='utf-8') as f:
                        file_data = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"    ✗ JSON decode error in file {idx}: {e}")
                    print(f"    → File might be corrupted or not a valid JSON file")
                    raise ValueError(f"Invalid JSON in file {file_name}: {str(e)}")
                except Exception as e:
                    print(f"    ✗ Error reading file {idx}: {e}")
                    raise
                
                # Verify we got data
                if not isinstance(file_data, dict):
                    print(f"    ⚠️  Warning: File data is not a dict: {type(file_data)}")
                    continue
                
                print(f"    → File read successfully, size: {file_path_obj.stat().st_size} bytes")
                
                # Validate basic structure
                if not isinstance(file_data, dict) or "audits" not in file_data:
                    print(f"    ⚠️  Warning: Invalid Lighthouse JSON structure in {file_path}")
                    continue
                
                # Extract page URL from THIS file
                page_url = file_data.get("finalUrl") or file_data.get("requestedUrl") or file_data.get("url", f"Unknown Page {idx}")
                
                # Extract page title from THIS file
                page_title = file_data.get("title", "")
                if not page_title:
                    audits = file_data.get("audits", {})
                    document_title_audit = audits.get("document-title", {})
                    if document_title_audit:
                        page_title = document_title_audit.get("title", "") or document_title_audit.get("displayValue", "")
                if not page_title:
                    url_parts = page_url.split("/")
                    page_title = url_parts[-1] if url_parts[-1] else (url_parts[-2] if len(url_parts) > 1 else f"Unknown Page {idx}")
                    if "?" in page_title:
                        page_title = page_title.split("?")[0]
                
                if page_title:
                    page_title = str(page_title).strip().rstrip("`'\"")
                
                # Extract metrics from THIS file's audits
                audits = file_data.get("audits", {})
                
                # Extract numeric values from THIS file
                fcp_audit = audits.get("first-contentful-paint", {})
                lcp_audit = audits.get("largest-contentful-paint", {})
                speed_index_audit = audits.get("speed-index", {})
                tbt_audit = audits.get("total-blocking-time", {})
                cls_audit = audits.get("cumulative-layout-shift", {})
                tti_audit = audits.get("interactive", {})
                
                # Get numeric values from THIS file - CRITICAL: Extract directly, no caching
                fcp_ms = fcp_audit.get("numericValue", 0) if fcp_audit else 0
                lcp_ms = lcp_audit.get("numericValue", 0) if lcp_audit else 0
                speed_index_ms = speed_index_audit.get("numericValue", 0) if speed_index_audit else 0
                tbt_ms = tbt_audit.get("numericValue", 0) if tbt_audit else 0
                cls_value = cls_audit.get("numericValue", 0) if cls_audit else 0
                tti_ms = tti_audit.get("numericValue", 0) if tti_audit else 0
                
                # Log raw values BEFORE conversion to verify they're different
                print(f"    → Raw metrics from file {idx}: LCP={lcp_ms}ms, FCP={fcp_ms}ms, TBT={tbt_ms}ms, CLS={cls_value}")
                
                # Convert to seconds where appropriate
                fcp = fcp_ms / 1000 if fcp_ms else 0
                lcp = lcp_ms / 1000 if lcp_ms else 0
                speed_index = speed_index_ms / 1000 if speed_index_ms else 0
                tti = tti_ms / 1000 if tti_ms else 0
                tbt = tbt_ms
                cls = cls_value
                
                # Verify values are actually numbers
                if not isinstance(lcp, (int, float)) or not isinstance(fcp, (int, float)):
                    print(f"    ⚠️  WARNING: Invalid metric types - LCP: {type(lcp)}, FCP: {type(fcp)}")
                
                # Extract performance score from THIS file
                categories = file_data.get("categories", {})
                performance = categories.get("performance", {})
                perf_score = performance.get("score", 0)
                if perf_score and perf_score <= 1:
                    perf_score = perf_score * 100
                
                # Extract test duration from THIS file
                test_duration = lcp if lcp > 0 else (speed_index if speed_index > 0 else fcp)
                
                # Extract resource summary from THIS file
                resource_summary = audits.get("resource-summary", {})
                total_elements = 0
                total_bytes = 0
                
                if resource_summary and "details" in resource_summary:
                    details = resource_summary.get("details", {})
                    items = details.get("items", [])
                    for item in items:
                        total_elements += item.get("requestCount", 0)
                        total_bytes += item.get("transferSize", 0)
                
                # Create page data entry for THIS file - completely independent
                # CRITICAL: Create a brand new dict with literal values, not references
                page_entry = {
                    "url": str(page_url),  # Ensure string, not reference
                    "page_title": str(page_title),  # Ensure string, not reference
                    "fcp": float(fcp),  # Ensure float, not reference
                    "lcp": float(lcp),  # Ensure float, not reference
                    "speed_index": float(speed_index),  # Ensure float, not reference
                    "tbt": float(tbt),  # Ensure float, not reference
                    "cls": float(cls),  # Ensure float, not reference
                    "tti": float(tti),  # Ensure float, not reference
                    "performance_score": float(perf_score),  # Ensure float, not reference
                    "test_duration": float(test_duration),  # Ensure float, not reference
                    "total_elements": int(total_elements),  # Ensure int, not reference
                    "total_bytes": int(total_bytes),  # Ensure int, not reference
                    "_file_index": int(idx),  # Ensure int, not reference
                    "_file_name": str(Path(file_path).name)  # Ensure string, not reference
                }
                
                # Log extracted metrics with verification
                print(f"    ✓ File {idx} extracted: URL={page_url[:50]}... | LCP={lcp*1000:.0f}ms ({lcp:.2f}s) | FCP={fcp*1000:.0f}ms | TBT={tbt:.0f}ms | CLS={cls:.3f}")
                print(f"    → Stored values: LCP={page_entry['lcp']:.3f}s, FCP={page_entry['fcp']:.3f}s, TBT={page_entry['tbt']:.0f}ms")
                
                # CRITICAL: Verify this entry is different from previous entries
                if len(all_page_data) > 0:
                    prev_entry = all_page_data[-1]
                    if abs(page_entry['lcp'] - prev_entry.get('lcp', 0)) < 0.001:
                        print(f"    ⚠️  WARNING: LCP value is identical to previous entry!")
                        print(f"       Current: {page_entry['lcp']:.3f}s, Previous: {prev_entry.get('lcp', 0):.3f}s")
                    else:
                        print(f"    ✓ LCP value is unique: {page_entry['lcp']:.3f}s (prev: {prev_entry.get('lcp', 0):.3f}s)")
                
                # Add to list - create a completely new dict to avoid any reference issues
                import copy
                all_page_data.append(copy.deepcopy(page_entry))
                
                # Store first file's structure for base (but don't use its _page_data)
                if idx == 1:
                    import copy
                    first_file_data = copy.deepcopy(file_data)
                    # Remove _page_data from first file data since we'll replace it
                    if "_page_data" in first_file_data:
                        del first_file_data["_page_data"]
                    if "_parsed_metrics" in first_file_data:
                        del first_file_data["_parsed_metrics"]
                
            except Exception as e:
                print(f"  ✗ Error parsing file {idx} ({file_path}): {e}")
                import traceback
                traceback.print_exc()
                continue
        
        if not all_page_data:
            raise ValueError("No valid Lighthouse files could be parsed")
        
        if not first_file_data:
            raise ValueError("No valid base file structure available")
        
        # Create base structure from first file (without _page_data)
        base_data = first_file_data.copy()
        
        # Add consolidated page data
        base_data["_page_data"] = all_page_data
        
        # Validate that all pages have unique metrics
        print(f"  🔍 Validating page data uniqueness...")
        lcp_values = [p.get("lcp", 0) for p in all_page_data]
        fcp_values = [p.get("fcp", 0) for p in all_page_data]
        unique_lcps = len(set([round(v, 2) for v in lcp_values if v > 0]))
        unique_fcps = len(set([round(v, 2) for v in fcp_values if v > 0]))
        print(f"    Unique LCP values: {unique_lcps}/{len([v for v in lcp_values if v > 0])}")
        print(f"    Unique FCP values: {unique_fcps}/{len([v for v in fcp_values if v > 0])}")
        
        if unique_lcps < len([v for v in lcp_values if v > 0]):
            print(f"    ⚠️  WARNING: Some pages have identical LCP values - this may indicate a parsing issue")
        
        # Calculate aggregated metrics (median for robustness)
        import statistics
        
        all_fcp = [p.get("fcp", 0) for p in all_page_data if p.get("fcp", 0) > 0]
        all_lcp = [p.get("lcp", 0) for p in all_page_data if p.get("lcp", 0) > 0]
        all_speed_index = [p.get("speed_index", 0) for p in all_page_data if p.get("speed_index", 0) > 0]
        all_tbt = [p.get("tbt", 0) for p in all_page_data if p.get("tbt", 0) > 0]
        all_cls = [p.get("cls", 0) for p in all_page_data if p.get("cls", 0) > 0]
        all_tti = [p.get("tti", 0) for p in all_page_data if p.get("tti", 0) > 0]
        all_perf_scores = [p.get("performance_score", 0) for p in all_page_data if p.get("performance_score", 0) > 0]
        
        # Update aggregated metrics
        base_data["_parsed_metrics"] = {
            "fcp": statistics.median(all_fcp) if all_fcp else 0,
            "lcp": statistics.median(all_lcp) if all_lcp else 0,
            "speed_index": statistics.median(all_speed_index) if all_speed_index else 0,
            "tbt": statistics.median(all_tbt) if all_tbt else 0,
            "cls": statistics.median(all_cls) if all_cls else 0,
            "tti": statistics.median(all_tti) if all_tti else 0,
            "performance_score": statistics.median(all_perf_scores) if all_perf_scores else 0
        }
        
        # Calculate test overview
        test_durations = [p.get("test_duration", 0) for p in all_page_data if p.get("test_duration", 0) > 0]
        total_elements = sum(p.get("total_elements", 0) for p in all_page_data)
        total_bytes = sum(p.get("total_bytes", 0) for p in all_page_data)
        
        base_data["_test_overview"] = {
            "total_pages": len(all_page_data),
            "test_duration": sum(test_durations) if test_durations else 0,
            "page_components": total_elements,
            "total_bytes": total_bytes
        }
        
        print(f"  ✓ Parsed {len(all_page_data)} pages from {len(file_paths)} files")
        
        return base_data

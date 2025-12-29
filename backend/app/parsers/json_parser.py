import json
from typing import List, Dict, Any
from app.models.web_vitals import WebVitalsData
from app.models.ui_performance import UIPerformanceData

class JSONParser:
    """Parser for JSON files"""
    
    @staticmethod
    def parse(file_path: str, category: str) -> List[Dict[str, Any]]:
        """
        Parse JSON file based on category
        Returns list of data objects
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle both single object and array
        if isinstance(data, dict):
            data = [data]
        elif not isinstance(data, list):
            raise ValueError("JSON must be an object or array")
        
        if category == "web_vitals":
            return JSONParser._parse_web_vitals(data)
        elif category == "ui_performance":
            return JSONParser._parse_ui_performance(data)
        else:
            raise ValueError(f"Unsupported category for JSON: {category}")
    
    @staticmethod
    def _parse_web_vitals(data: List[Dict]) -> List[Dict]:
        """Parse Web Vitals data from JSON"""
        results = []
        for item in data:
            parsed = {
                "lcp": item.get("lcp") or item.get("LCP"),
                "fid": item.get("fid") or item.get("FID"),
                "cls": item.get("cls") or item.get("CLS"),
                "fcp": item.get("fcp") or item.get("FCP"),
                "ttfb": item.get("ttfb") or item.get("TTFB"),
                "inp": item.get("inp") or item.get("INP"),
                "url": item.get("url") or item.get("URL"),
                "timestamp": item.get("timestamp") or item.get("time"),
                "custom_metrics": {k: v for k, v in item.items() 
                                  if k not in ["lcp", "fid", "cls", "fcp", "ttfb", "inp", "url", "timestamp", "time", "LCP", "FID", "CLS", "FCP", "TTFB", "INP", "URL"]}
            }
            results.append(parsed)
        return results
    
    @staticmethod
    def _parse_ui_performance(data: List[Dict]) -> List[Dict]:
        """Parse UI Performance data from JSON"""
        results = []
        for item in data:
            # Calculate derived metrics
            navigation_timing = item.get("navigationTiming") or item.get("navigation_timing") or item
            
            dns_lookup = None
            if "domainLookupEnd" in navigation_timing and "domainLookupStart" in navigation_timing:
                dns_lookup = navigation_timing["domainLookupEnd"] - navigation_timing["domainLookupStart"]
            elif "domain_lookup_end" in navigation_timing and "domain_lookup_start" in navigation_timing:
                dns_lookup = navigation_timing["domain_lookup_end"] - navigation_timing["domain_lookup_start"]
            
            connection = None
            if "connectEnd" in navigation_timing and "connectStart" in navigation_timing:
                connection = navigation_timing["connectEnd"] - navigation_timing["connectStart"]
            elif "connect_end" in navigation_timing and "connect_start" in navigation_timing:
                connection = navigation_timing["connect_end"] - navigation_timing["connect_start"]
            
            parsed = {
                **{k: navigation_timing.get(k) for k in [
                    "navigationStart", "fetchStart", "domainLookupStart", "domainLookupEnd",
                    "connectStart", "connectEnd", "secureConnectionStart", "requestStart",
                    "responseStart", "responseEnd", "domLoading", "domInteractive",
                    "domContentLoadedEventStart", "domContentLoadedEventEnd", "domComplete",
                    "loadEventStart", "loadEventEnd"
                ]},
                **{k: navigation_timing.get(k.replace("_", "")) for k in [
                    "navigation_start", "fetch_start", "domain_lookup_start", "domain_lookup_end",
                    "connect_start", "connect_end", "secure_connection_start", "request_start",
                    "response_start", "response_end", "dom_loading", "dom_interactive",
                    "dom_content_loaded_event_start", "dom_content_loaded_event_end", "dom_complete",
                    "load_event_start", "load_event_end"
                ]},
                "dns_lookup_time": dns_lookup,
                "connection_time": connection,
                "url": item.get("url") or item.get("URL"),
                "timestamp": item.get("timestamp") or item.get("time"),
                "full_page_load_time": item.get("loadEventEnd") or item.get("load_event_end") or item.get("full_page_load_time")
            }
            results.append(parsed)
        return results













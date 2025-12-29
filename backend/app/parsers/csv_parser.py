import pandas as pd
from typing import List, Dict, Any
from app.models.web_vitals import WebVitalsData
from app.models.ui_performance import UIPerformanceData

class CSVParser:
    """Parser for CSV files"""
    
    @staticmethod
    def parse(file_path: str, category: str) -> List[Dict[str, Any]]:
        """
        Parse CSV file based on category
        Returns list of data objects
        """
        df = pd.read_csv(file_path)
        
        if category == "web_vitals":
            return CSVParser._parse_web_vitals(df)
        elif category == "ui_performance":
            return CSVParser._parse_ui_performance(df)
        else:
            raise ValueError(f"Unsupported category for CSV: {category}")
    
    @staticmethod
    def _parse_web_vitals(df: pd.DataFrame) -> List[Dict]:
        """Parse Web Vitals data from CSV"""
        results = []
        for _, row in df.iterrows():
            # Handle different column name variations
            result = {
                "lcp": CSVParser._get_value(row, ["lcp", "LCP", "largest_contentful_paint"]),
                "fid": CSVParser._get_value(row, ["fid", "FID", "first_input_delay"]),
                "cls": CSVParser._get_value(row, ["cls", "CLS", "cumulative_layout_shift"]),
                "fcp": CSVParser._get_value(row, ["fcp", "FCP", "first_contentful_paint"]),
                "ttfb": CSVParser._get_value(row, ["ttfb", "TTFB", "time_to_first_byte"]),
                "inp": CSVParser._get_value(row, ["inp", "INP", "interaction_to_next_paint"]),
                "url": CSVParser._get_value(row, ["url", "URL", "page_url"]),
                "timestamp": CSVParser._get_value(row, ["timestamp", "time", "date", "datetime"]),
            }
            results.append(result)
        return results
    
    @staticmethod
    def _parse_ui_performance(df: pd.DataFrame) -> List[Dict]:
        """Parse UI Performance data from CSV"""
        results = []
        for _, row in df.iterrows():
            result = {
                "dns_lookup_time": CSVParser._get_value(row, ["dns_lookup_time", "dnsLookupTime", "dns"]),
                "connection_time": CSVParser._get_value(row, ["connection_time", "connectionTime", "connect"]),
                "ssl_time": CSVParser._get_value(row, ["ssl_time", "sslTime", "secure_connection_time"]),
                "time_to_first_byte": CSVParser._get_value(row, ["ttfb", "time_to_first_byte", "timeToFirstByte"]),
                "page_load_time": CSVParser._get_value(row, ["page_load_time", "pageLoadTime", "load_time"]),
                "full_page_load_time": CSVParser._get_value(row, ["full_page_load_time", "fullPageLoadTime", "total_load_time"]),
                "url": CSVParser._get_value(row, ["url", "URL", "page_url"]),
                "timestamp": CSVParser._get_value(row, ["timestamp", "time", "date", "datetime"]),
            }
            results.append(result)
        return results
    
    @staticmethod
    def _get_value(row: pd.Series, possible_keys: List[str]) -> Any:
        """Get value from row using multiple possible key names"""
        for key in possible_keys:
            if key in row and pd.notna(row[key]):
                return row[key]
        return None













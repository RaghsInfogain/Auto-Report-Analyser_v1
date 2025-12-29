import pandas as pd
import xml.etree.ElementTree as ET
from typing import List, Dict, Any

class JTLParser:
    """Parser for JMeter JTL files (CSV and XML formats)"""
    
    @staticmethod
    def parse(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse JTL file (CSV or XML format)
        Returns list of JMeter data objects
        """
        if file_path.endswith('.xml'):
            return JTLParser._parse_xml(file_path)
        else:
            return JTLParser._parse_csv(file_path)
    
    @staticmethod
    def _parse_csv(file_path: str) -> List[Dict]:
        """Parse CSV format JTL file"""
        df = pd.read_csv(file_path)
        results = []
        
        for _, row in df.iterrows():
            result = {
                "timestamp": JTLParser._get_value(row, ["timeStamp", "timestamp", "time"]),
                "label": JTLParser._get_value(row, ["label", "Label"]),
                "response_code": JTLParser._get_value(row, ["responseCode", "response_code", "rc"]),
                "response_message": JTLParser._get_value(row, ["responseMessage", "response_message", "rm"]),
                "thread_name": JTLParser._get_value(row, ["threadName", "thread_name", "tn"]),
                "data_type": JTLParser._get_value(row, ["dataType", "data_type", "dt"]),
                "success": JTLParser._get_value(row, ["success", "Success"]),
                "failure_message": JTLParser._get_value(row, ["failureMessage", "failure_message", "fm"]),
                "bytes": JTLParser._get_value(row, ["bytes", "Bytes"]),
                "sent_bytes": JTLParser._get_value(row, ["sentBytes", "sent_bytes", "sb"]),
                "grp_threads": JTLParser._get_value(row, ["grpThreads", "grp_threads", "gt"]),
                "all_threads": JTLParser._get_value(row, ["allThreads", "all_threads", "at"]),
                "latency": JTLParser._get_value(row, ["Latency", "latency", "lt"]),
                "sample_time": JTLParser._get_value(row, ["elapsed", "Elapsed", "elapsedTime", "sample_time", "st"]),
                "connect_time": JTLParser._get_value(row, ["Connect", "connect", "connectTime", "connect_time", "ct"]),
            }
            results.append(result)
        
        return results
    
    @staticmethod
    def _parse_xml(file_path: str) -> List[Dict]:
        """Parse XML format JTL file"""
        tree = ET.parse(file_path)
        root = tree.getroot()
        results = []
        
        for sample in root.findall('.//sample'):
            result = {
                "timestamp": sample.get("ts") or sample.get("t"),
                "label": sample.get("lb") or sample.get("label"),
                "response_code": sample.get("rc") or sample.get("responseCode"),
                "response_message": sample.get("rm") or sample.get("responseMessage"),
                "thread_name": sample.get("tn") or sample.get("threadName"),
                "data_type": sample.get("dt") or sample.get("dataType"),
                "success": sample.get("s") == "true" if sample.get("s") else None,
                "failure_message": sample.get("fm") or sample.get("failureMessage"),
                "bytes": int(sample.get("by") or sample.get("bytes") or 0),
                "sent_bytes": int(sample.get("sby") or sample.get("sentBytes") or 0),
                "grp_threads": int(sample.get("ng") or sample.get("grpThreads") or 0),
                "all_threads": int(sample.get("na") or sample.get("allThreads") or 0),
                "latency": float(sample.get("lt") or sample.get("latency") or 0),
                "sample_time": float(sample.get("t") or sample.get("elapsed") or sample.get("sampleTime") or 0),
                "connect_time": float(sample.get("ct") or sample.get("connect") or sample.get("connectTime") or 0),
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













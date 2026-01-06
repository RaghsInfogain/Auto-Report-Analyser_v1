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
        """Parse CSV format JTL file - Optimized for large files"""
        import time
        import os
        
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"  Reading CSV file ({file_size_mb:.1f} MB)...")
        
        # Use chunking for very large files to avoid memory issues
        chunk_size = 100000  # Process 100k rows at a time
        results = []
        
        # Read CSV in chunks for better memory management
        try:
            # First, read a small sample to get column names
            sample_df = pd.read_csv(file_path, nrows=10)
            columns = sample_df.columns.tolist()
            
            # Read full file in chunks
            chunk_list = []
            for chunk in pd.read_csv(file_path, chunksize=chunk_size, low_memory=False):
                chunk_list.append(chunk)
                if len(chunk_list) * chunk_size % 500000 == 0:
                    print(f"    Processed {len(chunk_list) * chunk_size:,} rows...")
            
            # Combine chunks
            df = pd.concat(chunk_list, ignore_index=True)
            print(f"  ✓ Loaded {len(df):,} rows into memory")
            
        except MemoryError:
            # If memory error, process in smaller chunks
            print(f"  ⚠ Large file detected, processing in chunks...")
            df = None
            chunk_list = []
            for chunk in pd.read_csv(file_path, chunksize=50000, low_memory=False):
                chunk_list.append(chunk)
                if len(chunk_list) % 10 == 0:
                    print(f"    Processed {len(chunk_list) * 50000:,} rows...")
            df = pd.concat(chunk_list, ignore_index=True)
            print(f"  ✓ Loaded {len(df):,} rows")
        
        # Convert to list of dicts - optimized
        print(f"  Converting to records...")
        start_time = time.time()
        
        # Use vectorized operations where possible
        results = []
        for idx, row in df.iterrows():
            if idx > 0 and idx % 100000 == 0:
                elapsed = time.time() - start_time
                rate = idx / elapsed if elapsed > 0 else 0
                print(f"    Converted {idx:,} records ({rate:,.0f} records/sec)...")
            
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
        
        elapsed = time.time() - start_time
        print(f"  ✓ Converted {len(results):,} records in {elapsed:.1f}s")
        
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
    
    @staticmethod
    def merge_data(all_data: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Merge multiple JTL data lists into a single list
        For very large datasets, skips sorting to improve performance
        Optimized for large datasets
        """
        if not all_data:
            return []
        
        if len(all_data) == 1:
            return all_data[0]
        
        # Flatten all data into a single list
        total_records = sum(len(data_list) for data_list in all_data)
        print(f"  Merging {total_records:,} total records from {len(all_data)} file(s)...")
        
        # For very large datasets (>500k), skip sorting to avoid long delays
        # The analyzer can handle unsorted data, and time-series will be calculated correctly
        if total_records > 500000:
            print(f"  Very large dataset ({total_records:,} records). Skipping sort for performance...")
            merged = []
            for idx, data_list in enumerate(all_data):
                print(f"    Processing file {idx+1}/{len(all_data)}: {len(data_list):,} records")
                merged.extend(data_list)
            print(f"  Merge complete: {len(merged):,} records (unsorted for performance)")
        elif total_records > 100000:
            print(f"  Large dataset detected ({total_records:,} records). Using optimized merge...")
            merged = []
            for idx, data_list in enumerate(all_data):
                print(f"    Processing file {idx+1}/{len(all_data)}: {len(data_list):,} records")
                merged.extend(data_list)
            
            # Quick sort for large but manageable datasets
            print(f"  Sorting {len(merged):,} records by timestamp...")
            def get_timestamp(item):
                ts = item.get("timestamp")
                if ts is None:
                    return 0
                try:
                    return float(ts)
                except (ValueError, TypeError):
                    return 0
            
            merged.sort(key=get_timestamp)
            print(f"  Merge complete: {len(merged):,} records")
        else:
            # For smaller datasets, use simple approach with sorting
            merged = []
            for data_list in all_data:
                merged.extend(data_list)
            
            # Sort by timestamp
            def get_timestamp(item):
                ts = item.get("timestamp")
                if ts is None:
                    return 0
                try:
                    return float(ts)
                except (ValueError, TypeError):
                    return 0
            
            merged.sort(key=get_timestamp)
        
        return merged













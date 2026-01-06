"""
Simplified and robust JTL parser for JMeter results
Handles CSV and XML formats efficiently
"""
import csv
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from pathlib import Path


class JTLParserV2:
    """Simplified JTL parser with robust error handling"""
    
    @staticmethod
    def parse(file_path: str) -> List[Dict[str, Any]]:
        """
        Parse JTL file (CSV or XML format)
        Returns list of standardized JMeter records
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.suffix.lower() == '.xml':
            return JTLParserV2._parse_xml(file_path)
        else:
            return JTLParserV2._parse_csv(file_path)
    
    @staticmethod
    def _parse_csv(file_path: Path) -> List[Dict[str, Any]]:
        """Parse CSV format JTL file - optimized and simple"""
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read first line to detect delimiter and headers
                first_line = f.readline()
                delimiter = ',' if ',' in first_line else '\t'
                f.seek(0)
                
                reader = csv.DictReader(f, delimiter=delimiter)
                
                for row_num, row in enumerate(reader, start=2):
                    try:
                        record = JTLParserV2._normalize_csv_record(row)
                        if record:  # Only add valid records
                            results.append(record)
                    except Exception as e:
                        # Skip invalid rows but continue processing
                        if row_num % 10000 == 0:
                            print(f"  Warning: Skipped row {row_num}: {e}")
                        continue
                        
        except Exception as e:
            raise ValueError(f"Error parsing CSV file {file_path}: {e}")
        
        return results
    
    @staticmethod
    def _normalize_csv_record(row: Dict[str, str]) -> Dict[str, Any]:
        """Normalize CSV row to standard format"""
        # Map common column name variations
        field_mapping = {
            'timestamp': ['timeStamp', 'timestamp', 'time', 'ts'],
            'label': ['label', 'Label', 'lb'],
            'response_code': ['responseCode', 'response_code', 'rc', 'code'],
            'response_message': ['responseMessage', 'response_message', 'rm', 'message'],
            'thread_name': ['threadName', 'thread_name', 'tn'],
            'data_type': ['dataType', 'data_type', 'dt'],
            'success': ['success', 'Success', 's'],
            'failure_message': ['failureMessage', 'failure_message', 'fm'],
            'bytes': ['bytes', 'Bytes', 'by'],
            'sent_bytes': ['sentBytes', 'sent_bytes', 'sby', 'sent'],
            'grp_threads': ['grpThreads', 'grp_threads', 'ng', 'gt'],
            'all_threads': ['allThreads', 'all_threads', 'na', 'at'],
            'latency': ['Latency', 'latency', 'lt'],
            'sample_time': ['elapsed', 'Elapsed', 'elapsedTime', 'sample_time', 'st', 't'],
            'connect_time': ['Connect', 'connect', 'connectTime', 'connect_time', 'ct'],
        }
        
        record = {}
        
        for target_field, possible_keys in field_mapping.items():
            value = None
            for key in possible_keys:
                if key in row and row[key]:
                    value = row[key]
                    break
            
            # Convert to appropriate type
            if value is not None and value != '':
                if target_field in ['timestamp', 'bytes', 'sent_bytes', 'grp_threads', 'all_threads']:
                    try:
                        record[target_field] = int(float(value))
                    except (ValueError, TypeError):
                        record[target_field] = 0
                elif target_field in ['latency', 'sample_time', 'connect_time']:
                    try:
                        record[target_field] = float(value)
                    except (ValueError, TypeError):
                        record[target_field] = 0.0
                elif target_field == 'success':
                    record[target_field] = str(value).lower() in ('true', '1', 'yes', 'success')
                else:
                    record[target_field] = str(value).strip()
            else:
                # Set defaults
                if target_field in ['timestamp', 'bytes', 'sent_bytes', 'grp_threads', 'all_threads']:
                    record[target_field] = 0
                elif target_field in ['latency', 'sample_time', 'connect_time']:
                    record[target_field] = 0.0
                elif target_field == 'success':
                    record[target_field] = True
                else:
                    record[target_field] = ''
        
        # Validate required fields
        if not record.get('timestamp') or not record.get('label'):
            return None  # Invalid record
        
        return record
    
    @staticmethod
    def _parse_xml(file_path: Path) -> List[Dict[str, Any]]:
        """Parse XML format JTL file"""
        results = []
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            for sample in root.findall('.//sample'):
                record = {
                    'timestamp': int(float(sample.get('ts', sample.get('t', 0)))),
                    'label': sample.get('lb') or sample.get('label') or '',
                    'response_code': sample.get('rc') or sample.get('responseCode') or '',
                    'response_message': sample.get('rm') or sample.get('responseMessage') or '',
                    'thread_name': sample.get('tn') or sample.get('threadName') or '',
                    'data_type': sample.get('dt') or sample.get('dataType') or '',
                    'success': sample.get('s', 'true').lower() == 'true',
                    'failure_message': sample.get('fm') or sample.get('failureMessage') or '',
                    'bytes': int(float(sample.get('by', sample.get('bytes', 0)))),
                    'sent_bytes': int(float(sample.get('sby', sample.get('sentBytes', 0)))),
                    'grp_threads': int(float(sample.get('ng', sample.get('grpThreads', 0)))),
                    'all_threads': int(float(sample.get('na', sample.get('allThreads', 0)))),
                    'latency': float(sample.get('lt', sample.get('latency', 0))),
                    'sample_time': float(sample.get('t', sample.get('elapsed', sample.get('sampleTime', 0)))),
                    'connect_time': float(sample.get('ct', sample.get('connect', sample.get('connectTime', 0)))),
                }
                results.append(record)
                
        except Exception as e:
            raise ValueError(f"Error parsing XML file {file_path}: {e}")
        
        return results
    
    @staticmethod
    def merge_data(data_lists: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """
        Merge multiple JTL data lists into one
        Simple concatenation - sorting is optional and can be done later if needed
        """
        if not data_lists:
            return []
        
        if len(data_lists) == 1:
            return data_lists[0]
        
        merged = []
        for data_list in data_lists:
            merged.extend(data_list)
        
        return merged


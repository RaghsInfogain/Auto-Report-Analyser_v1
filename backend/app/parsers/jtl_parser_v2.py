"""
Simplified and robust JTL parser for JMeter results
Handles CSV and XML formats efficiently
"""
import csv
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Mapping, Optional
from pathlib import Path

import numpy as np

from app.utils.jmeter_url import normalize_jmeter_url_value

# Canonical JTL/CSV column aliases → standard record keys (shared by DictReader + pandas paths)
FIELD_MAPPING: Mapping[str, List[str]] = {
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
    'url': ['URL', 'url', 'Url'],
    'hostname': ['Hostname', 'hostname', 'host'],
}

# Use vectorized pandas load above this size (CSV only) — much faster than row-wise csv on huge JTLs
PANDAS_CSV_BYTES = 30 * 1024 * 1024


def _resolve_jtl_columns(column_names: List[str]) -> Dict[str, str]:
    colset = set(column_names)
    resolved: Dict[str, str] = {}
    for target_field, possible_keys in FIELD_MAPPING.items():
        for key in possible_keys:
            if key in colset:
                resolved[target_field] = key
                break
    return resolved


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
        """Parse CSV format JTL — pandas for large files, DictReader otherwise."""
        try:
            if file_path.stat().st_size >= PANDAS_CSV_BYTES:
                return JTLParserV2._parse_csv_pandas(file_path)
        except OSError:
            pass
        return JTLParserV2._parse_csv_dict(file_path)

    @staticmethod
    def _parse_csv_dict(file_path: Path) -> List[Dict[str, Any]]:
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
    def _parse_csv_pandas(file_path: Path) -> List[Dict[str, Any]]:
        """Fast path for large CSV JTL using pandas + NumPy (falls back to DictReader if schema unknown)."""
        import pandas as pd

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            first_line = f.readline()
        sep = ',' if ',' in first_line else '\t'

        try:
            df = pd.read_csv(
                file_path,
                sep=sep,
                dtype=str,
                na_filter=False,
                engine='c',
                encoding='utf-8',
                encoding_errors='ignore',
                low_memory=False,
            )
        except Exception:
            return JTLParserV2._parse_csv_dict(file_path)

        df.columns = [str(c).strip() for c in df.columns]
        rmap = _resolve_jtl_columns(list(df.columns))
        if 'timestamp' not in rmap or 'label' not in rmap:
            return JTLParserV2._parse_csv_dict(file_path)

        n = len(df)
        if n == 0:
            return []

        ts = pd.to_numeric(df[rmap['timestamp']], errors='coerce').fillna(0).to_numpy(dtype=np.float64)
        ts_i = ts.astype(np.int64, copy=False)
        lab = df[rmap['label']].astype(str).str.strip().to_numpy()

        def col_int(name: str) -> np.ndarray:
            if name not in rmap:
                return np.zeros(n, dtype=np.int64)
            return pd.to_numeric(df[rmap[name]], errors='coerce').fillna(0).to_numpy(dtype=np.int64)

        def col_float(name: str) -> np.ndarray:
            if name not in rmap:
                return np.zeros(n, dtype=np.float64)
            return pd.to_numeric(df[rmap[name]], errors='coerce').fillna(0.0).to_numpy(dtype=np.float64)

        rc_str = (
            df[rmap['response_code']].astype(str).str.strip().to_numpy()
            if 'response_code' in rmap else np.array([''] * n, dtype=object)
        )

        latency = col_float('latency')
        sample_time = col_float('sample_time')
        connect_time = col_float('connect_time')
        bytes_a = col_int('bytes')
        sent_bytes = col_int('sent_bytes')
        grp_threads = col_int('grp_threads')
        all_threads = col_int('all_threads')

        if 'success' in rmap:
            sv = df[rmap['success']].astype(str).str.lower().str.strip().to_numpy()
            succ = (sv == 'true') | (sv == '1') | (sv == 'yes') | (sv == 'success')
        else:
            succ = np.ones(n, dtype=bool)

        resp_msg = (
            df[rmap['response_message']].astype(str).str.strip().to_numpy()
            if 'response_message' in rmap else np.array([''] * n, dtype=object)
        )
        thread_name = (
            df[rmap['thread_name']].astype(str).str.strip().to_numpy()
            if 'thread_name' in rmap else np.array([''] * n, dtype=object)
        )
        data_type = (
            df[rmap['data_type']].astype(str).str.strip().to_numpy()
            if 'data_type' in rmap else np.array([''] * n, dtype=object)
        )
        failure_message = (
            df[rmap['failure_message']].astype(str).str.strip().to_numpy()
            if 'failure_message' in rmap else np.array([''] * n, dtype=object)
        )
        url_raw = (
            df[rmap['url']].astype(str).str.strip().to_numpy()
            if 'url' in rmap else np.array([''] * n, dtype=object)
        )
        hostname = (
            df[rmap['hostname']].astype(str).str.strip().to_numpy()
            if 'hostname' in rmap else np.array([''] * n, dtype=object)
        )

        ms_col: Optional[str] = None
        if '_merge_source_idx' in df.columns:
            ms_col = '_merge_source_idx'
        elif 'merge_source_idx' in df.columns:
            ms_col = 'merge_source_idx'
        merge_src = None
        if ms_col:
            merge_src = pd.to_numeric(df[ms_col], errors='coerce').fillna(0).to_numpy(dtype=np.int64)

        valid = (ts_i > 0) & (lab != '') & (lab != 'nan')
        idxs = np.nonzero(valid)[0]

        records: List[Dict[str, Any]] = []
        for i in idxs:
            rcode = str(rc_str[i]) if rc_str[i] is not None else ''
            if rcode.lower() in ('nan', 'none'):
                rcode = ''
            rec = {
                'timestamp': int(ts_i[i]),
                'label': str(lab[i]),
                'response_code': rcode,
                'response_message': str(resp_msg[i]) if resp_msg[i] else '',
                'thread_name': str(thread_name[i]) if thread_name[i] else '',
                'data_type': str(data_type[i]) if data_type[i] else '',
                'success': bool(succ[i]),
                'failure_message': str(failure_message[i]) if failure_message[i] else '',
                'bytes': int(bytes_a[i]),
                'sent_bytes': int(sent_bytes[i]),
                'grp_threads': int(grp_threads[i]),
                'all_threads': int(all_threads[i]),
                'latency': float(latency[i]),
                'sample_time': float(sample_time[i]),
                'connect_time': float(connect_time[i]),
                'url': normalize_jmeter_url_value(str(url_raw[i]) if url_raw[i] else ''),
                'hostname': str(hostname[i]) if hostname[i] else '',
            }
            if merge_src is not None:
                rec['_merge_source_idx'] = int(merge_src[i])
            records.append(rec)

        return records

    @staticmethod
    def _normalize_csv_record(row: Dict[str, str]) -> Dict[str, Any]:
        """Normalize CSV row to standard format"""
        record = {}

        for target_field, possible_keys in FIELD_MAPPING.items():
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

        # Literal "null" / "n/a" in CSV is not a real URL (JMeter TC rows)
        record["url"] = normalize_jmeter_url_value(record.get("url", ""))

        if "_merge_source_idx" in row and row.get("_merge_source_idx") not in ("", None):
            try:
                record["_merge_source_idx"] = int(float(row["_merge_source_idx"]))
            except (ValueError, TypeError):
                record["_merge_source_idx"] = 0
        elif "merge_source_idx" in row and row.get("merge_source_idx") not in ("", None):
            try:
                record["_merge_source_idx"] = int(float(row["merge_source_idx"]))
            except (ValueError, TypeError):
                record["_merge_source_idx"] = 0

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
    def merge_data(
        data_lists: List[List[Dict[str, Any]]],
        *,
        tag_source_index: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Merge multiple JMeter JTL/CSV data lists using SIMPLE CONCATENATION.

        When tag_source_index=True, each row gets ``_merge_source_idx`` (0..n-1) so downstream
        analysis can treat files as parallel scenarios (e.g. sum of per-file peak VUsers).
        """
        if not data_lists:
            return []

        if len(data_lists) == 1:
            if not tag_source_index:
                return data_lists[0]
            return [{**dict(d), "_merge_source_idx": 0} for d in data_lists[0]]

        merged: List[Dict[str, Any]] = []
        for i, data_list in enumerate(data_lists):
            for d in data_list:
                row = dict(d)
                if tag_source_index:
                    row["_merge_source_idx"] = i
                merged.append(row)
        return merged

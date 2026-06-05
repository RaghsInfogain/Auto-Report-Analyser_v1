"""JMeter analysis with DB cache and chunked parse for large JTL files."""
from __future__ import annotations

import copy
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.analyzers.jmeter_analyzer_v2 import JMeterAnalyzerV2
from app.database.models import UploadedFile
from app.database.run_analysis_cache import (
    RunAnalysisCacheService,
    build_sources_fingerprint,
    resolve_primary_jmeter_file,
)
from app.database.service import DatabaseService
from app.parsers.jtl_parser_v2 import JTLParserV2, LARGE_FILE_SKIP_FULL_PARSE_BYTES
from app.parsers.json_parser import JSONParser

LARGE_BYTES = LARGE_FILE_SKIP_FULL_PARSE_BYTES
MAX_ANALYZE_ROWS = 2_000_000
CHUNK_ROWS = 200_000


def extract_base_url_from_metrics(metrics: Dict[str, Any]) -> Optional[str]:
    summary = metrics.get("summary") or {}
    if summary.get("base_url"):
        return str(summary["base_url"])
    header = metrics.get("report_header") or {}
    if header.get("application_name"):
        return str(header["application_name"])
    return None


def _parse_large_csv_capped(path: str) -> List[Dict[str, Any]]:
    import pandas as pd

    p = Path(path)
    with open(p, "r", encoding="utf-8", errors="ignore") as f:
        first = f.readline()
    sep = "," if "," in first else "\t"
    rows: List[Dict[str, Any]] = []
    for chunk in pd.read_csv(
        p,
        sep=sep,
        dtype=str,
        na_filter=False,
        chunksize=CHUNK_ROWS,
        encoding="utf-8",
        encoding_errors="ignore",
        low_memory=False,
    ):
        chunk.columns = [str(c).strip() for c in chunk.columns]
        for _, row in chunk.iterrows():
            rows.append(dict(row))
            if len(rows) >= MAX_ANALYZE_ROWS:
                return rows
    return rows


def parse_jmeter_file(path: str) -> List[Dict[str, Any]]:
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(path)
    ext = p.suffix.lower()
    if ext == ".json":
        return JSONParser.parse(str(p), "jmeter")
    if ext == ".xml":
        return JTLParserV2.parse(str(p))
    size = p.stat().st_size
    if size >= LARGE_BYTES:
        return _parse_large_csv_capped(str(p))
    return JTLParserV2.parse(str(p))


def analyze_jmeter_path(
    path: str,
    *,
    run_targets: Optional[Dict[str, float]] = None,
    application_display_name: Optional[str] = None,
    merged_source_filenames: Optional[List[str]] = None,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> Tuple[Dict[str, Any], int]:
    if progress_callback:
        progress_callback(f"Parsing {Path(path).name}…")
    data = parse_jmeter_file(path)
    if progress_callback:
        progress_callback(f"Analyzing {len(data):,} records…")
    metrics_obj = JMeterAnalyzerV2.analyze(
        data,
        targets=run_targets,
        application_display_name=application_display_name,
        merged_source_filenames=merged_source_filenames,
    )
    metrics = metrics_obj.dict()
    return metrics, len(data)


def try_load_cached_jmeter_metrics(
    db: Session,
    run_id: str,
    category_files: List[UploadedFile],
    regenerate: bool,
) -> Optional[Dict[str, Any]]:
    if regenerate:
        return None
    primary, path = resolve_primary_jmeter_file(category_files, run_id)
    if not primary or not path:
        return None
    row = RunAnalysisCacheService.get(db, run_id, "jmeter")
    if RunAnalysisCacheService.is_valid(row, path):
        print(f"  ✓ Using cached JMeter metrics for {run_id}")
        return copy.deepcopy(row.metrics)
    existing = DatabaseService.get_analysis_result(db, primary.file_id)
    if existing and existing.metrics:
        print(f"  ✓ Backfilling JMeter cache from analysis_results for {run_id}")
        metrics = copy.deepcopy(existing.metrics)
        persist_jmeter_cache(
            db,
            run_id,
            category_files,
            metrics,
            sample_count=primary.record_count or metrics.get("total_samples", 0),
            source_path=path,
            primary_file=primary,
        )
        return metrics
    return None


def persist_jmeter_cache(
    db: Session,
    run_id: str,
    category_files: List[UploadedFile],
    metrics: Dict[str, Any],
    *,
    sample_count: int = 0,
    source_path: Optional[str] = None,
    primary_file: Optional[UploadedFile] = None,
    analysis_duration: Optional[float] = None,
) -> None:
    primary, path = resolve_primary_jmeter_file(category_files, run_id)
    if primary_file:
        primary = primary_file
    if source_path:
        path = source_path
    if not primary or not path:
        return
    fp = build_sources_fingerprint([path])
    RunAnalysisCacheService.save(
        db,
        run_id=run_id,
        category="jmeter",
        file_id=primary.file_id,
        source_path=path,
        metrics=metrics,
        sample_count=sample_count or metrics.get("total_samples", 0),
        base_url=extract_base_url_from_metrics(metrics),
        analysis_duration=analysis_duration,
        fingerprint=fp,
    )


def apply_cached_jmeter_to_run(
    db: Session,
    run_id: str,
    category_files: List[UploadedFile],
    metrics: Dict[str, Any],
    start_time: float,
) -> Dict[str, Any]:
    """Sync analysis_results + all_metrics shape from cached metrics."""
    import copy as _copy

    primary, path = resolve_primary_jmeter_file(category_files, run_id)
    if not primary:
        primary = category_files[0]
    m = _copy.deepcopy(metrics)
    sample_count = m.get("total_samples") or primary.record_count or 0
    for db_file in category_files:
        existing = DatabaseService.get_analysis_result(db, db_file.file_id)
        if existing:
            existing.metrics = m
            existing.analyzed_at = __import__("datetime").datetime.utcnow()
            existing.analysis_duration = time.time() - start_time
        else:
            DatabaseService.create_analysis_result(
                db=db,
                file_id=db_file.file_id,
                category="jmeter",
                metrics=m,
                analysis_duration=time.time() - start_time,
            )
        db_file.record_count = sample_count
    db.commit()
    return {
        "file_id": primary.file_id,
        "filename": primary.filename,
        "category": "jmeter",
        "metrics": m,
        "source_path": path,
        "sample_count": sample_count,
    }

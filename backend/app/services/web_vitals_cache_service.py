"""Web Vitals / Lighthouse analysis cache."""
from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.models import UploadedFile
from app.database.run_analysis_cache import (
    RunAnalysisCacheService,
    build_sources_fingerprint,
    resolve_category_source_paths,
)
from app.database.service import DatabaseService


def try_load_cached_web_vitals_metrics(
    db: Session,
    run_id: str,
    category_files: List[UploadedFile],
    regenerate: bool,
) -> Optional[Dict[str, Any]]:
    if regenerate:
        return None
    paths = resolve_category_source_paths(category_files, run_id)
    if not paths:
        return None
    fp = build_sources_fingerprint(paths, extra={"category": "web_vitals"})
    row = RunAnalysisCacheService.get(db, run_id, "web_vitals")
    if RunAnalysisCacheService.is_valid_fingerprint(row, fp):
        print(f"  ✓ Using cached Web Vitals metrics for {run_id}")
        return copy.deepcopy(row.metrics)
    lighthouse_files = [f for f in category_files if f.file_path.endswith(".json")]
    if lighthouse_files:
        existing = DatabaseService.get_analysis_result(db, lighthouse_files[0].file_id)
        if existing and existing.metrics:
            print(f"  ✓ Backfilling Web Vitals cache from analysis_results for {run_id}")
            metrics = copy.deepcopy(existing.metrics)
            persist_web_vitals_cache(db, run_id, category_files, metrics)
            return metrics
    return None


def persist_web_vitals_cache(
    db: Session,
    run_id: str,
    category_files: List[UploadedFile],
    metrics: Dict[str, Any],
    *,
    sample_count: int = 0,
    analysis_duration: Optional[float] = None,
) -> None:
    paths = resolve_category_source_paths(category_files, run_id)
    if not paths:
        return
    primary = category_files[0]
    fp = build_sources_fingerprint(paths, extra={"category": "web_vitals"})
    RunAnalysisCacheService.save(
        db,
        run_id=run_id,
        category="web_vitals",
        file_id=primary.file_id,
        source_path=paths[0],
        metrics=metrics,
        sample_count=sample_count or len(metrics.get("page_data", [])),
        base_url=None,
        analysis_duration=analysis_duration,
        fingerprint=fp,
    )


def apply_cached_web_vitals_to_run(
    db: Session,
    run_id: str,
    category_files: List[UploadedFile],
    metrics: Dict[str, Any],
    start_time: float,
) -> Dict[str, Any]:
    import time

    m = copy.deepcopy(metrics)
    lighthouse_files = [f for f in category_files if f.file_path.endswith(".json")]
    file_count = len(lighthouse_files) or len(category_files)
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
                category="web_vitals",
                metrics=m,
                analysis_duration=time.time() - start_time,
            )
        db_file.record_count = file_count
    db.commit()
    primary = lighthouse_files[0] if lighthouse_files else category_files[0]
    return {
        "file_id": primary.file_id,
        "filename": primary.filename,
        "category": "web_vitals",
        "metrics": m,
        "sample_count": file_count,
    }

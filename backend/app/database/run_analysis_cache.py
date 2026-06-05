"""Unified run-level analysis cache (JMeter, Web Vitals) and comparison cache."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Session

from .models import Base, UploadedFile


class RunAnalysisCache(Base):
    __tablename__ = "run_analysis_cache"
    __table_args__ = (UniqueConstraint("run_id", "category", name="uq_run_analysis_cache_run_category"),)

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(100), index=True, nullable=False)
    category = Column(String(50), index=True, nullable=False)
    file_id = Column(String(100), nullable=False)
    source_path = Column(String(500), nullable=False)
    source_size = Column(Integer, default=0)
    source_mtime = Column(Float, default=0.0)
    source_fingerprint = Column(String(128), nullable=True)
    sample_count = Column(Integer, default=0)
    base_url = Column(String(500), nullable=True)
    metrics = Column(JSON, nullable=False)
    analyzed_at = Column(DateTime, default=datetime.utcnow)
    analysis_duration = Column(Float, nullable=True)


class ComparisonAnalysisCache(Base):
    __tablename__ = "comparison_analysis_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(128), unique=True, index=True, nullable=False)
    source_fingerprint = Column(String(128), nullable=True)
    comparison_type = Column(String(50), nullable=False)
    run_id_a = Column(String(100), nullable=True)
    run_id_b = Column(String(100), nullable=True)
    name_a = Column(String(255), nullable=True)
    name_b = Column(String(255), nullable=True)
    payload = Column(JSON, nullable=False)
    html_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def file_stat_fingerprint(path: str) -> Tuple[int, float]:
    try:
        st = os.stat(path)
        return int(st.st_size), float(st.st_mtime)
    except OSError:
        return 0, 0.0


def build_sources_fingerprint(paths: List[str], *, extra: Optional[Dict[str, Any]] = None) -> str:
    parts: List[str] = []
    for p in sorted(set(paths)):
        size, mtime = file_stat_fingerprint(p)
        parts.append(f"{p}|{size}|{mtime:.3f}")
    if extra:
        parts.append(json.dumps(extra, sort_keys=True, default=str))
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def resolve_primary_jmeter_file(
    category_files: List[UploadedFile],
    run_id: str,
) -> Tuple[Optional[UploadedFile], Optional[str]]:
    from app.utils.storage_paths import resolve_storage_path

    if not category_files:
        return None, None
    first = category_files[0]
    is_merged = len(category_files) > 1 and (
        "merged" in (first.file_path or "").lower()
        or "merged" in (first.filename or "").lower()
    )
    primary = first
    if is_merged:
        for f in category_files:
            if "merged" in (f.file_path or "").lower():
                primary = f
                break
    resolved = resolve_storage_path(
        primary.file_path,
        run_id=run_id,
        file_id=primary.file_id,
        filename=primary.filename,
    )
    return primary, resolved


def resolve_category_source_paths(category_files: List[UploadedFile], run_id: str) -> List[str]:
    from app.utils.storage_paths import resolve_storage_path

    paths: List[str] = []
    for f in category_files:
        p = resolve_storage_path(f.file_path, run_id=run_id, file_id=f.file_id, filename=f.filename)
        if p:
            paths.append(p)
    return paths


class RunAnalysisCacheService:
    @staticmethod
    def get(db: Session, run_id: str, category: str) -> Optional[RunAnalysisCache]:
        return (
            db.query(RunAnalysisCache)
            .filter(RunAnalysisCache.run_id == run_id, RunAnalysisCache.category == category)
            .first()
        )

    @staticmethod
    def is_valid(row: Optional[RunAnalysisCache], source_path: str, fingerprint: Optional[str] = None) -> bool:
        if not row or not row.metrics:
            return False
        size, mtime = file_stat_fingerprint(source_path)
        if size <= 0:
            return False
        if fingerprint and row.source_fingerprint and row.source_fingerprint != fingerprint:
            return False
        return (
            row.source_path == source_path
            and row.source_size == size
            and abs((row.source_mtime or 0) - mtime) < 1.0
        )

    @staticmethod
    def is_valid_fingerprint(row: Optional[RunAnalysisCache], fingerprint: str) -> bool:
        return bool(row and row.metrics and row.source_fingerprint == fingerprint)

    @staticmethod
    def save(
        db: Session,
        *,
        run_id: str,
        category: str,
        file_id: str,
        source_path: str,
        metrics: Dict[str, Any],
        sample_count: int = 0,
        base_url: Optional[str] = None,
        analysis_duration: Optional[float] = None,
        fingerprint: Optional[str] = None,
    ) -> RunAnalysisCache:
        size, mtime = file_stat_fingerprint(source_path)
        row = RunAnalysisCacheService.get(db, run_id, category)
        if row:
            row.file_id = file_id
            row.source_path = source_path
            row.source_size = size
            row.source_mtime = mtime
            row.source_fingerprint = fingerprint
            row.sample_count = sample_count
            row.base_url = base_url
            row.metrics = metrics
            row.analyzed_at = datetime.utcnow()
            row.analysis_duration = analysis_duration
        else:
            row = RunAnalysisCache(
                run_id=run_id,
                category=category,
                file_id=file_id,
                source_path=source_path,
                source_size=size,
                source_mtime=mtime,
                source_fingerprint=fingerprint,
                sample_count=sample_count,
                base_url=base_url,
                metrics=metrics,
                analysis_duration=analysis_duration,
            )
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_for_run(db: Session, run_id: str, category: Optional[str] = None) -> None:
        q = db.query(RunAnalysisCache).filter(RunAnalysisCache.run_id == run_id)
        if category:
            q = q.filter(RunAnalysisCache.category == category)
        for row in q.all():
            db.delete(row)
        db.commit()

    @staticmethod
    def get_base_url(db: Session, run_id: str, category: str = "jmeter") -> Optional[str]:
        row = RunAnalysisCacheService.get(db, run_id, category)
        return (row.base_url or None) if row else None


class ComparisonCacheService:
    @staticmethod
    def build_cache_key(
        comparison_type: str,
        run_id_a: Optional[str],
        run_id_b: Optional[str],
        *,
        name_a: str = "",
        name_b: str = "",
    ) -> str:
        payload = {
            "type": comparison_type,
            "a": run_id_a,
            "b": run_id_b,
            "name_a": name_a,
            "name_b": name_b,
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    @staticmethod
    def build_comparison_fingerprint(
        *,
        run_id_a: Optional[str],
        run_id_b: Optional[str],
        path_a: Optional[str],
        path_b: Optional[str],
        db: Optional[Session] = None,
    ) -> str:
        paths: List[str] = []
        if path_a:
            paths.append(path_a)
        if path_b:
            paths.append(path_b)
        if db and run_id_a and run_id_b:
            from app.database.service import DatabaseService

            for rid in (run_id_a, run_id_b):
                for f in DatabaseService.get_files_by_run_id(db, rid):
                    if f.category == "jmeter":
                        from app.utils.storage_paths import resolve_storage_path

                        rp = resolve_storage_path(f.file_path, run_id=rid, file_id=f.file_id, filename=f.filename)
                        if rp:
                            paths.append(rp)
        return build_sources_fingerprint(paths, extra={"run_a": run_id_a, "run_b": run_id_b})

    @staticmethod
    def get(db: Session, cache_key: str) -> Optional[ComparisonAnalysisCache]:
        return db.query(ComparisonAnalysisCache).filter(ComparisonAnalysisCache.cache_key == cache_key).first()

    @staticmethod
    def get_valid(db: Session, cache_key: str, fingerprint: str) -> Optional[Dict[str, Any]]:
        row = ComparisonCacheService.get(db, cache_key)
        if not row or not row.payload:
            return None
        if row.source_fingerprint and row.source_fingerprint != fingerprint:
            return None
        return row.payload if isinstance(row.payload, dict) else None

    @staticmethod
    def save(
        db: Session,
        *,
        cache_key: str,
        fingerprint: str,
        comparison_type: str,
        payload: Dict[str, Any],
        run_id_a: Optional[str] = None,
        run_id_b: Optional[str] = None,
        name_a: Optional[str] = None,
        name_b: Optional[str] = None,
        html_path: Optional[str] = None,
    ) -> ComparisonAnalysisCache:
        row = ComparisonCacheService.get(db, cache_key)
        if row:
            row.source_fingerprint = fingerprint
            row.payload = payload
            row.html_path = html_path
            row.created_at = datetime.utcnow()
        else:
            row = ComparisonAnalysisCache(
                cache_key=cache_key,
                source_fingerprint=fingerprint,
                comparison_type=comparison_type,
                run_id_a=run_id_a,
                run_id_b=run_id_b,
                name_a=name_a,
                name_b=name_b,
                payload=payload,
                html_path=html_path,
            )
            db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def invalidate_runs(db: Session, *run_ids: str) -> None:
        if not run_ids:
            return
        ids = set(run_ids)
        for row in db.query(ComparisonAnalysisCache).all():
            if row.run_id_a in ids or row.run_id_b in ids:
                db.delete(row)
        db.commit()

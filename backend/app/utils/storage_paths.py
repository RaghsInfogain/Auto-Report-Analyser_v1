"""Resolve persisted storage paths after repo moves or directory renames."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable, List, Optional

# backend/app/utils/storage_paths.py -> backend/
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BACKEND_DIR / "uploads"
MERGED_DIR = BACKEND_DIR / "merged"
REPORTS_DIR = BACKEND_DIR / "reports"

# Known legacy backend roots (e.g. repo moved under FY-26).
_LEGACY_BACKEND_ROOTS: tuple[Path, ...] = (
    Path("/Users/raghvendrakumar/Documents/Solution Development -Repos/Auto-Report-Analyser_v1/backend"),
)


def _candidate_paths(stored_path: str) -> List[Path]:
    """Build candidate absolute paths for a stored path."""
    original = Path(stored_path)
    candidates: List[Path] = [original]
    stored = str(original)

    for legacy_root in _LEGACY_BACKEND_ROOTS:
        legacy = str(legacy_root)
        if stored.startswith(legacy):
            suffix = stored[len(legacy) :].lstrip(os.sep)
            candidates.append(BACKEND_DIR / suffix)

    normalized = stored.replace("\\", "/")
    marker = "/backend/"
    if marker in normalized:
        suffix = normalized.rsplit(marker, 1)[1]
        candidates.append(BACKEND_DIR / suffix)

    seen: set[str] = set()
    unique: List[Path] = []
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def resolve_storage_path(
    stored_path: Optional[str],
    *,
    run_id: Optional[str] = None,
    file_id: Optional[str] = None,
    filename: Optional[str] = None,
) -> Optional[str]:
    """Return an existing on-disk path for a stored DB path, or None."""
    if stored_path:
        for candidate in _candidate_paths(stored_path):
            if candidate.is_file():
                return str(candidate.resolve())

    if run_id:
        merged = MERGED_DIR / f"{run_id}_merged.jtl"
        if merged.is_file():
            return str(merged.resolve())

    if file_id and UPLOAD_DIR.is_dir():
        extensions: List[str] = []
        if filename:
            ext = Path(filename).suffix
            if ext:
                extensions.append(ext)
        extensions.extend([".jtl", ".csv", ".json"])

        seen_ext: set[str] = set()
        for ext in extensions:
            if ext in seen_ext:
                continue
            seen_ext.add(ext)
            candidate = UPLOAD_DIR / f"{file_id}{ext}"
            if candidate.is_file():
                return str(candidate.resolve())

        for match in UPLOAD_DIR.glob(f"{file_id}*"):
            if match.is_file():
                return str(match.resolve())

    return None


def repair_persisted_paths(db) -> dict:
    """
    Rewrite stored paths in the DB when files exist under the current backend root.
    Returns counts of repaired rows.
    """
    from app.database.models import JmeterComparisonReport, UploadedFile

    stats = {"uploaded_files": 0, "comparison_reports": 0}

    for row in db.query(UploadedFile).all():
        resolved = resolve_storage_path(
            row.file_path,
            run_id=row.run_id,
            file_id=row.file_id,
            filename=row.filename,
        )
        if resolved and resolved != row.file_path:
            row.file_path = resolved
            stats["uploaded_files"] += 1

    for row in db.query(JmeterComparisonReport).all():
        resolved = resolve_storage_path(row.html_path)
        if resolved and resolved != row.html_path:
            row.html_path = resolved
            stats["comparison_reports"] += 1

    if stats["uploaded_files"] or stats["comparison_reports"]:
        db.commit()
        print(
            "Repaired persisted paths: "
            f"{stats['uploaded_files']} uploaded file(s), "
            f"{stats['comparison_reports']} comparison report(s)"
        )

    return stats

"""Large-file upload helpers: streaming save, JMeter finalize, record estimates."""
from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database.service import DatabaseService
from app.database.models import UploadedFile
from app.parsers.jtl_parser_v2 import JTLParserV2, LARGE_FILE_SKIP_FULL_PARSE_BYTES
from app.parsers.json_parser import JSONParser
from app.utils.upload_progress_tracker import UploadProgressTracker

# Partial uploads keyed by upload_id
_partial_paths: Dict[str, Dict[str, Any]] = {}


def register_partial_upload(
    upload_id: str,
    *,
    partial_path: Path,
    final_path: Path,
    run_id: str,
    file_id: str,
    filename: str,
    category: str,
    total_bytes: int,
) -> None:
    _partial_paths[upload_id] = {
        "partial_path": partial_path,
        "final_path": final_path,
        "run_id": run_id,
        "file_id": file_id,
        "filename": filename,
        "category": category,
        "total_bytes": total_bytes,
    }


def get_partial_upload(upload_id: str) -> Optional[Dict[str, Any]]:
    return _partial_paths.get(upload_id)


def pop_partial_upload(upload_id: str) -> Optional[Dict[str, Any]]:
    return _partial_paths.pop(upload_id, None)


async def stream_save_upload(
    upload_file: UploadFile,
    dest: Path,
    *,
    upload_id: Optional[str] = None,
    total_bytes: Optional[int] = None,
    chunk_size: int = 8 * 1024 * 1024,
    append: bool = False,
) -> int:
    """Write upload stream to disk in chunks; update upload progress when upload_id set."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    mode = "ab" if append else "wb"
    base_size = dest.stat().st_size if append and dest.is_file() else 0
    written = 0
    with open(dest, mode) as out:
        while True:
            chunk = await upload_file.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            written += len(chunk)
            if upload_id:
                UploadProgressTracker.update(upload_id, base_size + written)
    if upload_id and total_bytes and base_size + written < total_bytes:
        UploadProgressTracker.update(upload_id, base_size + written, "Upload received; finalizing…")
    return written


def estimate_jmeter_record_count(file_path: Path) -> int:
    ext = file_path.suffix.lower()
    try:
        if ext in (".jtl", ".csv"):
            size = file_path.stat().st_size
            if size >= LARGE_FILE_SKIP_FULL_PARSE_BYTES:
                return JTLParserV2.estimate_record_count(str(file_path))
            data = JTLParserV2.parse(str(file_path))
            return len(data)
        data = JSONParser.parse(str(file_path), "jmeter")
        return len(data)
    except Exception as e:
        print(f"  Warning: could not count records for {file_path.name}: {e}")
        if ext in (".jtl", ".csv"):
            return JTLParserV2.estimate_record_count(str(file_path))
        return 0


def finalize_jmeter_run(db: Session, run_id: str, upload_dir: Path, merged_dir: Path) -> None:
    """Post-upload JMeter merge / record counts (no full parse for large files)."""
    files = [
        f
        for f in DatabaseService.get_files_by_run_id(db, run_id)
        if f.category == "jmeter"
    ]
    if not files:
        return

    if len(files) > 1:
        paths = []
        names = []
        for f in files:
            p = Path(f.file_path)
            if p.is_file():
                paths.append(str(p))
                names.append(f.filename)
        if not paths:
            raise HTTPException(status_code=400, detail="JMeter files missing on disk")

        merged_dir.mkdir(parents=True, exist_ok=True)
        merged_path = merged_dir / f"{run_id}_merged.jtl"
        total_size = sum(Path(p).stat().st_size for p in paths)
        if total_size >= LARGE_FILE_SKIP_FULL_PARSE_BYTES:
            record_count = JTLParserV2.concatenate_files_on_disk(paths, str(merged_path))
        else:
            all_data = []
            for p in paths:
                if p.endswith((".jtl", ".csv")):
                    all_data.append(JTLParserV2.parse(p))
                else:
                    all_data.append(JSONParser.parse(p, "jmeter"))
            merged_data = JTLParserV2.merge_data(all_data, tag_source_index=True)
            import pandas as pd

            pd.DataFrame(merged_data).to_csv(merged_path, index=False)
            record_count = len(merged_data)

        merged_name = f"MERGED_{run_id}_{'+'.join(names[:3])}{'...' if len(names) > 3 else ''}"
        for f in files:
            f.file_path = str(merged_path)
            f.filename = merged_name
            f.file_size = merged_path.stat().st_size
            f.record_count = record_count
        db.commit()
        print(f"✓ Merged {len(files)} JMeter files → {merged_path} (~{record_count:,} rows est.)")
        return

    f = files[0]
    path = Path(f.file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail=f"Uploaded file not found: {path}")
    f.record_count = estimate_jmeter_record_count(path)
    f.file_size = path.stat().st_size
    db.commit()
    print(f"✓ Single JMeter file ready: {path.name} (~{f.record_count:,} rows est.)")

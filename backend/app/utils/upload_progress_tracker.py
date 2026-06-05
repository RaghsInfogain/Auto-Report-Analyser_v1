"""In-memory progress for large chunked file uploads."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Optional
import uuid


_upload_store: Dict[str, Dict] = {}

# 50 GB per file (supports 30–40 GB user payloads)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024 * 1024
CHUNK_SIZE_BYTES = 32 * 1024 * 1024  # client hint


class UploadProgressTracker:
    @staticmethod
    def create(
        *,
        filename: str,
        category: str,
        total_bytes: int,
        run_id: str,
        file_id: str,
    ) -> str:
        upload_id = str(uuid.uuid4())
        _upload_store[upload_id] = {
            "upload_id": upload_id,
            "filename": filename,
            "category": category,
            "total_bytes": total_bytes,
            "bytes_written": 0,
            "run_id": run_id,
            "file_id": file_id,
            "status": "in_progress",
            "message": "Starting upload…",
            "started_at": datetime.utcnow().isoformat(),
            "last_updated": datetime.utcnow().isoformat(),
            "completed_at": None,
        }
        return upload_id

    @staticmethod
    def update(upload_id: str, bytes_written: int, message: Optional[str] = None) -> Optional[Dict]:
        entry = _upload_store.get(upload_id)
        if not entry:
            return None
        entry["bytes_written"] = min(bytes_written, entry["total_bytes"])
        total = entry["total_bytes"] or 1
        pct = int((entry["bytes_written"] / total) * 100)
        entry["progress_percent"] = min(100, pct)
        if message:
            entry["message"] = message
        else:
            mb_done = entry["bytes_written"] / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            entry["message"] = f"Uploading {entry['filename']}: {mb_done:.1f} / {mb_total:.1f} MB"
        entry["last_updated"] = datetime.utcnow().isoformat()
        return entry

    @staticmethod
    def complete(upload_id: str, message: str = "Upload complete") -> Optional[Dict]:
        entry = _upload_store.get(upload_id)
        if not entry:
            return None
        entry["status"] = "completed"
        entry["bytes_written"] = entry["total_bytes"]
        entry["progress_percent"] = 100
        entry["message"] = message
        entry["completed_at"] = datetime.utcnow().isoformat()
        entry["last_updated"] = datetime.utcnow().isoformat()
        return entry

    @staticmethod
    def fail(upload_id: str, error_message: str) -> Optional[Dict]:
        entry = _upload_store.get(upload_id)
        if not entry:
            return None
        entry["status"] = "failed"
        entry["message"] = error_message
        entry["completed_at"] = datetime.utcnow().isoformat()
        entry["last_updated"] = datetime.utcnow().isoformat()
        return entry

    @staticmethod
    def get(upload_id: str) -> Optional[Dict]:
        return _upload_store.get(upload_id)

    @staticmethod
    def cleanup_old(max_age_hours: int = 24) -> None:
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        remove = []
        for uid, entry in _upload_store.items():
            lu = datetime.fromisoformat(entry["last_updated"])
            if lu < cutoff and entry["status"] in ("completed", "failed"):
                remove.append(uid)
        for uid in remove:
            del _upload_store[uid]

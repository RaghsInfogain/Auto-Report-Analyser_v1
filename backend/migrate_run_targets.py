#!/usr/bin/env python3
"""
Database Migration Script for Run Targets Table
Creates run_targets table for storing SLA/target values per run
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from app.database import DATABASE_URL
from app.database.models import Base, RunTarget


def migrate_run_targets():
    """Create run_targets table"""
    print("=" * 60)
    print("Run Targets Table Migration")
    print("=" * 60)
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    RunTarget.__table__.create(bind=engine, checkfirst=True)
    print("✅ Created table: run_targets")
    print("=" * 60)


if __name__ == "__main__":
    migrate_run_targets()

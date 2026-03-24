#!/usr/bin/env python3
"""
Validate that comparison-related tables exist and show row counts.
Run from backend directory: python validate_comparison_tables.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from app.database import DATABASE_URL, engine
from sqlalchemy import text

REQUIRED_TABLES = [
    "baseline_runs",
    "baseline_metrics",
    "comparison_results",
    "regression_details",
]


def validate():
    print("=" * 60)
    print("Comparison tables validation")
    print("=" * 60)
    print(f"Database: {DATABASE_URL.split('/')[-1] if '/' in DATABASE_URL else DATABASE_URL}")
    print()

    with engine.connect() as conn:
        # List all tables
        if "sqlite" in DATABASE_URL:
            result = conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ))
        else:
            result = conn.execute(text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
            ))
        existing_tables = [row[0] for row in result]

    missing = [t for t in REQUIRED_TABLES if t not in existing_tables]
    if missing:
        print("MISSING TABLES:", missing)
        print()
        print("Run the migration to create them:")
        print("  python migrate_comparison_tables.py")
        print("  (Answer 'yes' when prompted)")
        return False

    print("All comparison tables exist:")
    print()
    with engine.connect() as conn:
        for table in REQUIRED_TABLES:
            try:
                r = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = r.scalar()
                print(f"  {table}: {count} row(s)")
            except Exception as e:
                print(f"  {table}: ERROR - {e}")

    print()
    print("Runs in uploaded_files (available for baseline):")
    with engine.connect() as conn:
        r = conn.execute(text(
            "SELECT COUNT(DISTINCT run_id) FROM uploaded_files"
        ))
        run_count = r.scalar()
        print(f"  Distinct run_id count: {run_count}")
    print()
    print("=" * 60)
    print("Validation complete.")
    print("=" * 60)
    if run_count == 0:
        print()
        print("No runs in DB yet. Upload files first, then create a baseline.")
    elif run_count > 0:
        print()
        print("If the baseline dropdown is still empty, check:")
        print("  1. Frontend is calling the same backend (e.g. http://localhost:8000/api/runs)")
        print("  2. Browser console for CORS or network errors")
    return True


if __name__ == "__main__":
    try:
        ok = validate()
        sys.exit(0 if ok else 1)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

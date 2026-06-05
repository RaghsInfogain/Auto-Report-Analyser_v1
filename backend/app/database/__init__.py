"""Database initialization and connection management"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path

from .models import Base

# Database configuration - use absolute path for persistence
_db_path = Path(__file__).parent.parent.parent / "performance_analyzer.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{_db_path.absolute()}")

# Create engine
if DATABASE_URL.startswith("sqlite"):
    # SQLite configuration with timeout to prevent hangs
    # SQLite doesn't support QueuePool - use StaticPool or NullPool
    engine = create_engine(
        DATABASE_URL,
        connect_args={
            "check_same_thread": False,
            "timeout": 30.0  # 30 second timeout for individual queries
        },
        poolclass=StaticPool,  # SQLite requires StaticPool
        pool_pre_ping=True,  # Verify connections before using
        echo=False  # Set to True for SQL debugging
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """Initialize database tables"""
    from app.database import run_analysis_cache  # noqa: F401 — register cache tables

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_schema_patches()
    _repair_persisted_storage_paths()


def _repair_persisted_storage_paths():
    """Fix stored file paths when the repo was moved on disk."""
    try:
        from app.utils.storage_paths import repair_persisted_paths

        db = SessionLocal()
        try:
            repair_persisted_paths(db)
        finally:
            db.close()
    except Exception as e:
        print(f"Warning: could not repair persisted storage paths: {e}")


def _ensure_sqlite_schema_patches():
    """Lightweight migrations for SQLite when models gain columns."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(run_targets)")).fetchall()
        col_names = {r[1] for r in rows}
        if "application_name" not in col_names:
            conn.execute(text("ALTER TABLE run_targets ADD COLUMN application_name VARCHAR(500)"))

def get_db() -> Session:
    """Dependency for getting database session with proper error handling"""
    db = SessionLocal()
    try:
        yield db
        db.commit()  # Commit successful transactions
    except Exception as e:
        db.rollback()  # Rollback on error
        raise
    finally:
        db.close()  # Always close the session













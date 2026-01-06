"""Database initialization and connection management"""
from sqlalchemy import create_engine
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
    Base.metadata.create_all(bind=engine)

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













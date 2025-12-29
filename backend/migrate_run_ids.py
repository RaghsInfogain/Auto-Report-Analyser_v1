#!/usr/bin/env python3
"""
Migration script to convert existing Run IDs to sequential format (Run-1, Run-2, etc.)
Oldest run will be Run-1, second oldest will be Run-2, and so on.
"""
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from app.database.models import Base, UploadedFile
from app.database import DATABASE_URL

def migrate_run_ids():
    """Migrate existing run IDs to sequential format"""
    
    # Create database engine and session
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("Run ID Migration Script")
        print("=" * 60)
        print("\nThis will convert all existing Run IDs to sequential format.")
        print("Oldest run will become 'Run-1', second oldest 'Run-2', etc.\n")
        
        # Get all unique run_ids ordered by their oldest upload timestamp
        runs = db.query(
            UploadedFile.run_id,
            func.min(UploadedFile.uploaded_at).label('oldest_upload'),
            func.count(UploadedFile.file_id).label('file_count')
        ).group_by(UploadedFile.run_id).order_by(func.min(UploadedFile.uploaded_at).asc()).all()
        
        if not runs:
            print("✅ No runs found in database. Nothing to migrate.")
            return
        
        print(f"Found {len(runs)} unique Run IDs to migrate:\n")
        
        # Create mapping of old run_id to new run_id
        run_mapping = {}
        for index, run in enumerate(runs, start=1):
            old_run_id = run.run_id
            new_run_id = f"Run-{index}"
            run_mapping[old_run_id] = new_run_id
            
            print(f"  {old_run_id:50} → {new_run_id:10} ({run.file_count} files)")
        
        print(f"\n{'=' * 60}")
        confirmation = input("\nProceed with migration? (yes/no): ").strip().lower()
        
        if confirmation != "yes":
            print("\n❌ Migration cancelled.")
            return
        
        print("\n🔄 Starting migration...\n")
        
        # Update run_ids in database
        updated_count = 0
        for old_run_id, new_run_id in run_mapping.items():
            # Update all files with this run_id
            files = db.query(UploadedFile).filter(UploadedFile.run_id == old_run_id).all()
            for file in files:
                file.run_id = new_run_id
                updated_count += 1
        
        # Commit all changes
        db.commit()
        
        print(f"✅ Successfully migrated {updated_count} file records")
        print(f"✅ Converted {len(run_mapping)} unique Run IDs to sequential format")
        print("\nMigration complete! 🎉")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error during migration: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_run_ids()






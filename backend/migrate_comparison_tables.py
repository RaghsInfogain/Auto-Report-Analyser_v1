#!/usr/bin/env python3
"""
Database Migration Script for Performance Comparison Tables
Creates new tables: baseline_runs, baseline_metrics, comparison_results, regression_details
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import create_engine
from app.database import DATABASE_URL
from app.database.models import Base, BaselineRun, BaselineMetric, ComparisonResult, RegressionDetail

def migrate_comparison_tables():
    """Create comparison tables"""
    
    print("=" * 70)
    print("Performance Comparison Tables Migration")
    print("=" * 70)
    print()
    print("This script will create the following tables:")
    print("  - baseline_runs")
    print("  - baseline_metrics")
    print("  - comparison_results")
    print("  - regression_details")
    print()
    
    confirmation = input("Proceed with migration? (yes/no): ").strip().lower()
    
    if confirmation != "yes":
        print("\n❌ Migration cancelled.")
        return
    
    print("\n🔄 Creating tables...\n")
    
    try:
        # Create engine
        engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
        
        # Create only the new comparison tables
        # This will not affect existing tables
        BaselineRun.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created table: baseline_runs")
        
        BaselineMetric.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created table: baseline_metrics")
        
        ComparisonResult.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created table: comparison_results")
        
        RegressionDetail.__table__.create(bind=engine, checkfirst=True)
        print("✅ Created table: regression_details")
        
        print("\n" + "=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        print()
        print("📊 Performance Comparison Engine is now ready to use.")
        print()
        print("Next steps:")
        print("  1. Restart your backend server")
        print("  2. Create your first baseline using the API")
        print("  3. Run a comparison")
        print()
        print("API Documentation: http://localhost:8000/docs")
        print()
        
    except Exception as e:
        print(f"\n❌ Migration failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    migrate_comparison_tables()

# Run ID Migration Guide

## Overview

The Run ID system has been updated to use **sequential numbering** instead of timestamp-based UUIDs.

### Old Format
- `RUN-20251210104727-652ce91c`
- `RUN-20251210122123-a7d68c08`
- `RUN-20251211125312-464482b7`

### New Format
- `Run-1` (oldest run)
- `Run-2` (second oldest)
- `Run-3` (third oldest)
- And so on...

## What Changed?

### 1. Sequential Run IDs
- New uploads automatically get the next sequential Run ID
- Run-1 is reserved for the oldest run
- Each new upload batch increments the counter by 1

### 2. Database Changes
- Updated `DatabaseService.generate_next_run_id()` method
- Modified upload route to use sequential IDs
- All existing runs can be migrated to the new format

## Migration Process

### Step 1: Backup Your Database (Recommended)

```bash
# Navigate to backend directory
cd backend

# Create a backup
cp performance_analyzer.db performance_analyzer.db.backup
```

### Step 2: Run the Migration Script

```bash
# From the project root
./migrate_to_sequential_runs.sh
```

Or manually:

```bash
cd backend
source venv/bin/activate
python migrate_run_ids.py
```

### Step 3: Review the Changes

The migration script will:
1. Show you all existing Run IDs
2. Display the mapping (old → new)
3. Ask for confirmation before proceeding
4. Update all file records in the database

### Example Output

```
============================================================
Run ID Migration Script
============================================================

This will convert all existing Run IDs to sequential format.
Oldest run will become 'Run-1', second oldest 'Run-2', etc.

Found 3 unique Run IDs to migrate:

  RUN-20251210104727-652ce91c                    → Run-1     (3 files)
  RUN-20251210122123-a7d68c08                    → Run-2     (2 files)
  RUN-20251211125312-464482b7                    → Run-3     (1 files)

============================================================
Proceed with migration? (yes/no): yes

🔄 Starting migration...

✅ Successfully migrated 6 file records
✅ Converted 3 unique Run IDs to sequential format

Migration complete! 🎉
============================================================
```

## After Migration

### New Uploads
After migration, all new file uploads will automatically receive sequential Run IDs:
- If your last run was `Run-3`, the next upload becomes `Run-4`
- The system automatically finds the highest number and increments

### Frontend Display
The frontend will automatically display the new Run IDs without any code changes needed.

### Reports
- Existing report files will retain their old filenames
- New reports will use the new Run ID format
- All database references are updated correctly

## Technical Details

### Code Changes

**`backend/app/database/service.py`**
- Added `generate_next_run_id()` method
- Parses existing Run IDs to find the highest number
- Returns the next sequential ID

**`backend/app/api/routes.py`**
- Updated upload route to use `DatabaseService.generate_next_run_id()`
- Removed timestamp + UUID generation

**`backend/migrate_run_ids.py`**
- Migration script to renumber existing runs
- Orders runs by oldest upload timestamp
- Assigns Run-1 to the oldest, Run-2 to second oldest, etc.

### Database Schema
No schema changes required! The `run_id` column remains a `String(100)` field.

## Rollback

If you need to rollback:

```bash
cd backend
cp performance_analyzer.db.backup performance_analyzer.db
```

Then restart your server.

## Benefits

✅ **Cleaner URLs**: `/api/runs/Run-1` instead of `/api/runs/RUN-20251210104727-652ce91c`  
✅ **Better UX**: Users see "Run-1", "Run-2" instead of timestamps  
✅ **Easier to Reference**: "Check Run-5" is clearer than "Check RUN-20251210104727"  
✅ **Chronological Order**: Run-1 is always the first/oldest run  
✅ **Simpler Testing**: Predictable IDs make testing easier  

## Support

If you encounter any issues during migration:

1. Check that your virtual environment is activated
2. Ensure the database file exists at `backend/performance_analyzer.db`
3. Verify you have write permissions to the database
4. Review the migration script output for specific errors

## Future Runs

All future uploads will automatically use the new sequential format. No manual intervention needed! 🎉






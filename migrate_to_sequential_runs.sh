#!/bin/bash

echo "======================================"
echo "Run ID Migration Tool"
echo "======================================"
echo ""
echo "This script will convert all existing Run IDs"
echo "to sequential format (Run-1, Run-2, etc.)"
echo "where the oldest run becomes Run-1."
echo ""

# Navigate to the backend directory
cd "$(dirname "$0")/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "Please run ./run_backend.sh first to set up the environment."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Run the migration script
echo "Starting migration..."
echo ""

python migrate_run_ids.py

echo ""
echo "Migration process completed!"






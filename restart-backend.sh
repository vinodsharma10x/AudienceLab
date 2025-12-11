#!/bin/bash
# Restart Backend Script for AudienceLab

echo "Restarting AudienceLab Backend..."

# Kill any existing backend process
lsof -i:8000 -t | xargs kill -9 2>/dev/null && echo "Killed existing backend process" || echo "No existing backend process found"

# Small delay to ensure port is freed
sleep 1

# Navigate to backend directory
cd /Users/vinodsharma/code/AudienceLab/backend

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Ensure all dependencies are installed (including newly added boto3)
echo "Checking dependencies..."
pip install -q asyncpg boto3 2>/dev/null

# Start the backend
echo "Restarting backend server on port 8000..."
python start.py
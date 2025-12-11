#!/bin/bash

echo "Starting AudienceLab Backend Server"
echo "===================================="

# Navigate to backend directory
cd /Users/vinodsharma/code/AudienceLab/backend

# Check if we're in the right directory
echo "Current directory: $(pwd)"

# Check if main.py exists
if [ -f "main.py" ]; then
    echo "main.py found"
else
    echo "main.py not found"
    exit 1
fi

# Start the server
echo "Starting FastAPI server..."
echo "Server will be available at: http://localhost:8000"
echo "API docs will be at: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start uvicorn server
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

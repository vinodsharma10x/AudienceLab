#!/bin/bash
# Start Frontend Script for AudienceLab

echo "Starting AudienceLab Frontend..."

# Navigate to frontend directory
cd /Users/vinodsharma/code/AudienceLab/frontend

# Kill any existing frontend process (port 3000)
lsof -i:3000 -t | xargs kill -9 2>/dev/null && echo "Killed existing frontend process" || echo "No existing frontend process found"

# Start the frontend
echo "Starting frontend on port 3000..."
npm start
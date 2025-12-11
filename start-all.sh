#!/bin/bash
# Start Both Backend and Frontend for AudienceLab

echo "Starting AudienceLab Full Stack Application..."
echo "================================================"

# Function to open new terminal tab (Mac)
open_new_terminal_tab() {
    osascript -e 'tell application "Terminal" to activate' \
              -e 'tell application "System Events" to tell process "Terminal" to keystroke "t" using command down' \
              -e "tell application \"Terminal\" to do script \"$1\" in selected tab of the front window"
}

# Kill existing processes
echo "Cleaning up existing processes..."
lsof -i:8000 -t | xargs kill -9 2>/dev/null && echo "   Killed backend on port 8000" || echo "   No backend process found"
lsof -i:3000 -t | xargs kill -9 2>/dev/null && echo "   Killed frontend on port 3000" || echo "   No frontend process found"

echo ""
echo "Starting services..."
echo ""

# Start Backend in new terminal tab
echo "Starting Backend (port 8000)..."
BACKEND_CMD="cd /Users/vinodsharma/code/AudienceLab/backend && source venv/bin/activate && pip install -q asyncpg boto3 2>/dev/null && python start.py"
open_new_terminal_tab "$BACKEND_CMD"

# Wait a bit for backend to start
sleep 3

# Start Frontend in new terminal tab
echo "Starting Frontend (port 3000)..."
FRONTEND_CMD="cd /Users/vinodsharma/code/AudienceLab/frontend && npm start"
open_new_terminal_tab "$FRONTEND_CMD"

echo ""
echo "Both services starting in separate terminal tabs!"
echo ""
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "To stop services, use Ctrl+C in each terminal tab"
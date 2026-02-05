#!/bin/bash

echo "======================================"
echo "Auto Report Analyzer - Full Stack Setup"
echo "======================================"
echo ""

# Get the project root directory
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start Backend Server
echo "📦 Setting up Backend..."
cd "$PROJECT_ROOT/backend"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install backend dependencies if needed
if [ ! -f "venv/.dependencies_installed" ]; then
    echo "Installing backend dependencies..."
    pip install -r requirements.txt
    touch venv/.dependencies_installed
fi

# Create uploads directory if it doesn't exist
mkdir -p uploads reports

echo "🚀 Starting Backend Server on http://localhost:8000"
uvicorn app.main:app --reload --port 8000 > "$PROJECT_ROOT/backend.log" 2>&1 &
BACKEND_PID=$!

# Start Frontend Server
echo ""
echo "📦 Setting up Frontend..."
cd "$PROJECT_ROOT/frontend"

# Install frontend dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

echo "🚀 Starting Frontend Server on http://localhost:3020"
PORT=3020 npm start > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!

# Display status
echo ""
echo "======================================"
echo "✅ Servers are starting up!"
echo "======================================"
echo ""
echo "Backend:"
echo "  - API Server: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Logs: $PROJECT_ROOT/backend.log"
echo ""
echo "Frontend:"
echo "  - Web App: http://localhost:3020"
echo "  - Logs: $PROJECT_ROOT/frontend.log"
echo ""
echo "Press CTRL+C to stop both servers"
echo ""

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID


#!/bin/bash

echo "======================================"
echo "Restarting with Standard Ports"
echo "======================================"
echo ""

# Kill existing processes
echo "Stopping existing servers..."
lsof -ti:6000 | xargs kill -9 2>/dev/null
lsof -ti:7001 | xargs kill -9 2>/dev/null
lsof -ti:8000 | xargs kill -9 2>/dev/null
lsof -ti:3000 | xargs kill -9 2>/dev/null
pkill -f "react-scripts" 2>/dev/null
sleep 3

echo "✅ Servers stopped"
echo ""

# Start backend on port 8000
echo "Starting backend on port 8000..."
cd "$(dirname "$0")/backend"
source venv/bin/activate
uvicorn app.main:app --reload --port 8000 > ../backend.log 2>&1 &
BACKEND_PID=$!
echo "✅ Backend started (PID: $BACKEND_PID)"

sleep 3

# Start frontend on port 3000
echo "Starting frontend on port 3000..."
cd "$(dirname "$0")/frontend"
npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
echo "✅ Frontend started (PID: $FRONTEND_PID)"

echo ""
echo "======================================"
echo "Servers Running:"
echo "======================================"
echo "Backend:  http://localhost:8000"
echo "Frontend: http://localhost:3000"
echo ""
echo "Logs:"
echo "Backend:  tail -f backend.log"
echo "Frontend: tail -f frontend.log"
echo ""
echo "Press Ctrl+C to stop"
echo ""

wait



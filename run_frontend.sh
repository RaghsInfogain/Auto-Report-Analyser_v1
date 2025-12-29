#!/bin/bash

echo "======================================"
echo "Auto Report Analyzer - Frontend Only"
echo "======================================"
echo ""

# Navigate to the frontend directory
cd "$(dirname "$0")/frontend"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the React development server
echo "🚀 Starting Frontend Server..."
echo ""
echo "Server will be available at:"
echo "  - Web App: http://localhost:3000"
echo ""
echo "Press CTRL+C to stop the server"
echo ""

npm start






#!/bin/bash

echo "Starting Auto Report Analyzer Frontend..."

cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Start the development server
echo "Starting React development server on http://localhost:3020"
PORT=3020 npm start













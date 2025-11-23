# Quick Start Script for Linux/Mac
#!/bin/bash

echo "================================================"
echo "Industrial Sensor Monitoring System - Quick Start"
echo "================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

echo "[1/3] Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies"
    exit 1
fi

echo ""
echo "[2/3] Starting API Server..."
echo "API will be available at: http://localhost:8000"
echo "Dashboard will be available at: http://localhost:8000/dashboard"
echo ""

cd backend

# Start API server in background
python3 api.py > ../api.log 2>&1 &
API_PID=$!
echo "API Server started (PID: $API_PID)"

sleep 5

echo "[3/3] Starting Data Ingestion Service..."
echo ""

# Start ingestion service in background
python3 ingestion_service.py > ../ingestion.log 2>&1 &
INGESTION_PID=$!
echo "Ingestion Service started (PID: $INGESTION_PID)"

cd ..

echo ""
echo "================================================"
echo "System is running!"
echo "================================================"
echo ""
echo "Services:"
echo "  - API Server (PID: $API_PID)"
echo "  - Ingestion Service (PID: $INGESTION_PID)"
echo ""
echo "Open your browser to:"
echo "  http://localhost:8000/dashboard"
echo ""
echo "Logs are being written to:"
echo "  - api.log"
echo "  - ingestion.log"
echo ""
echo "To stop the system, run:"
echo "  kill $API_PID $INGESTION_PID"
echo ""
echo "Press Ctrl+C to stop monitoring (services will continue running)"
echo ""

# Keep script running and monitor processes
trap "echo 'Use kill command shown above to stop services'; exit" INT

# Wait for processes
wait $API_PID $INGESTION_PID

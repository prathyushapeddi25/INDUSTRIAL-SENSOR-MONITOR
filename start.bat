@echo off
echo ================================================
echo Industrial Sensor Monitoring System - Quick Start
echo ================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

echo [1/3] Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Starting API Server...
echo API will be available at: http://localhost:8000
echo Dashboard will be available at: http://localhost:8000/dashboard
echo.

cd backend
start "API Server" cmd /k "python api.py"

timeout /t 5 /nobreak >nul

echo [3/3] Starting Data Ingestion Service...
echo.
start "Ingestion Service" cmd /k "python ingestion_service.py"

echo.
echo ================================================
echo System is starting up!
echo ================================================
echo.
echo Two terminal windows have been opened:
echo   1. API Server (port 8000)
echo   2. Data Ingestion Service
echo.
echo Wait a few seconds, then open your browser to:
echo   http://localhost:8000/dashboard
echo.
echo Press any key to open the dashboard in your browser...
pause >nul

start http://localhost:8000/dashboard

echo.
echo To stop the system, close both terminal windows.
echo.
pause

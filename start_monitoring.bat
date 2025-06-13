@echo off
REM Start the enhanced monitoring system

echo ========================================
echo Starting Enhanced Monitoring System
echo ========================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Create required directories
if not exist "monitoring_logs" mkdir "monitoring_logs"
if not exist "shared_logs" mkdir "shared_logs"
if not exist "static" mkdir "static"

REM Start monitoring server
echo Starting monitoring server...
start "Monitoring Server" cmd /k python monitor_server.py

REM Wait for server to start
echo Waiting for server to start...
timeout /t 3 /nobreak >nul

REM Check if server is running
curl -s http://localhost:8888/api/status >nul 2>&1
if errorlevel 1 (
    echo WARNING: Server may not be running on default port 8888
    echo Trying alternate port 8889...
    start "Monitoring Server Alt" cmd /k python monitor_server.py --port 8889
    timeout /t 3 /nobreak >nul
)

REM Start enhanced monitor
echo Starting enhanced monitor...
start "Enhanced Monitor" cmd /k python enhanced_monitor.py

REM Start log sync
echo Starting log synchronization...
start "Log Sync" cmd /k sync_logs.bat

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Open dashboard in default browser
echo Opening dashboard in browser...
start http://localhost:8888

echo.
echo ========================================
echo Monitoring System Started!
echo ========================================
echo.
echo Dashboard: http://localhost:8888
echo.
echo To test the system:
echo   python test_monitoring.py
echo.
echo To simulate events:
echo   python test_monitoring.py simulate
echo.
echo Press any key to close this window...
pause >nul
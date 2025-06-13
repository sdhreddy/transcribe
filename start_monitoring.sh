#!/bin/bash
# Start the enhanced monitoring system on Linux/WSL

echo "========================================"
echo "Starting Enhanced Monitoring System"
echo "========================================"
echo

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8 or higher"
    exit 1
fi

# Create required directories
mkdir -p monitoring_logs shared_logs static

# Function to check if port is in use
check_port() {
    nc -z localhost $1 2>/dev/null
    return $?
}

# Kill any existing monitoring processes
echo "Checking for existing monitoring processes..."
pkill -f "monitor_server.py" 2>/dev/null
pkill -f "enhanced_monitor.py" 2>/dev/null
sleep 2

# Start monitoring server
echo "Starting monitoring server..."
if check_port 8888; then
    echo "Port 8888 is in use, trying 8889..."
    python3 monitor_server.py --port 8889 &
    SERVER_PORT=8889
else
    python3 monitor_server.py &
    SERVER_PORT=8888
fi
SERVER_PID=$!

# Wait for server to start
echo "Waiting for server to start..."
sleep 3

# Verify server is running
if ! check_port $SERVER_PORT; then
    echo "WARNING: Server may not be running properly"
else
    echo "Server running on port $SERVER_PORT"
fi

# Start enhanced monitor
echo "Starting enhanced monitor..."
python3 enhanced_monitor.py --server http://localhost:$SERVER_PORT &
MONITOR_PID=$!

# Function to cleanup on exit
cleanup() {
    echo
    echo "Shutting down monitoring system..."
    kill $SERVER_PID 2>/dev/null
    kill $MONITOR_PID 2>/dev/null
    echo "Monitoring system stopped"
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

echo
echo "========================================"
echo "Monitoring System Started!"
echo "========================================"
echo
echo "Dashboard: http://localhost:$SERVER_PORT"
echo
echo "To test the system:"
echo "  python3 test_monitoring.py"
echo
echo "To simulate events:"
echo "  python3 test_monitoring.py simulate"
echo
echo "Press Ctrl+C to stop monitoring..."
echo

# Keep script running
wait
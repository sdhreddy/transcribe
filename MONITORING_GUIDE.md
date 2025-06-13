# Enhanced Monitoring System Guide

This guide explains how to use the enhanced monitoring system for transcribe, which provides real-time diagnostics, cross-platform log syncing, and a web-based dashboard.

## Overview

The enhanced monitoring system consists of:
1. **Web Monitoring Server** (`monitor_server.py`) - Provides real-time dashboard
2. **Enhanced Monitor** (`enhanced_monitor.py`) - Detailed diagnostics with web integration
3. **Web Dashboard** - Real-time visualization at http://localhost:8888
4. **Log Sync Tool** (`sync_logs.bat`) - Automatic Windows/WSL log synchronization

## Quick Start

### Step 1: Start the Monitoring Server

In WSL or Linux:
```bash
python monitor_server.py
```

In Windows:
```cmd
python monitor_server.py
```

The server will start on http://localhost:8888 (accessible from any browser).

### Step 2: Start the Enhanced Monitor

In a new terminal:
```bash
python enhanced_monitor.py
```

Options:
- `--server http://localhost:8888` - Specify server URL (default)
- `--no-server` - Run in offline mode (logs only)

### Step 3: Access the Dashboard

Open your browser and navigate to:
```
http://localhost:8888
```

### Step 4: Start Log Syncing (Windows)

For automatic log syncing between Windows and WSL:
```cmd
sync_logs.bat
```

This will continuously sync logs to the `shared_logs` directory.

## Dashboard Features

### Real-Time Metrics
- **Total Transcriptions** - Number of voice inputs processed
- **Voice Detection** - User vs. other voice counts
- **Response Rate** - Percentage of inputs that triggered responses
- **Average Latency** - Processing time metrics

### Live Event Feed
- Voice decisions with confidence scores
- Color-coded indicators:
  - 🔵 Blue (U) - User voice detected
  - 🔴 Red (O) - Other voice detected
  - 🟢 Green (✓) - Response triggered

### Performance Monitoring
- Real-time latency charts
- Breakdown by stage:
  - Audio processing
  - Transcription
  - TTS (Text-to-Speech)

### Configuration Display
- Current voice filter settings
- Threshold values
- Profile information

## Using the Monitoring System

### For Testing Voice Discrimination

1. Start both the monitoring server and enhanced monitor
2. Open the dashboard in your browser
3. Run your transcribe application
4. Watch real-time decisions in the dashboard
5. Check confidence scores and response patterns

### For Cross-Platform Testing

1. Start monitoring server in WSL:
   ```bash
   python monitor_server.py
   ```

2. Run sync_logs.bat in Windows:
   ```cmd
   sync_logs.bat
   ```

3. Test on Windows - logs automatically sync to WSL
4. View real-time results at http://localhost:8888

### For Offline Analysis

1. Run enhanced monitor with `--no-server` flag
2. All events saved to `shared_logs` directory
3. Generate report with Ctrl+C
4. Open HTML report in browser

## Log Files and Locations

### Directories
- `monitoring_logs/` - Server and monitor logs
- `shared_logs/` - Cross-platform shared logs
- `diagnostics/` - Legacy diagnostic files

### Log Files
- `monitor_server_*.log` - Web server logs
- `enhanced_monitor_*.log` - Monitor process logs
- `events_*.jsonl` - Event stream (JSON lines)
- `monitor_report_*.html` - Session reports

## API Endpoints

The monitoring server provides these endpoints:

- `GET /` - Web dashboard
- `GET /api/status` - Server status
- `GET /api/stats` - Session statistics
- `GET /api/logs?limit=100` - Recent log entries
- `GET /api/events` - Server-sent events stream
- `POST /api/event` - Submit new event

## Troubleshooting

### Dashboard Not Loading
1. Check server is running: `http://localhost:8888/api/status`
2. Try different port: `python monitor_server.py --port 8889`
3. Check firewall settings

### No Events Showing
1. Ensure enhanced_monitor.py is running
2. Check transcribe app is using monitored instance
3. Verify network connectivity to server

### Log Sync Issues
1. Check WSL is running
2. Verify paths in sync_logs.bat
3. Run as administrator if needed

### Performance Issues
1. Clear old logs periodically
2. Limit dashboard to recent events
3. Use offline mode for intensive testing

## Advanced Features

### Custom Event Logging

From your code:
```python
from monitor_server import MonitoringClient

client = MonitoringClient()
client.send_event("custom_event", {
    "action": "test",
    "value": 123
})
```

### Programmatic Analysis

Read event logs:
```python
import json
from pathlib import Path

events = []
log_file = Path("shared_logs/events_20250613.jsonl")
with open(log_file) as f:
    for line in f:
        events.append(json.loads(line))
```

### Integration with CI/CD

The monitoring system can be integrated into automated testing:
```bash
# Start monitoring
python monitor_server.py &
SERVER_PID=$!

# Run tests
python enhanced_monitor.py --no-server &
MONITOR_PID=$!

# Run your tests here
python your_tests.py

# Stop monitoring
kill $MONITOR_PID
kill $SERVER_PID

# Check results
python analyze_logs.py shared_logs/
```

## Best Practices

1. **Start Fresh** - Clear old logs before important test sessions
2. **Use Descriptive Transcripts** - Makes event tracking easier
3. **Monitor Performance** - Watch for latency spikes
4. **Save Reports** - Generate HTML reports after each session
5. **Cross-Reference** - Compare dashboard with log files

## Security Notes

- Server binds to 0.0.0.0 by default (accessible from network)
- Use `--host 127.0.0.1` for local-only access
- No authentication on endpoints (add if needed)
- Logs may contain sensitive transcripts

## Support

For issues or questions:
1. Check monitor_server_*.log for server errors
2. Check enhanced_monitor_*.log for injection issues
3. Verify all dependencies installed
4. Test with simple scenarios first
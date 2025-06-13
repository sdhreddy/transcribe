#!/usr/bin/env python
"""Web server for real-time transcribe monitoring.

This server provides:
- Real-time log streaming via WebSocket
- REST API for diagnostics data
- Static file serving for the web dashboard
- Cross-platform log synchronization
"""

import os
import sys
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import threading
import time

# Web server imports
from aiohttp import web
from aiohttp_sse import sse_response
import aiohttp_cors

# Configure logging
log_dir = Path("monitoring_logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"monitor_server_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d - %(name)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class MonitoringServer:
    """Web server for real-time monitoring dashboard."""
    
    def __init__(self, host: str = '0.0.0.0', port: int = 8888):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.clients: Set[web.Response] = set()
        self.log_buffer: List[Dict] = []
        self.max_buffer_size = 1000
        
        # Shared directories for cross-platform access
        self.shared_log_dir = Path("shared_logs")
        self.shared_log_dir.mkdir(exist_ok=True)
        
        # Monitoring data
        self.session_data = {
            "start_time": datetime.now().isoformat(),
            "config": {},
            "stats": {
                "total_transcriptions": 0,
                "user_voice_detected": 0,
                "other_voice_detected": 0,
                "responses_triggered": 0,
                "responses_ignored": 0,
                "errors": 0
            },
            "performance": {
                "audio_latencies": [],
                "transcription_latencies": [],
                "tts_latencies": []
            },
            "recent_events": []
        }
        
        # Setup routes
        self._setup_routes()
        
        # Setup CORS
        cors = aiohttp_cors.setup(self.app, defaults={
            "*": aiohttp_cors.ResourceOptions(
                allow_credentials=True,
                expose_headers="*",
                allow_headers="*"
            )
        })
        
        for route in list(self.app.router.routes()):
            cors.add(route)
    
    def _setup_routes(self):
        """Setup web routes."""
        # API routes
        self.app.router.add_get('/api/status', self.handle_status)
        self.app.router.add_get('/api/logs', self.handle_logs)
        self.app.router.add_get('/api/stats', self.handle_stats)
        self.app.router.add_get('/api/events', self.handle_events_stream)
        self.app.router.add_post('/api/event', self.handle_post_event)
        
        # Static files
        static_dir = Path(__file__).parent / 'static'
        static_dir.mkdir(exist_ok=True)
        self.app.router.add_static('/', static_dir, name='static')
        self.app.router.add_get('/', self.handle_index)
    
    async def handle_index(self, request):
        """Serve the main dashboard page."""
        index_path = Path(__file__).parent / 'static' / 'monitor.html'
        if index_path.exists():
            return web.FileResponse(index_path)
        else:
            return web.Response(text="Dashboard not found. Creating...", status=404)
    
    async def handle_status(self, request):
        """Return server status."""
        return web.json_response({
            "status": "running",
            "uptime": (datetime.now() - datetime.fromisoformat(self.session_data["start_time"])).total_seconds(),
            "connected_clients": len(self.clients),
            "buffer_size": len(self.log_buffer)
        })
    
    async def handle_logs(self, request):
        """Return recent logs."""
        limit = int(request.query.get('limit', 100))
        return web.json_response(self.log_buffer[-limit:])
    
    async def handle_stats(self, request):
        """Return session statistics."""
        return web.json_response(self.session_data)
    
    async def handle_events_stream(self, request):
        """Server-sent events for real-time updates."""
        async with sse_response(request) as resp:
            self.clients.add(resp)
            try:
                # Send current stats
                await resp.send(json.dumps({
                    "type": "stats",
                    "data": self.session_data
                }))
                
                # Keep connection alive
                while True:
                    await asyncio.sleep(1)
                    if not resp.is_connected():
                        break
            finally:
                self.clients.discard(resp)
        return resp
    
    async def handle_post_event(self, request):
        """Handle posted events from the monitoring system."""
        try:
            data = await request.json()
            event_type = data.get('type')
            event_data = data.get('data', {})
            
            # Process event
            await self.process_event(event_type, event_data)
            
            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.error(f"Error processing event: {e}")
            return web.json_response({"error": str(e)}, status=400)
    
    async def process_event(self, event_type: str, data: Dict):
        """Process incoming event."""
        timestamp = datetime.now().isoformat()
        
        # Create log entry
        log_entry = {
            "timestamp": timestamp,
            "type": event_type,
            "data": data
        }
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        if len(self.log_buffer) > self.max_buffer_size:
            self.log_buffer.pop(0)
        
        # Update stats based on event type
        if event_type == "config":
            self.session_data["config"] = data
        
        elif event_type == "voice_decision":
            self.session_data["stats"]["total_transcriptions"] += 1
            
            if data.get("is_user_voice"):
                self.session_data["stats"]["user_voice_detected"] += 1
            else:
                self.session_data["stats"]["other_voice_detected"] += 1
            
            if data.get("should_respond"):
                self.session_data["stats"]["responses_triggered"] += 1
            else:
                self.session_data["stats"]["responses_ignored"] += 1
            
            # Add to recent events
            self.session_data["recent_events"].append({
                "timestamp": timestamp,
                "text": data.get("transcript", "")[:50],
                "is_user": data.get("is_user_voice"),
                "confidence": data.get("confidence"),
                "responded": data.get("should_respond")
            })
            
            # Keep only last 20 events
            if len(self.session_data["recent_events"]) > 20:
                self.session_data["recent_events"].pop(0)
        
        elif event_type == "latency":
            latency_type = data.get("stage")
            duration_ms = data.get("duration_ms", 0)
            
            if latency_type == "audio":
                self.session_data["performance"]["audio_latencies"].append(duration_ms)
            elif latency_type == "transcription":
                self.session_data["performance"]["transcription_latencies"].append(duration_ms)
            elif latency_type == "tts":
                self.session_data["performance"]["tts_latencies"].append(duration_ms)
            
            # Keep only last 100 measurements
            for key in self.session_data["performance"]:
                if len(self.session_data["performance"][key]) > 100:
                    self.session_data["performance"][key].pop(0)
        
        elif event_type == "error":
            self.session_data["stats"]["errors"] += 1
        
        # Broadcast to all connected clients
        await self.broadcast_event(log_entry)
        
        # Save to shared log file
        await self.save_to_shared_log(log_entry)
    
    async def broadcast_event(self, event: Dict):
        """Broadcast event to all connected clients."""
        disconnected = set()
        
        for client in self.clients:
            try:
                await client.send(json.dumps(event))
            except:
                disconnected.add(client)
        
        # Remove disconnected clients
        self.clients -= disconnected
    
    async def save_to_shared_log(self, event: Dict):
        """Save event to shared log file for cross-platform access."""
        log_file = self.shared_log_dir / f"events_{datetime.now().strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(log_file, 'a') as f:
                f.write(json.dumps(event) + '\n')
        except Exception as e:
            logger.error(f"Failed to save to shared log: {e}")
    
    def run(self):
        """Run the web server."""
        logger.info(f"Starting monitoring server on http://{self.host}:{self.port}")
        web.run_app(self.app, host=self.host, port=self.port)


class MonitoringClient:
    """Client for sending events to the monitoring server."""
    
    def __init__(self, server_url: str = "http://localhost:8888"):
        self.server_url = server_url
        self.session = None
        
        # Try to import aiohttp for async support
        try:
            import aiohttp
            self.aiohttp = aiohttp
        except ImportError:
            self.aiohttp = None
    
    async def send_event_async(self, event_type: str, data: Dict):
        """Send event asynchronously."""
        if not self.aiohttp:
            return
        
        if not self.session:
            self.session = self.aiohttp.ClientSession()
        
        try:
            async with self.session.post(
                f"{self.server_url}/api/event",
                json={"type": event_type, "data": data}
            ) as resp:
                return await resp.json()
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    def send_event(self, event_type: str, data: Dict):
        """Send event synchronously."""
        try:
            import requests
            response = requests.post(
                f"{self.server_url}/api/event",
                json={"type": event_type, "data": data},
                timeout=1
            )
            return response.json()
        except Exception as e:
            logger.error(f"Failed to send event: {e}")
    
    def close(self):
        """Close client session."""
        if self.session:
            asyncio.create_task(self.session.close())


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Transcribe Monitoring Server")
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8888, help='Port to bind to')
    args = parser.parse_args()
    
    server = MonitoringServer(host=args.host, port=args.port)
    
    try:
        server.run()
    except KeyboardInterrupt:
        logger.info("Server stopped")


if __name__ == "__main__":
    main()
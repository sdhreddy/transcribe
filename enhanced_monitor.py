#!/usr/bin/env python
"""Enhanced monitoring system with web integration.

This enhanced monitor:
- Integrates with the web monitoring server
- Provides detailed voice discrimination diagnostics
- Tracks performance metrics
- Supports cross-platform log syncing
"""

import os
import sys
import time
import json
import logging
import threading
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import requests

# Add app to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'transcribe'))

# Configure logging
log_dir = Path("monitoring_logs")
log_dir.mkdir(exist_ok=True)
shared_log_dir = Path("shared_logs")
shared_log_dir.mkdir(exist_ok=True)

log_file = log_dir / f"enhanced_monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


class EnhancedTranscribeMonitor:
    """Enhanced monitor with web server integration."""
    
    def __init__(self, server_url: str = "http://localhost:8888"):
        self.server_url = server_url
        self.session_start = time.time()
        self.events_queue = []
        self.send_thread = None
        self.running = True
        
        # Local statistics for offline mode
        self.local_stats = {
            "total_transcriptions": 0,
            "user_voice_detected": 0,
            "other_voice_detected": 0,
            "responses_triggered": 0,
            "responses_ignored": 0,
            "errors": 0,
            "voice_decisions": [],
            "latencies": {
                "audio": [],
                "transcription": [],
                "tts": []
            }
        }
        
        # Start event sender thread
        self.start_event_sender()
    
    def start_event_sender(self):
        """Start background thread to send events to server."""
        def sender():
            while self.running:
                if self.events_queue:
                    event = self.events_queue.pop(0)
                    try:
                        self.send_to_server(event['type'], event['data'])
                    except Exception as e:
                        logger.warning(f"Failed to send event to server: {e}")
                        # Save to local file as backup
                        self.save_event_locally(event)
                time.sleep(0.1)
        
        self.send_thread = threading.Thread(target=sender, daemon=True)
        self.send_thread.start()
    
    def send_to_server(self, event_type: str, data: Dict):
        """Send event to monitoring server."""
        try:
            response = requests.post(
                f"{self.server_url}/api/event",
                json={"type": event_type, "data": data},
                timeout=1
            )
            response.raise_for_status()
        except requests.exceptions.RequestException:
            raise
    
    def save_event_locally(self, event: Dict):
        """Save event to local file for offline analysis."""
        timestamp = datetime.now()
        filename = shared_log_dir / f"events_{timestamp.strftime('%Y%m%d')}.jsonl"
        
        try:
            with open(filename, 'a') as f:
                f.write(json.dumps({
                    "timestamp": timestamp.isoformat(),
                    **event
                }) + '\n')
        except Exception as e:
            logger.error(f"Failed to save event locally: {e}")
    
    def log_event(self, event_type: str, data: Dict):
        """Queue event for sending to server."""
        self.events_queue.append({
            "type": event_type,
            "data": data
        })
        
        # Also save locally for redundancy
        self.save_event_locally({"type": event_type, "data": data})
    
    def log_config(self, config: dict):
        """Log configuration settings."""
        config_data = {
            "voice_filter_enabled": config.get("General", {}).get("voice_filter_enabled"),
            "voice_filter_threshold": config.get("General", {}).get("voice_filter_threshold"),
            "inverted_voice_response": config.get("General", {}).get("inverted_voice_response"),
            "voice_filter_profile": config.get("General", {}).get("voice_filter_profile")
        }
        
        self.log_event("config", config_data)
        logger.info(f"Configuration logged: {json.dumps(config_data, indent=2)}")
    
    def log_voice_decision(self, audio_data: np.ndarray, sample_rate: int,
                          is_user: bool, confidence: float, should_respond: bool,
                          transcript: str = "", analysis_details: Dict = None):
        """Log detailed voice filtering decision."""
        decision_data = {
            "audio_length": len(audio_data) / sample_rate,
            "is_user_voice": is_user,
            "confidence": float(confidence),
            "should_respond": should_respond,
            "transcript": transcript,
            "sample_rate": sample_rate,
            "audio_stats": {
                "mean": float(np.mean(audio_data)),
                "std": float(np.std(audio_data)),
                "max": float(np.max(np.abs(audio_data))),
                "energy": float(np.sum(audio_data ** 2))
            }
        }
        
        # Add analysis details if provided
        if analysis_details:
            decision_data["analysis"] = analysis_details
        
        # Update local stats
        self.local_stats["total_transcriptions"] += 1
        if is_user:
            self.local_stats["user_voice_detected"] += 1
        else:
            self.local_stats["other_voice_detected"] += 1
        
        if should_respond:
            self.local_stats["responses_triggered"] += 1
        else:
            self.local_stats["responses_ignored"] += 1
        
        self.local_stats["voice_decisions"].append(decision_data)
        
        # Send to server
        self.log_event("voice_decision", decision_data)
        
        # Log with color coding
        if should_respond:
            logger.info(f"🟢 RESPOND: {transcript[:50]}... (user={is_user}, conf={confidence:.3f})")
        else:
            logger.info(f"🔴 IGNORE: {transcript[:50]}... (user={is_user}, conf={confidence:.3f})")
    
    def log_latency(self, stage: str, duration: float, details: Dict = None):
        """Log processing latency with detailed breakdown."""
        latency_data = {
            "stage": stage,
            "duration_ms": duration * 1000
        }
        
        if details:
            latency_data["details"] = details
        
        # Update local stats
        if stage in ["audio", "transcription", "tts"]:
            self.local_stats["latencies"][stage].append(duration * 1000)
        
        self.log_event("latency", latency_data)
        logger.debug(f"⏱️  {stage}: {duration*1000:.1f}ms")
    
    def log_error(self, error_type: str, error_msg: str, stack_trace: str = None):
        """Log error with details."""
        error_data = {
            "type": error_type,
            "message": error_msg,
            "stack_trace": stack_trace
        }
        
        self.local_stats["errors"] += 1
        self.log_event("error", error_data)
        logger.error(f"❌ {error_type}: {error_msg}")
    
    def generate_report(self) -> Path:
        """Generate comprehensive monitoring report."""
        report_file = shared_log_dir / f"monitor_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        
        # Calculate statistics
        total_decisions = len(self.local_stats["voice_decisions"])
        response_rate = (self.local_stats["responses_triggered"] / total_decisions * 100) if total_decisions > 0 else 0
        
        # Average latencies
        avg_latencies = {}
        for stage, values in self.local_stats["latencies"].items():
            avg_latencies[stage] = np.mean(values) if values else 0
        
        # Generate HTML report
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Transcribe Monitoring Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        .stat-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; border: 1px solid #dee2e6; }}
        .stat-value {{ font-size: 32px; font-weight: bold; color: #007bff; }}
        .stat-label {{ color: #6c757d; font-size: 14px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #dee2e6; }}
        th {{ background: #f8f9fa; font-weight: bold; }}
        .confidence-high {{ color: #28a745; }}
        .confidence-medium {{ color: #ffc107; }}
        .confidence-low {{ color: #dc3545; }}
        .timestamp {{ color: #6c757d; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Transcribe Monitoring Report</h1>
        <p class="timestamp">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        
        <h2>Session Statistics</h2>
        <div class="stat-grid">
            <div class="stat-card">
                <div class="stat-value">{self.local_stats['total_transcriptions']}</div>
                <div class="stat-label">Total Transcriptions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.local_stats['user_voice_detected']}</div>
                <div class="stat-label">User Voice Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{self.local_stats['other_voice_detected']}</div>
                <div class="stat-label">Other Voices Detected</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{response_rate:.1f}%</div>
                <div class="stat-label">Response Rate</div>
            </div>
        </div>
        
        <h2>Performance Metrics</h2>
        <table>
            <tr>
                <th>Stage</th>
                <th>Average Latency (ms)</th>
                <th>Min (ms)</th>
                <th>Max (ms)</th>
            </tr>
            <tr>
                <td>Audio Processing</td>
                <td>{avg_latencies.get('audio', 0):.1f}</td>
                <td>{min(self.local_stats['latencies']['audio']) if self.local_stats['latencies']['audio'] else 0:.1f}</td>
                <td>{max(self.local_stats['latencies']['audio']) if self.local_stats['latencies']['audio'] else 0:.1f}</td>
            </tr>
            <tr>
                <td>Transcription</td>
                <td>{avg_latencies.get('transcription', 0):.1f}</td>
                <td>{min(self.local_stats['latencies']['transcription']) if self.local_stats['latencies']['transcription'] else 0:.1f}</td>
                <td>{max(self.local_stats['latencies']['transcription']) if self.local_stats['latencies']['transcription'] else 0:.1f}</td>
            </tr>
            <tr>
                <td>TTS</td>
                <td>{avg_latencies.get('tts', 0):.1f}</td>
                <td>{min(self.local_stats['latencies']['tts']) if self.local_stats['latencies']['tts'] else 0:.1f}</td>
                <td>{max(self.local_stats['latencies']['tts']) if self.local_stats['latencies']['tts'] else 0:.1f}</td>
            </tr>
        </table>
        
        <h2>Recent Voice Decisions</h2>
        <table>
            <tr>
                <th>Time</th>
                <th>Transcript</th>
                <th>User Voice</th>
                <th>Confidence</th>
                <th>Action</th>
            </tr>
        """
        
        # Add recent voice decisions
        for decision in self.local_stats["voice_decisions"][-20:]:
            confidence = decision['confidence']
            confidence_class = 'confidence-high' if confidence > 0.7 else 'confidence-medium' if confidence > 0.4 else 'confidence-low'
            
            html_content += f"""
            <tr>
                <td class="timestamp">{datetime.now().strftime('%H:%M:%S')}</td>
                <td>{decision['transcript'][:50]}...</td>
                <td>{'Yes' if decision['is_user_voice'] else 'No'}</td>
                <td class="{confidence_class}">{confidence:.1%}</td>
                <td>{'Responded' if decision['should_respond'] else 'Ignored'}</td>
            </tr>
            """
        
        html_content += """
        </table>
        
        <h2>Errors</h2>
        <p>Total errors: {}</p>
    </div>
</body>
</html>
        """.format(self.local_stats['errors'])
        
        with open(report_file, 'w') as f:
            f.write(html_content)
        
        logger.info(f"📊 Report generated: {report_file}")
        return report_file
    
    def stop(self):
        """Stop the monitor."""
        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=2)


def inject_enhanced_monitoring(monitor: EnhancedTranscribeMonitor):
    """Inject enhanced monitoring into the transcribe application."""
    try:
        import app.transcribe.audio_transcriber as at
        import app.transcribe.voice_filter as vf
        
        # Save original methods
        original_transcribe = at.AudioTranscriber.transcribe_audio_queue
        original_init = at.AudioTranscriber.__init__
        original_filter_check = None
        
        if hasattr(vf, 'VoiceFilter'):
            original_filter_check = vf.VoiceFilter.is_user_voice
        
        def monitored_init(self, *args, **kwargs):
            """Monitored init to log config."""
            original_init(self, *args, **kwargs)
            monitor.log_config(self.config)
            logger.info("Enhanced monitoring injected into AudioTranscriber")
        
        def monitored_transcribe(self, audio_queue):
            """Enhanced monitored transcribe method."""
            logger.info("Starting enhanced monitored transcription loop")
            
            while True:
                start_time = time.time()
                who_spoke, data, time_spoken = audio_queue.get()
                
                queue_latency = time.time() - time_spoken.timestamp()
                monitor.log_latency("queue_wait", queue_latency)
                
                # Call original method logic
                self._update_last_sample_and_phrase_status(who_spoke, data, time_spoken)
                source_info = self.audio_sources_properties[who_spoke]
                
                text = ''
                try:
                    import tempfile
                    file_descriptor, path = tempfile.mkstemp(suffix=".wav")
                    os.close(file_descriptor)
                    source_info["process_data_func"](source_info["last_sample"], path)
                    
                    if self.transcribe:
                        transcribe_start = time.time()
                        response = self.stt_model.get_transcription(path)
                        text = self.stt_model.process_response(response)
                        
                        transcribe_duration = time.time() - transcribe_start
                        monitor.log_latency("transcription", transcribe_duration, {
                            "model": getattr(self.stt_model, 'model_type', 'unknown'),
                            "audio_length": len(source_info["last_sample"]) / source_info["sample_rate"]
                        })
                        
                        if text != '':
                            self._prune_audio_file(response, who_spoke, time_spoken, path)
                
                except Exception as e:
                    import traceback
                    monitor.log_error("transcription_error", str(e), traceback.format_exc())
                finally:
                    os.unlink(path)
                
                if text != '' and text.lower() != 'you':
                    if not (who_spoke == 'Speaker' and self._should_ignore_speaker_transcript(text)):
                        # Voice filtering logic with enhanced monitoring
                        should_process = True
                        
                        if self.voice_filter_enabled and self.voice_filter and who_spoke == 'You':
                            try:
                                filter_start = time.time()
                                audio_array = np.frombuffer(source_info["last_sample"], dtype=np.int16)
                                sample_rate = source_info["sample_rate"]
                                
                                # Check voice with detailed analysis
                                is_user_voice, confidence = self.voice_filter.is_user_voice(audio_array, sample_rate)
                                should_process = self.voice_filter.should_respond(is_user_voice, self.inverted_voice_response)
                                
                                filter_duration = time.time() - filter_start
                                
                                # Log detailed decision
                                monitor.log_voice_decision(
                                    audio_array, sample_rate,
                                    is_user_voice, confidence,
                                    should_process, text,
                                    analysis_details={
                                        "filter_duration_ms": filter_duration * 1000,
                                        "threshold": getattr(self.voice_filter, 'threshold', None)
                                    }
                                )
                                
                            except Exception as e:
                                import traceback
                                monitor.log_error("voice_filter_error", str(e), traceback.format_exc())
                                should_process = True
                        
                        if should_process:
                            self.update_transcript(who_spoke, text, time_spoken)
                            self.transcript_changed_event.set()
                
                total_latency = time.time() - start_time
                monitor.log_latency("total_processing", total_latency)
        
        # Enhanced voice filter monitoring
        def monitored_is_user_voice(self, audio_data, sample_rate):
            """Monitor voice filter decisions in detail."""
            start_time = time.time()
            
            # Call original method
            is_user, confidence = original_filter_check(self, audio_data, sample_rate)
            
            # Log filter performance
            duration = time.time() - start_time
            monitor.log_latency("voice_filter", duration, {
                "audio_length": len(audio_data) / sample_rate,
                "result": is_user,
                "confidence": float(confidence)
            })
            
            return is_user, confidence
        
        # Apply patches
        at.AudioTranscriber.__init__ = monitored_init
        at.AudioTranscriber.transcribe_audio_queue = monitored_transcribe
        
        if original_filter_check:
            vf.VoiceFilter.is_user_voice = monitored_is_user_voice
        
        logger.info("Enhanced monitoring successfully injected")
        
    except Exception as e:
        logger.error(f"Failed to inject monitoring: {e}")
        raise


def main():
    """Main entry point for enhanced monitor."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Enhanced Transcribe Monitor")
    parser.add_argument('--server', default='http://localhost:8888',
                       help='Monitoring server URL')
    parser.add_argument('--no-server', action='store_true',
                       help='Run without web server (offline mode)')
    args = parser.parse_args()
    
    # Create monitor
    monitor = EnhancedTranscribeMonitor(
        server_url=args.server if not args.no_server else None
    )
    
    print("🔍 Enhanced Transcribe Monitor")
    print("="*60)
    print(f"Server: {args.server if not args.no_server else 'Offline mode'}")
    print(f"Logs: {log_file}")
    print(f"Shared logs: {shared_log_dir}")
    print("Press Ctrl+C to stop and generate report")
    print("="*60)
    
    try:
        # Inject monitoring
        inject_enhanced_monitoring(monitor)
        
        print("✅ Enhanced monitoring active. Start the transcribe application now.")
        print(f"📊 View real-time dashboard at: {args.server}")
        
        # Keep running
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping enhanced monitor...")
        monitor.stop()
        
        # Generate report
        report_file = monitor.generate_report()
        print(f"\n📊 Report generated: {report_file}")
        print("Copy this file and the shared_logs directory to analyze the session")
    
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        monitor.log_error("monitor_crash", str(e))
        monitor.stop()


if __name__ == "__main__":
    main()
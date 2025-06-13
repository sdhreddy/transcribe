#!/usr/bin/env python
"""Real-time monitoring and diagnostics for voice discrimination.

This tool monitors the transcribe application in real-time and provides:
- Voice filter status and decisions
- Audio latency measurements
- Live transcription events
- Diagnostic information
"""

import os
import sys
import time
import json
import logging
from datetime import datetime
from pathlib import Path
import threading
from typing import Dict, List
import numpy as np

# Configure logging
log_dir = Path("diagnostics")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"monitor_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

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


class TranscribeMonitor:
    """Monitor for transcribe application diagnostics."""
    
    def __init__(self):
        self.events = []
        self.voice_decisions = []
        self.audio_latencies = []
        self.start_time = time.time()
        
        # Create diagnostic report structure
        self.diagnostic_data = {
            "session_start": datetime.now().isoformat(),
            "config": {},
            "events": [],
            "voice_decisions": [],
            "performance": {
                "audio_latencies": [],
                "tts_latencies": []
            },
            "errors": []
        }
    
    def log_config(self, config: dict):
        """Log configuration settings."""
        self.diagnostic_data["config"] = {
            "voice_filter_enabled": config.get("General", {}).get("voice_filter_enabled"),
            "voice_filter_threshold": config.get("General", {}).get("voice_filter_threshold"),
            "inverted_voice_response": config.get("General", {}).get("inverted_voice_response"),
            "voice_filter_profile": config.get("General", {}).get("voice_filter_profile")
        }
        logger.info(f"Configuration: {json.dumps(self.diagnostic_data['config'], indent=2)}")
    
    def log_voice_decision(self, audio_data: np.ndarray, sample_rate: int, 
                          is_user: bool, confidence: float, should_respond: bool,
                          transcript: str = ""):
        """Log voice filtering decision."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed": time.time() - self.start_time,
            "audio_length": len(audio_data) / sample_rate,
            "is_user_voice": is_user,
            "confidence": confidence,
            "should_respond": should_respond,
            "transcript": transcript[:50] + "..." if len(transcript) > 50 else transcript
        }
        
        self.voice_decisions.append(event)
        self.diagnostic_data["voice_decisions"].append(event)
        
        # Log with color coding
        if should_respond:
            logger.info(f"🟢 RESPOND: {transcript[:30]}... (user={is_user}, conf={confidence:.3f})")
        else:
            logger.info(f"🔴 IGNORE: {transcript[:30]}... (user={is_user}, conf={confidence:.3f})")
    
    def log_audio_latency(self, stage: str, duration: float):
        """Log audio processing latency."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage,
            "duration_ms": duration * 1000
        }
        
        self.audio_latencies.append(event)
        
        if stage == "tts_playback":
            self.diagnostic_data["performance"]["tts_latencies"].append(duration * 1000)
        else:
            self.diagnostic_data["performance"]["audio_latencies"].append(duration * 1000)
        
        logger.debug(f"⏱️  {stage}: {duration*1000:.1f}ms")
    
    def log_event(self, event_type: str, data: dict):
        """Log general event."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "elapsed": time.time() - self.start_time,
            "type": event_type,
            "data": data
        }
        
        self.events.append(event)
        self.diagnostic_data["events"].append(event)
        
        logger.info(f"📌 {event_type}: {json.dumps(data)}")
    
    def log_error(self, error_type: str, error_msg: str):
        """Log error."""
        error = {
            "timestamp": datetime.now().isoformat(),
            "type": error_type,
            "message": error_msg
        }
        
        self.diagnostic_data["errors"].append(error)
        logger.error(f"❌ {error_type}: {error_msg}")
    
    def save_diagnostics(self):
        """Save diagnostic data to file."""
        diag_file = log_dir / f"diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Add summary
        self.diagnostic_data["summary"] = {
            "total_events": len(self.events),
            "total_voice_decisions": len(self.voice_decisions),
            "responses_triggered": sum(1 for v in self.voice_decisions if v["should_respond"]),
            "responses_ignored": sum(1 for v in self.voice_decisions if not v["should_respond"]),
            "avg_audio_latency": np.mean(self.diagnostic_data["performance"]["audio_latencies"]) if self.diagnostic_data["performance"]["audio_latencies"] else 0,
            "avg_tts_latency": np.mean(self.diagnostic_data["performance"]["tts_latencies"]) if self.diagnostic_data["performance"]["tts_latencies"] else 0,
            "total_errors": len(self.diagnostic_data["errors"])
        }
        
        with open(diag_file, 'w') as f:
            json.dump(self.diagnostic_data, f, indent=2)
        
        logger.info(f"💾 Diagnostics saved to: {diag_file}")
        return diag_file
    
    def print_summary(self):
        """Print session summary."""
        print("\n" + "="*60)
        print("SESSION SUMMARY")
        print("="*60)
        
        summary = self.diagnostic_data.get("summary", {})
        print(f"Total voice decisions: {summary.get('total_voice_decisions', 0)}")
        print(f"Responses triggered: {summary.get('responses_triggered', 0)}")
        print(f"Responses ignored: {summary.get('responses_ignored', 0)}")
        
        if self.voice_decisions:
            user_decisions = [v for v in self.voice_decisions if v["is_user_voice"]]
            other_decisions = [v for v in self.voice_decisions if not v["is_user_voice"]]
            
            print(f"\nUser voice detected: {len(user_decisions)} times")
            print(f"Other voices detected: {len(other_decisions)} times")
            
            if user_decisions:
                avg_user_conf = np.mean([v["confidence"] for v in user_decisions])
                print(f"Avg user confidence: {avg_user_conf:.3f}")
            
            if other_decisions:
                avg_other_conf = np.mean([v["confidence"] for v in other_decisions])
                print(f"Avg other confidence: {avg_other_conf:.3f}")
        
        print(f"\nAvg audio latency: {summary.get('avg_audio_latency', 0):.1f}ms")
        print(f"Avg TTS latency: {summary.get('avg_tts_latency', 0):.1f}ms")
        print(f"Total errors: {summary.get('total_errors', 0)}")
        print("="*60)


# Global monitor instance
monitor = TranscribeMonitor()


def inject_monitoring():
    """Inject monitoring into audio_transcriber.py"""
    import app.transcribe.audio_transcriber as at
    
    # Save original methods
    original_transcribe = at.AudioTranscriber.transcribe_audio_queue
    original_init = at.AudioTranscriber.__init__
    
    def monitored_init(self, *args, **kwargs):
        """Monitored init to log config."""
        original_init(self, *args, **kwargs)
        monitor.log_config(self.config)
        logger.info(f"Voice filter enabled: {self.voice_filter_enabled}")
        logger.info(f"Voice filter exists: {self.voice_filter is not None}")
    
    def monitored_transcribe(self, audio_queue):
        """Monitored transcribe method."""
        logger.info("Starting monitored transcription loop")
        
        while True:
            start_time = time.time()
            who_spoke, data, time_spoken = audio_queue.get()
            
            queue_latency = time.time() - time_spoken.timestamp()
            monitor.log_audio_latency("queue_wait", queue_latency)
            
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
                    
                    monitor.log_audio_latency("transcription", time.time() - transcribe_start)
                    
                    if text != '':
                        self._prune_audio_file(response, who_spoke, time_spoken, path)
            
            except Exception as e:
                monitor.log_error("transcription_error", str(e))
            finally:
                os.unlink(path)
            
            if text != '' and text.lower() != 'you':
                if not (who_spoke == 'Speaker' and self._should_ignore_speaker_transcript(text)):
                    # Voice filtering logic
                    should_process = True
                    
                    if self.voice_filter_enabled and self.voice_filter and who_spoke == 'You':
                        try:
                            import numpy as np
                            audio_array = np.frombuffer(source_info["last_sample"], dtype=np.int16)
                            sample_rate = source_info["sample_rate"]
                            
                            # Check voice
                            is_user_voice, confidence = self.voice_filter.is_user_voice(audio_array, sample_rate)
                            should_process = self.voice_filter.should_respond(is_user_voice, self.inverted_voice_response)
                            
                            # Log decision
                            monitor.log_voice_decision(
                                audio_array, sample_rate, 
                                is_user_voice, confidence, 
                                should_process, text
                            )
                            
                        except Exception as e:
                            monitor.log_error("voice_filter_error", str(e))
                            should_process = True
                    
                    if should_process:
                        self.update_transcript(who_spoke, text, time_spoken)
                        self.transcript_changed_event.set()
                        monitor.log_event("transcript_added", {"speaker": who_spoke, "text": text[:50]})
            
            total_latency = time.time() - start_time
            monitor.log_audio_latency("total_processing", total_latency)
    
    # Monkey patch
    at.AudioTranscriber.__init__ = monitored_init
    at.AudioTranscriber.transcribe_audio_queue = monitored_transcribe
    
    logger.info("Monitoring injected into AudioTranscriber")


def main():
    """Main monitoring function."""
    print("🔍 Transcribe Voice Discrimination Monitor")
    print("="*60)
    print("This tool will monitor the transcribe application")
    print("Press Ctrl+C to stop and save diagnostics")
    print("="*60)
    
    try:
        # Import and inject monitoring
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app', 'transcribe'))
        inject_monitoring()
        
        print("✅ Monitoring active. Start the transcribe application now.")
        
        # Keep running
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\nStopping monitor...")
        monitor.print_summary()
        diag_file = monitor.save_diagnostics()
        print(f"\n📊 Diagnostic file: {diag_file}")
        print("Copy this file to analyze the session")
    
    except Exception as e:
        logger.error(f"Monitor error: {e}")
        monitor.log_error("monitor_crash", str(e))
        monitor.save_diagnostics()


if __name__ == "__main__":
    main()
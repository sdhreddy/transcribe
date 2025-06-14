"""Main entry point for low-latency transcribe application."""
import sys
import os
import signal
import time
import logging
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent / "sdk"))

from sdk.audio_recorder_updated import MicRecorder
from audio_transcriber_updated import AudioTranscriber
from streaming_transcriber import StreamingTranscriber
import conversation
from tsutils import configuration, app_logging

# Set up logging
logger = app_logging.get_module_logger("MAIN")

class LowLatencyTranscribe:
    """Main application class for low-latency transcription."""
    
    def __init__(self, config_path: str = "parameters.yaml"):
        """Initialize the application."""
        self.config = configuration.Config(config_path).data
        self.running = False
        
        # Initialize conversation
        self.conversation = conversation.Conversation()
        
        # Initialize audio recorder with WebRTC VAD
        self.mic_recorder = MicRecorder(
            source_name="Default Mic",
            use_webrtc_vad=self.config.get('General', {}).get('use_webrtc_vad', True)
        )
        
        # Initialize transcriber
        self.transcriber = AudioTranscriber(
            mic_source=self.mic_recorder,
            speaker_source=None,  # Not implemented for this demo
            model=None,  # Will use streaming transcriber
            convo=self.conversation,
            config=self.config
        )
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        
    def start(self):
        """Start the application."""
        logger.info("Starting Low-Latency Transcribe...")
        
        self.running = True
        
        # Start components
        self.transcriber.start()
        
        logger.info("Application started. Press Ctrl+C to stop.")
        
        # Main loop
        try:
            while self.running:
                # Check for transcript changes
                if self.transcriber.transcript_changed_event.wait(timeout=0.1):
                    self.transcriber.transcript_changed_event.clear()
                    self._display_transcript()
                    
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            
    def stop(self):
        """Stop the application."""
        logger.info("Stopping application...")
        self.running = False
        
        # Stop components
        if hasattr(self, 'mic_recorder'):
            self.mic_recorder.stop_recording()
            
        if hasattr(self, 'transcriber'):
            self.transcriber.stop()
            
        logger.info("Application stopped")
        
    def _display_transcript(self):
        """Display the current transcript."""
        # Get latest conversation entries
        recent = self.conversation.get_recent_entries(5)
        
        # Clear screen (optional)
        # os.system('clear' if os.name == 'posix' else 'cls')
        
        print("\n--- Transcript ---")
        for entry in recent:
            speaker = entry.get('speaker', 'Unknown')
            text = entry.get('text', '')
            timestamp = entry.get('timestamp', '')
            print(f"[{timestamp}] {speaker}: {text}")
        print("-" * 50)
        

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Low-Latency Transcribe")
    parser.add_argument(
        "-c", "--config",
        default="parameters.yaml",
        help="Path to configuration file"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.INFO)
        
    # Create and start application
    app = LowLatencyTranscribe(args.config)
    
    try:
        app.start()
    except Exception as e:
        logger.error(f"Application error: {e}", exc_info=True)
    finally:
        app.stop()
        

if __name__ == "__main__":
    main()
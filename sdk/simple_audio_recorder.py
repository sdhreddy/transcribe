"""
Simple continuous audio recorder without speech detection.
Records audio in fixed intervals without waiting for speech start/stop.
"""
import queue
import time
import logging
from datetime import datetime
import numpy as np
import custom_speech_recognition as sr
from tsutils import app_logging as al

logger = al.get_module_logger("SimpleMicRecorder")

class SimpleMicRecorder:
    """
    Simple continuous recorder that captures audio in fixed intervals.
    No speech detection, no pause detection - just continuous recording.
    """
    
    def __init__(self, source_name='You', recording_interval=3.0):
        """
        Initialize simple recorder.
        
        Args:
            source_name: Name identifier for this audio source
            recording_interval: Fixed interval in seconds for each recording chunk
        """
        logger.info(f"Initializing SimpleMicRecorder with {recording_interval}s intervals")
        
        self.source_name = source_name
        self.recording_interval = recording_interval
        self.enabled = True
        self.stop_recording = False
        
        # Initialize speech recognition components
        self.recorder = sr.Recognizer()
        # Don't need energy threshold for continuous recording
        self.recorder.energy_threshold = 1000
        self.recorder.dynamic_energy_threshold = False
        
        # Get microphone
        try:
            self.source = sr.Microphone()
            logger.info("Microphone initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize microphone: {e}")
            raise
            
    def adjust_for_noise(self, device_name, msg):
        """Compatibility method - we don't actually adjust for noise in simple mode"""
        logger.info(f"SimpleMicRecorder: Skipping noise adjustment for {device_name}")
        
    def enable(self):
        """Enable recording"""
        self.enabled = True
        logger.info("SimpleMicRecorder enabled")
        
    def disable(self):
        """Disable recording"""
        self.enabled = False
        logger.info("SimpleMicRecorder disabled")
        
    def get_name(self):
        """Get recorder name"""
        return f"SimpleMicRecorder - {self.source_name}"
        
    def record_audio(self, audio_queue: queue.Queue):
        """
        Start continuous recording in fixed intervals.
        
        This runs in a background thread and puts audio chunks into the queue
        at regular intervals regardless of whether speech is detected.
        """
        logger.info(f"Starting continuous recording with {self.recording_interval}s intervals")
        
        def recording_loop():
            """Main recording loop"""
            while not self.stop_recording:
                if not self.enabled:
                    time.sleep(0.1)
                    continue
                    
                try:
                    # Record for fixed interval
                    logger.debug(f"Recording {self.recording_interval}s chunk...")
                    start_time = datetime.utcnow()
                    
                    with self.source as source:
                        # Record audio for the specified interval
                        audio = self.recorder.record(source, duration=self.recording_interval)
                        
                    if self.enabled:
                        # Get raw audio data
                        data = audio.get_raw_data()
                        
                        # Put in queue immediately - no speech detection
                        audio_queue.put((self.source_name, data, start_time))
                        logger.debug(f"Audio chunk queued: {len(data)} bytes")
                        
                except Exception as e:
                    logger.error(f"Error during recording: {e}")
                    time.sleep(0.5)  # Brief pause before retry
                    
        # Start recording in background thread
        import threading
        self.recording_thread = threading.Thread(target=recording_loop, daemon=True)
        self.recording_thread.start()
        
        # Return stop function
        def stop_func(wait_for_stop=True):
            logger.info("Stopping SimpleMicRecorder")
            self.stop_recording = True
            if wait_for_stop and self.recording_thread.is_alive():
                self.recording_thread.join(timeout=5)
                
        return stop_func
        
    def write_wav_data_to_file(self):
        """Compatibility method - not implemented for simple recorder"""
        pass


# For testing the recorder standalone
if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.DEBUG)
    
    print("Testing SimpleMicRecorder...")
    test_queue = queue.Queue()
    
    recorder = SimpleMicRecorder(recording_interval=2.0)
    stop_func = recorder.record_audio(test_queue)
    
    print("Recording for 10 seconds...")
    start = time.time()
    
    while time.time() - start < 10:
        if not test_queue.empty():
            source, data, timestamp = test_queue.get()
            print(f"Got audio chunk: {len(data)} bytes from {source} at {timestamp}")
        time.sleep(0.1)
        
    print("Stopping recorder...")
    stop_func()
    print("Test complete!")
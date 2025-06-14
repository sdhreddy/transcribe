"""WebRTC VAD-based audio recorder for low-latency speech detection."""
import queue
import threading
import time
import numpy as np
import pyaudio
import webrtcvad
from typing import Optional, Callable
import logging

logger = logging.getLogger(__name__)

class WebRTCVADRecorder:
    """Audio recorder using WebRTC VAD for fast end-of-speech detection."""
    
    def __init__(self, 
                 sample_rate: int = 16000,
                 frame_ms: int = 20,
                 vad_aggressiveness: int = 2,
                 silence_ms: int = 300,
                 audio_queue: Optional[queue.Queue] = None,
                 callback: Optional[Callable] = None):
        """
        Initialize WebRTC VAD recorder.
        
        Args:
            sample_rate: Audio sample rate (must be 8000, 16000, 32000, or 48000)
            frame_ms: Frame duration in ms (must be 10, 20, or 30)
            vad_aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
            silence_ms: Milliseconds of silence before end-of-speech
            audio_queue: Queue to put audio segments
            callback: Optional callback for audio data
        """
        self.sample_rate = sample_rate
        self.frame_ms = frame_ms
        self.frame_size = int(sample_rate * frame_ms / 1000)
        self.vad_aggressiveness = vad_aggressiveness
        self.silence_ms = silence_ms
        self.audio_queue = audio_queue or queue.Queue()
        self.callback = callback
        
        # Initialize VAD
        self.vad = webrtcvad.Vad(vad_aggressiveness)
        
        # PyAudio setup
        self.p = pyaudio.PyAudio()
        self.stream = None
        self.recording = False
        self.thread = None
        
        # Audio buffer and state
        self.audio_buffer = b''
        self.silence_frames = 0
        self.is_speaking = False
        
        # Frame queue for processing
        self.frame_queue = queue.Queue()
        
    def start(self):
        """Start recording."""
        if self.recording:
            return
            
        self.recording = True
        
        # Open audio stream
        self.stream = self.p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.frame_size,
            stream_callback=self._audio_callback
        )
        
        # Start processing thread
        self.thread = threading.Thread(target=self._process_frames)
        self.thread.daemon = True
        self.thread.start()
        
        self.stream.start_stream()
        logger.info(f"WebRTC VAD recorder started (frame={self.frame_ms}ms, silence={self.silence_ms}ms)")
        
    def stop(self):
        """Stop recording."""
        if not self.recording:
            return
            
        self.recording = False
        
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            
        if self.thread:
            self.thread.join(timeout=1.0)
            
        logger.info("WebRTC VAD recorder stopped")
        
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """PyAudio callback to capture audio frames."""
        if status:
            logger.warning(f"PyAudio status: {status}")
            
        # Put frame in processing queue
        self.frame_queue.put(in_data)
        
        return (None, pyaudio.paContinue)
        
    def _process_frames(self):
        """Process audio frames with VAD."""
        while self.recording:
            try:
                # Get frame with timeout
                frame = self.frame_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            # Check if frame contains speech
            is_speech = self.vad.is_speech(frame, self.sample_rate)
            
            if is_speech:
                # Speech detected
                if not self.is_speaking:
                    logger.debug("Speech started")
                    self.is_speaking = True
                    
                self.audio_buffer += frame
                self.silence_frames = 0
                
            else:
                # Silence detected
                if self.is_speaking:
                    self.silence_frames += self.frame_ms
                    
                    # Still add frames during initial silence
                    if self.silence_frames <= self.silence_ms:
                        self.audio_buffer += frame
                    
                    # Check if we've had enough silence
                    if self.silence_frames > self.silence_ms:
                        # End of speech detected
                        logger.debug(f"Speech ended (buffer size: {len(self.audio_buffer)} bytes)")
                        
                        if len(self.audio_buffer) > 0:
                            # Convert to numpy array for compatibility
                            audio_array = np.frombuffer(self.audio_buffer, dtype=np.int16)
                            
                            # Put in queue
                            self.audio_queue.put(audio_array)
                            
                            # Call callback if provided
                            if self.callback:
                                self.callback(audio_array)
                        
                        # Reset state
                        self.audio_buffer = b''
                        self.silence_frames = 0
                        self.is_speaking = False
                        
    def get_audio(self, timeout: Optional[float] = None):
        """Get next audio segment from queue."""
        try:
            return self.audio_queue.get(timeout=timeout)
        except queue.Empty:
            return None
            
    def clear_queue(self):
        """Clear the audio queue."""
        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
                
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
        if self.p:
            self.p.terminate()
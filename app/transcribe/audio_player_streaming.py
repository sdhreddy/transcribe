# app/transcribe/audio_player_streaming.py
import pyaudio
import queue
import threading
import time
import logging
from tsutils import app_logging as al

logger = al.get_module_logger(al.AUDIO_PLAYER_LOGGER)

class StreamingAudioPlayer(threading.Thread):
    """Streaming audio player that plays audio chunks as they arrive."""
    
    def __init__(self, sample_rate=24_000, buf_ms=50, output_device_index=None):
        super().__init__(daemon=True)
        self.q: queue.Queue[bytes] = queue.Queue(maxsize=5)
        self.sample_rate = sample_rate
        self.buf_ms = buf_ms / 1000
        self.running = True
        self.playing = False
        
        try:
            pa = pyaudio.PyAudio()
            
            # Windows fix: List available devices if no device specified
            if output_device_index is None:
                device_count = pa.get_device_count()
                logger.info(f"Found {device_count} audio devices")
                
                # Try to find default output device
                try:
                    default_output = pa.get_default_output_device_info()
                    output_device_index = default_output['index']
                    logger.info(f"Using default output device: {default_output['name']}")
                except Exception:
                    logger.warning("No default output device found, using device 0")
                    output_device_index = 0
            
            # Windows fix: Increase buffer size on Windows for stability
            import platform
            if platform.system() == "Windows":
                buf_ms = max(75, buf_ms)  # Minimum 75ms on Windows
                logger.info(f"Windows detected: Using {buf_ms}ms buffer")
            
            self.stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
                output_device_index=output_device_index,
                frames_per_buffer=int(sample_rate * (buf_ms / 1000))
            )
            logger.info(f"Streaming audio player initialized: {sample_rate}Hz, {buf_ms}ms buffer, device {output_device_index}")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            raise

    def enqueue(self, chunk: bytes):
        """Add audio chunk to playback queue."""
        try:
            self.q.put(chunk, timeout=0.1)
        except queue.Full:
            logger.warning("Audio queue full, dropping chunk")

    def stop(self):
        """Stop the audio player thread."""
        self.running = False
        self.q.put(None)  # Sentinel to unblock

    def run(self):
        """Main playback loop."""
        logger.info("Streaming audio player thread started")
        
        while self.running:
            try:
                chunk = self.q.get(timeout=1.0)
                if chunk is None:
                    break
                    
                self.playing = True
                # Windows fix: Use wait=True on newer PyAudio versions for better stability
                try:
                    self.stream.write(chunk, exception_on_underflow=False)
                except Exception as e:
                    # Fallback for older PyAudio versions
                    self.stream.write(chunk)
                self.playing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Audio playback error: {e}")
                
        self.stream.stop_stream()
        self.stream.close()
        logger.info("Streaming audio player thread stopped")
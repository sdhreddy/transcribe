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
        self.q: queue.Queue[bytes] = queue.Queue(maxsize=100)
        self.sample_rate = sample_rate
        self.buf_ms = buf_ms
        self.running = True
        self.playing = False
        self.output_device_index = output_device_index
        
        try:
            pa = pyaudio.PyAudio()
            
            # Windows fix: List available devices if no device specified
            if output_device_index is None:
                device_count = pa.get_device_count()
                logger.info(f"[Audio Init] Found {device_count} audio devices")
                
                # Try to find default output device
                try:
                    default_output = pa.get_default_output_device_info()
                    output_device_index = default_output['index']
                    self.output_device_index = output_device_index
                    logger.info(f"[Audio Init] Using default output device: {default_output['name']}")
                except Exception as e:
                    logger.warning(f"[Audio Init] No default output device found ({e}), using device 0")
                    output_device_index = 0
                    self.output_device_index = 0
            
            # Windows fix: Increase buffer size on Windows for stability
            import platform
            if platform.system() == "Windows":
                buf_ms = max(75, buf_ms)  # Minimum 75ms on Windows
                logger.info(f"[Audio Init] Windows detected: Using {buf_ms}ms buffer")
            
            frames_per_buffer = int(sample_rate * (buf_ms / 1000))
            logger.info(f"[Audio Init] Creating stream with frames_per_buffer={frames_per_buffer}")
            
            self.stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=sample_rate,
                output=True,
                output_device_index=output_device_index,
                frames_per_buffer=frames_per_buffer
            )
            logger.info(f"[Audio Init] Streaming audio player initialized: {sample_rate}Hz, {buf_ms}ms buffer, device {output_device_index}")
        except Exception as e:
            logger.error(f"[Audio Init] Failed to initialize PyAudio: {type(e).__name__}: {e}")
            import traceback
            logger.error(f"[Audio Init] Traceback:\n{traceback.format_exc()}")
            raise

    def enqueue(self, chunk: bytes):
        """Add audio chunk to playback queue."""
        if self.q.full():
            logger.warning("[TTS] queue full – dropping audio chunk")
            return
        try:
            self.q.put(chunk, timeout=0.1)
        except queue.Full:
            logger.warning("[TTS Debug] Audio queue full, dropping chunk")

    
    def recover_audio(self):
        """Try to recover audio playback after errors."""
        try:
            logger.info("[TTS Debug] Attempting audio recovery...")
            self.stream.stop_stream()
            self.stream.close()
            
            # Reinitialize
            pa = pyaudio.PyAudio()
            self.stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.output_device_index if hasattr(self, 'output_device_index') else None,
                frames_per_buffer=int(self.sample_rate * (self.buf_ms / 1000))
            )
            logger.info("[TTS Debug] Audio recovery successful")
            return True
        except Exception as e:
            logger.error(f"[TTS Debug] Audio recovery failed: {e}")
            return False

    def stop(self):
        """Stop the audio player thread."""
        self.running = False
        self.q.put(None)  # Sentinel to unblock

    def run(self):
        """Main playback loop."""
        logger.info("[TTS Debug] Streaming audio player thread started")
        
        consecutive_errors = 0
        
        while self.running:
            try:
                chunk = self.q.get(timeout=1.0)
                if chunk is None:
                    logger.info("[TTS Debug] Received stop signal")
                    break
                
                # Reset error counter on successful get
                consecutive_errors = 0
                
                self.playing = True
                # Windows fix: Use wait=True on newer PyAudio versions for better stability
                try:
                    bytes_written = self.stream.write(chunk, exception_on_underflow=False)
                    logger.debug(f"[TTS Debug] Wrote {bytes_written if bytes_written else len(chunk)} bytes")
                except Exception as e:
                    # Fallback for older PyAudio versions
                    try:
                        self.stream.write(chunk)
                    except Exception as e2:
                        logger.error(f"[TTS Debug] Failed to write audio: {e2}")
                        consecutive_errors += 1
                        if consecutive_errors > 5:
                            logger.error("[TTS Debug] Too many audio errors, stopping player")
                            break
                
                self.playing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[TTS Debug] Audio playback error: {type(e).__name__}: {e}")
                consecutive_errors += 1
                if consecutive_errors > 5:
                    logger.error("[TTS Debug] Too many errors, stopping player")
                    break
                
        self.stream.stop_stream()
        self.stream.close()
        logger.info("[TTS Debug] Streaming audio player thread stopped")
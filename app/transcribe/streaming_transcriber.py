"""Streaming Whisper transcriber using faster-whisper for low latency."""
import numpy as np
import logging
import queue
import threading
from typing import Optional, Callable, Tuple
from faster_whisper import WhisperModel
import torch

logger = logging.getLogger(__name__)

class StreamingTranscriber:
    """Streaming transcriber using faster-whisper for low-latency transcription."""
    
    def __init__(self,
                 model_size: str = "medium",
                 device: str = "auto",
                 compute_type: str = "float16",
                 language: str = "en",
                 initial_prompt: Optional[str] = None,
                 vad_filter: bool = True,
                 vad_parameters: Optional[dict] = None):
        """
        Initialize streaming transcriber.
        
        Args:
            model_size: Whisper model size
            device: Device to use (auto, cuda, cpu)
            compute_type: Computation type (float16, int8, etc.)
            language: Language code
            initial_prompt: Initial prompt for context
            vad_filter: Whether to use VAD filtering
            vad_parameters: VAD parameters dict
        """
        self.model_size = model_size
        self.language = language
        self.initial_prompt = initial_prompt
        self.vad_filter = vad_filter
        
        # Auto-detect device
        if device == "auto":
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        # Adjust compute type for CPU
        if self.device == "cpu" and compute_type == "float16":
            compute_type = "int8"
            
        self.compute_type = compute_type
        
        # VAD parameters
        self.vad_params = vad_parameters or {
            "threshold": 0.5,
            "min_speech_duration_ms": 250,
            "max_speech_duration_s": float("inf"),
            "min_silence_duration_ms": 2000,
            "speech_pad_ms": 400,
        }
        
        # Initialize model
        logger.info(f"Loading Whisper model: {model_size} on {self.device} with {compute_type}")
        self.model = WhisperModel(
            model_size,
            device=self.device,
            compute_type=compute_type,
            num_workers=1,
            cpu_threads=4
        )
        
        # Processing state
        self.processing_queue = queue.Queue()
        self.result_queue = queue.Queue()
        self.processing_thread = None
        self.running = False
        
    def start(self):
        """Start the transcription processing thread."""
        if self.running:
            return
            
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_audio)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("Streaming transcriber started")
        
    def stop(self):
        """Stop the transcription processing thread."""
        if not self.running:
            return
            
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        logger.info("Streaming transcriber stopped")
        
    def transcribe_audio(self, audio: np.ndarray, callback: Optional[Callable] = None) -> Optional[str]:
        """
        Transcribe audio segment.
        
        Args:
            audio: Audio data as numpy array
            callback: Optional callback for results
            
        Returns:
            Transcribed text or None if async
        """
        if callback:
            # Async mode
            self.processing_queue.put((audio, callback))
            return None
        else:
            # Sync mode
            return self._transcribe_segment(audio)
            
    def _process_audio(self):
        """Background thread to process audio segments."""
        while self.running:
            try:
                # Get audio segment with timeout
                audio, callback = self.processing_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            try:
                # Transcribe segment
                text = self._transcribe_segment(audio)
                
                # Call callback with result
                if callback and text:
                    callback(text)
                    
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                
    def _transcribe_segment(self, audio: np.ndarray) -> Optional[str]:
        """
        Transcribe a single audio segment.
        
        Args:
            audio: Audio data as numpy array
            
        Returns:
            Transcribed text or None
        """
        try:
            # Convert to float32 for faster-whisper
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
                
            # Transcribe with faster-whisper
            segments, info = self.model.transcribe(
                audio,
                language=self.language,
                initial_prompt=self.initial_prompt,
                beam_size=5,
                best_of=5,
                patience=1.0,
                length_penalty=1.0,
                temperature=0.0,
                compression_ratio_threshold=2.4,
                log_prob_threshold=-1.0,
                no_speech_threshold=0.6,
                word_timestamps=False,
                vad_filter=self.vad_filter,
                vad_parameters=self.vad_params
            )
            
            # Collect text from segments
            text_parts = []
            for segment in segments:
                text_parts.append(segment.text.strip())
                
            full_text = " ".join(text_parts)
            
            if full_text:
                logger.debug(f"Transcribed: {full_text}")
                return full_text
            else:
                return None
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
            
    def get_model_info(self) -> dict:
        """Get information about the loaded model."""
        return {
            "model_size": self.model_size,
            "device": self.device,
            "compute_type": self.compute_type,
            "language": self.language,
            "vad_enabled": self.vad_filter
        }
        
    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()
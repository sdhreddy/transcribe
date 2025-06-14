"""Updated AudioTranscriber with streaming support for low latency."""
import sys
import os
import queue
import time
import threading
import logging
from pathlib import Path
import numpy as np

sys.path.append('../..')
import conversation
import constants
from tsutils import app_logging as al
from tsutils import duration, utilities

# Import the new streaming transcriber
from .streaming_transcriber import StreamingTranscriber

logger = al.get_module_logger(al.TRANSCRIBER_LOGGER)

try:
    from transcribe.voice_filter import VoiceFilter
    logger.info("Using production VoiceFilter")
except ImportError:
    try:
        from voice_filter import VoiceFilter
        logger.info("Using local VoiceFilter")
    except ImportError:
        from transcribe.voice_filter_mock import VoiceFilter
        logger.warning("WARNING: Using MockVoiceFilter for testing")


class AudioTranscriber:
    """Audio transcriber with streaming support for low latency."""
    
    def __init__(self, mic_source, speaker_source, model,
                 convo: conversation.Conversation,
                 config: dict):
        """Initialize the audio transcriber with streaming support."""
        logger.info(f"Initializing {self.__class__.__name__}")
        
        self.transcript_changed_event = threading.Event()
        self.last_transcript_update_time = None
        self.config = config
        self.convo = convo
        self.mic_source = mic_source
        self.speaker_source = speaker_source
        
        # Voice filter configuration
        voice_filter_config = config.get('General', {}).get('voice_filter_enabled', 'No')
        if isinstance(voice_filter_config, bool):
            self.voice_filter_enabled = voice_filter_config
        else:
            self.voice_filter_enabled = voice_filter_config == 'Yes'
            
        # Initialize VoiceFilter
        self.voice_filter = None
        if self.voice_filter_enabled:
            try:
                profile_path = config.get('General', {}).get('voice_filter_profile', 'my_voice.npy')
                if not Path(profile_path).is_absolute():
                    profile_path = str(Path('/home/sdhre/transcribe') / profile_path)
                    
                self.voice_filter = VoiceFilter(
                    profile_path=profile_path,
                    similarity_threshold=float(config.get('General', {}).get('voice_filter_threshold', 0.75))
                )
                logger.info(f"VoiceFilter initialized with profile: {profile_path}")
            except Exception as e:
                logger.error(f"Failed to initialize VoiceFilter: {e}")
                self.voice_filter = None
                
        # Check if streaming is enabled
        self.use_streaming = config.get('General', {}).get('use_streaming_transcriber', True)
        
        if self.use_streaming:
            # Initialize streaming transcriber
            self.transcriber = StreamingTranscriber(
                model_size=config.get('OpenAI', {}).get('model', 'medium'),
                device="auto",
                compute_type="float16",
                language="en",
                initial_prompt=config.get('OpenAI', {}).get('initial_prompt'),
                vad_filter=True,
                vad_parameters={
                    "threshold": 0.5,
                    "min_speech_duration_ms": 250,
                    "min_silence_duration_ms": 300,
                    "speech_pad_ms": 200,
                }
            )
            self.transcriber.start()
            logger.info("Streaming transcriber initialized")
        else:
            # Use original model
            self.transcriber = model
            logger.info("Using traditional transcriber")
            
        # Threading
        self.mutex = threading.Lock()
        self.audio_queue = queue.Queue()
        
        # Processing state
        self.processing_thread = None
        self.running = False
        
    def start(self):
        """Start the transcription processing."""
        if self.running:
            return
            
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_audio_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        logger.info("Audio transcriber started")
        
    def stop(self):
        """Stop the transcription processing."""
        if not self.running:
            return
            
        self.running = False
        
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
            
        if self.use_streaming and hasattr(self, 'transcriber'):
            self.transcriber.stop()
            
        logger.info("Audio transcriber stopped")
        
    def transcribe_audio(self, audio_data: np.ndarray, source: str):
        """
        Transcribe audio data from a specific source.
        
        Args:
            audio_data: Audio data as numpy array
            source: Source identifier ("You" or "Speaker")
        """
        self.audio_queue.put((audio_data, source, time.time()))
        
    def _process_audio_queue(self):
        """Process audio segments from the queue."""
        while self.running:
            try:
                # Get audio data with timeout
                audio_data, source, timestamp = self.audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue
                
            try:
                # Apply voice filter if enabled
                if self.voice_filter_enabled and self.voice_filter and source == "You":
                    is_primary_speaker = self.voice_filter.is_primary_speaker(audio_data)
                    
                    if is_primary_speaker:
                        logger.debug("Primary speaker detected - skipping transcription")
                        continue
                    else:
                        logger.debug("Non-primary speaker detected - processing")
                        
                # Transcribe audio
                if self.use_streaming:
                    # Use streaming transcriber
                    text = self.transcriber.transcribe_audio(audio_data)
                else:
                    # Use traditional method
                    text = self._transcribe_traditional(audio_data)
                    
                if text and text.strip():
                    # Update conversation
                    with self.mutex:
                        persona = utilities.get_persona_from_source(source)
                        self.convo.update_conversation(persona, text, time_spoken=timestamp)
                        self.transcript_changed_event.set()
                        self.last_transcript_update_time = time.time()
                        
                    logger.info(f"Transcribed [{source}]: {text}")
                    
            except Exception as e:
                logger.error(f"Error processing audio: {e}")
                
    def _transcribe_traditional(self, audio_data: np.ndarray) -> str:
        """Fallback to traditional transcription method."""
        # Convert numpy array to audio data format expected by the model
        # This would depend on your specific model implementation
        # For now, returning empty string as placeholder
        return ""
        
    def process_speaker_audio(self, audio_data, source):
        """Process audio from speaker source."""
        self.transcribe_audio(audio_data, source)
        
    def process_mic_audio(self, audio_data):
        """Process audio from microphone source.""" 
        self.transcribe_audio(audio_data, "You")
        
    def get_transcript_changed_event(self):
        """Get the transcript changed event."""
        return self.transcript_changed_event
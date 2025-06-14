"""Updated audio recorder with WebRTC VAD support for low-latency recording."""
import sys
import os
import queue
import time
import wave
from datetime import datetime
from abc import abstractmethod

# Import recorder options
try:
    from .mock_mic_recorder import MockMicRecorder
except ImportError:
    MockMicRecorder = None

try:
    from .simple_audio_recorder import SimpleMicRecorder
except ImportError:
    SimpleMicRecorder = None

try:
    from .webrtc_vad_recorder import WebRTCVADRecorder
except ImportError:
    WebRTCVADRecorder = None

import logging
import pyaudio
import custom_speech_recognition as sr
from tsutils import app_logging as al
from tsutils import configuration

sys.path.append('../..')

ENERGY_THRESHOLD = 600
DYNAMIC_ENERGY_THRESHOLD = False

logger = al.get_module_logger(al.AUDIO_RECORDER_LOGGER)

# Original imports and constants remain the same...
# [Include all the DRIVER_TYPE mapping and other constants from original file]

class MicRecorder:
    """Enhanced microphone recorder with WebRTC VAD support."""
    
    def __init__(self, source_name: str = "Default Mic", mic_index=None, 
                 use_webrtc_vad: bool = True, audio_queue: queue.Queue = None):
        """
        Initialize microphone recorder.
        
        Args:
            source_name: Name of the microphone
            mic_index: Microphone device index
            use_webrtc_vad: Whether to use WebRTC VAD (True) or traditional method (False)
            audio_queue: Audio queue for captured segments
        """
        logger.info(f'Initializing MicRecorder (WebRTC VAD: {use_webrtc_vad})')
        
        self.source_name = source_name
        self.enabled = True
        self.use_webrtc_vad = use_webrtc_vad
        self.audio_queue = audio_queue or queue.Queue()
        self.config = configuration.Config().data
        
        if use_webrtc_vad and WebRTCVADRecorder:
            # Initialize WebRTC VAD recorder
            self._init_webrtc_vad()
        else:
            # Fall back to traditional recorder
            self._init_traditional_recorder(mic_index)
            
    def _init_webrtc_vad(self):
        """Initialize WebRTC VAD recorder."""
        # Get VAD parameters from config
        vad_params = self.config.get('vad_parameters', {})
        
        self.vad_recorder = WebRTCVADRecorder(
            sample_rate=16000,
            frame_ms=vad_params.get('frame_ms', 20),
            vad_aggressiveness=vad_params.get('aggressiveness', 2),
            silence_ms=vad_params.get('silence_ms', 300),
            audio_queue=self.audio_queue
        )
        
        # Start recording immediately
        self.vad_recorder.start()
        logger.info("WebRTC VAD recorder initialized and started")
        
    def _init_traditional_recorder(self, mic_index):
        """Initialize traditional speech recognition recorder."""
        self.recorder = sr.Recognizer()
        self.recorder.energy_threshold = ENERGY_THRESHOLD
        self.recorder.dynamic_energy_threshold = DYNAMIC_ENERGY_THRESHOLD
        self.recorder.pause_threshold = 0.6
        self.recorder.non_speaking_duration = 0.5
        
        # Set up microphone
        self.mic_index = mic_index or self._get_default_mic_index()
        self.source = sr.Microphone(device_index=self.mic_index)
        
        # Set up background listening
        self.stop_listening = None
        
    def _get_default_mic_index(self):
        """Get default microphone index."""
        pa = pyaudio.PyAudio()
        try:
            default = pa.get_default_input_device_info()
            return default['index']
        except Exception:
            return None
        finally:
            pa.terminate()
            
    def record_callback(self, audio_queue, phrase_time_limit):
        """
        Callback for traditional recorder to match WebRTC VAD interface.
        
        This wraps the traditional callback to work with the audio queue.
        """
        def callback(recognizer, audio):
            # Convert audio data to numpy array
            audio_data = audio.get_raw_data()
            import numpy as np
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Put in queue
            self.audio_queue.put(audio_array)
            
        if self.use_webrtc_vad:
            # WebRTC VAD handles its own callbacks
            return None
        else:
            # Traditional method
            return callback
            
    def start_recording(self, audio_queue, phrase_time_limit):
        """Start recording with the selected method."""
        if self.use_webrtc_vad:
            # Already started in init
            logger.info("WebRTC VAD recorder already running")
        else:
            # Traditional method
            callback = self.record_callback(audio_queue, phrase_time_limit)
            self.stop_listening = self.recorder.listen_in_background(
                self.source, 
                callback,
                phrase_time_limit=phrase_time_limit
            )
            logger.info("Traditional recorder started in background")
            
    def stop_recording(self):
        """Stop recording."""
        if self.use_webrtc_vad and hasattr(self, 'vad_recorder'):
            self.vad_recorder.stop()
        elif hasattr(self, 'stop_listening') and self.stop_listening:
            self.stop_listening(wait_for_stop=False)
            
    def enable(self):
        """Enable transcription from this device."""
        self.enabled = True
        
    def disable(self):
        """Disable transcription from this device."""
        self.enabled = False
        
    def get_name(self):
        """Get the name of this device."""
        return self.source_name
        
    def clear_queue(self):
        """Clear the audio queue."""
        if self.use_webrtc_vad and hasattr(self, 'vad_recorder'):
            self.vad_recorder.clear_queue()
        else:
            while not self.audio_queue.empty():
                try:
                    self.audio_queue.get_nowait()
                except queue.Empty:
                    break
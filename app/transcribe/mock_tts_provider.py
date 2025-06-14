"""Mock TTS provider for testing without API calls."""

import time
import struct
import math
import os
from app.transcribe.streaming_tts import BaseTTS

class MockTTS(BaseTTS):
    """Mock TTS provider that generates synthetic audio for testing."""
    
    def __init__(self, cfg):
        super().__init__(cfg)
        self.latency = 0.1  # Simulate 100ms latency
        
    def stream(self, text: str):
        """Generate mock audio chunks for the given text."""
        # Simulate initial latency
        time.sleep(self.latency)
        
        # Calculate audio duration based on text length
        # Assume 150 words per minute speaking rate
        words = len(text.split())
        duration = (words / 150) * 60  # seconds
        
        # Generate audio at 24kHz, 16-bit mono
        sample_rate = self.cfg.sample_rate
        total_samples = int(sample_rate * duration)
        chunk_size = 4096  # bytes
        samples_per_chunk = chunk_size // 2  # 16-bit = 2 bytes per sample
        
        # Generate chunks
        samples_generated = 0
        chunk_count = 0
        
        while samples_generated < total_samples:
            # Generate a chunk of audio (simple sine wave for testing)
            chunk_samples = min(samples_per_chunk, total_samples - samples_generated)
            
            # Create audio data (440Hz tone with envelope)
            audio_data = []
            for i in range(chunk_samples):
                t = (samples_generated + i) / sample_rate
                # Simple envelope to avoid clicks
                envelope = min(1.0, (samples_generated + i) / 1000, (total_samples - samples_generated - i) / 1000)
                sample = int(envelope * 0.3 * 32767 * math.sin(2 * math.pi * 440 * t))
                audio_data.append(sample)
            
            # Convert to bytes
            chunk_bytes = struct.pack('<%dh' % len(audio_data), *audio_data)
            
            # Log first chunk for debugging
            if chunk_count == 0:
                print(f"[Mock TTS] First audio chunk: {len(chunk_bytes)} bytes")
            
            yield chunk_bytes
            
            samples_generated += chunk_samples
            chunk_count += 1
            
            # Simulate streaming delay between chunks
            time.sleep(0.01)
        
        print(f"[Mock TTS] Complete: {chunk_count} chunks, {samples_generated*2} bytes")

# Monkey-patch the TTS factory when in test mode
def enable_mock_tts():
    """Enable mock TTS for testing."""
    import app.transcribe.streaming_tts as tts_module
    
    # Save original factory
    original_create_tts = tts_module.create_tts
    
    def mock_create_tts(cfg):
        """Create mock TTS when in test mode."""
        if os.environ.get('USE_MOCK_TTS', 'false').lower() == 'true':
            print("[TTS] Using MockTTS for testing")
            return MockTTS(cfg)
        return original_create_tts(cfg)
    
    # Replace factory
    tts_module.create_tts = mock_create_tts
    
    print("[TTS] Mock TTS provider enabled")
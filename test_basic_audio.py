#!/usr/bin/env python3
"""Simple test to verify streaming audio works."""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_audio():
    """Test basic audio functionality."""
    print("BASIC AUDIO TEST")
    print("=" * 40)
    
    try:
        # Test 1: Audio player
        print("\n1. Testing audio player...")
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
        
        player = StreamingAudioPlayer()
        player.start()
        print("   ✅ Audio player started")
        
        # Create a simple beep sound (1kHz sine wave)
        import math
        sample_rate = 24000
        duration = 0.5  # 500ms beep
        frequency = 1000  # 1kHz
        
        samples = []
        for i in range(int(sample_rate * duration)):
            sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            samples.extend([sample & 0xFF, (sample >> 8) & 0xFF])  # Little-endian
        
        audio_data = bytes(samples)
        
        print("   Playing test beep...")
        player.enqueue(audio_data)
        time.sleep(1)  # Wait for playback
        
        player.stop()
        print("   ✅ Audio test complete")
        
        # Test 2: TTS
        print("\n2. Testing TTS...")
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        
        tts = create_tts(TTSConfig(provider="openai"))
        
        chunks = 0
        for chunk in tts.stream("Testing audio playback."):
            chunks += 1
            player.enqueue(chunk)
        
        print(f"   ✅ TTS generated {chunks} chunks")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {type(e).__name__}: {e}")
        return False

if __name__ == "__main__":
    print("Testing basic audio functionality...\n")
    
    if test_basic_audio():
        print("\n✅ Basic audio test passed!")
    else:
        print("\n❌ Basic audio test failed!")

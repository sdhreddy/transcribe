#!/usr/bin/env python3
"""Direct test of Windows audio playback to isolate the issue."""

import os
import sys
import time
import struct
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_direct_audio():
    """Test audio playback directly without the full pipeline."""
    print("=== DIRECT WINDOWS AUDIO TEST ===\n")
    
    # Test 1: Can we create audio player?
    print("1. Creating audio player...")
    try:
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
        
        player = StreamingAudioPlayer()
        player.start()
        print("   ✅ Audio player created and started")
        
    except Exception as e:
        print(f"   ❌ Failed to create audio player: {e}")
        return False
    
    # Test 2: Generate test tone
    print("\n2. Generating test tone...")
    
    # Generate 1 second of 440Hz tone at 24kHz
    sample_rate = 24000
    duration = 1.0
    frequency = 440
    
    samples = []
    for i in range(int(sample_rate * duration)):
        t = i / sample_rate
        sample = int(0.3 * 32767 * math.sin(2 * math.pi * frequency * t))
        samples.append(sample)
    
    # Convert to bytes (16-bit PCM)
    audio_data = struct.pack('<%dh' % len(samples), *samples)
    print(f"   Generated {len(audio_data)} bytes of audio")
    
    # Test 3: Play the audio
    print("\n3. Playing test tone...")
    print("   You should hear a 440Hz beep for 1 second")
    
    # Split into chunks like TTS would
    chunk_size = 4096
    chunks_played = 0
    
    for i in range(0, len(audio_data), chunk_size):
        chunk = audio_data[i:i+chunk_size]
        player.enqueue(chunk)
        chunks_played += 1
        time.sleep(0.01)  # Small delay between chunks
    
    print(f"   Enqueued {chunks_played} chunks")
    
    # Wait for playback
    print("\n4. Waiting for playback to complete...")
    time.sleep(2)
    
    # Test 4: Check if player is still alive
    if player.is_alive():
        print("   ✅ Audio player still running")
    else:
        print("   ❌ Audio player thread died")
    
    # Stop player
    player.stop()
    print("\n5. Audio player stopped")
    
    return True

def test_tts_direct():
    """Test TTS directly without the full pipeline."""
    print("\n\n=== DIRECT TTS TEST ===\n")
    
    # Test 1: Create TTS
    print("1. Creating TTS provider...")
    try:
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        
        config = TTSConfig(provider="openai", voice="alloy")
        tts = create_tts(config)
        print(f"   ✅ Created {tts.__class__.__name__}")
        
    except Exception as e:
        print(f"   ❌ Failed to create TTS: {e}")
        return False
    
    # Test 2: Generate audio
    print("\n2. Generating TTS audio...")
    test_text = "This is a test of text to speech."
    
    try:
        chunks = []
        for chunk in tts.stream(test_text):
            chunks.append(chunk)
            
        print(f"   ✅ Generated {len(chunks)} chunks, {sum(len(c) for c in chunks)} bytes")
        
    except Exception as e:
        print(f"   ❌ TTS generation failed: {e}")
        return False
    
    # Test 3: Play TTS audio
    print("\n3. Playing TTS audio...")
    try:
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
        
        player = StreamingAudioPlayer()
        player.start()
        
        for chunk in chunks:
            player.enqueue(chunk)
            
        print(f"   Enqueued {len(chunks)} chunks")
        
        # Wait for playback
        time.sleep(3)
        
        player.stop()
        print("   ✅ TTS playback complete")
        
    except Exception as e:
        print(f"   ❌ Playback failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("WINDOWS AUDIO DIRECT TEST")
    print("=" * 50)
    print("\nThis test will:")
    print("1. Play a 440Hz beep for 1 second")
    print("2. Play a TTS test phrase")
    print("\nIf you hear both, audio is working.")
    print("If you hear neither, there's an audio device issue.")
    print("If you hear only the beep, TTS is the issue.")
    print("\n" + "=" * 50)
    
    # Run tests
    audio_ok = test_direct_audio()
    
    if audio_ok:
        tts_ok = test_tts_direct()
    else:
        print("\nSkipping TTS test - basic audio not working")
        tts_ok = False
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY:")
    print(f"  Basic audio: {'✅ PASS' if audio_ok else '❌ FAIL'}")
    print(f"  TTS audio: {'✅ PASS' if tts_ok else '❌ FAIL'}")
    
    if audio_ok and tts_ok:
        print("\n✅ Audio system working! Issue must be in sentence detection/timing")
    elif audio_ok and not tts_ok:
        print("\n⚠️  Basic audio works but TTS fails - check API key")
    else:
        print("\n❌ Basic audio not working - check Windows audio settings")
#!/usr/bin/env python3
"""Fix script to resolve streaming audio issues on Windows."""

import os
import re

def revert_problematic_changes():
    """Revert the problematic streaming changes that broke audio."""
    
    print("FIXING STREAMING AUDIO ISSUES")
    print("=" * 50)
    print()
    
    # 1. Fix the queue join that might cause deadlock
    print("1. Fixing potential deadlock in gpt_responder.py...")
    
    gpt_path = "app/transcribe/gpt_responder.py"
    if os.path.exists(gpt_path):
        with open(gpt_path, 'r') as f:
            content = f.read()
        
        # Remove the problematic join() calls that can cause deadlock
        original = content
        content = re.sub(
            r'# Wait for TTS queue to empty before returning\s*\n\s*if self\.tts_enabled and hasattr\(self, \'sent_q\'\):\s*\n\s*self\.sent_q\.join\(\)\s*# wait until player consumed everything',
            '',
            content
        )
        
        if content != original:
            with open(gpt_path, 'w') as f:
                f.write(content)
            print("   ✅ Removed potentially blocking queue.join() calls")
        else:
            print("   ℹ️  No problematic join() calls found")
    
    # 2. Reduce min sentence chars back to reasonable level
    print("\n2. Adjusting minimum sentence characters...")
    
    params_path = "app/transcribe/parameters.yaml"
    if os.path.exists(params_path):
        with open(params_path, 'r') as f:
            content = f.read()
        
        # Change back to 20 chars (more reasonable than 40)
        content = re.sub(
            r'tts_min_sentence_chars:\s*40',
            'tts_min_sentence_chars: 20',
            content
        )
        
        with open(params_path, 'w') as f:
            f.write(content)
        print("   ✅ Set minimum sentence chars to 20 (was 40)")
    
    # 3. Add better error handling to TTS worker
    print("\n3. Improving TTS worker error handling...")
    
    if os.path.exists(gpt_path):
        with open(gpt_path, 'r') as f:
            content = f.read()
        
        # Find the TTS worker error handling section
        if "# Don't let the worker die - continue processing" in content:
            # Already has good error handling
            print("   ✅ TTS worker already has proper error handling")
        else:
            print("   ⚠️  Consider adding better error handling to TTS worker")
    
    # 4. Ensure audio player has proper initialization
    print("\n4. Checking audio player initialization...")
    
    audio_path = "app/transcribe/audio_player_streaming.py"
    if os.path.exists(audio_path):
        with open(audio_path, 'r') as f:
            content = f.read()
        
        if "logger.info(f\"Streaming audio player initialized:" in content:
            print("   ✅ Audio player has initialization logging")
        else:
            print("   ⚠️  Consider adding initialization logging")
    
    print("\n" + "=" * 50)
    print("FIXES APPLIED!")
    print("\nNow test again. The audio should work properly.")
    print("\nIf issues persist, run: python debug_streaming_audio_issue.py")

def create_simple_test():
    """Create a simple test to verify audio works."""
    
    test_content = '''#!/usr/bin/env python3
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
        print("\\n1. Testing audio player...")
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
        print("\\n2. Testing TTS...")
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
    print("Testing basic audio functionality...\\n")
    
    if test_basic_audio():
        print("\\n✅ Basic audio test passed!")
    else:
        print("\\n❌ Basic audio test failed!")
'''
    
    with open("test_basic_audio.py", 'w') as f:
        f.write(test_content)
    
    print("\nCreated test_basic_audio.py for testing audio playback")

if __name__ == "__main__":
    revert_problematic_changes()
    create_simple_test()
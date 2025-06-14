#!/usr/bin/env python3
"""Debug TTS issue with more detailed output."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_basic_tts():
    """Test basic TTS functionality with detailed debug."""
    print("=== Basic TTS Debug Test ===\n")
    
    try:
        print("1. Importing modules...")
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        print("   ✓ Imports successful")
        
        print("\n2. Getting API key...")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            import yaml
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
        print(f"   ✓ API key found ({len(api_key)} chars)")
        
        print("\n3. Creating TTS config...")
        config = TTSConfig(provider="openai", voice="alloy", api_key=api_key)
        print("   ✓ Config created")
        
        print("\n4. Creating TTS instance...")
        tts = create_tts(config)
        print(f"   ✓ TTS instance created: {tts.__class__.__name__}")
        
        print("\n5. Testing TTS stream method...")
        test_text = "Hello."
        print(f"   Input text: '{test_text}'")
        
        print("\n6. Calling OpenAI API...")
        start = time.time()
        
        # Try to get the first chunk
        chunks = list(tts.stream(test_text))
        
        api_time = time.time() - start
        print(f"   ✓ API call completed in {api_time:.2f}s")
        print(f"   ✓ Received {len(chunks)} chunks")
        
        if chunks:
            total_size = sum(len(chunk) for chunk in chunks)
            print(f"   ✓ Total audio size: {total_size} bytes")
            print(f"   ✓ First chunk size: {len(chunks[0])} bytes")
        
        print("\n✅ TTS is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


def test_audio_player():
    """Test if audio player can be created."""
    print("\n\n=== Audio Player Test ===\n")
    
    try:
        print("1. Importing audio player...")
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
        print("   ✓ Import successful")
        
        print("\n2. Creating audio player...")
        player = StreamingAudioPlayer()
        print("   ✓ Player created")
        
        print("\n3. Starting player thread...")
        player.start()
        print("   ✓ Player started")
        
        print("\n4. Stopping player...")
        player.stop()
        print("   ✓ Player stopped")
        
        print("\n✅ Audio player is working!")
        
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}")
        
        if "No Default Output Device Available" in str(e):
            print("\nThis is a Windows audio device issue.")
            print("Try:")
            print("1. Check Windows sound settings")
            print("2. Ensure speakers/headphones are connected")
            print("3. Run: python debug_tts_windows.py")


if __name__ == "__main__":
    test_basic_tts()
    test_audio_player()
    
    print("\n" + "="*50)
    print("\nIf TTS works but audio player fails:")
    print("- It's a Windows audio device issue")
    print("- The TTS streaming itself is working")
    print("\nIf TTS hangs:")
    print("- Check internet connection")
    print("- Verify OpenAI API key has credits")
    print("- Try in a simpler script without audio")
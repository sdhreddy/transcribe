#!/usr/bin/env python3
"""Quick sanity test for TTS streaming to verify bytes are returned."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tts_returns_bytes():
    """Test that TTS stream returns bytes, not AudioResponseChunk objects."""
    print("=== TTS SANITY TEST ===\n")
    
    try:
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        
        print("1. Creating OpenAI TTS instance...")
        tts = create_tts(TTSConfig(provider="openai", voice="alloy"))
        
        print("2. Testing stream output...")
        test_text = "Hello streaming world."
        
        # Get first chunk
        first = next(tts.stream(test_text))
        
        # Verify it's bytes
        if isinstance(first, (bytes, bytearray)):
            print(f"✅ First chunk is bytes: {len(first)} bytes")
            print(f"   Type: {type(first).__name__}")
            
            if len(first) > 500:
                print("✅ Chunk size looks good (>500 bytes)")
            else:
                print("⚠️  Chunk might be too small")
                
            return True
        else:
            print(f"❌ ERROR: First chunk is {type(first).__name__}, not bytes!")
            print(f"   This will cause audio player to drop chunks silently")
            return False
            
    except StopIteration:
        print("❌ ERROR: No chunks returned from TTS stream")
        return False
        
    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}: {e}")
        
        # If it's an API key issue, provide helpful message
        if "api_key" in str(e).lower():
            print("\nMake sure OpenAI API key is set in override.yaml")
        
        import traceback
        traceback.print_exc()
        return False

def test_expected_behavior():
    """Show what should happen when working correctly."""
    print("\n=== EXPECTED BEHAVIOR ===\n")
    
    print("When everything works correctly:")
    print("1. Colleague speaks one long sentence")
    print("2. Visual tokens appear in UI")
    print("3. <0.3s later you hear audio playing")
    print("4. Audio plays through completely")
    print("5. Second colleague sentence triggers its own audio")
    print("6. No silence, no lock-ups")
    
    print("\nConsole should show:")
    print("- [TTS Debug] Token received: ...")
    print("- [TTS Debug] Sentence detected: ...")
    print("- [TTS Debug] First audio chunk received in XXXms")
    print("- [TTS Debug] TTS completed: XX chunks")

if __name__ == "__main__":
    # Check virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not activated!")
        print("   Run: source venv/bin/activate\n")
    
    # Run sanity test
    success = test_tts_returns_bytes()
    
    # Show expected behavior
    test_expected_behavior()
    
    if success:
        print("\n✅ Sanity test PASSED - TTS returns bytes correctly")
    else:
        print("\n❌ Sanity test FAILED - Fix the issues above")
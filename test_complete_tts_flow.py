#!/usr/bin/env python3
"""Test the complete TTS flow to identify where audio is failing."""

import os
import sys
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_tts_flow():
    """Test each component of the TTS flow."""
    print("=== TESTING COMPLETE TTS FLOW ===\n")
    
    # Test 1: Load config
    print("1. Loading configuration...")
    from tsutils import configuration
    config = configuration.Config().data
    
    tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
    tts_provider = config.get('General', {}).get('tts_provider', 'gtts')
    
    print(f"   tts_streaming_enabled: {tts_enabled}")
    print(f"   tts_provider: {tts_provider}")
    
    if not tts_enabled:
        print("   ❌ TTS is disabled!")
        return
    
    # Test 2: Create TTS provider
    print("\n2. Creating TTS provider...")
    try:
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        
        tts_config = TTSConfig(
            provider=tts_provider,
            voice=config.get('General', {}).get('tts_voice', 'alloy'),
            sample_rate=config.get('General', {}).get('tts_sample_rate', 24000)
        )
        
        tts = create_tts(tts_config)
        print(f"   ✅ Created {tts.__class__.__name__}")
        
    except Exception as e:
        print(f"   ❌ Failed to create TTS: {type(e).__name__}: {e}")
        return
    
    # Test 3: Generate audio
    print("\n3. Testing TTS audio generation...")
    test_text = "This is a test of the streaming text to speech system."
    
    try:
        chunks_received = 0
        total_bytes = 0
        
        print(f"   Generating audio for: '{test_text}'")
        
        for chunk in tts.stream(test_text):
            chunks_received += 1
            
            if isinstance(chunk, bytes):
                total_bytes += len(chunk)
                if chunks_received == 1:
                    print(f"   ✅ First chunk: {len(chunk)} bytes (type: {type(chunk).__name__})")
            else:
                print(f"   ❌ Chunk {chunks_received} is not bytes! Type: {type(chunk).__name__}")
                return
        
        print(f"   ✅ Total: {chunks_received} chunks, {total_bytes} bytes")
        
    except Exception as e:
        print(f"   ❌ TTS generation failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Test 4: Check Windows console output
    print("\n4. Check Windows Console for:")
    print("   - [TTS Debug] messages showing chunks being processed")
    print("   - [TTS Debug] First audio chunk from OpenAI: XXXX bytes")
    print("   - [TTS Debug] OpenAI TTS complete: XX chunks, XXXXX bytes")
    print("   - Any error messages")
    
    print("\n5. Common Issues:")
    print("   - If no [TTS Debug] messages: TTS worker thread not running")
    print("   - If chunks not bytes: Iterator issue (should be fixed now)")
    print("   - If no audio playback: Audio device or queue issue")

if __name__ == "__main__":
    # Test in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual environment active\n")
    else:
        print("⚠️  Virtual environment not active!\n")
    
    test_tts_flow()
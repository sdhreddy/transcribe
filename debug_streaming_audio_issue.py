#!/usr/bin/env python3
"""Debug script to identify why audio is not playing after streaming TTS changes."""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_configuration():
    """Check if TTS is properly configured."""
    print("=== CHECKING TTS CONFIGURATION ===\n")
    
    from tsutils import configuration
    config = configuration.Config().data
    
    # Check TTS settings
    tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
    tts_provider = config.get('General', {}).get('tts_provider', 'gtts')
    min_chars = config.get('General', {}).get('tts_min_sentence_chars', 10)
    
    print(f"1. Streaming TTS enabled: {tts_enabled}")
    print(f"2. TTS provider: {tts_provider}")
    print(f"3. Min sentence chars: {min_chars}")
    
    if not tts_enabled:
        print("\n❌ ISSUE: Streaming TTS is disabled!")
        return False
        
    if min_chars > 40:
        print(f"\n⚠️  WARNING: Min sentence chars is high ({min_chars}), might delay audio")
    
    return True

def test_audio_player():
    """Test if audio player can initialize."""
    print("\n=== TESTING AUDIO PLAYER ===\n")
    
    try:
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
        
        print("1. Creating audio player...")
        player = StreamingAudioPlayer()
        print("   ✅ Audio player created successfully")
        
        print("2. Starting audio player thread...")
        player.start()
        print("   ✅ Audio player thread started")
        
        # Test enqueueing
        print("3. Testing audio queue...")
        test_data = b'\x00' * 1000  # Silent audio
        player.enqueue(test_data)
        print("   ✅ Audio enqueue successful")
        
        player.stop()
        print("   ✅ Audio player stopped cleanly")
        
        return True
        
    except Exception as e:
        print(f"   ❌ Audio player error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_tts_provider():
    """Test if TTS provider works."""
    print("\n=== TESTING TTS PROVIDER ===\n")
    
    try:
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        from tsutils import configuration
        
        config = configuration.Config().data
        tts_provider = config.get('General', {}).get('tts_provider', 'gtts')
        
        print(f"1. Creating {tts_provider} TTS provider...")
        tts = create_tts(TTSConfig(provider=tts_provider))
        print(f"   ✅ {tts_provider} TTS created")
        
        print("2. Testing TTS stream...")
        test_text = "This is a test sentence for debugging streaming TTS functionality."
        
        chunk_count = 0
        total_bytes = 0
        
        for chunk in tts.stream(test_text):
            chunk_count += 1
            total_bytes += len(chunk)
            if chunk_count == 1:
                print(f"   ✅ First chunk received: {len(chunk)} bytes")
        
        print(f"   ✅ Total: {chunk_count} chunks, {total_bytes} bytes")
        
        return True
        
    except Exception as e:
        print(f"   ❌ TTS provider error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_responder_state():
    """Check if responder initializes with TTS properly."""
    print("\n=== CHECKING RESPONDER TTS STATE ===\n")
    
    try:
        from app.transcribe import app_utils
        from app.transcribe.global_vars import TranscriptionGlobals
        from tsutils import configuration
        
        config = configuration.Config().data
        global_vars = TranscriptionGlobals()
        global_vars.config = config
        
        print("1. Creating GPT responder...")
        responder = app_utils.create_responder(
            provider_name=config['General']['chat_inference_provider'],
            config=config,
            convo=global_vars.convo,
            save_to_file=False,
            response_file_name="test.txt"
        )
        
        print(f"   Responder type: {type(responder).__name__}")
        
        # Check TTS attributes
        if hasattr(responder, 'tts_enabled'):
            print(f"   ✅ TTS enabled: {responder.tts_enabled}")
        else:
            print("   ❌ No tts_enabled attribute!")
            
        if hasattr(responder, 'tts'):
            print(f"   ✅ TTS provider: {type(responder.tts).__name__}")
        else:
            print("   ❌ No TTS provider initialized!")
            
        if hasattr(responder, 'player'):
            print(f"   ✅ Audio player: {type(responder.player).__name__}")
            print(f"      Running: {responder.player.is_alive() if hasattr(responder.player, 'is_alive') else 'Unknown'}")
        else:
            print("   ❌ No audio player initialized!")
            
        if hasattr(responder, 'tts_worker_thread'):
            print(f"   ✅ TTS worker thread exists")
            print(f"      Running: {responder.tts_worker_thread.is_alive()}")
        else:
            print("   ❌ No TTS worker thread!")
            
        return True
        
    except Exception as e:
        print(f"   ❌ Responder error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_common_issues():
    """Check for common issues that might prevent audio."""
    print("\n=== CHECKING COMMON ISSUES ===\n")
    
    issues = []
    
    # Check if override.yaml has API key
    if os.path.exists("app/transcribe/override.yaml"):
        with open("app/transcribe/override.yaml", 'r') as f:
            content = f.read()
            if "YOUR_API_KEY" in content or "api_key: null" in content:
                issues.append("OpenAI API key not set in override.yaml")
    
    # Check if min_sentence_chars is too high
    from tsutils import configuration
    config = configuration.Config().data
    min_chars = config.get('General', {}).get('tts_min_sentence_chars', 10)
    if min_chars >= 40:
        issues.append(f"Min sentence chars ({min_chars}) might be too high - sentences won't trigger audio until they're long")
    
    # Check dependencies
    try:
        import openai
        import pyaudio
    except ImportError as e:
        issues.append(f"Missing dependency: {e}")
    
    if issues:
        print("Found potential issues:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
    else:
        print("   ✅ No common issues found")
    
    return len(issues) == 0

def main():
    """Run all debug checks."""
    print("STREAMING TTS DEBUG DIAGNOSTIC")
    print("=" * 50)
    print()
    
    # Enable debug logging
    logging.basicConfig(level=logging.DEBUG)
    
    all_good = True
    
    # Run checks
    all_good &= check_configuration()
    all_good &= test_audio_player()
    all_good &= test_tts_provider()
    all_good &= check_responder_state()
    all_good &= check_common_issues()
    
    print("\n" + "=" * 50)
    if all_good:
        print("✅ All checks passed!")
        print("\nIf audio still doesn't work, check the console logs for:")
        print("- [TTS Debug] messages")
        print("- Any error messages during runtime")
        print("- Whether sentences are being detected")
    else:
        print("❌ Some checks failed - see above for details")
        print("\nFix the issues and try again.")

if __name__ == "__main__":
    # Check virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Virtual environment not activated!")
        print("   Run: source venv/bin/activate\n")
    
    main()
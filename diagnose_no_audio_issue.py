#!/usr/bin/env python3
"""Diagnose why there's no audio output despite all fixes."""

import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable all debug logging
logging.basicConfig(level=logging.DEBUG)

def check_audio_flow():
    """Check each step of the audio flow to find where it breaks."""
    print("=== DIAGNOSING NO AUDIO ISSUE ===\n")
    
    # Step 1: Check if TTS is enabled
    print("1. Checking TTS configuration...")
    from tsutils import configuration
    config = configuration.Config().data
    
    tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
    tts_provider = config.get('General', {}).get('tts_provider', 'gtts')
    
    print(f"   tts_streaming_enabled: {tts_enabled}")
    print(f"   tts_provider: {tts_provider}")
    
    if not tts_enabled:
        print("   ❌ ISSUE: Streaming TTS is disabled!")
        return
    
    # Step 2: Check if responder has TTS components
    print("\n2. Checking if responder initializes TTS...")
    try:
        from app.transcribe import app_utils
        from app.transcribe.global_vars import TranscriptionGlobals
        
        global_vars = TranscriptionGlobals()
        global_vars.config = config
        
        responder = app_utils.create_responder(
            provider_name=config['General']['chat_inference_provider'],
            config=config,
            convo=global_vars.convo,
            save_to_file=False,
            response_file_name="test.txt"
        )
        
        print(f"   Responder type: {type(responder).__name__}")
        print(f"   Has tts_enabled: {hasattr(responder, 'tts_enabled')}")
        if hasattr(responder, 'tts_enabled'):
            print(f"   tts_enabled value: {responder.tts_enabled}")
        
        print(f"   Has tts: {hasattr(responder, 'tts')}")
        print(f"   Has player: {hasattr(responder, 'player')}")
        print(f"   Has tts_worker_thread: {hasattr(responder, 'tts_worker_thread')}")
        
        if hasattr(responder, 'tts_worker_thread'):
            print(f"   TTS worker alive: {responder.tts_worker_thread.is_alive()}")
        
    except Exception as e:
        print(f"   ❌ Error creating responder: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Step 3: Check OpenAI TTS stream parameter
    print("\n3. Checking OpenAI TTS implementation...")
    
    # Look at the source code
    streaming_tts_path = "app/transcribe/streaming_tts.py"
    if os.path.exists(streaming_tts_path):
        with open(streaming_tts_path, 'r') as f:
            content = f.read()
            
        if "stream=True" in content:
            print("   ⚠️  WARNING: Code has 'stream=True' parameter")
            print("   This parameter might not be supported by OpenAI TTS API")
            print("   The API returns a streaming response by default when using iter_bytes()")
        
        if "resp.iter_bytes(" in content:
            print("   ✅ Using iter_bytes() correctly")
        else:
            print("   ❌ Not using iter_bytes()")
    
    # Step 4: Check for error handling
    print("\n4. Checking error handling in TTS worker...")
    
    gpt_path = "app/transcribe/gpt_responder.py"
    if os.path.exists(gpt_path):
        with open(gpt_path, 'r') as f:
            content = f.read()
            
        if "task_done()" in content:
            print("   ✅ Has task_done() calls")
        else:
            print("   ❌ Missing task_done() calls")
            
        if "except Exception as e:" in content and "TTS worker error" in content:
            print("   ✅ Has error handling in TTS worker")
        else:
            print("   ⚠️  Limited error handling")
    
    # Step 5: Suggest fixes
    print("\n5. RECOMMENDED FIXES:")
    print("   a) Remove 'stream=True' parameter from OpenAI TTS call")
    print("   b) Add more logging to see if TTS chunks are being generated")
    print("   c) Check Windows console for [TTS Debug] messages")
    print("   d) Verify API key is valid for OpenAI TTS")

def check_recent_changes():
    """Check what changed in recent commits."""
    print("\n6. Recent changes that might affect audio:")
    
    import subprocess
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-5", "--", "app/transcribe/streaming_tts.py"],
            capture_output=True,
            text=True
        )
        if result.stdout:
            print("   Recent streaming_tts.py changes:")
            print(result.stdout)
    except:
        pass

if __name__ == "__main__":
    check_audio_flow()
    check_recent_changes()
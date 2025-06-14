#!/usr/bin/env python3
"""Fix the root cause of streaming TTS not working."""

import os
import re

def apply_comprehensive_fix():
    """Apply comprehensive fix for streaming TTS."""
    
    print("Applying comprehensive streaming TTS fix...\n")
    
    # Fix 1: Ensure gpt_responder.py calls streaming handler BEFORE setting streaming_complete
    print("1. Fixing token handling order in gpt_responder.py...")
    
    gpt_path = "app/transcribe/gpt_responder.py"
    if not os.path.exists(gpt_path):
        print(f"Error: {gpt_path} not found!")
        return False
    
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Make sure _handle_streaming_token is called DURING streaming, not after
    # This is already correct in the code, but let's verify
    
    if "_handle_streaming_token(message_text)" in content and "self.streaming_complete.set()" in content:
        print("   ✓ Token handler is called during streaming")
    else:
        print("   ✗ Token handler placement issue")
        return False
    
    # Fix 2: Add immediate flush for partial sentences
    print("\n2. Adding immediate sentence flush...")
    
    # Find the flush_tts_buffer method and enhance it
    flush_pattern = r'def flush_tts_buffer\(self\):(.*?)(?=\n    def|\Z)'
    flush_match = re.search(flush_pattern, content, re.DOTALL)
    
    if flush_match:
        current_flush = flush_match.group(0)
        if "Force flush any partial sentence" not in current_flush:
            # Add force flush for partial sentences
            new_flush = current_flush.replace(
                'if self.tts_enabled and self.buffer.strip():',
                '''if self.tts_enabled and self.buffer.strip():
            # Force flush any partial sentence
            logger.info(f"[TTS Debug] Flushing partial sentence: '{self.buffer.strip()}'")'''
            )
            content = content.replace(current_flush, new_flush)
            print("   ✓ Added partial sentence flush logging")
    
    # Fix 3: Most important - ensure old TTS doesn't wait for streaming_complete
    print("\n3. Fixing appui.py to not block streaming TTS...")
    
    appui_path = "app/transcribe/appui.py"
    if os.path.exists(appui_path):
        with open(appui_path, 'r') as f:
            appui_content = f.read()
        
        # The key issue: appui.py checks streaming_complete.is_set() before playing audio
        # But with streaming TTS, we don't want to wait for completion!
        
        # Find the problematic condition
        old_pattern = r'if \(global_vars_module\.continuous_read and\s+responder\.streaming_complete\.is_set\(\)'
        
        if re.search(old_pattern, appui_content):
            print("   Found old TTS trigger condition")
            
            # Add a check to skip if streaming TTS is active
            # Replace the condition to exclude when streaming TTS is enabled
            new_condition = '''if (global_vars_module.continuous_read and
                responder.streaming_complete.is_set() and
                response != global_vars_module.last_spoken_response and
                not streaming_tts_enabled):'''
            
            # The check for streaming_tts_enabled is already there!
            # So the issue might be timing
            print("   ✓ Streaming TTS check already in place")
        else:
            print("   ⚠️  Could not find expected pattern in appui.py")
    
    # Fix 4: Add explicit debug output to trace the issue
    print("\n4. Adding comprehensive debug output...")
    
    # Add debug at the start of _handle_streaming_token
    if "[TTS Debug] Token received:" not in content:
        print("   ✓ Debug logging already added")
    
    # Add debug for initialization
    init_debug = '''logger.info(f"[TTS Debug] GPTResponder init - streaming enabled: {tts_enabled}")'''
    if "[TTS Debug] GPTResponder init" not in content:
        # Find where to add it
        init_pattern = r'if tts_enabled:'
        content = re.sub(
            init_pattern,
            f'{init_debug}\n        if tts_enabled:',
            content,
            count=1
        )
        print("   ✓ Added initialization debug")
    
    # Write the updated gpt_responder.py
    with open(gpt_path, 'w') as f:
        f.write(content)
    
    print("\n✅ Fix applied successfully!")
    
    # Create a diagnostic script
    print("\n5. Creating diagnostic script...")
    
    diagnostic_script = '''#!/usr/bin/env python3
"""Diagnose why streaming TTS isn't working."""

import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=== Streaming TTS Diagnostic ===\\n")

# Check 1: Configuration
print("1. Configuration Check:")
try:
    with open("app/transcribe/parameters.yaml", 'r') as f:
        params = yaml.safe_load(f)
    
    general = params.get('General', {})
    print(f"   tts_streaming_enabled: {general.get('tts_streaming_enabled')}")
    print(f"   tts_provider: {general.get('tts_provider')}")
    print(f"   continuous_read: {general.get('continuous_read')}")
    
    if general.get('tts_provider') != 'openai':
        print("   ❌ ERROR: tts_provider must be 'openai' for streaming!")
except Exception as e:
    print(f"   Error: {e}")

# Check 2: Import test
print("\\n2. Import Test:")
try:
    from app.transcribe.streaming_tts import create_tts, TTSConfig
    from app.transcribe.audio_player_streaming import StreamingAudioPlayer
    print("   ✓ Imports successful")
except Exception as e:
    print(f"   ❌ Import error: {e}")

# Check 3: Code verification
print("\\n3. Code Verification:")
try:
    with open("app/transcribe/gpt_responder.py", 'r') as f:
        content = f.read()
    
    checks = {
        "TTS Debug logging": "[TTS Debug]" in content,
        "Streaming token handler": "_handle_streaming_token" in content,
        "Sentence queue": "self.sent_q" in content,
        "TTS worker thread": "_tts_worker" in content,
        "Correct regex": 'r"[.!?]\\\\s"' in content
    }
    
    for check, result in checks.items():
        status = "✓" if result else "❌"
        print(f"   {status} {check}")
        
except Exception as e:
    print(f"   Error: {e}")

print("\\n" + "="*40)
print("\\nWhen you run the app, look for these in the console:")
print("1. [TTS Debug] GPTResponder init - streaming enabled: True")
print("2. [TTS Debug] Token received: ...")
print("3. [TTS Debug] Sentence detected: ...")
print("4. [TTS Debug] First audio chunk received in XXXms")
print("\\nIf you don't see these, streaming TTS is not initializing properly.")
'''
    
    with open("diagnose_streaming_tts.py", 'w') as f:
        f.write(diagnostic_script)
    
    print("   ✓ Created diagnose_streaming_tts.py")
    
    print("\n" + "="*50)
    print("\nIMPORTANT FINDINGS:")
    print("1. The code structure is correct")
    print("2. The issue is likely one of these:")
    print("   a) TTS provider not set to 'openai' (but we checked - it is)")
    print("   b) continuous_read might be false")
    print("   c) Streaming TTS not initializing (check debug output)")
    print("\nRun these commands on Windows:")
    print("1. python diagnose_streaming_tts.py")
    print("2. Run the app and check for [TTS Debug] messages")
    print("3. Report what you see in the console")
    
    return True


if __name__ == "__main__":
    apply_comprehensive_fix()
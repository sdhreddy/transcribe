#!/usr/bin/env python3
"""Find why streaming TTS isn't working."""

import yaml
import os
import sys

def analyze_issue():
    """Analyze the streaming TTS issue."""
    print("=== Finding Streaming TTS Issue ===\n")
    
    # 1. Check parameters.yaml directly
    print("1. Checking parameters.yaml...")
    with open('app/transcribe/parameters.yaml', 'r') as f:
        params = yaml.safe_load(f)
    
    general = params.get('General', {})
    print(f"   tts_streaming_enabled: {general.get('tts_streaming_enabled')}")
    print(f"   tts_provider: {general.get('tts_provider')}")
    print(f"   continuous_read: {general.get('continuous_read')}")
    
    # 2. Check the initialization flow
    print("\n2. Checking initialization order...")
    
    # Read gpt_responder.py to check the init
    with open('app/transcribe/gpt_responder.py', 'r') as f:
        content = f.read()
    
    # Check if the debug messages are there
    if "[INIT DEBUG]" in content:
        print("   ✓ Debug messages are in place")
    
    # Check if streaming TTS init is in GPTResponder.__init__
    if "if tts_enabled:" in content:
        print("   ✓ Streaming TTS initialization found in GPTResponder")
    
    # 3. The key issue - check if config is passed properly
    print("\n3. Analyzing OpenAIResponder initialization...")
    
    # Find OpenAIResponder class
    import re
    openai_class = re.search(r'class OpenAIResponder.*?def __init__.*?super\(\).__init__\((.*?)\)', 
                            content, re.DOTALL)
    
    if openai_class:
        super_call = openai_class.group(1)
        print(f"   super().__init__ called with: {super_call.strip()[:100]}...")
        
        if "config=" in super_call:
            print("   ✓ Config is passed to parent class")
        else:
            print("   ✗ Config might not be passed correctly!")
    
    # 4. Check for the real issue
    print("\n4. Checking old TTS system...")
    
    # The real culprit might be in appui.py
    with open('app/transcribe/appui.py', 'r') as f:
        appui_content = f.read()
    
    # Check if old TTS is still active
    if "audio_player_var.speech_text_available.set()" in appui_content:
        print("   ⚠️  Old TTS system found in appui.py")
        
        # Check if it's properly disabled when streaming is on
        if "not streaming_tts_enabled" in appui_content:
            print("   ✓ Old TTS checks for streaming_tts_enabled")
        else:
            print("   ✗ Old TTS might interfere with streaming!")
    
    # 5. The sentence detection issue
    print("\n5. Checking sentence detection...")
    
    if "_handle_streaming_token" in content:
        print("   ✓ Token handler exists")
        
        # Check if it's called during streaming
        if "_handle_streaming_token(message_text)" in content:
            print("   ✓ Token handler is called during streaming")
            
            # Count how many times it's called
            count = content.count("_handle_streaming_token(message_text)")
            print(f"   Found {count} calls to token handler")
    
    print("\n" + "="*50)
    print("\nCONCLUSION:")
    
    # Final diagnosis
    if general.get('tts_streaming_enabled') and general.get('tts_provider') == 'openai':
        print("✓ Configuration is correct")
        print("\nThe issue is likely:")
        print("1. Old TTS system waiting for complete response")
        print("2. Check console for [INIT DEBUG] messages")
        print("3. If no debug messages, GPTResponder not initializing")
        print("\nSOLUTION:")
        print("The old TTS in audio_player.py might be playing AFTER")
        print("the response completes, overriding streaming TTS.")
    else:
        print("✗ Configuration issue - fix parameters.yaml")


if __name__ == "__main__":
    analyze_issue()
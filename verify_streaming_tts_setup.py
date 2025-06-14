#!/usr/bin/env python3
"""Verify streaming TTS setup and provide focused diagnostics."""

import os
import sys
import time
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_critical_settings():
    """Check all critical settings for streaming TTS."""
    print("=== Verifying Streaming TTS Setup ===\n")
    
    issues = []
    
    # 1. Check parameters.yaml
    print("1. Checking parameters.yaml...")
    try:
        with open("app/transcribe/parameters.yaml", 'r') as f:
            params = yaml.safe_load(f)
        
        general = params.get('General', {})
        
        # Critical settings
        settings = {
            'tts_streaming_enabled': general.get('tts_streaming_enabled'),
            'tts_provider': general.get('tts_provider'),
            'continuous_read': general.get('continuous_read'),
            'tts_min_sentence_chars': general.get('tts_min_sentence_chars', 10)
        }
        
        print("   Current settings:")
        for key, value in settings.items():
            print(f"   - {key}: {value}")
            
        # Check for issues
        if settings['tts_streaming_enabled'] != True:
            issues.append("tts_streaming_enabled must be true")
        if settings['tts_provider'] != 'openai':
            issues.append("tts_provider must be 'openai' for streaming")
        if settings['continuous_read'] == False:
            issues.append("continuous_read should be true")
            
    except Exception as e:
        issues.append(f"Error reading parameters.yaml: {e}")
    
    # 2. Check API key
    print("\n2. Checking OpenAI API key...")
    api_key = None
    
    # Check environment
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        print("   ✓ Found in environment")
    else:
        # Check override.yaml
        try:
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
                if api_key:
                    print("   ✓ Found in override.yaml")
        except:
            pass
    
    if not api_key:
        issues.append("No OpenAI API key found")
    
    # 3. Check code changes
    print("\n3. Checking code changes...")
    
    # Check gpt_responder.py
    try:
        with open("app/transcribe/gpt_responder.py", 'r') as f:
            gpt_content = f.read()
        
        required_patterns = [
            ('Sentence detection regex', r'SENT_END = re\.compile\(r"\[\.!\?\]\\s"\)'),
            ('Handle streaming token', '_handle_streaming_token'),
            ('TTS worker', '_tts_worker'),
            ('Sentence queue', 'self.sent_q'),
            ('TTS Debug logging', '[TTS Debug]')
        ]
        
        for name, pattern in required_patterns:
            if pattern in gpt_content:
                print(f"   ✓ {name}")
            else:
                print(f"   ✗ {name}")
                issues.append(f"Missing: {name}")
                
    except Exception as e:
        issues.append(f"Error checking gpt_responder.py: {e}")
    
    # 4. Summary
    print("\n" + "="*50)
    if issues:
        print(f"❌ Found {len(issues)} issue(s):\n")
        for i, issue in enumerate(issues, 1):
            print(f"{i}. {issue}")
        print("\nStreaming TTS will NOT work properly!")
    else:
        print("✅ All settings verified! Streaming TTS should work.\n")
        print("If it's still not working, the issue might be:")
        print("1. Old TTS system interference")
        print("2. Network latency to OpenAI")
        print("3. Windows audio device issues")
    
    return len(issues) == 0


def test_quick_stream():
    """Quick test of streaming functionality."""
    print("\n\n=== Quick Streaming Test ===\n")
    
    try:
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        
        # Get API key
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                with open("app/transcribe/override.yaml", 'r') as f:
                    override = yaml.safe_load(f)
                    api_key = override.get('OpenAI', {}).get('api_key')
            except:
                pass
        
        if not api_key:
            print("Cannot test - no API key")
            return
        
        print("Testing OpenAI TTS latency...")
        config = TTSConfig(provider="openai", voice="alloy", api_key=api_key)
        tts = create_tts(config)
        
        start = time.time()
        chunks = iter(tts.stream("Quick test."))
        first = next(chunks)
        latency = time.time() - start
        
        print(f"First chunk received in: {latency*1000:.0f}ms")
        if latency < 0.5:
            print("✅ Excellent latency!")
        elif latency < 1.0:
            print("⚠️  Moderate latency")
        else:
            print("❌ High latency - check network connection")
            
    except Exception as e:
        print(f"Test failed: {e}")


def provide_manual_check():
    """Provide manual debugging steps."""
    print("\n\n=== Manual Debugging Steps ===\n")
    
    print("1. When you test the app, watch the console/logs for:")
    print("   - [TTS Debug] messages")
    print("   - 'Token received' messages")
    print("   - 'Sentence detected' messages")
    print("   - 'First audio chunk' timing")
    
    print("\n2. Expected flow:")
    print("   a. Colleague speaks")
    print("   b. GPT starts responding (tokens arrive)")
    print("   c. First sentence completes (. ! or ?)")
    print("   d. TTS starts immediately (<400ms)")
    print("   e. Audio plays while more text arrives")
    
    print("\n3. If you see sentences detected but no audio:")
    print("   - Check Windows audio devices")
    print("   - Try running: python debug_tts_windows.py")
    
    print("\n4. If you don't see sentence detection:")
    print("   - GPT might not be adding punctuation")
    print("   - Buffer might not reach 42 chars")


if __name__ == "__main__":
    if check_critical_settings():
        test_quick_stream()
    
    provide_manual_check()
    
    print("\n" + "="*50)
    print("Next steps:")
    print("1. Check the console output when running the app")
    print("2. Look for [TTS Debug] messages")
    print("3. Report what you see in the logs")
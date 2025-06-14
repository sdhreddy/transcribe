#!/usr/bin/env python3
"""Debug script to test streaming TTS functionality"""

import sys
import os
import yaml

# Add the app directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def test_streaming_tts():
    print("=== Streaming TTS Debug Test ===\n")
    
    # Check parameters.yaml
    print("1. Checking configuration...")
    with open('app/transcribe/parameters.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    streaming_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
    print(f"   - tts_streaming_enabled: {streaming_enabled}")
    print(f"   - tts_provider: {config.get('General', {}).get('tts_provider', 'N/A')}")
    print(f"   - tts_voice: {config.get('General', {}).get('tts_voice', 'N/A')}")
    
    # Check imports
    print("\n2. Checking required imports...")
    missing_deps = []
    
    try:
        import pyaudio
        print("   ✓ pyaudio imported successfully")
    except ImportError as e:
        print(f"   ✗ pyaudio import failed: {e}")
        missing_deps.append('pyaudio')
    
    try:
        import openai
        print("   ✓ openai imported successfully")
    except ImportError as e:
        print(f"   ✗ openai import failed: {e}")
        missing_deps.append('openai')
    
    try:
        import gtts
        print("   ✓ gtts imported successfully")
    except ImportError as e:
        print(f"   ✗ gtts import failed: {e}")
        missing_deps.append('gtts')
    
    if missing_deps:
        print(f"\n⚠️  Missing dependencies: {', '.join(missing_deps)}")
        print("\nTo install:")
        print("  pip install " + " ".join(missing_deps))
        return
    
    # Test streaming TTS initialization
    print("\n3. Testing streaming TTS initialization...")
    try:
        from transcribe.streaming_tts import create_tts, TTSConfig
        from transcribe.audio_player_streaming import StreamingAudioPlayer
        
        tts_config = TTSConfig(
            provider=config.get('General', {}).get('tts_provider', 'gtts'),
            voice=config.get('General', {}).get('tts_voice', 'alloy'),
            sample_rate=config.get('General', {}).get('tts_sample_rate', 24000),
            api_key=config.get('OpenAI', {}).get('api_key')
        )
        
        print(f"   - Creating TTS with provider: {tts_config.provider}")
        tts = create_tts(tts_config)
        print("   ✓ TTS created successfully")
        
        print("   - Creating StreamingAudioPlayer...")
        player = StreamingAudioPlayer(sample_rate=tts_config.sample_rate)
        print("   ✓ StreamingAudioPlayer created successfully")
        
    except Exception as e:
        print(f"   ✗ Error during initialization: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n4. Testing GPTResponder initialization...")
    try:
        # Mock conversation object
        class MockConversation:
            def update_conversation(self, **kwargs):
                pass
        
        from transcribe.gpt_responder import GPTResponder
        
        responder = GPTResponder(
            config={'General': config['General'], 'OpenAI': config.get('OpenAI', {})},
            convo=MockConversation(),
            file_name='test.txt',
            save_to_file=False
        )
        
        if responder.tts_enabled:
            print("   ✓ GPTResponder initialized with streaming TTS enabled")
        else:
            print("   ✗ GPTResponder initialized but streaming TTS is disabled")
            
    except Exception as e:
        print(f"   ✗ Error initializing GPTResponder: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== Debug test complete ===")

if __name__ == "__main__":
    test_streaming_tts()
#!/usr/bin/env python3
"""Debug script for TTS issues on Windows."""
import os
import sys
import time
import pyaudio

def list_audio_devices():
    """List all available audio devices."""
    print("=== Available Audio Devices ===")
    pa = pyaudio.PyAudio()
    device_count = pa.get_device_count()
    
    print(f"Total devices: {device_count}")
    print()
    
    for i in range(device_count):
        info = pa.get_device_info_by_index(i)
        print(f"Device {i}: {info['name']}")
        print(f"  - Channels: {info['maxOutputChannels']} output, {info['maxInputChannels']} input")
        print(f"  - Sample Rate: {info['defaultSampleRate']} Hz")
        print(f"  - Host API: {pa.get_host_api_info_by_index(info['hostApi'])['name']}")
        
        if info['maxOutputChannels'] > 0:
            print(f"  - OUTPUT CAPABLE")
        print()
    
    try:
        default = pa.get_default_output_device_info()
        print(f"Default output device: {default['index']} - {default['name']}")
    except Exception as e:
        print(f"ERROR: No default output device! {e}")
    
    pa.terminate()


def test_simple_tts():
    """Test basic TTS functionality."""
    print("\n=== Testing Simple TTS ===")
    
    # Check for API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Try to read from override.yaml
        override_path = "app/transcribe/override.yaml"
        if os.path.exists(override_path):
            import yaml
            with open(override_path, 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
    
    if not api_key:
        print("ERROR: No OpenAI API key found!")
        print("Set OPENAI_API_KEY environment variable or add to override.yaml")
        return
    
    print("API key found, testing TTS...")
    
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    try:
        from app.transcribe.streaming_tts import create_tts, TTSConfig
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
        
        # Test with OpenAI
        print("\nTesting OpenAI TTS...")
        config = TTSConfig(provider="openai", voice="alloy", api_key=api_key)
        tts = create_tts(config)
        player = StreamingAudioPlayer()
        player.start()
        
        test_text = "Hello, this is a test of streaming text to speech."
        print(f"Speaking: '{test_text}'")
        
        start = time.time()
        first_chunk_time = None
        
        for i, chunk in enumerate(tts.stream(test_text)):
            if i == 0:
                first_chunk_time = time.time() - start
                print(f"First chunk received in: {first_chunk_time:.3f}s")
            player.enqueue(chunk)
        
        print("Waiting for playback to complete...")
        time.sleep(3)
        player.stop()
        
        print("✓ OpenAI TTS test completed")
        
    except Exception as e:
        print(f"✗ TTS test failed: {e}")
        import traceback
        traceback.print_exc()


def test_sentence_streaming():
    """Test sentence-level streaming simulation."""
    print("\n=== Testing Sentence Streaming ===")
    
    import re
    
    buffer = ""
    SENT_END = re.compile(r"[.!?]\s")
    
    # Simulate token stream
    tokens = [
        "Hello", " there", ".", " ",
        "How", " are", " you", "?", " ",
        "This", " is", " a", " test", " of", " streaming", ".", " ",
        "It", " should", " work", " well", "!"
    ]
    
    sentences = []
    
    print("Token stream simulation:")
    for token in tokens:
        buffer += token
        print(f"Buffer: '{buffer}'", end="")
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            buffer = buffer[match.end():]
            sentences.append(sentence)
            print(f" -> Found sentence: '{sentence}'")
        else:
            print()
    
    print(f"\nFound {len(sentences)} sentences total")


if __name__ == "__main__":
    print("TTS Debugging Tool for Windows")
    print("=" * 50)
    
    list_audio_devices()
    test_simple_tts()
    test_sentence_streaming()
    
    print("\n" + "=" * 50)
    print("Debug complete!")
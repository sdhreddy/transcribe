#!/usr/bin/env python3
"""Isolated test of streaming TTS to diagnose the issue."""

import os
import sys
import time
import re
import queue
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_minimal_streaming():
    """Test the absolute minimum streaming setup."""
    print("=== Minimal Streaming Test ===\n")
    
    # Import after path setup
    from app.transcribe.streaming_tts import create_tts, TTSConfig
    from app.transcribe.audio_player_streaming import StreamingAudioPlayer
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import yaml
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
        except:
            pass
    
    if not api_key:
        print("ERROR: No OpenAI API key found!")
        return
    
    print("1. Creating TTS and audio player...")
    config = TTSConfig(provider="openai", voice="alloy", api_key=api_key)
    tts = create_tts(config)
    player = StreamingAudioPlayer()
    player.start()
    
    print("2. Testing direct TTS streaming...")
    test_text = "Hello. This is a test."
    
    start = time.time()
    chunk_count = 0
    first_chunk_time = None
    
    for chunk in tts.stream(test_text):
        if chunk_count == 0:
            first_chunk_time = time.time() - start
            print(f"   First chunk: {first_chunk_time*1000:.0f}ms")
        chunk_count += 1
        player.enqueue(chunk)
    
    print(f"   Total chunks: {chunk_count}")
    print(f"   Total time: {(time.time()-start)*1000:.0f}ms")
    
    print("\n3. Waiting for playback...")
    time.sleep(3)
    
    player.stop()
    print("✓ Direct streaming works!\n")


def test_sentence_queue_streaming():
    """Test with sentence queue like in the real app."""
    print("=== Sentence Queue Test ===\n")
    
    from app.transcribe.streaming_tts import create_tts, TTSConfig
    from app.transcribe.audio_player_streaming import StreamingAudioPlayer
    
    # Get API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        try:
            import yaml
            with open("app/transcribe/override.yaml", 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
        except:
            pass
    
    if not api_key:
        return
    
    # Setup like in gpt_responder.py
    sent_q = queue.Queue()
    tts = create_tts(TTSConfig(provider="openai", voice="alloy", api_key=api_key))
    player = StreamingAudioPlayer()
    player.start()
    
    def tts_worker():
        """Simulate the TTS worker."""
        print("TTS worker started")
        while True:
            try:
                sentence = sent_q.get(timeout=1.0)
                if sentence is None:
                    break
                print(f"TTS: Processing '{sentence}'")
                start = time.time()
                for chunk in tts.stream(sentence):
                    player.enqueue(chunk)
                print(f"TTS: Done in {(time.time()-start)*1000:.0f}ms")
            except queue.Empty:
                continue
    
    # Start worker
    worker = threading.Thread(target=tts_worker, daemon=True)
    worker.start()
    
    # Simulate sentence detection
    print("1. Simulating GPT token stream...")
    buffer = ""
    SENT_END = re.compile(r"[.!?]\s")
    
    tokens = [
        "Hello", " there", ".", " ",
        "This", " is", " a", " streaming", " test", ".", " ",
        "It", " should", " work", " immediately", "!"
    ]
    
    for i, token in enumerate(tokens):
        buffer += token
        print(f"   Token {i}: '{token}'")
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"   → Sentence: '{sentence}'")
            sent_q.put(sentence)
            buffer = buffer[match.end():]
        
        time.sleep(0.05)  # Simulate token delay
    
    print("\n2. Waiting for playback...")
    time.sleep(5)
    
    # Cleanup
    sent_q.put(None)
    worker.join(timeout=2)
    player.stop()
    
    print("✓ Queue-based streaming works!\n")


def diagnose_config():
    """Check configuration issues."""
    print("=== Configuration Diagnosis ===\n")
    
    try:
        import yaml
        with open("app/transcribe/parameters.yaml", 'r') as f:
            params = yaml.safe_load(f)
        
        general = params.get('General', {})
        
        # Check critical settings
        issues = []
        
        if not general.get('tts_streaming_enabled'):
            issues.append("tts_streaming_enabled is False or missing")
        
        if general.get('tts_provider') != 'openai':
            issues.append(f"tts_provider is '{general.get('tts_provider')}' (should be 'openai')")
        
        if general.get('continuous_read') is False:
            issues.append("continuous_read is False")
        
        print("Configuration:")
        print(f"  tts_streaming_enabled: {general.get('tts_streaming_enabled')}")
        print(f"  tts_provider: {general.get('tts_provider')}")
        print(f"  continuous_read: {general.get('continuous_read')}")
        print(f"  tts_min_sentence_chars: {general.get('tts_min_sentence_chars', 10)}")
        
        if issues:
            print(f"\n❌ Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("\n✓ Configuration looks good!")
            
    except Exception as e:
        print(f"Error reading config: {e}")


if __name__ == "__main__":
    print("Streaming TTS Isolated Test")
    print("=" * 50 + "\n")
    
    # Run tests
    diagnose_config()
    print()
    
    test_minimal_streaming()
    test_sentence_queue_streaming()
    
    print("\nConclusion:")
    print("If both tests work but the app doesn't stream:")
    print("1. The old TTS system might be interfering")
    print("2. streaming_complete event might be blocking")
    print("3. Sentence detection might not be triggered during streaming")
    print("\nRun fix_streaming_tts_final.py to apply the interference fix.")
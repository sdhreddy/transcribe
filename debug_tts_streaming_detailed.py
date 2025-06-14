#!/usr/bin/env python3
"""Detailed TTS streaming debug script."""
import os
import sys
import time
import re
import queue
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_sentence_detection():
    """Test if sentence detection logic is working correctly."""
    print("=== Testing Sentence Detection Logic ===")
    
    buffer = ""
    SENT_END = re.compile(r"[.!?]\s")
    sentences_found = []
    
    # Simulate streaming tokens
    test_tokens = [
        "Hello", " there", ".", " ",
        "How", " are", " you", "?", " ",
        "This", " is", " a", " streaming", " test", "."
    ]
    
    print("Streaming tokens:")
    for i, token in enumerate(test_tokens):
        buffer += token
        print(f"Token {i}: '{token}' | Buffer: '{buffer}'")
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"  -> SENTENCE FOUND: '{sentence}'")
            sentences_found.append(sentence)
            buffer = buffer[match.end():]
            print(f"  -> Remaining buffer: '{buffer}'")
    
    print(f"\nTotal sentences found: {len(sentences_found)}")
    for s in sentences_found:
        print(f"  - '{s}'")
    
    return len(sentences_found) == 3


def test_tts_provider():
    """Check which TTS provider is configured."""
    print("\n=== Checking TTS Provider Configuration ===")
    
    try:
        import yaml
        
        # Check parameters.yaml
        params_path = "app/transcribe/parameters.yaml"
        if os.path.exists(params_path):
            with open(params_path, 'r') as f:
                params = yaml.safe_load(f)
                
            general = params.get('General', {})
            print(f"tts_streaming_enabled: {general.get('tts_streaming_enabled')}")
            print(f"tts_provider: {general.get('tts_provider')}")
            print(f"tts_min_sentence_chars: {general.get('tts_min_sentence_chars')}")
            
            if general.get('tts_provider') != 'openai':
                print("⚠️  WARNING: TTS provider is not 'openai' - streaming won't work!")
                return False
        else:
            print("ERROR: parameters.yaml not found!")
            return False
            
    except Exception as e:
        print(f"Error reading config: {e}")
        return False
    
    return True


def test_streaming_flow():
    """Test the complete streaming flow."""
    print("\n=== Testing Complete Streaming Flow ===")
    
    from app.transcribe.streaming_tts import create_tts, TTSConfig
    from app.transcribe.audio_player_streaming import StreamingAudioPlayer
    
    # Check API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        override_path = "app/transcribe/override.yaml"
        if os.path.exists(override_path):
            import yaml
            with open(override_path, 'r') as f:
                override = yaml.safe_load(f)
                api_key = override.get('OpenAI', {}).get('api_key')
    
    if not api_key:
        print("ERROR: No OpenAI API key found!")
        return False
    
    print("API key found ✓")
    
    # Test streaming
    config = TTSConfig(provider="openai", voice="alloy", api_key=api_key)
    tts = create_tts(config)
    player = StreamingAudioPlayer()
    player.start()
    
    # Simulate sentence queue
    sent_q = queue.Queue()
    
    def tts_worker():
        """Simulate the TTS worker thread."""
        while True:
            try:
                sentence = sent_q.get(timeout=1.0)
                if sentence is None:
                    break
                    
                print(f"TTS Worker: Processing '{sentence}'")
                start = time.time()
                
                first_chunk = True
                for chunk in tts.stream(sentence):
                    if first_chunk:
                        latency = time.time() - start
                        print(f"  First chunk latency: {latency*1000:.0f}ms")
                        first_chunk = False
                    player.enqueue(chunk)
                    
            except queue.Empty:
                continue
    
    # Start worker
    worker = threading.Thread(target=tts_worker, daemon=True)
    worker.start()
    
    # Test sentences
    test_sentences = [
        "This is the first sentence.",
        "Here comes the second one.",
        "And finally, the third sentence!"
    ]
    
    print("\nSimulating sentence streaming:")
    for i, sent in enumerate(test_sentences):
        print(f"Enqueueing sentence {i+1}: '{sent}'")
        sent_q.put(sent)
        time.sleep(0.5)  # Simulate time between sentences
    
    # Wait for playback
    print("\nWaiting for playback to complete...")
    time.sleep(5)
    
    # Cleanup
    sent_q.put(None)
    player.stop()
    worker.join(timeout=2)
    
    return True


def check_gpt_responder_integration():
    """Check if gpt_responder.py is properly integrated."""
    print("\n=== Checking GPT Responder Integration ===")
    
    gpt_path = "app/transcribe/gpt_responder.py"
    if not os.path.exists(gpt_path):
        print("ERROR: gpt_responder.py not found!")
        return
    
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Check key components
    checks = {
        "SENT_END regex": r'SENT_END = re\.compile\(r"\[\.!\?\]\\s"\)',
        "_handle_streaming_token method": r'def _handle_streaming_token\(self, token: str\):',
        "sent_q initialization": r'self\.sent_q: queue\.Queue\[str\] = queue\.Queue\(\)',
        "_tts_worker method": r'def _tts_worker\(self\):',
        "tts_enabled check": r'if not self\.tts_enabled:',
        "sentence boundary check": r'match = self\.SENT_END\.search\(self\.buffer\)'
    }
    
    for name, pattern in checks.items():
        if re.search(pattern, content):
            print(f"✓ {name}")
        else:
            print(f"✗ {name} - NOT FOUND!")
    
    # Check if _handle_streaming_token is called
    if "_handle_streaming_token(message_text)" in content:
        print("✓ _handle_streaming_token is being called")
    else:
        print("✗ _handle_streaming_token is NOT being called!")


def test_with_mock_gpt_stream():
    """Test with a mock GPT stream to isolate the issue."""
    print("\n=== Testing with Mock GPT Stream ===")
    
    import queue
    import re
    
    buffer = ""
    sent_q = queue.Queue()
    SENT_END = re.compile(r"[.!?]\s")
    
    # Mock GPT tokens (simulating real response)
    mock_tokens = [
        "Based", " on", " the", " error", " message", ",", " you", " need", " to", 
        " install", " PyAudio", ".", " ", "Try", " running", " this", " command", ":", " ",
        "pip", " install", " pyaudio", ".", " ", "If", " that", " doesn't", " work", ",", 
        " you", " might", " need", " platform", "-specific", " installation", "."
    ]
    
    print("Simulating GPT token stream:")
    sentences_found = []
    
    for token in mock_tokens:
        buffer += token
        
        # Check for sentence
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            if len(sentence) >= 10:  # Min length check
                print(f"  -> Sentence ready for TTS: '{sentence}'")
                sentences_found.append(sentence)
                sent_q.put(sentence)
            buffer = buffer[match.end():]
    
    print(f"\nSentences that would be sent to TTS: {len(sentences_found)}")
    
    # Check remaining buffer
    if buffer.strip():
        print(f"Remaining buffer: '{buffer.strip()}'")


if __name__ == "__main__":
    print("Detailed TTS Streaming Debug")
    print("=" * 50)
    
    # Run all tests
    results = []
    
    results.append(("Sentence Detection", test_sentence_detection()))
    results.append(("TTS Provider Config", test_tts_provider()))
    
    check_gpt_responder_integration()
    test_with_mock_gpt_stream()
    
    # Only test full flow if config is correct
    if results[1][1]:  # If TTS provider is correct
        results.append(("Streaming Flow", test_streaming_flow()))
    
    print("\n" + "=" * 50)
    print("Test Results:")
    for test_name, passed in results:
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"{test_name}: {status}")
    
    print("\nPossible Issues:")
    print("1. If sentence detection passed but TTS still waits:")
    print("   - Check if _handle_streaming_token is being called during streaming")
    print("   - Verify tts_streaming_enabled is true")
    print("   - Ensure OpenAI API key is valid")
    print("\n2. If provider is not 'openai':")
    print("   - Edit parameters.yaml and set tts_provider: openai")
    print("\n3. If integration check shows missing methods:")
    print("   - The file may not have been updated properly on Windows")
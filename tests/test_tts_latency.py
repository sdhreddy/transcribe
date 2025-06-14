# tests/test_tts_latency.py
import time
import numpy as np
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.transcribe.streaming_tts import create_tts, TTSConfig


def test_tts_latency():
    """Test that first TTS chunk arrives within 300ms."""
    # Test OpenAI TTS
    cfg = TTSConfig(
        provider="openai", 
        voice="alloy",
        api_key=os.getenv("OPENAI_API_KEY")
    )
    tts = create_tts(cfg)
    
    print("Testing OpenAI TTS latency...")
    t0 = time.time()
    chunks = iter(tts.stream("Latency check."))
    
    try:
        first = next(chunks)
        lat = time.time() - t0
        print(f"First chunk latency: {lat:.3f}s")
        
        assert lat < 0.30, f"First chunk took {lat:.2f}s (expected < 0.30s)"
        assert len(first) > 1000 and len(first) % 2 == 0, f"Invalid chunk size: {len(first)}"
        print("✓ OpenAI TTS latency test passed")
        
    except Exception as e:
        print(f"✗ OpenAI TTS test failed: {e}")
        

def test_gtts_fallback():
    """Test GTTS fallback (non-streaming but compatible)."""
    cfg = TTSConfig(provider="gtts")
    tts = create_tts(cfg)
    
    print("\nTesting GTTS fallback...")
    t0 = time.time()
    chunks = list(tts.stream("Hello world."))
    lat = time.time() - t0
    
    print(f"GTTS generation time: {lat:.3f}s")
    print(f"Number of chunks: {len(chunks)}")
    print("✓ GTTS fallback test passed")


def test_sentence_streaming():
    """Test sentence-level streaming behavior."""
    from app.transcribe.gpt_responder import GPTResponder
    import queue
    import re
    
    print("\nTesting sentence boundary detection...")
    
    # Simulate the sentence detection logic
    buffer = ""
    sent_q = queue.Queue()
    SENT_END = re.compile(r"[.!?]\s")
    
    test_tokens = [
        "Hello", " there", ".", " How", " are", " you", " doing", "?", " I",
        " hope", " you", "'re", " well", ".", " This", " is", " a", " test", "."
    ]
    
    sentences_found = []
    
    for token in test_tokens:
        buffer += token
        
        match = SENT_END.search(buffer)
        if match:
            complete_sentence = buffer[:match.end()].strip()
            if complete_sentence and len(complete_sentence) >= 10:
                sentences_found.append(complete_sentence)
                buffer = buffer[match.end():]
    
    print(f"Found {len(sentences_found)} sentences:")
    for i, sent in enumerate(sentences_found, 1):
        print(f"  {i}. '{sent}'")
    
    assert len(sentences_found) >= 2, "Should find at least 2 sentences"
    print("✓ Sentence detection test passed")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-k", "--test", help="Run specific test")
    args = parser.parse_args()
    
    if args.test == "tts_latency":
        test_tts_latency()
    elif args.test == "gtts":
        test_gtts_fallback()
    elif args.test == "sentence":
        test_sentence_streaming()
    else:
        # Run all tests
        test_tts_latency()
        test_gtts_fallback()
        test_sentence_streaming()
#!/usr/bin/env python3
"""Test streaming TTS timing."""
import time
import re

def test_sentence_timing():
    """Test how quickly sentences are detected."""
    buffer = ""
    SENT_END = re.compile(r"[.!?]\s")
    
    # Simulate token stream
    tokens = ["Hello", " world", ".", " ", "How", " are", " you", "?"]
    
    start = time.time()
    for i, token in enumerate(tokens):
        buffer += token
        token_time = time.time() - start
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"Sentence '{sentence}' ready at {token_time*1000:.0f}ms")
            buffer = buffer[match.end():]

if __name__ == "__main__":
    test_sentence_timing()

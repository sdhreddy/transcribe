#!/usr/bin/env python3
"""Test what's happening with sentence detection."""

import re
import queue

# Simulate the current regex
SENT_END = re.compile(r"[.!?](?:\s|$)")

def simulate_streaming(text):
    """Simulate how text is processed."""
    print(f"Simulating: '{text}'\n")
    
    buffer = ""
    sentences = []
    
    # Simulate word by word (like GPT tokens)
    words = text.split()
    for i, word in enumerate(words):
        if buffer and not buffer.endswith(' '):
            buffer += ' '
        buffer += word
        print(f"Token {i+1}: '{word}' -> Buffer: '{buffer}'")
        
        # Check for sentence
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"  → SENTENCE: '{sentence}'")
            sentences.append(sentence)
            buffer = buffer[match.end():].strip()
            print(f"  → Remaining: '{buffer}'")
    
    if buffer:
        print(f"\nFinal buffer (not sent): '{buffer}'")
    
    print(f"\nTotal sentences found: {len(sentences)}")
    for s in sentences:
        print(f"  - '{s}'")
    
    return sentences

# Test with typical GPT response
test_text = "Based on the error message, you need to install PyAudio. Try running pip install pyaudio on Windows."
sentences = simulate_streaming(test_text)

print("\n" + "="*50)
print("ISSUE: If only first sentence is spoken, the rest is stuck in buffer!")

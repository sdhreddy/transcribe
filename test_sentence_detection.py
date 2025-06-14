#!/usr/bin/env python3
"""Test sentence detection with real examples."""
import re

# Test the sentence detection
SENT_END = re.compile(r"[.!?](?:\s|$)|(?:\.com|\.org|\.net)(?:\s|$)")

test_cases = [
    "Hello world. How are you?",
    "Visit example.com for more info.",
    "This is great! What do you think?",
    "No punctuation yet but getting long",
    "Short",
    "This has a comma, which might help.",
]

print("Testing sentence detection:\n")

for test in test_cases:
    buffer = ""
    print(f"Input: '{test}'")
    
    # Simulate token by token
    tokens = test.split(' ')
    for i, token in enumerate(tokens):
        if i > 0:
            buffer += ' '
        buffer += token
        
        match = SENT_END.search(buffer)
        if match:
            sentence = buffer[:match.end()].strip()
            print(f"  → Sentence detected: '{sentence}'")
            buffer = buffer[match.end():].strip()
    
    if buffer:
        print(f"  → Remaining: '{buffer}'")
    print()

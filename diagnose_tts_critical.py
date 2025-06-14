#!/usr/bin/env python3
"""Critical diagnostic for TTS issues."""

import os
import re

def diagnose_critical_issues():
    """Diagnose why TTS is failing so badly."""
    
    print("=== CRITICAL TTS DIAGNOSTIC ===\n")
    
    # 1. Check what's actually happening in the code
    print("1. Analyzing current code state...")
    
    gpt_path = "app/transcribe/gpt_responder.py"
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Check sentence detection
    regex_match = re.search(r'self\.SENT_END = re\.compile\((.*?)\)', content)
    if regex_match:
        print(f"   Current regex: {regex_match.group(1)}")
    
    # Check if we're accumulating responses
    if "collected_messages += message_text" in content:
        print("   ✓ Accumulating messages")
    
    # Count handle_streaming_token calls
    calls = content.count("_handle_streaming_token(message_text)")
    print(f"   Found {calls} calls to _handle_streaming_token")
    
    # 2. The 4-word issue suggests the sentence is being cut off
    print("\n2. Analyzing why only 4 words are spoken...")
    
    # Check buffer handling
    if "self.buffer = self.buffer[match.end()]" in content:
        print("   ⚠️  Buffer might be cleared incorrectly")
    
    # 3. Create a test to see what's happening
    print("\n3. Creating real-world test...")
    
    test_script = '''#!/usr/bin/env python3
"""Test what's happening with sentence detection."""

import re
import queue

# Simulate the current regex
SENT_END = re.compile(r"[.!?](?:\\s|$)")

def simulate_streaming(text):
    """Simulate how text is processed."""
    print(f"Simulating: '{text}'\\n")
    
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
        print(f"\\nFinal buffer (not sent): '{buffer}'")
    
    print(f"\\nTotal sentences found: {len(sentences)}")
    for s in sentences:
        print(f"  - '{s}'")
    
    return sentences

# Test with typical GPT response
test_text = "Based on the error message, you need to install PyAudio. Try running pip install pyaudio on Windows."
sentences = simulate_streaming(test_text)

print("\\n" + "="*50)
print("ISSUE: If only first sentence is spoken, the rest is stuck in buffer!")
'''
    
    with open("test_real_streaming.py", 'w') as f:
        f.write(test_script)
    
    print("   Created test_real_streaming.py")
    
    # 4. Create emergency fix
    print("\n4. Creating emergency fix...")
    
    fix_script = '''#!/usr/bin/env python3
"""Emergency fix for TTS issues."""

import os

print("Applying emergency TTS fix...\\n")

gpt_path = "app/transcribe/gpt_responder.py"
with open(gpt_path, 'r') as f:
    content = f.read()

# Fix 1: Make sure we're not cutting off the buffer wrong
print("1. Fixing buffer handling...")
if "self.buffer = self.buffer[match.end()]" in content:
    # The issue might be stripping too much
    content = content.replace(
        "self.buffer = self.buffer[match.end()]",
        "self.buffer = self.buffer[match.end():].lstrip()"  # Only strip left spaces
    )
    print("   ✓ Fixed buffer trimming")

# Fix 2: Force flush more aggressively
print("\\n2. Making flush more aggressive...")
flush_method = """    def flush_tts_buffer(self):
        \\"\\"\\"Flush any remaining text in buffer when streaming completes.\\"\\"\\"
        if self.tts_enabled and self.buffer.strip():
            logger.info(f"[TTS Debug] Flushing remaining buffer: '{self.buffer.strip()}'")
            self.sent_q.put(self.buffer.strip())
            self.buffer = \\"\\"
"""

# Replace the flush method
import re
flush_pattern = r'def flush_tts_buffer\\(self\\):.*?self\\.buffer = \\"\\"'
if re.search(flush_pattern, content, re.DOTALL):
    content = re.sub(flush_pattern, flush_method.strip(), content, flags=re.DOTALL)
    print("   ✓ Updated flush method")

# Fix 3: Add periodic buffer checks
print("\\n3. Adding periodic buffer flush...")
if "# Periodic flush check" not in content:
    # Add after the force break at 42 chars
    periodic_check = """        # Periodic flush check - don't let buffer grow too large
        elif len(self.buffer) > 30 and ' ' in self.buffer:
            # Find last space and break there
            last_space = self.buffer.rfind(' ')
            if last_space > 15:
                partial = self.buffer[:last_space].strip()
                if partial:
                    logger.info(f"[TTS Debug] Periodic flush at space: '{partial}'")
                    self.sent_q.put(partial)
                    self.buffer = self.buffer[last_space:].lstrip()
        """
    
    # Insert before the 42 char check
    content = content.replace(
        "elif len(self.buffer) > 42:",
        periodic_check + "elif len(self.buffer) > 42:"
    )
    print("   ✓ Added periodic flush")

# Write the fixed file
with open(gpt_path, 'w') as f:
    f.write(content)

print("\\n✅ Emergency fixes applied!")
print("\\nWhat was fixed:")
print("1. Buffer handling - prevent cutting off words")
print("2. More aggressive flushing of remaining text")
print("3. Periodic flush at word boundaries")
'''
    
    with open("emergency_tts_fix.py", 'w') as f:
        f.write(fix_script)
    
    print("   Created emergency_tts_fix.py")
    
    print("\n" + "="*50)
    print("\nDIAGNOSIS:")
    print("1. Only 4 words spoken = sentence detection is too aggressive")
    print("2. Audio after visual = not detecting sentences during stream")
    print("3. Audio stops = buffer not being flushed properly")
    print("\nRun these:")
    print("1. python test_real_streaming.py - See the issue")
    print("2. python emergency_tts_fix.py - Apply fixes")


if __name__ == "__main__":
    diagnose_critical_issues()
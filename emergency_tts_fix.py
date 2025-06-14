#!/usr/bin/env python3
"""Emergency fix for TTS issues."""

import os

print("Applying emergency TTS fix...\n")

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
print("\n2. Making flush more aggressive...")
flush_method = """    def flush_tts_buffer(self):
        \"\"\"Flush any remaining text in buffer when streaming completes.\"\"\"
        if self.tts_enabled and self.buffer.strip():
            logger.info(f"[TTS Debug] Flushing remaining buffer: '{self.buffer.strip()}'")
            self.sent_q.put(self.buffer.strip())
            self.buffer = \"\"
"""

# Replace the flush method
import re
flush_pattern = r'def flush_tts_buffer\(self\):.*?self\.buffer = \"\"'
if re.search(flush_pattern, content, re.DOTALL):
    content = re.sub(flush_pattern, flush_method.strip(), content, flags=re.DOTALL)
    print("   ✓ Updated flush method")

# Fix 3: Add periodic buffer checks
print("\n3. Adding periodic buffer flush...")
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

print("\n✅ Emergency fixes applied!")
print("\nWhat was fixed:")
print("1. Buffer handling - prevent cutting off words")
print("2. More aggressive flushing of remaining text")
print("3. Periodic flush at word boundaries")

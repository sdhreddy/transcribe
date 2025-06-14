#!/usr/bin/env python3
"""Fix audio stopping issue."""

import os

# Fix 1: Increase queue size
audio_path = "app/transcribe/audio_player_streaming.py"
if os.path.exists(audio_path):
    with open(audio_path, 'r') as f:
        content = f.read()
    
    # Increase queue size
    content = content.replace(
        "queue.Queue(maxsize=5)",
        "queue.Queue(maxsize=20)"
    )
    
    with open(audio_path, 'w') as f:
        f.write(content)
    print("✓ Increased audio queue size")

# Fix 2: Add worker keep-alive
gpt_path = "app/transcribe/gpt_responder.py"
if os.path.exists(gpt_path):
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Make sure worker doesn't die on empty queue
    if "timeout=1.0" in content and "# Keep worker alive" not in content:
        content = content.replace(
            "sentence = self.sent_q.get(timeout=1.0)",
            "sentence = self.sent_q.get(timeout=0.5)  # Keep worker alive"
        )
        
        with open(gpt_path, 'w') as f:
            f.write(content)
        print("✓ Reduced worker timeout for keep-alive")

print("\nFixes applied!")

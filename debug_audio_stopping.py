#!/usr/bin/env python3
"""Debug why audio stops after 2 responses."""

def analyze_audio_stopping():
    """Analyze why audio stops working."""
    
    print("=== Analyzing Audio Stopping Issue ===\n")
    
    print("Possible causes:")
    print("1. TTS worker thread dying")
    print("2. Audio queue getting full") 
    print("3. OpenAI API rate limiting")
    print("4. Audio player thread dying")
    print("5. Memory/resource leak")
    
    print("\nTo diagnose, look for these in console when audio stops:")
    print("- '[TTS Debug] TTS worker error'")
    print("- '[TTS Debug] Audio queue full'")
    print("- No more '[TTS Debug] Token received' messages")
    print("- No more '[TTS Debug] Sentence detected' messages")
    
    print("\nQuick fixes to try:")
    print("1. Increase audio queue size:")
    print("   In audio_player_streaming.py, change:")
    print("   self.q: queue.Queue[bytes] = queue.Queue(maxsize=5)")
    print("   to:")
    print("   self.q: queue.Queue[bytes] = queue.Queue(maxsize=20)")
    
    print("\n2. Add keep-alive to TTS worker:")
    print("   The worker might be timing out on queue.get()")
    
    print("\n3. Check if it's specific to certain text:")
    print("   Some characters might cause TTS API errors")
    
    # Create a fix script
    fix_script = '''#!/usr/bin/env python3
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

print("\\nFixes applied!")
'''
    
    with open("fix_audio_stopping.py", 'w') as f:
        f.write(fix_script)
    
    print("\nCreated fix_audio_stopping.py - run it to apply fixes")


if __name__ == "__main__":
    analyze_audio_stopping()
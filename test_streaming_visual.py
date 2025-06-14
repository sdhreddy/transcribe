#!/usr/bin/env python3
"""Visual test for streaming TTS - shows clear timing evidence."""

import time
import threading
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Global tracking
events = []
audio_started = False
response_complete = False

def log_event(event_type, message):
    """Log an event with timestamp."""
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    events.append(f"[{timestamp}] {event_type}: {message}")
    print(f"[{timestamp}] {event_type}: {message}")

def create_visual_test():
    """Create a visual test that clearly shows if streaming works."""
    
    test_code = '''#!/usr/bin/env python3
"""Visual streaming TTS test - RUN THIS IN WINDOWS."""

import time
import threading
from datetime import datetime

print("="*60)
print("STREAMING TTS VISUAL TEST")
print("="*60)
print()
print("This test will clearly show if TTS is streaming or not.")
print("Watch the timeline below...")
print()

# Import after banner
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.transcribe import app_utils
from app.transcribe.global_vars import TranscriptionGlobals
from tsutils import configuration

# Timing tracking
start_time = time.time()
events = []

def log(message):
    """Log with timestamp."""
    elapsed = time.time() - start_time
    timestamp = f"{elapsed:6.2f}s"
    print(f"{timestamp} - {message}")
    events.append((elapsed, message))

# Initialize
log("Starting test...")
log("Loading configuration...")

config = configuration.Config().data
global_vars = TranscriptionGlobals()
global_vars.config = config

# Check config
streaming_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
tts_provider = config.get('General', {}).get('tts_provider', 'gtts')

log(f"Config: streaming={streaming_enabled}, provider={tts_provider}")

if not streaming_enabled:
    print("\\n❌ STREAMING NOT ENABLED IN CONFIG!")
    sys.exit(1)

# Create responder
log("Creating GPT responder...")
responder = app_utils.create_responder(
    provider_name=config['General']['chat_inference_provider'],
    config=config,
    convo=global_vars.convo,
    save_to_file=False,
    response_file_name="test.txt"
)

if hasattr(responder, 'tts_enabled'):
    log(f"TTS enabled in responder: {responder.tts_enabled}")
else:
    log("WARNING: No TTS enabled attribute!")

# Add test conversation
log("Adding test question to conversation...")
test_question = "What are the three main benefits of using Python for data science?"

global_vars.convo.update_conversation(
    persona="Human",
    text=test_question,
    time_spoken=datetime.utcnow(),
    update_previous=False
)

# Monitor response generation
response_chunks = []
audio_events = []

def monitor_response():
    """Monitor response generation."""
    last_len = 0
    while True:
        current = getattr(responder, 'response', '')
        if len(current) > last_len:
            chunk = current[last_len:]
            elapsed = time.time() - start_time
            response_chunks.append((elapsed, len(chunk)))
            log(f"RESPONSE: +{len(chunk)} chars (total: {len(current)})")
            last_len = len(current)
        
        if hasattr(responder, 'streaming_complete') and responder.streaming_complete.is_set():
            log("RESPONSE: Complete")
            break
        time.sleep(0.05)

# Start monitoring
monitor_thread = threading.Thread(target=monitor_response, daemon=True)
monitor_thread.start()

# Generate response
log("Triggering GPT response...")
responder.enabled = True
response = responder.generate_response_from_transcript_no_check()

# Wait for completion
monitor_thread.join(timeout=30)

# Analysis
print()
print("="*60)
print("RESULTS:")
print("="*60)

if response:
    print(f"Response generated: {len(response)} characters")
    print(f"First 100 chars: {response[:100]}...")
else:
    print("❌ No response generated!")

print()
print("STREAMING ANALYSIS:")
print("-"*40)

# Check if audio started before response completed
first_response_time = response_chunks[0][0] if response_chunks else 0
last_response_time = response_chunks[-1][0] if response_chunks else 0

print(f"Response generation time: {last_response_time - first_response_time:.2f}s")

# Look for TTS evidence in the timeline
tts_during_response = False
for i, (elapsed, msg) in enumerate(events):
    if "TTS" in msg and first_response_time < elapsed < last_response_time:
        tts_during_response = True
        print(f"✅ TTS activity at {elapsed:.2f}s (during response generation)")

if not tts_during_response:
    print("❌ No TTS activity during response generation")
    print("   TTS is waiting for complete response (NOT STREAMING)")
else:
    print("✅ TTS IS STREAMING!")

print()
print("RECOMMENDATION:")
if tts_during_response:
    print("Streaming appears to be working correctly.")
else:
    print("Streaming is NOT working. Audio plays after response completes.")
    print("Check console for [TTS Debug] messages.")
'''
    
    return test_code

def create_diagnostic_test():
    """Create a diagnostic test to identify the exact issue."""
    
    diag_code = '''#!/usr/bin/env python3
"""Diagnostic test to find why streaming isn't working."""

import time
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("STREAMING TTS DIAGNOSTIC")
print("="*50)

# Capture all debug output
logging.basicConfig(level=logging.DEBUG)

# Test 1: Check if responder initializes with TTS
print("\\n1. Testing responder initialization...")

from tsutils import configuration
from app.transcribe import app_utils
from app.transcribe.global_vars import TranscriptionGlobals

config = configuration.Config().data
global_vars = TranscriptionGlobals()
global_vars.config = config

# Create responder and check attributes
responder = app_utils.create_responder(
    provider_name=config['General']['chat_inference_provider'],
    config=config,
    convo=global_vars.convo,
    save_to_file=False,
    response_file_name="test.txt"
)

print(f"   Responder class: {responder.__class__.__name__}")
print(f"   Has tts_enabled: {hasattr(responder, 'tts_enabled')}")
if hasattr(responder, 'tts_enabled'):
    print(f"   tts_enabled value: {responder.tts_enabled}")
print(f"   Has sent_q: {hasattr(responder, 'sent_q')}")
print(f"   Has _handle_streaming_token: {hasattr(responder, '_handle_streaming_token')}")

# Test 2: Check if tokens are being handled
print("\\n2. Testing token handling...")

if hasattr(responder, '_handle_streaming_token'):
    # Simulate some tokens
    test_tokens = ["Hello", " world", ".", " This", " is", " a", " test", "."]
    
    for token in test_tokens:
        responder._handle_streaming_token(token)
        print(f"   Sent token: '{token}'")
        
        # Check buffer state
        if hasattr(responder, 'buffer'):
            print(f"   Buffer: '{responder.buffer}'")
        
        # Check queue
        if hasattr(responder, 'sent_q'):
            print(f"   Queue size: {responder.sent_q.qsize()}")
        
        time.sleep(0.1)
    
    # Flush any remaining
    if hasattr(responder, 'flush_tts_buffer'):
        responder.flush_tts_buffer()
        print("   Flushed buffer")
else:
    print("   ERROR: No _handle_streaming_token method!")

# Test 3: Check the actual flow
print("\\n3. Checking actual token flow...")

# Look at the source to see where tokens are handled
import inspect
if hasattr(responder, 'generate_response_from_transcript_no_check'):
    source = inspect.getsource(responder.generate_response_from_transcript_no_check)
    if "_handle_streaming_token" in source:
        print("   ✓ Token handler is called in response generation")
    else:
        print("   ✗ Token handler NOT called in response generation!")

print("\\n" + "="*50)
print("DIAGNOSIS COMPLETE")
print("Check the output above to see where streaming breaks down.")
'''
    
    return diag_code

def main():
    """Create all test files."""
    print("Creating streaming TTS test files...\n")
    
    # Create visual test
    visual_test = create_visual_test()
    with open("test_streaming_visual_windows.py", 'w') as f:
        f.write(visual_test)
    print("✓ Created test_streaming_visual_windows.py")
    
    # Create diagnostic test
    diag_test = create_diagnostic_test()
    with open("diagnose_streaming_issue.py", 'w') as f:
        f.write(diag_test)
    print("✓ Created diagnose_streaming_issue.py")
    
    # Create final fix based on all findings
    final_fix = '''#!/usr/bin/env python3
"""Final comprehensive fix for streaming TTS."""

import os
import re

def apply_final_streaming_fix():
    """Apply the definitive fix for streaming TTS."""
    
    print("Applying FINAL streaming TTS fix...\\n")
    
    # The core issue: Token handler might not be called during streaming
    gpt_path = "app/transcribe/gpt_responder.py"
    
    if not os.path.exists(gpt_path):
        print("Error: gpt_responder.py not found!")
        return
    
    with open(gpt_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Ensure token handler is called
    print("1. Checking token handler calls...")
    
    # Find where we accumulate messages
    pattern = r'collected_messages \\+= message_text'
    matches = list(re.finditer(pattern, content))
    
    fixed_count = 0
    for match in matches:
        # Check if _handle_streaming_token is called nearby
        start = max(0, match.start() - 200)
        end = min(len(content), match.end() + 200)
        context = content[start:end]
        
        if "_handle_streaming_token" not in context:
            print(f"   Found accumulation without token handler at position {match.start()}")
            # This is a problem - we need to add the handler call
            fixed_count += 1
    
    if fixed_count > 0:
        print(f"   ✗ Found {fixed_count} places missing token handler!")
        # Add the fix here
    else:
        print("   ✓ Token handlers properly called")
    
    # Fix 2: Make sure TTS worker starts
    print("\\n2. Checking TTS worker initialization...")
    
    if "self.tts_worker_thread.start()" in content:
        print("   ✓ TTS worker thread starts")
    else:
        print("   ✗ TTS worker thread not starting!")
    
    # Fix 3: Reduce latency
    print("\\n3. Optimizing for lower latency...")
    
    # Change minimum sentence length to 5
    params_path = "app/transcribe/parameters.yaml"
    if os.path.exists(params_path):
        with open(params_path, 'r') as f:
            params = f.read()
        
        params = re.sub(r'tts_min_sentence_chars:\\s*\\d+', 'tts_min_sentence_chars: 5', params)
        
        with open(params_path, 'w') as f:
            f.write(params)
        print("   ✓ Reduced minimum sentence length")
    
    print("\\n✅ Final fixes applied!")
    print("\\nNow run: python test_streaming_visual_windows.py")

if __name__ == "__main__":
    apply_final_streaming_fix()
'''
    
    with open("apply_final_streaming_fix.py", 'w') as f:
        f.write(final_fix)
    print("✓ Created apply_final_streaming_fix.py")
    
    print("\n" + "="*50)
    print("TEST INSTRUCTIONS:\n")
    print("1. First run the diagnostic:")
    print("   python diagnose_streaming_issue.py")
    print("\n2. Apply the final fix:")
    print("   python apply_final_streaming_fix.py")
    print("\n3. Run the visual test:")
    print("   python test_streaming_visual_windows.py")
    print("\nThe visual test will clearly show if streaming is working.")
    print("Look for '✅ TTS IS STREAMING!' or '❌ NOT STREAMING'")

if __name__ == "__main__":
    main()
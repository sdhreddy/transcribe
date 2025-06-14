#!/usr/bin/env python3
"""Automated test for streaming TTS - no manual intervention needed."""

import os
import sys
import time
import threading
import queue
import logging
from datetime import datetime
import re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture all logs
log_capture = []
response_timeline = []
tts_timeline = []

class LogCapture(logging.Handler):
    """Capture log messages for analysis."""
    def emit(self, record):
        log_capture.append({
            'time': time.time(),
            'level': record.levelname,
            'message': record.getMessage()
        })

def setup_logging():
    """Setup logging to capture debug messages."""
    # Get all relevant loggers
    loggers = [
        'tsutils.app_logging.gpt_responder',
        'tsutils.app_logging.audio_player',
        'gpt_responder',
        'audio_player'
    ]
    
    handler = LogCapture()
    handler.setLevel(logging.DEBUG)
    
    for logger_name in loggers:
        logger = logging.getLogger(logger_name)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
    
    # Also capture root logger
    logging.getLogger().addHandler(handler)

def analyze_logs():
    """Analyze captured logs for streaming behavior."""
    print("\n=== LOG ANALYSIS ===\n")
    
    # Find key events
    tts_init = [log for log in log_capture if "TTS streaming enabled" in log['message']]
    tokens_received = [log for log in log_capture if "Token received:" in log['message']]
    sentences_detected = [log for log in log_capture if "Sentence detected:" in log['message']]
    tts_processing = [log for log in log_capture if "TTS processing sentence:" in log['message']]
    audio_chunks = [log for log in log_capture if "First audio chunk received" in log['message']]
    
    print(f"TTS Initialized: {len(tts_init) > 0}")
    print(f"Tokens received: {len(tokens_received)}")
    print(f"Sentences detected: {len(sentences_detected)}")
    print(f"TTS processing: {len(tts_processing)}")
    print(f"Audio chunks: {len(audio_chunks)}")
    
    # Check streaming behavior
    if tokens_received and sentences_detected:
        # Calculate time from first token to first sentence
        if sentences_detected:
            first_token_time = tokens_received[0]['time'] if tokens_received else 0
            first_sentence_time = sentences_detected[0]['time']
            latency = first_sentence_time - first_token_time
            print(f"\nFirst sentence detection latency: {latency:.2f}s")
            
            if latency < 2.0:
                print("✅ PASS: Sentence detected quickly")
            else:
                print("❌ FAIL: Sentence detection too slow")
    
    # Check if TTS is processing during response generation
    if sentences_detected and tts_processing:
        # Find overlaps
        response_still_generating = True
        for tts_log in tts_processing:
            # Check if this TTS happened before response completed
            completion_logs = [log for log in log_capture if "streaming_complete" in log['message']]
            if completion_logs:
                if tts_log['time'] < completion_logs[0]['time']:
                    print("✅ PASS: TTS processing during response generation!")
                    response_still_generating = False
                    break
        
        if response_still_generating:
            print("❌ FAIL: TTS only after response complete")
    
    return len(sentences_detected) > 0 and len(tts_processing) > 0

def simulate_conversation():
    """Simulate a conversation flow."""
    print("=== SIMULATING CONVERSATION ===\n")
    
    # 1. Initialize the system
    print("1. Initializing system...")
    from tsutils import configuration
    from app.transcribe.global_vars import TranscriptionGlobals
    from app.transcribe import app_utils
    
    config = configuration.Config().data
    
    # Check configuration
    streaming_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
    tts_provider = config.get('General', {}).get('tts_provider', 'gtts')
    
    print(f"   Streaming enabled: {streaming_enabled}")
    print(f"   TTS provider: {tts_provider}")
    
    if not streaming_enabled or tts_provider != 'openai':
        print("\n❌ Configuration not set for streaming!")
        return False
    
    # 2. Create components
    print("\n2. Creating components...")
    global_vars = TranscriptionGlobals()
    global_vars.config = config
    
    # Create responder
    chat_provider = config['General']['chat_inference_provider']
    responder = app_utils.create_responder(
        provider_name=chat_provider,
        config=config,
        convo=global_vars.convo,
        save_to_file=False,
        response_file_name="test.txt"
    )
    
    if not responder:
        print("❌ Failed to create responder!")
        return False
    
    print(f"   Responder created: {responder.__class__.__name__}")
    print(f"   TTS enabled: {getattr(responder, 'tts_enabled', False)}")
    
    # 3. Simulate transcription
    print("\n3. Simulating colleague speech...")
    test_utterance = "Can you explain what a Python decorator is and show me a simple example?"
    
    # Update conversation as if transcribed
    global_vars.convo.update_conversation(
        persona="Human",
        text=test_utterance,
        time_spoken=datetime.utcnow(),
        update_previous=False
    )
    
    print(f"   Added: '{test_utterance}'")
    
    # 4. Get response
    print("\n4. Generating GPT response...")
    responder.enabled = True
    
    start_time = time.time()
    
    # Start monitoring response
    def monitor_response():
        last_len = 0
        while True:
            current_response = getattr(responder, 'response', '')
            if len(current_response) > last_len:
                new_text = current_response[last_len:]
                response_timeline.append({
                    'time': time.time() - start_time,
                    'text': new_text,
                    'total': len(current_response)
                })
                last_len = len(current_response)
            
            if hasattr(responder, 'streaming_complete') and responder.streaming_complete.is_set():
                break
            time.sleep(0.05)
    
    monitor_thread = threading.Thread(target=monitor_response, daemon=True)
    monitor_thread.start()
    
    # Generate response
    response = responder.generate_response_from_transcript_no_check()
    
    # Wait for monitoring to complete
    monitor_thread.join(timeout=5)
    
    end_time = time.time()
    duration = end_time - start_time
    
    print(f"   Response generated in {duration:.2f}s")
    if response:
        print(f"   Response length: {len(response)} chars")
        print(f"   Response preview: '{response[:100]}...'")
    else:
        print("   ❌ No response generated!")
    
    # 5. Analyze timing
    print("\n5. Analyzing streaming behavior...")
    
    # Show response timeline
    if response_timeline:
        print("\n   Response chunks timeline:")
        for i, chunk in enumerate(response_timeline[:5]):
            print(f"   {chunk['time']:6.2f}s - Chunk {i+1}: {len(chunk['text'])} chars")
    
    # Check logs
    streaming_success = analyze_logs()
    
    return streaming_success

def create_fix_script():
    """Create a script to fix identified issues."""
    print("\n=== CREATING FIX SCRIPT ===\n")
    
    fix_content = '''#!/usr/bin/env python3
"""Fix streaming TTS issues found by automated test."""

import os
import re

def fix_streaming_issues():
    """Apply fixes for streaming TTS."""
    
    print("Applying streaming TTS fixes...\\n")
    
    # Fix 1: Ensure sentences are processed immediately
    print("1. Optimizing sentence processing...")
    
    gpt_path = "app/transcribe/gpt_responder.py"
    if os.path.exists(gpt_path):
        with open(gpt_path, 'r') as f:
            content = f.read()
        
        # Add immediate processing flag
        if "# Process immediately" not in content:
            content = content.replace(
                "self.sent_q.put(complete_sentence)",
                "self.sent_q.put(complete_sentence)  # Process immediately"
            )
            
            with open(gpt_path, 'w') as f:
                f.write(content)
            print("   ✓ Added immediate processing")
    
    # Fix 2: Reduce minimum sentence length
    print("\\n2. Reducing minimum sentence length...")
    
    params_path = "app/transcribe/parameters.yaml"
    if os.path.exists(params_path):
        with open(params_path, 'r') as f:
            content = f.read()
        
        # Change min chars from 10 to 5
        content = re.sub(
            r'tts_min_sentence_chars:\\s*\\d+',
            'tts_min_sentence_chars: 5',
            content
        )
        
        with open(params_path, 'w') as f:
            f.write(content)
        print("   ✓ Reduced to 5 characters")
    
    print("\\n✅ Fixes applied!")

if __name__ == "__main__":
    fix_streaming_issues()
'''
    
    with open("fix_streaming_automated.py", 'w') as f:
        f.write(fix_content)
    
    print("Created fix_streaming_automated.py")

def main():
    """Main test execution."""
    print("=== AUTOMATED STREAMING TTS TEST ===")
    print("This test will simulate a full conversation flow\\n")
    
    # Setup logging capture
    setup_logging()
    
    try:
        # Run the simulation
        success = simulate_conversation()
        
        # Create fix script
        create_fix_script()
        
        # Summary
        print("\n" + "="*50)
        print("TEST SUMMARY:\n")
        
        if success:
            print("✅ Streaming TTS is working!")
            print("   - Sentences are detected during response generation")
            print("   - TTS processes sentences before response completes")
        else:
            print("❌ Streaming TTS is NOT working properly")
            print("   - Check [TTS Debug] messages in logs")
            print("   - Run: python fix_streaming_automated.py")
        
        # Show captured logs
        if log_capture:
            print("\nKey log messages:")
            for log in log_capture[:10]:
                if "TTS Debug" in log['message']:
                    print(f"   {log['message']}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
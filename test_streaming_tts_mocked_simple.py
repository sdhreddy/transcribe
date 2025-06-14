#!/usr/bin/env python3
"""Automated test for streaming TTS with mocked audio - simplified approach."""

import os
import sys
import time
import threading
import queue
import logging
from datetime import datetime
from unittest.mock import MagicMock

# Mock pyaudio BEFORE any imports
mock_pyaudio = MagicMock()
mock_pyaudio_instance = MagicMock()
mock_pyaudio_instance.get_device_count.return_value = 1
mock_pyaudio_instance.get_default_output_device_info.return_value = {'index': 0, 'name': 'Mock Device'}
mock_stream = MagicMock()
mock_pyaudio_instance.open.return_value = mock_stream
mock_pyaudio.PyAudio.return_value = mock_pyaudio_instance
mock_pyaudio.paInt16 = 8
sys.modules['pyaudio'] = mock_pyaudio

# Now add paths and import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture variables
log_capture = []
response_timeline = []
audio_chunks_received = []
sentences_processed = []

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
    handler = LogCapture()
    handler.setLevel(logging.DEBUG)
    
    # Add to root logger to catch everything
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)

def analyze_streaming_flow():
    """Analyze if streaming TTS is working correctly."""
    print("\n=== STREAMING FLOW ANALYSIS ===\n")
    
    # Check for key streaming indicators
    streaming_indicators = {
        'tokens_received': 0,
        'sentences_detected': 0,
        'tts_called': 0,
        'audio_chunks': 0,
        'streaming_enabled': False
    }
    
    for log in log_capture:
        msg = log['message']
        if "Token received:" in msg or "token:" in msg.lower():
            streaming_indicators['tokens_received'] += 1
        elif "Sentence detected:" in msg or "sentence_end" in msg:
            streaming_indicators['sentences_detected'] += 1
        elif "TTS processing" in msg or "Generating TTS" in msg:
            streaming_indicators['tts_called'] += 1
        elif "Audio chunk" in msg or "audio bytes" in msg:
            streaming_indicators['audio_chunks'] += 1
        elif "TTS streaming enabled" in msg:
            streaming_indicators['streaming_enabled'] = True
    
    print("Streaming Indicators:")
    for key, value in streaming_indicators.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")
    
    # Check for streaming behavior
    if streaming_indicators['sentences_detected'] > 0:
        # Look for evidence of concurrent processing
        concurrent_processing = False
        for i, log in enumerate(log_capture):
            if "TTS processing" in log['message']:
                # Check if more tokens came after this
                for j in range(i+1, len(log_capture)):
                    if "Token received:" in log_capture[j]['message']:
                        concurrent_processing = True
                        break
        
        if concurrent_processing:
            print("\n✅ STREAMING CONFIRMED: TTS processing while tokens still arriving")
        else:
            print("\n❌ NO STREAMING: TTS only after all tokens received")
    
    return streaming_indicators['sentences_detected'] > 0

def run_test():
    """Run the streaming TTS test."""
    print("=== RUNNING STREAMING TTS TEST (MOCKED) ===\n")
    
    try:
        # Import modules after mocking
        from tsutils import configuration
        from app.transcribe.global_vars import TranscriptionGlobals
        from app.transcribe import app_utils
        from app.transcribe.conversation import Conversation
        
        # 1. Load configuration
        print("1. Loading configuration...")
        config = configuration.Config().data
        
        # Force streaming settings
        config['General']['tts_streaming_enabled'] = True
        config['General']['tts_provider'] = 'openai'
        print("   ✓ Forced streaming TTS configuration")
        
        # 2. Create components
        print("\n2. Creating components...")
        global_vars = TranscriptionGlobals()
        global_vars.config = config
        
        # Create conversation
        convo = Conversation()
        global_vars.convo = convo
        
        # Create responder
        chat_provider = config['General'].get('chat_inference_provider', 'openai')
        print(f"   Using chat provider: {chat_provider}")
        
        responder = app_utils.create_responder(
            provider_name=chat_provider,
            config=config,
            convo=convo,
            save_to_file=False,
            response_file_name="test.txt"
        )
        
        if not responder:
            print("❌ Failed to create responder!")
            return False
        
        print(f"   ✓ Responder created: {responder.__class__.__name__}")
        
        # Check TTS setup
        has_tts = hasattr(responder, 'tts_enabled')
        print(f"   TTS enabled attribute: {has_tts}")
        if has_tts:
            print(f"   TTS enabled value: {responder.tts_enabled}")
        
        # 3. Simulate conversation
        print("\n3. Simulating conversation...")
        test_prompt = "What is machine learning? Please explain briefly."
        
        convo.update_conversation(
            persona="Human",
            text=test_prompt,
            time_spoken=datetime.utcnow(),
            update_previous=False
        )
        print(f"   Added prompt: '{test_prompt}'")
        
        # 4. Generate response
        print("\n4. Generating response with streaming...")
        responder.enabled = True
        
        # Monitor the response generation
        start_time = time.time()
        
        # Hook into the responder to track streaming
        if hasattr(responder, 'on_token'):
            original_on_token = responder.on_token
            def track_token(token):
                response_timeline.append({
                    'time': time.time() - start_time,
                    'token': token
                })
                return original_on_token(token) if original_on_token else None
            responder.on_token = track_token
        
        # Generate the response
        print("   Calling generate_response_from_transcript_no_check()...")
        response = responder.generate_response_from_transcript_no_check()
        
        end_time = time.time()
        duration = end_time - start_time
        
        print(f"\n   Response generated in {duration:.2f}s")
        if response:
            print(f"   Response length: {len(response)} chars")
            print(f"   Response preview: {response[:100]}...")
        else:
            print("   ❌ No response generated")
        
        # 5. Analyze results
        print("\n5. Analyzing results...")
        
        # Check if we captured streaming data
        if response_timeline:
            print(f"   ✓ Captured {len(response_timeline)} response chunks")
            print("   First 5 chunks:")
            for i, chunk in enumerate(response_timeline[:5]):
                print(f"     {chunk['time']:.2f}s: {chunk.get('token', 'N/A')[:20]}...")
        else:
            print("   ❌ No response timeline captured")
        
        # Analyze logs
        return analyze_streaming_flow()
        
    except Exception as e:
        print(f"\n❌ Test error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test runner."""
    print("STREAMING TTS FLOW TEST (WSL COMPATIBLE)")
    print("="*50)
    print("This test verifies the streaming TTS flow without audio devices\n")
    
    # Setup logging
    setup_logging()
    
    # Run test
    success = run_test()
    
    # Summary
    print("\n" + "="*50)
    print("TEST RESULTS:\n")
    
    if success:
        print("✅ Streaming TTS flow appears to be working")
        print("   - Sentences are being detected from streaming tokens")
        print("   - TTS would be called for each sentence")
    else:
        print("❌ Streaming TTS flow has issues")
        print("   - Check if sentences are being detected")
        print("   - Verify TTS is being called during streaming")
    
    # Show key logs
    print(f"\nTotal logs captured: {len(log_capture)}")
    if log_capture:
        print("\nKey log messages:")
        important_logs = [log for log in log_capture if any(
            keyword in log['message'] for keyword in 
            ['TTS', 'Sentence', 'Token', 'streaming', 'enabled']
        )]
        for log in important_logs[:10]:
            print(f"  [{log['level']}] {log['message'][:100]}...")

if __name__ == "__main__":
    main()
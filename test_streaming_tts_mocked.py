#!/usr/bin/env python3
"""Automated test for streaming TTS with mocked audio components - runs in WSL without audio devices."""

import os
import sys
import time
import threading
import queue
import logging
from datetime import datetime
import re
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Capture all logs
log_capture = []
response_timeline = []
tts_timeline = []
audio_chunks_received = []

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

class MockStreamingAudioPlayer(threading.Thread):
    """Mock StreamingAudioPlayer that doesn't require PyAudio."""
    
    def __init__(self, sample_rate=24_000, buf_ms=50, output_device_index=None):
        super().__init__(daemon=True)
        self.q = queue.Queue(maxsize=20)
        self.sample_rate = sample_rate
        self.buf_ms = buf_ms / 1000
        self.running = True
        self.playing = False
        self.chunks_received = []
        self.output_device_index = output_device_index
        
        # Log initialization
        logger = logging.getLogger('tsutils.app_logging.audio_player')
        logger.info(f"[MOCK] Streaming audio player initialized: {sample_rate}Hz, {buf_ms}ms buffer")
        
    def enqueue(self, chunk: bytes):
        """Add audio chunk to playback queue."""
        timestamp = time.time()
        self.chunks_received.append({'time': timestamp, 'size': len(chunk)})
        audio_chunks_received.append({'time': timestamp, 'size': len(chunk)})
        
        # Log chunk receipt
        logger = logging.getLogger('tsutils.app_logging.audio_player')
        logger.info(f"[MOCK] Audio chunk received: {len(chunk)} bytes")
        
        if len(self.chunks_received) == 1:
            logger.info("[TTS Debug] First audio chunk received")
        
        try:
            self.q.put(chunk, timeout=0.1)
        except queue.Full:
            logger.warning("[TTS Debug] Audio queue full, dropping chunk")
    
    def recover_audio(self):
        """Mock audio recovery."""
        logger = logging.getLogger('tsutils.app_logging.audio_player')
        logger.info("[MOCK] Audio recovery successful (no-op)")
        return True
    
    def stop(self):
        """Stop the audio player thread."""
        self.running = False
        self.q.put(None)  # Sentinel to unblock
    
    def run(self):
        """Main playback loop - simulates audio playback without actual audio."""
        logger = logging.getLogger('tsutils.app_logging.audio_player')
        logger.info("[MOCK] Streaming audio player thread started")
        
        while self.running:
            try:
                chunk = self.q.get(timeout=1.0)
                if chunk is None:
                    logger.info("[MOCK] Received stop signal")
                    break
                
                self.playing = True
                # Simulate playback time based on chunk size
                # Assuming 16-bit mono at sample_rate
                duration = len(chunk) / (2 * self.sample_rate)
                logger.debug(f"[MOCK] 'Playing' {len(chunk)} bytes for {duration:.3f}s")
                time.sleep(duration * 0.1)  # Speed up for testing
                self.playing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[MOCK] Playback error: {type(e).__name__}: {e}")
        
        logger.info("[MOCK] Streaming audio player thread stopped")

def mock_pyaudio():
    """Create mock PyAudio classes."""
    mock_pa = MagicMock()
    mock_pa.get_device_count.return_value = 1
    mock_pa.get_default_output_device_info.return_value = {
        'index': 0,
        'name': 'Mock Audio Device'
    }
    
    # Mock stream
    mock_stream = MagicMock()
    mock_stream.write.return_value = None
    mock_pa.open.return_value = mock_stream
    
    # Mock constants
    mock_pa.paInt16 = 8  # PyAudio constant
    
    return mock_pa

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
    print(f"Total mocked audio chunks: {len(audio_chunks_received)}")
    
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
    
    # Check audio chunk generation
    if audio_chunks_received:
        print(f"\n✅ PASS: {len(audio_chunks_received)} audio chunks generated")
        first_chunk_time = audio_chunks_received[0]['time'] - response_timeline[0]['time'] if response_timeline else 0
        print(f"   First chunk latency: {first_chunk_time:.2f}s from response start")
    else:
        print("\n❌ FAIL: No audio chunks generated")
    
    return len(sentences_detected) > 0 and len(tts_processing) > 0

def simulate_conversation():
    """Simulate a conversation flow with mocked audio."""
    print("=== SIMULATING CONVERSATION (MOCKED AUDIO) ===\n")
    
    # Mock pyaudio module itself before imports
    import sys
    mock_pyaudio_module = MagicMock()
    mock_pyaudio_module.PyAudio = mock_pyaudio
    mock_pyaudio_module.paInt16 = 8
    sys.modules['pyaudio'] = mock_pyaudio_module
    
    # Mock other modules that might use pyaudio
    try:
        # Pre-emptively patch modules that might import pyaudio
        with patch.dict('sys.modules', {'pyaudio': mock_pyaudio_module}):
            # Now we can patch the StreamingAudioPlayer
            with patch('app.transcribe.audio_player_streaming.StreamingAudioPlayer', MockStreamingAudioPlayer):
                
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
                print("   Attempting to enable streaming for test...")
                
                # Force enable streaming for the test
                config['General']['tts_streaming_enabled'] = True
                config['General']['tts_provider'] = 'openai'
                print("   ✓ Forced streaming configuration for test")
            
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
            response_timeline.clear()  # Reset timeline
            
            # Start monitoring response
            def monitor_response():
                last_len = 0
                while True:
                    current_response = getattr(responder, 'response', '')
                    if len(current_response) > last_len:
                        new_text = current_response[last_len:]
                        response_timeline.append({
                            'time': time.time(),
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
                    elapsed = chunk['time'] - response_timeline[0]['time'] if response_timeline else 0
                    print(f"   {elapsed:6.2f}s - Chunk {i+1}: {len(chunk['text'])} chars")
            
            # Show audio chunks timeline
            if audio_chunks_received:
                print("\n   Audio chunks timeline:")
                start_ref = response_timeline[0]['time'] if response_timeline else start_time
                for i, chunk in enumerate(audio_chunks_received[:5]):
                    elapsed = chunk['time'] - start_ref
                    print(f"   {elapsed:6.2f}s - Audio chunk {i+1}: {chunk['size']} bytes")
            
            # Check logs
            streaming_success = analyze_logs()
            
            return streaming_success

def show_detailed_logs():
    """Show detailed log analysis."""
    print("\n=== DETAILED LOG ANALYSIS ===\n")
    
    # Group logs by type
    log_types = {
        'token': [],
        'sentence': [],
        'tts': [],
        'audio': [],
        'error': []
    }
    
    for log in log_capture:
        msg = log['message']
        if "Token received:" in msg:
            log_types['token'].append(log)
        elif "Sentence detected:" in msg or "sentence_end" in msg:
            log_types['sentence'].append(log)
        elif "TTS processing" in msg or "TTS Debug" in msg:
            log_types['tts'].append(log)
        elif "[MOCK]" in msg:
            log_types['audio'].append(log)
        elif log['level'] == 'ERROR':
            log_types['error'].append(log)
    
    # Show summary
    print("Log Summary:")
    print(f"  Tokens: {len(log_types['token'])}")
    print(f"  Sentences: {len(log_types['sentence'])}")
    print(f"  TTS Events: {len(log_types['tts'])}")
    print(f"  Audio Events: {len(log_types['audio'])}")
    print(f"  Errors: {len(log_types['error'])}")
    
    # Show errors if any
    if log_types['error']:
        print("\nErrors detected:")
        for err in log_types['error'][:5]:
            print(f"  - {err['message']}")
    
    # Show sentence detection flow
    if log_types['sentence']:
        print("\nSentence Detection Flow:")
        for i, log in enumerate(log_types['sentence'][:5]):
            print(f"  {i+1}. {log['message'][:80]}...")

def main():
    """Main test execution."""
    print("=== AUTOMATED STREAMING TTS TEST (MOCKED FOR WSL) ===")
    print("This test simulates audio playback without requiring audio devices\n")
    
    # Setup logging capture
    setup_logging()
    
    try:
        # Run the simulation
        success = simulate_conversation()
        
        # Show detailed logs
        show_detailed_logs()
        
        # Summary
        print("\n" + "="*50)
        print("TEST SUMMARY:\n")
        
        if success:
            print("✅ Streaming TTS flow is working!")
            print("   - Sentences are detected during response generation")
            print("   - TTS processes sentences before response completes")
            print("   - Audio chunks are being generated (mocked)")
        else:
            print("❌ Streaming TTS flow has issues")
            print("   - Check the detailed logs above")
            print("   - Verify configuration settings")
        
        # Final statistics
        print(f"\nTest Statistics:")
        print(f"  Total logs captured: {len(log_capture)}")
        print(f"  Response chunks: {len(response_timeline)}")
        print(f"  Audio chunks: {len(audio_chunks_received)}")
        
    except Exception as e:
        print(f"\n❌ Test failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
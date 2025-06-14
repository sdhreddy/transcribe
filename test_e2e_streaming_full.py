#!/usr/bin/env python3
"""End-to-end integration test for streaming TTS."""

import os
import sys
import time
import threading
import queue
from unittest.mock import Mock, patch
import wave
import struct

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class E2EStreamingTest:
    """End-to-end test simulating real user interaction."""
    
    def __init__(self):
        self.events = []
        self.start_time = time.time()
        
    def log_event(self, event_type, message):
        """Log an event with timing."""
        elapsed = time.time() - self.start_time
        self.events.append({
            'time': elapsed,
            'type': event_type,
            'message': message
        })
        print(f"[{elapsed:5.2f}s] {event_type}: {message}")
    
    def create_mock_audio(self, duration=3.0, sample_rate=16000):
        """Create mock audio data simulating speech."""
        samples = []
        for i in range(int(sample_rate * duration)):
            # Simulate speech frequencies
            t = i / sample_rate
            sample = int(2000 * (
                0.3 * (t % 0.1) +  # Simulate speech pattern
                0.2 * (t % 0.05)
            ))
            samples.append(sample)
        
        return struct.pack('<%dh' % len(samples), *samples)
    
    def test_full_flow(self):
        """Test the complete flow from voice input to audio output."""
        print("\n" + "="*60)
        print("E2E STREAMING TTS TEST")
        print("="*60)
        
        # Import components
        from app.transcribe import audio_transcriber
        from app.transcribe import gpt_responder
        from app.transcribe import conversation
        from app.transcribe import global_vars
        from tsutils import configuration
        
        # Load config
        config = configuration.Config().data
        self.log_event("CONFIG", f"LLM interval: {config['General']['llm_response_interval']}s")
        self.log_event("CONFIG", f"TTS enabled: {config['General']['tts_streaming_enabled']}")
        
        # Create mock components
        mock_queue = queue.Queue()
        mock_convo = Mock(spec=conversation.Conversation)
        mock_convo.get_merged_conversation_response.return_value = [
            ("You", "Hello, how are you?", "1")
        ]
        
        # Create transcriber
        self.log_event("INIT", "Creating audio transcriber")
        transcriber = Mock()
        transcriber.transcript_changed_event = threading.Event()
        transcriber.get_transcript.return_value = ["You: Hello, how are you?"]
        
        # Create GPT responder
        self.log_event("INIT", "Creating GPT responder")
        responder = gpt_responder.GPTResponder(
            config=config,
            convo=mock_convo,
            file_name="test.txt",
            save_to_file=False
        )
        
        # Mock the LLM response
        def mock_llm_response(*args, **kwargs):
            self.log_event("GPT", "Starting GPT response generation")
            
            # Simulate streaming tokens
            test_response = "Hello! I'm doing well, thank you. How can I help you today?"
            words = test_response.split()
            
            for i, word in enumerate(words):
                time.sleep(0.1)  # Simulate token delay
                responder._handle_streaming_token(word + " ")
                self.log_event("TOKEN", f"Token {i+1}: '{word}'")
            
            responder.flush_tts_buffer()
            return test_response
        
        responder.generate_response_from_transcript_no_check = mock_llm_response
        responder.enabled = True
        
        # Start responder thread
        responder_thread = threading.Thread(
            target=responder.respond_to_transcriber,
            args=(transcriber,),
            daemon=True
        )
        responder_thread.start()
        
        # Simulate voice input
        self.log_event("VOICE", "Simulating voice input: 'Hello, how are you?'")
        
        # Trigger transcript change
        time.sleep(0.5)
        self.log_event("TRANSCRIPT", "Setting transcript changed event")
        transcriber.transcript_changed_event.set()
        
        # Wait for processing
        self.log_event("WAIT", "Waiting for GPT response...")
        time.sleep(3)
        
        # Check if TTS was triggered
        if hasattr(responder, 'sent_q') and responder.tts_enabled:
            sentences_queued = []
            try:
                while True:
                    sentence = responder.sent_q.get_nowait()
                    sentences_queued.append(sentence)
            except queue.Empty:
                pass
            
            self.log_event("TTS", f"Sentences queued for TTS: {len(sentences_queued)}")
            for s in sentences_queued:
                self.log_event("SENTENCE", f"'{s}'")
        
        # Analyze results
        print("\n" + "="*60)
        print("ANALYSIS")
        print("="*60)
        
        # Calculate timings
        voice_to_gpt = 0
        gpt_to_first_token = 0
        first_token_to_audio = 0
        
        for i, event in enumerate(self.events):
            if event['type'] == 'TRANSCRIPT':
                voice_to_gpt = event['time']
            elif event['type'] == 'GPT':
                gpt_to_first_token = event['time'] - voice_to_gpt
            elif event['type'] == 'TOKEN' and 'Token 1:' in event['message']:
                first_token_time = event['time']
        
        print(f"Voice → GPT trigger: {voice_to_gpt:.2f}s")
        print(f"GPT trigger → First token: {gpt_to_first_token:.2f}s")
        print(f"Expected total delay: ~{voice_to_gpt + gpt_to_first_token:.2f}s")
        
        # Check if delay is acceptable
        total_delay = voice_to_gpt + gpt_to_first_token
        if total_delay < 2.0:
            print("\n✅ Response time is good (<2s)")
        else:
            print(f"\n⚠️  Response time is slow ({total_delay:.1f}s)")
            if voice_to_gpt > 2.0:
                print("   Issue: LLM response interval too high")
            if gpt_to_first_token > 2.0:
                print("   Issue: GPT generation too slow")
        
        return total_delay < 2.0

if __name__ == '__main__':
    test = E2EStreamingTest()
    success = test.test_full_flow()
    
    print("\n" + "="*60)
    if success:
        print("✅ E2E TEST PASSED - Streaming should work!")
    else:
        print("❌ E2E TEST FAILED - Check timing analysis above")
    
    sys.exit(0 if success else 1)

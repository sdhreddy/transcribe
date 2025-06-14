#!/usr/bin/env python3
"""Real-time debugging tool to identify why streaming TTS isn't working."""

import os
import sys
import time
import threading
import queue
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class StreamingDebugger:
    """Debug streaming TTS in real-time."""
    
    def __init__(self):
        self.events = []
        self.start_time = time.time()
        
    def log_event(self, event_type, message, data=None):
        """Log an event with timing."""
        event = {
            'time': time.time() - self.start_time,
            'type': event_type,
            'message': message,
            'data': data,
            'timestamp': datetime.now().isoformat()
        }
        self.events.append(event)
        
        # Print in real-time
        print(f"[{event['time']:6.2f}s] {event_type}: {message}")
        if data:
            print(f"          Data: {data}")
    
    def analyze_issue(self):
        """Analyze the logged events to identify issues."""
        print("\n" + "=" * 60)
        print("STREAMING TTS ANALYSIS")
        print("=" * 60)
        
        # Group events by type
        event_types = {}
        for event in self.events:
            event_type = event['type']
            if event_type not in event_types:
                event_types[event_type] = []
            event_types[event_type].append(event)
        
        # Analysis 1: Check token flow
        print("\n1. Token Flow Analysis:")
        token_events = event_types.get('TOKEN', [])
        if not token_events:
            print("   ❌ No tokens received - GPT streaming not working")
        else:
            print(f"   ✅ {len(token_events)} tokens received")
            first_token_time = token_events[0]['time']
            print(f"   First token at: {first_token_time:.2f}s")
        
        # Analysis 2: Check sentence detection
        print("\n2. Sentence Detection Analysis:")
        sentence_events = event_types.get('SENTENCE', [])
        if not sentence_events:
            print("   ❌ No sentences detected - check regex pattern")
        else:
            print(f"   ✅ {len(sentence_events)} sentences detected")
            for i, event in enumerate(sentence_events[:3]):  # Show first 3
                print(f"   Sentence {i+1} at {event['time']:.2f}s: {event['data'][:50]}...")
        
        # Analysis 3: Check TTS generation
        print("\n3. TTS Generation Analysis:")
        tts_events = event_types.get('TTS_START', [])
        if not tts_events:
            print("   ❌ No TTS generation - check TTS worker thread")
        else:
            print(f"   ✅ {len(tts_events)} TTS generations started")
            
            # Check TTS completion
            tts_complete = event_types.get('TTS_COMPLETE', [])
            print(f"   ✅ {len(tts_complete)} TTS generations completed")
        
        # Analysis 4: Check audio playback
        print("\n4. Audio Playback Analysis:")
        audio_events = event_types.get('AUDIO_CHUNK', [])
        if not audio_events:
            print("   ❌ No audio chunks played - check audio player")
        else:
            print(f"   ✅ {len(audio_events)} audio chunks played")
            first_audio = audio_events[0]['time']
            print(f"   First audio at: {first_audio:.2f}s")
        
        # Analysis 5: Timing analysis
        print("\n5. Timing Analysis:")
        if token_events and audio_events:
            first_token = token_events[0]['time']
            first_audio = audio_events[0]['time']
            delay = first_audio - first_token
            print(f"   Token to audio delay: {delay:.2f}s")
            
            if delay > 2.0:
                print("   ⚠️  High delay - not true streaming")
            else:
                print("   ✅ Low delay - streaming working")
        
        # Analysis 6: Identify bottlenecks
        print("\n6. Bottleneck Analysis:")
        
        # Check if sentences are being queued but not processed
        queue_events = event_types.get('QUEUE', [])
        if queue_events:
            max_queue_size = max(e['data'] for e in queue_events if e['data'])
            print(f"   Max queue size: {max_queue_size}")
            if max_queue_size > 5:
                print("   ⚠️  Queue backing up - TTS processing too slow")
        
        # Check for errors
        error_events = event_types.get('ERROR', [])
        if error_events:
            print(f"\n   ❌ {len(error_events)} errors found:")
            for error in error_events:
                print(f"      - {error['message']}")
        
        # Summary
        print("\n" + "=" * 60)
        print("SUMMARY:")
        
        issues = []
        
        if not token_events:
            issues.append("No GPT tokens received")
        elif not sentence_events:
            issues.append("Sentence detection not working")
        elif not tts_events:
            issues.append("TTS not generating audio")
        elif not audio_events:
            issues.append("Audio not playing")
        elif token_events and audio_events:
            delay = audio_events[0]['time'] - token_events[0]['time']
            if delay > 2.0:
                issues.append(f"High latency ({delay:.1f}s) - not true streaming")
        
        if issues:
            print("Issues found:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ Streaming appears to be working correctly")
        
        return len(issues) == 0

def test_streaming_flow():
    """Test the streaming flow with mock data."""
    debugger = StreamingDebugger()
    
    print("Testing streaming TTS flow...")
    print("This will simulate a GPT response and track the flow\n")
    
    # Import components
    try:
        from app.transcribe.gpt_responder import GPTResponder
        from app.transcribe.streaming_tts import TTSConfig, create_tts
        from app.transcribe.audio_player_streaming import StreamingAudioPlayer
    except ImportError as e:
        debugger.log_event('ERROR', f'Import failed: {e}')
        debugger.analyze_issue()
        return
    
    # Mock config
    config = {
        'General': {
            'tts_streaming_enabled': True,
            'tts_provider': 'openai',
            'tts_voice': 'alloy',
            'tts_sample_rate': 24000,
            'tts_min_sentence_chars': 10,
            'llm_response_interval': 1
        },
        'OpenAI': {
            'api_key': os.environ.get('OPENAI_API_KEY', 'test-key')
        }
    }
    
    # Create components
    try:
        # Mock conversation
        class MockConversation:
            def update_conversation(self, **kwargs):
                pass
        
        # Create responder
        responder = GPTResponder(
            config=config,
            convo=MockConversation(),
            file_name='test.txt',
            save_to_file=False
        )
        
        debugger.log_event('INIT', 'GPTResponder created', 
                          {'tts_enabled': responder.tts_enabled})
        
        # Hook into responder to track events
        original_handle_token = responder._handle_streaming_token
        original_tts_worker = responder._tts_worker
        
        def tracked_handle_token(token):
            debugger.log_event('TOKEN', f'Token: "{token}"', len(responder.buffer))
            result = original_handle_token(token)
            
            # Check if sentence was detected
            if hasattr(responder, 'sent_q') and not responder.sent_q.empty():
                debugger.log_event('SENTENCE', 'Sentence queued', responder.sent_q.qsize())
            
            return result
        
        def tracked_tts_worker():
            while True:
                try:
                    sentence = responder.sent_q.get(timeout=0.5)
                    if sentence is None:
                        break
                    
                    debugger.log_event('TTS_START', f'Processing: "{sentence[:30]}..."')
                    
                    # Mock TTS generation
                    time.sleep(0.2)  # Simulate TTS delay
                    
                    debugger.log_event('TTS_COMPLETE', 'Audio generated')
                    
                    # Mock audio chunks
                    for i in range(3):
                        debugger.log_event('AUDIO_CHUNK', f'Chunk {i+1}', 4096)
                        time.sleep(0.05)
                    
                    responder.sent_q.task_done()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    debugger.log_event('ERROR', f'TTS worker error: {e}')
        
        # Replace methods
        responder._handle_streaming_token = tracked_handle_token
        
        # Start mock TTS worker
        if responder.tts_enabled:
            worker = threading.Thread(target=tracked_tts_worker, daemon=True)
            worker.start()
        
        # Simulate streaming tokens
        test_text = "Hello, this is a test. The quick brown fox jumps over the lazy dog. How are you today?"
        words = test_text.split()
        
        print("Simulating GPT streaming...\n")
        
        for word in words:
            tracked_handle_token(word + ' ')
            time.sleep(0.1)  # Simulate GPT delay
        
        # Flush buffer
        responder.flush_tts_buffer()
        
        # Wait for processing
        print("\nWaiting for processing to complete...")
        time.sleep(2)
        
        # Stop worker
        if responder.tts_enabled:
            responder.sent_q.put(None)
            worker.join(timeout=2)
        
    except Exception as e:
        debugger.log_event('ERROR', f'Test failed: {e}')
    
    # Analyze results
    debugger.analyze_issue()

def main():
    """Run the streaming debugger."""
    print("=" * 60)
    print("STREAMING TTS REAL-TIME DEBUGGER")
    print("=" * 60)
    print()
    
    # Check if we should run the test or just provide instructions
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        test_streaming_flow()
    else:
        print("This debugger helps identify why streaming TTS isn't working.")
        print("\nUsage:")
        print("1. Run with --test flag to test the flow:")
        print("   python debug_streaming_realtime.py --test")
        print("\n2. Or integrate into your app by adding debug calls:")
        print("   from debug_streaming_realtime import StreamingDebugger")
        print("   debugger = StreamingDebugger()")
        print("   debugger.log_event('TOKEN', 'Token received', token)")
        print("\nThe debugger will analyze:")
        print("- Token flow from GPT")
        print("- Sentence detection")
        print("- TTS generation")
        print("- Audio playback")
        print("- Timing and latency")

if __name__ == '__main__':
    main()
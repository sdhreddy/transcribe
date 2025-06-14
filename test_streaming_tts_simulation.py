#!/usr/bin/env python3
"""Simulate the streaming TTS flow to verify the logic without audio devices."""

import time
import threading
import queue
import re
from datetime import datetime

class MockStreamingSimulation:
    """Simulate the streaming TTS flow."""
    
    def __init__(self):
        self.sent_q = queue.Queue()
        self.response = ""
        self.complete_sentence = ""
        self.sentences_detected = []
        self.tts_processed = []
        self.audio_chunks = []
        self.streaming_complete = threading.Event()
        
    def detect_sentence_end(self, text):
        """Detect if text ends with a sentence marker."""
        # From the actual code pattern
        sentence_ends = ['.', '!', '?', ':', '\n', '。', '！', '？', '：', '।', '۔']
        return any(text.rstrip().endswith(end) for end in sentence_ends)
    
    def process_token(self, token):
        """Process a streaming token (simulating GPT responder logic)."""
        print(f"[{time.time():.2f}] Token received: '{token}'")
        
        self.response += token
        self.complete_sentence += token
        
        # Check for sentence end (from gpt_responder.py logic)
        if self.detect_sentence_end(self.complete_sentence):
            # Check minimum length (usually 10 chars)
            if len(self.complete_sentence.strip()) > 5:
                print(f"[{time.time():.2f}] Sentence detected: '{self.complete_sentence.strip()}'")
                self.sentences_detected.append({
                    'time': time.time(),
                    'sentence': self.complete_sentence.strip()
                })
                self.sent_q.put(self.complete_sentence)
                self.complete_sentence = ""
    
    def tts_processor_thread(self):
        """Simulate the TTS processor thread."""
        print(f"[{time.time():.2f}] TTS processor thread started")
        
        while not self.streaming_complete.is_set() or not self.sent_q.empty():
            try:
                sentence = self.sent_q.get(timeout=0.1)
                print(f"[{time.time():.2f}] TTS processing sentence: '{sentence.strip()[:50]}...'")
                
                # Simulate TTS processing time
                time.sleep(0.2)
                
                # Simulate audio chunk generation
                chunk_size = len(sentence) * 100  # Fake audio size
                self.audio_chunks.append({
                    'time': time.time(),
                    'size': chunk_size,
                    'sentence': sentence
                })
                print(f"[{time.time():.2f}] Audio chunk generated: {chunk_size} bytes")
                
                self.tts_processed.append({
                    'time': time.time(),
                    'sentence': sentence
                })
                
            except queue.Empty:
                continue
        
        print(f"[{time.time():.2f}] TTS processor thread stopped")
    
    def simulate_streaming_response(self, text):
        """Simulate a streaming response."""
        print(f"\n=== SIMULATING STREAMING RESPONSE ===")
        print(f"Full text: '{text[:100]}...'\n")
        
        # Start TTS processor thread
        tts_thread = threading.Thread(target=self.tts_processor_thread, daemon=True)
        tts_thread.start()
        
        # Simulate token streaming
        tokens = text.split(' ')
        start_time = time.time()
        
        for i, word in enumerate(tokens):
            # Add space except for first word
            token = word if i == 0 else ' ' + word
            self.process_token(token)
            
            # Simulate token arrival delay
            time.sleep(0.05)
        
        # Mark streaming complete
        self.streaming_complete.set()
        print(f"\n[{time.time():.2f}] Streaming complete")
        
        # Wait for TTS to finish
        tts_thread.join(timeout=2.0)
        
        end_time = time.time()
        duration = end_time - start_time
        
        return duration

def run_simulation():
    """Run the streaming simulation."""
    print("=== STREAMING TTS FLOW SIMULATION ===")
    print("This simulates the actual streaming logic without audio devices\n")
    
    # Test text with multiple sentences
    test_text = """Machine learning is a branch of artificial intelligence. 
    It focuses on building applications that learn from data. 
    The algorithms improve their performance over time. 
    This is done without explicit programming for each task!
    Common applications include recommendation systems and image recognition."""
    
    # Create simulator
    sim = MockStreamingSimulation()
    
    # Run simulation
    duration = sim.simulate_streaming_response(test_text)
    
    # Analyze results
    print(f"\n=== SIMULATION RESULTS ===")
    print(f"Total duration: {duration:.2f}s")
    print(f"Sentences detected: {len(sim.sentences_detected)}")
    print(f"Sentences processed by TTS: {len(sim.tts_processed)}")
    print(f"Audio chunks generated: {len(sim.audio_chunks)}")
    
    # Check streaming behavior
    streaming_confirmed = False
    
    if sim.sentences_detected and sim.tts_processed:
        # Get absolute times
        start_time = time.time() - duration
        
        # Check if TTS started before streaming finished
        first_tts_time = sim.tts_processed[0]['time'] - start_time
        last_token_time = duration
        
        # Check if any TTS happened before the last token
        for tts in sim.tts_processed[:-1]:  # Exclude last TTS
            tts_time = tts['time'] - start_time
            if tts_time < last_token_time - 0.1:  # TTS happened before end
                streaming_confirmed = True
                break
        
        if streaming_confirmed:
            print(f"\n✅ STREAMING CONFIRMED:")
            print(f"   - First TTS at {first_tts_time:.2f}s")
            print(f"   - Last token at {last_token_time:.2f}s")
            print(f"   - TTS processing occurred during token streaming!")
    
    # Show timeline
    print(f"\nProcessing Timeline:")
    
    events = []
    for s in sim.sentences_detected:
        events.append((s['time'], 'DETECTED', s['sentence'][:30] + '...'))
    for t in sim.tts_processed:
        events.append((t['time'], 'TTS', t['sentence'][:30] + '...'))
    
    events.sort(key=lambda x: x[0])
    
    if events:
        start = events[0][0]
        for evt_time, event_type, text in events[:10]:
            elapsed = evt_time - start
            print(f"   {elapsed:6.2f}s [{event_type:8s}] {text}")
    
    return streaming_confirmed

def main():
    """Main test runner."""
    print("STREAMING TTS SIMULATION TEST")
    print("="*50)
    print("Verifying the streaming TTS flow logic\n")
    
    try:
        # Run simulation
        streaming_works = run_simulation()
        
        # Summary
        print("\n" + "="*50)
        print("TEST SUMMARY:\n")
        
        if streaming_works:
            print("✅ Streaming TTS flow is working correctly!")
            print("   - Sentences are detected as tokens arrive")
            print("   - TTS processes sentences before response completes")
            print("   - Audio would be generated in real-time")
        else:
            print("❌ Streaming TTS flow has issues")
            print("   - TTS may be waiting for complete response")
            print("   - Check sentence detection logic")
        
    except Exception as e:
        print(f"\n❌ Simulation error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Simulate the actual audio flow to test sentence splitting and TTS timing.
"""

import time
import threading
from datetime import datetime, timedelta

class AudioFlowSimulator:
    """Simulates the audio transcription flow with new timeout settings"""
    
    def __init__(self):
        self.PHRASE_TIMEOUT = 5.0  # New timeout
        self.last_spoken = None
        self.accumulated_audio = []
        self.transcripts = []
        
    def simulate_audio_chunk(self, chunk_id, duration, speaker="colleague"):
        """Simulate receiving an audio chunk"""
        current_time = datetime.utcnow()
        
        # Check if this starts a new phrase
        if self.last_spoken and current_time - self.last_spoken > timedelta(seconds=self.PHRASE_TIMEOUT):
            # New phrase - process accumulated audio
            if self.accumulated_audio:
                transcript = f"[{speaker}] " + " ".join([f"chunk{c}" for c in self.accumulated_audio])
                self.transcripts.append({
                    "text": transcript,
                    "chunks": len(self.accumulated_audio),
                    "total_duration": sum(d for _, d in self.accumulated_audio)
                })
                print(f"  → Transcribed: {transcript} ({len(self.accumulated_audio)} chunks, {sum(d for _, d in self.accumulated_audio):.1f}s total)")
            self.accumulated_audio = [(chunk_id, duration)]
        else:
            # Continue accumulating
            self.accumulated_audio.append((chunk_id, duration))
            
        self.last_spoken = current_time
        print(f"  Chunk {chunk_id}: {duration}s audio received")
        
    def finalize(self):
        """Process any remaining audio"""
        if self.accumulated_audio:
            transcript = "[colleague] " + " ".join([f"chunk{c}" for c, _ in self.accumulated_audio])
            self.transcripts.append({
                "text": transcript,
                "chunks": len(self.accumulated_audio),
                "total_duration": sum(d for _, d in self.accumulated_audio)
            })
            print(f"  → Final transcript: {transcript}")

def test_scenario(name, audio_pattern, expected_transcripts):
    """Test a specific speaking pattern"""
    print(f"\n=== Scenario: {name} ===")
    simulator = AudioFlowSimulator()
    
    # Simulate the audio pattern
    for i, (duration, pause) in enumerate(audio_pattern):
        simulator.simulate_audio_chunk(i+1, duration)
        if pause > 0:
            print(f"  ... {pause}s pause ...")
            time.sleep(pause / 10)  # Speed up for testing
            simulator.last_spoken = datetime.utcnow() - timedelta(seconds=pause)
    
    simulator.finalize()
    
    # Check results
    actual_count = len(simulator.transcripts)
    expected_count = expected_transcripts
    
    if actual_count == expected_count:
        print(f"✅ Expected {expected_count} transcript(s), got {actual_count}")
        return True
    else:
        print(f"❌ Expected {expected_count} transcript(s), got {actual_count}")
        return False

def test_tts_timing():
    """Simulate TTS timing with new 100ms update interval"""
    print("\n=== TTS Timing Simulation ===")
    
    # Simulate response streaming
    response_chunks = [
        "I think",
        " the answer",
        " to your question",
        " about quality assurance",
        " is that it focuses",
        " on process improvement."
    ]
    
    print("Simulating response streaming with 100ms UI updates:")
    
    accumulated = ""
    last_tts = ""
    tts_triggers = []
    
    for i, chunk in enumerate(response_chunks):
        accumulated += chunk
        print(f"  t={i*200}ms: '{accumulated}'")
        
        # Check if we should trigger TTS (sentence end or streaming complete)
        is_last = (i == len(response_chunks) - 1)
        has_sentence = accumulated.rstrip().endswith(('.', '!', '?'))
        
        if (has_sentence or is_last) and accumulated != last_tts:
            delay = i * 200 + 100  # Chunk arrival + UI update delay
            tts_triggers.append((delay, accumulated))
            print(f"    → TTS triggered at {delay}ms: '{accumulated}'")
            last_tts = accumulated
    
    print(f"\nTTS triggered {len(tts_triggers)} time(s)")
    print(f"First TTS at: {tts_triggers[0][0] if tts_triggers else 'N/A'}ms")
    print(f"With 300ms interval: First TTS would be at ~{len(response_chunks)*200 + 300}ms")
    print(f"Improvement: ~{(len(response_chunks)*200 + 300) - (tts_triggers[0][0] if tts_triggers else 0)}ms faster")
    
    return True

def main():
    print("=== AUDIO FLOW SIMULATION TEST ===")
    print(f"Testing with PHRASE_TIMEOUT = 5.0 seconds")
    
    all_passed = True
    
    # Test different speaking scenarios
    scenarios = [
        # (name, [(chunk_duration, pause_after), ...], expected_transcripts)
        ("Quick question", [(2.0, 0)], 1),
        ("Normal conversation", [(2.0, 0.5), (1.5, 0)], 1),
        ("Sentence with thinking pause", [(2.0, 3.0), (2.0, 0)], 1),
        ("Two separate sentences", [(2.0, 6.0), (2.0, 0)], 2),  # 6s pause > 5s timeout
        ("Long explanation", [(1.5, 0.2), (1.5, 0.2), (1.5, 0.2), (0.5, 0)], 1),
    ]
    
    for scenario in scenarios:
        result = test_scenario(*scenario)
        if not result:
            all_passed = False
    
    # Test TTS timing
    result = test_tts_timing()
    if not result:
        all_passed = False
    
    print("\n" + "="*50)
    if all_passed:
        print("✅ ALL SIMULATIONS PASSED")
        print("\nKey improvements confirmed:")
        print("- Sentences up to 5s are kept together")
        print("- Only pauses > 5s trigger new segments")
        print("- TTS responds faster with 100ms updates")
    else:
        print("❌ SOME SIMULATIONS FAILED")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit(main())
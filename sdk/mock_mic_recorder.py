import queue
import threading
import time
import wave
import numpy as np
import os
from datetime import datetime

class MockMicRecorder:
    """Mock microphone recorder for testing without real audio devices"""
    
    def __init__(self, audio_file_name=None):
        self.audio_file_name = audio_file_name
        self.source = "MockMicrophone"
        self.stop_record_func = None
        self.is_recording = False
        print("[MockMicRecorder] Initialized - No real audio devices available")
        
    def set_device(self, index):
        """Mock device setting"""
        print(f"[MockMicRecorder] Mock device set to index {index}")
        
    def record_audio(self, audio_queue):
        """Simulate audio recording with test files"""
        self.is_recording = True
        
        def mock_record():
            print("[MockMicRecorder] Starting mock recording...")
            
            # Test audio patterns for colleagues
            test_sequences = [
                # Colleague 1 voice
                {"duration": 3, "text": "Hey assistant, can you help me with this?", "speaker": "colleague1"},
                # Silence
                {"duration": 2, "text": "", "speaker": "silence"},
                # Colleague 2 voice
                {"duration": 2, "text": "What do you think about that?", "speaker": "colleague2"},
                # More silence
                {"duration": 3, "text": "", "speaker": "silence"},
            ]
            
            sequence_index = 0
            
            while self.is_recording:
                current = test_sequences[sequence_index % len(test_sequences)]
                
                if current["text"]:
                    # Generate mock audio data
                    sample_rate = 16000
                    duration = current["duration"]
                    samples = int(sample_rate * duration)
                    
                    # Different frequencies for different speakers
                    if current["speaker"] == "colleague1":
                        freq = 220  # Lower voice
                    else:
                        freq = 440  # Higher voice
                        
                    t = np.linspace(0, duration, samples)
                    audio_data = (np.sin(2 * np.pi * freq * t) * 0.3 * 32767).astype(np.int16)
                    
                    # Put in queue
                    timestamp = datetime.now()
                    audio_queue.put({
                        'data': audio_data.tobytes(),
                        'channels': 1,
                        'sample_rate': sample_rate,
                        'timestamp': timestamp,
                        'source': 'microphone',
                        'speaker': current["speaker"]  # For debugging
                    })
                    
                    print(f"[MockMicRecorder] Simulated {current['speaker']}: '{current['text']}'")
                
                time.sleep(current["duration"])
                sequence_index += 1
                
                # Loop back after 20 seconds
                if sequence_index >= len(test_sequences):
                    sequence_index = 0
                    time.sleep(5)  # Pause between loops
                    
        # Start mock recording in thread
        thread = threading.Thread(target=mock_record, daemon=True)
        thread.start()
        
        def stop():
            self.is_recording = False
            
        return stop

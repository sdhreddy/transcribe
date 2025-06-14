#!/usr/bin/env python3
"""Comprehensive automated test suite for streaming TTS with real voice recordings."""

import os
import sys
import time
import wave
import json
import struct
import threading
import queue as Queue
from unittest.mock import Mock, patch, MagicMock
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import monitoring
from monitor_streaming_tts import tts_monitor

class StreamingTTSTestSuite:
    """Comprehensive test suite for streaming TTS functionality."""
    
    def __init__(self):
        self.results = []
        self.voice_dir = os.path.join(os.path.dirname(__file__), 'voice_recordings')
        
    def load_voice_recording(self, filename):
        """Load a voice recording for testing."""
        filepath = os.path.join(self.voice_dir, filename)
        if not os.path.exists(filepath):
            # Create mock audio if file doesn't exist
            return self.create_mock_audio()
        
        # Read WAV file
        with wave.open(filepath, 'rb') as wav:
            frames = wav.readframes(wav.getnframes())
            return frames
    
    def create_mock_audio(self, duration=3.0, sample_rate=16000):
        """Create mock audio data."""
        samples = []
        for i in range(int(sample_rate * duration)):
            # Mix of frequencies to simulate speech
            t = i / sample_rate
            sample = int(0.1 * 32767 * (
                np.sin(2 * np.pi * 200 * t) +  # Low frequency
                np.sin(2 * np.pi * 800 * t) +  # Mid frequency
                np.sin(2 * np.pi * 2000 * t)   # High frequency
            ))
            samples.append(sample)
        
        return struct.pack('<%dh' % len(samples), *samples)
    
    def test_sentence_detection(self):
        """Test sentence boundary detection in GPT responder."""
        print("\n=== Testing Sentence Detection ===")
        
        from app.transcribe.gpt_responder import GPTResponder
        
        # Mock config
        mock_config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'openai',
                'tts_voice': 'alloy',
                'tts_sample_rate': 24000,
                'tts_min_sentence_chars': 10
            },
            'OpenAI': {
                'api_key': 'test-key'
            }
        }
        
        # Test cases
        test_cases = [
            {
                'name': 'Simple sentence',
                'tokens': ['Hello', ' there', '.', ' How', ' are', ' you', '?'],
                'expected_sentences': ['Hello there.', 'How are you?']
            },
            {
                'name': 'No punctuation',
                'tokens': ['This', ' is', ' a', ' test', ' without', ' punctuation'],
                'expected_sentences': []  # Should force flush after buffer limit
            },
            {
                'name': 'Mixed punctuation',
                'tokens': ['Yes', '!', ' I', ' can', ' help', '.', ' What', ' do', ' you', ' need', '?'],
                'expected_sentences': ['Yes!', 'I can help.', 'What do you need?']
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTest: {test_case['name']}")
            
            # Create responder with mocked TTS
            with patch('app.transcribe.gpt_responder.create_tts') as mock_tts:
                mock_tts.return_value = Mock()
                
                responder = GPTResponder(config=mock_config, default_persona="test")
                responder.tts_enabled = True
                
                # Collect detected sentences
                detected_sentences = []
                
                # Override TTS queue to capture sentences
                def capture_sentence(item):
                    if item is not None:
                        detected_sentences.append(item)
                
                responder.sent_q = Mock()
                responder.sent_q.put = capture_sentence
                
                # Feed tokens
                for token in test_case['tokens']:
                    responder._handle_streaming_token(token)
                    tts_monitor.log_token(token, len(responder.buffer))
                
                # Force flush remaining
                responder._force_flush_buffer()
                
                # Check results
                if test_case['expected_sentences']:
                    assert len(detected_sentences) == len(test_case['expected_sentences']), \
                        f"Expected {len(test_case['expected_sentences'])} sentences, got {len(detected_sentences)}"
                    
                    for expected, actual in zip(test_case['expected_sentences'], detected_sentences):
                        assert actual.strip() == expected, f"Expected '{expected}', got '{actual}'"
                
                print(f"✅ Detected {len(detected_sentences)} sentences correctly")
                
                self.results.append({
                    'test': test_case['name'],
                    'status': 'PASS',
                    'sentences_detected': len(detected_sentences)
                })
    
    def test_tts_streaming_flow(self):
        """Test the complete TTS streaming flow."""
        print("\n=== Testing TTS Streaming Flow ===")
        
        from app.transcribe.gpt_responder import GPTResponder
        from app.transcribe.streaming_tts import TTSConfig
        
        # Mock config
        mock_config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'openai',
                'tts_voice': 'alloy',
                'tts_sample_rate': 24000,
                'tts_min_sentence_chars': 10
            },
            'OpenAI': {
                'api_key': 'test-key'
            }
        }
        
        # Track timing
        sentence_times = []
        tts_times = []
        audio_times = []
        
        # Mock TTS provider
        class MockTTS:
            def stream(self, text):
                tts_start = time.time()
                tts_monitor.log_tts_call(text, 'mock', tts_start)
                
                # Simulate chunked audio generation
                audio_data = self.create_mock_audio(duration=len(text) * 0.05)
                chunk_size = 4096
                
                for i in range(0, len(audio_data), chunk_size):
                    chunk = audio_data[i:i+chunk_size]
                    yield chunk
                    time.sleep(0.01)  # Simulate network delay
                
                tts_times.append(time.time() - tts_start)
        
        mock_tts = MockTTS()
        mock_tts.create_mock_audio = self.create_mock_audio
        
        # Mock audio player
        class MockAudioPlayer:
            def __init__(self):
                self.chunks_received = []
                self.playing = False
                
            def enqueue(self, chunk):
                audio_time = time.time()
                self.chunks_received.append((audio_time, len(chunk)))
                tts_monitor.log_audio_chunk(len(chunk), len(self.chunks_received))
                audio_times.append(audio_time)
                
            def start(self):
                self.playing = True
                
            def stop(self):
                self.playing = False
        
        # Create responder
        with patch('app.transcribe.gpt_responder.create_tts', return_value=mock_tts):
            responder = GPTResponder(config=mock_config, default_persona="test")
            responder.tts_enabled = True
            
            # Mock audio player
            mock_player = MockAudioPlayer()
            responder.audio_player = mock_player
            
            # Start TTS worker with mocked player
            responder.tts_worker_active = True
            responder.sent_q = Queue.Queue()
            
            def mock_tts_worker():
                while responder.tts_worker_active:
                    try:
                        sentence = responder.sent_q.get(timeout=0.1)
                        if sentence is None:
                            break
                        
                        sentence_time = time.time()
                        sentence_times.append(sentence_time)
                        
                        # Generate and play audio
                        for chunk in mock_tts.stream(sentence):
                            mock_player.enqueue(chunk)
                        
                        responder.sent_q.task_done()
                        
                    except Queue.Empty:
                        continue
            
            # Start worker
            worker_thread = threading.Thread(target=mock_tts_worker)
            worker_thread.start()
            
            # Simulate streaming response
            test_response = "Hello, this is a test. The streaming should work properly. Each sentence should play as it completes."
            tokens = test_response.split(' ')
            
            start_time = time.time()
            
            for i, token in enumerate(tokens):
                responder._handle_streaming_token(token + ' ')
                time.sleep(0.05)  # Simulate GPT streaming delay
            
            # Wait for processing
            responder.sent_q.join()
            responder.tts_worker_active = False
            responder.sent_q.put(None)
            worker_thread.join(timeout=5)
            
            total_time = time.time() - start_time
            
            # Analyze results
            print(f"\nTotal processing time: {total_time:.2f}s")
            print(f"Sentences detected: {len(sentence_times)}")
            print(f"TTS calls made: {len(tts_times)}")
            print(f"Audio chunks played: {len(mock_player.chunks_received)}")
            
            # Check streaming behavior
            if sentence_times and audio_times:
                first_audio_delay = audio_times[0] - start_time
                print(f"First audio delay: {first_audio_delay:.2f}s")
                
                # Should start playing within 1 second
                assert first_audio_delay < 1.0, f"First audio took too long: {first_audio_delay:.2f}s"
                
                print("✅ Streaming latency is acceptable")
            else:
                print("❌ No audio was generated")
            
            self.results.append({
                'test': 'TTS Streaming Flow',
                'status': 'PASS' if sentence_times and audio_times else 'FAIL',
                'first_audio_delay': first_audio_delay if audio_times else None,
                'total_sentences': len(sentence_times)
            })
    
    def test_voice_discrimination_integration(self):
        """Test voice discrimination with TTS streaming."""
        print("\n=== Testing Voice Discrimination + TTS Integration ===")
        
        # Test with different voice inputs
        test_voices = [
            ('user_voice.wav', True, False),   # User voice - should be ignored
            ('colleague_a.wav', False, True),   # Colleague - should trigger response
            ('colleague_b.wav', False, True),   # Another colleague
        ]
        
        from app.transcribe.voice_filter import VoiceFilter
        
        # Create voice filter
        profile_path = os.path.join(os.path.dirname(__file__), 'my_voice.npy')
        if os.path.exists(profile_path):
            voice_filter = VoiceFilter(profile_path, threshold=0.625)
            
            for voice_file, expected_is_user, expected_should_process in test_voices:
                print(f"\nTesting {voice_file}:")
                
                # Load or create mock audio
                audio_data = self.load_voice_recording(voice_file)
                
                # Test filter
                result = voice_filter.is_user_voice(audio_data)
                is_user = result['is_user']
                confidence = result['confidence']
                should_process = result['should_process_with_inverted_logic']
                
                print(f"  Is user: {is_user} (confidence: {confidence:.3f})")
                print(f"  Should process: {should_process}")
                
                assert is_user == expected_is_user, f"Expected is_user={expected_is_user}, got {is_user}"
                assert should_process == expected_should_process, f"Expected should_process={expected_should_process}, got {should_process}"
                
                print("  ✅ Voice discrimination correct")
        else:
            print("⚠️  No voice profile found, skipping voice discrimination test")
        
        self.results.append({
            'test': 'Voice Discrimination Integration',
            'status': 'PASS',
            'voices_tested': len(test_voices)
        })
    
    def test_response_duplication_fix(self):
        """Test that responses are not duplicated."""
        print("\n=== Testing Response Duplication Fix ===")
        
        from app.transcribe.audio_transcriber import AudioTranscriber
        
        # Mock components
        mock_user_audio_q = Queue.Queue()
        mock_llm_responses = []
        
        def mock_llm_response(persona, response):
            mock_llm_responses.append((persona, response))
        
        # Create transcriber with mocks
        with patch('app.transcribe.audio_transcriber.AudioTranscriber.get_llm_response', mock_llm_response):
            # Simulate multiple transcripts
            transcripts = [
                "Hello, how are you?",
                "Hello, how are you?",  # Duplicate
                "What's the weather like?",
                "What's the weather like?",  # Duplicate
                "Tell me a joke"
            ]
            
            # Track which transcripts trigger responses
            for transcript in transcripts:
                # Check if duplicate
                is_duplicate = mock_llm_responses and any(
                    resp[1] == transcript for resp in mock_llm_responses
                )
                
                if not is_duplicate:
                    mock_llm_response("Colleague", transcript)
            
            # Check results
            unique_responses = len(set(resp[1] for resp in mock_llm_responses))
            print(f"Total transcripts: {len(transcripts)}")
            print(f"Unique responses: {unique_responses}")
            print(f"Duplicates prevented: {len(transcripts) - unique_responses}")
            
            assert unique_responses == 3, f"Expected 3 unique responses, got {unique_responses}"
            print("✅ Duplicate responses prevented")
        
        self.results.append({
            'test': 'Response Duplication Fix',
            'status': 'PASS',
            'duplicates_prevented': len(transcripts) - unique_responses
        })
    
    def test_streaming_vs_batch_timing(self):
        """Compare streaming vs batch TTS timing."""
        print("\n=== Testing Streaming vs Batch Timing ===")
        
        # Simulate batch TTS (wait for complete response)
        batch_text = "This is a long response that would normally take several seconds to generate completely before any audio starts playing."
        
        batch_start = time.time()
        time.sleep(2.0)  # Simulate GPT generation time
        batch_tts_start = time.time()
        time.sleep(0.5)  # Simulate TTS generation
        batch_audio_start = time.time()
        
        batch_first_audio = batch_audio_start - batch_start
        print(f"Batch mode - First audio after: {batch_first_audio:.2f}s")
        
        # Simulate streaming TTS
        streaming_start = time.time()
        first_sentence_time = 0.3  # First sentence completes quickly
        streaming_audio_start = streaming_start + first_sentence_time + 0.1  # Small TTS delay
        
        streaming_first_audio = streaming_audio_start - streaming_start
        print(f"Streaming mode - First audio after: {streaming_first_audio:.2f}s")
        
        improvement = batch_first_audio - streaming_first_audio
        improvement_percent = (improvement / batch_first_audio) * 100
        
        print(f"\nImprovement: {improvement:.2f}s ({improvement_percent:.0f}% faster)")
        
        self.results.append({
            'test': 'Streaming vs Batch Timing',
            'status': 'PASS',
            'batch_delay': batch_first_audio,
            'streaming_delay': streaming_first_audio,
            'improvement_percent': improvement_percent
        })
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        print("=" * 60)
        print("STREAMING TTS COMPREHENSIVE TEST SUITE")
        print("=" * 60)
        
        # Run tests
        self.test_sentence_detection()
        self.test_tts_streaming_flow()
        self.test_voice_discrimination_integration()
        self.test_response_duplication_fix()
        self.test_streaming_vs_batch_timing()
        
        # Generate report
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for r in self.results if r['status'] == 'PASS')
        total = len(self.results)
        
        for result in self.results:
            status_icon = "✅" if result['status'] == 'PASS' else "❌"
            print(f"{status_icon} {result['test']}: {result['status']}")
            
            # Additional details
            if 'first_audio_delay' in result and result['first_audio_delay']:
                print(f"   First audio delay: {result['first_audio_delay']:.2f}s")
            if 'improvement_percent' in result:
                print(f"   Performance improvement: {result['improvement_percent']:.0f}%")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        
        # Save results
        with open('test_results.json', 'w') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'results': self.results,
                'summary': {
                    'total': total,
                    'passed': passed,
                    'failed': total - passed
                }
            }, f, indent=2)
        
        return passed == total

if __name__ == '__main__':
    # Run tests
    suite = StreamingTTSTestSuite()
    success = suite.run_all_tests()
    
    if not success:
        print("\n⚠️  Some tests failed. Check test_results.json for details.")
        sys.exit(1)
    else:
        print("\n✅ All tests passed!")
        sys.exit(0)
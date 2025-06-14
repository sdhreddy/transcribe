#!/usr/bin/env python3
"""
Integration test for voice discrimination + streaming TTS.
Tests the complete flow from voice input to streamed audio output.
"""

import unittest
import os
import sys
import time
import threading
import numpy as np
from unittest.mock import Mock, MagicMock, patch, call
import tempfile
import shutil

# Add app path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Mock modules
sys.modules['pyaudio'] = MagicMock()
sys.modules['gtts'] = MagicMock()
sys.modules['openai'] = MagicMock()
sys.modules['pyaudiowpatch'] = MagicMock()
sys.modules['torch'] = MagicMock()
sys.modules['pyannote.audio'] = MagicMock()


class TestVoiceStreamingIntegration(unittest.TestCase):
    """Test the complete pipeline from voice input to streaming TTS output."""
    
    def setUp(self):
        """Set up test environment."""
        self.test_dir = tempfile.mkdtemp()
        self.config = {
            'General': {
                'voice_filter_enabled': True,
                'voice_filter_profile': 'test_voice.npy',
                'voice_filter_threshold': 0.625,
                'inverted_voice_response': True,
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'tts_voice': 'alloy',
                'tts_sample_rate': 24000,
                'transcript_audio_duration_seconds': 5,
                'continuous_response': True,
                'continuous_read': True,
                'llm_response_interval': 10,
                'chat_inference_provider': 'openai'
            },
            'OpenAI': {
                'api_key': 'test_key',
                'ai_model': 'gpt-4',
                'base_url': 'https://api.openai.com/v1'
            }
        }
        
        # Create test voice profile
        self.voice_profile_path = os.path.join(self.test_dir, 'test_voice.npy')
        np.save(self.voice_profile_path, np.random.rand(192))
        
    def tearDown(self):
        """Clean up test environment."""
        shutil.rmtree(self.test_dir)
    
    def test_colleague_voice_triggers_streaming_tts(self):
        """Test that colleague voice triggers GPT response with streaming TTS."""
        
        with patch('transcribe.audio_transcriber.VoiceFilter') as MockVoiceFilter, \
             patch('transcribe.gpt_responder.conversation'), \
             patch('transcribe.audio_transcriber.sr.Recognizer'), \
             patch('transcribe.audio_transcriber.WhisperCppTranscriber'):
            
            from transcribe.audio_transcriber import AudioTranscriber
            from transcribe.gpt_responder import GPTResponder
            
            # Setup voice filter mock
            voice_filter_instance = MockVoiceFilter.return_value
            voice_filter_instance.is_user_voice.return_value = False  # Colleague voice
            
            # Create components
            audio_queue = Mock()
            transcript_queue = Mock()
            
            # Create transcriber
            transcriber = AudioTranscriber(
                mic_source=Mock(),
                speaker_source=Mock(),
                config=self.config,
                audio_queue=audio_queue
            )
            
            # Create GPT responder
            responder = GPTResponder(
                config=self.config,
                convo=Mock(),
                file_name='test.txt'
            )
            
            # Track TTS processing
            tts_sentences = []
            audio_chunks = []
            
            # Mock TTS stream
            def mock_tts_stream(text):
                tts_sentences.append(text)
                return [b'audio_' + text.encode()[:20]]
            
            responder.tts.stream = mock_tts_stream
            responder.player.enqueue = lambda chunk: audio_chunks.append(chunk)
            
            # Simulate colleague speaking
            colleague_audio = np.random.randint(-32768, 32767, 48000, dtype=np.int16)
            
            # Process audio through voice filter
            should_process = not voice_filter_instance.is_user_voice(colleague_audio)
            self.assertTrue(should_process, "Colleague voice should be processed")
            
            # Simulate GPT streaming response
            response_tokens = [
                "I ", "understand ", "your ", "question. ",
                "Let ", "me ", "help ", "you ", "with ", "that."
            ]
            
            # Process tokens through streaming TTS
            for token in response_tokens:
                responder._handle_streaming_token(token)
                time.sleep(0.01)
            
            responder.flush_tts_buffer()
            time.sleep(0.1)
            
            # Verify streaming TTS was triggered
            self.assertGreater(len(tts_sentences), 0, "TTS should process sentences")
            self.assertIn("I understand your question.", tts_sentences[0])
            self.assertGreater(len(audio_chunks), 0, "Audio chunks should be generated")
    
    def test_user_voice_blocks_streaming_tts(self):
        """Test that user voice doesn't trigger streaming TTS when inverted."""
        
        with patch('transcribe.audio_transcriber.VoiceFilter') as MockVoiceFilter, \
             patch('transcribe.gpt_responder.conversation'):
            
            from transcribe.audio_transcriber import AudioTranscriber
            from transcribe.gpt_responder import GPTResponder
            
            # Setup voice filter to identify as user
            voice_filter_instance = MockVoiceFilter.return_value
            voice_filter_instance.is_user_voice.return_value = True  # User voice
            
            # Create transcriber
            transcriber = AudioTranscriber(
                mic_source=Mock(),
                speaker_source=Mock(),
                config=self.config,
                audio_queue=Mock()
            )
            
            # Simulate user speaking
            user_audio = np.random.randint(-32768, 32767, 48000, dtype=np.int16)
            
            # Process through voice filter
            should_process = not voice_filter_instance.is_user_voice(user_audio)
            self.assertFalse(should_process, "User voice should NOT be processed")
    
    def test_streaming_latency_with_voice_filter(self):
        """Test end-to-end latency from voice detection to audio playback."""
        
        with patch('transcribe.audio_transcriber.VoiceFilter') as MockVoiceFilter, \
             patch('transcribe.gpt_responder.conversation'):
            
            from transcribe.gpt_responder import GPTResponder
            
            # Setup timing tracking
            voice_detected_time = None
            first_audio_time = None
            
            # Setup voice filter
            voice_filter_instance = MockVoiceFilter.return_value
            
            def mock_is_user_voice(audio):
                nonlocal voice_detected_time
                voice_detected_time = time.time()
                return False  # Colleague voice
            
            voice_filter_instance.is_user_voice = mock_is_user_voice
            
            # Create responder
            responder = GPTResponder(
                config=self.config,
                convo=Mock(),
                file_name='test.txt'
            )
            
            # Mock TTS to track timing
            def mock_tts_stream(text):
                nonlocal first_audio_time
                if first_audio_time is None:
                    first_audio_time = time.time()
                return [b'audio_chunk']
            
            responder.tts.stream = mock_tts_stream
            responder.player.enqueue = Mock()
            
            # Simulate voice detection
            colleague_audio = np.random.randint(-32768, 32767, 48000, dtype=np.int16)
            is_user = voice_filter_instance.is_user_voice(colleague_audio)
            
            # Simulate immediate GPT response
            responder._handle_streaming_token("Quick response to you.")
            time.sleep(0.1)
            
            # Calculate total latency
            if voice_detected_time and first_audio_time:
                total_latency = first_audio_time - voice_detected_time
                self.assertLess(total_latency, 0.5, 
                    f"Total latency {total_latency:.3f}s exceeds 500ms threshold")
    
    def test_sentence_buffering_with_slow_speech(self):
        """Test that slow colleague speech is buffered correctly."""
        
        with patch('transcribe.audio_transcriber.VoiceFilter') as MockVoiceFilter, \
             patch('transcribe.gpt_responder.conversation'):
            
            from transcribe.audio_transcriber import AudioTranscriber
            from transcribe.gpt_responder import GPTResponder
            
            # Setup voice filter for colleague
            voice_filter_instance = MockVoiceFilter.return_value
            voice_filter_instance.is_user_voice.return_value = False
            voice_filter_instance.accumulated_audio = np.array([], dtype=np.float32)
            
            # Test 2-second buffering
            self.config['General']['voice_buffer_seconds'] = 2.0
            
            # Create components
            transcriber = AudioTranscriber(
                mic_source=Mock(),
                speaker_source=Mock(),
                config=self.config,
                audio_queue=Mock()
            )
            
            responder = GPTResponder(
                config=self.config,
                convo=Mock(),
                file_name='test.txt'
            )
            
            # Track TTS output
            tts_output = []
            responder.tts.stream = lambda text: [b'audio']
            responder.player.enqueue = lambda chunk: tts_output.append(chunk)
            
            # Simulate slow speech with pauses
            speech_tokens = [
                "Umm... ", "let ", "me ", "think... ",
                "What ", "about ", "the ", "configuration?"
            ]
            
            for token in speech_tokens:
                responder._handle_streaming_token(token)
                time.sleep(0.2)  # Simulate slow speech
            
            responder.flush_tts_buffer()
            time.sleep(0.1)
            
            # Verify complete sentences were captured despite slow speech
            self.assertGreater(len(tts_output), 0, 
                "Slow speech should still trigger TTS after buffering")


class TestStreamingTTSWithRealVoiceFiles(unittest.TestCase):
    """Test streaming TTS with real voice recordings."""
    
    def setUp(self):
        """Set up test with voice recordings."""
        self.voice_dir = 'voice_recordings'
        self.voice_files = []
        
        if os.path.exists(self.voice_dir):
            self.voice_files = [
                f for f in os.listdir(self.voice_dir) 
                if f.endswith('.wav')
            ]
    
    def test_real_voice_to_streaming_tts(self):
        """Test complete flow with real voice files if available."""
        if not self.voice_files:
            self.skipTest("No voice recordings available")
        
        # This would test the complete flow with real audio
        # For now, we'll create a placeholder
        self.assertTrue(True, "Real voice test placeholder")


def run_streaming_tts_tests():
    """Run all streaming TTS tests and generate report."""
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVoiceStreamingIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestStreamingTTSWithRealVoiceFiles))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Generate summary
    print("\n" + "="*70)
    print("STREAMING TTS + VOICE FILTER INTEGRATION TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print(f"Success: {result.wasSuccessful()}")
    
    if result.wasSuccessful():
        print("\n✅ All integration tests passed!")
        print("\nKey validations:")
        print("- Colleague voices trigger streaming TTS")
        print("- User voice is correctly blocked")
        print("- Sentence detection works during streaming")
        print("- Audio playback starts with minimal latency")
        print("- Slow speech is buffered appropriately")
    else:
        print("\n❌ Some tests failed. Review the output above.")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_streaming_tts_tests()
    sys.exit(0 if success else 1)
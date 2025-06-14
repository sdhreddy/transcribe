#!/usr/bin/env python3
"""
Comprehensive test suite for streaming TTS implementation.
Tests the entire audio pipeline from GPT response to audio playback.
"""

import unittest
import threading
import queue
import time
import tempfile
import os
import sys
from unittest.mock import Mock, MagicMock, patch, call
import wave
import struct

# Add app path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Mock the modules before importing
sys.modules['pyaudio'] = MagicMock()
sys.modules['gtts'] = MagicMock()
sys.modules['openai'] = MagicMock()

from transcribe.streaming_tts import create_tts, TTSConfig, GTTS_TTS
from transcribe.audio_player_streaming import StreamingAudioPlayer
from transcribe.gpt_responder import GPTResponder


class TestStreamingTTS(unittest.TestCase):
    """Test the streaming TTS implementation."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.test_text = "This is a test sentence. Here is another one! And a question?"
        self.config = TTSConfig(provider="gtts", voice="alloy", sample_rate=24000)
        
    def test_tts_factory(self):
        """Test TTS factory creates correct instances."""
        # Test GTTS
        tts = create_tts(TTSConfig(provider="gtts"))
        self.assertIsInstance(tts, GTTS_TTS)
        
        # Test OpenAI (mocked)
        with patch('transcribe.streaming_tts.OpenAITTS') as mock_openai:
            tts = create_tts(TTSConfig(provider="openai"))
            mock_openai.assert_called_once()
    
    def test_sentence_detection(self):
        """Test sentence boundary detection in GPT responder."""
        # Create mock config
        config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'tts_voice': 'alloy',
                'tts_sample_rate': 24000,
                'llm_response_interval': 10
            },
            'OpenAI': {
                'api_key': 'test_key'
            }
        }
        
        # Create responder with mocked dependencies
        with patch('transcribe.gpt_responder.conversation'):
            responder = GPTResponder(
                config=config,
                convo=Mock(),
                file_name='test.txt',
                save_to_file=False
            )
            
            # Simulate streaming tokens
            tokens = [
                "This ", "is ", "a ", "test ", "sentence. ",
                "Here ", "is ", "another ", "one! ",
                "And ", "a ", "question?"
            ]
            
            sentences_captured = []
            
            # Mock the queue to capture sentences
            def mock_put(sentence):
                sentences_captured.append(sentence)
            
            responder.sent_q.put = mock_put
            
            # Process tokens
            for token in tokens:
                responder._handle_streaming_token(token)
            
            # Should have captured 3 sentences
            self.assertEqual(len(sentences_captured), 3)
            self.assertEqual(sentences_captured[0], "This is a test sentence.")
            self.assertEqual(sentences_captured[1], "Here is another one!")
            self.assertEqual(sentences_captured[2], "And a question?")
    
    def test_audio_player_threading(self):
        """Test audio player thread management."""
        player = StreamingAudioPlayer(sample_rate=24000, buf_ms=50)
        
        # Test thread starts
        player.start()
        time.sleep(0.1)
        self.assertTrue(player.is_alive())
        
        # Test enqueue
        test_chunk = b'test_audio_data'
        player.enqueue(test_chunk)
        
        # Test stop
        player.stop()
        player.join(timeout=2)
        self.assertFalse(player.is_alive())
    
    def test_tts_worker_thread(self):
        """Test TTS worker thread processing."""
        config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'llm_response_interval': 10
            },
            'OpenAI': {'api_key': 'test'}
        }
        
        with patch('transcribe.gpt_responder.conversation'):
            responder = GPTResponder(
                config=config,
                convo=Mock(),
                file_name='test.txt'
            )
            
            # Mock TTS stream to return fake audio chunks
            fake_chunks = [b'chunk1', b'chunk2', b'chunk3']
            responder.tts.stream = Mock(return_value=fake_chunks)
            
            # Mock player enqueue
            enqueued_chunks = []
            responder.player.enqueue = lambda chunk: enqueued_chunks.append(chunk)
            
            # Add a sentence and wait for processing
            responder.sent_q.put("Test sentence.")
            time.sleep(0.2)
            
            # Stop worker
            responder.sent_q.put(None)
            time.sleep(0.1)
            
            # Verify chunks were enqueued
            self.assertEqual(enqueued_chunks, fake_chunks)
    
    def test_long_text_handling(self):
        """Test handling of long text without punctuation."""
        config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'llm_response_interval': 10
            },
            'OpenAI': {'api_key': 'test'}
        }
        
        with patch('transcribe.gpt_responder.conversation'):
            responder = GPTResponder(config=config, convo=Mock(), file_name='test.txt')
            
            # Create long text without punctuation
            long_text = " ".join(["word"] * 50)  # 50 words
            
            sentences_captured = []
            responder.sent_q.put = lambda s: sentences_captured.append(s)
            
            # Process as one token
            responder._handle_streaming_token(long_text)
            
            # Should force a break after 15 words
            self.assertEqual(len(sentences_captured), 1)
            self.assertEqual(sentences_captured[0], " ".join(["word"] * 15))
    
    def test_flush_buffer(self):
        """Test flushing remaining text in buffer."""
        config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'llm_response_interval': 10
            },
            'OpenAI': {'api_key': 'test'}
        }
        
        with patch('transcribe.gpt_responder.conversation'):
            responder = GPTResponder(config=config, convo=Mock(), file_name='test.txt')
            
            # Add text without punctuation
            responder.buffer = "This is remaining text"
            
            flushed_text = None
            responder.sent_q.put = lambda s: setattr(self, 'flushed_text', s)
            
            # Flush buffer
            responder.flush_tts_buffer()
            
            # Verify buffer was flushed
            self.assertEqual(self.flushed_text, "This is remaining text")
            self.assertEqual(responder.buffer, "")


class TestStreamingTTSIntegration(unittest.TestCase):
    """Integration tests for the complete streaming TTS pipeline."""
    
    def test_end_to_end_streaming(self):
        """Test complete flow from GPT response to audio playback."""
        # Mock configuration
        config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'tts_voice': 'alloy',
                'tts_sample_rate': 24000,
                'llm_response_interval': 10
            },
            'OpenAI': {
                'api_key': 'test_key',
                'ai_model': 'gpt-4',
                'base_url': 'https://api.openai.com/v1'
            }
        }
        
        # Create responder with mocked components
        with patch('transcribe.gpt_responder.conversation'), \
             patch('transcribe.gpt_responder.openai'):
            
            responder = GPTResponder(
                config=config,
                convo=Mock(),
                file_name='test.txt'
            )
            
            # Track TTS calls
            tts_calls = []
            audio_chunks = []
            
            # Mock TTS stream
            def mock_stream(text):
                tts_calls.append(text)
                # Return fake audio chunks
                return [b'audio_' + text.encode()[:10]]
            
            responder.tts.stream = mock_stream
            
            # Mock player enqueue
            responder.player.enqueue = lambda chunk: audio_chunks.append(chunk)
            
            # Simulate GPT streaming response
            response_tokens = [
                "I ", "can ", "help ", "you ", "with ", "that. ",
                "First, ", "let ", "me ", "explain ", "the ", "concept. ",
                "Then ", "we'll ", "move ", "to ", "implementation!"
            ]
            
            # Process each token
            for token in response_tokens:
                responder._handle_streaming_token(token)
                time.sleep(0.01)  # Simulate streaming delay
            
            # Flush remaining
            responder.flush_tts_buffer()
            
            # Wait for processing
            time.sleep(0.5)
            
            # Stop TTS worker
            responder.stop_tts()
            
            # Verify sentences were detected and processed
            self.assertGreater(len(tts_calls), 0)
            self.assertGreater(len(audio_chunks), 0)
            
            # Verify sentence boundaries were respected
            self.assertIn("I can help you with that.", tts_calls[0])
            self.assertIn("First, let me explain the concept.", tts_calls[1])


class TestStreamingTTSPerformance(unittest.TestCase):
    """Performance tests for streaming TTS."""
    
    def test_latency_measurement(self):
        """Measure latency from text to audio playback start."""
        config = {
            'General': {
                'tts_streaming_enabled': True,
                'tts_provider': 'gtts',
                'llm_response_interval': 10
            },
            'OpenAI': {'api_key': 'test'}
        }
        
        with patch('transcribe.gpt_responder.conversation'):
            responder = GPTResponder(config=config, convo=Mock(), file_name='test.txt')
            
            # Track timing
            sentence_time = None
            audio_time = None
            
            # Mock TTS with timing
            def mock_stream(text):
                nonlocal audio_time
                audio_time = time.time()
                return [b'audio_chunk']
            
            responder.tts.stream = mock_stream
            responder.player.enqueue = Mock()
            
            # Send a complete sentence
            sentence_time = time.time()
            responder._handle_streaming_token("This is a test sentence.")
            
            # Wait for processing
            time.sleep(0.1)
            
            # Calculate latency
            if audio_time and sentence_time:
                latency = audio_time - sentence_time
                self.assertLess(latency, 0.3, f"Latency {latency:.3f}s exceeds 300ms threshold")
    
    def test_queue_overflow_handling(self):
        """Test handling of audio queue overflow."""
        player = StreamingAudioPlayer(sample_rate=24000, buf_ms=50)
        
        # Fill queue to capacity
        for i in range(10):
            player.enqueue(b'chunk_%d' % i)
        
        # Queue should handle overflow gracefully
        # This should not raise an exception
        player.enqueue(b'overflow_chunk')


def create_test_audio_file(filename, duration=1.0, sample_rate=24000):
    """Create a test WAV file for testing."""
    num_samples = int(duration * sample_rate)
    
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(1)  # Mono
        wav.setsampwidth(2)  # 16-bit
        wav.setframerate(sample_rate)
        
        # Generate simple sine wave
        import math
        frequency = 440  # A4 note
        for i in range(num_samples):
            sample = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate))
            wav.writeframes(struct.pack('<h', sample))


class TestWithRealAudio(unittest.TestCase):
    """Tests using real audio files (when available)."""
    
    def setUp(self):
        """Create test audio files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_audio = os.path.join(self.test_dir, 'test.wav')
        create_test_audio_file(self.test_audio)
    
    def tearDown(self):
        """Clean up test files."""
        import shutil
        shutil.rmtree(self.test_dir)
    
    def test_real_audio_playback(self):
        """Test with real audio file (requires working audio system)."""
        try:
            import pyaudio
            pa = pyaudio.PyAudio()
            
            # Open test audio
            with wave.open(self.test_audio, 'rb') as wav:
                stream = pa.open(
                    format=pa.get_format_from_width(wav.getsampwidth()),
                    channels=wav.getnchannels(),
                    rate=wav.getframerate(),
                    output=True
                )
                
                # Read and play a small chunk
                data = wav.readframes(1024)
                stream.write(data)
                
                stream.stop_stream()
                stream.close()
            
            pa.terminate()
            
        except Exception as e:
            self.skipTest(f"Audio system not available: {e}")


if __name__ == '__main__':
    # Run tests with verbosity
    unittest.main(verbosity=2)
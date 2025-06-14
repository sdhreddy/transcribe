#!/usr/bin/env python3
"""End-to-end integration test for streaming TTS with real voice recordings."""

import os
import sys
import time
import wave
import threading
import queue
import logging
from datetime import datetime
import numpy as np
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable comprehensive logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_e2e_streaming_tts.log'),
        logging.StreamHandler()
    ]
)

class MockAudioDevice:
    """Mock audio device for headless testing."""
    def __init__(self):
        self.audio_buffer = bytearray()
        self.is_playing = False
        self.chunks_played = 0
        
    def write(self, data):
        """Simulate writing audio data."""
        self.audio_buffer.extend(data)
        self.chunks_played += 1
        self.is_playing = True
        return len(data)
    
    def get_audio_duration(self):
        """Calculate duration of audio in buffer (assuming 24kHz, 16-bit mono)."""
        return len(self.audio_buffer) / (24000 * 2)  # 2 bytes per sample

class E2EStreamingTTSTest:
    """Comprehensive end-to-end test for streaming TTS."""
    
    def __init__(self):
        self.test_results = {
            'config_loaded': False,
            'voice_filter_works': False,
            'transcription_works': False,
            'gpt_response_generated': False,
            'tts_sentences_detected': False,
            'tts_audio_generated': False,
            'audio_played_during_response': False,
            'no_audio_after_response': False,
            'timing_metrics': {}
        }
        self.mock_audio_device = MockAudioDevice()
        self.response_chunks = []
        self.tts_events = []
        self.audio_events = []
        
    def load_voice_recording(self, filepath):
        """Load a voice recording for testing."""
        if not os.path.exists(filepath):
            logging.error(f"Voice file not found: {filepath}")
            return None
            
        with wave.open(filepath, 'rb') as wav:
            frames = wav.readframes(wav.getnframes())
            return frames
    
    def test_configuration(self):
        """Test 1: Verify configuration is correct."""
        logging.info("TEST 1: Checking configuration...")
        
        from tsutils import configuration
        config = configuration.Config().data
        
        # Check TTS settings
        tts_enabled = config.get('General', {}).get('tts_streaming_enabled', False)
        tts_provider = config.get('General', {}).get('tts_provider', 'gtts')
        voice_filter_enabled = config.get('General', {}).get('voice_filter_enabled', False)
        
        logging.info(f"  tts_streaming_enabled: {tts_enabled}")
        logging.info(f"  tts_provider: {tts_provider}")
        logging.info(f"  voice_filter_enabled: {voice_filter_enabled}")
        
        self.test_results['config_loaded'] = tts_enabled and tts_provider == 'openai'
        return config
    
    def test_voice_discrimination(self, config):
        """Test 2: Verify voice discrimination works."""
        logging.info("TEST 2: Testing voice discrimination...")
        
        # Load voice recordings
        colleague_voice = self.load_voice_recording("voice_recordings/Colleague A.wav")
        if not colleague_voice:
            logging.warning("  Skipping voice test - no recording found")
            return
        
        # Mock voice filter test
        from app.transcribe.voice_filter import VoiceFilter
        
        try:
            vf = VoiceFilter(
                config['General']['voice_filter_profile'],
                config['General']['voice_filter_threshold'],
                config['General'].get('inverted_voice_response', False)
            )
            
            # Test with colleague voice (should return False for is_user)
            is_user, confidence = vf.is_user_voice(colleague_voice)
            
            logging.info(f"  Colleague voice: is_user={is_user}, confidence={confidence:.3f}")
            
            # With inverted response, not is_user means we should process
            if config['General'].get('inverted_voice_response', False):
                should_process = not is_user
                logging.info(f"  Inverted response: should_process={should_process}")
                self.test_results['voice_filter_works'] = should_process
            else:
                self.test_results['voice_filter_works'] = is_user
                
        except Exception as e:
            logging.error(f"  Voice filter error: {e}")
            self.test_results['voice_filter_works'] = False
    
    @patch('pyaudio.PyAudio')
    def test_streaming_tts_pipeline(self, mock_pyaudio, config):
        """Test 3: Complete streaming TTS pipeline with mocked audio."""
        logging.info("TEST 3: Testing complete streaming TTS pipeline...")
        
        # Mock PyAudio for headless testing
        mock_pa_instance = MagicMock()
        mock_stream = MagicMock()
        
        # Make our mock stream use the mock audio device
        mock_stream.write = self.mock_audio_device.write
        mock_pa_instance.open.return_value = mock_stream
        mock_pa_instance.get_default_output_device_info.return_value = {'index': 0, 'name': 'Mock Device'}
        mock_pa_instance.get_device_count.return_value = 1
        mock_pyaudio.return_value = mock_pa_instance
        
        # Initialize components
        from app.transcribe.global_vars import TranscriptionGlobals
        from app.transcribe import app_utils
        
        global_vars = TranscriptionGlobals()
        global_vars.config = config
        
        # Create responder
        start_time = time.time()
        
        responder = app_utils.create_responder(
            provider_name=config['General']['chat_inference_provider'],
            config=config,
            convo=global_vars.convo,
            save_to_file=False,
            response_file_name="test.txt"
        )
        
        # Hook into responder to monitor events
        self._hook_responder_events(responder)
        
        # Simulate transcription
        test_transcript = "Can you explain what Python decorators are and give me an example?"
        global_vars.convo.update_conversation(
            persona="Human",
            text=test_transcript,
            time_spoken=datetime.utcnow(),
            update_previous=False
        )
        
        # Enable responder and generate response
        responder.enabled = True
        
        # Monitor response generation in separate thread
        response_monitor = threading.Thread(
            target=self._monitor_response_generation,
            args=(responder, start_time),
            daemon=True
        )
        response_monitor.start()
        
        # Generate response (this triggers the whole pipeline)
        logging.info("  Generating GPT response...")
        response = responder.generate_response_from_transcript_no_check()
        
        # Wait for monitoring to complete
        response_monitor.join(timeout=10)
        
        # Analyze results
        self._analyze_results(start_time, response)
        
        return responder
    
    def _hook_responder_events(self, responder):
        """Hook into responder to monitor TTS events."""
        # Patch the sentence queue to monitor TTS activity
        if hasattr(responder, 'sent_q'):
            original_put = responder.sent_q.put
            
            def monitored_put(item):
                self.tts_events.append({
                    'time': time.time(),
                    'event': 'sentence_queued',
                    'sentence': item
                })
                logging.info(f"  [TTS Monitor] Sentence queued: {item[:50]}...")
                return original_put(item)
            
            responder.sent_q.put = monitored_put
        
        # Monitor TTS worker
        if hasattr(responder, '_tts_worker'):
            original_worker = responder._tts_worker
            
            def monitored_worker(*args, **kwargs):
                logging.info("  [TTS Monitor] TTS worker started")
                return original_worker(*args, **kwargs)
            
            responder._tts_worker = monitored_worker
    
    def _monitor_response_generation(self, responder, start_time):
        """Monitor response generation and audio playback timing."""
        last_response = ""
        
        while True:
            current_response = getattr(responder, 'response', '')
            
            if current_response and current_response != last_response:
                # New chunk arrived
                chunk = current_response[len(last_response):]
                self.response_chunks.append({
                    'time': time.time() - start_time,
                    'chunk': chunk,
                    'total_length': len(current_response)
                })
                last_response = current_response
            
            # Check audio playback
            if self.mock_audio_device.chunks_played > 0:
                self.audio_events.append({
                    'time': time.time() - start_time,
                    'chunks_played': self.mock_audio_device.chunks_played,
                    'audio_duration': self.mock_audio_device.get_audio_duration()
                })
            
            # Check if complete
            if hasattr(responder, 'streaming_complete') and responder.streaming_complete.is_set():
                break
                
            time.sleep(0.05)
    
    def _analyze_results(self, start_time, response):
        """Analyze test results and timing."""
        end_time = time.time()
        total_duration = end_time - start_time
        
        logging.info(f"\n  Total test duration: {total_duration:.2f}s")
        
        # Check if response was generated
        if response:
            logging.info(f"  ✅ Response generated: {len(response)} chars")
            self.test_results['gpt_response_generated'] = True
        else:
            logging.error("  ❌ No response generated!")
            return
        
        # Check TTS events
        if self.tts_events:
            logging.info(f"  ✅ TTS events: {len(self.tts_events)} sentences queued")
            self.test_results['tts_sentences_detected'] = True
            
            # Show first few TTS events
            for event in self.tts_events[:3]:
                rel_time = event['time'] - start_time
                logging.info(f"    {rel_time:.2f}s: {event['sentence'][:50]}...")
        else:
            logging.error("  ❌ No TTS sentences detected!")
        
        # Check audio generation
        if self.mock_audio_device.chunks_played > 0:
            logging.info(f"  ✅ Audio chunks played: {self.mock_audio_device.chunks_played}")
            logging.info(f"  Total audio duration: {self.mock_audio_device.get_audio_duration():.2f}s")
            self.test_results['tts_audio_generated'] = True
            
            # Check if audio started during response generation
            if self.response_chunks and self.audio_events:
                first_audio_time = self.audio_events[0]['time']
                last_response_time = self.response_chunks[-1]['time']
                
                if first_audio_time < last_response_time:
                    logging.info(f"  ✅ Audio started during response generation!")
                    self.test_results['audio_played_during_response'] = True
                else:
                    logging.error(f"  ❌ Audio only started after response complete")
        else:
            logging.error("  ❌ No audio chunks played!")
        
        # Timing metrics
        self.test_results['timing_metrics'] = {
            'total_duration': total_duration,
            'response_chunks': len(self.response_chunks),
            'tts_events': len(self.tts_events),
            'audio_chunks': self.mock_audio_device.chunks_played
        }
    
    def run_all_tests(self):
        """Run all tests and generate report."""
        logging.info("="*60)
        logging.info("E2E STREAMING TTS TEST SUITE")
        logging.info("="*60)
        
        # Test 1: Configuration
        config = self.test_configuration()
        
        # Test 2: Voice discrimination
        self.test_voice_discrimination(config)
        
        # Test 3: Complete pipeline
        self.test_streaming_tts_pipeline(config)
        
        # Generate report
        self.generate_report()
        
        return self.test_results
    
    def generate_report(self):
        """Generate comprehensive test report."""
        logging.info("\n" + "="*60)
        logging.info("TEST RESULTS SUMMARY")
        logging.info("="*60)
        
        # Overall pass/fail
        all_passed = all([
            self.test_results['config_loaded'],
            self.test_results['gpt_response_generated'],
            self.test_results['tts_sentences_detected'],
            self.test_results['tts_audio_generated']
        ])
        
        if all_passed:
            if self.test_results['audio_played_during_response']:
                logging.info("✅ ALL TESTS PASSED - STREAMING TTS WORKING!")
            else:
                logging.info("⚠️  TESTS PASSED BUT AUDIO NOT STREAMING")
        else:
            logging.info("❌ TESTS FAILED - ISSUES FOUND")
        
        # Detailed results
        logging.info("\nDetailed Results:")
        for key, value in self.test_results.items():
            if key != 'timing_metrics':
                status = "✅" if value else "❌"
                logging.info(f"  {status} {key}: {value}")
        
        # Timing analysis
        if 'timing_metrics' in self.test_results:
            metrics = self.test_results['timing_metrics']
            logging.info(f"\nTiming Metrics:")
            for key, value in metrics.items():
                logging.info(f"  {key}: {value}")
        
        # Recommendations
        logging.info("\nRecommendations:")
        if not self.test_results['tts_audio_generated']:
            logging.info("  - Check OpenAI API key is valid")
            logging.info("  - Verify TTS worker thread is running")
            logging.info("  - Check for exceptions in TTS stream() method")
        elif not self.test_results['audio_played_during_response']:
            logging.info("  - Check sentence detection timing")
            logging.info("  - Verify buffer flushing logic")
            logging.info("  - Reduce min_sentence_chars setting")

if __name__ == "__main__":
    # Run the test suite
    test_suite = E2EStreamingTTSTest()
    results = test_suite.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if results.get('audio_played_during_response', False) else 1)
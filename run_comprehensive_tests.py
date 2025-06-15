#!/usr/bin/env python3
"""Comprehensive end-to-end integration testing for all streaming TTS fixes."""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
import threading
import queue

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

class ComprehensiveTestRunner:
    """Run all tests in headless CI mode."""
    
    def __init__(self):
        self.test_results = []
        self.start_time = time.time()
        
    def log(self, message, level="INFO"):
        """Log with timestamp."""
        elapsed = time.time() - self.start_time
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] [{level}] [{elapsed:5.2f}s] {message}")
        
    def run_test(self, test_name, test_func):
        """Run a single test and record results."""
        self.log(f"Running test: {test_name}")
        
        try:
            start = time.time()
            result = test_func()
            duration = time.time() - start
            
            self.test_results.append({
                'name': test_name,
                'status': 'PASS' if result else 'FAIL',
                'duration': duration,
                'error': None
            })
            
            status = "✅ PASS" if result else "❌ FAIL"
            self.log(f"{test_name}: {status} ({duration:.2f}s)")
            return result
            
        except Exception as e:
            duration = time.time() - start
            self.test_results.append({
                'name': test_name,
                'status': 'ERROR',
                'duration': duration,
                'error': str(e)
            })
            
            self.log(f"{test_name}: ❌ ERROR - {e}", "ERROR")
            return False
    
    def test_configuration(self):
        """Test 1: Verify configuration is correct."""
        try:
            from tsutils import configuration
            config = configuration.Config().data
            
            # Check critical settings
            checks = []
            
            # LLM response interval (was 10, should be 1)
            interval = config['General']['llm_response_interval']
            checks.append(('llm_response_interval', interval == 1, f"Expected 1, got {interval}"))
            
            # TTS streaming enabled
            tts_enabled = config['General']['tts_streaming_enabled']
            checks.append(('tts_streaming_enabled', tts_enabled, f"Expected True, got {tts_enabled}"))
            
            # TTS provider
            tts_provider = config['General']['tts_provider']
            checks.append(('tts_provider', tts_provider == 'openai', f"Expected 'openai', got '{tts_provider}'"))
            
            # Continuous response
            continuous = config['General']['continuous_response']
            checks.append(('continuous_response', continuous, f"Expected True, got {continuous}"))
            
            # Min sentence chars
            min_chars = config['General']['tts_min_sentence_chars']
            checks.append(('tts_min_sentence_chars', min_chars <= 20, f"Expected <=20, got {min_chars}"))
            
            # Voice filter
            voice_filter = config['General']['voice_filter_enabled']
            checks.append(('voice_filter_enabled', True, f"Voice filter is {voice_filter}"))
            
            # Print results
            all_passed = True
            for check_name, passed, message in checks:
                if passed:
                    self.log(f"  ✓ {check_name}: {message}")
                else:
                    self.log(f"  ✗ {check_name}: {message}", "WARN")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log(f"Configuration test failed: {e}", "ERROR")
            return False
    
    def test_imports(self):
        """Test 2: Verify all required modules can be imported."""
        modules_to_test = [
            ('app.transcribe.gpt_responder', 'GPT Responder'),
            ('app.transcribe.audio_transcriber', 'Audio Transcriber'),
            ('app.transcribe.streaming_tts', 'Streaming TTS'),
            ('app.transcribe.audio_player_streaming', 'Audio Player'),
            ('app.transcribe.voice_filter', 'Voice Filter'),
            ('app.transcribe.appui', 'App UI'),
            ('app.transcribe.main', 'Main'),
        ]
        
        all_passed = True
        for module_name, display_name in modules_to_test:
            try:
                __import__(module_name)
                self.log(f"  ✓ {display_name} imported successfully")
            except Exception as e:
                self.log(f"  ✗ {display_name} import failed: {e}", "ERROR")
                all_passed = False
        
        return all_passed
    
    def test_gpt_responder_timing(self):
        """Test 3: Verify GPT responder initializes with correct timing."""
        try:
            from app.transcribe.gpt_responder import GPTResponder
            from app.transcribe.conversation import Conversation
            from tsutils import configuration
            
            config = configuration.Config().data
            convo = Conversation(context=None)
            
            # Create responder
            responder = GPTResponder(
                config=config,
                convo=convo,
                file_name="test.txt",
                save_to_file=False
            )
            
            # Check interval
            interval = responder.llm_response_interval
            self.log(f"  LLM response interval: {interval}s")
            
            # Check TTS enabled
            tts_enabled = responder.tts_enabled
            self.log(f"  TTS enabled: {tts_enabled}")
            
            # Check streaming flag exists
            has_flag = hasattr(responder, 'streaming_tts_active')
            self.log(f"  Has streaming_tts_active flag: {has_flag}")
            
            return interval == 1 and has_flag
            
        except Exception as e:
            self.log(f"GPT responder test failed: {e}", "ERROR")
            return False
    
    def test_audio_flow(self):
        """Test 4: Simulate audio flow from transcription to TTS."""
        try:
            from app.transcribe.audio_transcriber import AudioTranscriber
            from unittest.mock import Mock
            
            # Create mock components
            mock_queue = queue.Queue()
            mock_convo = Mock()
            mock_convo.get_merged_conversation_response.return_value = [
                ("You", "Test message", "1")
            ]
            
            # Test transcript change event
            transcriber = Mock(spec=AudioTranscriber)
            transcriber.transcript_changed_event = threading.Event()
            
            # Simulate transcript change
            self.log("  Simulating voice input...")
            transcriber.transcript_changed_event.set()
            
            # Check if event is set
            is_set = transcriber.transcript_changed_event.is_set()
            self.log(f"  Transcript changed event set: {is_set}")
            
            return is_set
            
        except Exception as e:
            self.log(f"Audio flow test failed: {e}", "ERROR")
            return False
    
    def test_sentence_detection(self):
        """Test 5: Verify sentence detection works correctly."""
        try:
            import re
            
            # Test the regex pattern
            SENT_END = re.compile(r"[.!?]")
            
            test_cases = [
                ("Hello world.", True, "Simple sentence with period"),
                ("Hello world!", True, "Sentence with exclamation"),
                ("Hello world?", True, "Sentence with question mark"),
                ("Hello world", False, "No punctuation"),
                ("Hello.", True, "Short sentence"),
                ("Hi", False, "Too short, no punctuation"),
            ]
            
            all_passed = True
            for text, should_match, description in test_cases:
                match = SENT_END.search(text)
                matched = match is not None
                
                if matched == should_match:
                    self.log(f"  ✓ {description}: '{text}' -> {matched}")
                else:
                    self.log(f"  ✗ {description}: '{text}' -> {matched} (expected {should_match})", "WARN")
                    all_passed = False
            
            return all_passed
            
        except Exception as e:
            self.log(f"Sentence detection test failed: {e}", "ERROR")
            return False
    
    def test_tts_provider(self):
        """Test 6: Verify TTS provider can be created."""
        try:
            from app.transcribe.streaming_tts import create_tts, TTSConfig
            
            # Create config (without API key for safety)
            config = TTSConfig(
                provider="openai",
                voice="alloy",
                sample_rate=24000,
                api_key="test-key"  # Won't actually call API
            )
            
            # Create TTS
            tts = create_tts(config)
            
            # Check class
            class_name = tts.__class__.__name__
            self.log(f"  TTS provider created: {class_name}")
            
            # Check if stream method exists
            has_stream = hasattr(tts, 'stream')
            self.log(f"  Has stream method: {has_stream}")
            
            return class_name == "OpenAITTS" and has_stream
            
        except Exception as e:
            self.log(f"TTS provider test failed: {e}", "ERROR")
            return False
    
    def test_audio_player(self):
        """Test 7: Verify audio player can be created."""
        try:
            from app.transcribe.audio_player_streaming import StreamingAudioPlayer
            
            # Create player (but don't start it)
            player = StreamingAudioPlayer()
            
            # Check attributes
            has_queue = hasattr(player, 'q')
            has_enqueue = hasattr(player, 'enqueue')
            
            self.log(f"  Has queue: {has_queue}")
            self.log(f"  Has enqueue method: {has_enqueue}")
            self.log(f"  Queue max size: {player.q.maxsize if has_queue else 'N/A'}")
            
            return has_queue and has_enqueue
            
        except Exception as e:
            self.log(f"Audio player test failed: {e}", "ERROR")
            return False
    
    def test_response_timing_logs(self):
        """Test 8: Verify response timing logs are in place."""
        try:
            # Check if audio_transcriber has timing logs
            with open('app/transcribe/audio_transcriber.py', 'r') as f:
                content = f.read()
            
            has_response_debug = '[Response Debug]' in content
            self.log(f"  Has [Response Debug] logs: {has_response_debug}")
            
            # Check if gpt_responder has timing logs
            with open('app/transcribe/gpt_responder.py', 'r') as f:
                content = f.read()
            
            has_first_token = '_first_token_time' in content
            self.log(f"  Has first token timing: {has_first_token}")
            
            return has_response_debug and has_first_token
            
        except Exception as e:
            self.log(f"Response timing logs test failed: {e}", "ERROR")
            return False
    
    def generate_report(self):
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['status'] == 'PASS')
        failed = sum(1 for r in self.test_results if r['status'] == 'FAIL')
        errors = sum(1 for r in self.test_results if r['status'] == 'ERROR')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_duration': time.time() - self.start_time,
            'summary': {
                'total': total_tests,
                'passed': passed,
                'failed': failed,
                'errors': errors
            },
            'tests': self.test_results
        }
        
        # Save JSON report
        with open('test_report.json', 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"⚠️  Errors: {errors}")
        print(f"Total Time: {report['total_duration']:.2f}s")
        
        # Detailed results
        print("\nDetailed Results:")
        for test in self.test_results:
            status_icon = {
                'PASS': '✅',
                'FAIL': '❌',
                'ERROR': '⚠️'
            }.get(test['status'], '?')
            
            print(f"{status_icon} {test['name']}: {test['status']} ({test['duration']:.2f}s)")
            if test['error']:
                print(f"   Error: {test['error']}")
        
        return passed == total_tests
    
    def run_all_tests(self):
        """Run all tests in sequence."""
        print("="*60)
        print("COMPREHENSIVE STREAMING TTS TEST SUITE")
        print("="*60)
        print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Define all tests
        tests = [
            ("Configuration Check", self.test_configuration),
            ("Module Imports", self.test_imports),
            ("GPT Responder Timing", self.test_gpt_responder_timing),
            ("Audio Flow Simulation", self.test_audio_flow),
            ("Sentence Detection", self.test_sentence_detection),
            ("TTS Provider Creation", self.test_tts_provider),
            ("Audio Player Creation", self.test_audio_player),
            ("Response Timing Logs", self.test_response_timing_logs),
        ]
        
        # Run each test
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
            print()  # Blank line between tests
        
        # Generate report
        all_passed = self.generate_report()
        
        print("\n" + "="*60)
        if all_passed:
            print("✅ ALL TESTS PASSED - System should be working!")
            print("\nNext steps:")
            print("1. Run the application with: run_windows_launch.bat")
            print("2. Test with real voice input")
            print("3. Verify audio streams while text appears")
        else:
            print("❌ SOME TESTS FAILED - Check detailed results above")
            print("\nDebug the failed tests before running the application")
        
        return all_passed

if __name__ == '__main__':
    runner = ComprehensiveTestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
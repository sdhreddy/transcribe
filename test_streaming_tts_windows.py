#!/usr/bin/env python3
"""
Definitive test script for streaming TTS on Windows.
This script tests the actual code paths from the application, mocking only what's necessary for WSL.
"""
import sys
import os
import threading
import time
import queue
import logging
import traceback
from unittest.mock import Mock, patch, MagicMock
from dataclasses import dataclass
import json

# Add the app path to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('TTS_TEST')

# Test results storage
test_results = {
    'config_loaded': False,
    'tts_enabled_in_config': False,
    'responder_created': False,
    'tts_initialized': False,
    'tts_worker_started': False,
    'sentence_detection_working': False,
    'tts_stream_called': False,
    'audio_chunks_generated': False,
    'audio_player_received_chunks': False,
    'streaming_flow_complete': False,
    'errors': []
}

# Mock PyAudio to prevent audio device errors in WSL
class MockPyAudio:
    class Stream:
        def __init__(self):
            self.written_chunks = []
            
        def write(self, data, exception_on_underflow=False):
            self.written_chunks.append(data)
            logger.info(f"[MOCK] Audio write called with {len(data)} bytes")
            test_results['audio_player_received_chunks'] = True
            return len(data)
            
        def stop_stream(self):
            pass
            
        def close(self):
            pass
    
    def __init__(self):
        self.stream = self.Stream()
        
    def open(self, **kwargs):
        logger.info(f"[MOCK] PyAudio.open called with: {kwargs}")
        return self.stream
        
    def get_device_count(self):
        return 1
        
    def get_default_output_device_info(self):
        return {'index': 0, 'name': 'Mock Audio Device'}

# Patch pyaudio before any imports
sys.modules['pyaudio'] = Mock()
sys.modules['pyaudio'].PyAudio = MockPyAudio
sys.modules['pyaudio'].paInt16 = 8  # PyAudio constant

# Mock database before imports
sys.modules['app.transcribe.db'] = Mock()
sys.modules['app.transcribe.db.app_db'] = Mock()
sys.modules['app.transcribe.db.conversation'] = Mock()
sys.modules['app.transcribe.db.llm_responses'] = Mock()
sys.modules['app.transcribe.db.summaries'] = Mock()

# Create mock AppDB class
class MockAppDB:
    def get_invocation_id(self):
        return 1
    def get_object(self, table_name):
        return Mock()

# Set up the mock
sys.modules['app.transcribe.db'].AppDB = MockAppDB

# Mock OpenAI client
class MockOpenAIClient:
    class Audio:
        def __init__(self):
            self.speech = self.Speech()
            
        class Speech:
            @staticmethod
            def create(**kwargs):
                logger.info(f"[MOCK] OpenAI TTS called with: {kwargs}")
                test_results['tts_stream_called'] = True
                
                class MockResponse:
                    content = b"Mock audio data " * 100  # Simulate audio data
                    
                    def iter_bytes(self, chunk_size=4096):
                        for i in range(0, len(MockResponse.content), chunk_size):
                            yield MockResponse.content[i:i+chunk_size]
                            test_results['audio_chunks_generated'] = True
                
                return MockResponse()
    
    class Chat:
        class Completions:
            @staticmethod
            def create(**kwargs):
                logger.info(f"[MOCK] OpenAI chat completion called")
                return []
    
    def __init__(self, api_key=None, base_url=None):
        self.audio = self.Audio()
        self.chat = self.Chat()
        self.chat.completions = self.Chat.Completions()

# Mock openai module before imports
import openai
sys.modules['openai'] = Mock()
sys.modules['openai'].OpenAI = MockOpenAIClient

# Now import the actual modules
from app.transcribe.gpt_responder import GPTResponder, OpenAIResponder
from app.transcribe.streaming_tts import create_tts, TTSConfig
from app.transcribe.audio_player_streaming import StreamingAudioPlayer
from app.transcribe import conversation
from tsutils import configuration

# Test harness
class StreamingTTSTestHarness:
    def __init__(self):
        self.config = None
        self.responder = None
        self.conversation = None
        
    def load_config(self):
        """Load actual configuration from the app"""
        try:
            config_obj = configuration.Config()
            self.config = config_obj.data
            test_results['config_loaded'] = True
            
            # Check TTS configuration
            tts_enabled = self.config.get('General', {}).get('tts_streaming_enabled', False)
            test_results['tts_enabled_in_config'] = tts_enabled
            
            logger.info(f"Config loaded. TTS enabled: {tts_enabled}")
            logger.info(f"TTS provider: {self.config.get('General', {}).get('tts_provider')}")
            logger.info(f"TTS voice: {self.config.get('General', {}).get('tts_voice')}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            test_results['errors'].append(f"Config load error: {str(e)}")
            return False
    
    def create_responder(self):
        """Create the GPT responder with actual code paths"""
        try:
            # Create conversation object with mock context
            mock_context = Mock()
            self.conversation = conversation.Conversation(context=mock_context)
            
            # Mock OpenAI module
            mock_openai = Mock()
            mock_openai.OpenAI = MockOpenAIClient
            
            # Create responder using actual factory pattern from app
            self.responder = OpenAIResponder(
                config=self.config,
                convo=self.conversation,
                response_file_name="test_response.txt",
                save_to_file=False
            )
            
            # Replace the OpenAI client with our mock
            self.responder.llm_client = MockOpenAIClient()
            
            # Also patch the TTS OpenAI client if it exists
            if hasattr(self.responder, 'tts') and hasattr(self.responder.tts, 'client'):
                self.responder.tts.client = MockOpenAIClient()
            
            test_results['responder_created'] = True
            
            # Check if TTS was initialized
            if hasattr(self.responder, 'tts_enabled'):
                test_results['tts_initialized'] = self.responder.tts_enabled
                logger.info(f"Responder TTS enabled: {self.responder.tts_enabled}")
                
                if self.responder.tts_enabled:
                    # Check if worker thread started
                    if hasattr(self.responder, 'tts_worker_thread'):
                        test_results['tts_worker_started'] = self.responder.tts_worker_thread.is_alive()
                        logger.info(f"TTS worker thread alive: {test_results['tts_worker_started']}")
            
            return True
        except Exception as e:
            logger.error(f"Failed to create responder: {e}")
            logger.error(traceback.format_exc())
            test_results['errors'].append(f"Responder creation error: {str(e)}")
            return False
    
    def test_sentence_detection(self):
        """Test the sentence detection logic"""
        try:
            if not self.responder or not self.responder.tts_enabled:
                logger.warning("Skipping sentence detection test - TTS not enabled")
                return False
                
            logger.info("Testing sentence detection...")
            
            # Simulate streaming tokens
            test_sentences = [
                ("Hello", False),  # No sentence end
                (" world", False),  # Still no sentence end
                (".", True),  # Sentence end - should trigger
                (" How", False),  # New sentence start
                (" are", False),
                (" you", False),
                ("?", True),  # Another sentence end
            ]
            
            sentences_detected = []
            
            # Hook into the sentence queue to capture detected sentences
            original_put = self.responder.sent_q.put
            def mock_put(sentence):
                sentences_detected.append(sentence)
                original_put(sentence)
            self.responder.sent_q.put = mock_put
            
            # Reset buffer
            self.responder.buffer = ""
            
            # Feed tokens
            for token, should_trigger in test_sentences:
                self.responder._handle_streaming_token(token)
                
                if should_trigger:
                    # Give it a moment to process
                    time.sleep(0.1)
            
            logger.info(f"Sentences detected: {sentences_detected}")
            test_results['sentence_detection_working'] = len(sentences_detected) > 0
            
            return True
        except Exception as e:
            logger.error(f"Sentence detection test failed: {e}")
            test_results['errors'].append(f"Sentence detection error: {str(e)}")
            return False
    
    def test_streaming_flow(self):
        """Test the complete streaming flow"""
        try:
            if not self.responder or not self.responder.tts_enabled:
                logger.warning("Skipping streaming flow test - TTS not enabled")
                return False
                
            logger.info("Testing complete streaming flow...")
            
            # Create a mock LLM streaming response
            class MockChunk:
                class Choice:
                    class Delta:
                        def __init__(self, content):
                            self.content = content
                    def __init__(self, content):
                        self.delta = self.Delta(content)
                
                def __init__(self, content):
                    self.choices = [self.Choice(content)]
            
            # Simulate streaming response
            streaming_text = "Hello world. How are you today? I hope you're doing well."
            
            # Mock the LLM response
            def mock_chat_completion(**kwargs):
                chunks = []
                # Break text into word chunks
                words = streaming_text.split()
                for i, word in enumerate(words):
                    if i > 0:
                        chunks.append(MockChunk(" " + word))
                    else:
                        chunks.append(MockChunk(word))
                return iter(chunks)
            
            self.responder.llm_client.chat.completions.create = Mock(side_effect=mock_chat_completion)
            
            # Start monitoring
            chunks_processed = []
            original_stream = self.responder.tts.stream if hasattr(self.responder, 'tts') else None
            
            if original_stream:
                def mock_stream(text):
                    chunks_processed.append(text)
                    logger.info(f"[TTS] Processing: '{text}'")
                    return original_stream(text)
                
                self.responder.tts.stream = mock_stream
            
            # Trigger response generation
            self.responder._update_conversation = Mock()  # Prevent DB updates
            
            # Create mock messages
            messages = [{"role": "user", "content": "Hello"}]
            
            # Call the actual response method
            response = self.responder._get_llm_response(messages, 0.0, 10)
            
            # Wait for processing
            time.sleep(2)
            
            # Check results
            logger.info(f"Response received: {response}")
            logger.info(f"TTS chunks processed: {chunks_processed}")
            
            test_results['streaming_flow_complete'] = len(chunks_processed) > 0
            
            return True
        except Exception as e:
            logger.error(f"Streaming flow test failed: {e}")
            logger.error(traceback.format_exc())
            test_results['errors'].append(f"Streaming flow error: {str(e)}")
            return False

def print_test_results():
    """Print comprehensive test results"""
    print("\n" + "="*60)
    print("STREAMING TTS TEST RESULTS")
    print("="*60)
    
    # Overall result
    streaming_works = (
        test_results['config_loaded'] and
        test_results['tts_enabled_in_config'] and
        test_results['responder_created'] and
        test_results['tts_initialized'] and
        test_results['tts_worker_started'] and
        test_results['sentence_detection_working'] and
        test_results['tts_stream_called'] and
        test_results['audio_chunks_generated'] and
        test_results['streaming_flow_complete']
    )
    
    print(f"\n🎯 STREAMING TTS WORKING: {'YES ✅' if streaming_works else 'NO ❌'}")
    
    print("\nDetailed Results:")
    print("-" * 60)
    
    # Individual checks
    checks = [
        ('Configuration loaded', test_results['config_loaded']),
        ('TTS enabled in config', test_results['tts_enabled_in_config']),
        ('Responder created', test_results['responder_created']),
        ('TTS initialized', test_results['tts_initialized']),
        ('TTS worker thread started', test_results['tts_worker_started']),
        ('Sentence detection working', test_results['sentence_detection_working']),
        ('TTS stream() called', test_results['tts_stream_called']),
        ('Audio chunks generated', test_results['audio_chunks_generated']),
        ('Audio player received chunks', test_results['audio_player_received_chunks']),
        ('Streaming flow complete', test_results['streaming_flow_complete']),
    ]
    
    for check_name, passed in checks:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{check_name:<35} {status}")
    
    if test_results['errors']:
        print("\n⚠️  Errors encountered:")
        for error in test_results['errors']:
            print(f"  - {error}")
    
    # Diagnosis
    print("\n📋 DIAGNOSIS:")
    print("-" * 60)
    
    if not test_results['config_loaded']:
        print("❌ Configuration failed to load. Check parameters.yaml exists.")
    elif not test_results['tts_enabled_in_config']:
        print("❌ TTS is DISABLED in configuration. Set 'tts_streaming_enabled: true' in parameters.yaml")
    elif not test_results['responder_created']:
        print("❌ Responder creation failed. Check error logs above.")
    elif not test_results['tts_initialized']:
        print("❌ TTS initialization failed within responder.")
    elif not test_results['tts_worker_started']:
        print("❌ TTS worker thread failed to start.")
    elif not test_results['sentence_detection_working']:
        print("❌ Sentence detection logic is not working properly.")
    elif not test_results['tts_stream_called']:
        print("❌ TTS stream() method was never called.")
    elif not test_results['audio_chunks_generated']:
        print("❌ TTS is not generating audio chunks.")
    elif not test_results['streaming_flow_complete']:
        print("❌ Complete streaming flow is broken somewhere.")
    else:
        print("✅ All components are working correctly!")
        print("   Streaming TTS should work on Windows.")
    
    print("\n" + "="*60)

def main():
    """Run all tests"""
    print("Starting Streaming TTS Test for Windows...")
    print("This test uses actual code paths from the application.")
    print("-" * 60)
    
    harness = StreamingTTSTestHarness()
    
    # Test 1: Load configuration
    print("\n1. Loading configuration...")
    if not harness.load_config():
        print_test_results()
        return
    
    # Test 2: Create responder
    print("\n2. Creating GPT responder...")
    if not harness.create_responder():
        print_test_results()
        return
    
    # Test 3: Sentence detection
    print("\n3. Testing sentence detection...")
    harness.test_sentence_detection()
    
    # Test 4: Complete streaming flow
    print("\n4. Testing complete streaming flow...")
    harness.test_streaming_flow()
    
    # Wait a bit for async operations to complete
    print("\n5. Waiting for async operations...")
    time.sleep(2)
    
    # Print results
    print_test_results()

if __name__ == "__main__":
    main()
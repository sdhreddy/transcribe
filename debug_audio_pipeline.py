#!/usr/bin/env python3
"""Debug the entire audio pipeline to find where audio is failing."""

import os
import sys
import time
import threading
import logging
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Enable mock TTS
os.environ['USE_MOCK_TTS'] = 'true'

# Enable all debug logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class AudioPipelineDebugger:
    """Debug each stage of the audio pipeline."""
    
    def __init__(self):
        self.pipeline_stages = {
            'config_loaded': False,
            'responder_created': False,
            'tts_initialized': False,
            'audio_player_created': False,
            'worker_thread_started': False,
            'sentence_detected': False,
            'tts_stream_called': False,
            'audio_chunk_generated': False,
            'audio_chunk_enqueued': False,
            'audio_chunk_played': False
        }
        self.debug_info = []
        
    def log_stage(self, stage, success, info=""):
        """Log a pipeline stage result."""
        self.pipeline_stages[stage] = success
        status = "✅" if success else "❌"
        msg = f"{status} {stage}: {info}"
        print(msg)
        self.debug_info.append(msg)
        
    @patch('pyaudio.PyAudio')
    def debug_pipeline(self, mock_pyaudio):
        """Debug the complete audio pipeline."""
        print("="*60)
        print("AUDIO PIPELINE DEBUGGER")
        print("="*60)
        
        # Mock PyAudio
        mock_pa = MagicMock()
        mock_stream = MagicMock()
        mock_pa.open.return_value = mock_stream
        mock_pa.get_default_output_device_info.return_value = {'index': 0, 'name': 'Mock'}
        mock_pa.get_device_count.return_value = 1
        mock_pyaudio.return_value = mock_pa
        
        # Track audio writes
        audio_writes = []
        def mock_write(data, **kwargs):
            audio_writes.append({'data': data, 'size': len(data), 'time': time.time()})
            print(f"[Audio Write] {len(data)} bytes written to audio device")
            return len(data)
        mock_stream.write = mock_write
        
        # Stage 1: Load configuration
        print("\n1. Loading configuration...")
        try:
            from tsutils import configuration
            config = configuration.Config().data
            self.log_stage('config_loaded', True, 
                          f"tts_enabled={config['General'].get('tts_streaming_enabled')}")
        except Exception as e:
            self.log_stage('config_loaded', False, str(e))
            return
        
        # Stage 2: Create responder
        print("\n2. Creating responder...")
        try:
            from app.transcribe.global_vars import TranscriptionGlobals
            from app.transcribe import app_utils
            
            # Enable mock TTS
            from app.transcribe.mock_tts_provider import enable_mock_tts
            enable_mock_tts()
            
            global_vars = TranscriptionGlobals()
            global_vars.config = config
            
            responder = app_utils.create_responder(
                provider_name=config['General']['chat_inference_provider'],
                config=config,
                convo=global_vars.convo,
                save_to_file=False,
                response_file_name="test.txt"
            )
            self.log_stage('responder_created', True, type(responder).__name__)
        except Exception as e:
            self.log_stage('responder_created', False, str(e))
            return
        
        # Stage 3: Check TTS initialization
        print("\n3. Checking TTS initialization...")
        if hasattr(responder, 'tts_enabled') and responder.tts_enabled:
            self.log_stage('tts_initialized', True, 
                          f"tts_enabled={responder.tts_enabled}")
        else:
            self.log_stage('tts_initialized', False, "TTS not enabled in responder")
            return
        
        # Stage 4: Check audio player
        print("\n4. Checking audio player...")
        if hasattr(responder, 'player'):
            self.log_stage('audio_player_created', True, 
                          f"player type={type(responder.player).__name__}")
        else:
            self.log_stage('audio_player_created', False, "No audio player")
            return
        
        # Stage 5: Check worker thread
        print("\n5. Checking TTS worker thread...")
        if hasattr(responder, 'tts_worker_thread') and responder.tts_worker_thread.is_alive():
            self.log_stage('worker_thread_started', True, "Thread is alive")
        else:
            self.log_stage('worker_thread_started', False, "Thread not running")
        
        # Stage 6: Test sentence detection
        print("\n6. Testing sentence detection...")
        
        # Hook into sentence queue
        sentences_queued = []
        if hasattr(responder, 'sent_q'):
            original_put = responder.sent_q.put
            def tracked_put(item):
                sentences_queued.append(item)
                print(f"[Sentence Queue] '{item}'")
                self.log_stage('sentence_detected', True, f"'{item[:30]}...'")
                return original_put(item)
            responder.sent_q.put = tracked_put
        
        # Stage 7: Test TTS stream
        print("\n7. Testing TTS stream generation...")
        
        # Hook into TTS stream
        if hasattr(responder, 'tts'):
            original_stream = responder.tts.stream
            def tracked_stream(text):
                print(f"[TTS Stream] Called with: '{text[:30]}...'")
                self.log_stage('tts_stream_called', True, text[:30])
                chunks = list(original_stream(text))
                if chunks:
                    self.log_stage('audio_chunk_generated', True, 
                                 f"{len(chunks)} chunks, {sum(len(c) for c in chunks)} bytes")
                for chunk in chunks:
                    yield chunk
            responder.tts.stream = tracked_stream
        
        # Stage 8: Generate a test response
        print("\n8. Generating test response...")
        
        # Add test conversation
        from datetime import datetime
        # Initialize conversation properly
        global_vars.convo.clear()
        global_vars.convo.update_conversation(
            persona=1,  # Use numeric persona
            text="What is Python?",
            time_spoken=datetime.utcnow(),
            update_previous=False
        )
        
        # Enable responder
        responder.enabled = True
        
        # Generate response with mock LLM
        with patch.object(responder, '_get_llm_response') as mock_llm:
            # Simulate streaming response
            def simulate_streaming(messages, temp, timeout):
                test_response = "Python is a programming language. It is very popular."
                # Simulate token-by-token streaming
                for word in test_response.split():
                    responder._handle_streaming_token(word + " ")
                    time.sleep(0.05)
                responder.streaming_complete.set()
                return test_response
            
            mock_llm.side_effect = simulate_streaming
            
            # Generate response
            response = responder.generate_response_from_transcript_no_check()
            
            print(f"\nGenerated response: '{response}'")
        
        # Wait for audio processing
        print("\n9. Waiting for audio processing...")
        time.sleep(2)
        
        # Check results
        print("\n10. Checking results...")
        
        if sentences_queued:
            print(f"  ✅ Sentences queued: {len(sentences_queued)}")
            for s in sentences_queued:
                print(f"    - '{s}'")
        else:
            print("  ❌ No sentences queued!")
        
        if audio_writes:
            self.log_stage('audio_chunk_played', True, 
                          f"{len(audio_writes)} writes, {sum(w['size'] for w in audio_writes)} bytes")
        else:
            self.log_stage('audio_chunk_played', False, "No audio written")
        
        # Generate report
        self.generate_report()
    
    def generate_report(self):
        """Generate pipeline debug report."""
        print("\n" + "="*60)
        print("PIPELINE DEBUG REPORT")
        print("="*60)
        
        # Check where pipeline broke
        failed_stages = [stage for stage, success in self.pipeline_stages.items() if not success]
        
        if not failed_stages:
            print("✅ ALL STAGES PASSED!")
            print("\nIf audio still not playing on Windows:")
            print("1. Check Windows audio device settings")
            print("2. Verify no other app is using audio")
            print("3. Check Windows console for error messages")
        else:
            print(f"❌ PIPELINE FAILED AT: {failed_stages[0]}")
            print("\nFailed stages:")
            for stage in failed_stages:
                print(f"  - {stage}")
        
        print("\nPipeline flow:")
        for stage, success in self.pipeline_stages.items():
            status = "✅" if success else "❌"
            print(f"  {status} {stage}")
        
        # Save detailed log
        with open('audio_pipeline_debug.log', 'w') as f:
            f.write("Audio Pipeline Debug Log\n")
            f.write("="*60 + "\n\n")
            for info in self.debug_info:
                f.write(info + "\n")
        
        print(f"\nDetailed log saved to: audio_pipeline_debug.log")

if __name__ == "__main__":
    debugger = AudioPipelineDebugger()
    debugger.debug_pipeline()
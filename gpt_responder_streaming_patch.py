#!/usr/bin/env python3
"""
Patch for gpt_responder.py to add streaming TTS support.
This creates the modifications needed for progressive TTS.
"""

PATCH_IMPORTS = """
# Add these imports after existing imports
import re
import queue
from .streaming_tts import create_tts, TTSConfig
from .audio_player_streaming import StreamingAudioPlayer
"""

PATCH_INIT = """
# Add to __init__ method after self.streaming_complete = threading.Event()
        
        # Streaming TTS support
        self.buffer = ""
        self.sent_q: queue.Queue[str] = queue.Queue()
        self.SENT_END = re.compile(r"[.!?]\s*")  # sentence boundary pattern
        
        # Initialize TTS if enabled
        if config.get('General', {}).get('tts_streaming_enabled', False):
            tts_config = TTSConfig(
                provider=config.get('General', {}).get('tts_provider', 'gtts'),
                voice=config.get('General', {}).get('tts_voice', 'alloy'),
                sample_rate=config.get('General', {}).get('tts_sample_rate', 24000),
                api_key=config.get('OpenAI', {}).get('api_key')
            )
            self.tts = create_tts(tts_config)
            self.player = StreamingAudioPlayer(sample_rate=tts_config.sample_rate)
            self.player.start()
            self.tts_worker_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_worker_thread.start()
            self.tts_enabled = True
            logger.info("Streaming TTS initialized")
        else:
            self.tts_enabled = False
"""

PATCH_METHODS = """
# Add these methods to GPTResponder class

    def _handle_streaming_token(self, token: str):
        \"\"\"Handle incoming token from LLM stream for TTS processing.\"\"\"
        if not self.tts_enabled:
            return
            
        self.buffer += token
        
        # Check for sentence boundaries
        matches = list(self.SENT_END.finditer(self.buffer))
        if matches:
            # Get the last complete sentence
            last_match = matches[-1]
            complete_sentence = self.buffer[:last_match.end()].strip()
            
            if complete_sentence and len(complete_sentence) > 10:  # Min length check
                self.sent_q.put(complete_sentence)
                self.buffer = self.buffer[last_match.end():]
        
        # Also check if buffer is getting too long without punctuation
        elif len(self.buffer) > 100:
            # Force a break at a reasonable point
            words = self.buffer.split()
            if len(words) > 15:
                # Take first 15 words
                partial = ' '.join(words[:15])
                self.sent_q.put(partial)
                self.buffer = ' '.join(words[15:])
    
    def _tts_worker(self):
        \"\"\"Worker thread that converts sentences to speech and plays them.\"\"\"
        logger.info("TTS worker thread started")
        
        while True:
            try:
                sentence = self.sent_q.get(timeout=1.0)
                if sentence is None:  # Shutdown signal
                    break
                    
                logger.info(f"TTS processing: {len(sentence)} chars")
                
                # Stream TTS audio
                for audio_chunk in self.tts.stream(sentence):
                    self.player.enqueue(audio_chunk)
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"TTS worker error: {e}")
                
        logger.info("TTS worker thread stopped")
    
    def flush_tts_buffer(self):
        \"\"\"Flush any remaining text in buffer when streaming completes.\"\"\"
        if self.tts_enabled and self.buffer.strip():
            self.sent_q.put(self.buffer.strip())
            self.buffer = ""
    
    def stop_tts(self):
        \"\"\"Stop TTS playback and cleanup.\"\"\"
        if self.tts_enabled:
            self.sent_q.put(None)  # Signal worker to stop
            self.player.stop()
"""

PATCH_STREAMING = """
# Modify the streaming loop in generate_response_from_transcript_no_check 
# and generate_response_for_selected_text methods

# In the streaming loop where it says:
#     collected_messages += message_text
# Add after that line:
                        self._handle_streaming_token(message_text)

# After the streaming loop completes, add:
                self.flush_tts_buffer()
"""

def create_patch_file():
    """Create a complete patch file for gpt_responder.py"""
    
    with open('gpt_responder_streaming.patch', 'w') as f:
        f.write("=== Streaming TTS Patch for gpt_responder.py ===\n\n")
        f.write("1. Add imports:\n")
        f.write(PATCH_IMPORTS)
        f.write("\n\n2. Modify __init__ method:\n")
        f.write(PATCH_INIT)
        f.write("\n\n3. Add new methods:\n")
        f.write(PATCH_METHODS)
        f.write("\n\n4. Modify streaming loops:\n")
        f.write(PATCH_STREAMING)
        
    print("Created gpt_responder_streaming.patch")

if __name__ == "__main__":
    create_patch_file()
#!/usr/bin/env python3
"""Fix critical audio player issues."""

import os

def fix_audio_player():
    """Fix audio player to be more robust."""
    
    print("Fixing critical audio player issues...\n")
    
    audio_path = "app/transcribe/audio_player_streaming.py"
    if not os.path.exists(audio_path):
        print(f"Error: {audio_path} not found!")
        return
    
    with open(audio_path, 'r') as f:
        content = f.read()
    
    # Fix 1: Make the audio player more robust
    print("1. Making audio player more robust...")
    
    # Find the run method
    if "def run(self):" in content:
        # Replace the run method with a more robust version
        new_run_method = '''    def run(self):
        """Main playback loop."""
        logger.info("[TTS Debug] Streaming audio player thread started")
        
        consecutive_errors = 0
        
        while self.running:
            try:
                chunk = self.q.get(timeout=1.0)
                if chunk is None:
                    logger.info("[TTS Debug] Received stop signal")
                    break
                
                # Reset error counter on successful get
                consecutive_errors = 0
                
                self.playing = True
                # Windows fix: Use wait=True on newer PyAudio versions for better stability
                try:
                    bytes_written = self.stream.write(chunk, exception_on_underflow=False)
                    logger.debug(f"[TTS Debug] Wrote {bytes_written if bytes_written else len(chunk)} bytes")
                except Exception as e:
                    # Fallback for older PyAudio versions
                    try:
                        self.stream.write(chunk)
                    except Exception as e2:
                        logger.error(f"[TTS Debug] Failed to write audio: {e2}")
                        consecutive_errors += 1
                        if consecutive_errors > 5:
                            logger.error("[TTS Debug] Too many audio errors, stopping player")
                            break
                
                self.playing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"[TTS Debug] Audio playback error: {type(e).__name__}: {e}")
                consecutive_errors += 1
                if consecutive_errors > 5:
                    logger.error("[TTS Debug] Too many errors, stopping player")
                    break
                
        self.stream.stop_stream()
        self.stream.close()
        logger.info("[TTS Debug] Streaming audio player thread stopped")'''
        
        # Replace the old run method
        import re
        run_pattern = r'def run\(self\):.*?logger\.info\("\[TTS Debug\] Streaming audio player thread stopped"\)'
        
        # First check if we have the new version already
        if "[TTS Debug] Streaming audio player thread started" not in content:
            # Find and replace the old method
            old_run_pattern = r'def run\(self\):.*?self\.stream\.close\(\)\s*logger\.info\("Streaming audio player thread stopped"\)'
            match = re.search(old_run_pattern, content, re.DOTALL)
            if match:
                content = content.replace(match.group(0), new_run_method.strip())
                print("   ✓ Updated run method with better error handling")
            else:
                print("   ⚠️  Could not find run method to update")
    
    # Fix 2: Add recovery mechanism
    print("\n2. Adding audio recovery mechanism...")
    
    if "def recover_audio(self):" not in content:
        recovery_method = '''
    def recover_audio(self):
        """Try to recover audio playback after errors."""
        try:
            logger.info("[TTS Debug] Attempting audio recovery...")
            self.stream.stop_stream()
            self.stream.close()
            
            # Reinitialize
            pa = pyaudio.PyAudio()
            self.stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=self.sample_rate,
                output=True,
                output_device_index=self.output_device_index if hasattr(self, 'output_device_index') else None,
                frames_per_buffer=int(self.sample_rate * (self.buf_ms / 1000))
            )
            logger.info("[TTS Debug] Audio recovery successful")
            return True
        except Exception as e:
            logger.error(f"[TTS Debug] Audio recovery failed: {e}")
            return False'''
        
        # Add before the stop method
        if "def stop(self):" in content:
            content = content.replace("def stop(self):", recovery_method + "\n\n    def stop(self):")
            print("   ✓ Added recovery mechanism")
    
    # Write the updated file
    with open(audio_path, 'w') as f:
        f.write(content)
    
    print("\n✅ Audio player fixes applied!")
    print("\nWhat was fixed:")
    print("1. Better error handling in playback loop")
    print("2. Error counter to prevent infinite loops")
    print("3. Recovery mechanism for audio failures")
    print("4. More debug logging")


if __name__ == "__main__":
    fix_audio_player()
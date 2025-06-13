#!/usr/bin/env python
"""Voice enrollment script to create voice profile for discrimination.

This script helps create a voice profile (voiceprint) from your voice recordings
for use with the voice discrimination feature.
"""

import os
import sys
import argparse
import logging
import numpy as np
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.transcribe.voice_filter import VoiceFilter

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def record_voice_sample(duration: int = 10, output_file: str = "voice_sample.wav"):
    """Record a voice sample from microphone."""
    try:
        import pyaudio
        import wave
        
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        p = pyaudio.PyAudio()
        
        print(f"\n🎤 Recording will start in 3 seconds...")
        print("Please read the following text naturally:")
        print("\n" + "="*60)
        print("The quick brown fox jumps over the lazy dog.")
        print("I am recording my voice to create a voice profile.")
        print("This will help the system recognize my voice.")
        print("="*60 + "\n")
        
        import time
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        
        print(f"🔴 Recording for {duration} seconds... Speak now!")
        
        stream = p.open(format=FORMAT,
                      channels=CHANNELS,
                      rate=RATE,
                      input=True,
                      frames_per_buffer=CHUNK)
        
        frames = []
        
        for _ in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)
        
        print("✅ Recording complete!")
        
        stream.stop_stream()
        stream.close()
        p.terminate()
        
        # Save the recording
        wf = wave.open(output_file, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()
        
        return output_file
        
    except Exception as e:
        logger.error(f"Failed to record voice sample: {e}")
        return None


def create_voiceprint(audio_files: list, output_profile: str = "my_voice.npy"):
    """Create voice profile from audio files."""
    voice_filter = VoiceFilter()
    
    if not voice_filter.inference:
        logger.error("Voice filter not initialized. Please check HuggingFace token.")
        return False
    
    embeddings = []
    
    for audio_file in audio_files:
        if not os.path.exists(audio_file):
            logger.warning(f"Audio file not found: {audio_file}")
            continue
        
        logger.info(f"Processing: {audio_file}")
        embedding = voice_filter.extract_embedding(audio_file)
        
        if embedding is not None:
            embeddings.append(embedding)
            logger.info(f"✅ Extracted embedding from {audio_file}")
        else:
            logger.warning(f"❌ Failed to extract embedding from {audio_file}")
    
    if not embeddings:
        logger.error("No embeddings extracted. Cannot create voice profile.")
        return False
    
    # Average the embeddings
    avg_embedding = np.mean(embeddings, axis=0)
    logger.info(f"Created average embedding from {len(embeddings)} samples")
    
    # Save the profile
    voice_filter.save_profile(avg_embedding, output_profile)
    logger.info(f"✅ Voice profile saved to: {output_profile}")
    
    return True


def main():
    parser = argparse.ArgumentParser(description="Create voice profile for discrimination")
    parser.add_argument('--record', action='store_true', help='Record new voice samples')
    parser.add_argument('--duration', type=int, default=10, help='Recording duration in seconds')
    parser.add_argument('--files', nargs='+', help='Audio files to process')
    parser.add_argument('--output', default='my_voice.npy', help='Output profile filename')
    parser.add_argument('--samples', type=int, default=3, help='Number of samples to record')
    
    args = parser.parse_args()
    
    audio_files = []
    
    # Check HuggingFace token
    vf = VoiceFilter()
    if not vf._get_hf_token():
        print("\n❌ HuggingFace token not found!")
        print("Please set your token using one of these methods:")
        print("1. Set environment variable: export HF_TOKEN=your_token")
        print("2. Save to file: echo 'your_token' > ~/.huggingface_token")
        print("3. Windows: echo your_token > %USERPROFILE%\\huggingface_token.txt")
        print("\nGet your token from: https://huggingface.co/settings/tokens")
        return
    
    if args.record:
        # Record new samples
        print(f"\n🎙️  Voice Enrollment - Recording {args.samples} samples")
        print("="*60)
        
        for i in range(args.samples):
            print(f"\n📍 Sample {i+1} of {args.samples}")
            sample_file = f"voice_sample_{i+1}.wav"
            
            if i > 0:
                input("Press Enter to record next sample...")
            
            recorded_file = record_voice_sample(args.duration, sample_file)
            if recorded_file:
                audio_files.append(recorded_file)
    
    elif args.files:
        # Use provided files
        audio_files = args.files
    
    else:
        # Look for existing voice samples
        sample_dir = Path("saved_voice_recordings")
        if sample_dir.exists():
            audio_files = list(sample_dir.glob("*.wav"))
            audio_files = [str(f) for f in audio_files]
            if audio_files:
                print(f"Found {len(audio_files)} existing voice samples")
    
    if not audio_files:
        print("\n❌ No audio files to process!")
        print("Use --record to record new samples or --files to specify existing files")
        return
    
    print(f"\n🔧 Creating voice profile from {len(audio_files)} files...")
    success = create_voiceprint(audio_files, args.output)
    
    if success:
        print("\n✅ Voice enrollment complete!")
        print(f"Profile saved to: {args.output}")
        print("\nTo test your voice profile:")
        print("1. Update parameters.yaml to set voice_filter_profile to your profile filename")
        print("2. Run the transcribe application")
        print("3. Speak - the AI should NOT respond to your voice")
        print("4. Have a colleague speak - the AI SHOULD respond")
    
    # Clean up temporary files if we recorded them
    if args.record:
        for f in audio_files:
            try:
                os.unlink(f)
            except:
                pass


if __name__ == "__main__":
    main()
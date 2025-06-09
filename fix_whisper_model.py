#!/usr/bin/env python3
"""
Fix corrupted Whisper model by clearing cache and re-downloading
"""
import os
import shutil
import whisper

def fix_whisper_model():
    """Clear Whisper model cache and re-download"""
    
    # Get Whisper cache directory
    cache_dir = os.path.expanduser("~/.cache/whisper")
    
    print(f"🗑️  Clearing Whisper model cache at: {cache_dir}")
    
    # Remove cache directory if it exists
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print("✅ Cache cleared successfully")
    else:
        print("ℹ️  Cache directory doesn't exist")
    
    # Re-download the base model
    print("📥 Re-downloading Whisper base model...")
    try:
        model = whisper.load_model("base")
        print("✅ Whisper base model downloaded successfully")
        
        # Test the model
        print("🧪 Testing model...")
        # Create a dummy audio array for testing
        import numpy as np
        dummy_audio = np.zeros(16000, dtype=np.float32)  # 1 second of silence at 16kHz
        result = model.transcribe(dummy_audio)
        print("✅ Model test successful")
        
    except Exception as e:
        print(f"❌ Failed to download/test model: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🔧 Fixing Whisper model...")
    if fix_whisper_model():
        print("🎉 Whisper model fixed successfully!")
    else:
        print("💥 Failed to fix Whisper model")
#!/usr/bin/env python3
"""
Clear all Whisper and PyTorch caches completely
"""
import os
import shutil
import glob

def clear_all_caches():
    """Clear all possible cache locations"""
    
    cache_dirs = [
        "~/.cache/whisper",
        "~/.cache/torch",
        "~/.cache/huggingface", 
        "~/.torch",
        "/tmp/whisper*",
        "./whisper*"
    ]
    
    print("🧹 Clearing all Whisper and PyTorch caches...")
    
    for cache_pattern in cache_dirs:
        expanded_path = os.path.expanduser(cache_pattern)
        
        # Handle glob patterns
        if '*' in expanded_path:
            matching_paths = glob.glob(expanded_path)
            for path in matching_paths:
                if os.path.exists(path):
                    try:
                        if os.path.isdir(path):
                            shutil.rmtree(path)
                            print(f"✅ Removed directory: {path}")
                        else:
                            os.remove(path)
                            print(f"✅ Removed file: {path}")
                    except Exception as e:
                        print(f"⚠️  Could not remove {path}: {e}")
        else:
            if os.path.exists(expanded_path):
                try:
                    if os.path.isdir(expanded_path):
                        shutil.rmtree(expanded_path)
                        print(f"✅ Removed directory: {expanded_path}")
                    else:
                        os.remove(expanded_path)
                        print(f"✅ Removed file: {expanded_path}")
                except Exception as e:
                    print(f"⚠️  Could not remove {expanded_path}: {e}")
            else:
                print(f"ℹ️  Path does not exist: {expanded_path}")
    
    print("🎯 Forcing fresh Whisper model download...")
    
    # Force fresh download by removing environment variables that might cache paths
    env_vars_to_unset = ['WHISPER_CACHE_DIR', 'TORCH_HOME', 'XDG_CACHE_HOME']
    for var in env_vars_to_unset:
        if var in os.environ:
            del os.environ[var]
            print(f"🗑️  Unset environment variable: {var}")

if __name__ == "__main__":
    clear_all_caches()
    print("✨ All caches cleared! Try running the app again.")
#!/usr/bin/env python3
"""
Wrapper script to run Transcribe with ALSA warnings suppressed
"""
import os
import sys
import subprocess

def suppress_alsa_warnings():
    """Set environment variables to suppress ALSA/JACK warnings"""
    # Suppress ALSA warnings
    os.environ['ALSA_PCM_CARD'] = 'default'
    os.environ['ALSA_PCM_DEVICE'] = '0'
    
    # Suppress JACK warnings  
    os.environ['JACK_NO_AUDIO_RESERVATION'] = '1'
    
    # Redirect ALSA error output to /dev/null
    os.environ['LIBASOUND_THREAD_SAFE'] = '0'

def main():
    """Run the main transcribe application with suppressed warnings"""
    print("🎧 Starting Transcribe with WSL/ARM64 optimizations...")
    
    # Suppress ALSA warnings
    suppress_alsa_warnings()
    
    # Change to the app directory
    app_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app', 'transcribe')
    os.chdir(app_dir)
    
    # Run the main application
    try:
        # Use virtual environment python if available
        venv_python = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python3')
        python_exe = venv_python if os.path.exists(venv_python) else sys.executable
        print(f"Using Python: {python_exe}")
        
        # Redirect stderr to suppress ALSA warnings while keeping Python errors
        with open('/dev/null', 'w') as devnull:
            # Keep stdout for app output, redirect only ALSA stderr
            result = subprocess.run([
                python_exe, 'main.py'
            ], stderr=subprocess.PIPE, stdout=sys.stdout, text=True)
            
            # Only show stderr if it contains Python errors (not ALSA warnings)
            if result.stderr and not any(alsa_term in result.stderr.lower() 
                                       for alsa_term in ['alsa', 'jack', 'pulse', 'pcm']):
                print(result.stderr, file=sys.stderr)
                
    except KeyboardInterrupt:
        print("\n👋 Transcribe stopped by user")
    except Exception as e:
        print(f"❌ Error running Transcribe: {e}")

if __name__ == "__main__":
    main()
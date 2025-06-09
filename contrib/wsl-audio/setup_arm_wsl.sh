#!/bin/bash
# Setup script for Transcribe on ARM64/WSL2
# Run this script to configure audio for optimal performance on WSL

set -e

echo "🔧 Setting up Transcribe for ARM64/WSL2..."

# Create ALSA configuration to suppress warnings
echo "📢 Configuring ALSA to suppress warnings..."
if [ ! -f ~/.asoundrc ]; then
    cp contrib/wsl-audio/asoundrc ~/.asoundrc
    echo "✅ ALSA configuration installed at ~/.asoundrc"
else
    echo "⚠️  ~/.asoundrc already exists. Backup and merge manually if needed:"
    echo "   cp ~/.asoundrc ~/.asoundrc.backup"
    echo "   cp contrib/wsl-audio/asoundrc ~/.asoundrc"
fi

# Check if PulseAudio is running
echo "🔊 Checking PulseAudio status..."
if pgrep pulseaudio > /dev/null; then
    echo "✅ PulseAudio is running"
else
    echo "🚀 Starting PulseAudio..."
    pulseaudio --start --exit-idle-time=-1
    sleep 2
    if pgrep pulseaudio > /dev/null; then
        echo "✅ PulseAudio started successfully"
    else
        echo "❌ Failed to start PulseAudio. You may need to install it:"
        echo "   sudo apt update && sudo apt install pulseaudio"
    fi
fi

# Test audio devices
echo "🎤 Testing audio device access..."
python3 -c "
import sys
sys.path.append('sdk')
import audio_recorder as ar
try:
    print('Available input devices:')
    inputs, outputs = ar.list_audio_devices()
    for i, (idx, name) in enumerate(inputs):
        print(f'  {idx}: {name}')
    print(f'Total input devices: {len(inputs)}')
    print(f'Total output devices: {len(outputs)}')
    print('✅ Audio device enumeration successful')
except Exception as e:
    print(f'❌ Audio device test failed: {e}')
    sys.exit(1)
"

echo "
🎉 Setup complete! 

📋 Next steps:
1. Update your override.yaml with the correct OpenAI API key
2. Run the application: cd app/transcribe && python3 main.py
3. If you see ALSA warnings, restart your terminal and try again

🔧 Troubleshooting:
- For speaker recording on WSL, you may need to configure Windows audio loopback
- Check available devices in the app startup output to verify your mic selection
- Enable Windows Subsystem for Linux audio in Windows settings

📖 See README for additional ARM64/WSL specific configuration details.
"
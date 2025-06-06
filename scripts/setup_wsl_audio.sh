#!/usr/bin/env bash
set -e

# Install pulseaudio and ALSA utilities if they aren't installed
if ! dpkg -s pulseaudio >/dev/null 2>&1; then
    echo "=== Installing PulseAudio and ALSA utilities ==="
    sudo apt-get update
    sudo apt-get install -y pulseaudio alsa-utils
fi


# WSL's default kernel does not provide the ALSA loopback module (snd_aloop),
# so we rely solely on PulseAudio to bridge audio between Windows and Linux.

# Start PulseAudio
pulseaudio --check || pulseaudio --start
sleep 1

# Export PulseAudio server address for Windows interoperability
export PULSE_SERVER=tcp:localhost:4713

echo "PulseAudio started with server $PULSE_SERVER"


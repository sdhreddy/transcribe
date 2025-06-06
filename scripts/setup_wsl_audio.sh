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

# 'snd_aloop' is not available in the default WSL kernel; skip loading it

# Load ALSA loopback module
if ! lsmod | grep -q snd_aloop; then
    echo "=== Loading ALSA loopback module ==="
    sudo modprobe snd_aloop
fi



# Start PulseAudio
pulseaudio --check || pulseaudio --start
sleep 1




# Export PulseAudio server address for Windows interoperability
export PULSE_SERVER=tcp:localhost:4713

echo "PulseAudio started with server $PULSE_SERVER"


# Configure PulseAudio loopback sink and source
pactl list short modules | grep -q module-alsa-sink || \
    pacmd load-module module-alsa-sink device="hw:Loopback,0,0"
pactl list short modules | grep -q module-alsa-source || \
    pacmd load-module module-alsa-source device="hw:Loopback,1,0"

# Set default sink and source to loopback
if pacmd list-sinks | grep -q "alsa_output.hw_Loopback_0_0"; then
    pacmd set-default-sink alsa_output.hw_Loopback_0_0 || true
fi
if pacmd list-sources | grep -q "alsa_input.hw_Loopback_1_0"; then
    pacmd set-default-source alsa_input.hw_Loopback_1_0 || true
fi

# Verify loopback device exists
if arecord -l | grep -qi Loopback && aplay -l | grep -qi Loopback; then
    echo "Loopback audio device is configured."
else
    echo "Failed to configure loopback audio device." >&2
    exit 1
fi

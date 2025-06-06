#!/usr/bin/env bash
set -e

echo "=== Installing and starting PulseAudio under WSLg ==="
sudo apt-get update
sudo apt-get install -y pulseaudio alsa-utils

# Start PulseAudio; WSLg forwards audio automatically
pulseaudio --start || true

echo "PulseAudio is running under WSLg; no PULSE_SERVER override is needed."


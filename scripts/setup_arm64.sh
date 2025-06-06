#!/usr/bin/env bash
set -e

echo "=== Installing ARM64/Ubuntu system packages ==="
sudo apt-get update && sudo apt-get install -y \
    python3-venv python3-pip python3-tk portaudio19-dev \
    ffmpeg build-essential libssl-dev libffi-dev \
    libatlas-base-dev libasound2-dev libportaudio2 \
    libportaudiocpp0 tk

echo "=== Create and activate Python virtual environment ==="
python3 -m venv venv
source venv/bin/activate

echo "=== Upgrade pip, setuptools, and wheel ==="
pip install --upgrade pip setuptools wheel

echo "=== Install Python dependencies ==="
pip install --upgrade -r requirements.txt


echo "=== Install testing dependencies ==="
pip install --upgrade pytest pytest-cov pytest-mock


echo "=== Setup complete! Run 'source venv/bin/activate' to activate your env ==="

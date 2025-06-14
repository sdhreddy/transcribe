#!/bin/bash
# Start transcribe with proper environment setup

# Change to the transcribe directory
cd /home/sdhre/transcribe

# Load HuggingFace token
export HUGGINGFACE_TOKEN=$(cat /home/sdhre/.huggingface_token)

# Set Claude Opus 4 model
export ANTHROPIC_MODEL=claude-opus-4-20250514

# Activate virtual environment
source venv/bin/activate

# Add current directory to Python path for pytorch_patch
export PYTHONPATH=/home/sdhre/transcribe:$PYTHONPATH

# Change to app/transcribe directory where parameters.yaml is located
cd app/transcribe

# Start the transcribe application
python3 main.py "$@"

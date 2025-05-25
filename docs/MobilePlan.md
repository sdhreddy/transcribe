# Mobile Strategy

This project does not yet provide a full mobile implementation. The recommended approach is to reuse the FastAPI backend and build a React Native client.

## Approach 1: React Native
- Share much of the web client code.
- Use the backend API for transcription, TTS, and settings.
- Bundle minimal native modules for microphone access.

## Approach 2: Flutter
- Build a Flutter application using platform channels for audio streaming.
- Communicate with the FastAPI backend for model inference.

Model files are heavy and typically remain on the server. Mobile apps stream audio to the server and receive transcription and responses.

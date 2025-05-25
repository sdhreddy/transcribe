# Web Architecture

This document describes the web implementation of Transcribe. The web version reuses the
existing Python backend and exposes a modern React interface.

## Backend

- **Framework**: FastAPI
- **Endpoints**:
  - `POST /api/transcribe` – speech‑to‑text using the `whisper` library.
  - `POST /api/tts` – text‑to‑speech using `gtts` and returned as an MP3 stream.
  - `POST /api/chat` – chat completion via the OpenAI client.
  - `GET /api/models` – list available STT models.
  - `GET/POST /api/settings/{key}` – persist settings in a SQLite DB.
  - `WS /ws` – simple WebSocket interface for streaming.

Heavy AI models remain on the server so the browser only streams audio and receives
results. This keeps the client lightweight and works on mobile devices.

## Frontend

- **Framework**: React with Vite (see `package.json`).
- Uses the MediaRecorder API for microphone capture.
- Displays transcription results and chat history and offers basic playback
  using the HTML5 `Audio` element.
- Settings such as selected STT model are saved through the backend API and loaded on start.
- Responsive CSS ensures usability on phones and desktops.

## Deployment

A multi‑stage `Dockerfile` builds both backend and frontend. For local development:

```bash
python -m pip install -r requirements.txt
cd web/client && npm install
uvicorn web.server:app --reload
# in another terminal
cd web/client && npm run start
```

For container deployment:

```bash
docker compose up --build
```

This serves the application on port `8000` with the static React build.

## Mobile

A minimal Android app can be built with React Native reusing most of the web
code. The mobile client streams audio to the same FastAPI backend for inference
and receives transcription, chat responses and MP3 playback URLs.

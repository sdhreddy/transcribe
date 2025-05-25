# Web Version Setup

This document describes how to run the Transcribe web application locally.

## Prerequisites
- Python 3.11+
- Node.js 20+
- npm
- ffmpeg installed and available in your PATH

## Setup Steps
1. Install Python dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```
2. Install JavaScript dependencies:
   ```bash
   cd web/client
   npm install
   ```
3. Start the FastAPI server and React dev server:
   ```bash
   # From repository root
   uvicorn web.server:app --reload
   # In another terminal
   cd web/client && npm run start
   ```

The React app will proxy API requests to the FastAPI backend running on port 8000.

## Docker
You can also build and run using Docker:
```bash
docker compose up --build
```
This builds the backend and frontend images and serves the app on `http://localhost:8000`.

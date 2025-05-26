from fastapi import (
    FastAPI,
    WebSocket,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Form,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import tempfile
import os
import io
import whisper
import gtts
import openai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "sqlite:///./web_settings.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Simple settings table using SQLAlchemy
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Setting(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(String)

Base.metadata.create_all(bind=engine)

STT_MODELS = [
    "tiny",
    "base",
    "small",
    "medium",
    "large",
]

# Dependency to get DB session

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/settings/{key}")
async def read_setting(key: str, db=Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if not setting:
        raise HTTPException(status_code=404, detail="Setting not found")
    return {"key": setting.key, "value": setting.value}

@app.post("/api/settings/{key}")
async def write_setting(key: str, value: str, db=Depends(get_db)):
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        setting.value = value
    else:
        setting = Setting(key=key, value=value)
        db.add(setting)
    db.commit()
    return {"key": setting.key, "value": setting.value}

# Speech to text using whisper
@app.post("/api/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...), model: str = Form("base")
):
    """Transcribe uploaded audio using whisper."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    model_obj = whisper.load_model(model)
    result = model_obj.transcribe(tmp_path)
    os.remove(tmp_path)
    return {"text": result.get("text", "")}


@app.get("/api/models")
async def list_models():
    """Return available speech to text models."""
    return {"models": STT_MODELS}


@app.post("/api/tts")
async def text_to_speech(text: str = Form(...), lang: str = Form("en")):
    """Convert text to speech and return mp3 data."""
    tts = gtts.gTTS(text, lang=lang)
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tts.save(tmp.name)
        with open(tmp.name, "rb") as af:
            audio_bytes = af.read()
    os.remove(tmp.name)
    return StreamingResponse(io.BytesIO(audio_bytes), media_type="audio/mpeg")


@app.post("/api/chat")
async def chat(message: str = Form(...), model: str = Form("gpt-3.5-turbo")):
    """Simple chat endpoint using OpenAI LLM."""
    client = openai.OpenAI()
    completion = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": message}],
    )
    text = completion.choices[0].message.content
    return {"text": text}

# WebSocket echo server for streaming
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except Exception:
        await websocket.close()

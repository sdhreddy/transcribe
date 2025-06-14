# app/transcribe/streaming_tts.py
import abc
import typing as T
import queue
import threading
import pyaudio
import io
import wave
from dataclasses import dataclass
import os

@dataclass
class TTSConfig:
    provider: str = "openai"          # configurable
    voice: str = "alloy"              # configurable
    sample_rate: int = 24_000         # configurable
    api_key: str | None = None

class BaseTTS(abc.ABC):
    def __init__(self, cfg: TTSConfig):
        self.cfg = cfg

    @abc.abstractmethod
    def stream(self, text: str) -> T.Iterable[bytes]:
        """Yield raw 16-bit little-endian PCM chunks."""

# ---------- OpenAI -----------------------------------------------------------------

class OpenAITTS(BaseTTS):
    def __init__(self, cfg):
        super().__init__(cfg)
        from openai import OpenAI
        self.client = OpenAI(api_key=cfg.api_key or os.getenv("OPENAI_API_KEY"))

    def stream(self, text: str):
        # OpenAI TTS - note: OpenAI doesn't support a 'stream' parameter
        # but the response can be iterated for chunks
        resp = self.client.audio.speech.create(
            model="tts-1",
            voice=self.cfg.voice,
            input=text,
            response_format="pcm",    # raw PCM for immediate playback
            stream=True               # Enable streaming response
        )
        
        # The response supports chunk iteration via iter_bytes()
        for chunk in resp.iter_bytes(chunk_size=4096):
            # Each chunk is bytes containing raw 16-bit PCM audio
            yield chunk

# ---------- GTTS Fallback (non-streaming but compatible) ---------------------------

class GTTS_TTS(BaseTTS):
    def __init__(self, cfg):
        super().__init__(cfg)
        import gtts
        self.gtts = gtts

    def stream(self, text: str):
        # GTTS doesn't support streaming, so we generate the full audio
        # and yield it in chunks to maintain interface compatibility
        import tempfile
        import subprocess
        
        audio_obj = self.gtts.gTTS(text, lang='en')
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as tmp:
            audio_obj.save(tmp.name)
            
            # Convert MP3 to raw PCM using ffmpeg
            cmd = [
                'ffmpeg', '-i', tmp.name,
                '-f', 's16le',  # 16-bit little-endian
                '-acodec', 'pcm_s16le',
                '-ar', str(self.cfg.sample_rate),
                '-ac', '1',  # mono
                '-'  # output to stdout
            ]
            
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            
            # Yield audio in chunks
            while True:
                chunk = proc.stdout.read(4096)
                if not chunk:
                    break
                yield chunk
            
            proc.wait()
            os.unlink(tmp.name)

# ---------- Coqui XTTS --------------------------------------------------------------

class CoquiTTS(BaseTTS):
    def __init__(self, cfg):
        super().__init__(cfg)
        try:
            from TTS.api import TTS
            self.tts = TTS(model_name="tts_models/multilingual/xtts_v2")
            self.speaker_wav = "samples/voice.wav"   # optional reference
        except ImportError:
            raise ImportError("Coqui TTS not installed. Use 'pip install TTS'")

    def stream(self, text: str):
        gen = self.tts.inference_stream(
            text, 
            speaker_wav=self.speaker_wav,
            stream_chunk_size=2048  # reduce first-chunk delay
        )
        for wav_bytes in gen:
            yield wav_bytes

# ---------- Factory ----------------------------------------------------------------

def create_tts(cfg: TTSConfig) -> BaseTTS:
    if cfg.provider == "coqui":
        return CoquiTTS(cfg)
    elif cfg.provider == "gtts":
        return GTTS_TTS(cfg)
    return OpenAITTS(cfg)
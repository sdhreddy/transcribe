from __future__ import annotations

"""Streaming Text-to-Speech helpers.

This module provides a small abstraction layer so the application can
consume real-time audio chunks from multiple TTS providers in a unified
way.  The public contract is the `StreamingTTS` base-class – call
`StreamingTTSFactory.create(config)` to obtain the concrete
implementation and then iterate over ``stream(text)`` to receive raw
16-bit little-endian PCM audio frames suitable for immediate playback
via PyAudio.

Only OpenAI's ``tts-1`` model is implemented at the moment; a Coqui
XTTS implementation stub is provided and will raise
``NotImplementedError`` until completed.

All providers are expected to:
  • honour *sample_rate* supplied in the YAML config
  • return **mono** audio in 16-bit LE format (the current audio player
    opens the PyAudio stream in this format)
  • yield reasonably small chunks (≈50–100 ms) to keep latency low.

Example
-------
>>> cfg = yaml.safe_load(open('parameters.yaml'))
>>> tts = StreamingTTSFactory.create(cfg['General'])
>>> for chunk in tts.stream("Hello there!"):
...     pyaudio_stream.write(chunk)
"""

from typing import Iterable, Generator, Optional
import importlib
import logging
import inspect

logger = logging.getLogger(__name__)

try:
    # Newer OpenAI SDK (>=1.12) renamed the entry-point to `openai`
    openai = importlib.import_module("openai")
except ModuleNotFoundError:  # pragma: no cover – handled at runtime
    openai = None  # type: ignore

__all__ = [
    "StreamingTTS",
    "OpenAITTS",
    "CoquiTTS",
    "StreamingTTSFactory",
]


class StreamingTTS:
    """Base-class for streaming TTS back-ends."""

    def __init__(self, *, voice: str, sample_rate: int) -> None:
        self.voice = voice
        self.sample_rate = sample_rate

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def stream(self, text: str) -> Iterable[bytes]:
        """Yield PCM16LE audio chunks for *text*.
        Concrete subclasses must implement this method.
        """
        raise NotImplementedError


class OpenAITTS(StreamingTTS):
    """OpenAI ``tts-1`` streaming implementation."""

    def __init__(self, *, api_key: str, base_url: Optional[str], model: str,
                 voice: str, sample_rate: int) -> None:
        super().__init__(voice=voice, sample_rate=sample_rate)
        if openai is None:
            raise RuntimeError("openai SDK is not installed – add it to requirements.txt")

        # Create a lightweight client – this avoids touching global openai.api_key
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url) if base_url else openai.OpenAI(api_key=api_key)
        self._model = model

    def stream(self, text: str) -> Generator[bytes, None, None]:
        logger.debug("[OpenAITTS] Requesting streaming audio (len=%d)", len(text))

        sig = inspect.signature(self._client.audio.speech.create)

        # Determine correct parameter names across SDK versions
        fmt_key = "response_format" if "response_format" in sig.parameters else ("format" if "format" in sig.parameters else None)
        sr_key = "sample_rate" if "sample_rate" in sig.parameters else ("sampling_rate" if "sampling_rate" in sig.parameters else None)

        kwargs = {
            "model": self._model,
            "voice": self.voice,
            "input": text,
            "response_format": "pcm",  # OpenAI expects 'pcm' not 'pcm16'
        }
        # Note: OpenAI doesn't support custom sample rates for TTS
        # It always returns 24kHz for pcm16 format

        supports_stream = "stream" in sig.parameters
        if supports_stream:
            kwargs["stream"] = True

        try:
            response = self._client.audio.speech.create(**kwargs)
        except TypeError as e:
            # Fallback for SDKs that *unexpectedly* reject 'stream'
            if "unexpected keyword argument 'stream'" in str(e):
                kwargs.pop("stream", None)
                response = self._client.audio.speech.create(**kwargs)
            else:
                raise

        # ------------------------------------------------------------------
        # Handle response types across SDK versions
        # ------------------------------------------------------------------
        # 1. Streaming generator (preferred)
        if hasattr(response, "__iter__") and not isinstance(response, (bytes, bytearray)):
            for chunk in response:
                audio_bytes = getattr(chunk, "audio", None)
                if not audio_bytes:
                    continue
                yield audio_bytes
            return

        # 2. Object with .iter_bytes() helper
        if hasattr(response, "iter_bytes"):
            for b in response.iter_bytes():
                yield b
            return

        # 3. Flat bytes payload – chunk manually to ~50 ms (≈2400 frames @ 24 kHz * 2 bytes)
        if isinstance(response, (bytes, bytearray)):
            chunk_size = int(self.sample_rate * 0.05) * 2  # 50 ms, 16-bit mono
            for i in range(0, len(response), chunk_size):
                yield response[i : i + chunk_size]
            return

        # 4. Unexpected type – log and bail
        logger.error("[OpenAITTS] Unsupported response type: %s", type(response))


class CoquiTTS(StreamingTTS):
    """Coqui XTTS streaming implementation (stub)."""

    def __init__(self, *, voice: str, sample_rate: int, **kwargs) -> None:  # noqa: D401,E501 – signature flexibility
        super().__init__(voice=voice, sample_rate=sample_rate)
        # The real implementation requires the Coqui-AI SDK which is not yet
        # part of transcribe's dependency set.  Raise for now so callers know
        # the feature is unavailable.
        raise NotImplementedError("Coqui XTTS streaming not implemented yet – set tts_provider: openai")

    def stream(self, text: str) -> Iterable[bytes]:  # pragma: no cover
        raise NotImplementedError


# -------------------------------------------------------------------------
# Factory helper
# -------------------------------------------------------------------------

class StreamingTTSFactory:
    """Create provider-specific `StreamingTTS` instances from YAML config."""

    @staticmethod
    def create(config: dict) -> StreamingTTS:
        general_cfg = config.get("General", {})
        provider = general_cfg.get("tts_provider", "openai").lower()
        voice = general_cfg.get("tts_voice", "alloy")
        sample_rate = int(general_cfg.get("tts_sample_rate", 24000))

        if provider == "openai":
            openai_cfg = config.get("OpenAI", {})
            api_key = openai_cfg.get("api_key")
            base_url = openai_cfg.get("base_url")
            model = "tts-1"  # currently hard-coded, could be made configurable
            if not api_key:
                raise ValueError("OpenAI API key missing in parameters.yaml -> OpenAI: api_key")
            return OpenAITTS(api_key=api_key, base_url=base_url, model=model,
                             voice=voice, sample_rate=sample_rate)

        if provider == "coqui":
            return CoquiTTS(voice=voice, sample_rate=sample_rate)

        raise ValueError(f"Unsupported tts_provider '{provider}'. Expected 'openai' or 'coqui'.") 
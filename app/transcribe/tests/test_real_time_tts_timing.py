import time
import threading
from unittest.mock import MagicMock

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.transcribe.audio_player import AudioPlayer
from app.transcribe.global_vars import TranscriptionGlobals


def test_real_time_tts_timing(monkeypatch):
    ctx = TranscriptionGlobals()
    ctx.audio_queue = MagicMock()
    ctx.audio_queue.empty.return_value = True
    ctx.speaker_audio_recorder = MagicMock()
    ctx.speaker_audio_recorder.enabled = True

    convo = MagicMock()
    convo.context = ctx

    player = AudioPlayer(convo)
    timings = []

    def fake_play_audio(speech, lang, rate):
        timings.append((speech, time.time()))

    monkeypatch.setattr(player, "play_audio", fake_play_audio)

    config = {
        "General": {"tts_speech_rate": 1.0},
        "OpenAI": {"response_lang": "english"},
    }

    thread = threading.Thread(target=player.play_audio_loop, args=(config,))
    thread.start()

    start = time.time()
    for chunk, delay in [("This is ", 0.0), ("a test ", 0.1), ("of streaming.", 0.2)]:
        time.sleep(delay)
        player.enqueue_chunk(chunk)

    time.sleep(0.5)
    player.stop_loop = True
    thread.join(timeout=1)

    arrival_times = [start + 0.0, start + 0.1, start + 0.2]
    assert len(timings) == 3
    for (speech, play_time), arrival in zip(timings, arrival_times):
        assert play_time - arrival < 0.2

    for i in range(1, len(timings)):
        assert timings[i][1] - timings[i - 1][1] < 0.4

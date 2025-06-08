import os
import os
import sys
import logging
import types
import pytest
import custom_speech_recognition as sr_module

BASE_DIR = os.path.join(os.path.dirname(__file__), '..')
sys.path.append(BASE_DIR)

from sdk import audio_recorder


class DummyMicrophone:
    def __init__(self, *args, **kwargs):
        self.device_index = kwargs.get('device_index', 0)
        self.SAMPLE_RATE = int(kwargs.get('sample_rate', 44100))
        self.SAMPLE_WIDTH = 2
        self.channels = kwargs.get('channels', 1)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


class FakePA:
    def __init__(self, has_devices=True):
        self.has_devices = has_devices

    def get_device_count(self):
        return 1 if self.has_devices else 0

    def get_device_info_by_index(self, index):
        return {
            'index': index,
            'name': f'Dev{index}',
            'maxInputChannels': 1,
            'maxOutputChannels': 1,
            'isLoopbackDevice': True,
            'defaultSampleRate': 44100,
        }

    def get_default_input_device_info(self):
        raise IOError()

    def get_host_api_info_by_type(self, typ):
        return {'defaultOutputDevice': 0}

    def get_loopback_device_info_generator(self):
        yield {
            'index': 0,
            'name': 'Dev0',
            'isLoopbackDevice': True,
            'maxInputChannels': 1,
            'defaultSampleRate': 44100,
        }

    def terminate(self):
        pass


def test_list_audio_devices_logs(caplog, monkeypatch):
    monkeypatch.setattr(audio_recorder, 'pyaudio', types.SimpleNamespace(PyAudio=lambda: FakePA(), paWASAPI=0, get_sample_size=lambda fmt: 2, paInt16=1))
    caplog.set_level(logging.INFO)
    inputs, outputs = audio_recorder.list_audio_devices()
    assert inputs == [(0, 'Dev0')]
    assert outputs == [(0, 'Dev0')]
    assert 'Available input devices' in caplog.text
    assert 'Available output devices' in caplog.text


def test_initialization_success(monkeypatch):
    monkeypatch.setattr(audio_recorder, 'pyaudio', types.SimpleNamespace(PyAudio=lambda: FakePA(), paWASAPI=0, get_sample_size=lambda fmt: 2, paInt16=1))
    monkeypatch.setattr(sr_module, 'Microphone', DummyMicrophone)
    monkeypatch.setattr(sr_module.Recognizer, 'adjust_for_ambient_noise', lambda self, source, duration=1: None)
    class DummyConfig:
        def __init__(self):
            self.data = {'General': {'transcript_audio_duration_seconds': 1}}
    monkeypatch.setattr(audio_recorder.configuration, 'Config', DummyConfig)
    monkeypatch.setattr(audio_recorder, 'sr', sr_module)
    mic = audio_recorder.MicRecorder()
    speaker = audio_recorder.SpeakerRecorder()
    assert mic.device_info['name'] == 'Dev0'
    assert speaker.device_info['name'] == 'Dev0'


def test_no_devices(monkeypatch):
    monkeypatch.setattr(audio_recorder, 'pyaudio', types.SimpleNamespace(PyAudio=lambda: FakePA(has_devices=False), paWASAPI=0, get_sample_size=lambda fmt: 2, paInt16=1))
    monkeypatch.setattr(sr_module, 'Microphone', DummyMicrophone)
    monkeypatch.setattr(sr_module.Recognizer, 'adjust_for_ambient_noise', lambda self, source, duration=1: None)
    class DummyConfig:
        def __init__(self):
            self.data = {'General': {'transcript_audio_duration_seconds': 1}}
    monkeypatch.setattr(audio_recorder.configuration, 'Config', DummyConfig)
    monkeypatch.setattr(audio_recorder, 'sr', sr_module)
    with pytest.raises(RuntimeError):
        audio_recorder.MicRecorder()

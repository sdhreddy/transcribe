import os
import sys
import importlib.util

test_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..')))
sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..', '..', '..')))

from tsutils import configuration
configuration.Config.__init__ = lambda self, *a, **k: None
configuration.Config._current_data = {
    'General': {
        'disable_mic': False,
        'mic_device_index': -1,
        'disable_speaker': False,
        'speaker_device_index': -1,
        'llm_response_interval': 10,
        'system_prompt': 'test',
        'initial_convo': {}
    },
    'OpenAI': {'audio_lang': 'english', 'response_lang': 'english'}
}
module_path = os.path.join(test_dir, '..', 'global_vars.py')
sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..')))
sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..', '..')))
sys.path.insert(0, os.path.abspath(os.path.join(test_dir, '..', '..', '..')))
spec = importlib.util.spec_from_file_location('global_vars', module_path)
gv_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gv_mod)
TranscriptionGlobals = gv_mod.TranscriptionGlobals
import pytest


def test_initiate_audio_devices_skips_on_wsl_error(monkeypatch, tmp_path):
    import sdk.audio_recorder as ar
    # Simulate MicRecorder raising an exception when instantiated
    def _raise(*args, **kwargs):
        raise Exception("no device")
    monkeypatch.setattr(ar, 'MicRecorder', _raise)
    gv = TranscriptionGlobals()
    config = {'General': {'disable_mic': False,
                          'mic_device_index': -1,
                          'disable_speaker': False,
                          'speaker_device_index': -1}}
    gv.initiate_audio_devices(config)
    assert gv.user_audio_recorder is None
    assert gv.speaker_audio_recorder is None

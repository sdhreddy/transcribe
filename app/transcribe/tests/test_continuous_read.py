import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from tsutils import configuration
configuration.Config.__init__ = lambda self, *a, **k: None
configuration.Config._current_data = {
    'General': {
        'llm_response_interval': 10,
        'system_prompt': 'test',
        'initial_convo': {}
    },
    'OpenAI': {'audio_lang': 'english', 'response_lang': 'english'}
}
from app.transcribe.appui import AppUI
from tsutils.configuration import Config


@unittest.skipIf('DISPLAY' not in os.environ, 'requires display')
class TestContinuousRead(unittest.TestCase):
    @patch.object(Config, 'add_override_value')
    def test_toggle_updates_config(self, mock_add):
        config = {
            'General': {
                'continuous_read': False,
                'continuous_response': False,
                'llm_response_interval': 10
            },
            'OpenAI': {
                'audio_lang': 'english',
                'response_lang': 'english'
            }
        }
        Config._current_data = config
        ui = AppUI(config=config)
        ui.global_vars.audio_player_var = MagicMock()
        ui.continuous_read_button.select()
        ui.toggle_continuous_read()
        mock_add.assert_called_with({'General': {'continuous_read': True}})

    def test_tts_trigger_once(self):
        from app.transcribe import appui
        Config._current_data = {
            'General': {'llm_response_interval': 10},
            'OpenAI': {'audio_lang': 'english', 'response_lang': 'english'}
        }
        gv = appui.global_vars_module = appui.TranscriptionGlobals()
        gv.audio_player_var = MagicMock()
        gv.continuous_read = True
        gv.last_tts_response = ""
        gv.last_spoken_response = ""
        responder = MagicMock()
        responder.response = "assistant: [hi]"
        responder.streaming_complete.is_set.return_value = True
        textbox = MagicMock()
        label = MagicMock()
        slider = MagicMock()
        slider.get.return_value = 10
        appui.update_response_ui(responder, textbox, label, slider)
        responder.streaming_complete.is_set.return_value = False
        appui.update_response_ui(responder, textbox, label, slider)
        self.assertEqual(gv.audio_player_var.speech_text_available.set.call_count, 1)

if __name__ == "__main__":
    unittest.main()


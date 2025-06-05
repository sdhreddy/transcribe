import unittest
from unittest.mock import patch, MagicMock
import sys
import os
from types import ModuleType

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.modules["pyaudiowpatch"] = ModuleType("pyaudiowpatch")
from tsutils import configuration

configuration.Config.__init__ = lambda self, *a, **k: None
from app.transcribe.appui import AppUI
from tsutils.configuration import Config


@unittest.skipIf("DISPLAY" not in os.environ, "requires display")
class TestContinuousResponse(unittest.TestCase):
    @patch.object(Config, "add_override_value")
    def test_toggle_without_read(self, mock_add):
        config = {
            "General": {
                "continuous_read": False,
                "continuous_response": False,
                "llm_response_interval": 10,
                "chat_inference_provider": "openai",
                "system_prompt": "test",
                "initial_convo": {},
            },
            "OpenAI": {
                "audio_lang": "english",
                "response_lang": "english",
                "api_key": "x",
                "base_url": "y",
                "ai_model": "z",
            },
        }
        Config._current_data = config
        ui = AppUI(config=config)
        ui.global_vars.audio_player_var = MagicMock()
        ui.global_vars.responder = MagicMock()
        ui.global_vars.responder.enabled = False
        ui.freeze_unfreeze()
        self.assertTrue(ui.global_vars.responder.enabled)
        mock_add.assert_called_with({"General": {"continuous_response": True}})
        ui.freeze_unfreeze()
        self.assertFalse(ui.global_vars.responder.enabled)
        self.assertEqual(
            mock_add.call_args_list[-1].args[0],
            {"General": {"continuous_response": False}},
        )

    @patch.object(Config, "add_override_value")
    def test_toggle_with_read_enabled(self, mock_add):
        config = {
            "General": {
                "continuous_read": True,
                "continuous_response": False,
                "llm_response_interval": 10,
                "chat_inference_provider": "openai",
                "system_prompt": "test",
                "initial_convo": {},
            },
            "OpenAI": {
                "audio_lang": "english",
                "response_lang": "english",
                "api_key": "x",
                "base_url": "y",
                "ai_model": "z",
            },
        }
        Config._current_data = config
        ui = AppUI(config=config)
        ui.global_vars.audio_player_var = MagicMock()
        ui.global_vars.responder = MagicMock()
        ui.global_vars.responder.enabled = False
        ui.continuous_read_button.select()
        ui.toggle_continuous_read()
        ui.freeze_unfreeze()
        self.assertTrue(ui.global_vars.responder.enabled)
        mock_add.assert_any_call({"General": {"continuous_response": True}})
        ui.freeze_unfreeze()
        self.assertFalse(ui.global_vars.responder.enabled)
        self.assertEqual(
            mock_add.call_args_list[-1].args[0],
            {"General": {"continuous_response": False}},
        )


if __name__ == "__main__":
    unittest.main()

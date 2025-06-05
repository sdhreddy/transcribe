import unittest
from unittest.mock import MagicMock, call

import sys
import os
from types import ModuleType

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.modules["pyaudiowpatch"] = ModuleType("pyaudiowpatch")

from app.transcribe.gpt_responder import GPTResponder


class FakeChunk:
    def __init__(self, text):
        class Delta:
            def __init__(self, content):
                self.content = content

        self.choices = [type("Obj", (), {"delta": Delta(text)})]


class TestStreamingTTS(unittest.TestCase):
    def setUp(self):
        self.context = MagicMock()
        self.context.continuous_read = True
        self.context.update_response_now = False
        self.context.audio_player_var = MagicMock()

        self.convo = MagicMock()
        self.convo.context = self.context
        config = {
            "General": {"llm_response_interval": 10, "continuous_response": True},
            "OpenAI": {"response_lang": "english"},
        }
        self.responder = GPTResponder(
            config=config, convo=self.convo, file_name="x", openai_module=MagicMock()
        )
        self.responder.enabled = True
        self.responder.llm_client = MagicMock()
        self.responder.model = "gpt"

    def test_enqueue_chunks_when_streaming(self):
        stream = [FakeChunk("Hello "), FakeChunk("world! How "), FakeChunk("are you?")]
        self.responder.llm_client.chat.completions.create.return_value = stream
        result = self.responder._get_llm_response([], 0.5, 30)
        self.assertEqual(result, "Hello world! How are you?")
        self.context.audio_player_var.enqueue_chunk.assert_has_calls(
            [call("Hello "), call("world! How "), call("are you?")]
        )

    def test_no_enqueue_when_manual(self):
        self.context.update_response_now = True
        stream = [FakeChunk("Hello "), FakeChunk("world!")]
        self.responder.llm_client.chat.completions.create.return_value = stream
        self.context.audio_player_var.enqueue_chunk.reset_mock()
        self.responder._get_llm_response([], 0.5, 30)
        self.assertFalse(self.context.audio_player_var.enqueue_chunk.called)

    def test_mode_a_no_audio(self):
        self.context.continuous_read = False
        self.context.update_response_now = True
        self.responder.enabled = False
        stream = [FakeChunk("Hi"), FakeChunk(" there")]
        self.responder.llm_client.chat.completions.create.return_value = stream
        self.responder._get_llm_response([], 0.5, 30)
        self.assertFalse(self.context.audio_player_var.enqueue_chunk.called)

    def test_mode_c_src_on_read_off(self):
        self.context.continuous_read = False
        self.context.update_response_now = False
        self.responder.enabled = True
        stream = [FakeChunk("Hello"), FakeChunk(" world")]
        self.responder.llm_client.chat.completions.create.return_value = stream
        self.context.audio_player_var.enqueue_chunk.reset_mock()
        self.responder._get_llm_response([], 0.5, 30)
        self.assertFalse(self.context.audio_player_var.enqueue_chunk.called)

    def test_mode_d_src_on_rrc_on(self):
        self.context.continuous_read = True
        self.context.update_response_now = False
        self.responder.enabled = True
        stream = [FakeChunk("Hello "), FakeChunk("world!")]
        self.responder.llm_client.chat.completions.create.return_value = stream
        self.context.audio_player_var.enqueue_chunk.reset_mock()
        self.responder._get_llm_response([], 0.5, 30)
        self.context.audio_player_var.enqueue_chunk.assert_has_calls(
            [call("Hello "), call("world!")]
        )


if __name__ == "__main__":
    unittest.main()

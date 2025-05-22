import unittest
from unittest.mock import MagicMock, patch
import threading

from app.transcribe.gpt_responder import GPTResponder


class TestGPTResponderReadContinuous(unittest.TestCase):
    def setUp(self):
        self.config = {
            'General': {
                'llm_response_interval': 1,
                'chat_inference_provider': 'openai',
                'read_continuous_response': True
            },
            'OpenAI': {
                'api_key': 'key',
                'base_url': 'url',
                'ai_model': 'model',
                'response_request_timeout_seconds': 10,
                'summarize_request_timeout_seconds': 30,
                'temperature': 0.0
            }
        }

        self.context = MagicMock()
        self.context.audio_player_var = MagicMock()
        self.context.audio_player_var.speech_text_available = threading.Event()

        self.convo = MagicMock()
        self.convo.context = self.context

        self.responder = GPTResponder(config=self.config, convo=self.convo, file_name='file', save_to_file=False)
        self.responder.enabled = True

    @patch.object(GPTResponder, 'generate_response_from_transcript_no_check', return_value='hi')
    def test_read_continuous_response_sets_event(self, mock_gen):
        self.responder.generate_response_from_transcript()
        self.context.set_read_response.assert_called_with(True)
        self.assertTrue(self.context.audio_player_var.speech_text_available.is_set())



    @patch.object(GPTResponder, '_save_response_to_file')
    @patch.object(GPTResponder, 'llm_client')
    def test_generate_response_selected_text_sets_event(self, mock_client, mock_save):
        stream_chunk = MagicMock()
        stream_chunk.choices = [MagicMock(delta=MagicMock(content='hi'))]
        mock_client.chat.completions.create.return_value = [stream_chunk]
        self.responder.generate_response_for_selected_text('text')
        self.context.set_read_response.assert_called_with(True)
        self.assertTrue(self.context.audio_player_var.speech_text_available.is_set())



if __name__ == '__main__':
    unittest.main()


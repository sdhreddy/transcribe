import unittest
from unittest.mock import patch, MagicMock
from app.transcribe.gpt_responder import GPTResponder



class TestGPTResponder(unittest.TestCase):
    @patch.object(GPTResponder, "_get_llm_response", return_value="hi")
    @patch("app.transcribe.gpt_responder.utilities.is_api_key_valid", return_value=True)
    def test_generate_response_for_selected_text_stream(self, mock_valid, mock_get):
        convo = MagicMock()
        config = {
            "General": {
                "chat_inference_provider": "openai",
                "llm_response_interval": 1,
            },
            "OpenAI": {
                "api_key": "x",
                "base_url": "y",
                "ai_model": "z",
                "response_request_timeout_seconds": 1,
                "temperature": 0.1,
            },
        }
        responder = GPTResponder(config=config, convo=convo, file_name="f.txt")
        responder.llm_client = MagicMock()
        responder.streaming_complete = MagicMock()
        with patch(
            "app.transcribe.gpt_responder.prompts.create_prompt_for_text",
            return_value=[],
        ):
            result = responder.generate_response_for_selected_text("text")
        self.assertEqual(result, "hi")
        mock_get.assert_called_once()


if __name__ == "__main__":

class TestGPTResponder(unittest.TestCase):
    @patch.object(GPTResponder, '_get_llm_response', return_value='hi')
    @patch('app.transcribe.gpt_responder.utilities.is_api_key_valid', return_value=True)
    def test_generate_response_for_selected_text_stream(self, mock_valid, mock_get):
        convo = MagicMock()
        config = {
            'General': {
                'chat_inference_provider': 'openai',
                'llm_response_interval': 1,
            },
            'OpenAI': {
                'api_key': 'x',
                'base_url': 'y',
                'ai_model': 'z',
                'response_request_timeout_seconds': 1,
                'temperature': 0.1,
            }
        }
        responder = GPTResponder(config=config, convo=convo, file_name='f.txt')
        responder.llm_client = MagicMock()
        responder.streaming_complete = MagicMock()
        with patch('app.transcribe.gpt_responder.prompts.create_prompt_for_text', return_value=[]):
            result = responder.generate_response_for_selected_text('text')
        self.assertEqual(result, 'hi')
        mock_get.assert_called_once()

if __name__ == '__main__':

    unittest.main()

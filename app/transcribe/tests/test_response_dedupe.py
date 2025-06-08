import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.transcribe.audio_player import AudioPlayer

class TestResponseDedupe(unittest.TestCase):
    @patch('gtts.gTTS')
    def test_response_deduplication(self, mock_gtts):
        mock_gtts.return_value = MagicMock(save=MagicMock())
        with patch('subprocess.Popen') as popen_mock:
            convo = MagicMock()
            convo.context = MagicMock()
            convo.context.audio_queue = MagicMock()
            convo.context.audio_queue.empty.return_value = True
            player = AudioPlayer(convo=convo)
            player.play_audio('hi', 'en', rate=1.0, volume=0.1, response_id='r1')
            player.play_audio('hi', 'en', rate=1.0, volume=0.1, response_id='r1')
            self.assertEqual(popen_mock.call_count, 1)

if __name__ == '__main__':
    unittest.main()

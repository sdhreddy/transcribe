import unittest
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.transcribe.audio_player import AudioPlayer

class TestSinglePlayback(unittest.TestCase):
    @patch('gtts.gTTS')
    def test_single_audio_playback(self, mock_gtts):
        mock_gtts.return_value = MagicMock(save=MagicMock())
        popen_calls = []

        def fake_popen(cmd, *args, **kwargs):
            popen_calls.append(cmd)
            class DummyProc:
                def poll(self):
                    return 0
                def terminate(self):
                    pass
                def wait(self, timeout=None):
                    pass
                def kill(self):
                    pass
            return DummyProc()

        convo = MagicMock()
        convo.context = MagicMock()
        convo.context.audio_queue = MagicMock()
        convo.context.audio_queue.empty.return_value = True

        with patch('subprocess.Popen', side_effect=fake_popen):
            player = AudioPlayer(convo=convo)

            player.play_audio('hi', 'en', rate=1.0, volume=0.5, response_id='s')


            player.play_audio('hi', 'en', rate=1.0, volume=0.5, response_id='s')


            player.play_audio('hi', 'en', rate=1.0, volume=0.5, response_id='s')


            player.play_audio('hi', 'en', rate=1.0, volume=0.5, response_id='s')

            player.play_audio('hi', 'en', rate=1.0, volume=0.5)



            self.assertEqual(len(popen_calls), 1)

if __name__ == '__main__':
    unittest.main()

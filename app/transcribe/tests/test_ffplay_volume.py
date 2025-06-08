import unittest
from unittest.mock import patch, MagicMock

import time

import time


import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.transcribe.audio_player import AudioPlayer

class TestFFplayVolume(unittest.TestCase):
    @patch('gtts.gTTS')
    def test_volume_argument_passed(self, mock_gtts):
        mock_gtts.return_value = MagicMock(save=MagicMock())
        captured_cmds = []

        def fake_popen(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            class DummyProc:
                def __init__(self):
                    self.count = 0
                def poll(self):
                    self.count += 1
                    return 0 if self.count > 1 else None
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
            for volume in [0.2, 0.5, 0.8]:

                player.play_audio('hi', 'en', rate=1.0, volume=volume, response_id=str(volume))
                cmd = captured_cmds[-1]
                joined = ' '.join(cmd)
                self.assertIn(f'volume={volume}', joined)
                time.sleep(1.1)


                player.play_audio('hi', 'en', rate=1.0, volume=volume)
                cmd = captured_cmds[-1]
                joined = ' '.join(cmd)
                self.assertIn(f'volume={volume}', joined)


if __name__ == '__main__':
    unittest.main()

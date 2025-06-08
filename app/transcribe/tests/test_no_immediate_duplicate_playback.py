import unittest
import threading
import time
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.transcribe.audio_player import AudioPlayer


class TestNoImmediateDuplicatePlayback(unittest.TestCase):
    @patch('gtts.gTTS')
    def test_no_immediate_duplicate_playback(self, mock_gtts):
        mock_gtts.return_value = MagicMock(save=MagicMock())

        def fake_popen(cmd, *args, **kwargs):
            class DummyProc:
                def __init__(self):
                    self.count = 0
                def poll(self):
                    self.count += 1
                    return 0 if self.count > 3 else None
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
        with patch('subprocess.Popen', side_effect=fake_popen) as popen_mock:
            player = AudioPlayer(convo=convo)
            t1 = threading.Thread(target=player.play_audio, args=('hi','en'), kwargs={'rate':1.0, 'volume':0.5})
            t1.start()
            time.sleep(0.05)
            player.play_audio('hi','en', rate=1.0, volume=0.5)
            t1.join()
            self.assertEqual(popen_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()

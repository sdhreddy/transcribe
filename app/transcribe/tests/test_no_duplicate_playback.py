import unittest
import threading
from unittest.mock import patch, MagicMock
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app.transcribe.audio_player import AudioPlayer


class TestNoDuplicatePlayback(unittest.TestCase):
    @patch('gtts.gTTS')
    def test_concurrent_playback_invocation(self, mock_gtts):
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

            t1 = threading.Thread(target=player.play_audio, args=('hi', 'en'), kwargs={'rate':1.0, 'volume':0.5, 'response_id':'1'})
            t2 = threading.Thread(target=player.play_audio, args=('hi', 'en'), kwargs={'rate':1.0, 'volume':0.5, 'response_id':'1'})


            t1 = threading.Thread(target=player.play_audio, args=('hi', 'en'), kwargs={'rate':1.0, 'volume':0.5, 'response_id':'1'})
            t2 = threading.Thread(target=player.play_audio, args=('hi', 'en'), kwargs={'rate':1.0, 'volume':0.5, 'response_id':'1'})

            t1 = threading.Thread(target=player.play_audio, args=('hi', 'en'), kwargs={'rate':1.0, 'volume':0.5})
            t2 = threading.Thread(target=player.play_audio, args=('hi', 'en'), kwargs={'rate':1.0, 'volume':0.5})


            t1.start()
            t2.start()
            t1.join()
            t2.join()
            self.assertEqual(popen_mock.call_count, 1)


if __name__ == '__main__':
    unittest.main()


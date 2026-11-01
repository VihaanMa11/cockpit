import unittest
from music import Music


class MusicStateTests(unittest.TestCase):
    def test_mock_player_state_and_controls(self):
        player = Music(mock=True)
        self.assertFalse(player.mock_snapshot()["active"])
        player.apply_mock_action("play_pause")
        playing = player.mock_snapshot()
        self.assertEqual(playing["status"], "playing")
        self.assertTrue(playing["active"])
        player.apply_mock_action("volume_up")
        self.assertGreater(player.mock_snapshot()["volume"], playing["volume"])
        title = playing["title"]
        player.apply_mock_action("next_track")
        self.assertNotEqual(player.mock_snapshot()["title"], title)


if __name__ == "__main__":
    unittest.main()

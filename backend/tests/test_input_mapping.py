import unittest
from main import resolve_input_action, should_auto_open


class InputMappingTests(unittest.TestCase):
    def test_screen_and_context_mappings(self):
        mapping = {
            "left": {"action": "navigate", "delta": -1},
            "up": {"home": "none", "music": "volume_up", "agents": "select_prev"},
            "down": {"agents": "select_next"},
            "approve": {"music": "next_track"},
            "voice": {"agents": "none"},
        }
        self.assertEqual(resolve_input_action("left", "home", mapping), "navigate")
        self.assertEqual(resolve_input_action("up", "music", mapping), "volume_up")
        self.assertEqual(resolve_input_action("down", "agents", mapping), "select_next")
        self.assertEqual(resolve_input_action("approve", "music", mapping), "next_track")
        self.assertEqual(resolve_input_action("voice", "agents", mapping), "none")

    def test_music_auto_open_only_on_play_transition(self):
        paused = {"status": "paused"}
        playing = {"status": "playing"}
        self.assertTrue(should_auto_open(paused, playing, True))
        self.assertFalse(should_auto_open(playing, playing, True))
        self.assertFalse(should_auto_open(paused, playing, False))


if __name__ == "__main__":
    unittest.main()

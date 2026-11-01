import unittest
from sensors import Sensors


class MissingSensorTests(unittest.TestCase):
    def test_missing_dht22_returns_unknown_without_raising(self):
        sensor = Sensors(mock=False, gpio=4)
        self.assertIsNone(sensor._dht_value(0)["value"])
        self.assertFalse(sensor._dht_value(0)["stale"])

    def test_last_good_reading_becomes_stale(self):
        sensor = Sensors(mock=False, stale_seconds=30)
        sensor.last_dht = (20.0, 45.0)
        sensor.last_dht_at = 1
        self.assertEqual(sensor._dht_value(0)["value"], 20.0)
        self.assertTrue(sensor._dht_value(0)["stale"])


if __name__ == "__main__":
    unittest.main()

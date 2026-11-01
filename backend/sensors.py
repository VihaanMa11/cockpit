"""Best-effort sensor adapter. Missing hardware is represented as null data."""
import asyncio
import time
from pathlib import Path


class Sensors:
    def __init__(self, mock=False, gpio=4, stale_seconds=30):
        self.mock, self.gpio, self.stale_seconds = mock, gpio, stale_seconds
        self.last_dht = None
        self.last_dht_at = None
        self.dht_device = None

    async def snapshot(self):
        if self.mock:
            now = time.time()
            return {"temperature": {"value": 22.4, "updated_at": now, "stale": False}, "humidity": {"value": 48, "updated_at": now, "stale": False}, "cpu_temperature": 47.2, "wifi_connected": True, "air_quality": None, "supply_voltage": None}
        await asyncio.to_thread(self._read_dht)
        cpu = None
        try:
            cpu = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000
        except (OSError, ValueError):
            pass
        return {"temperature": self._dht_value(0), "humidity": self._dht_value(1), "cpu_temperature": cpu, "wifi_connected": self._wifi(), "air_quality": None, "supply_voltage": None}

    def _read_dht(self):
        try:
            if self.dht_device is None:
                import board
                import adafruit_dht
                self.dht_device = adafruit_dht.DHT22(getattr(board, f"D{self.gpio}"), use_pulseio=False)
            temperature, humidity = self.dht_device.temperature, self.dht_device.humidity
            if temperature is not None and humidity is not None:
                self.last_dht = (float(temperature), float(humidity))
                self.last_dht_at = time.time()
        except Exception:
            pass

    def _dht_value(self, index):
        fresh = self.last_dht_at is not None and time.time() - self.last_dht_at <= self.stale_seconds
        return {"value": self.last_dht[index] if self.last_dht else None, "updated_at": self.last_dht_at, "stale": bool(self.last_dht and not fresh)}

    @staticmethod
    def _wifi():
        try:
            import subprocess
            result = subprocess.run(["iwgetid", "-r"], capture_output=True, timeout=1)
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return None

"""Best-effort sensor adapter. Missing hardware is represented as null data."""
import asyncio
import logging
import time
from pathlib import Path

logger = logging.getLogger("cockpit.sensors")


class Sensors:
    def __init__(self, mock=False, gpio=4, stale_seconds=30, sensor_type="auto"):
        self.mock = mock
        self.gpio = gpio
        self.stale_seconds = stale_seconds
        self.sensor_type = str(sensor_type).lower()
        self.last_dht = None
        self.last_dht_at = None
        self.dht_device = None
        self._active_type = None

    async def snapshot(self):
        if self.mock:
            now = time.time()
            return {
                "temperature": {"value": 22.4, "updated_at": now, "stale": False},
                "humidity": {"value": 48, "updated_at": now, "stale": False},
                "cpu_temperature": 47.2,
                "wifi_connected": True,
                "air_quality": None,
                "supply_voltage": None,
            }
        await asyncio.to_thread(self._read_dht)
        cpu = None
        try:
            cpu = int(Path("/sys/class/thermal/thermal_zone0/temp").read_text().strip()) / 1000
        except (OSError, ValueError):
            pass
        return {
            "temperature": self._dht_value(0),
            "humidity": self._dht_value(1),
            "cpu_temperature": cpu,
            "wifi_connected": self._wifi(),
            "air_quality": None,
            "supply_voltage": None,
        }

    def _init_device(self, dht_type):
        import board
        import adafruit_dht

        pin_obj = getattr(board, f"D{self.gpio}")
        if dht_type == "dht11":
            return adafruit_dht.DHT11(pin_obj, use_pulseio=False)
        return adafruit_dht.DHT22(pin_obj, use_pulseio=False)

    def _read_dht(self):
        try:
            import board
            import adafruit_dht
        except ImportError:
            return

        candidates = ["dht22", "dht11"] if self.sensor_type == "auto" else [self.sensor_type]
        if self._active_type and self._active_type in candidates:
            candidates.remove(self._active_type)
            candidates.insert(0, self._active_type)

        for candidate in candidates:
            try:
                if self.dht_device is None or self._active_type != candidate:
                    if self.dht_device is not None:
                        try:
                            self.dht_device.exit()
                        except Exception:
                            pass
                    self.dht_device = self._init_device(candidate)
                    self._active_type = candidate

                temperature = self.dht_device.temperature
                humidity = self.dht_device.humidity
                if temperature is not None and humidity is not None:
                    self.last_dht = (float(temperature), float(humidity))
                    self.last_dht_at = time.time()
                    return
            except Exception:
                # Timing errors are common with DHT single-bus protocol on Linux; retry on next tick
                pass

    def _dht_value(self, index):
        fresh = self.last_dht_at is not None and time.time() - self.last_dht_at <= self.stale_seconds
        return {
            "value": self.last_dht[index] if self.last_dht else None,
            "updated_at": self.last_dht_at,
            "stale": bool(self.last_dht and not fresh),
        }

    @staticmethod
    def _wifi():
        try:
            import subprocess

            result = subprocess.run(["iwgetid", "-r"], capture_output=True, timeout=1)
            return result.returncode == 0 and bool(result.stdout.strip())
        except Exception:
            return None

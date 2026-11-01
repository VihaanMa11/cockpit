"""Configurable GPIO input adapter; all physical inputs emit common events."""
import asyncio
import logging

logger = logging.getLogger("cockpit.hardware")
EVENTS = {"left", "right", "up", "down", "press", "run", "approve", "stop", "voice"}


class Hardware:
    def __init__(self, config):
        self.config = config
        self.mode = "mock"
        self._loop = None
        self._on_event = None
        self.devices = []

    def start(self, loop, on_event):
        self._loop, self._on_event = loop, on_event
        if self.config.get("mock_mode", True):
            self.mode = "mock"
            return
        try:
            self._start_real()
            self.mode = "real"
            logger.info("hardware: gpiozero + lgpio ready")
        except Exception as exc:
            self.mode = "mock"
            logger.warning("hardware unavailable (%s); using mock inputs", exc)

    def _start_real(self):
        from gpiozero import Button
        from gpiozero.pins.lgpio import LGPIOFactory

        factory = LGPIOFactory()
        debounce = float(self.config.get("joystick", {}).get("bounce_time", 0.05))
        for button in self.config.get("buttons", {}).values():
            self._watch(factory, int(button["pin"]), button["event"], debounce)
        for event, pin in self.config.get("joystick", {}).get("pins", {}).items():
            self._watch(factory, int(pin), event, debounce)

    def _watch(self, factory, pin, event, debounce):
        from gpiozero import Button
        if event not in EVENTS:
            raise ValueError(f"Unsupported input event {event}")
        device = Button(pin, pull_up=True, bounce_time=debounce, hold_time=0.25, hold_repeat=True, pin_factory=factory)
        device.when_pressed = lambda event=event: self._emit(event, False)
        if event in ("up", "down"):
            device.when_held = lambda event=event: self._emit(event, True)
        self.devices.append(device)

    def _emit(self, event, repeat):
        asyncio.run_coroutine_threadsafe(self._on_event(event, repeat=repeat), self._loop)

    async def mock_event(self, event):
        if self.mode != "mock":
            raise RuntimeError("mock events are only available in mock mode")
        if event not in EVENTS:
            raise ValueError(f"Unknown event {event}")
        await self._on_event(event)

    async def mock_press(self, button_id):
        button = self.config.get("buttons", {}).get(str(button_id))
        if not button:
            raise ValueError(f"unknown button id {button_id}")
        await self.mock_event(button["event"])

    async def mock_rotate(self, direction):
        if direction not in ("cw", "ccw"):
            raise ValueError(f"unknown direction {direction}")
        await self.mock_event("up" if direction == "ccw" else "down")

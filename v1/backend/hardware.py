"""GPIO abstraction for Cockpit.

Tries real GPIO (gpiozero + lgpio pin factory) first; falls back to a mock
that is driven by the /api/dev/* REST endpoints. Both paths call the same
async callbacks, so behaviour is identical in real and mock mode.
"""

import asyncio
import logging

logger = logging.getLogger("cockpit.hardware")

BUTTON_PINS = {1: 5, 2: 6, 3: 13, 4: 16}
ENCODER_PIN_A = 17
ENCODER_PIN_B = 27
DEBOUNCE_SECONDS = 0.05


class Hardware:
    def __init__(self):
        self.mode = "mock"
        self._loop = None
        self._on_button = None
        self._on_rotate = None
        self._button_devices = {}
        self._encoder_device = None

    def start(self, loop, on_button, on_rotate):
        """on_button(button_id: int) and on_rotate(direction: 'cw'|'ccw')
        are async callables. Called once at app startup."""
        self._loop = loop
        self._on_button = on_button
        self._on_rotate = on_rotate
        try:
            self._start_real()
            self.mode = "real"
            logger.info("hardware: real GPIO initialised (gpiozero + lgpio)")
        except Exception as exc:
            self.mode = "mock"
            logger.warning("hardware: real GPIO unavailable (%s) — using MOCK mode", exc)

    def _start_real(self):
        from gpiozero import Button, RotaryEncoder
        from gpiozero.pins.lgpio import LGPIOFactory

        factory = LGPIOFactory()

        for button_id, pin in BUTTON_PINS.items():
            btn = Button(pin, pull_up=True, bounce_time=DEBOUNCE_SECONDS, pin_factory=factory)
            btn.when_pressed = self._make_button_handler(button_id)
            self._button_devices[button_id] = btn

        encoder = RotaryEncoder(ENCODER_PIN_A, ENCODER_PIN_B, pin_factory=factory)
        encoder.when_rotated_clockwise = self._make_rotate_handler("cw")
        encoder.when_rotated_counter_clockwise = self._make_rotate_handler("ccw")
        self._encoder_device = encoder

    def _make_button_handler(self, button_id):
        def handler():
            asyncio.run_coroutine_threadsafe(self._on_button(button_id), self._loop)
        return handler

    def _make_rotate_handler(self, direction):
        def handler():
            asyncio.run_coroutine_threadsafe(self._on_rotate(direction), self._loop)
        return handler

    async def mock_press(self, button_id: int):
        if self.mode != "mock":
            raise RuntimeError("mock_press is only available in mock mode")
        if button_id not in BUTTON_PINS:
            raise ValueError(f"unknown button id {button_id}")
        await self._on_button(button_id)

    async def mock_rotate(self, direction: str):
        if self.mode != "mock":
            raise RuntimeError("mock_rotate is only available in mock mode")
        if direction not in ("cw", "ccw"):
            raise ValueError("direction must be 'cw' or 'ccw'")
        await self._on_rotate(direction)

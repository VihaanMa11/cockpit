"""Configurable GPIO input adapter; all physical buttons emit digital events."""
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
        # If mock_mode is explicitly set to true in config.json, stay in mock mode
        if self.config.get("mock_mode") is True:
            self.mode = "mock"
            logger.info("hardware: mock mode explicitly enabled via config.json")
            return

        try:
            self._start_real()
            self.mode = "real"
            logger.info("hardware: gpiozero ready with %d button(s)", len(self.devices))
        except Exception as exc:
            self.mode = "mock"
            logger.warning("hardware unavailable (%s); falling back to mock inputs", exc)

    def stop(self):
        for device in self.devices:
            try:
                device.close()
            except Exception:
                pass
        self.devices.clear()

    def _start_real(self):
        from gpiozero import Button
        factory = None
        try:
            from gpiozero.pins.lgpio import LGPIOFactory
            factory = LGPIOFactory()
            logger.info("hardware: using LGPIOFactory for Pi GPIO")
        except Exception as exc:
            logger.warning("hardware: LGPIOFactory unavailable (%s), trying default factory", exc)
            factory = None

        debounce = float(self.config.get("button_debounce", 0.05))

        # Register all configured physical buttons
        for key, button in self.config.get("buttons", {}).items():
            pin = int(button["pin"])
            event = button["event"]
            self._watch(factory, pin, event, debounce)

    def _watch(self, factory, pin, event, debounce):
        from gpiozero import Button
        if event not in EVENTS:
            raise ValueError(f"Unsupported input event {event}")

        kwargs = {
            "pull_up": True,
            "bounce_time": debounce,
            "hold_time": 0.25,
            "hold_repeat": True,
        }
        if factory is not None:
            kwargs["pin_factory"] = factory

        device = Button(pin, **kwargs)

        # IMPORTANT: gpiozero passes the Device instance to callbacks if the handler accepts arguments.
        # We define closures taking *args to discard whatever gpiozero passes and emit our target event.
        def on_press(*args):
            logger.info("hardware: physical press on GPIO%d -> event '%s'", pin, event)
            self._emit(event, False)

        def on_hold(*args):
            logger.info("hardware: physical hold on GPIO%d -> event '%s'", pin, event)
            self._emit(event, True)

        device.when_pressed = on_press
        if event in ("up", "down"):
            device.when_held = on_hold

        self.devices.append(device)
        logger.info("hardware: watching GPIO%d for '%s' event (pull_up=True)", pin, event)

    def _emit(self, event, repeat):
        if self._loop and self._on_event:
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

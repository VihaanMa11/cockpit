"""Cockpit backend: FastAPI app.

Owns the in-memory state, drives the WebSocket broadcast, exposes the REST
surface (config/health/dev-only mock controls), and serves the built React
frontend as static files.
"""

import asyncio
import json
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from actions import post_webhook
from hardware import Hardware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cockpit.main")

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

MAX_EVENTS = 20
BUTTON_GLOW_SECONDS = 0.2


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


config = load_config()

state = {
    "mode": "mock",
    "screen_index": 0,
    "screen_name": config["screens"][0]["name"] if config["screens"] else None,
    "selection_index": 0,
    "selection_label": None,
    "buttons": {bid: False for bid in config["buttons"]},
    "encoder_steps": 0,
    "last_action": None,
    "clients_connected": 0,
    "events": [],
}


def current_screen() -> dict:
    return config["screens"][state["screen_index"]]


def current_workflow() -> dict | None:
    workflows = current_screen()["workflows"]
    if not workflows:
        return None
    return workflows[state["selection_index"]]


def sync_selection() -> None:
    state["screen_name"] = current_screen()["name"]
    wf = current_workflow()
    state["selection_label"] = wf["label"] if wf else None


sync_selection()


def push_event(kind: str, message: str) -> None:
    state["events"].insert(0, {"kind": kind, "message": message, "ts": time.time()})
    del state["events"][MAX_EVENTS:]


class ConnectionManager:
    def __init__(self):
        self.active: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active.append(ws)
        state["clients_connected"] = len(self.active)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active:
            self.active.remove(ws)
        state["clients_connected"] = len(self.active)

    async def broadcast(self) -> None:
        payload = json.dumps({"type": "state", "state": state})
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
hardware = Hardware()


async def broadcast() -> None:
    await manager.broadcast()


async def flash_button(button_id: int) -> None:
    key = str(button_id)
    state["buttons"][key] = True
    await broadcast()
    await asyncio.sleep(BUTTON_GLOW_SECONDS)
    state["buttons"][key] = False
    await broadcast()


async def handle_button_press(button_id: int) -> None:
    button_id = int(button_id)
    btn_cfg = config["buttons"].get(str(button_id))
    if not btn_cfg:
        logger.warning("press: unknown button id %s", button_id)
        return

    asyncio.create_task(flash_button(button_id))
    role = btn_cfg["role"]

    if role == "next_screen":
        state["screen_index"] = (state["screen_index"] + 1) % len(config["screens"])
        state["selection_index"] = 0
        sync_selection()
        push_event("screen", f"→ screen: {state['screen_name']}")
        await broadcast()

    elif role == "launch":
        wf = current_workflow()
        if wf is None:
            push_event("launch", "✗ no workflow selected")
            await broadcast()
            return
        state["last_action"] = {"type": "launch", "label": wf["label"], "status": "pending", "ts": time.time()}
        push_event("launch", f"▶ launching {wf['label']}…")
        await broadcast()
        ok = await post_webhook(wf["webhook"], {
            "screen": state["screen_name"],
            "workflow": wf["label"],
            "ts": time.time(),
        })
        state["last_action"] = {
            "type": "launch",
            "label": wf["label"],
            "status": "ok" if ok else "failed",
            "ts": time.time(),
        }
        push_event("launch", f"✓ {wf['label']} done" if ok else f"✗ {wf['label']} failed")
        await broadcast()

    elif role == "webhook":
        label = btn_cfg["label"]
        url = btn_cfg.get("webhook", "")
        push_event(label.lower(), f"▶ {label}…")
        await broadcast()
        ok = await post_webhook(url, {"action": label.lower(), "ts": time.time()})
        state["last_action"] = {
            "type": label.lower(),
            "label": label,
            "status": "ok" if ok else "failed",
            "ts": time.time(),
        }
        push_event(label.lower(), f"✓ {label} done" if ok else f"✗ {label} failed")
        await broadcast()

    else:
        logger.warning("press: unknown role %r for button %s", role, button_id)


async def handle_rotate(direction: str) -> None:
    workflows = current_screen()["workflows"]
    n = len(workflows)
    if n == 0:
        return
    delta = 1 if direction == "cw" else -1
    state["selection_index"] = (state["selection_index"] + delta) % n
    state["encoder_steps"] += delta
    sync_selection()
    push_event("select", f"↕ {state['selection_label']}")
    await broadcast()


@asynccontextmanager
async def lifespan(app: FastAPI):
    loop = asyncio.get_event_loop()
    hardware.start(loop, handle_button_press, handle_rotate)
    state["mode"] = hardware.mode
    logger.info("Cockpit backend started in %s mode", hardware.mode)
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({"type": "state", "state": state}))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@app.get("/api/config")
async def get_config():
    return config


@app.get("/api/health")
async def get_health():
    return {"status": "ok", "mode": hardware.mode}


@app.post("/api/dev/press/{button_id}")
async def dev_press(button_id: int):
    if hardware.mode != "mock":
        raise HTTPException(status_code=403, detail="dev endpoints are only available in mock mode")
    if button_id not in (1, 2, 3, 4):
        raise HTTPException(status_code=400, detail="button_id must be 1-4")
    await hardware.mock_press(button_id)
    return {"ok": True}


@app.post("/api/dev/rotate/{direction}")
async def dev_rotate(direction: str):
    if hardware.mode != "mock":
        raise HTTPException(status_code=403, detail="dev endpoints are only available in mock mode")
    if direction not in ("cw", "ccw"):
        raise HTTPException(status_code=400, detail="direction must be 'cw' or 'ccw'")
    await hardware.mock_rotate(direction)
    return {"ok": True}


if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/")
    async def frontend_missing():
        return {"detail": "frontend/dist not built yet — run `npm run build` in frontend/"}

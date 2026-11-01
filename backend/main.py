"""FastAPI state, input dispatch, webhook execution, and live updates."""
import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from actions import post_webhook
from hardware import EVENTS, Hardware
from music import Music
from sensors import Sensors

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("cockpit.main")
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"
config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
workflows = config.get("workflows", [])

state = {
    "mode": "mock", "screen_index": 0, "selection_index": 0,
    "workflows": [{"status": "idle", "last_run": None, "error": None} for _ in workflows],
    "music": {}, "sensors": {}, "events": [],
}
remote_music = {"state": None, "updated_at": 0.0, "artwork_hash": None, "art_url": None, "commands": []}
COMPANION_TOKEN_PATH = BASE_DIR / "companion_token.txt"


def companion_token():
    return os.environ.get("COCKPIT_COMPANION_TOKEN", "").strip() or (COMPANION_TOKEN_PATH.read_text(encoding="utf-8").strip() if COMPANION_TOKEN_PATH.is_file() else "")


class Connections:
    def __init__(self):
        self.clients = []

    async def connect(self, ws):
        await ws.accept()
        self.clients.append(ws)
        await ws.send_text(json.dumps({"type": "state", "state": state}))

    def disconnect(self, ws):
        if ws in self.clients:
            self.clients.remove(ws)

    async def broadcast(self):
        message = json.dumps({"type": "state", "state": state})
        for ws in list(self.clients):
            try:
                await ws.send_text(message)
            except Exception:
                self.disconnect(ws)


manager = Connections()
hardware = Hardware(config)
music = Music(mock=config.get("mock_mode", True), config=config.get("music"))
sensors = Sensors(mock=config.get("mock_mode", True), gpio=config.get("sensors", {}).get("dht22_gpio", 4), stale_seconds=config.get("sensors", {}).get("stale_seconds", 30))


def resolve_input_action(event, screen, mapping):
    if event in ("left", "right"):
        return mapping.get(event, {}).get("action", "navigate")
    return mapping.get(event, {}).get(screen, "none")


def should_auto_open(previous, current, enabled=True):
    return bool(enabled and current.get("status") == "playing" and previous.get("status") != "playing")


def push_event(kind, message):
    state["events"] = ([{"kind": kind, "message": message, "ts": time.time()}] + state["events"])[:20]


async def broadcast():
    await manager.broadcast()


async def run_workflow(index):
    wf = workflows[index]
    state["workflows"][index] = {"status": "running", "last_run": time.time(), "error": None}
    push_event("workflow", f"Running {wf.get('label', 'workflow')}")
    await broadcast()
    timeout = float(wf.get("timeout", 5))
    try:
        url = wf.get("webhook", "")
        method = wf.get("method", "POST").upper()
        if config.get("mock_mode", True):
            if url == "mock://timeout":
                await asyncio.sleep(timeout + 0.5)
                ok, error = False, "Request timed out"
            elif url == "mock://failure":
                ok, error = False, "Mock failure"
            else:
                await asyncio.sleep(0.25)
                ok, error = True, None
        else:
            ok, error = await post_webhook(url, {"workflow": wf.get("label"), "ts": time.time()}, method=method, timeout=timeout)
        status = "success" if ok else "failed"
    except Exception as exc:
        status, error = "failed", str(exc)[:80]
    state["workflows"][index] = {"status": status, "last_run": time.time(), "error": error}
    push_event("workflow", f"{wf.get('label', 'Workflow')}: {status}" + (f" — {error}" if error else ""))
    await broadcast()


async def dispatch_action(action):
    screen = ("home", "music", "agents")[state["screen_index"]]
    if action == "none" or not action:
        return
    if action == "select_prev":
        state["selection_index"] = (state["selection_index"] - 1) % max(1, len(workflows))
    elif action == "select_next":
        state["selection_index"] = (state["selection_index"] + 1) % max(1, len(workflows))
    elif action == "run_workflow":
        if workflows:
            asyncio.create_task(run_workflow(state["selection_index"] % len(workflows)))
    elif action in {"play_pause", "next_track", "previous_track", "volume_up", "volume_down"}:
        remote_is_live = (
            state.get("music", {}).get("source") == "spotify-windows"
            and state.get("music", {}).get("active")
            and time.monotonic() - remote_music["updated_at"] < 12
        )
        if remote_is_live:
            remote_music["commands"].append({"id": time.time_ns(), "action": action})
            remote_music["commands"] = remote_music["commands"][-32:]
        else:
            await music.act(action)
    await broadcast()


async def handle_input(event, repeat=False):
    if event not in EVENTS:
        return
    if repeat and not (event in ("up", "down") and state["screen_index"] == 1):
        return
    mapping = config.get("input_mapping", {}).get(event, {})
    if event in ("left", "right"):
        delta = int(mapping.get("delta", -1 if event == "left" else 1))
        state["screen_index"] = (state["screen_index"] + delta) % 3
        state["selection_index"] = 0
        push_event("screen", ("Home", "Music", "Agents")[state["screen_index"]])
    else:
        screen = ("home", "music", "agents")[state["screen_index"]]
        await dispatch_action(resolve_input_action(event, screen, config.get("input_mapping", {})))
    await broadcast()


async def live_updates():
    while True:
        if remote_music["state"] is not None and time.monotonic() - remote_music["updated_at"] < 12:
            current = remote_music["state"]
        else:
            current = await music.snapshot()
        previous = state.get("music", {})
        if should_auto_open(previous, current, config.get("music", {}).get("auto_open", True)):
            state["screen_index"] = 1
        state["music"] = current
        state["sensors"] = await sensors.snapshot()
        await broadcast()
        await asyncio.sleep(float(config.get("music", {}).get("poll_seconds", 1.5)))


@asynccontextmanager
async def lifespan(app):
    loop = asyncio.get_running_loop()
    hardware.start(loop, handle_input)
    state["mode"] = hardware.mode
    music.mock = hardware.mode == "mock"
    sensors.mock = hardware.mode == "mock"
    task = asyncio.create_task(live_updates())
    yield
    task.cancel()
    for device in hardware.devices:
        device.close()


app = FastAPI(lifespan=lifespan)


def require_local_kiosk(request: Request):
    """Allow UI actions only from the Pi's own same-origin kiosk browser."""
    peer = request.client.host if request.client else ""
    try:
        is_loopback = ipaddress.ip_address(peer).is_loopback
    except ValueError:
        is_loopback = False
    allowed_origins = {"http://127.0.0.1:8000", "http://localhost:8000"}
    origin = request.headers.get("origin", "")
    host = request.headers.get("host", "")
    if not is_loopback or origin not in allowed_origins or host not in {"127.0.0.1:8000", "localhost:8000"}:
        raise HTTPException(status_code=403, detail="Local Cockpit kiosk controls only")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/api/config")
async def get_config():
    return config


@app.get("/api/health")
async def get_health():
    return {"status": "ok", "mode": state["mode"]}


@app.post("/api/local/event/{event}")
async def local_kiosk_event(event: str, request: Request):
    require_local_kiosk(request)
    if event not in EVENTS:
        raise HTTPException(status_code=400, detail="unknown input event")
    await handle_input(event)
    return {"ok": True}


@app.post("/api/local/screen/{screen_index}")
async def local_kiosk_screen(screen_index: int, request: Request):
    require_local_kiosk(request)
    if screen_index not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="screen index must be 0, 1, or 2")
    state["screen_index"] = screen_index
    state["selection_index"] = 0
    await broadcast()
    return {"ok": True}


@app.post("/api/local/select/{workflow_index}")
async def local_kiosk_select(workflow_index: int, request: Request):
    require_local_kiosk(request)
    if workflow_index < 0 or workflow_index >= len(workflows):
        raise HTTPException(status_code=400, detail="unknown workflow index")
    state["selection_index"] = workflow_index
    await broadcast()
    return {"ok": True}


@app.post("/api/music/companion")
async def companion_music(request: Request):
    expected = companion_token()
    supplied = request.headers.get("x-cockpit-token", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Laptop music bridge is not configured on this Cockpit server")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid Cockpit companion token")
    raw = await request.body()
    if len(raw) > 7_000_000:
        raise HTTPException(status_code=413, detail="Music update is too large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Expected a JSON object")
    if payload.get("source") != "spotify-windows":
        raise HTTPException(status_code=400, detail="Unsupported companion source")
    title = str(payload.get("title") or "")[:300]
    artist = str(payload.get("artist") or "")[:500]
    album = str(payload.get("album") or "")[:300]
    active = bool(payload.get("active") and title)
    status = str(payload.get("status") or "stopped").lower()
    if status not in {"playing", "paused", "stopped"}:
        status = "stopped"
    artwork_hash = str(payload.get("artwork_hash") or "")[:64]
    if artwork_hash != remote_music["artwork_hash"]:
        remote_music["art_url"] = None
        encoded = payload.get("artwork_b64")
        mime = str(payload.get("artwork_mime") or "").lower()
        extensions = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
        if encoded and mime in extensions:
            try:
                image = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=400, detail="Invalid artwork data") from exc
            if len(image) > 5_000_000:
                raise HTTPException(status_code=413, detail="Artwork is too large")
            digest = hashlib.sha256(image).hexdigest()
            if not artwork_hash or hmac.compare_digest(artwork_hash, digest):
                art_dir = BASE_DIR / "cache" / "artwork"
                art_dir.mkdir(parents=True, exist_ok=True)
                filename = f"spotify-{digest[:24]}{extensions[mime]}"
                target = art_dir / filename
                if not target.exists():
                    target.write_bytes(image)
                remote_music["art_url"] = f"/api/artwork/{filename}"
            else:
                raise HTTPException(status_code=400, detail="Artwork hash mismatch")
        remote_music["artwork_hash"] = artwork_hash
    if not active:
        remote_music["art_url"] = None
        remote_music["artwork_hash"] = None
    duration = max(0, min(86_400, int(payload.get("duration") or 0)))
    elapsed = max(0, min(duration or 86_400, int(payload.get("elapsed") or 0)))
    incoming_music = {
        "active": active, "status": status if active else "stopped",
        "title": title if active else "Nothing playing", "artist": artist if active else "",
        "album": album if active else "", "duration": duration, "elapsed": elapsed,
        "art_url": remote_music["art_url"] if active else None,
        "volume": None, "source": "spotify-windows",
    }
    previous_music = state.get("music", {})
    remote_music["state"] = incoming_music
    remote_music["updated_at"] = time.monotonic()
    state["music"] = incoming_music
    if should_auto_open(previous_music, incoming_music, config.get("music", {}).get("auto_open", True)):
        state["screen_index"] = 1
    await broadcast()
    return {"ok": True}


@app.get("/api/music/companion/commands")
async def companion_music_commands(request: Request):
    expected = companion_token()
    supplied = request.headers.get("x-cockpit-token", "")
    if not expected:
        raise HTTPException(status_code=503, detail="Laptop music bridge is not configured on this Cockpit server")
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="Invalid Cockpit companion token")
    commands = remote_music["commands"]
    remote_music["commands"] = []
    return {"commands": commands}


@app.post("/api/dev/event/{event}")
async def dev_event(event: str):
    if state["mode"] != "mock":
        raise HTTPException(status_code=403, detail="mock events only")
    if event not in EVENTS:
        raise HTTPException(status_code=400, detail="unknown input event")
    await hardware.mock_event(event)
    return {"ok": True}


@app.post("/api/dev/screen/{screen_index}")
async def dev_screen(screen_index: int):
    if state["mode"] != "mock":
        raise HTTPException(status_code=403, detail="mock controls only")
    if screen_index not in (0, 1, 2):
        raise HTTPException(status_code=400, detail="screen index must be 0, 1, or 2")
    state["screen_index"] = screen_index
    state["selection_index"] = 0
    await broadcast()
    return {"ok": True}


@app.post("/api/dev/select/{workflow_index}")
async def dev_select(workflow_index: int):
    if state["mode"] != "mock":
        raise HTTPException(status_code=403, detail="mock controls only")
    if workflow_index < 0 or workflow_index >= len(workflows):
        raise HTTPException(status_code=400, detail="unknown workflow index")
    state["selection_index"] = workflow_index
    await broadcast()
    return {"ok": True}


@app.post("/api/dev/press/{button_id}")
async def dev_press(button_id: int):
    if state["mode"] != "mock":
        raise HTTPException(status_code=403, detail="mock inputs only")
    try:
        await hardware.mock_press(button_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True}


@app.post("/api/dev/rotate/{direction}")
async def dev_rotate(direction: str):
    if state["mode"] != "mock" or direction not in ("cw", "ccw"):
        raise HTTPException(status_code=400, detail="invalid mock rotation")
    await hardware.mock_rotate(direction)
    return {"ok": True}


@app.post("/api/dev/music/{action}")
async def dev_music(action: str):
    if state["mode"] != "mock":
        raise HTTPException(status_code=403, detail="mock player only")
    aliases = {"play": "play_pause", "pause": "play_pause", "next": "next_track", "previous": "previous_track"}
    action = aliases.get(action, action)
    if action not in {"play_pause", "next_track", "previous_track", "volume_up", "volume_down"}:
        raise HTTPException(status_code=400, detail="unknown player action")
    await music.act(action)
    return {"ok": True}


@app.get("/api/artwork/{filename}")
async def artwork(filename: str):
    path = BASE_DIR / "cache" / "artwork" / Path(filename).name
    if not path.is_file():
        raise HTTPException(status_code=404, detail="artwork not cached")
    return FileResponse(path)


if (BASE_DIR.parent / "assets").exists():
    app.mount("/static", StaticFiles(directory=str(BASE_DIR.parent / "assets")), name="assets")
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
else:
    @app.get("/")
    async def frontend_missing():
        return {"detail": "frontend/dist not built yet — run npm run build in frontend/"}

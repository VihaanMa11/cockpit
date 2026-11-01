# Cockpit Windows companion — Spotify now-playing bridge
# Run on the laptop; the Pi-hosted Cockpit displays the data over its existing WebSocket.
import asyncio
import base64
import ctypes
import getpass
import hashlib
import json
import logging
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as SessionManager,
        GlobalSystemMediaTransportControlsSessionPlaybackStatus as PlaybackStatus,
    )
    from winrt.windows.storage.streams import InputStreamOptions
except ImportError as exc:
    print("Missing Windows Runtime bindings. Run Start-Cockpit-Spotify-Bridge.bat to install them.")
    raise SystemExit(1) from exc

APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / "CockpitMusicBridge"
CONFIG_FILE = APP_DIR / "config.json"
POLL_SECONDS = 1.5
MAX_ART_BYTES = 5_000_000
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cockpit-spotify-bridge")


def load_config():
    if CONFIG_FILE.is_file():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    APP_DIR.mkdir(parents=True, exist_ok=True)
    print("Cockpit Spotify Bridge setup")
    print("Use the Cockpit host's LAN address, e.g. http://192.168.1.25:8000")
    server = input("Cockpit server URL: ").strip().rstrip("/")
    if not server.startswith(("http://", "https://")):
        raise ValueError("Server URL must start with http:// or https://")
    token = getpass.getpass("Cockpit bridge token: ").strip()
    if len(token) < 24:
        raise ValueError("The token looks too short. Generate one on the Cockpit server as shown in README.md")
    config = {"server_url": server, "token": token}
    CONFIG_FILE.write_text(json.dumps(config, indent=2), encoding="utf-8")
    try:
        CONFIG_FILE.chmod(0o600)
    except OSError:
        pass
    print(f"Saved laptop settings to {CONFIG_FILE}")
    return config


def seconds(value):
    if value is None:
        return 0
    if hasattr(value, "total_seconds"):
        return max(0, int(value.total_seconds()))
    return max(0, int(value) // 10_000_000)


async def thumbnail_data(properties):
    thumbnail = properties.thumbnail
    if thumbnail is None:
        return None, None, ""
    stream = await thumbnail.open_read_async()
    size = int(stream.size)
    if size <= 0 or size > MAX_ART_BYTES:
        return None, None, ""
    buffer = bytearray(size)
    read_buffer = await stream.read_async(buffer, size, InputStreamOptions.NONE)
    image = bytes(read_buffer)
    mime = (stream.content_type or "").lower()
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        mime = mimetypes.guess_type("cover.jpg")[0] or "image/jpeg"
    return base64.b64encode(image).decode("ascii"), mime, hashlib.sha256(image).hexdigest()


async def find_spotify_session(manager):
    candidates = []
    for session in manager.get_sessions():
        app_id = str(session.source_app_user_model_id or "")
        if "spotify" not in app_id.casefold():
            continue
        try:
            info = session.get_playback_info()
            props = await session.try_get_media_properties_async()
            if not props or not props.title:
                continue
            playing = info.playback_status == PlaybackStatus.PLAYING
            paused = info.playback_status == PlaybackStatus.PAUSED
            timeline = session.get_timeline_properties()
            payload = {
                "source": "spotify-windows",
                "active": True,
                "status": "playing" if playing else "paused" if paused else "stopped",
                "title": props.title,
                "artist": props.artist or "",
                "album": props.album_title or "",
                "duration": seconds(timeline.end_time),
                "elapsed": seconds(timeline.position),
                "artwork_b64": None,
                "artwork_mime": None,
                "artwork_hash": "",
            }
            try:
                art_b64, art_mime, art_hash = await thumbnail_data(props)
                payload.update(artwork_b64=art_b64, artwork_mime=art_mime, artwork_hash=art_hash)
            except Exception as exc:
                log.debug("Spotify metadata is available, but its artwork could not be read: %s", exc)
            candidates.append((playing, payload))
        except Exception as exc:
            log.debug("Could not read a Spotify media session: %s", exc)
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def publish(config, payload):
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = urllib.request.Request(
        config["server_url"] + "/api/music/companion",
        data=body,
        headers={"Content-Type": "application/json", "X-Cockpit-Token": config["token"]},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return response.status


def fetch_commands(config):
    request = urllib.request.Request(
        config["server_url"] + "/api/music/companion/commands",
        headers={"X-Cockpit-Token": config["token"]},
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.loads(response.read().decode("utf-8"))


def adjust_windows_volume(direction):
    # The Windows media volume keys adjust the laptop's master output volume.
    key = 0xAF if direction == "up" else 0xAE
    keyup = 0x0002
    ctypes.windll.user32.keybd_event(key, 0, 0, 0)
    ctypes.windll.user32.keybd_event(key, 0, keyup, 0)


async def apply_commands(session, commands):
    actions = {
        "play_pause": "try_toggle_play_pause_async",
        "next_track": "try_skip_next_async",
        "previous_track": "try_skip_previous_async",
    }
    for command in commands:
        action = command.get("action")
        try:
            if action in actions and session is not None:
                success = await getattr(session, actions[action])()
                if not success:
                    log.warning("Windows did not accept Spotify command: %s", action)
            elif action == "volume_up":
                adjust_windows_volume("up")
            elif action == "volume_down":
                adjust_windows_volume("down")
            else:
                log.warning("Cannot apply Spotify command without a Spotify session: %s", action)
        except Exception:
            log.exception("Could not apply Spotify command: %s", action)


async def run():
    config = load_config()
    manager = await SessionManager.request_async()
    previous_signature = None
    last_publish = 0.0
    last_warning = 0.0
    log.info("Watching Spotify media sessions. Leave this window open while using Cockpit.")
    while True:
        try:
            payload = await find_spotify_session(manager)
            if payload is None:
                payload = {
                    "source": "spotify-windows", "active": False, "status": "stopped",
                    "title": "", "artist": "", "album": "", "duration": 0, "elapsed": 0,
                    "artwork_b64": None, "artwork_mime": None, "artwork_hash": "",
                }
            request_artwork = False
            try:
                command_state = fetch_commands(config)
                commands = command_state.get("commands", [])
                session = next((s for s in manager.get_sessions()
                                if "spotify" in str(s.source_app_user_model_id or "").casefold()), None)
                await apply_commands(session, commands)
                request_artwork = bool(command_state.get("request_artwork"))
            except urllib.error.HTTPError as exc:
                if time.monotonic() - last_warning > 20:
                    log.warning("Cockpit command endpoint returned HTTP %s.", exc.code)
                    last_warning = time.monotonic()
            except (OSError, TimeoutError) as exc:
                if time.monotonic() - last_warning > 20:
                    log.warning("Cannot reach Cockpit command endpoint (%s). Retrying.", exc)
                    last_warning = time.monotonic()
            signature = tuple(payload.get(key) for key in ("active", "status", "title", "artist", "album", "duration", "artwork_hash"))
            # Send progress every ~1.5 seconds; attach image bytes only when the image changes.
            if signature == previous_signature and not request_artwork:
                payload["artwork_b64"] = None
                payload["artwork_mime"] = None
            try:
                publish(config, payload)
                if not payload["active"] and previous_signature is not None and previous_signature[0]:
                    log.info("Spotify stopped; Cockpit will return to its local player after the bridge timeout.")
                previous_signature = signature
                last_publish = time.monotonic()
            except urllib.error.HTTPError as exc:
                if time.monotonic() - last_warning > 20:
                    log.warning("Cockpit returned HTTP %s. Check the server URL and companion token.", exc.code)
                    last_warning = time.monotonic()
            except (OSError, TimeoutError) as exc:
                if time.monotonic() - last_warning > 20:
                    log.warning("Cannot reach Cockpit at %s (%s). Retrying.", config["server_url"], exc)
                    last_warning = time.monotonic()
            await asyncio.sleep(max(0.1, POLL_SECONDS - (time.monotonic() - last_publish)))
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Unexpected error while reading Spotify. Retrying shortly.")
            await asyncio.sleep(POLL_SECONDS)


def main():
    if sys.platform != "win32":
        raise SystemExit("This companion runs on Windows 10/11.")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nCockpit Spotify Bridge stopped.")


if __name__ == "__main__":
    main()


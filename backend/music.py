"""Optional MPRIS controls through playerctl and system volume tools."""
import asyncio
import hashlib
import logging
import shutil

logger = logging.getLogger("cockpit.music")


async def command(*args, timeout=2):
    try:
        proc = await asyncio.create_subprocess_exec(*args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        return out.decode("utf-8", "replace").strip() if proc.returncode == 0 else None
    except (FileNotFoundError, asyncio.TimeoutError, OSError):
        return None


class Music:
    def __init__(self, mock=False, config=None):
        self.mock = mock
        self.config = config or {}
        self.index = 0
        self.elapsed = 0
        self.playing = False
        self.player_active = False
        self.volume = 0.55
        self.tracks = [
            {"title": "Midnight City", "artist": "M83", "album": "Hurry Up, We're Dreaming", "duration": 244},
            {"title": "Sunset Lover", "artist": "Petit Biscuit", "album": "Presence", "duration": 237},
            {"title": "Weightless", "artist": "Marconi Union", "album": "Ambient Transmissions Vol. 2", "duration": 480},
        ]

    @staticmethod
    def empty_state():
        return {"active": False, "status": "stopped", "title": "Nothing playing", "artist": "", "album": "", "duration": 0, "elapsed": 0, "art_url": None, "volume": None}

    def mock_snapshot(self):
        if not self.player_active:
            return self.empty_state()
        track = self.tracks[self.index]
        if self.playing:
            self.elapsed = (self.elapsed + 1) % track["duration"]
        return {"active": True, "status": "playing" if self.playing else "paused", **track, "elapsed": self.elapsed, "art_url": None, "volume": self.volume}

    def apply_mock_action(self, action):
        if action == "play_pause":
            self.player_active = True
            self.playing = not self.playing
        elif action == "next_track":
            self.player_active = True
            self.index = (self.index + 1) % len(self.tracks)
            self.elapsed = 0
        elif action == "previous_track":
            self.player_active = True
            self.index = (self.index - 1) % len(self.tracks)
            self.elapsed = 0
        elif action == "volume_up":
            self.volume = min(1.0, self.volume + 0.05)
        elif action == "volume_down":
            self.volume = max(0.0, self.volume - 0.05)

    async def snapshot(self):
        if self.mock:
            return self.mock_snapshot()
        if not shutil.which("playerctl"):
            return self.empty_state()
        metadata = await command("playerctl", "metadata", "--format", "{{status}}\n{{artist}}\n{{title}}\n{{album}}\n{{mpris:length}}\n{{mpris:artUrl}}")
        if not metadata:
            return self.empty_state()
        values = (metadata.splitlines() + [""] * 6)[:6]
        status, artist, title, album, duration, art = values
        elapsed, volume = await command("playerctl", "position"), await self._volume()
        try:
            duration = int(float(duration) / 1_000_000)
        except (ValueError, TypeError):
            duration = 0
        try:
            elapsed = int(float(elapsed or 0))
        except ValueError:
            elapsed = 0
        art_url = await self.cache_art(art) if art else None
        return {"active": True, "status": status.lower(), "title": title or "Unknown track", "artist": artist, "album": album, "duration": duration, "elapsed": elapsed, "art_url": art_url, "volume": volume}

    async def cache_art(self, url):
        from pathlib import Path
        from urllib.parse import unquote, urlparse
        import httpx
        root = Path(__file__).parent / "cache" / "artwork"
        root.mkdir(parents=True, exist_ok=True)
        name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
        parsed = urlparse(url)
        try:
            if parsed.scheme == "file":
                source = Path(unquote(parsed.path))
                if not source.is_file():
                    return None
                target = root / f"{name}{source.suffix or '.img'}"
                if not target.exists():
                    target.write_bytes(source.read_bytes())
            elif parsed.scheme in ("http", "https"):
                target = root / f"{name}{Path(parsed.path).suffix[:8] or '.img'}"
                if not target.exists():
                    async with httpx.AsyncClient(timeout=3, follow_redirects=True) as client:
                        response = await client.get(url)
                        response.raise_for_status()
                        target.write_bytes(response.content[:8_000_000])
            else:
                return None
            return f"/api/artwork/{target.name}"
        except (OSError, httpx.HTTPError):
            logger.debug("Unable to cache album art %s", url)
            return None

    async def _volume(self):
        value = await command("wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@")
        try:
            if value:
                return min(1, max(0, float(value.split()[-1])))
        except ValueError:
            pass
        value = await command("pactl", "get-sink-volume", "@DEFAULT_SINK@")
        try:
            return int(value.split("/")[1].strip().rstrip("%")) / 100 if value else None
        except (ValueError, IndexError):
            return None

    async def act(self, action):
        if self.mock:
            self.apply_mock_action(action)
            return
        commands = {
            "play_pause": ("playerctl", "play-pause"), "next_track": ("playerctl", "next"),
            "previous_track": ("playerctl", "previous"),
            "volume_up": ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%+"),
            "volume_down": ("wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "5%-"),
        }
        cmd = commands.get(action)
        if action in ("volume_up", "volume_down") and not shutil.which("wpctl"):
            cmd = ("pactl", "set-sink-volume", "@DEFAULT_SINK@", "+5%" if action == "volume_up" else "-5%")
        if cmd:
            await command(*cmd)

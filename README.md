# Cockpit v2

Cockpit v2 is a React/Vite desk console served by FastAPI. Its 3:2 layout fills the 480 × 320 landscape area of the 3.5-inch SPI TFT and scales up to a 960 × 640 canvas on larger laptop windows. Navigation is keyboard or GPIO only.

## Laptop mock mode

1. Install Python 3.10+ and Node.js 18+.
2. In `backend/`, create a virtual environment, activate it, and install `pip install -r requirements.txt`.
3. In a second terminal, run `npm install` and `npm run dev` from `frontend/`.
4. Start the API from `backend/` with `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.
5. Open the Vite URL (normally `http://localhost:5173`). For the production-style single port, run `npm run build` in `frontend/` and open `http://localhost:8000`.

Mock mode is enabled by `mock_mode: true` in `backend/config.json`. Arrow keys navigate and select; Enter runs/plays; A and S change tracks; Up/Down change volume on Music. The `Demo` workflow category provides success, failure, and timeout examples. Mock calls never contact configured external webhook URLs. For scripted checks, mock inputs are available at `/api/dev/event/{left|right|up|down|press|run|approve|stop|voice}` and mock player actions at `/api/dev/music/{play|pause|next|previous|volume_up|volume_down}`.

## Raspberry Pi

Use Raspberry Pi OS 64-bit with Python, Node, and the GPIO packages described in `backend/requirements.txt`. Install `playerctl` and a working PipeWire (`wpctl`) or PulseAudio (`pactl`) audio server. Build the UI with `npm run build` in `frontend/`; run the backend with `python -m uvicorn main:app --host 0.0.0.0 --port 8000` from `backend/`.

### Install Python dependencies in the project environment

Raspberry Pi OS Bookworm and newer mark system Python as externally managed. Install the GPIO driver through `apt`, then install the app's Python packages into its virtual environment. Run these commands from the Pi:

```sh
sudo apt update
sudo apt install -y python3-full python3-lgpio
cd ~/cockpit/backend
python3 -m venv --system-site-packages .venv
./.venv/bin/python -m pip install --upgrade pip
./.venv/bin/python -m pip install -r requirements.txt
```

Using `./.venv/bin/python -m pip` explicitly avoids accidentally invoking system `pip`. If the DHT22 is connected, install its optional driver into the same environment with `./.venv/bin/python -m pip install adafruit-circuitpython-dht`. Do not use `sudo pip` or `--break-system-packages`.

Before enabling hardware, set `mock_mode` to `false` in `backend/config.json`. GPIO initialization uses gpiozero with `LGPIOFactory`; if it fails, the app falls back to mock mode. The 5-way digital joystick uses GPIO17 (up), GPIO27 (down), GPIO22 (left), GPIO23 (right), GPIO24 (press), with pull-ups and configured debounce. Buttons remain GPIO5 (RUN), GPIO6 (APPROVE), GPIO13 (STOP), GPIO16 (VOICE). DHT22 data uses GPIO4. Common ground and correct 3.3 V sensor wiring are required.

For kiosk startup, install Chromium, configure the Pi desktop session to launch Chromium in kiosk mode at `http://localhost:8000`, and enable the existing `backend/cockpit.service` with systemd after updating its user and path. Use a 480 × 320 landscape display mode.

## Wallpaper, workflows, and controls

- `ui.wallpaper` points to an image URL. The bundled `/assets/wallpapers/default.svg` is the fallback; replace the file or set the config path to another file served from `assets/`. Home uses cover cropping and a readability overlay. A missing image leaves the built-in gradient underneath.
- Add/edit entries under `workflows` with `label`, optional `description` and `category`, `webhook`, `method`, and optional timeout seconds. Workflow state is per list position and is broadcast live.
- Change `input_mapping` to change per-screen actions without editing code. `buttons` and `joystick.pins` hold GPIO pins and event names. `ui.clock_24h` selects 24-hour or locale 12-hour time; `music.auto_open` controls the once-per-play transition.
- Keep webhook URLs and tokens in `config.json` or an environment file; never put credentials in source code. Do not commit real secrets.

## Music and Bluetooth

Music controls use the system's active MPRIS player through `playerctl`; artwork from `mpris:artUrl` is cached under `backend/cache/artwork/`. Volume uses `wpctl` when available, otherwise `pactl`. A local player such as mpv with an MPRIS plugin or a Spotify Connect receiver on the Pi exposes metadata and controls directly.

### Bluetooth audio from a phone

1. Connect speakers to the Pi and verify they play audio. On Raspberry Pi OS Lite, first install and enable BlueZ plus the Bluetooth audio integration matching the active PipeWire/PulseAudio stack; desktop images may already include it.
2. Open `bluetoothctl` on the Pi and run `power on`, `agent on`, and `default-agent`.
3. Run `scan on`, note the phone's Bluetooth address, then run `pair <PHONE-MAC>`, `trust <PHONE-MAC>`, and `connect <PHONE-MAC>`. Stop scanning with `scan off`.
4. On the phone, select the Pi as the Bluetooth audio output and start music. Check the Pi's audio devices with `wpctl status` (or `pactl list short sinks`) and confirm sound reaches the connected speakers.
5. Check local MPRIS players with `playerctl -l`. A Bluetooth phone can stream audio without appearing as an MPRIS player on the Pi, so metadata, album art, and transport controls may remain unavailable for that phone session. For those features use an MPRIS-capable Pi player, such as mpv with its MPRIS plugin or a Spotify Connect receiver.

The app controls the active local MPRIS player through `playerctl`; it does not control the phone's Bluetooth transport directly.

### Spotify playing on a Windows laptop

The Pi cannot see the laptop's local Spotify MPRIS session. Use the companion package in `windows-companion/` to forward now-playing metadata and its Windows media-session artwork over your LAN; the Pi displays it through the existing WebSocket. This sends metadata and album art only, not audio. The bridge is preferred while it is connected and the backend falls back to the Pi's local MPRIS player after 12 seconds without updates.

1. On the Cockpit host, run this from `backend/` to create the private shared token, then restart Cockpit:
   - Linux/Pi: `python -c "import secrets,pathlib; pathlib.Path('companion_token.txt').write_text(secrets.token_urlsafe(32))"`
   - PowerShell: `python -c "import secrets,pathlib; pathlib.Path('companion_token.txt').write_text(secrets.token_urlsafe(32))"`
2. Copy the token from `backend/companion_token.txt` using `cat companion_token.txt` on Linux or `Get-Content companion_token.txt` in PowerShell. Do not commit or share it publicly.
3. Extract `windows-companion/Cockpit-Spotify-Bridge-Windows.zip` on the laptop and launch `Start-Cockpit-Spotify-Bridge.bat`. It creates a local Python environment and installs the required Windows media-session bindings. Python 3.11+ is required; install it from [python.org](https://www.python.org/downloads/windows/) if needed.
4. Enter the Pi's LAN URL (for example `http://192.168.1.25:8000`) and paste the token at the prompt. Open Spotify and play a track; leave the bridge window running. Its config is stored in `%APPDATA%\CockpitMusicBridge\config.json`.

Keep the Pi and laptop on a trusted LAN and allow inbound TCP port 8000 from the laptop. The bridge endpoint requires the shared token. The Music controls continue to target the Pi-local player; forwarding remote playback controls to the laptop is not part of this metadata bridge.

## Pi setup checklist

- [ ] Wire the DHT22 data line to GPIO4 and install the Raspberry Pi DHT22 Python dependencies (`adafruit-circuitpython-dht` and its board support); confirm readings after startup.
- [ ] Wire joystick GPIO17/27/22/23/24 and four buttons GPIO5/6/13/16; confirm pull-up logic, shared ground, and debounce.
- [ ] Connect speakers/headphones; verify the default PipeWire/PulseAudio sink and `wpctl` or `pactl` volume control.
- [ ] Pair the phone as a Bluetooth audio source if desired; verify audio reception and separately confirm whether a local MPRIS player is available.
- [ ] Set `mock_mode` to false, verify `/api/health` reports real mode, and check missing DHT22/player behavior is graceful.
- [ ] Configure Chromium kiosk autostart for `http://localhost:8000` at 480 × 320 landscape.

## Tests

From `backend/`, run `python -m unittest discover -s tests`. From `frontend/`, run `npm run build`.

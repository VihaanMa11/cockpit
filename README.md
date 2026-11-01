# Cockpit v2

Cockpit v2 is a React/Vite desk console served by FastAPI. Its responsive 3:2 layout fills the 480 × 320 landscape area of the MPI3501-style 3.5-inch SPI TFT and scales up to a 960 × 640 canvas on larger laptop windows. It supports keyboard, configured GPIO, and touchscreen controls in the Pi's local kiosk.

## Laptop mock mode

1. Install Python 3.10+ and Node.js 18+.
2. In `backend/`, create a virtual environment, activate it, and install `pip install -r requirements.txt`.
3. In a second terminal, run `npm install` and `npm run dev` from `frontend/`.
4. Start the API from `backend/` with `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.
5. Open the Vite URL (normally `http://localhost:5173`). For the production-style single port, run `npm run build` in `frontend/` and open `http://localhost:8000`.

Mock mode is enabled by `mock_mode: true` in `backend/config.json`. Arrow keys navigate and select; Enter runs/plays; A and S change tracks; Up/Down change volume on Music. The `Demo` workflow category provides success, failure, and timeout examples. Mock calls never contact configured external webhook URLs. For scripted checks, mock inputs are available at `/api/dev/event/{left|right|up|down|press|run|approve|stop|voice}` and mock player actions at `/api/dev/music/{play|pause|next|previous|volume_up|volume_down}`.

## Raspberry Pi

Use Raspberry Pi OS 64-bit. The setup script installs the desktop packages when starting from Raspberry Pi OS Lite (Trixie or Bookworm), selects desktop boot, then builds the UI, creates the Python venv, installs the DHT22 driver, enables real GPIO mode, installs the backend service, and configures Chromium kiosk autostart to open Cockpit at `/` after desktop login. Set up the TFT driver first, then pull the latest repository and rerun the script.

### TFT display, joystick, buttons, and DHT22

The photo matches the MPI3501-style 3.5-inch RPi Display (480 × 320, ILI9486 display controller, XPT2046 resistive touch). Its SPI/touch overlay uses GPIO7–11, GPIO17, GPIO24, and GPIO25. The old joystick map used GPIO17 and GPIO24, which conflict with the screen, so the current map is:

| Control | BCM GPIO | Physical pin |
| --- | ---: | ---: |
| Joystick up | 18 | 12 |
| Joystick down | 19 | 35 |
| Joystick left | 20 | 38 |
| Joystick right | 21 | 40 |
| Joystick press | 22 | 15 |
| RUN button | 5 | 29 |
| APPROVE button | 6 | 31 |
| STOP button | 13 | 33 |
| VOICE button | 16 | 36 |
| DHT22 data | 4 | 7 |

Use BCM numbering in `backend/config.json`; do not confuse BCM GPIO numbers with physical header pin numbers. **The display covers the first 26 physical pins.** To use the joystick, buttons, and DHT22 with the screen attached, fit a 40-pin stack-through/extended header or equivalent GPIO breakout that exposes the Pi pins while the TFT is mounted. Do not connect an input to GPIO7–11, 17, 24, or 25; those belong to the TFT/touch interface. The DHT22 needs 3.3 V, ground, data on GPIO4, and a 4.7–10 kΩ pull-up between data and 3.3 V if the sensor board does not include one.

For the screen driver, the manufacturer identifies this board family as MPI3501 and documents the `LCD35-show` driver. Back up the Pi before installing a third-party display driver; the vendor script changes boot/display configuration and reboots the Pi. From the Pi terminal, install it and reboot:

```sh
cd ~
git clone https://github.com/goodtft/LCD-show.git
cd LCD-show
sudo ./LCD35-show
```

After the Pi reboots and the screen shows the Raspberry Pi desktop, clone/pull Cockpit and run:

```sh
cd ~/cockpit/cockpitv2
git pull --ff-only origin master
chmod +x scripts/setup-pi.sh
./scripts/setup-pi.sh
sudo reboot
```

The included script installs a graphical desktop if needed, builds the app, and configures Chromium kiosk to open Cockpit Home. The vendor display driver is a separate prerequisite; Cockpit code alone cannot initialize the panel controller. For the MPI3501's normal landscape orientation, run `cd ~/LCD-show && sudo ./rotate.sh 0` after the driver is installed; this restores the driver's default 90° landscape position and matching touch calibration. The `rotate.sh` values are relative to the driver's starting orientation. If `rotate.sh 0` does not give landscape on your board, stop and check the active `dtoverlay` line before trying other rotations.

Touchscreen taps work in the local kiosk: tap the bottom screen indicators to navigate, tap a workflow row to select it, and use `RUN SELECTED` to trigger it. Local touch actions are accepted only from the Pi itself at `127.0.0.1:8000`, with a matching same-origin request. A browser opened from another computer can view Cockpit, but it cannot trigger local kiosk actions. Physical joystick and buttons continue to work independently.

### Python environment

The setup script creates `backend/.venv` with `--system-site-packages`, installs `python3-lgpio` through `apt`, and installs all Python packages into that virtual environment. This avoids Raspberry Pi OS's externally-managed system Python error. Do not use `sudo pip` or `--break-system-packages`.

GPIO initialization uses gpiozero with `LGPIOFactory`; if it fails, the app falls back to mock mode. The setup script sets `mock_mode` to `false`. Use the pin table above and ensure all inputs share a common ground. The TFT must be configured for 480 × 320 landscape orientation.

## Wallpaper, workflows, and controls

- `ui.wallpaper` points to an image URL. The bundled `/assets/wallpapers/default.svg` is the fallback; replace the file or set the config path to another file served from `assets/`. Home uses cover cropping and a readability overlay. A missing image leaves the built-in gradient underneath.
- Add/edit entries under `workflows` with `label`, optional `description` and `category`, `webhook`, `method`, and optional timeout seconds. Workflow state is per list position and is broadcast live.
- Change `input_mapping` to change per-screen actions without editing code. `buttons` and `joystick.pins` hold GPIO pins and event names. `ui.clock_24h` selects 24-hour or locale 12-hour time; `music.auto_open` controls the once-per-play transition.
- On the touch screen, tap a bottom indicator to switch Home/Music/Agents, tap a workflow to select it, then tap `RUN SELECTED`; Music transport and volume controls are also tappable.
- On Agents, joystick press, RUN, and APPROVE all run the selected workflow; left/right changes screens and up/down changes the selected workflow.
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

- [ ] Install the MPI3501-compatible `LCD35-show` display/touch driver and verify the 480 × 320 desktop appears before installing kiosk startup.
- [ ] Fit a stack-through GPIO header/breakout so the buttons, remapped joystick, and sensor remain reachable with the TFT installed.
- [ ] Wire the DHT22 data line to GPIO4 and confirm readings after startup.
- [ ] Wire joystick GPIO18/19/20/21/22 and buttons GPIO5/6/13/16; confirm pull-up logic, shared ground, and debounce.
- [ ] Connect speakers/headphones; verify the default PipeWire/PulseAudio sink and `wpctl` or `pactl` volume control.
- [ ] Pair the phone as a Bluetooth audio source if desired; verify audio reception and separately confirm whether a local MPRIS player is available.
- [ ] Set `mock_mode` to false, verify `/api/health` reports real mode, and check missing DHT22/player behavior is graceful.
- [ ] Run `scripts/setup-pi.sh`, reboot, and confirm Chromium opens Cockpit Home automatically on the TFT.

## Tests

From `backend/`, run `python -m unittest discover -s tests`. From `frontend/`, run `npm run build`.

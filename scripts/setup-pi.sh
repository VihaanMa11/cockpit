#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PI_USER="$(id -un)"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"

if [[ ! -f "$BACKEND/main.py" || ! -f "$FRONTEND/package.json" ]]; then
  echo "Run this script from a Cockpit checkout (scripts/setup-pi.sh)." >&2
  exit 1
fi

echo "Installing Cockpit dependencies for $PI_USER..."
sudo apt update
sudo apt install -y python3-full python3-venv python3-lgpio nodejs npm chromium

python3 -m venv --system-site-packages "$BACKEND/.venv"
"$BACKEND/.venv/bin/python" -m pip install --upgrade pip
"$BACKEND/.venv/bin/python" -m pip install -r "$BACKEND/requirements.txt" adafruit-circuitpython-dht

cd "$FRONTEND"
npm ci
npm run build

python3 - "$BACKEND/config.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
config = json.loads(path.read_text(encoding="utf-8"))
config["mock_mode"] = False
config.setdefault("joystick", {})["pins"] = {
    "up": 18,
    "down": 19,
    "left": 20,
    "right": 21,
    "press": 22,
}
config.setdefault("sensors", {})["dht22_gpio"] = 4
path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY

sudo tee /etc/systemd/system/cockpit.service >/dev/null <<EOF
[Unit]
Description=Cockpit desk console backend
After=network-online.target
Wants=network-online.target

[Service]
User=$PI_USER
WorkingDirectory=$BACKEND
ExecStart=$BACKEND/.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=2

[Install]
WantedBy=multi-user.target
EOF

CHROMIUM="$(command -v chromium || command -v chromium-browser || true)"
if [[ -z "$CHROMIUM" ]]; then
  echo "Chromium was not found after installation." >&2
  exit 1
fi

mkdir -p "$PI_HOME/.local/bin" "$PI_HOME/.config/labwc" "$PI_HOME/.config/lxsession/LXDE-pi"
cat > "$PI_HOME/.local/bin/cockpit-kiosk" <<EOF
#!/bin/sh
sleep 8
exec "$CHROMIUM" --kiosk --no-first-run --disable-infobars --disable-session-crashed-bubble http://127.0.0.1:8000/
EOF
chmod +x "$PI_HOME/.local/bin/cockpit-kiosk"
chown "$PI_USER":"$(id -gn "$PI_USER")" "$PI_HOME/.local/bin/cockpit-kiosk"

for autostart in "$PI_HOME/.config/labwc/autostart" "$PI_HOME/.config/lxsession/LXDE-pi/autostart"; do
  touch "$autostart"
  if ! grep -Fq "$PI_HOME/.local/bin/cockpit-kiosk" "$autostart"; then
    printf '\n%s &\n' "$PI_HOME/.local/bin/cockpit-kiosk" >> "$autostart"
  fi
  chown "$PI_USER":"$(id -gn "$PI_USER")" "$autostart"
done

if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_boot_behaviour B4 || true
fi

sudo systemctl daemon-reload
sudo systemctl enable --now cockpit

echo
echo "Cockpit is installed and will start at http://127.0.0.1:8000/ after desktop login."
echo "Reboot after confirming the TFT driver is installed: sudo reboot"
echo "Check backend status with: sudo systemctl status cockpit --no-pager"

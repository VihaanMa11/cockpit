#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
PI_USER="$(id -un)"
PI_HOME="$(getent passwd "$PI_USER" | cut -d: -f6)"
OS_CODENAME="$(. /etc/os-release && printf '%s' "${VERSION_CODENAME:-}")"

if [[ ! -f "$BACKEND/main.py" || ! -f "$FRONTEND/package.json" ]]; then
  echo "Run this script from a Cockpit checkout (scripts/setup-pi.sh)." >&2
  exit 1
fi

echo "Installing Cockpit dependencies for $PI_USER..."
sudo apt update
case "$OS_CODENAME" in
  trixie)
    # Raspberry Pi OS 13 split the desktop into these Wayland meta-packages.
    GUI_PACKAGES=(rpd-wayland-core rpd-theme)
    BOOT_MODE="B4"
    ;;
  bookworm)
    GUI_PACKAGES=(raspberrypi-ui-mods lightdm)
    BOOT_MODE="B4"
    ;;
  *)
    echo "Unsupported Raspberry Pi OS release '$OS_CODENAME'. Install its desktop environment first, then rerun this script." >&2
    exit 1
    ;;
esac
sudo apt install -y python3-full python3-venv python3-lgpio nodejs chromium playerctl pulseaudio-utils xinit xserver-xorg-core xserver-xorg-video-fbdev x11-xserver-utils xauth dbus-x11 "${GUI_PACKAGES[@]}"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm was not found. Install Node.js with its bundled npm, then rerun this script." >&2
  exit 1
fi

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
After=network.target

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

PI_UID="$(id -u "$PI_USER")"
TFT_FB=""
for fb_path in /sys/class/graphics/fb*; do
  [[ -r "$fb_path/name" ]] || continue
  if grep -qi 'ili9486' "$fb_path/name"; then
    TFT_FB="/dev/${fb_path##*/}"
    break
  fi
done
if [[ -z "$TFT_FB" ]]; then
  echo "Could not find the ILI9486 TFT framebuffer. Check that the TFT overlay is enabled and rebooted." >&2
  exit 1
fi

mkdir -p "$PI_HOME/.local/bin" "$PI_HOME/.config/labwc" "$PI_HOME/.config/lxsession/LXDE-pi" /etc/X11
cat > "$PI_HOME/.local/bin/cockpit-tft-kiosk" <<EOF
#!/bin/sh
xset -dpms
xset s off
exec "$CHROMIUM" --kiosk --start-fullscreen --window-position=0,0 --window-size=480,320 --force-device-scale-factor=1 --no-first-run --disable-infobars --disable-session-crashed-bubble http://127.0.0.1:8000/
EOF
chmod +x "$PI_HOME/.local/bin/cockpit-tft-kiosk"
chown "$PI_USER":"$(id -gn "$PI_USER")" "$PI_HOME/.local/bin/cockpit-tft-kiosk"

for autostart in "$PI_HOME/.config/labwc/autostart" "$PI_HOME/.config/lxsession/LXDE-pi/autostart"; do
  touch "$autostart"
  tmpfile="$(mktemp)"
  grep -Fv "$PI_HOME/.local/bin/cockpit-kiosk" "$autostart" > "$tmpfile" || true
  grep -Fv "$PI_HOME/.local/bin/cockpit-tft-kiosk" "$tmpfile" > "$autostart" || true
  rm -f "$tmpfile"
  chown "$PI_USER":"$(id -gn "$PI_USER")" "$autostart"
done

# GoodTFT's older login profile starts a separate X session on every shell login.
# Preserve a backup, then let the dedicated systemd service own the TFT X server.
if [[ -f "$PI_HOME/.bash_profile" ]] && grep -Eq 'startx|FRAMEBUFFER=/dev/fb[0-9]+' "$PI_HOME/.bash_profile"; then
  sudo cp -n "$PI_HOME/.bash_profile" "$PI_HOME/.bash_profile.lcd-show-backup"
  sudo sed -i -E -e '/startx/d' -e '/FRAMEBUFFER=\/dev\/fb[0-9]+/d' "$PI_HOME/.bash_profile"
  sudo chown "$PI_USER":"$(id -gn "$PI_USER")" "$PI_HOME/.bash_profile"
fi

sudo tee /etc/X11/xorg-cockpit-tft.conf >/dev/null <<EOF
Section "Device"
    Identifier "CockpitTFT"
    Driver "fbdev"
    Option "fbdev" "$TFT_FB"
EndSection

Section "Screen"
    Identifier "CockpitTFTScreen"
    Device "CockpitTFT"
    DefaultDepth 16
EndSection

Section "ServerLayout"
    Identifier "CockpitTFTLayout"
    Screen "CockpitTFTScreen"
EndSection
EOF

sudo tee /etc/systemd/system/cockpit-tft-kiosk.service >/dev/null <<EOF
[Unit]
Description=Cockpit-only kiosk on the SPI TFT framebuffer
After=cockpit.service user-runtime-dir@${PI_UID}.service
Wants=cockpit.service

[Service]
Type=simple
User=$PI_USER
Group=$(id -gn "$PI_USER")
SupplementaryGroups=video input
PAMName=login
WorkingDirectory=$BACKEND
Environment=HOME=$PI_HOME
Environment=FRAMEBUFFER=$TFT_FB
Environment=XDG_RUNTIME_DIR=/run/user/$PI_UID
TTYPath=/dev/tty8
StandardInput=tty
TTYReset=yes
TTYVHangup=yes
TTYVTDisallocate=no
ExecStartPre=/usr/bin/test -e $TFT_FB
ExecStart=/usr/bin/xinit $PI_HOME/.local/bin/cockpit-tft-kiosk -- :1 vt8 -keeptty -novtswitch -config /etc/X11/xorg-cockpit-tft.conf
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# Remove any framebuffer-copy service from the earlier mirrored-screen setup.
sudo systemctl disable --now cockpit-display-mirror.service 2>/dev/null || true

sudo systemctl set-default graphical.target
if command -v raspi-config >/dev/null 2>&1; then
  sudo raspi-config nonint do_boot_behaviour "$BOOT_MODE" || true
fi
sudo systemctl enable lightdm || true

sudo systemctl daemon-reload
sudo systemctl enable cockpit
sudo systemctl restart cockpit
sudo systemctl enable cockpit-tft-kiosk.service
sudo systemctl restart cockpit-tft-kiosk.service

echo
echo "The Raspberry Pi desktop stays on HDMI; Cockpit kiosk is assigned to $TFT_FB (TFT)."
echo "Reboot after confirming the TFT driver is installed: sudo reboot"
echo "Check backend status with: sudo systemctl status cockpit --no-pager"
echo "Check TFT kiosk status with: sudo systemctl status cockpit-tft-kiosk --no-pager"

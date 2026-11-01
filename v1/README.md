# Cockpit — desk console dashboard

A Raspberry Pi 4 reads 4 push buttons + 1 rotary encoder over GPIO and serves
a live web dashboard (FastAPI + WebSocket backend, React frontend) at
`http://<pi-ip>:8000`. Pressing a button launches a workflow (n8n / agent
webhook); turning the encoder scrolls the on-screen selection. See
`HARDWARE_SPEC.md` for the wiring and `MASTER_PROMPT.md` for the full spec.

---

## 1. Laptop dev (mock mode, no hardware needed)

**Backend:**

```bash
cd backend
python -m venv .venv
# Windows:            .venv\Scripts\activate
# macOS/Linux:         source .venv/bin/activate
pip install -r requirements.txt
```

**Frontend** (separate terminal):

```bash
cd frontend
npm install
npm run build
```

**Run the server** (serves the built frontend on the same port):

```bash
cd backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000**. The status bar will read **MOCK** — there's
no GPIO on a laptop, so the backend automatically falls back to mock mode
(logged clearly on startup). Use the on-screen **dev controls** panel
(Rotate ◀ / ▶, RUN, Approve, Stop, NEXT) to drive the whole flow:

- **Rotate** moves the highlighted workflow up/down the current screen's list
  (wraps at the ends).
- **NEXT** advances to the next screen (wraps after the last one), resetting
  the highlight to the top.
- **RUN** launches the highlighted workflow's webhook; the row flashes
  "▶ launching…" then "✓ done" / "✗ failed".
- **Approve** / **Stop** fire their own fixed webhooks regardless of screen/selection.

Every action appears instantly in the event log — that's the WebSocket push,
not polling.

> Note: with the placeholder `config.json` webhook URLs (`localhost:5678`),
> RUN/Approve/Stop will show "✗ failed" unless you have n8n running locally —
> that's expected and the intended graceful failure behaviour.

While iterating on frontend code you can instead run `npm run dev` in
`frontend/` (Vite dev server on :5173, proxying `/api` and `/ws` to :8000 —
see `vite.config.js`) alongside the backend, for hot reload.

---

## 2. Configure your webhooks

Edit `backend/config.json`. There are three kinds of entries to point at your
real n8n / agent webhook URLs:

- `buttons["2"].webhook` — the **Approve** button's webhook.
- `buttons["3"].webhook` — the **Stop** button's webhook.
- Each `screens[].workflows[].webhook` — one URL per workflow in the
  scrollable lists (add/remove/rename screens and workflows freely; the UI is
  fully config-driven).

`buttons["1"]` (RUN) and `buttons["4"]` (NEXT) have no webhook of their own —
RUN launches whatever workflow is currently highlighted.

Save the file and restart the backend (or just re-run RUN/Approve/Stop —
`config.json` is read once at startup, so restart uvicorn after edits).

---

## 3. Deploy to the Pi

**Option A — git:**

```bash
git clone https://github.com/VihaanMa11/cockpit.git
```

(This is a private repo — on the Pi you'll need to authenticate, e.g. `gh auth login` first if you have the GitHub CLI installed, or clone over SSH with a deploy key.)

**Option B — scp, from your laptop:**

```bash
scp -r cockpit <your-pi-username>@<pi-ip>:/home/<your-pi-username>/
```

Then, over SSH on the Pi:

```bash
sudo apt update
sudo apt install -y python3-lgpio   # prebuilt GPIO backend — avoids compiling lgpio via pip

cd ~/cockpit/backend
python -m venv --system-site-packages .venv   # --system-site-packages lets the venv see apt's python3-lgpio
source .venv/bin/activate
pip install -r requirements.txt     # installs gpiozero + fastapi/uvicorn/httpx

# Node.js is not preinstalled on Raspberry Pi OS — install it (skip if
# `node --version` already prints v18+):
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

cd ../frontend
npm install
npm run build                     # or scp your laptop's prebuilt frontend/dist/ across instead

cd ../backend
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

From your **laptop** browser, go to `http://<pi-ip>:8000` (find the Pi's IP
with `hostname -I` on the Pi). The status bar should now read **REAL** —
that means real GPIO initialised successfully.

---

## 4. Auto-start on boot

```bash
sudo cp ~/cockpit/backend/cockpit.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable cockpit.service
sudo systemctl start cockpit.service
```

`cockpit.service` is already filled in for user `vihaan1106` at
`/home/vihaan1106/cockpit`. If you ever move the project or use a different
user, edit `User`, `WorkingDirectory`, and `ExecStart` in that file first.

Check status/logs with `systemctl status cockpit` / `journalctl -u cockpit -f`.

Once enabled, the dashboard comes up automatically on every boot/reboot — no
more SSH-in-and-run-uvicorn. To stop relying on it temporarily (e.g. to run
the backend manually in a foreground terminal for debugging), stop the
service first so it doesn't fight over port 8000: `sudo systemctl stop
cockpit.service`.

---

## 5. Wiring (BCM pin numbers — see HARDWARE_SPEC.md for full detail)

| Component              | GPIO (BCM) | Other leg |
|-------------------------|-----------|-----------|
| Button 1 — RUN           | GPIO5     | GND rail  |
| Button 2 — Approve       | GPIO6     | GND rail  |
| Button 3 — Stop          | GPIO13    | GND rail  |
| Button 4 — NEXT          | GPIO16    | GND rail  |
| Encoder A (outer pin)    | GPIO17    | —         |
| Encoder B (outer pin)    | GPIO27    | —         |
| Encoder C (common)       | GND       | —         |

Buttons use the Pi's internal pull-ups (no external resistors). The encoder
is a bare 3-pin type with **no push switch** — RUN is the only launch
control. All GND legs share one common ground rail back to any Pi GND pin.

---

## 6. Troubleshooting

- **`npm: command not found` on the Pi:** Node.js isn't preinstalled on
  Raspberry Pi OS. Install it with `curl -fsSL
  https://deb.nodesource.com/setup_20.x | sudo -E bash -` then `sudo apt
  install -y nodejs` (as shown in section 3), then retry `npm install && npm
  run build` in `frontend/`.
- **Can't reach `http://<pi-ip>:8000` from your laptop:** confirm both
  devices are on the same WiFi, confirm the Pi's IP with `hostname -I`, and
  confirm the server log says `Uvicorn running on http://0.0.0.0:8000` (not
  `127.0.0.1` — if it says that, the bind host in your run command is wrong).
  Also check the Pi's firewall (`sudo ufw status`) isn't blocking port 8000.
- **Status bar stuck on MOCK on the Pi:** check the startup log line from
  `hardware.py` — it prints the real GPIO init error (`No module named
  'lgpio'` means the venv can't see it). Fix: `sudo apt install -y
  python3-lgpio`, then recreate the venv **with** `--system-site-packages`
  (`python -m venv --system-site-packages .venv`) so it picks up the
  apt-installed module — a plain `.venv` without that flag won't see it. Also
  make sure you're in the `gpio` group (`sudo usermod -aG gpio $USER`, then
  log out/in).
- **`pip install` fails building `lgpio` wheel (`swig: No such file or
  directory` etc.):** you're hitting the exact problem the apt-based install
  above avoids — `lgpio` isn't in `requirements.txt` on purpose. Don't
  `pip install lgpio` directly; use `sudo apt install -y python3-lgpio` +
  `--system-site-packages` as shown in section 3.
- **Pin factory errors:** make sure you're on Raspberry Pi OS with the
  `lgpio` library available, and that no other process (old pigpiod, another
  instance of this app) is holding the GPIO lines.
- **A button/encoder never registers:** almost always a loose wire or a
  missing ground — recheck that leg and the shared GND rail before suspecting
  the code.
- **Webhook shows "✗ failed":** check the URL in `config.json`, confirm the
  n8n workflow is **active**, and confirm the Pi can reach that URL (e.g.
  `curl` it from the Pi over SSH).

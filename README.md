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
cd ~/cockpit/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # installs gpiozero + lgpio (ARM-only marker) + fastapi/uvicorn/httpx

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

Before installing, open `backend/cockpit.service` and fix `User`,
`WorkingDirectory`, and `ExecStart` if your username or install path differ
from `pi` / `/home/pi/cockpit`.

Check status/logs with `systemctl status cockpit` / `journalctl -u cockpit -f`.

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

- **Can't reach `http://<pi-ip>:8000` from your laptop:** confirm both
  devices are on the same WiFi, confirm the Pi's IP with `hostname -I`, and
  confirm the server log says `Uvicorn running on http://0.0.0.0:8000` (not
  `127.0.0.1` — if it says that, the bind host in your run command is wrong).
  Also check the Pi's firewall (`sudo ufw status`) isn't blocking port 8000.
- **Status bar stuck on MOCK on the Pi:** check the startup log line from
  `hardware.py` — it prints the real GPIO init error. Common causes: `lgpio`
  didn't install (`pip install lgpio` or `sudo apt install -y
  python3-lgpio`), or you're not in the `gpio` group (`sudo usermod -aG gpio
  $USER`, then log out/in).
- **Pin factory errors:** make sure you're on Raspberry Pi OS with the
  `lgpio` library available, and that no other process (old pigpiod, another
  instance of this app) is holding the GPIO lines.
- **A button/encoder never registers:** almost always a loose wire or a
  missing ground — recheck that leg and the shared GND rail before suspecting
  the code.
- **Webhook shows "✗ failed":** check the URL in `config.json`, confirm the
  n8n workflow is **active**, and confirm the Pi can reach that URL (e.g.
  `curl` it from the Pi over SSH).

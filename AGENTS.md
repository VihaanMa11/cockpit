# Cockpit v2 contributor notes

## Run locally

- Backend: `cd backend`, create/activate a Python virtual environment, `pip install -r requirements.txt`, then `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.
- Frontend development: in another terminal run `cd frontend`, `npm install`, `npm run dev`; Vite proxies API and WebSocket requests to port 8000.
- Production: run `npm run build` in `frontend/`; FastAPI serves `frontend/dist` from port 8000.
- Hardware is auto-detected; unavailable GPIO, DHT22, and MPRIS devices must leave the backend in mock/degraded operation, not prevent startup.
- Pi deployment: install the MPI3501 TFT driver first, then run `scripts/setup-pi.sh` from the checkout root. The script generates the service unit for the active Pi username/path and configures desktop kiosk startup.

## Conventions

- Keep hardware integrations behind backend adapters and emit the common configured input events.
- Touch UI control requests must be same-origin loopback only; never expose workflow-triggering control routes to LAN clients.
- Keep screen content and physical pin/mapping choices in `backend/config.json`; do not put webhook secrets in source code.
- MPI3501 display/touch occupies BCM GPIO7–11, 17, 24, and 25. Keep joystick on BCM 18/19/20/21/22, buttons on 5/6/13/16, and DHT22 data on GPIO4. A stack-through header or GPIO breakout is required to reach pins covered by the display.
- Keep existing backend capabilities available even when the current UI does not expose them.
- The supported display target is 480 × 320 landscape; keep body copy legible at that size.

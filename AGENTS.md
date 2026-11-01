# Cockpit v2 contributor notes

## Run locally

- Backend: `cd backend`, create/activate a Python virtual environment, `pip install -r requirements.txt`, then `python -m uvicorn main:app --host 0.0.0.0 --port 8000`.
- Frontend development: in another terminal run `cd frontend`, `npm install`, `npm run dev`; Vite proxies API and WebSocket requests to port 8000.
- Production: run `npm run build` in `frontend/`; FastAPI serves `frontend/dist` from port 8000.
- Hardware is auto-detected; unavailable GPIO, DHT22, and MPRIS devices must leave the backend in mock/degraded operation, not prevent startup.

## Conventions

- Keep hardware integrations behind backend adapters and emit the common configured input events.
- Keep screen content and physical pin/mapping choices in `backend/config.json`; do not put webhook secrets in source code.
- Keep existing backend capabilities available even when the current UI does not expose them.
- The supported display target is 480 × 320 landscape. Avoid touch-dependent interaction and keep body copy legible.

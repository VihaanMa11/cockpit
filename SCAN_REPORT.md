# Scan report

## Structure and run paths

- `backend/` contains the FastAPI app, GPIO adapter, webhook helper, JSON config, requirements, and systemd service.
- `frontend/` contains a React 18 app built with Vite, source components and hooks, and the npm lockfile.
- For laptop development: install `backend/requirements.txt`, run `uvicorn main:app --host 0.0.0.0 --port 8000` from `backend/`, and run `npm run dev` from `frontend/` (Vite proxies `/api` and `/ws`). For production, build the frontend and let FastAPI serve `frontend/dist`.

## Frontend

- React with Vite; no router dependency. `App.jsx` switches rendered content based on the backend's configured screen index.
- Styling is plain CSS in `src/styles.css`, currently using a flexible dashboard layout and a responsive breakpoint.
- The current components include tabs, a workflow list, action indicators, event log, status bar, and mock dev controls. The WebSocket hook consumes complete state snapshots from `/ws`.

## Backend and state

- `main.py` loads `backend/config.json` at import time, owns screen/selection/button/action/event state, handles mock or GPIO callbacks, and broadcasts state snapshots over `/ws`.
- `/api/config` returns the config, `/api/health` reports mode, and `/api/dev/press/{button_id}` plus `/api/dev/rotate/{direction}` simulate input in mock mode.
- `actions.py` posts JSON to configured webhooks with a three-second timeout. Config currently defines four workflow screens and four button roles.

## Hardware and mock mode

- `hardware.py` configures gpiozero with `LGPIOFactory`, falling back to mock mode on initialization failure.
- Existing BCM pin assignments are buttons 1–4 on GPIO5/6/13/16, plus a bare rotary encoder on GPIO17/27. Buttons use 50 ms debounce. The adjacent `HARDWARE_SPEC.md` documents this wiring and the existing laptop mock behavior.
- There is no DHT22, Wi-Fi, CPU-temperature, ENS160, INA219, joystick, MPRIS/music, or keyboard-event implementation in the app. The current encoder is not a 5-way switch.

## Reusable pieces

- Reuse the FastAPI app/lifespan, config endpoint, WebSocket state snapshots, webhook timeout helper, and GPIO-to-async callback pattern.
- The current workflow list and `post_webhook` helper can be adapted for the Agents screen; mock input endpoints provide a starting point for keyboard-driven development.

## Gaps and inconsistencies

- The current app shows arbitrary config-defined screens and workflow lists, not the requested fixed Home/Music/Agents UI.
- Existing wiring documentation calls button 4 NEXT and specifies the rotary encoder. The v2 design replaces encoder wiring with a 5-way joystick on GPIO17/27/22/23/24 and changes button 4 to VOICE; physical wiring must match that documented assumption.
- No test or lint scripts are defined in `frontend/package.json`; no test suite was found in the app. The current webhook helper only posts, uses a fixed timeout, and returns a boolean.
- `README.md` explains the current dashboard, webhooks, Pi deployment, and systemd service, but not Chromium kiosk mode, sensors, Bluetooth, or music playback.

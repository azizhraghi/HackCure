# Replaced by `mobile/`

This copy of the app was merged into `mobile/` (2026-10-11) so the team has one app:

- Kept from here: sign-in / account creation (`AuthScreen`), the SurgiGuard API client (`services/backend.ts`,
  `hooks/useBackend.ts`), ESP32 live vitals (`LiveVitals`), family linking, device-alert watcher and family screens.
- In `mobile/` the app talks to two servers, both editable in Settings:
  `apiUrl` = AI backend (FastAPI: care plan, check-in, assistant, twin) and `accountUrl` = SurgiGuard API (.NET, ngrok).
- "Continue without an account (demo)" opens the app on the AI backend's demo patient when the .NET API is not running.
- The ESP32 device id is no longer asked when creating an account (link the board with `PUT /api/patients/me/device`
  or `seed_story.py`).

Build the phone app from `mobile/` (`npm install`, `npm run android`); the browser build is `npm run build:web`.

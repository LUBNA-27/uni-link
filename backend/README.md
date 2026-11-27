# UniLink 2.0 — backend (Rev. E)

FastAPI + Pydantic v2 + h3 + google-genai. All transport, fares and wallets are **simulated** (`"source": "simulation"`); no dispatch, no real money.

## Run (Replit)

```bash
pip install -r requirements.txt
python -m pytest backend/tests -q                                   # full suite
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}        # serves /api/* and frontend/dist on one origin
```

Replit `.replit` run command: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`
Secrets: `GEMINI_API_KEY` (Replit Secrets only). Optional env: `CORS_ORIGINS` (comma list, dev only), `UNILINK_DATA_DIR` (path to `data/`), `UNILINK_DOCS=0` to hide `/docs`.

## Fixtures

`backend/fixtures/*.json` are reference fixtures built to the Rev. E §06/§13 golden path (seed 2026, 60 synthetic riders). They are used by default so the backend and tests run without `data/`. Once Rawan's `data/` matches this schema, point `UNILINK_DATA_DIR` at it and re-run pytest. `/api/health` reports which source is live.

Leg-duration convention: each leg stores `off_min` and an already-traffic-adjusted `peak_min` (07:30–08:30). A `traffic` event applies its multiplier once to `off_min`, rounded up. Pickup time = arrival at the door, then a dwell of 1 min (3 min for a wheelchair). Without a preferred pickup, the route is scheduled backwards to `class_start − buffer − 5 min slack`, then replayed forwards.

## Endpoints

`GET /api/health` · `POST /api/timetable/parse` (multipart; PNG/JPEG/WebP, ≤ 5 MB) · `POST /api/timetable/manual` · `POST /api/timetable/confirm` · `POST /api/plan` · `POST /api/trips/confirm` · `POST /api/trips/shift-class` · `POST /api/trips/emergency` · `POST /api/trips/split-invite` · `POST /api/parcels/quote` · `GET /api/simulation/state?session_id=` · `POST /api/simulation/event` · `POST /api/voice/intent` · `GET /api/insights?session_id=`

Errors are always `{"error": {"code", "message"}}`.

## Consent / revision rules

- Quotes (`/api/plan`) and proposals have no side effects. `plan_revision` starts at 1 and increments on each booking commit, event and reset.
- Rescue proposals need every *affected* rider (fare up, new rider, or pickup time changed) to call `/api/trips/confirm` with the proposal id, the current revision and their new fare. Nothing is charged until the last consent arrives; then all charges are applied together.
- A stale revision returns 409 `STALE_PLAN`. Reusing the same idempotency key replays the earlier result, and reusing it with a different payload returns 409.

## Where this follows Rev. E over the build prompt

| Topic | Build prompt | Implemented (Rev. E master wins) |
|---|---|---|
| Co-rider cancel time | 07:20 | **06:55**, so the 07:05 Class Shift comes *after* the rescue is accepted |
| Class Shift refund | 1,860 | **1,900** (actual revised paid amount) → wallet 12,000 → 10,140 → 10,100 → 10,140 |
| Best Deal relaxations | includes `fare_cap` | fare cap is **never relaxed**; above-cap routes appear as `unbookable_comparisons` |
| H3 clustering | res-8 `grid_disk k=1` as the matching cluster | corridor riders are about 2 km apart (wider than k=1), so matching uses fixture zones; H3 k=1 gates Emergency insertion |

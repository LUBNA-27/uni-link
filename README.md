# UniLink 2.0 — Campus Commute

> **Track 02: Student & Commuter Mobility** · Built for the **Jeeny Next Stop Mobility × AI Hackathon**  
> A Jeeny-integrated smart student mobility feature combining AI timetable parsing, constrained corridor carpooling, integer-fils fare splitting, accessibility-first routing, and real-time trip replanning.

> [!NOTE]
> **Hackathon Simulation Notice:** All demand, dispatch, traffic, tariffs, bookings, and wallet ledger transactions in this prototype are **simulated** (`"source": "simulation"`). No real vehicles are dispatched and no real payments are processed.

---

## Why UniLink 2.0?

University commuters in Jordan face high daily solo ride costs, rigid class schedules, uncoordinated carpool matching, and unreliable pickup options—especially for women-only pools and wheelchair users. **UniLink 2.0** adds a dedicated **Campus Commute** flow inside Jeeny that turns a student's weekly timetable into pre-matched, policy-safe, dynamically rescued campus trips.

---

## Core Features & UX

- **Timetable-to-Trip Intake (`Schedule`):** Upload a timetable photo (`PNG` / `JPEG` / `WebP`, up to 5 MB) parsed by Gemini into structured `Sun–Thu` classes with uncertain-field flags, or enter/edit classes manually. Without `GEMINI_API_KEY`, the API returns `503 VISION_UNAVAILABLE` rather than fabricating results.
- **Constraint-Safe Ride Matching & Best Deal (`Trip` & `Journey`):** Matches corridor riders across supported zones (`irbid_east` → `JUST`, `irbid_nuzha` → `JUST`, `sweileh` → `AAU`). Hard filters—**gender pool** (`female_only` / `male_only`), **vehicle capacity**, **class arrival deadline**, **wheelchair / Big Car requirements**, and **fare cap**—are never relaxed. Soft preferences (companion count, departure window, or `main_road_shuttle` feeder mode) relax cleanly under **Best Deal** proposals.
- **Integer-Fils Leg-Weighted Pricing (`pricing.py`):** Uses exact `Fraction` arithmetic and largest-remainder allocation with conservation checks (`PricingInvariantError`) so rider shares reconcile to the vehicle total without floating-point drift. Includes **Ride & Box** sealed parcel quotes (up to 5 kg, blocked on wheelchair trips) and **Split-Link** co-rider invites.
- **Accessibility-First Mobility:** Wheelchair requests require a ramp-equipped `WAV` vehicle and are never downgraded to a sedan; unavailable WAV capacity surfaces an honest `no_accessible_route` hand-off. Accessible drop-off metadata explicitly marks `verified: false` (synthetic fixture).
- **Smart Rescue, Class Shift & Emergency Insertion (`Booked`):** Handles co-rider cancellations, traffic delays, full shuttles, and vehicle unavailability with multi-rider consent tracking, atomic next-class rebooking (`/api/trips/shift-class`), en-route emergency seat insertion (`/api/trips/emergency`), idempotency keys, and `409 STALE_REVISION` protection.
- **Bilingual (`EN` / `عربي`) UX & Fleet Insights (`Insights`):** Full English and Arabic RTL UI (`193` audited strings), deterministic whitelist-only bilingual voice intent read-back (`/api/voice/intent`), and session-computed fleet metrics (`/api/insights`).

---

## System Architecture & Tech Stack

```
┌──────────────────────────────────────────────────────────────────────┐
│  Frontend (frontend/) — React 19 · TypeScript · Vite 8 · Tailwind v4 │
│  Screens: Schedule · Trip · Journey · Booked (Pass) · Insights       │
│  Bilingual EN/AR (i18n.ts, useT.ts) · Live-by-default API client     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ Same-origin HTTP/JSON (/api/*)
┌──────────────────────────────────▼───────────────────────────────────┐
│  Backend (backend/) — FastAPI · Pydantic v2 · H3 · Uvicorn           │
│  • main.py        FastAPI app, security headers, static dist mount   │
│  • contract.py    External Pydantic wire contract (mirrors types.ts) │
│  • wire.py        Wire adapter, consent, decline/cancel, 409 checks  │
│  • replanner.py   Unified engine: plan, rescue, class shift, emerg.  │
│  • pricing.py     Exact Fraction integer-fils split & parcel quotes  │
│  • matching.py    Pool eligibility, accessibility & H3 emergency     │
│  • routing.py     Door-to-door & main-road shuttle timing            │
│  • vision.py      Gemini structured timetable extraction             │
│  • voice.py       Deterministic bilingual voice intent classifier    │
│  • state.py       Thread-safe, LRU-bounded in-memory SessionStore    │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │ Optional AI vision extraction
┌──────────────────────────────────▼───────────────────────────────────┐
│  Google Gemini (google-genai) via GEMINI_API_KEY (Replit Secrets)    │
└──────────────────────────────────────────────────────────────────────┘
```

### API Endpoints
- `GET /api/health` · `GET /api/insights` · `GET /api/simulation/state`
- `POST /api/timetable/parse` · `POST /api/timetable/manual` · `POST /api/timetable/confirm`
- `POST /api/plan` · `POST /api/trips/confirm` · `POST /api/trips/shift-class` · `POST /api/trips/emergency`
- `POST /api/trips/split-invite` · `POST /api/parcels/quote` · `POST /api/simulation/event` · `POST /api/voice/intent`

---

## Quick Start

### 1. Local Development
**Prerequisites:** Python 3.11+ and Node.js 22.12+

```bash
# Install backend dependencies
python -m pip install -r requirements.txt

# Build the frontend production bundle (served by FastAPI on the same origin)
cd frontend
npm ci --include=dev
node scripts/check-i18n.mjs
npm run build
cd ..

# Start the single-worker FastAPI server
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Open `http://localhost:8000` (app) and `http://localhost:8000/api/health` (health check). Append `?live=mock` only for offline UI QA.

### 2. Run Tests & Evaluations
```bash
# Full backend + contract + pricing + variation suite (skips live Gemini without a key)
python -m pytest backend/tests -v -rs

# Live Gemini vision test (requires GEMINI_API_KEY in environment)
python -m pytest backend/tests/test_gemini_live.py -q -s -rs

# Live HTTP smoke & Gemini eval against a running server
python -m backend.smoke_live http://localhost:8000
python -m backend.eval.gemini_eval http://localhost:8000
```

### 3. Replit Deployment
1. Import this repository into Replit (pre-configured via [`.replit`](.replit) and [`scripts/replit_run.sh`](scripts/replit_run.sh)).
2. Add the following in **Replit Secrets** (never commit keys to `.env` or source files):
   - `GEMINI_API_KEY` — your Google Gemini API key
   - `GEMINI_MODEL` *(optional)* — `gemini-3.8-flash` (default)
   - `GEMINI_THINKING_LEVEL` *(optional)* — `low` (for compatible Gemini 3.x models)
3. Deploy as a **single instance** (`deploymentTarget = "gce"`, `--workers 1`), because session state and trip revisions live in memory.

---

## Repository Structure

```text
uni-link/
├── backend/                  # FastAPI app, replanning/pricing engines, fixtures, evals & pytest suite
│   ├── fixtures/             # Anonymous synthetic riders, vehicles, shuttles, hubs, zones & tariffs
│   ├── eval/                 # Ground-truth timetable images (demo_A/B/C) & Gemini eval runner
│   └── tests/                # Unit, wire-contract, variation-grid & Gemini eval tests
├── frontend/                 # React + TypeScript + Vite student app (EN/AR)
│   ├── scripts/check-i18n.mjs
│   └── src/                  # Screens (Schedule, Trip, Journey, Booked, Insights) & components
├── docs/
│   ├── competition/          # Playbook, judging panel, business model, pitch rubric & survey docs
│   └── openapi.json          # API specification
├── evidence/                 # Captured team verification logs (pytest, smoke, browser E2E, variation)
├── scripts/                  # Replit launch script, browser E2E & fixture generator
├── .replit                   # Replit build, run, port 8000 & single-worker GCE deployment config
├── requirements.txt          # Python dependencies
├── RELEASE_START_HERE.md     # Merged release candidate runbook
└── BUILD_STATUS.md           # Integration milestone notes
```

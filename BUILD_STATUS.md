> **Merge update:** see `RELEASE_START_HERE.md` for the current release instructions and checks. This document is the original backend-team report, not fresh test evidence. Its older mock defaults and setup instructions are superseded.

# UniLink 2.0 — BUILD_STATUS (integration milestone)

_Updated 2026-11-27 ~17:40 Amman. Business logic: Rev. E master. Wire format: `frontend/src/types.ts` + `06_Frontend_Contract_for_Ranad` (round 2)._

## What was assembled
- **Frontend:** Lubna's source copied verbatim from project docs 07–10 into `frontend/`. No component, screen, `api.ts`, `types.ts` or `mock.ts` was changed. `DEFAULT_LIVE` flags are untouched.
- **Backend:** Ranad's engine is unchanged in behaviour (routing, pricing, replanner, state, vision). A thin compatibility layer converts between the engine and Lubna's wire format:
  - `backend/contract.py`: Pydantic mirror of `types.ts`
  - `backend/wire.py`: shape conversion plus decline / cancel_trip / peer-consent
- `backend/main.py` is Ranad's app, not the health-check shell. It serves `frontend/dist` on the same origin.
- **Rider fixtures:** `display_name` and `phone` removed. Every numeric value is preserved; Rawan's dataset is not swapped in yet.

## Test results (actual)
| Check | Command | Result |
|---|---|---|
| Backend + contract tests | `python -m pytest backend/tests -q` | **87 passed, 1 skipped** (skipped = live Gemini, see below) |
| Frontend production build | `cd frontend && npm install && npm run build` | **built** (`tsc -b` strict + vite) |
| Live HTTP smoke test (uvicorn, real sockets) | `python -m backend.smoke_live [URL]` | **SMOKE PASSED**: timetable → BD1 1860/08:17/85.25, BD2 1565/08:08/80.00 → book (12000→10140) → cancel 06:55 → R2 1900 (+40) → requester approves (no charge) → peer consent → 10100 → class shift 07:05 refund 1900 / new 1860, 10:47/10:53/10:58 → 11:15 → 10140; ledger debit 1860, debit 40, refund 1900, debit 1860. Zaid (separate session): WAV-01 2700 / 08:45, then WAV-01 out → `no_accessible_route`. Round trips 2–7 ms locally. |
| Browser E2E (headless Chrome, `?live=all`) | `python scripts/browser_e2e.py` | **PASSED, 0 console errors**: same journey clicked through Lubna's UI, plus Zaid's WAV pass and no-option screen |
| Gemini (mocked model) | part of pytest | passing: schema/temperature/thinking config, injection text treated as data, MIME/size checks, key never leaked |
| **Gemini live accuracy** | `python -m backend.eval.gemini_eval https://<app>.replit.app` | **NOT RUN (no key)** |
| **Gemini (real API call)** | `GEMINI_API_KEY=… UNILINK_TIMETABLE_IMAGE=path.png python -m pytest backend/tests/test_gemini_live.py -q -s` | **NOT RUN**: no key in this workspace. Never claim live inference until this passes. |

## P0 integration fixes (all 12 done)
1. Timetable upload accepts the multipart field `image` (`file` also accepted).
2. Timetable responses use `{id, course, weekday Sun–Thu, start, end?, room?}`. `uncertain_fields` are `{class_id, field, reason}`. `inference_source` is `gemini_vision` only when the model was actually called; manual entry returns `manual`. Without a key, parse returns 503 `VISION_UNAVAILABLE` and never fakes a result.
3. Timetable confirm returns `{session_id, confirmed, class_count, invalidated_plans}`. If the schedule changes, pending quotes are dropped and the revision increments, so an old plan gets a 409.
4. Each PlanOption includes:
   - pickups with synthetic landmarks
   - `fare.shares`
   - vehicle `{kind, label, wheelchair_accessible}`
   - `accessible_dropoff` with `verified: false` and its source labelled synthetic
   - `hard_filters_passed`, built from the checks the engine actually ran
   - `flags` and `deadline`
   - `relaxed: null` on exact matches
5. Confirm responses use the contract statuses (`confirmed`, `awaiting_consent`, `declined`, `canceled`), plus `revision`, `wallet.balance_fils`, `amount_paid_fils` and `pending_consents`.
6. Smart Rescue, Class Shift and Emergency all return the same Proposal shape. `plan.plan_id` equals `proposal_id`. Above-cap options appear as `alternatives` with `selectable: false`.
7. Simulation state includes trips (with plan and amount paid), pending proposals and the wallet with ledger entries `{at, kind, amount_fils, note}`. Every amount is positive and marked debit or refund.
8. The simulation event accepts `cancel` and `peer_consent`. Peer consent covers only the synthetic co-riders on the targeted pending proposal. It never covers the requester or the session's own rider.
9. Confirm supports `decision: accept | decline | cancel_trip`. `replaces_trip_id` is checked, and the Class Shift replacement is atomic.
10. Emergency requests enforce the gender pool, wheelchair (never a sedan), Big Car, fare cap and sharing opt-in, and check the rider is eligible for the pool. A solo hand-off is offered only within the fare cap.
11. Errors use `{code, message, current_revision?}`. A stale request returns 409 `STALE_REVISION` with `current_revision`.
12. No names or phone numbers in fixtures. A test scans every response for coordinates, names and phones.

## 17:20 update
- **`DEFAULT_LIVE` is now all `true`** in `frontend/src/api.ts`. The plain URL runs the real backend and the MOCK banner is gone. The browser E2E was re-run on the plain URL (no `?live=`): **PASSED, 0 console errors**. Mocks remain only as a dev fallback, reachable by setting a flag back to false.
- **Live Gemini check is ready but NOT YET RUN.**
  - `backend/eval/demo_A.png` and `demo_B.png` are synthetic, clean, computer-drawn timetables with hand-written `*.truth.json`.
  - `python -m backend.eval.gemini_eval <URL>` uploads them exactly as the UI does and prints the HTTP status, latency, field accuracy and whether demo_A and demo_B give different first classes.
  - Without a key it currently prints `503 VISION_UNAVAILABLE` for both images; it never fakes a result.
  - Also test 2–3 real, redacted student timetable photos before quoting accuracy; synthetic images are the easy case.

## 17:45 update — verification & evidence (raw outputs in `evidence/`)
| Run | Result |
|---|---|
| Full backend suite `python -m pytest backend/tests -q -rs` | **118 passed, 5 skipped** (all 5 = live Gemini, no key) → `evidence/pytest_full.txt` |
| Live HTTP smoke `python -m backend.smoke_live` | **SMOKE PASSED** → `evidence/smoke_live.txt` |
| Browser E2E, plain URL | **PASSED, 0 console errors** → `evidence/browser_e2e.txt` |
| Planner variation `test_variation.py` (19 tests incl. 240-combination invariant grid) | **passed** → `evidence/variation_report.txt` |
| Gemini checker self-test (fake model outputs, NOT inference) `test_gemini_eval_logic.py` | **12 passed**: a faithful extraction passes; invented class, wrong time, wrong weekday, empty extraction, a guessed value for an unreadable field, missing telemetry and a key leak all FAIL as they should |
| **Live Gemini inference** `test_gemini_live.py` / `python -m backend.eval.gemini_eval <URL>` | **NOT RUN: no `GEMINI_API_KEY` here.** All three eval images return `503 VISION_UNAVAILABLE` → `evidence/gemini_eval_no_key.txt`. No accuracy, latency or token figures exist yet. |

**Live Gemini checks (per image, against hand-written `*.truth.json`):**
- at least one class extracted
- weekday, course and start match the truth
- no invented classes
- unreadable fields are left empty or flagged
- `inference_ms` and token `usage` are reported (they are now additive fields on the parse response)
- the API key never appears in the response

Also checked across images: at least two distinct images, and distinct images give distinct schedules. The eval images are `demo_A`, `demo_B` and `demo_C`. In `demo_C` the room cell is empty and one start time is blotted out on purpose. To score real photos, put redacted images plus your own truth files in a folder and set `UNILINK_TIMETABLE_DIR`.

**Planner variation, computed results (excerpt):**
| Input changed | Result |
|---|---|
| companions 2 | exact M1 1860, 08:17 |
| companions 1 | pair 2490 > cap, so Best Deal → shuttle 1210 |
| companions 0 | none at cap 2000; solo 4260, 08:11 at cap 5000 |
| cap 1565 / 1859 | only BD 1565 |
| cap 1860 | 1860 + 1565 |
| cap ≤ 1564 | no option |
| pickup 07:40 (c=2) | 07:40 / 07:47 / 07:52 → 08:13 |
| pickup 07:54 (c=2) | late, so Best Deal shuttle 940 or depart −10 |
| 11:30 class, pickup 10:47 | R-4HN, R-8PX, 11:15 |
| class 08:00 / 09:00 | honest no-option |
| all sedans unavailable | Big Car rates (shuttle 1000; door 2250 at cap 5000) |
| sedans and Big Cars unavailable | no option |
| Big Car required | never dropped |

**Findings (not changed; team decision needed):**
1. **Stale preferred pickup.** The Trip screen defaults `preferred_pickup` to 07:44 for every class. For an 11:30 class with 07:44 still in the form, the planner returns a valid plan that arrives at 08:17, more than three hours early. That plan is allowed under the current rules, which have no "too early" limit. Options: the UI derives the default pickup from the chosen class (Lubna), or the backend adds a maximum-early-arrival rule. That would be new behaviour, so it was not added without agreement.
2. **Class 08:45 gives the same output as 08:30.** The preferred pickup is fixed at 07:44, and the 08:30 companions fall inside the ±15-minute window. This is expected, but when demonstrating variation, change the pickup time as well as the class.

## API readiness: endpoints Lubna can flip to LIVE now
`parse` (once `GEMINI_API_KEY` is set; it returns a clean 503 without one), `manual`, `confirmTT`, `plan`, `confirm`, `shift`, `emergency`, `state`, `event`, `health`. All of these were exercised by the browser test with `?live=all`.

To go live, either set `DEFAULT_LIVE` in `frontend/src/api.ts` (Lubna's file) or demo with `?live=all`. With every flag live, the MOCK banner disappears.

## Unresolved / for the team
- **Reconstructed files.** `frontend/package.json`, `package-lock.json`, `tsconfig*.json` and `public/favicon.svg` were not in the project docs, so I wrote minimal stand-ins. The build is green with them. **Lubna: replace them with your originals if you have them.**
- **Zaid demo session.** DevDrawer's "Load Zaid demo" keeps the current session id. To keep Sara and Zaid separate as agreed, open Zaid with `?session=<other id>`; the browser test did this. Changing that button is Lubna's call.
- **No-option proposals.** A rescue with no feasible option (e.g. WAV-01 lost after Zaid booked) has no Proposal shape in `types.ts` because `plan` is required. It shows instead as trip flags `VEHICLE_UNAVAILABLE` and `OPERATOR_ASSISTANCE_REQUIRED`, and no sedan is ever proposed.
- **Additive fields.** `PlanResponse` also carries `compute_ms`, `audit`, `rejected` and `unbookable_comparisons` as measured evidence. TypeScript ignores them.
- **Not touched in this milestone:** voice, parcels, Split-Link, insights. Their behaviour is unchanged and their tests pass.

## Run commands
```bash
pip install -r requirements.txt
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}     # app + API on one origin
python -m pytest backend/tests -q                                 # tests
python -m backend.smoke_live http://localhost:8000                # live API smoke (or the Replit URL)
```
Replit: the `.replit` file is Lubna's original. For the `GEMINI_API_KEY` secret, use Secrets only.

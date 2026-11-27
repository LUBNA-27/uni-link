# Frontend ⇄ backend contract requests (Lubna → Ranad)

Source of truth: Rev. E master §10. Types live in `frontend/src/types.ts`; client + per-endpoint flags in `frontend/src/api.ts`.
Everything below marked **ADD** is NOT in §10 but the UI needs it. Please accept/reject in the 10-minute schema sync BEFORE freezing `schemas.py`.

## Conventions the UI relies on
- Money = integer fils. Time = "HH:MM". Errors = `{code, message}` (FastAPI `{detail:{code,message}}` also accepted). 409 must include `current_revision`.
- `GET /api/simulation/state?session_id=…` (query param).
- Never return raw home pins; pickups use synthetic landmark labels.

## /api/plan response — ADD to each option
| Field | Why |
|---|---|
| `pickups[]: {rider_token, landmark, time "HH:MM", is_you}` | route strip with times (07:44/07:51/07:56). Without it UI shows order only |
| `deadline` | UI must not compute class_start − buffer |
| `vehicle: {kind: sedan\|big_car\|wav, label, wheelchair_accessible}` | WAV badge |
| `hard_filters_passed: string[]` | show "never relaxed" guarantees from the engine, not UI claims |
| `flags[]` | `CAP_EXCEEDED_REQUIRES_APPROVAL`, `LATE_ARRIVAL`, `NO_RAMP`, `ACCESSIBILITY_UNVERIFIED` |
Top level: `status` ∈ exact_match \| best_deal_proposed \| no_feasible_route \| no_accessible_route; for no-option add `reason{code,message}` and `assistance{message}`.
Exact match = same `options[]` shape with `relaxed: null`.

## Timetable
- parse/manual response: `classes[{id,course,weekday Sun–Thu,start,end?,room?}]`, `uncertain_fields[{class_id,field,reason}]`, `inference_source` gemini_vision\|manual\|fixture, `model?`.
- confirm response: `{confirmed, class_count, invalidated_plans}`.

## /api/trips/confirm
Request per §10 + **ADD** `decision?: accept(default)|decline|cancel_trip` and `replaces_trip_id?` (Class Shift atomic replace).
Response: `status` confirmed\|awaiting_consent\|declined\|canceled, `trip_id`, `plan`, `amount_paid_fils`, `wallet.balance_fils`, `pending_consents[{rider_token,label,state}]`, `idempotent_replay?`.
Open question: is decline/cancel better as a separate route? UI only needs one call each.

## Proposals (rescue / class shift / emergency) — one shape
`{proposal_id, kind, message, plan_revision, plan(PlanOption), previous_your_share_fils?, delta_fils (new − previous), refund_fils?, new_charge_fils?, next_class?, requires_approval, consents[], alternatives?[{label, your_share_fils, delta_fils, flags, selectable:false}]}`
Appears in `SimState.pending_proposals` AND in the shift/emergency responses.
Above-cap options (pair 2.49 / solo 4.26) go in `alternatives` with `selectable:false`; never in `plan`.

## /api/trips/shift-class
`{status: shift_proposed|no_next_class, proposal?, cancel_only?{refund_fils,terms}, message}`. UI sends `request_time` from the sim clock (editable).

## /api/trips/emergency
`{status: emergency_proposed|no_option|solo_handoff_eligible, proposal?, newcomer_fare_fils?, existing_riders_fares_unchanged?, reason?, message}`.

## /api/simulation/state
`{revision, sim_time, service_date, trips[{trip_id,status,class_start,plan,amount_paid_fils,has_next_class}], pending_proposals[], wallet{balance_fils, ledger[{at,kind debit|refund,amount_fils,note}]}}` (a +40-fils rescue revision is a **debit**, never a refund).
UI polls every 4 s while a trip or proposal exists.

## /api/simulation/event
Enum in §10 + **ADD** `peer_consent` (simulated explicit consent of synthetic riders). Returns SimState.

## Flip-to-live checklist (per endpoint, in `frontend/src/api.ts` → DEFAULT_LIVE, or `?live=plan,confirm`)
health ✔ (shell) · parse · manual · confirmTT · plan · confirm · state · event · shift · emergency.
Golden numbers the UI test expects (mock reproduces them): BD1 1860/08:17/U85.25, BD2 1565/08:08/U80.00, R2 1900 (+40), wallet 12000→10140→10100→10140, shift refund 1900 / new 1860, emergency 1575.


## AGREED corrections (round 2) — implemented in types.ts / mock.ts
1. `fare.shares[]: {rider_token, share_fils}` — rendered as "Fair split" on the pass and in Best Deal cards (collapsible). Server-computed; Σ = vehicle total.
2. `PlanOption.accessible_dropoff?: {label, source, verified}` — UI always prints the source and shows "NOT verified" when `verified:false`.
3. `desired_companions` may be 0. Zaid's separate demo (dev drawer → "Load Zaid demo"): sweileh → AAU, male_only, wheelchair, class 09:00, fare cap 3000, 0 companions → expects WAV-01, 2700 fils, arrive 08:45.
4. Ledger sign fixed (debit 40).
5. `EmergencyRequest` now carries the same hard constraints: campus_id, zone_id, service_date, class_start, arrival_buffer_min, request_time, gender_pool, fare_cap_fils, accessibility{wheelchair,big_car}, sharing_opt_in.
6. Sessions: each browser auto-creates its own `s-xxxxxxxx` session (localStorage). Stage demo = shared session via `?session=demo_01` or dev drawer → "Use shared stage session". Rider token still defaults to R-7K2 (dev drawer changes it); tell me if independent users should get server-assigned tokens.

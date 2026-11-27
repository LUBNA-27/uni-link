/**
 * UniLink API contract types (Rev. E master §10).
 *
 * Fields marked "PROPOSED" are NOT in the frozen §10 text; the frontend needs them
 * and they must be agreed with Ranad before `backend/schemas.py` is frozen.
 * See CONTRACT_FOR_RANAD.md.
 *
 * Money is ALWAYS integer fils. Times are service-date-local "HH:MM".
 * The frontend never computes prices, matches or rankings — it only renders these.
 */

export type Fils = number
export type HHMM = string
export type Weekday = 'Sun' | 'Mon' | 'Tue' | 'Wed' | 'Thu'
export type GenderPool = 'female_only' | 'male_only'
export type PickupMode = 'door_to_door' | 'main_road_shuttle'
export type Booking = 'day_ahead' | 'on_demand'

export interface ApiErrorBody {
  code: string
  message: string
  /** PROPOSED: present on 409 STALE_REVISION so the UI can refetch. */
  current_revision?: number
}

/* ───────────── health ───────────── */
export interface HealthResponse {
  status: 'ok'
  fixture_version: string
  gemini_ready: boolean
  source: 'simulation'
}

/* ───────────── timetable ───────────── */
export interface ClassItem {
  id: string
  course: string
  weekday: Weekday
  start: HHMM
  end?: HHMM
  room?: string
}
export type EditableField = 'course' | 'weekday' | 'start' | 'end' | 'room'
export interface UncertainField {
  class_id: string
  field: EditableField
  reason: string
}
export interface TimetableResponse {
  session_id: string
  classes: ClassItem[]
  uncertain_fields: UncertainField[]
  /** 'gemini_vision' only when the model was really called. */
  inference_source: 'gemini_vision' | 'manual' | 'fixture'
  /** only if a model was called */
  model?: string
  source: 'simulation' | 'inference'
}
export interface TimetableConfirmResponse {
  session_id: string
  confirmed: boolean
  class_count: number
  /** true when the confirmed schedule changed and downstream plans were invalidated */
  invalidated_plans: boolean
}

/* ───────────── plan ───────────── */
export interface PlanRequest {
  session_id: string
  rider_token: string
  campus_id: string
  zone_id: string
  service_date: string
  class_start: HHMM
  arrival_buffer_min: number
  pickup_mode: PickupMode
  gender_pool: GenderPool
  /** 0 = ride alone (allowed) */
  desired_companions: number
  booking: Booking
  preferred_pickup: HHMM
  fare_cap_fils: Fils
  accessibility: { wheelchair: boolean; big_car: boolean }
  sharing_opt_in: boolean
}

/** AGREED: accessible drop-off, always source-labeled; never shown as fact without its source. */
export interface AccessibleDropoff {
  label: string
  source: string
  verified: boolean
}

/** PROPOSED: per-stop times with a SYNTHETIC landmark label (never a real home pin). */
export interface Pickup {
  rider_token: string
  landmark: string
  time: HHMM
  is_you: boolean
}
export interface FareShare {
  rider_token: string
  share_fils: Fils
}
export interface Fare {
  your_share_fils: Fils
  /** AGREED: leg-weighted split per rider, to demonstrate the fair-split formula (Σ = vehicle_total) */
  shares?: FareShare[]
  vehicle_total_fils: Fils
  /** hypothetical comparator only — not an available quote */
  hypothetical_reference_fils?: Fils
  delta_vs_reference_fils?: number
}
export type PlanFlag =
  | 'CAP_EXCEEDED_REQUIRES_APPROVAL'
  | 'LATE_ARRIVAL'
  | 'NO_RAMP'
  | 'ACCESSIBILITY_UNVERIFIED'
  | string
export interface PlanOption {
  plan_id: string
  /** which ONE soft constraint was relaxed; null for an exact match */
  relaxed: string | null
  utility?: number
  leave_home: HHMM
  arrival: HHMM
  /** PROPOSED: backend-computed deadline (class_start − buffer) so UI never derives it */
  deadline?: HHMM
  pickup_order: string[]
  pickups?: Pickup[]
  fare: Fare
  /** PROPOSED */
  vehicle?: { kind: 'sedan' | 'big_car' | 'wav'; label: string; wheelchair_accessible: boolean }
  /** AGREED: source-labeled accessible drop-off (wheelchair plans) */
  accessible_dropoff?: AccessibleDropoff
  /** PROPOSED: hard filters this option passed, e.g. ["Female-only pool","Capacity ≤ 4"] */
  hard_filters_passed?: string[]
  flags?: PlanFlag[]
}
export type PlanStatus =
  | 'exact_match'
  | 'best_deal_proposed'
  | 'no_feasible_route'
  | 'no_accessible_route'
export interface PlanResponse {
  session_id: string
  plan_revision: number
  status: PlanStatus
  exact_match_found: boolean
  options: PlanOption[]
  /** PROPOSED: for no-option states */
  reason?: { code: string; message: string }
  /** PROPOSED: honest operator-assistance text for no_accessible_route */
  assistance?: { message: string }
  requires_approval: boolean
  source: 'simulation'
}

/* ───────────── confirm / consent ───────────── */
export interface ConfirmRequest {
  session_id: string
  rider_token: string
  plan_id: string
  plan_revision: number
  accepted_fare_fils: Fils
  idempotency_key: string
  /** PROPOSED: accept (default) / decline (keep old booking) / cancel_trip (cancel-only after Class Shift) */
  decision?: 'accept' | 'decline' | 'cancel_trip'
  /** PROPOSED: for Class Shift — the booking this replaces atomically */
  replaces_trip_id?: string
}
export type ConsentState = 'pending' | 'accepted' | 'declined'
export interface ConsentEntry {
  rider_token: string
  /** safe label such as "You", "Companion B", "Replacement rider" */
  label: string
  state: ConsentState
}
export interface ConfirmResponse {
  session_id: string
  revision: number
  status: 'confirmed' | 'awaiting_consent' | 'declined' | 'canceled'
  trip_id?: string
  plan?: PlanOption
  amount_paid_fils?: Fils
  wallet?: { balance_fils: Fils }
  pending_consents?: ConsentEntry[]
  /** true if this idempotency_key was already applied */
  idempotent_replay?: boolean
  source: 'simulation'
}

/* ───────────── proposals (rescue / shift / emergency) ───────────── */
export interface ProposalAlternative {
  label: string
  your_share_fils: Fils
  delta_fils: number
  flags?: PlanFlag[]
  /** false = informational only (e.g. above fare cap) */
  selectable: boolean
}
export interface Proposal {
  proposal_id: string
  kind: 'smart_rescue' | 'class_shift' | 'emergency'
  /** human-readable trigger, e.g. "A companion canceled at 06:55" */
  message: string
  plan_revision: number
  plan: PlanOption
  previous_your_share_fils?: Fils
  /** your new share − your previous share (positive needs explicit approval) */
  delta_fils: number
  /** class_shift only */
  refund_fils?: Fils
  new_charge_fils?: Fils
  next_class?: ClassItem
  requires_approval: boolean
  consents: ConsentEntry[]
  alternatives?: ProposalAlternative[]
}

export interface LedgerEntry {
  at: HHMM
  kind: 'debit' | 'refund'
  amount_fils: Fils
  note: string
}
export interface TripView {
  trip_id: string
  status: 'confirmed' | 'awaiting_consent' | 'dispatched' | 'canceled' | 'completed'
  class_start: HHMM
  plan: PlanOption
  amount_paid_fils: Fils
  has_next_class: boolean
}
export interface SimState {
  session_id: string
  revision: number
  sim_time: HHMM
  service_date: string
  trips: TripView[]
  pending_proposals: Proposal[]
  wallet: { balance_fils: Fils; ledger: LedgerEntry[] }
  source: 'simulation'
}

/* ───────────── class shift ───────────── */
export interface ShiftRequest {
  session_id: string
  trip_id: string
  rider_token: string
  request_time: HHMM
}
export interface ShiftResponse {
  session_id: string
  revision: number
  status: 'shift_proposed' | 'no_next_class'
  trip_id: string
  proposal?: Proposal
  /** PROPOSED: cancel-only terms when there is no next class */
  cancel_only?: { refund_fils: Fils; terms: string }
  message: string
  source: 'simulation'
}

/* ───────────── emergency ───────────── */
/** AGREED: same hard constraints as normal planning (expanded request). */
export interface EmergencyRequest {
  session_id: string
  rider_token: string
  campus_id: string
  zone_id: string
  service_date: string
  class_start: HHMM
  arrival_buffer_min: number
  request_time: HHMM
  gender_pool: GenderPool
  fare_cap_fils: Fils
  accessibility: { wheelchair: boolean; big_car: boolean }
  sharing_opt_in: boolean
}
export interface EmergencyResponse {
  session_id: string
  revision: number
  status: 'emergency_proposed' | 'no_option' | 'solo_handoff_eligible'
  proposal?: Proposal
  newcomer_fare_fils?: Fils
  existing_riders_fares_unchanged?: boolean
  reason?: { code: string; message: string }
  message: string
  source: 'simulation'
}

/* ───────────── simulation events ───────────── */
export type SimEventName =
  | 'cancel'
  | 'traffic'
  | 'shuttle_full'
  | 'vehicle_unavailable'
  | 'reset'
  /** PROPOSED: simulate other riders' explicit consent (they are synthetic) */
  | 'peer_consent'
export interface SimEventRequest {
  session_id: string
  event: SimEventName
  target?: string
  sim_time?: HHMM
}

/* ───────────── insights (PROPOSED) ───────────── */
/** Aggregate statistics computed by the backend from fixtures. No personal rows, no mock values on the client. */
export interface InsightMetric {
  /** stable id, e.g. "plans_evaluated", "plan_latency_p50_ms", "fare_conservation_ok" */
  id: string
  /** human label, localized by the server using Accept-Language */
  label: string
  value: number | string | boolean
  /** "ms" | "count" | "fils" | "%" ... — "fils" is rendered as JOD + exact fils */
  unit?: string
  /** sample size behind the number */
  n?: number
  note?: string
}
export interface InsightsResponse {
  session_id: string
  generated_at: string
  /** what the numbers are computed from, e.g. "60 synthetic riders, fixtures v1" */
  basis: string
  metrics: InsightMetric[]
  source: 'simulation'
}

/* ───────────── fleet insights (as served by GET /api/insights) ───────────── */
/** Aggregates the backend computes from the synthetic fixtures. Rendered as-is; never mocked. */
export interface FleetInsights {
  requests_by_hour: Record<string, number>
  requests_by_zone: Record<string, number>
  accessible_requests: number
  opted_in_riders: number
  shuttle_seats: Record<string, number>
  wav_available: number
  wav_total: number
  /** B2B semester-pass subsidy example (fils), computed separately from passenger fares */
  b2b_semester_pass_example: Record<string, number>
  prediction?: Record<string, string | boolean> | null
  source: 'simulation'
}

/* ───────────── voice intent (POST /api/voice/intent) ───────────── */
export type VoiceIntent =
  | 'plan_trip' | 'read_route' | 'accept_best_deal' | 'approve_rescue' | 'decline'
  | 'shift_to_next_class' | 'emergency_ride' | 'repeat' | 'unknown'
export interface VoiceIntentResponse {
  intent: VoiceIntent
  confidence: number
  slots: Record<string, string>
  readback_ar: string
  readback_en: string
  requires_confirmation: boolean
  /** the server never acts on voice alone */
  action_taken: 'none'
  plan_id?: string | null
  plan_revision: number
  fare_fils?: Fils | null
  source: 'simulation'
}

/* ───────────── Ride & Box (POST /api/parcels/quote) ───────────── */
export interface ParcelQuoteRequest {
  session_id: string
  trip_id: string
  declared_value_fils: Fils
  size: 'small' | 'medium'
  weight_g: number
}
export interface ParcelQuoteResponse {
  trip_id: string
  corridor_km: string
  parcel_fee_fils: Fils
  insurance_fils: Fils
  total_fils: Fils
  driver_share_fils: Fils
  jeeny_share_fils: Fils
  /** always false: a quote never creates a shipment */
  shipment_created: false
  source: 'simulation'
}

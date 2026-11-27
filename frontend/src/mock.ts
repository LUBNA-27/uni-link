/**
 * ⚠️ TEMPORARY MOCKS — NOT BACKEND LOGIC ⚠️
 * Canned payloads copied from the Rev. E golden path (§06 / §10) so the UI can be built
 * before Ranad's endpoints exist. Nothing here matches, prices or ranks anything:
 * it replays fixed numbers. Delete a mock by flipping its flag in api.ts → LIVE.
 * The UI shows a visible "MOCK" chip for every call served from here.
 */
import { ApiError } from './api-error'
import type {
  ClassItem, ConfirmRequest, ConfirmResponse, ConsentEntry, EmergencyRequest, EmergencyResponse,
  HealthResponse, LedgerEntry, PlanOption, PlanRequest, PlanResponse, Proposal, ShiftRequest,
  ShiftResponse, SimEventRequest, SimState, TimetableConfirmResponse, TimetableResponse, TripView,
} from './types'

const wait = (ms = 350) => new Promise((r) => setTimeout(r, ms))

export type MockScenario = 'sara' | 'wav_ok' | 'wav_out'
let scenario: MockScenario = 'sara'
export const setMockScenario = (s: MockScenario) => { scenario = s; reset() }
export const getMockScenario = () => scenario

const HF = ['Same-gender pool', 'Capacity ≤ 4', 'Meets class deadline']

const BD1: PlanOption = {
  plan_id: 'BD1', relaxed: 'companions 3→2', utility: 85.25, leave_home: '07:44', arrival: '08:17', deadline: '08:20',
  pickup_order: ['R-7K2', 'R-3QM', 'R-9TD'],
  pickups: [
    { rider_token: 'R-7K2', landmark: 'Your door · Irbid East (synthetic)', time: '07:44', is_you: true },
    { rider_token: 'R-3QM', landmark: 'Companion B · Irbid East (synthetic)', time: '07:51', is_you: false },
    { rider_token: 'R-9TD', landmark: 'Companion C · Irbid East (synthetic)', time: '07:56', is_you: false },
  ],
  fare: { your_share_fils: 1860, vehicle_total_fils: 4500, hypothetical_reference_fils: 1565, delta_vs_reference_fils: 295,
    shares: [{ rider_token: 'R-7K2', share_fils: 1860 }, { rider_token: 'R-3QM', share_fils: 1380 }, { rider_token: 'R-9TD', share_fils: 1260 }] },
  vehicle: { kind: 'sedan', label: 'Standard car · 4 seats', wheelchair_accessible: false },
  hard_filters_passed: HF,
}
const BD2: PlanOption = {
  plan_id: 'BD2', relaxed: 'departure −10 min', utility: 80.0, leave_home: '07:34', arrival: '08:08', deadline: '08:20',
  pickup_order: ['R-7K2', 'R-3QM', 'R-9TD', 'R-5LP'],
  fare: { your_share_fils: 1565, vehicle_total_fils: 4500, delta_vs_reference_fils: 0,
    shares: [{ rider_token: 'R-7K2', share_fils: 1565 }, { rider_token: 'R-3QM', share_fils: 1085 }, { rider_token: 'R-9TD', share_fils: 965 }, { rider_token: 'R-5LP', share_fils: 885 }] },
  vehicle: { kind: 'sedan', label: 'Standard car · 4 seats', wheelchair_accessible: false },
  hard_filters_passed: HF,
}
const R2: PlanOption = {
  plan_id: 'R2', relaxed: null, leave_home: '07:44', arrival: '08:15', deadline: '08:20',
  pickup_order: ['R-7K2', 'R-3QM', 'R-5LP'],
  pickups: [
    { rider_token: 'R-7K2', landmark: 'Your door · Irbid East (synthetic)', time: '07:44', is_you: true },
    { rider_token: 'R-3QM', landmark: 'Companion B · Irbid East (synthetic)', time: '07:51', is_you: false },
    { rider_token: 'R-5LP', landmark: 'Replacement rider D · Irbid East (synthetic)', time: '07:56', is_you: false },
  ],
  fare: { your_share_fils: 1900, vehicle_total_fils: 4500,
    shares: [{ rider_token: 'R-7K2', share_fils: 1900 }, { rider_token: 'R-3QM', share_fils: 1420 }, { rider_token: 'R-5LP', share_fils: 1180 }] },
  vehicle: BD1.vehicle, hard_filters_passed: HF,
}
const SH1: PlanOption = {
  plan_id: 'SH1', relaxed: null, leave_home: '10:47', arrival: '11:15', deadline: '11:20',
  pickup_order: ['R-7K2', 'R-4HN', 'R-8PX'],
  pickups: [
    { rider_token: 'R-7K2', landmark: 'Your door · Irbid East (synthetic)', time: '10:47', is_you: true },
    { rider_token: 'R-4HN', landmark: 'Companion · Irbid East (synthetic)', time: '10:53', is_you: false },
    { rider_token: 'R-8PX', landmark: 'Companion · Irbid East (synthetic)', time: '10:58', is_you: false },
  ],
  fare: { your_share_fils: 1860, vehicle_total_fils: 4500 },
  vehicle: BD1.vehicle, hard_filters_passed: HF,
}
const EMG1: PlanOption = {
  plan_id: 'EMG1', relaxed: null, leave_home: '08:01', arrival: '08:18', deadline: '08:20',
  pickup_order: ['R-7K2'],
  pickups: [{ rider_token: 'R-7K2', landmark: 'Nearest road to your door (synthetic)', time: '08:01', is_you: true }],
  fare: { your_share_fils: 1575, vehicle_total_fils: 0 },
  vehicle: { kind: 'sedan', label: 'En-route trip TRP-0002', wheelchair_accessible: false },
  hard_filters_passed: ['Female-only trip', 'Free seat available', 'Everyone still meets their deadline'],
}
const WAV: PlanOption = {
  plan_id: 'WAV1', relaxed: null, leave_home: '08:25', arrival: '08:45', deadline: '08:50',
  pickup_order: ['R-W01'],
  pickups: [{ rider_token: 'R-W01', landmark: 'Ramp-accessible pickup · Sweileh (synthetic)', time: '08:25', is_you: true }],
  fare: { your_share_fils: 2700, vehicle_total_fils: 2700, shares: [{ rider_token: 'R-W01', share_fils: 2700 }] },
  vehicle: { kind: 'wav', label: 'WAV-01 · ramp vehicle', wheelchair_accessible: true },
  accessible_dropoff: { label: 'Ramp-equipped campus entrance (demo)', source: 'MOCK · simulation fixture, not a verified campus fact', verified: false },
  hard_filters_passed: ['Wheelchair-accessible vehicle', 'Meets class deadline'],
}

/* ───────── mutable mock "server" state (canned sequence only) ───────── */
interface M {
  revision: number; sim_time: string; balance: number; ledger: LedgerEntry[]
  trip?: TripView; proposal?: Proposal; saraAccepted: boolean; peersAccepted: boolean; keys: Map<string, ConfirmResponse>
}
const fresh = (): M => ({ revision: 1, sim_time: '06:30', balance: 12000, ledger: [], saraAccepted: false, peersAccepted: false, keys: new Map() })
let m: M = fresh()
function reset() { m = fresh() }

const consents = (): ConsentEntry[] => [
  { rider_token: 'R-7K2', label: 'You', state: m.saraAccepted ? 'accepted' : 'pending' },
  { rider_token: 'R-3QM', label: 'Companion B (simulated)', state: m.peersAccepted ? 'accepted' : 'pending' },
  { rider_token: 'R-5LP', label: 'Replacement rider D (simulated)', state: m.peersAccepted ? 'accepted' : 'pending' },
]
const rescue = (): Proposal => ({
  proposal_id: 'R2', kind: 'smart_rescue',
  message: 'Companion C canceled at 06:55. We found a replacement rider who can now ride at your time.',
  plan_revision: m.revision, plan: R2, previous_your_share_fils: 1860, delta_fils: 40, requires_approval: true,
  consents: consents(),
  alternatives: [
    { label: 'Continue as a pair', your_share_fils: 2490, delta_fils: 630, flags: ['CAP_EXCEEDED_REQUIRES_APPROVAL'], selectable: false },
    { label: 'Ride alone', your_share_fils: 4260, delta_fils: 2400, flags: ['CAP_EXCEEDED_REQUIRES_APPROVAL'], selectable: false },
  ],
})
const shiftProposal = (): Proposal => ({
  proposal_id: 'SH1', kind: 'class_shift',
  message: 'Your 08:30 class is canceled. Your next class is 11:30 — here is a new group for it.',
  plan_revision: m.revision, plan: SH1, previous_your_share_fils: 1900, delta_fils: -40,
  refund_fils: 1900, new_charge_fils: 1860,
  next_class: { id: 'c2', course: 'Class 2', weekday: 'Sun', start: '11:30' },
  requires_approval: true,
  consents: [{ rider_token: 'R-7K2', label: 'You', state: 'pending' }],
})

const state = (): SimState => ({
  session_id: 'mock', revision: m.revision, sim_time: m.sim_time, service_date: '2026-11-29',
  trips: m.trip ? [m.trip] : [],
  pending_proposals: m.proposal ? [{ ...m.proposal, consents: m.proposal.kind === 'smart_rescue' ? consents() : m.proposal.consents }] : [],
  wallet: { balance_fils: m.balance, ledger: m.ledger }, source: 'simulation',
})
const bump = () => { m.revision += 1 }

/* ───────── endpoints ───────── */
export async function health(): Promise<HealthResponse> {
  await wait(150)
  return { status: 'ok', fixture_version: 'MOCK', gemini_ready: false, source: 'simulation' }
}

const DEMO_CLASSES: ClassItem[] = [
  { id: 'c1', course: 'CS 201 · Data Structures', weekday: 'Sun', start: '08:30', end: '09:30', room: 'Eng. 102' },
  { id: 'c2', course: 'AI 305 · Machine Learning', weekday: 'Sun', start: '11:30', end: '12:30', room: 'IT 214' },
  { id: 'c3', course: 'CS 250 · Databases', weekday: 'Tue', start: '10:00', end: '11:00', room: 'Eng. 110' },
]
export async function parseTimetable(_file: File, session_id: string): Promise<TimetableResponse> {
  await wait(900)
  return {
    session_id, classes: DEMO_CLASSES, inference_source: 'fixture', source: 'simulation',
    uncertain_fields: [{ class_id: 'c2', field: 'start', reason: 'Low contrast in the photo — please check the time.' }],
  }
}
export async function manualTimetable(session_id: string, classes: ClassItem[]): Promise<TimetableResponse> {
  await wait(300)
  return { session_id, classes, uncertain_fields: [], inference_source: 'manual', source: 'simulation' }
}
export async function confirmTimetable(_s: string, classes: ClassItem[]): Promise<TimetableConfirmResponse> {
  await wait(300)
  return { session_id: 'mock', confirmed: true, class_count: classes.length, invalidated_plans: false }
}

export async function plan(req: PlanRequest): Promise<PlanResponse> {
  await wait(700)
  const base = { session_id: req.session_id, plan_revision: m.revision, requires_approval: true, source: 'simulation' as const }
  if (scenario === 'wav_ok')
    return { ...base, status: 'exact_match', exact_match_found: true, options: [WAV], requires_approval: false }
  if (scenario === 'wav_out')
    return {
      ...base, status: 'no_accessible_route', exact_match_found: false, options: [],
      reason: { code: 'NO_ACCESSIBLE_VEHICLE', message: 'No wheelchair-accessible vehicle is available for your class time.' },
      assistance: { message: 'We never offer a car without a ramp. A UniLink operator can arrange assistance — this is a simulated hand-off, nothing is dispatched.' },
    }
  return { ...base, status: 'best_deal_proposed', exact_match_found: false, options: [BD1, BD2] }
}

export async function confirm(req: ConfirmRequest): Promise<ConfirmResponse> {
  await wait(500)
  const prior = m.keys.get(req.idempotency_key)
  if (prior) return { ...prior, idempotent_replay: true }
  if (req.plan_revision !== m.revision && req.plan_id !== 'R2' && req.plan_id !== 'SH1')
    throw new ApiError('STALE_REVISION', 'The plan changed while you were deciding.', 409, m.revision)
  const ok = (r: Omit<ConfirmResponse, 'session_id' | 'revision' | 'source'>): ConfirmResponse => {
    bump()
    const out: ConfirmResponse = { session_id: req.session_id, revision: m.revision, source: 'simulation', ...r }
    m.keys.set(req.idempotency_key, out)
    return out
  }
  if (req.decision === 'decline') { m.proposal = undefined; return ok({ status: 'declined' }) }
  if (req.decision === 'cancel_trip') {
    m.balance += 1900; m.ledger.push({ at: m.sim_time, kind: 'refund', amount_fils: 1900, note: 'Trip canceled — refund' })
    m.trip = undefined; m.proposal = undefined
    return ok({ status: 'canceled', wallet: { balance_fils: m.balance } })
  }
  if (req.plan_id === 'R2') {
    m.saraAccepted = true
    if (!m.peersAccepted) return ok({ status: 'awaiting_consent', pending_consents: consents() })
    return commitRescue(ok)
  }
  if (req.plan_id === 'SH1') {
    m.balance += 1900 - 1860
    m.ledger.push({ at: m.sim_time, kind: 'refund', amount_fils: 1900, note: 'Old 08:30 booking released' },
      { at: m.sim_time, kind: 'debit', amount_fils: 1860, note: 'New 11:30 booking' })
    m.trip = { trip_id: 'T-1001', status: 'confirmed', class_start: '11:30', plan: SH1, amount_paid_fils: 1860, has_next_class: false }
    m.proposal = undefined
    return ok({ status: 'confirmed', trip_id: 'T-1001', plan: SH1, amount_paid_fils: 1860, wallet: { balance_fils: m.balance } })
  }
  const p = req.plan_id === 'BD2' ? BD2 : req.plan_id === 'EMG1' ? EMG1 : req.plan_id === 'WAV1' ? WAV : BD1
  m.balance -= req.accepted_fare_fils
  m.ledger.push({ at: m.sim_time, kind: 'debit', amount_fils: req.accepted_fare_fils, note: `Booking ${p.plan_id}` })
  m.trip = { trip_id: 'T-1001', status: 'confirmed', class_start: p.plan_id === 'EMG1' ? '08:30' : '08:30', plan: p, amount_paid_fils: req.accepted_fare_fils, has_next_class: true }
  return ok({ status: 'confirmed', trip_id: 'T-1001', plan: p, amount_paid_fils: req.accepted_fare_fils, wallet: { balance_fils: m.balance } })
}
function commitRescue(ok: (r: Omit<ConfirmResponse, 'session_id' | 'revision' | 'source'>) => ConfirmResponse) {
  m.balance += 1860 - 1900
  m.ledger.push({ at: m.sim_time, kind: 'debit', amount_fils: 40, note: 'Rescue revision — extra share' })
  m.trip = { trip_id: 'T-1001', status: 'confirmed', class_start: '08:30', plan: R2, amount_paid_fils: 1900, has_next_class: true }
  m.proposal = undefined; m.saraAccepted = false; m.peersAccepted = false
  return ok({ status: 'confirmed', trip_id: 'T-1001', plan: R2, amount_paid_fils: 1900, wallet: { balance_fils: m.balance } })
}

export async function shiftClass(req: ShiftRequest): Promise<ShiftResponse> {
  await wait(500)
  m.sim_time = req.request_time
  m.proposal = shiftProposal()
  return {
    session_id: req.session_id, revision: m.revision, status: 'shift_proposed', trip_id: req.trip_id,
    proposal: m.proposal, message: 'Next class found from your saved timetable. Nothing changes until you approve.', source: 'simulation',
  }
}

export async function emergency(req: EmergencyRequest): Promise<EmergencyResponse> {
  await wait(600)
  m.sim_time = req.request_time
  const proposal: Proposal = {
    proposal_id: 'EMG1', kind: 'emergency', plan_revision: m.revision, plan: EMG1, delta_fils: 0, requires_approval: true,
    message: 'A female-only trip already on the road can pick you up on its way.', consents: [{ rider_token: 'R-7K2', label: 'You', state: 'pending' }],
  }
  return {
    session_id: req.session_id, revision: m.revision, status: 'emergency_proposed', proposal,
    newcomer_fare_fils: 1575, existing_riders_fares_unchanged: true,
    message: 'Emergency price applies to you only. Riders already on the trip pay the same.', source: 'simulation',
  }
}

export async function simState(): Promise<SimState> { await wait(120); return state() }

export async function simEvent(req: SimEventRequest): Promise<SimState> {
  await wait(300)
  if (req.event === 'reset') { reset(); return state() }
  if (req.event === 'cancel' && req.target === 'R-9TD') {
    m.sim_time = req.sim_time ?? '06:55'; bump()
    if (m.trip) m.proposal = rescue()
    return state()
  }
  if (req.event === 'peer_consent') {
    m.peersAccepted = true
    if (m.saraAccepted && m.proposal?.kind === 'smart_rescue') {
      // commit exactly as the backend would after the last consent
      m.balance += 1860 - 1900
      m.ledger.push({ at: m.sim_time, kind: 'debit', amount_fils: 40, note: 'Rescue revision — extra share' })
      m.trip = { trip_id: 'T-1001', status: 'confirmed', class_start: '08:30', plan: R2, amount_paid_fils: 1900, has_next_class: true }
      m.proposal = undefined; m.saraAccepted = false; m.peersAccepted = false; bump()
    }
    return state()
  }
  throw new ApiError('MOCK_UNSUPPORTED', `The mock has no canned result for "${req.event}". Flip LIVE.event once Ranad's engine is up.`, 501)
}

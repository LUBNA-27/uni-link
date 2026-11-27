/**
 * Typed API client. One flag per endpoint: false = serve the labeled MOCK in mock.ts,
 * true = call the real FastAPI route (same origin). Flip flags as Ranad's endpoints land.
 * Release defaults to live. Explicit offline QA fallback: ?live=mock (never a live demo).
 * The frontend NEVER computes matching, pricing, ranking or wallet math.
 */
import { ApiError } from './api-error'
import { getLang } from './i18n'
import * as mock from './mock'
import type {
  ClassItem, ConfirmRequest, ConfirmResponse, EmergencyRequest, EmergencyResponse, HealthResponse,
  PlanRequest, PlanResponse, ShiftRequest, ShiftResponse, SimEventRequest, SimState,
  TimetableConfirmResponse, TimetableResponse, FleetInsights,
  ParcelQuoteRequest, ParcelQuoteResponse, VoiceIntentResponse,
} from './types'

export { ApiError }

export type Endpoint =
  | 'health' | 'parse' | 'manual' | 'confirmTT' | 'plan' | 'confirm' | 'shift' | 'emergency' | 'state' | 'event' | 'insights'
  | 'voice' | 'parcel'

/** Release: all implemented endpoints use the live backend by default. */
const DEFAULT_LIVE: Record<Endpoint, boolean> = {
  health: true,
  parse: true,
  manual: true,
  confirmTT: true,
  plan: true,
  confirm: true,
  shift: true,
  emergency: true,
  state: true,
  event: true,
  insights: true,
  voice: true,
  parcel: true,
}

function resolveLive(): Record<Endpoint, boolean> {
  const live = { ...DEFAULT_LIVE }
  try {
    const q = new URLSearchParams(window.location.search).get('live')
    if (q === 'all') (Object.keys(live) as Endpoint[]).forEach((k) => (live[k] = true))
    else if (q === 'mock') (Object.keys(live) as Endpoint[]).forEach((k) => (live[k] = false))
    else if (q) q.split(',').forEach((k) => { if (k in live) live[k as Endpoint] = true })
  } catch { /* ignore */ }
  return live
}
export const LIVE = resolveLive()
export const isMock = (e: Endpoint) => !LIVE[e]
// `insights`, `voice` and `parcel` never have a mock (no invented numbers), so they do not count as MOCK data.
const NO_MOCK: Endpoint[] = ['health', 'insights', 'voice', 'parcel']
export const anyMock = () => (Object.keys(LIVE) as Endpoint[]).some((k) => !NO_MOCK.includes(k) && !LIVE[k])

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  let res: Response
  try {
    res = await fetch(path, {
      method,
      headers: { 'Accept-Language': getLang(), ...(body && !(body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}) },
      body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError('NETWORK', 'Cannot reach the server. Check your connection and try again.')
  }
  let data: unknown = null
  try { data = await res.json() } catch { /* non-JSON */ }
  if (!res.ok) {
    // accept {code,message} directly or FastAPI-style {detail:{code,message}}
    const d = (data as { detail?: unknown } | null)?.detail ?? data
    const e = (d && typeof d === 'object' ? d : {}) as { code?: string; message?: string; current_revision?: number }
    throw new ApiError(e.code ?? `HTTP_${res.status}`, e.message ?? `Request failed (${res.status})`, res.status, e.current_revision)
  }
  return data as T
}

export const api = {
  health: (): Promise<HealthResponse> => (LIVE.health ? call('GET', '/api/health') : mock.health()),

  parseTimetable: (file: File, session_id: string): Promise<TimetableResponse> => {
    if (!LIVE.parse) return mock.parseTimetable(file, session_id)
    const f = new FormData()
    f.append('session_id', session_id)
    f.append('image', file)
    return call('POST', '/api/timetable/parse', f)
  },
  manualTimetable: (session_id: string, classes: ClassItem[]): Promise<TimetableResponse> =>
    LIVE.manual ? call('POST', '/api/timetable/manual', { session_id, classes }) : mock.manualTimetable(session_id, classes),
  confirmTimetable: (session_id: string, classes: ClassItem[]): Promise<TimetableConfirmResponse> =>
    LIVE.confirmTT ? call('POST', '/api/timetable/confirm', { session_id, classes }) : mock.confirmTimetable(session_id, classes),

  plan: (req: PlanRequest): Promise<PlanResponse> => (LIVE.plan ? call('POST', '/api/plan', req) : mock.plan(req)),
  confirm: (req: ConfirmRequest): Promise<ConfirmResponse> =>
    LIVE.confirm ? call('POST', '/api/trips/confirm', req) : mock.confirm(req),
  shiftClass: (req: ShiftRequest): Promise<ShiftResponse> =>
    LIVE.shift ? call('POST', '/api/trips/shift-class', req) : mock.shiftClass(req),
  emergency: (req: EmergencyRequest): Promise<EmergencyResponse> =>
    LIVE.emergency ? call('POST', '/api/trips/emergency', req) : mock.emergency(req),

  simState: (session_id: string): Promise<SimState> =>
    LIVE.state ? call('GET', `/api/simulation/state?session_id=${encodeURIComponent(session_id)}`) : mock.simState(),
  /** Real computed statistics only. Returns null while the endpoint is not live — NEVER a mock number. */
  insights: (session_id: string): Promise<FleetInsights | null> =>
    LIVE.insights ? call('GET', `/api/insights?session_id=${encodeURIComponent(session_id)}`) : Promise.resolve(null),
  /** Whitelist voice intent. Read-back only: the server never moves money or books on voice alone. */
  voiceIntent: (session_id: string, transcript: string, locale: 'ar-JO' | 'en'): Promise<VoiceIntentResponse | null> =>
    LIVE.voice ? call('POST', '/api/voice/intent', { session_id, transcript, locale }) : Promise.resolve(null),
  /** Ride & Box quote on a booked trip. A quote never creates a shipment. */
  parcelQuote: (req: ParcelQuoteRequest): Promise<ParcelQuoteResponse | null> =>
    LIVE.parcel ? call('POST', '/api/parcels/quote', req) : Promise.resolve(null),
  simEvent: (req: SimEventRequest): Promise<SimState> =>
    LIVE.event ? call('POST', '/api/simulation/event', req) : mock.simEvent(req),
}

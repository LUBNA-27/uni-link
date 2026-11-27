import { useEffect, useState } from 'react'
import { api, LIVE, type Endpoint } from '../api'
import { getMockScenario, setMockScenario, type MockScenario } from '../mock'
import { SHARED_SESSION, useStore } from '../store'
import type { HealthResponse, SimEventRequest } from '../types'
import { Button, ErrorBox, inputCls, Sheet } from './ui'

const EVENTS: { label: string; req: Omit<SimEventRequest, 'session_id'> }[] = [
  { label: 'Companion C cancels @ 06:55', req: { event: 'cancel', target: 'R-9TD', sim_time: '06:55' } },
  { label: 'Other riders consent (simulated)', req: { event: 'peer_consent' } },
  { label: 'Traffic ×1.6', req: { event: 'traffic', target: 'all' } },
  { label: 'Shuttle S1 full @ 07:47', req: { event: 'shuttle_full', target: 'S1', sim_time: '07:47' } },
  { label: 'WAV-01 unavailable', req: { event: 'vehicle_unavailable', target: 'WAV-01' } },
  { label: 'Reset simulation', req: { event: 'reset' } },
]

/** Presenter / QA panel. Hidden by default (footer link or ?dev=1). Not part of the student flow. */
export function DevDrawer() {
  const { devOpen, setDevOpen, sessionId, riderToken, setIdentity, setSim, resetAll, setTimetable, setRequest, setPlan, go } = useStore()
  const [sid, setSid] = useState(sessionId)
  const [tok, setTok] = useState(riderToken)
  const [health, setHealth] = useState<HealthResponse | string>()
  const [scenario, setScenario] = useState<MockScenario>(getMockScenario())
  const [err, setErr] = useState<unknown>()
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!devOpen) return
    api.health().then(setHealth).catch((e: Error) => setHealth(e.message))
  }, [devOpen])

  /** Zaid's separate accessibility demo: Sweileh → AAU, male-only, wheelchair, 09:00 class, cap above 2.700. */
  const loadZaid = () => {
    resetAll()
    setIdentity(sessionId, 'R-W01'); setTok('R-W01')
    setMockScenario('wav_ok'); setScenario('wav_ok')
    setTimetable([{ id: 'z1', course: 'AAU class (demo)', weekday: 'Sun', start: '09:00' }], [], true)
    setRequest({
      session_id: sessionId, rider_token: 'R-W01', campus_id: 'AAU', zone_id: 'sweileh', service_date: '2026-11-29',
      class_start: '09:00', arrival_buffer_min: 10, pickup_mode: 'door_to_door', gender_pool: 'male_only',
      desired_companions: 0, booking: 'day_ahead', preferred_pickup: '08:25', fare_cap_fils: 3000,
      accessibility: { wheelchair: true, big_car: false }, sharing_opt_in: true,
    })
    setPlan(undefined); setDevOpen(false); go('trip')
  }
  const loadSara = () => {
    resetAll(); setIdentity(sessionId, 'R-7K2'); setTok('R-7K2'); setMockScenario('sara'); setScenario('sara'); setDevOpen(false)
  }

  const fire = async (req: Omit<SimEventRequest, 'session_id'>) => {
    setBusy(true); setErr(undefined)
    try { setSim(await api.simEvent({ session_id: sessionId, ...req })); if (req.event === 'reset') resetAll() } catch (e) { setErr(e) } finally { setBusy(false) }
  }

  return (
    <Sheet open={devOpen} onClose={() => setDevOpen(false)} title="Simulation controls">
      <div className="space-y-4 text-plum">
        <section>
          <h3 className="mb-1 text-sm font-extrabold">Server</h3>
          <p className="text-xs">
            {typeof health === 'string' ? `⚠ ${health}` : health ? `OK · fixtures ${health.fixture_version} · gemini_ready ${String(health.gemini_ready)}` : 'checking…'}
          </p>
          <ul className="mt-2 grid grid-cols-2 gap-1 text-xs">
            {(Object.keys(LIVE) as Endpoint[]).map((k) => (
              <li key={k} className={`rounded-lg px-2 py-1 font-bold ${LIVE[k] ? 'bg-lime' : 'bg-amber-200'}`}>{k}: {LIVE[k] ? 'LIVE' : 'MOCK'}</li>
            ))}
          </ul>
          <p className="mt-1 text-xs text-plum/60">Live is the default. Explicit offline QA: <code>?live=mock</code>; return to live: <code>?live=all</code>.</p>
        </section>

        <section className="space-y-2">
          <h3 className="text-sm font-extrabold">Session & rider</h3>
          <input className={inputCls} aria-label="Session id" value={sid} onChange={(e) => setSid(e.target.value)} />
          <input className={inputCls} aria-label="Rider token" value={tok} onChange={(e) => setTok(e.target.value)} />
          <p className="text-xs text-plum/70">Independent users get their own session automatically. For the stage demo with Fleet controls, use one shared session.</p>
          <Button variant="outline-lime" onClick={() => setSid(SHARED_SESSION)}>Use shared stage session ({SHARED_SESSION})</Button>
          <div className="grid grid-cols-2 gap-2">
            <Button variant="outline-lime" onClick={loadSara}>Load Sara demo</Button>
            <Button variant="outline-lime" onClick={loadZaid}>Load Zaid demo</Button>
          </div>
          <Button onClick={() => { setIdentity(sid.trim(), tok.trim()); setDevOpen(false) }}>Apply</Button>
        </section>

        <section className="space-y-2">
          <h3 className="text-sm font-extrabold">Mock scenario (only affects MOCK /api/plan)</h3>
          <select className={inputCls} value={scenario} onChange={(e) => { const s = e.target.value as MockScenario; setScenario(s); setMockScenario(s); resetAll() }}>
            <option value="sara">Sara · Best Deal (golden path)</option>
            <option value="wav_ok">Zaid · wheelchair, WAV-01 available</option>
            <option value="wav_out">Wheelchair · WAV unavailable (honest no-option)</option>
          </select>
        </section>

        <section className="space-y-2">
          <h3 className="text-sm font-extrabold">Simulation events</h3>
          {EVENTS.map((e) => <Button key={e.label} variant="danger" disabled={busy} onClick={() => fire(e.req)}>{e.label}</Button>)}
          <ErrorBox error={err} />
        </section>
      </div>
    </Sheet>
  )
}

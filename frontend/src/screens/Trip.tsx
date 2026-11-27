import { useMemo, useState } from 'react'
import { Accessibility, Lock, SlidersHorizontal, Zap } from 'lucide-react'
import { api } from '../api'
import { fmtFils, fmtJod, newKey, weekdayOf } from '../format'
import { currency } from '../i18n'
import { useT } from '../useT'
import { useStore } from '../store'
import type { EmergencyRequest, EmergencyResponse, GenderPool, PlanRequest } from '../types'
import { Button, Card, Chip, ErrorBox, Field, inputCls, Intro, MockChip, Sheet } from '../components/ui'
import { ProposalView } from '../components/ProposalView'

const ZONES = [
  { zone_id: 'irbid_east', campus_id: 'JUST', label: 'Irbid East → JUST' },
  { zone_id: 'irbid_nuzha', campus_id: 'JUST', label: 'Irbid Nuzha → JUST' },
  { zone_id: 'sweileh', campus_id: 'AAU', label: 'Sweileh → AAU' },
]

function Toggle({ on, onChange, label, sub, tone = 'magenta' }:
  { on: boolean; onChange: (b: boolean) => void; label: string; sub?: string; tone?: 'magenta' | 'lime' }) {
  return (
    <button type="button" role="switch" aria-checked={on} onClick={() => onChange(!on)}
      className="flex min-h-14 w-full items-center justify-between gap-3 rounded-xl bg-white p-3 text-start">
      <span><span className="block font-bold text-plum">{label}</span>{sub && <span className="block text-xs text-plum/60">{sub}</span>}</span>
      <span className={`flex h-7 w-12 shrink-0 items-center rounded-full p-0.5 transition-colors ${on ? (tone === 'lime' ? 'bg-lime' : 'bg-magenta') : 'bg-plum/20'}`}>
        <span className={`size-6 rounded-full bg-white shadow transition-transform ${on ? 'translate-x-5 rtl:-translate-x-5' : ''}`} />
      </span>
    </button>
  )
}

/** Default pickup = 46 min before the class (08:30 → 07:44, the Rev. E demo value). */
const PICKUP_LEAD_MIN = 46
function defaultPickup(classStart?: string): string {
  if (!classStart) return '07:44'
  const [h, m] = classStart.split(':').map(Number)
  const mins = Math.max(0, h * 60 + m - PICKUP_LEAD_MIN)
  return `${String(Math.floor(mins / 60)).padStart(2, '0')}:${String(mins % 60).padStart(2, '0')}`
}

export default function Trip() {
  const t = useT()
  const { sessionId, riderToken, classes, request, runPlan, go, sim, setSim, preset } = useStore()
  const init = request
  const [zone, setZone] = useState(init?.zone_id ?? 'irbid_east')
  const [date, setDate] = useState(init?.service_date ?? '2026-11-29')
  const [classStart, setClassStart] = useState(init?.class_start ?? '')
  const [buffer, setBuffer] = useState(init?.arrival_buffer_min ?? 10)
  const [pool, setPool] = useState<GenderPool>(init?.gender_pool ?? 'female_only')
  const [companions, setCompanions] = useState(init?.desired_companions ?? preset?.companions ?? 3)
  // null = follow the chosen class; a string = the rider's own edit (kept as-is).
  const [pickupOverride, setPickupOverride] = useState<string | null>(init?.preferred_pickup ?? null)
  const [capJod, setCapJod] = useState(init ? init.fare_cap_fils / 1000 : preset?.capJod ?? 2)
  const [wheelchair, setWheelchair] = useState(init?.accessibility.wheelchair ?? preset?.wheelchair ?? false)
  const [bigCar, setBigCar] = useState(init?.accessibility.big_car ?? false)
  const [optIn, setOptIn] = useState(init?.sharing_opt_in ?? true)

  // emergency
  const [now, setNow] = useState(sim?.sim_time ?? '07:58')
  const [emg, setEmg] = useState<EmergencyResponse | null>(null)
  const [emgBusy, setEmgBusy] = useState(false)
  const [emgErr, setEmgErr] = useState<unknown>()

  const wd = weekdayOf(date)
  const todays = useMemo(() => classes.filter((c) => c.weekday === wd).sort((a, b) => a.start.localeCompare(b.start)), [classes, wd])
  const chosen = todays.find((c) => c.start === classStart) ?? todays[0]
  const pickup = pickupOverride ?? defaultPickup(chosen?.start)
  const campus = ZONES.find((z) => z.zone_id === zone)!.campus_id
  const capFils = Math.round(capJod * 1000)

  const submit = async () => {
    if (!chosen) return
    const req: PlanRequest = {
      session_id: sessionId, rider_token: riderToken, campus_id: campus, zone_id: zone, service_date: date,
      class_start: chosen.start, arrival_buffer_min: buffer, pickup_mode: 'door_to_door', gender_pool: pool,
      desired_companions: companions, booking: 'day_ahead', preferred_pickup: pickup, fare_cap_fils: capFils,
      accessibility: { wheelchair, big_car: bigCar }, sharing_opt_in: optIn,
    }
    go('journey')
    void runPlan(req)
  }

  const askEmergency = async () => {
    if (!chosen) return
    setEmgBusy(true); setEmgErr(undefined)
    // same hard constraints as normal planning (gender pool, accessibility, cap, deadline buffer)
    const req: EmergencyRequest = {
      session_id: sessionId, rider_token: riderToken, campus_id: campus, zone_id: zone, service_date: date,
      class_start: chosen.start, arrival_buffer_min: buffer, request_time: now, gender_pool: pool,
      fare_cap_fils: capFils, accessibility: { wheelchair, big_car: bigCar }, sharing_opt_in: optIn,
    }
    try { setEmg(await api.emergency(req)) }
    catch (e) { setEmgErr(e) } finally { setEmgBusy(false) }
  }
  const approveEmergency = async () => {
    const p = emg?.proposal
    if (!p) return
    setEmgBusy(true); setEmgErr(undefined)
    try {
      await api.confirm({
        session_id: sessionId, rider_token: riderToken, plan_id: p.plan.plan_id, plan_revision: p.plan_revision,
        accepted_fare_fils: p.plan.fare.your_share_fils, idempotency_key: newKey(),
      })
      setSim(await api.simState(sessionId)); setEmg(null); go('booked')
    } catch (e) { setEmgErr(e) } finally { setEmgBusy(false) }
  }

  return (
    <div className="space-y-4">
      <Intro title={t('Plan your ride')} text={t('Door-to-Door to campus, shared fairly. Tell us what matters.')} />
      <div className="flex flex-wrap gap-2">
        <MockChip endpoint="plan" />
        {preset && !init && <Chip tone="lime">{t(preset.service === 'ride' ? 'Ride: ride alone' : preset.service === 'carpool' ? 'Carpooling: up to 3 companions' : 'Accessibility: wheelchair on')}</Chip>}
      </div>

      <Card className="space-y-4">
        <Field label={t('Where from?')}>
          <select className={inputCls} value={zone} onChange={(e) => setZone(e.target.value)}>
            {ZONES.map((z) => <option key={z.zone_id} value={z.zone_id}>{t(z.label)}</option>)}
          </select>
        </Field>
        <Field label={t('Day')} hint={wd ? t(`${wd}day`) : t('No classes on Fridays and Saturdays')}>
          <input type="date" className={inputCls} value={date} onChange={(e) => setDate(e.target.value)} />
        </Field>
        {wd && todays.length === 0 && <p className="rounded-xl bg-amber-100 p-3 text-sm text-plum">{t('No classes saved for {d}. Go back and add one to your timetable.', { d: t(`${wd}day`) })}</p>}
        {todays.length > 0 && (
          <fieldset>
            <legend className="mb-1 text-sm font-bold text-plum">{t('Which class are you riding for?')}</legend>
            <div className="grid grid-cols-2 gap-2">
              {todays.map((c) => (
                <button key={c.id} type="button" aria-pressed={chosen?.id === c.id} onClick={() => setClassStart(c.start)}
                  className={`min-h-14 rounded-xl border-2 p-2 text-start ${chosen?.id === c.id ? 'border-magenta bg-white' : 'border-transparent bg-white/60'}`}>
                  <span className="block text-xl font-black text-plum">{c.start}</span>
                  <span className="block truncate text-xs text-plum/70">{c.course}</span>
                </button>
              ))}
            </div>
          </fieldset>
        )}
        <Field label={t('Arrive before class')} hint={t('Your deadline is calculated by the server from this.')}>
          <select className={inputCls} value={buffer} onChange={(e) => setBuffer(Number(e.target.value))}>
            {[5, 10, 15].map((m) => <option key={m} value={m}>{t('{m} minutes', { m })}</option>)}
          </select>
        </Field>
        <div className="flex items-center gap-2 rounded-xl bg-white p-3 text-sm font-bold text-plum">
          <Chip tone="lime">{t('Default')}</Chip> {t('Door-to-Door pickup')}
        </div>
      </Card>

      <Card className="space-y-3">
        <h2 className="flex items-center gap-2 font-extrabold text-plum"><Lock className="size-4" aria-hidden /> {t('Never relaxed')}</h2>
        <div role="radiogroup" aria-label={t('Who can ride with you')} className="grid grid-cols-2 gap-2">
          {(['female_only', 'male_only'] as GenderPool[]).map((g) => (
            <button key={g} role="radio" aria-checked={pool === g} onClick={() => setPool(g)}
              className={`min-h-12 rounded-xl border-2 px-3 font-bold ${pool === g ? 'border-magenta bg-white text-plum' : 'border-transparent bg-white/60 text-plum/70'}`}>
              {g === 'female_only' ? t('Female-only') : t('Male-only')}
            </button>
          ))}
        </div>
        <Toggle tone="lime" on={wheelchair} onChange={setWheelchair} label={t('I use a wheelchair')} sub={t('Only ramp vehicles are offered. If none, we say so — never a car without a ramp.')} />
        <Toggle tone="lime" on={bigCar} onChange={setBigCar} label={t('I need a Big Car')} sub={t('Extra space for equipment.')} />
        <p className="flex items-center gap-1.5 text-xs text-plum/60"><Accessibility className="size-4" aria-hidden /> {t('Max 4 riders per car and your arrival deadline are always enforced.')}</p>
      </Card>

      <Card className="space-y-4">
        <h2 className="flex items-center gap-2 font-extrabold text-plum"><SlidersHorizontal className="size-4" aria-hidden /> {t('Can be flexible (Best Deal)')}</h2>
        <Field label={companions === 0 ? t('Companions: 0 (ride alone)') : t('Companions: {n}', { n: companions })} hint={t('If no exact match, Best Deal relaxes ONE of these at a time.')}>
          <input type="range" min={0} max={3} step={1} value={companions} onChange={(e) => setCompanions(Number(e.target.value))} className="h-10 w-full accent-magenta" />
        </Field>
        <Field label={t('Preferred pickup time')}>
          <input type="time" className={inputCls} value={pickup} onChange={(e) => setPickupOverride(e.target.value)} />
        </Field>
        <Field label={t('Fare cap (JOD)')} hint={t('Max your share: {x}. You approve every price increase.', { x: `${currency()} ${fmtJod(capFils)} (${fmtFils(capFils)})` })}>
          <input type="number" inputMode="decimal" min={0.5} step={0.1} className={inputCls} value={capJod} onChange={(e) => setCapJod(Number(e.target.value))} />
        </Field>
        <Toggle on={optIn} onChange={setOptIn} label={t('Share the ride')} sub={t('Required to split the fare with same-pool students.')} />
      </Card>

      <Button disabled={!chosen || (!optIn && companions > 0) || capFils < 100} onClick={submit}>{t('Find my ride')}</Button>
      {!optIn && companions > 0 && <p className="text-center text-sm text-white/70">{t('Turn on “Share the ride” to find shared options.')}</p>}

      <Card className="space-y-3">
        <h2 className="flex items-center gap-2 font-extrabold text-plum"><Zap className="size-4" aria-hidden /> {t('Running late?')}</h2>
        <p className="text-sm text-plum/70">{t('Emergency mode looks for a trip already on the road. Price changes apply to you only.')}</p>
        <Field label={t('It is now (simulated)')}><input type="time" className={inputCls} value={now} onChange={(e) => setNow(e.target.value)} /></Field>
        <ErrorBox error={emgErr} />
        <Button variant="outline-lime" busy={emgBusy && !emg} disabled={!chosen} onClick={askEmergency}>{t('Find me a ride now')}</Button>
      </Card>

      <Sheet open={!!emg} onClose={() => setEmg(null)} title={t('Emergency ride')}>
        {emg?.proposal ? (
          <ProposalView p={emg.proposal} myToken={riderToken} busy={emgBusy} approveLabel={`${t('Approve')} · ${currency()} ${fmtJod(emg.proposal.plan.fare.your_share_fils)}`}
            onApprove={approveEmergency} onDecline={() => setEmg(null)} />
        ) : emg && (
          <div className="space-y-3 text-plum">
            <p className="font-bold">{emg.reason?.message ?? emg.message}</p>
            {emg.status === 'solo_handoff_eligible' && (
              <p className="rounded-xl bg-white p-3 text-sm">{t('A standard solo ride may be possible, but it is only a simulated hand-off and may be above your fare cap. Nothing is dispatched or booked.')}</p>
            )}
            <Button variant="danger" onClick={() => setEmg(null)}>{t('Close')}</Button>
          </div>
        )}
        <ErrorBox error={emgErr} />
      </Sheet>
    </div>
  )
}

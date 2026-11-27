import { useEffect, useRef, useState } from 'react'
import {
  Accessibility, ArrowRight, BellRing, CalendarDays, Camera, Car, CheckCircle2, Mic, Package, Search, Users, Wallet, Zap,
} from 'lucide-react'
import { useStore, type Service } from '../store'
import { useT } from '../useT'
import { jod } from '../format'
import type { SimState, TripView } from '../types'
import { BellButton, initials, MenuIcon } from '../components/Chrome'
import { Chip } from '../components/ui'
import { BoxSheet, VoiceSheet } from '../components/Assist'

const isActive = (x: TripView) => x.status !== 'canceled' && x.status !== 'completed'

export default function Home({ onMenu, onNotif }: { onMenu: () => void; onNotif: () => void }) {
  const t = useT()
  const { sim, displayName, riderToken, go, startService, timetableConfirmed, classes } = useStore()
  const [voice, setVoice] = useState(false)
  const [box, setBox] = useState(false)
  const trip = sim?.trips.find(isActive)

  // When the active trip finishes (completed), show a short "back to normal" note.
  const lastId = useRef<string | undefined>(undefined)
  const [ended, setEnded] = useState<string>()
  useEffect(() => {
    const prev = lastId.current
    if (prev && !trip) {
      const was = sim?.trips.find((x) => x.trip_id === prev)
      if (was?.status === 'completed') setEnded(prev)
    }
    lastId.current = trip?.trip_id
  }, [trip, sim])
  useEffect(() => {
    if (!ended) return
    const id = window.setTimeout(() => setEnded(undefined), 5000)
    return () => window.clearTimeout(id)
  }, [ended])

  const name = displayName.trim() || 'Lubna'

  return (
    <div className="pb-32">
      <header className="relative overflow-hidden rounded-b-[2rem] bg-plum-2 px-4 pb-5 pt-4 shadow-xl">
        <RouteDecor />
        <div className="relative flex items-center gap-3">
          <button onClick={onMenu} aria-label={t('Open menu')} className="grid size-11 shrink-0 place-items-center rounded-2xl bg-white/10 text-white"><MenuIcon /></button>
          <button onClick={() => go('wallet')} className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl text-start" aria-label={t('Profile and wallet')}>
            <span className="grid size-12 shrink-0 place-items-center rounded-full bg-magenta text-lg font-black text-white ring-2 ring-lime/70">{initials(name)}</span>
            <span className="min-w-0">
              <span className="block truncate text-lg font-black leading-tight text-white">{name}</span>
              <span className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] font-bold text-white/70">
                <span>{t('ID {id}', { id: riderToken })}</span>
                {sim && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-lime px-2 py-0.5 text-plum">
                    <Wallet className="size-3" aria-hidden />{jod(sim.wallet.balance_fils)}
                  </span>
                )}
                {sim && <span className="rounded-full bg-white/10 px-2 py-0.5">{t('Trips: {n}', { n: sim.trips.length })}</span>}
              </span>
            </span>
          </button>
          <BellButton onClick={onNotif} />
        </div>

        {trip && sim && <TrackingCard trip={trip} sim={sim} />}
        {ended && (
          <p role="status" className="reveal relative mt-4 flex items-center gap-2 rounded-2xl bg-lime p-3 text-sm font-extrabold text-plum">
            <CheckCircle2 className="size-5" aria-hidden /> {t('Trip {id} completed. Welcome back!', { id: ended })}
          </p>
        )}

        <div className="relative mt-4 flex items-center gap-2 rounded-2xl bg-white p-1.5 shadow-lg">
          <button onClick={() => (timetableConfirmed ? go('trip') : go('schedule'))} className="flex min-h-12 min-w-0 flex-1 items-center gap-3 rounded-xl px-2 text-start">
            <Search className="size-5 shrink-0 text-magenta" aria-hidden />
            <span className="min-w-0">
              <span className="block truncate text-base font-black text-plum">{t('Where to, {name}?', { name: name.toUpperCase() })}</span>
              <span className="block truncate text-xs font-semibold text-plum/55">{t('Campus, class or hub')}</span>
            </span>
          </button>
          <button onClick={() => setVoice(true)} aria-label={t('Speak your request')}
            className="grid size-12 shrink-0 place-items-center rounded-xl bg-magenta text-white"><Mic className="size-5" aria-hidden /></button>
        </div>
      </header>

      <Promos onPick={(s) => (s === 'schedule' ? go('schedule') : s === 'late' ? go(timetableConfirmed ? 'trip' : 'schedule') : startService(s))} />

      <section aria-labelledby="svc" className="px-4 pt-6">
        <h2 id="svc" className="mb-3 text-lg font-black text-white">{t('Services')}</h2>
        <div className="grid grid-cols-2 gap-3">
          <Tile Icon={Car} title={t('Ride')} sub={t('Your own ride to campus')} tone="plum" onClick={() => startService('ride')} />
          <Tile Icon={Package} title={t('Box')} sub={t('Send a parcel along your trip')} tone="plum" onClick={() => setBox(true)} />
          <Tile Icon={Users} title={t('Carpooling')} sub={t('Share the ride, split fairly')} tone="magenta" badge={t('UniLink')} onClick={() => startService('carpool')} />
          <Tile Icon={Accessibility} title={t('Accessibility')} sub={t('Ramp vehicles only')} tone="lime" badge={t('UniLink')} onClick={() => startService('accessibility')} />
        </div>
      </section>

      <section className="px-4 pt-5">
        <button onClick={() => go('schedule')} className="flex min-h-16 w-full items-center gap-3 rounded-2xl bg-plum-2 p-3 text-start">
          <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-lime text-plum"><CalendarDays className="size-5" aria-hidden /></span>
          <span className="min-w-0 flex-1">
            <span className="block font-extrabold">{timetableConfirmed ? t('Timetable: {n} classes', { n: classes.length }) : t('Add your timetable')}</span>
            <span className="block text-xs text-white/65">{timetableConfirmed ? t('Tap to review or edit') : t('Upload a photo or type it in — needed before booking')}</span>
          </span>
          <ArrowRight className="size-5 text-lime rtl:rotate-180" aria-hidden />
        </button>
      </section>

      <VoiceSheet open={voice} onClose={() => setVoice(false)} />
      <BoxSheet open={box} onClose={() => setBox(false)} trip={trip} />
    </div>
  )
}

/* ───────────── live tracking card (pushes the rest of Home down) ───────────── */
function TrackingCard({ trip, sim }: { trip: TripView; sim: SimState }) {
  const t = useT()
  const { go } = useStore()
  const p = trip.plan
  const stops = [
    ...(p.pickups ?? []).map((s) => ({ key: s.rider_token, label: s.is_you ? t('You') : t(s.landmark).split(' · ')[0], time: s.time, you: s.is_you })),
    { key: 'campus', label: t('Campus'), time: p.arrival, you: false },
  ]
  // Display only: a stop counts as passed once the simulated clock reaches its server-given time.
  const passed = (hhmm: string) => !!hhmm && sim.sim_time >= hhmm
  const next = stops.find((s) => !passed(s.time))
  const pending = sim.pending_proposals.length
  const status = trip.status === 'awaiting_consent' ? t('AWAITING CONSENT') : trip.status === 'dispatched' ? t('ON THE WAY') : t('BOOKED')
  const wav = p.vehicle?.wheelchair_accessible

  return (
    <section aria-live="polite" aria-label={t('Live trip')} className="reveal relative mt-4 overflow-hidden rounded-3xl bg-lavender text-plum shadow-xl">
      <div className="flex items-center justify-between bg-magenta px-4 py-2 text-white">
        <span className="inline-flex items-center gap-2 text-xs font-black tracking-[0.14em]">
          <span className="live-dot size-2 rounded-full bg-lime" aria-hidden /> {status}
        </span>
        <span className="text-xs font-bold">{t('Sim clock {t}', { t: sim.sim_time })}</span>
      </div>
      <div className="p-4">
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-[11px] font-bold uppercase text-plum/60">{next ? t('Next: {s}', { s: next.label }) : t('Arriving')}</p>
            <p className="text-3xl font-black leading-none tabular-nums">{next?.time || p.arrival}</p>
          </div>
          <div className="text-end">
            <p className="text-[11px] font-bold uppercase text-plum/60">{t('Arrive')}</p>
            <p className="text-xl font-black tabular-nums text-magenta">{p.arrival}</p>
          </div>
        </div>

        <ol className="mt-3 flex items-start" aria-label={t('Pickup order')}>
          {stops.map((s, i) => {
            const done = passed(s.time)
            return (
              <li key={s.key} className="flex min-w-0 flex-1 flex-col items-center text-center">
                <span className="flex w-full items-center">
                  <span className={`h-1 flex-1 ${i === 0 ? 'invisible' : done ? 'bg-magenta' : 'bg-plum/15'}`} />
                  <span className={`grid size-5 shrink-0 place-items-center rounded-full border-2 ${
                    s.key === 'campus' ? 'border-plum bg-lime' : done ? 'border-magenta bg-magenta' : s.you ? 'border-magenta bg-white' : 'border-plum/30 bg-white'}`} />
                  <span className={`h-1 flex-1 ${i === stops.length - 1 ? 'invisible' : passed(stops[i + 1].time) ? 'bg-magenta' : 'bg-plum/15'}`} />
                </span>
                <span className={`mt-1 w-full truncate px-0.5 text-[10px] font-bold ${s.you ? 'text-magenta' : 'text-plum/70'}`}>{s.label}</span>
                <span className="text-[10px] font-black tabular-nums">{s.time}</span>
              </li>
            )
          })}
        </ol>

        <div className="mt-3 flex flex-wrap gap-1.5">
          {p.vehicle && <Chip tone={wav ? 'lime' : 'soft'}>{wav && <Accessibility className="size-3.5" aria-hidden />}{t(p.vehicle.label)}</Chip>}
          <Chip tone="soft">{t('Leave home {t}', { t: p.leave_home })}</Chip>
          <Chip tone="soft">{t('Paid {x}', { x: jod(trip.amount_paid_fils) })}</Chip>
        </div>

        {pending > 0 && (
          <button onClick={() => go('booked')} className="mt-3 flex min-h-12 w-full items-center gap-2 rounded-2xl bg-plum px-3 text-start text-sm font-extrabold text-white">
            <BellRing className="size-5 text-lime" aria-hidden /> <span className="flex-1">{t('{n} update(s) need your OK', { n: pending })}</span>
            <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
          </button>
        )}
        <button onClick={() => go('booked')} className="mt-2 min-h-11 w-full rounded-2xl border-2 border-plum/15 bg-white text-sm font-extrabold">{t('View boarding pass')}</button>
      </div>
    </section>
  )
}

/* ───────────── animated promo boxes (features, not invented offers) ───────────── */
type PromoTarget = Service | 'schedule' | 'late'
const PROMOS: { id: PromoTarget; title: string; text: string; cta: string; Icon: typeof Camera; cls: string }[] = [
  { id: 'schedule', title: 'Snap your timetable', text: 'Gemini reads your classes. You check every field before anything is booked.', cta: 'Add timetable', Icon: Camera, cls: 'bg-lime text-plum' },
  { id: 'carpool', title: 'Carpool to campus, split fairly', text: 'Each rider pays for the distance they ride. Same-pool riders only.', cta: 'Find a carpool', Icon: Users, cls: 'bg-magenta text-white' },
  { id: 'accessibility', title: 'Accessibility first', text: 'Ramp vehicles only. If none is free, we tell you honestly.', cta: 'Accessible ride', Icon: Accessibility, cls: 'bg-white text-plum' },
  { id: 'late', title: 'Running late?', text: 'Emergency mode looks for a car already on the road to campus.', cta: 'Plan now', Icon: Zap, cls: 'bg-plum text-white ring-2 ring-lime/60' },
]

function Promos({ onPick }: { onPick: (s: PromoTarget) => void }) {
  const t = useT()
  const ref = useRef<HTMLDivElement>(null)
  const [i, setI] = useState(0)
  const [paused, setPaused] = useState(false)

  useEffect(() => {
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduce || paused) return
    const id = window.setInterval(() => setI((x) => (x + 1) % PROMOS.length), 4500)
    return () => window.clearInterval(id)
  }, [paused])
  useEffect(() => {
    const el = ref.current
    const card = el?.children[i] as HTMLElement | undefined
    if (el && card) el.scrollTo({ left: card.offsetLeft - el.offsetLeft - 16, behavior: 'smooth' })
  }, [i])
  const onScroll = () => {
    const el = ref.current
    if (!el) return
    const kids = Array.from(el.children) as HTMLElement[]
    const mid = el.scrollLeft + el.clientWidth / 2 + el.offsetLeft
    let best = 0, bd = Infinity
    kids.forEach((k, j) => { const d = Math.abs(k.offsetLeft + k.clientWidth / 2 - mid); if (d < bd) { bd = d; best = j } })
    if (best !== i) setI(best)
  }

  return (
    <section aria-roledescription="carousel" aria-label={t('What UniLink can do')} className="pt-5"
      onPointerDown={() => setPaused(true)} onFocus={() => setPaused(true)}>
      <div ref={ref} onScroll={onScroll} className="no-scrollbar flex snap-x snap-mandatory gap-3 overflow-x-auto px-4 pb-1">
        {PROMOS.map(({ id, title, text, cta, Icon, cls }, j) => (
          <article key={id} aria-roledescription="slide" aria-label={`${j + 1} / ${PROMOS.length}`}
            className={`promo relative w-[86%] shrink-0 snap-center overflow-hidden rounded-3xl p-4 shadow-lg ${cls}`}>
            <span className="float-a pointer-events-none absolute -end-6 -top-6 size-24 rounded-full bg-current opacity-10" aria-hidden />
            <span className="float-b pointer-events-none absolute -bottom-8 end-10 size-16 rounded-full bg-current opacity-10" aria-hidden />
            <Icon className="size-7" aria-hidden />
            <h3 className="mt-2 text-lg font-black leading-tight">{t(title)}</h3>
            <p className="mt-1 text-sm opacity-80">{t(text)}</p>
            <button onClick={() => onPick(id)} className="mt-3 inline-flex min-h-10 items-center gap-1.5 text-sm font-extrabold underline-offset-4 hover:underline">
              {t(cta)} <ArrowRight className="size-4 rtl:rotate-180" aria-hidden />
            </button>
          </article>
        ))}
      </div>
      <div className="mt-2 flex justify-center gap-1.5" aria-hidden>
        {PROMOS.map((p, j) => <span key={p.id} className={`h-1.5 rounded-full transition-all ${j === i ? 'w-6 bg-lime' : 'w-1.5 bg-white/30'}`} />)}
      </div>
    </section>
  )
}

function Tile({ Icon, title, sub, tone, badge, onClick }:
  { Icon: typeof Car; title: string; sub: string; tone: 'plum' | 'magenta' | 'lime'; badge?: string; onClick: () => void }) {
  const ic = { plum: 'bg-plum text-lime', magenta: 'bg-magenta text-white', lime: 'bg-lime text-plum' }[tone]
  return (
    <button onClick={onClick} className="relative flex min-h-32 flex-col items-start rounded-3xl bg-lavender p-4 text-start text-plum shadow-lg transition-transform active:scale-[.97]">
      {badge && <span className="absolute end-3 top-3 rounded-full bg-plum px-2 py-0.5 text-[10px] font-black text-lime">{badge}</span>}
      <span className={`grid size-12 place-items-center rounded-2xl ${ic}`}><Icon className="size-6" aria-hidden /></span>
      <span className="mt-3 text-lg font-black leading-tight">{title}</span>
      <span className="mt-0.5 text-xs font-semibold text-plum/65">{sub}</span>
    </button>
  )
}

/** Subtle transit-line decoration behind the header. */
function RouteDecor() {
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox="0 0 400 260" preserveAspectRatio="none" aria-hidden>
      <path d="M-20 210 C 80 150, 160 250, 260 170 S 380 90, 430 120" fill="none" stroke="rgb(216 245 41 / .18)" strokeWidth="3" strokeDasharray="3 10" strokeLinecap="round" />
      <path d="M-20 60 C 90 20, 200 110, 300 40 S 400 10, 430 30" fill="none" stroke="rgb(236 0 140 / .25)" strokeWidth="3" strokeLinecap="round" />
      <circle cx="260" cy="170" r="6" fill="none" stroke="rgb(216 245 41 / .35)" strokeWidth="2.5" />
      <circle cx="300" cy="40" r="5" fill="rgb(236 0 140 / .45)" />
    </svg>
  )
}

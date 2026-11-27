import { useEffect, useState } from 'react'
import {
  BarChart3, Bell, CalendarDays, History, Home, Languages, Route, Sliders, Ticket, Wallet, X,
} from 'lucide-react'
import { useStore, type View } from '../store'
import { useT } from '../useT'
import { jod } from '../format'
import { Button, Sheet } from './ui'

/** Initials for the avatar; falls back to a neutral mark. */
export const initials = (name: string) =>
  name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase() ?? '').join('') || '•'

/** Bottom navigation: Wallet · Home (centre) · History. */
export function BottomNav() {
  const t = useT()
  const { view, go } = useStore()
  const item = (v: View, label: string, Icon: typeof Wallet) => (
    <button onClick={() => go(v)} aria-current={view === v ? 'page' : undefined}
      className={`flex min-h-14 flex-1 flex-col items-center justify-center gap-0.5 text-[11px] font-extrabold ${view === v ? 'text-magenta' : 'text-plum/60'}`}>
      <Icon className="size-6" aria-hidden />{t(label)}
    </button>
  )
  return (
    <nav aria-label={t('Main')} className="fixed inset-x-0 bottom-0 z-30 mx-auto w-full max-w-md">
      <div className="relative flex items-end rounded-t-3xl bg-white px-6 pb-[max(0.5rem,env(safe-area-inset-bottom))] pt-1 shadow-[0_-10px_30px_rgb(0_0_0/0.25)]">
        {item('wallet', 'Wallet', Wallet)}
        <div className="flex flex-1 justify-center">
          <button onClick={() => go('home')} aria-current={view === 'home' ? 'page' : undefined} aria-label={t('Home')}
            className={`-mt-8 grid size-16 place-items-center rounded-full border-4 border-white shadow-lg transition-colors ${view === 'home' ? 'bg-magenta text-white' : 'bg-plum text-lime'}`}>
            <Home className="size-7" aria-hidden />
          </button>
        </div>
        {item('history', 'History', History)}
      </div>
    </nav>
  )
}

/** Header for every screen except Home: back to Home, title, language. Flow screens keep the 4-step progress. */
const STEPS: { view: View; label: string; Icon: typeof Route }[] = [
  { view: 'schedule', label: 'Schedule', Icon: CalendarDays },
  { view: 'trip', label: 'Trip', Icon: Sliders },
  { view: 'journey', label: 'Journey', Icon: Route },
  { view: 'booked', label: 'Pass', Icon: Ticket },
]
const TITLES: Partial<Record<View, string>> = {
  wallet: 'Wallet', history: 'History', insights: 'Fleet Insights',
}
export function SubHeader({ onMenu }: { onMenu: () => void }) {
  const t = useT()
  const { view, go, timetableConfirmed, plan, planning, planError, sim, lang, setLang } = useStore()
  const enabled: Partial<Record<View, boolean>> = {
    schedule: true, trip: timetableConfirmed, journey: !!plan || planning || !!planError, booked: !!sim?.trips.length,
  }
  const inFlow = STEPS.some((s) => s.view === view)
  return (
    <header className="sticky top-0 z-20 bg-plum/95 px-4 pb-2 pt-3 backdrop-blur">
      <div className="mb-2 flex items-center gap-2">
        <button onClick={onMenu} aria-label={t('Open menu')} className="grid size-11 place-items-center rounded-2xl bg-plum-2"><MenuIcon /></button>
        <p className="min-w-0 flex-1 truncate text-lg font-black tracking-tight">
          {TITLES[view] ? t(TITLES[view]!) : <>Jeeny <span className="text-lime">UniLink</span></>}
        </p>
        <button onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')} className="inline-flex min-h-11 items-center gap-1 rounded-full bg-plum-2 px-3 text-sm font-extrabold"
          aria-label={lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}>
          <Languages className="size-4" aria-hidden />{lang === 'ar' ? 'EN' : 'عربي'}
        </button>
        <button onClick={() => go('home')} aria-label={t('Home')} className="grid size-11 place-items-center rounded-2xl bg-plum-2"><Home className="size-5" aria-hidden /></button>
      </div>
      {inFlow && (
        <nav aria-label={t('Progress')} className="grid grid-cols-4 gap-1.5">
          {STEPS.map(({ view: v, label, Icon }) => (
            <button key={v} disabled={!enabled[v]} aria-current={view === v ? 'step' : undefined} onClick={() => go(v)}
              className={`flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-xl text-[11px] font-extrabold transition-colors ${
                view === v ? 'bg-lime text-plum' : enabled[v] ? 'bg-plum-2 text-white' : 'bg-plum-2/50 text-white/35'}`}>
              <Icon className="size-4" aria-hidden />{t(label)}
            </button>
          ))}
        </nav>
      )}
    </header>
  )
}

/** Three stacked bars (side menu). */
export function MenuIcon() {
  return (
    <span className="flex w-5 flex-col gap-[5px]" aria-hidden>
      <span className="h-0.5 rounded bg-current" /><span className="h-0.5 rounded bg-current" /><span className="h-0.5 w-3.5 rounded bg-current" />
    </span>
  )
}

export function BellButton({ onClick }: { onClick: () => void }) {
  const t = useT()
  const { sim } = useStore()
  const n = sim?.pending_proposals.length ?? 0
  return (
    <button onClick={onClick} aria-label={n ? t('Notifications ({n} new)', { n }) : t('Notifications')}
      className="relative grid size-11 place-items-center rounded-2xl bg-white/10 text-white">
      <Bell className="size-5" aria-hidden />
      {n > 0 && <span className="absolute -end-1 -top-1 grid min-w-5 place-items-center rounded-full bg-magenta px-1 text-[11px] font-black ring-2 ring-plum">{n}</span>}
    </button>
  )
}

/** Side menu (slides in from the reading-start side). */
export function SideMenu({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT()
  const { go, displayName, setDisplayName, riderToken, lang, setLang, setDevOpen, sim, timetableConfirmed } = useStore()
  const [name, setName] = useState(displayName)
  useEffect(() => { if (open) setName(displayName) }, [open, displayName])
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', k)
    return () => document.removeEventListener('keydown', k)
  }, [open, onClose])
  if (!open) return null
  const to = (v: View) => { go(v); onClose() }
  const rows: { v: View; label: string; Icon: typeof Home; sub?: string }[] = [
    { v: 'home', label: 'Home', Icon: Home },
    { v: 'schedule', label: 'My timetable', Icon: CalendarDays, sub: timetableConfirmed ? t('Confirmed') : t('Not set yet') },
    { v: 'trip', label: 'Plan a ride', Icon: Sliders },
    { v: 'booked', label: 'My pass', Icon: Ticket },
    { v: 'wallet', label: 'Wallet', Icon: Wallet, sub: sim ? jod(sim.wallet.balance_fils) : undefined },
    { v: 'history', label: 'History', Icon: History },
    { v: 'insights', label: 'Fleet Insights', Icon: BarChart3 },
  ]
  return (
    <div className="fixed inset-0 z-50 flex bg-black/60" role="dialog" aria-modal="true" aria-label={t('Menu')} onClick={onClose}>
      <div className="menu-in flex h-full w-[82%] max-w-xs flex-col overflow-y-auto bg-lavender text-plum shadow-2xl" onClick={(e) => e.stopPropagation()}>
        <div className="bg-plum px-5 pb-5 pt-6 text-white">
          <div className="flex items-start justify-between">
            <span className="grid size-14 place-items-center rounded-full bg-magenta text-xl font-black">{initials(name)}</span>
            <button onClick={onClose} aria-label={t('Close')} className="grid size-10 place-items-center rounded-full hover:bg-white/10"><X className="size-5" /></button>
          </div>
          <label className="mt-3 block text-xs font-bold text-white/60">{t('Display name (this device only)')}
            <input value={name} onChange={(e) => setName(e.target.value)} onBlur={() => setDisplayName(name.trim() || 'Lubna')}
              className="mt-1 min-h-11 w-full rounded-xl bg-white/10 px-3 text-base font-extrabold text-white placeholder:text-white/40" />
          </label>
          <p className="mt-2 text-xs text-white/60">{t('Rider ID {id}', { id: riderToken })}</p>
        </div>
        <ul className="flex-1 space-y-1 p-3">
          {rows.map(({ v, label, Icon, sub }) => (
            <li key={v}>
              <button onClick={() => to(v)} className="flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-start font-bold hover:bg-plum/10">
                <Icon className="size-5 text-magenta" aria-hidden />
                <span className="flex-1">{t(label)}</span>
                {sub && <span className="text-xs font-semibold text-plum/60">{sub}</span>}
              </button>
            </li>
          ))}
          <li>
            <button onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')} className="flex min-h-12 w-full items-center gap-3 rounded-xl px-3 text-start font-bold hover:bg-plum/10">
              <Languages className="size-5 text-magenta" aria-hidden /><span className="flex-1">{t('Language')}</span>
              <span className="rounded-full bg-plum px-2.5 py-1 text-xs text-white">{lang === 'ar' ? 'عربي' : 'English'}</span>
            </button>
          </li>
        </ul>
        <div className="space-y-2 border-t border-plum/10 p-4">
          <Button variant="danger" onClick={() => { setDevOpen(true); onClose() }}>{t('Simulation controls')}</Button>
          <p className="text-xs text-plum/60">{t('Simulation data = the engine is real, the world is simulated. MOCK = a temporary stand-in, not the engine.')}</p>
        </div>
      </div>
    </div>
  )
}

const KIND: Record<string, string> = { smart_rescue: 'SMART RESCUE', class_shift: 'CLASS SHIFT', emergency: 'EMERGENCY RIDE' }

/** Notifications: what the server says needs the rider's attention. Nothing is invented. */
export function NotificationsSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT()
  const { sim, go } = useStore()
  const items = sim?.pending_proposals ?? []
  const trip = sim?.trips.find((x) => x.status !== 'canceled' && x.status !== 'completed')
  return (
    <Sheet open={open} onClose={onClose} title={t('Notifications')}>
      <ul className="space-y-2 text-plum">
        {items.map((p) => (
          <li key={p.proposal_id} className="rounded-2xl bg-white p-3">
            <p className="text-[11px] font-black tracking-[0.14em] text-magenta">{t(KIND[p.kind] ?? p.kind)}</p>
            <p className="mt-0.5 text-sm font-semibold">{p.message}</p>
            <button onClick={() => { go('booked'); onClose() }} className="mt-2 min-h-10 text-sm font-extrabold text-magenta underline">{t('Review now')}</button>
          </li>
        ))}
        {trip && (
          <li className="rounded-2xl bg-white p-3 text-sm">
            <p className="font-bold">{t('Trip {id} · arrive {a}', { id: trip.trip_id, a: trip.plan.arrival })}</p>
            <p className="text-xs text-plum/60">{t('Sim clock {t}', { t: sim?.sim_time ?? '' })}</p>
          </li>
        )}
        {!items.length && !trip && <li className="rounded-2xl bg-white p-4 text-sm">{t('No notifications yet. Updates about your trips appear here.')}</li>}
      </ul>
    </Sheet>
  )
}

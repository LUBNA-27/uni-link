import { CalendarDays, Languages, Route, Sliders, Ticket } from 'lucide-react'
import { StoreProvider, useStore, type View } from './store'
import Schedule from './screens/Schedule'
import Trip from './screens/Trip'
import Journey from './screens/Journey'
import Booked from './screens/Booked'
import Insights from './screens/Insights'
import { useT } from './useT'
import { DevDrawer } from './components/DevDrawer'
import { anyMock } from './api'

const STEPS: { view: View; label: string; Icon: typeof Route }[] = [
  { view: 'schedule', label: 'Schedule', Icon: CalendarDays },
  { view: 'trip', label: 'Trip', Icon: Sliders },
  { view: 'journey', label: 'Journey', Icon: Route },
  { view: 'booked', label: 'Pass', Icon: Ticket },
]

function Shell() {
  const t = useT()
  const { view, go, timetableConfirmed, plan, planning, planError, sim, setDevOpen, lang, setLang } = useStore()
  const enabled: Record<View, boolean> = {
    schedule: true,
    trip: timetableConfirmed,
    journey: !!plan || planning || !!planError,
    booked: !!sim?.trips.length,
    insights: true,
  }
  return (
    <div className="mx-auto flex min-h-dvh w-full max-w-md flex-col bg-plum text-white">
      <header className="sticky top-0 z-20 bg-plum/95 px-4 pb-2 pt-3 backdrop-blur">
        <div className="mb-2 flex items-center gap-2">
          <img src="./favicon.svg" alt="" className="size-8" />
          <div className="leading-tight">
            <p className="text-lg font-black tracking-tight">Jeeny <span className="text-lime">UniLink</span></p>
            <p className="text-[11px] font-semibold text-white/60">{t('Campus Commute · prototype')}</p>
          </div>
          <button onClick={() => setLang(lang === 'ar' ? 'en' : 'ar')} className="ms-auto inline-flex min-h-10 items-center gap-1 rounded-full bg-plum-2 px-3 text-sm font-extrabold" aria-label={lang === 'ar' ? 'Switch to English' : 'التبديل إلى العربية'}>
            <Languages className="size-4" aria-hidden />{lang === 'ar' ? 'EN' : 'عربي'}
          </button>
        </div>
        <nav aria-label={t('Progress')} className="grid grid-cols-4 gap-1.5">
          {STEPS.map(({ view: v, label, Icon }) => (
            <button key={v} disabled={!enabled[v]} aria-current={view === v ? 'step' : undefined} onClick={() => go(v)}
              className={`flex min-h-12 flex-col items-center justify-center gap-0.5 rounded-xl text-[11px] font-extrabold transition-colors ${
                view === v ? 'bg-lime text-plum' : enabled[v] ? 'bg-plum-2 text-white' : 'bg-plum-2/50 text-white/35'}`}>
              <Icon className="size-4" aria-hidden />{t(label)}
            </button>
          ))}
        </nav>
      </header>

      {anyMock() && (
        <p className="mx-4 mt-2 rounded-lg bg-amber-200 px-3 py-1.5 text-center text-xs font-bold text-plum" role="note">
          {t('Demo build: some screens use temporary MOCK data (not the real engine yet).')}
        </p>
      )}

      <main className="flex-1 px-4 pb-8 pt-4">
        {view === 'schedule' && <Schedule />}
        {view === 'trip' && <Trip />}
        {view === 'journey' && <Journey />}
        {view === 'booked' && <Booked />}
        {view === 'insights' && <Insights />}
      </main>

      <footer className="px-4 pb-6 text-center text-xs text-white/55">
        <p>{t('UniLink — hackathon prototype, simulation data.')}</p>
        <p className="mx-auto mt-1 max-w-xs">{t('Simulation data = the engine is real, the world is simulated. MOCK = a temporary stand-in, not the engine.')}</p>
        <button onClick={() => go('insights')} className="mt-1 min-h-10 px-3 font-bold underline">{t('Fleet Insights')}</button>
        <button onClick={() => setDevOpen(true)} className="mt-1 min-h-10 px-3 font-bold underline">{t('Simulation controls')}</button>
      </footer>
      <DevDrawer />
    </div>
  )
}

export default function App() {
  return (
    <StoreProvider>
      <Shell />
    </StoreProvider>
  )
}

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { api, LIVE } from './api'
import { applyLang, getLang, type Lang } from './i18n'
import type { ClassItem, PlanRequest, PlanResponse, SimState, UncertainField } from './types'

export type View = 'schedule' | 'trip' | 'journey' | 'booked' | 'insights'

interface Store {
  view: View
  go: (v: View) => void
  sessionId: string
  riderToken: string
  setIdentity: (sessionId: string, riderToken: string) => void
  classes: ClassItem[]
  uncertain: UncertainField[]
  timetableConfirmed: boolean
  setTimetable: (classes: ClassItem[], uncertain: UncertainField[], confirmed: boolean) => void
  request?: PlanRequest
  setRequest: (r: PlanRequest) => void
  plan?: PlanResponse
  setPlan: (p?: PlanResponse) => void
  sim?: SimState
  setSim: (s: SimState) => void
  refreshSim: () => Promise<void>
  /** planning state so Journey can show a skeleton / error / retry */
  planning: boolean
  planError?: unknown
  runPlan: (r: PlanRequest) => Promise<void>
  lang: Lang
  setLang: (l: Lang) => void
  devOpen: boolean
  setDevOpen: (b: boolean) => void
  resetAll: () => void
}

const Ctx = createContext<Store | null>(null)
export const useStore = () => {
  const c = useContext(Ctx)
  if (!c) throw new Error('useStore outside provider')
  return c
}

const SS = {
  get(k: string, d: string) { try { return localStorage.getItem(k) ?? d } catch { return d } },
  set(k: string, v: string) { try { localStorage.setItem(k, v) } catch { /* private mode */ } },
}
/** Independent users get their OWN session. The stage demo uses ?session=demo_01 (or the shared-session button). */
export const SHARED_SESSION = 'demo_01'
function initialSession(): string {
  const q = new URLSearchParams(window.location.search).get('session')
  if (q) { SS.set('uni.session', q); return q }
  const saved = SS.get('uni.session', '')
  if (saved) return saved
  const fresh = `s-${Math.random().toString(36).slice(2, 10)}`
  SS.set('uni.session', fresh)
  return fresh
}

export function StoreProvider({ children }: { children: ReactNode }) {
  const [view, setView] = useState<View>('schedule')
  const [sessionId, setSessionId] = useState(initialSession)
  const [riderToken, setRiderToken] = useState(() => SS.get('uni.rider', 'R-7K2'))
  const [classes, setClasses] = useState<ClassItem[]>([])
  const [uncertain, setUncertain] = useState<UncertainField[]>([])
  const [timetableConfirmed, setConfirmed] = useState(false)
  const [request, setRequest] = useState<PlanRequest>()
  const [plan, setPlan] = useState<PlanResponse>()
  const [sim, setSim] = useState<SimState>()
  const [planning, setPlanning] = useState(false)
  const [planError, setPlanError] = useState<unknown>()
  const [lang, setLangState] = useState<Lang>(getLang)
  const setLang = useCallback((l: Lang) => { applyLang(l); setLangState(l) }, [])
  const [devOpen, setDevOpen] = useState(() => new URLSearchParams(window.location.search).get('dev') === '1')

  const setIdentity = useCallback((s: string, r: string) => {
    setSessionId(s); setRiderToken(r); SS.set('uni.session', s); SS.set('uni.rider', r)
  }, [])
  const setTimetable = useCallback((c: ClassItem[], u: UncertainField[], ok: boolean) => {
    setClasses(c); setUncertain(u); setConfirmed(ok)
  }, [])

  const sid = useRef(sessionId)
  useEffect(() => { sid.current = sessionId }, [sessionId])
  const refreshSim = useCallback(async () => {
    try { setSim(await api.simState(sid.current)) } catch { /* surfaced by the screens that need it */ }
  }, [])

  // Poll per-session state while a trip or proposal exists (live only; the mock is pushed after each action).
  const needsPoll = view === 'booked' || (sim?.pending_proposals.length ?? 0) > 0
  useEffect(() => {
    if (!LIVE.state || !needsPoll) return
    const t = setInterval(refreshSim, 4000)
    const vis = () => { if (document.visibilityState === 'visible') void refreshSim() }
    document.addEventListener('visibilitychange', vis)
    return () => { clearInterval(t); document.removeEventListener('visibilitychange', vis) }
  }, [needsPoll, refreshSim])

  const runPlan = useCallback(async (r: PlanRequest) => {
    setRequest(r); setPlan(undefined); setPlanError(undefined); setPlanning(true)
    try {
      await refreshSim()
      setPlan(await api.plan(r))
    } catch (e) { setPlanError(e) } finally { setPlanning(false) }
  }, [refreshSim])

  const resetAll = useCallback(() => {
    setClasses([]); setUncertain([]); setConfirmed(false); setRequest(undefined); setPlan(undefined); setPlanError(undefined); setPlanning(false); setSim(undefined); setView('schedule')
  }, [])

  const value = useMemo<Store>(
    () => ({
      view, go: setView, sessionId, riderToken, setIdentity, classes, uncertain, timetableConfirmed, setTimetable,
      request, setRequest, plan, setPlan, sim, setSim, refreshSim, planning, planError, runPlan, lang, setLang, devOpen, setDevOpen, resetAll,
    }),
    [view, sessionId, riderToken, setIdentity, classes, uncertain, timetableConfirmed, setTimetable, request, plan, sim, refreshSim, planning, planError, runPlan, lang, setLang, devOpen, resetAll],
  )
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}

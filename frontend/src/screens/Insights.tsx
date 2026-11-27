import { useCallback, useEffect, useState } from 'react'
import { Accessibility, BarChart3, Bus, CalendarClock, RefreshCw, Users } from 'lucide-react'
import { api } from '../api'
import { jod } from '../format'
import { useStore } from '../store'
import { useT } from '../useT'
import type { FleetInsights } from '../types'
import { Button, Card, Chip, ErrorBox, Intro } from '../components/ui'

const ZONE: Record<string, string> = { irbid_east: 'Irbid East', irbid_nuzha: 'Irbid Nuzha', sweileh: 'Sweileh' }

/** Single-hue horizontal bars with direct labels; values exactly as served. */
function Bars({ data, label, fmt = (k: string) => k }: { data: Record<string, number>; label: string; fmt?: (k: string) => string }) {
  const t = useT()
  const rows = Object.entries(data)
  const max = Math.max(1, ...rows.map(([, v]) => v))
  if (!rows.length) return <p className="text-sm text-plum/60">{t('No data for this day.')}</p>
  return (
    <ul className="space-y-2" aria-label={label}>
      {rows.map(([k, v]) => (
        <li key={k} className="grid grid-cols-[5.5rem_1fr] items-center gap-2" title={`${fmt(k)}: ${v}`}>
          <span className="truncate text-xs font-bold text-plum/70">{fmt(k)}</span>
          <span className="relative h-6 rounded-md bg-white">
            <span className="absolute inset-y-0 start-0 rounded-e-md bg-magenta" style={{ width: `${(v / max) * 100}%` }} />
            {v / max > 0.8
              ? <span className="absolute inset-y-0 end-0 grid place-items-center px-1.5 text-xs font-black tabular-nums text-white">{v}</span>
              : <span className="absolute inset-y-0 grid place-items-center px-1.5 text-xs font-black tabular-nums text-plum"
                  style={{ insetInlineStart: `${(v / max) * 100}%` }}>{v}</span>}
          </span>
        </li>
      ))}
    </ul>
  )
}

/** Renders ONLY what the backend computed from the simulation fixtures. No placeholder numbers. */
export default function Insights() {
  const t = useT()
  const { sessionId } = useStore()
  const [data, setData] = useState<FleetInsights | null | undefined>(undefined)
  const [error, setError] = useState<unknown>()

  const load = useCallback(async () => {
    setError(undefined)
    try { setData(await api.insights(sessionId)) } catch (e) { setError(e); setData(null) }
  }, [sessionId])
  useEffect(() => { void load() }, [load])

  const p = data?.prediction

  return (
    <div className="space-y-4">
      <Intro title={t('Fleet Insights')} text={t('Computed by the backend from the simulation fixtures. Fictional riders, not real users.')} />
      <ErrorBox error={error} onRetry={load} />
      {data === undefined && <div className="h-32 animate-pulse rounded-3xl bg-plum-2" aria-label={t('Loading…')} />}
      {data === null && !error && (
        <Card className="space-y-2 text-plum">
          <h2 className="flex items-center gap-2 text-lg font-black"><BarChart3 className="size-5 text-magenta" aria-hidden /> {t('No numbers yet')}</h2>
          <p className="text-sm">{t('Insights appear once the live engine is connected. We never show made-up statistics here.')}</p>
        </Card>
      )}
      {data && (
        <>
          <div className="grid grid-cols-3 gap-2 text-plum">
            <Card className="p-3!"><Accessibility className="size-5 text-magenta" aria-hidden /><p className="mt-1 text-2xl font-black tabular-nums">{data.wav_available}/{data.wav_total}</p><p className="text-[11px] font-bold text-plum/60">{t('Ramp vehicles free')}</p></Card>
            <Card className="p-3!"><Accessibility className="size-5 text-magenta" aria-hidden /><p className="mt-1 text-2xl font-black tabular-nums">{data.accessible_requests}</p><p className="text-[11px] font-bold text-plum/60">{t('Wheelchair requests')}</p></Card>
            <Card className="p-3!"><Users className="size-5 text-magenta" aria-hidden /><p className="mt-1 text-2xl font-black tabular-nums">{data.opted_in_riders}</p><p className="text-[11px] font-bold text-plum/60">{t('Riders opted in to share')}</p></Card>
          </div>
          <Card className="space-y-3 text-plum">
            <h2 className="font-extrabold">{t('Requests by class hour')}</h2>
            <Bars data={data.requests_by_hour} label={t('Requests by class hour')} />
          </Card>
          <Card className="space-y-3 text-plum">
            <h2 className="font-extrabold">{t('Requests by zone')}</h2>
            <Bars data={data.requests_by_zone} label={t('Requests by zone')} fmt={(k) => t(ZONE[k] ?? k)} />
          </Card>
          <Card className="space-y-3 text-plum">
            <h2 className="flex items-center gap-2 font-extrabold"><Bus className="size-5 text-magenta" aria-hidden /> {t('Shuttle seats left')}</h2>
            <Bars data={data.shuttle_seats} label={t('Shuttle seats left')} />
          </Card>
          {p && (
            <Card className="space-y-2 text-plum">
              <h2 className="flex items-center gap-2 font-extrabold"><CalendarClock className="size-5 text-magenta" aria-hidden /> {t('Tomorrow')}</h2>
              {p.suggest_booking
                ? <p className="text-sm">{t('Your timetable has a {c} class on {d}. We can suggest booking it — nothing is booked automatically.', { c: String(p.first_class ?? ''), d: t(String(p.day ?? '')) })}</p>
                : <p className="text-sm">{t('No class tomorrow in your saved timetable.')}</p>}
              <Chip tone="soft">{t('Rule: timetable frequency · no auto-booking')}</Chip>
            </Card>
          )}
          <Card className="space-y-1 text-plum">
            <h2 className="font-extrabold">{t('B2B semester pass example')}</h2>
            <p className="text-sm">{t('{n} trips · university pays {u} · student pays {s}', {
              n: data.b2b_semester_pass_example.trips ?? 0,
              u: jod(data.b2b_semester_pass_example.institution_fils ?? 0),
              s: jod(data.b2b_semester_pass_example.student_fils ?? 0),
            })}</p>
          </Card>
          <Button variant="outline-lime" onClick={load}><RefreshCw className="size-4" aria-hidden /> {t('Refresh')}</Button>
        </>
      )}
    </div>
  )
}

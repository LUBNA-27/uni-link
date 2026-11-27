import { useCallback, useEffect, useState } from 'react'
import { BarChart3, RefreshCw } from 'lucide-react'
import { api } from '../api'
import { fmtFils, jod } from '../format'
import { useStore } from '../store'
import { useT } from '../useT'
import type { InsightMetric, InsightsResponse } from '../types'
import { Button, Card, ErrorBox, Intro } from '../components/ui'

/** Renders ONLY what the backend computed. No placeholder numbers are ever shown. */
export default function Insights() {
  const t = useT()
  const { sessionId, lang } = useStore()
  const [data, setData] = useState<InsightsResponse | null | undefined>(undefined)
  const [error, setError] = useState<unknown>()

  const load = useCallback(async () => {
    setError(undefined)
    try { setData(await api.insights(sessionId)) } catch (e) { setError(e); setData(null) }
  }, [sessionId])
  useEffect(() => { void load() }, [load])

  const show = (m: InsightMetric) => {
    if (m.unit === 'fils' && typeof m.value === 'number') return <>{jod(m.value)} <span className="text-xs font-bold text-plum/60">({fmtFils(m.value)})</span></>
    if (typeof m.value === 'boolean') return m.value ? t('Yes') : t('No')
    return <>{typeof m.value === 'number' ? m.value.toLocaleString('en-US') : m.value}{m.unit && m.unit !== 'fils' ? ` ${m.unit}` : ''}</>
  }

  return (
    <div className="space-y-4">
      <Intro title={t('Fleet Insights')} text={t('Numbers the engine computed from this simulated session.')} />
      <ErrorBox error={error} onRetry={load} />
      {data === undefined && <div className="h-32 animate-pulse rounded-3xl bg-plum-2" aria-label={t('Loading…')} />}
      {data === null && !error && (
        <Card className="space-y-2 text-plum">
          <h2 className="flex items-center gap-2 text-lg font-black"><BarChart3 className="size-5 text-magenta" aria-hidden /> {t('No numbers yet')}</h2>
          <p className="text-sm">{t('Insights appear once the live engine is connected. We never show made-up statistics here.')}</p>
        </Card>
      )}
      {data && (
        <Card className="space-y-3 text-plum">
          <p className="text-xs text-plum/60">{t('Basis: {b}', { b: data.basis })} · {new Date(data.generated_at).toLocaleString(lang === 'ar' ? 'ar-JO' : 'en-GB')} · {t('Simulation data')}</p>
          <dl className="grid grid-cols-2 gap-3">
            {data.metrics.map((m) => (
              <div key={m.id} className="rounded-2xl bg-white p-3">
                <dt className="text-xs font-bold uppercase text-plum/60">{t(m.label)}</dt>
                <dd className="mt-1 text-xl font-black tabular-nums">{show(m)}</dd>
                {(m.n !== undefined || m.note) && <p className="mt-1 text-[11px] text-plum/60">{m.n !== undefined ? t('n = {n}', { n: m.n }) : ''} {m.note ?? ''}</p>}
              </div>
            ))}
          </dl>
          <Button variant="outline-lime" onClick={load}><RefreshCw className="size-4" aria-hidden /> {t('Refresh')}</Button>
        </Card>
      )}
    </div>
  )
}

import { useEffect } from 'react'
import { Accessibility, ArrowRight, Car, RefreshCw } from 'lucide-react'
import { jod } from '../format'
import { useStore } from '../store'
import { useT } from '../useT'
import type { TripView } from '../types'
import { Button, Card, Chip, Intro } from '../components/ui'

const LABEL: Record<TripView['status'], string> = {
  confirmed: 'BOOKED', awaiting_consent: 'AWAITING CONSENT', dispatched: 'ON THE WAY', canceled: 'CANCELED', completed: 'COMPLETED',
}

/** Trips in this simulated session, newest first, as the server reports them. */
export default function History() {
  const t = useT()
  const { sim, refreshSim, go, timetableConfirmed } = useStore()
  useEffect(() => { void refreshSim() }, [refreshSim])
  const trips = [...(sim?.trips ?? [])].reverse()

  return (
    <div className="space-y-4">
      <Intro title={t('Your trips')} text={t('Every booking in this simulated session.')} />
      <div className="flex items-center gap-2">
        {sim && <Chip tone="soft"><span className="text-white">{t('Sim clock {t}', { t: sim.sim_time })}</span></Chip>}
        <button onClick={refreshSim} className="ms-auto inline-flex min-h-10 items-center gap-1 text-xs font-bold text-white/70"><RefreshCw className="size-4" aria-hidden /> {t('Refresh')}</button>
      </div>
      {!trips.length && (
        <Card className="space-y-3 text-plum">
          <p className="font-bold">{t('No trips yet.')}</p>
          <Button onClick={() => go(timetableConfirmed ? 'trip' : 'schedule')}>{t('Plan a ride')}</Button>
        </Card>
      )}
      <ul className="space-y-3">
        {trips.map((x) => {
          const live = x.status !== 'canceled' && x.status !== 'completed'
          const wav = x.plan.vehicle?.wheelchair_accessible
          return (
            <li key={x.trip_id}>
              <button disabled={!live} onClick={() => go('booked')}
                className={`flex w-full items-center gap-3 rounded-3xl p-4 text-start shadow-lg ${live ? 'bg-lavender text-plum' : 'bg-plum-2 text-white/80'}`}>
                <span className={`grid size-12 shrink-0 place-items-center rounded-2xl ${live ? 'bg-magenta text-white' : 'bg-white/10'}`}>
                  {wav ? <Accessibility className="size-6" aria-hidden /> : <Car className="size-6" aria-hidden />}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex flex-wrap items-center gap-1.5">
                    <span className="font-black">{x.trip_id}</span>
                    <Chip tone={live ? 'lime' : 'soft'} className={live ? '' : 'text-white'}>{t(LABEL[x.status])}</Chip>
                  </span>
                  <span className="mt-0.5 block text-xs font-semibold opacity-70">
                    {t('Class {c} · arrive {a} · leave {l}', { c: x.class_start, a: x.plan.arrival, l: x.plan.leave_home })}
                  </span>
                  {x.plan.vehicle && <span className="block text-xs opacity-70">{t(x.plan.vehicle.label)}</span>}
                </span>
                <span className="text-end">
                  <b className="block tabular-nums">{jod(x.amount_paid_fils)}</b>
                  {live && <ArrowRight className="ms-auto mt-1 size-4 rtl:rotate-180" aria-hidden />}
                </span>
              </button>
            </li>
          )
        })}
      </ul>
    </div>
  )
}

import type { ReactNode } from 'react'
import { Accessibility, Check, GraduationCap, MapPin, ShieldAlert } from 'lucide-react'
import { currency } from '../i18n'
import { fmtFils, fmtJod, jod } from '../format'
import { useT } from '../useT'
import type { PlanOption } from '../types'
import { useStore } from '../store'
import { Chip } from './ui'

/** Vertical route strip: pickups (closest → farthest) then campus. Pure rendering. */
export function RouteStrip({ option }: { option: PlanOption }) {
  const t = useT()
  const stops = option.pickups ?? option.pickup_order.map((tok, i) => ({
    rider_token: tok, landmark: i === 0 ? t('Your pickup') : t('Companion pickup {n}', { n: i }), time: '', is_you: i === 0,
  }))
  return (
    <ol className="relative ms-1 space-y-3" aria-label={t('Pickup order')}>
      <span className="absolute start-[11px] top-3 bottom-8 w-0.5 bg-plum/20" aria-hidden />
      {stops.map((s, i) => (
        <li key={s.rider_token} className="relative flex items-center gap-3">
          <span className={`z-10 grid size-6 shrink-0 place-items-center rounded-full text-[11px] font-black ${s.is_you ? 'bg-magenta text-white' : 'bg-plum text-white'}`}>
            {i + 1}
          </span>
          <span className="min-w-0 flex-1 truncate text-sm font-semibold text-plum">{t(s.landmark)}</span>
          {s.time && <span className="font-black tabular-nums text-plum">{s.time}</span>}
        </li>
      ))}
      <li className="relative flex items-center gap-3">
        <span className="z-10 grid size-6 shrink-0 place-items-center rounded-full bg-lime text-plum"><GraduationCap className="size-3.5" aria-hidden /></span>
        <span className="flex-1 text-sm font-bold text-plum">{t('Campus drop-off')}</span>
        <span className="font-black tabular-nums text-plum">{option.arrival}</span>
      </li>
    </ol>
  )
}

/** Leg-weighted fair split, exactly as returned by the server. Display only. */
export function SplitList({ option }: { option: PlanOption }) {
  const { riderToken } = useStore()
  const t = useT()
  const shares = option.fare.shares
  if (!shares || shares.length < 2) return null
  const label = (tok: string) => {
    if (tok === riderToken) return t('You')
    const p = option.pickups?.find((x) => x.rider_token === tok)
    return p ? t(p.landmark).split(' · ')[0] : tok
  }
  return (
    <section aria-label={t('Fair split · each pays for the distance they ride')} className="rounded-xl bg-white p-3">
      <p className="mb-1.5 text-xs font-bold uppercase text-plum/60">{t('Fair split · each pays for the distance they ride')}</p>
      <ul className="space-y-1 text-sm">
        {shares.map((r) => (
          <li key={r.rider_token} className={`flex justify-between ${r.rider_token === riderToken ? 'font-black text-magenta' : ''}`}>
            <span>{label(r.rider_token)}</span><span className="tabular-nums">{jod(r.share_fils)} <span className="text-xs font-normal text-plum/60">({fmtFils(r.share_fils)})</span></span>
          </li>
        ))}
      </ul>
      <p className="mt-1.5 text-xs text-plum/60">{t('Vehicle total {x} = what the shares add up to (server-computed).', { x: jod(option.fare.vehicle_total_fils) })}</p>
    </section>
  )
}

export function BoardingPass({
  option, heading = 'BOARDING PASS', badge, children, showReference = true,
}: { option: PlanOption; heading?: string; badge?: ReactNode; children?: ReactNode; showReference?: boolean }) {
  const t = useT()
  const f = option.fare
  const wav = option.vehicle?.wheelchair_accessible
  return (
    <article className="ticket overflow-hidden rounded-3xl bg-lavender text-plum shadow-xl" aria-label={t('BOARDING PASS')}>
      <header className="flex items-center justify-between bg-magenta px-5 py-2.5 text-white">
        <span className="text-xs font-black tracking-[0.18em]">UNILINK · {t(heading)}</span>
        {badge}
      </header>

      <div className="p-5">
        <div className="mb-1 flex items-center gap-2 text-xs font-bold uppercase tracking-wide text-plum/60">
          <MapPin className="size-3.5" aria-hidden /> {t('Door-to-Door → Campus')}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-bold uppercase text-plum/60">{t('Arrive')}</p>
            <p className="text-5xl font-black leading-none tabular-nums">{option.arrival}</p>
            {option.deadline && <p className="mt-1 text-xs text-plum/60">{t('deadline {t}', { t: option.deadline })}</p>}
          </div>
          <div>
            <p className="text-xs font-bold uppercase text-plum/60">{t('Your share')}</p>
            <p className="text-4xl font-black leading-none tabular-nums text-magenta">
              <span className="me-1 text-base font-extrabold">{currency()}</span>{fmtJod(f.your_share_fils)}
            </p>
            <p className="mt-0.5 text-xs font-bold text-plum/70">{fmtFils(f.your_share_fils)}</p>
            <p className="mt-1 text-xs text-plum/60">{t('of {x} vehicle total', { x: jod(f.vehicle_total_fils) })}</p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          <Chip tone="soft">{t('Leave home {t}', { t: option.leave_home })}</Chip>
          {option.vehicle && (
            <Chip tone={wav ? 'lime' : 'soft'}>
              {wav && <Accessibility className="size-3.5" aria-hidden />} {t(option.vehicle.label)}
            </Chip>
          )}
          {option.flags?.map((fl) => <Chip key={fl} tone="amber">{t(fl) === fl ? fl.replaceAll('_', ' ') : t(fl)}</Chip>)}
        </div>
      </div>

      <div className="ticket-cut" aria-hidden />

      <div className="p-5">
        <RouteStrip option={option} />

        {option.accessible_dropoff && (
          <div className={`mt-4 rounded-xl p-3 text-sm ${option.accessible_dropoff.verified ? 'bg-lime/40' : 'bg-amber-100'}`}>
            <p className="flex items-center gap-1.5 font-bold">
              {option.accessible_dropoff.verified ? <Accessibility className="size-4" aria-hidden /> : <ShieldAlert className="size-4" aria-hidden />}
              {t('Accessible drop-off: {l}', { l: t(option.accessible_dropoff.label) })}
            </p>
            <p className="mt-0.5 text-xs text-plum/70">
              {option.accessible_dropoff.verified ? t('Source: {s} · verified', { s: t(option.accessible_dropoff.source) }) : t('Source: {s} · NOT verified — confirm with campus', { s: t(option.accessible_dropoff.source) })}
            </p>
          </div>
        )}

        <div className="mt-4"><SplitList option={option} /></div>

        {showReference && f.hypothetical_reference_fils !== undefined && (
          <p className="mt-4 rounded-xl bg-white p-3 text-xs text-plum/70">
            {t('Hypothetical reference: the same route with 4 riders would cost {x} — an illustration, not an available quote.', { x: jod(f.hypothetical_reference_fils) })}
            {f.delta_vs_reference_fils !== undefined && <> {t('Your difference: {x}.', { x: jod(f.delta_vs_reference_fils, true) })}</>}
          </p>
        )}

        {option.hard_filters_passed && option.hard_filters_passed.length > 0 && (
          <ul className="mt-3 flex flex-wrap gap-1.5" aria-label={t('Safety and accessibility filters never relaxed')}>
            {option.hard_filters_passed.map((h) => (
              <li key={h}><Chip tone="soft"><Check className="size-3" aria-hidden /> {t(h)}</Chip></li>
            ))}
          </ul>
        )}
        {children && <div className="mt-4 space-y-2">{children}</div>}
      </div>
    </article>
  )
}

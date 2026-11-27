import { Ban, CheckCircle2, Clock, Hourglass } from 'lucide-react'
import { currency } from '../i18n'
import { fmtFils, fmtJod, jod } from '../format'
import { useT } from '../useT'
import type { Proposal } from '../types'
import { RouteStrip } from './BoardingPass'
import { Button, Chip } from './ui'

const TITLES: Record<Proposal['kind'], string> = {
  smart_rescue: 'SMART RESCUE',
  class_shift: 'CLASS SHIFT',
  emergency: 'EMERGENCY RIDE',
}

/**
 * Renders any backend proposal (rescue / class shift / emergency). Nothing is applied
 * until the rider taps Approve — and for group changes the other riders must consent too.
 */
export function ProposalView({
  p, myToken, onApprove, onDecline, busy, approveLabel,
}: {
  p: Proposal; myToken: string; onApprove: () => void; onDecline: () => void; busy?: boolean; approveLabel?: string
}) {
  const t = useT()
  const me = p.consents.find((c) => c.rider_token === myToken)
  const iAccepted = me?.state === 'accepted'
  const waiting = iAccepted && p.consents.some((c) => c.state === 'pending')
  const f = p.plan.fare

  return (
    <article className="overflow-hidden rounded-3xl bg-lavender text-plum shadow-lg" aria-label={t('{x} proposal', { x: t(TITLES[p.kind]) })}>
      <header className="flex items-center justify-between bg-lime px-5 py-2">
        <span className="text-xs font-black tracking-[0.16em]">{t(TITLES[p.kind])}</span>
        <Chip tone="plum">{t('Needs your OK')}</Chip>
      </header>
      <div className="space-y-4 p-5">
        <p className="font-semibold">{p.message}</p>

        {p.kind === 'class_shift' && p.next_class && (
          <div className="rounded-2xl bg-white p-3 text-sm">
            <p className="text-xs font-bold uppercase text-plum/60">{t('Next class from your saved timetable')}</p>
            <p className="text-lg font-black">{p.next_class.start} <span className="font-semibold text-plum/70">{p.next_class.course}</span></p>
            <p className="text-xs text-plum/60">{t('No new photo scan was needed.')}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-bold uppercase text-plum/60">{t('Arrive')}</p>
            <p className="text-4xl font-black leading-none tabular-nums">{p.plan.arrival}</p>
            <p className="mt-1 text-xs text-plum/60">{t('leave {t}', { t: p.plan.leave_home })}</p>
          </div>
          <div>
            <p className="text-xs font-bold uppercase text-plum/60">{t('Your share')}</p>
            <p className="text-3xl font-black leading-none tabular-nums text-magenta"><span className="me-1 text-sm">{currency()}</span>{fmtJod(f.your_share_fils)}</p>
            <p className="text-xs font-bold text-plum/70">{fmtFils(f.your_share_fils)}</p>
            {p.previous_your_share_fils !== undefined && (
              <p className="mt-1 text-xs text-plum/70">{t('was {x}', { x: jod(p.previous_your_share_fils) })} · <b>{jod(p.delta_fils, true)}</b> <span className="text-xs">({fmtFils(p.delta_fils, true)})</span></p>
            )}
          </div>
        </div>

        {p.kind === 'class_shift' && p.refund_fils !== undefined && p.new_charge_fils !== undefined && (
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 rounded-2xl bg-white p-3 text-sm">
            <dt>{t('Old booking refunded')}</dt><dd className="font-black tabular-nums">{jod(p.refund_fils)}</dd>
            <dt>{t('New booking charged')}</dt><dd className="font-black tabular-nums">{jod(p.new_charge_fils)}</dd>
            <dt className="font-bold">{t('Net change')}</dt><dd className="font-black tabular-nums text-magenta">{jod(p.delta_fils, true)}</dd>
          </dl>
        )}
        {p.kind === 'emergency' && (
          <p className="rounded-2xl bg-white p-3 text-sm">{t('Emergency pricing applies to you only. Riders already on this trip keep the same fare and their arrival time.')}</p>
        )}

        <RouteStrip option={p.plan} />

        {p.consents.length > 1 && (
          <section aria-label={t('Group consent')} className="rounded-2xl bg-white p-3">
            <p className="mb-2 text-xs font-bold uppercase text-plum/60">{t('Everyone affected must agree (simulated riders)')}</p>
            <ul className="space-y-1.5 text-sm">
              {p.consents.map((c) => (
                <li key={c.rider_token} className="flex items-center justify-between">
                  <span>{c.label}</span>
                  <Chip tone={c.state === 'accepted' ? 'lime' : c.state === 'declined' ? 'amber' : 'soft'}>
                    {c.state === 'accepted' ? <CheckCircle2 className="size-3.5" aria-hidden /> : <Clock className="size-3.5" aria-hidden />}
                    {t(c.state)}
                  </Chip>
                </li>
              ))}
            </ul>
          </section>
        )}

        {p.alternatives && p.alternatives.length > 0 && (
          <section aria-label={t('Options above your fare cap')}>
            <p className="mb-2 text-xs font-bold uppercase text-plum/60">{t('Other options (not bookable under your fare cap)')}</p>
            <ul className="space-y-1.5">
              {p.alternatives.map((a) => (
                <li key={a.label} className="flex items-center justify-between rounded-xl border border-dashed border-plum/30 p-2.5 text-sm text-plum/70">
                  <span className="inline-flex items-center gap-1.5"><Ban className="size-4" aria-hidden />{t(a.label)}</span>
                  <span className="font-bold tabular-nums">{jod(a.your_share_fils)} <span className="text-xs">({jod(a.delta_fils, true)})</span></span>
                </li>
              ))}
            </ul>
            <p className="mt-1.5 text-xs text-plum/60">{t('Raising your cap is a separate change you must make yourself.')}</p>
          </section>
        )}

        {waiting ? (
          <p className="flex items-center gap-2 rounded-2xl bg-white p-4 text-sm font-bold" role="status">
            <Hourglass className="size-5 text-magenta" aria-hidden /> {t('You approved. Waiting for the other riders — nobody is charged until all agree.')}
          </p>
        ) : (
          <div className="space-y-2">
            <Button busy={busy} onClick={onApprove}>
              {approveLabel ?? `${t('Approve')}${p.delta_fils > 0 ? ` ${jod(p.delta_fils, true)}` : ''}`}
            </Button>
            <Button variant="danger" disabled={busy} onClick={onDecline}>
              {p.kind === 'class_shift' ? t('Keep my current booking') : p.kind === 'emergency' ? t('No thanks') : t('Decline')}
            </Button>
          </div>
        )}
      </div>
    </article>
  )
}

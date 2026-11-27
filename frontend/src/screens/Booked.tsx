import { useState } from 'react'
import { CalendarX2, RefreshCw, Wallet } from 'lucide-react'
import { api, ApiError } from '../api'
import { fmtFils, jod, newKey } from '../format'
import { useT } from '../useT'
import { useStore } from '../store'
import type { Proposal, ShiftResponse, TripView } from '../types'
import { BoardingPass } from '../components/BoardingPass'
import { ProposalView } from '../components/ProposalView'
import { Button, Card, Chip, ErrorBox, inputCls, Intro, MockChip, Sheet } from '../components/ui'

export default function Booked() {
  const t = useT()
  const { sessionId, riderToken, sim, refreshSim, go } = useStore()
  const [busyId, setBusyId] = useState<string>()
  const [error, setError] = useState<unknown>()
  const [notice, setNotice] = useState<string>()
  const [shiftOpen, setShiftOpen] = useState(false)
  const [shiftTime, setShiftTime] = useState('')
  const [shift, setShift] = useState<ShiftResponse | null>(null)

  const trip: TripView | undefined = sim?.trips.find((x) => x.status !== 'canceled')
  const shiftId = shift?.proposal?.proposal_id
  const proposals = (sim?.pending_proposals ?? []).filter((p) => p.proposal_id !== shiftId)

  const settle = async (fn: () => Promise<unknown>, id: string) => {
    setBusyId(id); setError(undefined); setNotice(undefined)
    try { await fn() } catch (e) {
      if (e instanceof ApiError && e.status === 409) setNotice(t('This proposal changed while you were deciding. We refreshed it — please review it again.'))
      else setError(e)
    } finally { setBusyId(undefined); await refreshSim() }
  }

  const respond = (p: Proposal, decision: 'accept' | 'decline') =>
    settle(async () => {
      const r = await api.confirm({
        session_id: sessionId, rider_token: riderToken, plan_id: p.plan.plan_id, plan_revision: p.plan_revision,
        accepted_fare_fils: p.plan.fare.your_share_fils, idempotency_key: newKey(), decision,
        replaces_trip_id: p.kind === 'class_shift' ? trip?.trip_id : undefined,
      })
      if (p.kind === 'class_shift') { setShift(null); setShiftOpen(false) }
      if (r.status === 'confirmed') setNotice(p.kind === 'class_shift' ? t('Class shifted. Your old seat was released.') : t('Updated. Your wallet and trip are up to date.'))
      if (r.status === 'awaiting_consent') setNotice(t('Thanks — waiting for the other riders to agree. You are not charged until everyone does.'))
    }, p.proposal_id)

  const openShift = () => { setShift(null); setError(undefined); setShiftTime(sim?.sim_time ?? ''); setShiftOpen(true) }
  const askShift = () =>
    settle(async () => {
      if (!trip) return
      setShift(await api.shiftClass({ session_id: sessionId, trip_id: trip.trip_id, rider_token: riderToken, request_time: shiftTime }))
    }, 'shift')
  const cancelOnly = () =>
    settle(async () => {
      await api.confirm({ session_id: sessionId, rider_token: riderToken, plan_id: trip?.plan.plan_id ?? '', plan_revision: sim?.revision ?? 0,
        accepted_fare_fils: 0, idempotency_key: newKey(), decision: 'cancel_trip' })
      setShift(null); setShiftOpen(false); setNotice(t('Trip canceled.'))
    }, 'cancel')

  return (
    <div className="space-y-4">
      <Intro title={trip ? t('You are booked') : t('No active trip')} text={trip ? t('Show this pass to your driver. Simulation only — no real car is dispatched.') : t('Book a ride to see your boarding pass here.')} />
      <div className="flex flex-wrap items-center gap-2">
        <MockChip endpoint="state" />
        {sim && <Chip tone="soft"><span className="text-white">{t('Sim clock {t}', { t: sim.sim_time })}</span></Chip>}
        <button onClick={refreshSim} aria-label={t('Refresh')} className="ms-auto inline-flex items-center gap-1 text-xs font-bold text-white/70"><RefreshCw className="size-4" aria-hidden /> {t('Refresh')}</button>
      </div>

      {notice && <p role="status" className="rounded-2xl bg-lime p-3 text-sm font-bold text-plum">{notice}</p>}
      <ErrorBox error={error} />

      {proposals.map((p) => (
        <ProposalView key={p.proposal_id} p={p} myToken={riderToken} busy={busyId === p.proposal_id}
          onApprove={() => respond(p, 'accept')} onDecline={() => respond(p, 'decline')} />
      ))}

      {trip ? (
        <BoardingPass option={trip.plan} heading={`${t('TRIP')} ${trip.trip_id}`} showReference={false}
          badge={<Chip tone="lime">{trip.status === 'awaiting_consent' ? t('AWAITING CONSENT') : t('BOOKED')}</Chip>}>
          <p className="text-sm text-plum/70">{t('Paid so far:')} <b>{jod(trip.amount_paid_fils)}</b> <span className="text-xs">({fmtFils(trip.amount_paid_fils)})</span></p>
          <Button variant="outline-lime" onClick={openShift}><CalendarX2 className="size-5" aria-hidden /> {t('My first class was canceled')}</Button>
        </BoardingPass>
      ) : (
        <Button onClick={() => go('trip')}>{t('Plan a ride')}</Button>
      )}

      {sim && (
        <Card className="space-y-2 text-plum">
          <h2 className="flex items-center gap-2 font-extrabold"><Wallet className="size-5" aria-hidden /> {t('Jeeny Wallet (simulated)')}</h2>
          <p className="text-3xl font-black tabular-nums">{jod(sim.wallet.balance_fils)}</p>
          <p className="-mt-1 text-xs font-bold text-plum/70">{fmtFils(sim.wallet.balance_fils)}</p>
          {sim.wallet.ledger.length > 0 && (
            <ul className="divide-y divide-plum/10 text-sm" aria-label={t('Wallet ledger')}>
              {sim.wallet.ledger.map((l, i) => (
                <li key={i} className="flex justify-between py-1.5">
                  <span>{l.at} · {t(l.note)}</span>
                  <b className={l.kind === 'debit' ? 'text-magenta' : ''}><span dir="ltr">{l.kind === 'debit' ? '−' : '+'}{jod(l.amount_fils)}</span> <span className="text-xs font-normal">({fmtFils(l.amount_fils)})</span></b>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <Sheet open={shiftOpen} onClose={() => setShiftOpen(false)} title={t('My first class was canceled')}>
        <div className="space-y-4 text-plum">
          {!shift && (
            <>
              <p className="text-sm">{t('We will use your saved timetable to find your next class. Nothing changes until you approve.')}</p>
              <label className="block text-sm font-bold">{t('It is now (simulated)')}
                <input type="time" className={`${inputCls} mt-1`} value={shiftTime} onChange={(e) => setShiftTime(e.target.value)} />
              </label>
              <ErrorBox error={error} />
              <Button busy={busyId === 'shift'} disabled={!shiftTime} onClick={askShift}>{t('Find my next class')}</Button>
            </>
          )}
          {shift?.status === 'shift_proposed' && shift.proposal && (
            <ProposalView p={(sim?.pending_proposals.find((x) => x.proposal_id === shift.proposal!.proposal_id)) ?? shift.proposal}
              myToken={riderToken} busy={busyId === shift.proposal.proposal_id}
              approveLabel={t('Switch to my {x} class', { x: shift.proposal.next_class?.start ?? t('next') })}
              onApprove={() => respond(shift.proposal!, 'accept')} onDecline={() => respond(shift.proposal!, 'decline')} />
          )}
          {shift?.status === 'no_next_class' && (
            <div className="space-y-3">
              <p className="font-bold">{shift.message}</p>
              {shift.cancel_only && (
                <p className="rounded-xl bg-white p-3 text-sm">{t('Cancel this trip and get')} <b>{jod(shift.cancel_only.refund_fils)}</b> {t('back.')} {shift.cancel_only.terms}</p>
              )}
              <ErrorBox error={error} />
              {shift.cancel_only && <Button variant="primary" busy={busyId === 'cancel'} onClick={cancelOnly}>{t('Cancel this trip')}</Button>}
              <Button variant="danger" onClick={() => setShiftOpen(false)}>{t('Keep my trip')}</Button>
            </div>
          )}
        </div>
      </Sheet>
    </div>
  )
}

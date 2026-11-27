import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import { fmtFils, jod, newKey } from '../format'
import { useT } from '../useT'
import { useStore } from '../store'
import type { ConfirmResponse, PlanOption } from '../types'
import { BoardingPass } from './BoardingPass'
import { Button, ErrorBox, MockChip, Sheet } from './ui'

/**
 * Initial booking confirmation. Sends session, rider_token, plan_id, plan_revision,
 * accepted_fare_fils and an idempotency_key that survives retries. The frontend never
 * deducts money — it shows whatever the server returns.
 */
export function ConfirmSheet({
  option, planRevision, onClose, onDone, onStale,
}: {
  option: PlanOption | null; planRevision: number; onClose: () => void
  onDone: (r: ConfirmResponse) => void; onStale: () => void
}) {
  const t = useT()
  const { sessionId, riderToken, sim } = useStore()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  const [ack, setAck] = useState(false)
  // one idempotency key per opened plan; retries reuse it, a different plan gets a new one
  const [idemKey, setIdemKey] = useState(newKey)
  const planId = option?.plan_id
  useEffect(() => { setIdemKey(newKey()); setAck(false); setError(undefined) }, [planId])

  const submit = async () => {
    if (!option) return
    setBusy(true); setError(undefined)
    try {
      const r = await api.confirm({
        session_id: sessionId, rider_token: riderToken, plan_id: option.plan_id, plan_revision: planRevision,
        accepted_fare_fils: option.fare.your_share_fils, idempotency_key: idemKey,
      })
      onDone(r)
    } catch (e) {
      setError(e)
    } finally { setBusy(false) }
  }
  const stale = error instanceof ApiError && error.status === 409

  return (
    <Sheet open={!!option} onClose={onClose} title={t('Confirm your ride')}>
      {option && (
        <div className="space-y-4 text-plum">
          <MockChip endpoint="confirm" />
          <BoardingPass option={option} heading="REVIEW" showReference={false} />
          <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 rounded-2xl bg-white p-4 text-sm">
            <dt>{t('You will pay')}</dt><dd className="font-black tabular-nums text-magenta">{jod(option.fare.your_share_fils)} <span className="text-xs font-bold text-plum/70">({fmtFils(option.fare.your_share_fils)})</span></dd>
            {sim && (<><dt>{t('Jeeny Wallet balance now')}</dt><dd className="font-bold tabular-nums">{jod(sim.wallet.balance_fils)}</dd></>)}
          </dl>
          <label className="flex items-start gap-3 text-sm">
            <input type="checkbox" className="mt-0.5 size-6 accent-magenta" checked={ack} onChange={(e) => setAck(e.target.checked)} />
            <span>{t('I understand this is a simulated booking. No real payment is made and no real car is dispatched.')}</span>
          </label>
          {stale ? (
            <div className="space-y-2">
              <ErrorBox error={error} />
              <Button onClick={onStale}>{t('See the updated plan')}</Button>
            </div>
          ) : (
            <>
              <ErrorBox error={error} onRetry={submit} />
              <Button busy={busy} disabled={!ack} onClick={submit}>{t('Confirm · pay {x} from Wallet', { x: jod(option.fare.your_share_fils) })}</Button>
            </>
          )}
        </div>
      )}
    </Sheet>
  )
}

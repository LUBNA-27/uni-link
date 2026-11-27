import { useCallback, useEffect, useState } from 'react'
import { ArrowDownLeft, ArrowUpRight, BarChart3, GraduationCap, RefreshCw, Wallet as WalletIcon } from 'lucide-react'
import { api } from '../api'
import { fmtFils, jod } from '../format'
import { useStore } from '../store'
import { useT } from '../useT'
import type { FleetInsights } from '../types'
import { Button, Card, Chip, ErrorBox } from '../components/ui'

/** Simulated Jeeny Wallet: balance and ledger exactly as the server returns them. */
export default function Wallet() {
  const t = useT()
  const { sim, refreshSim, sessionId, go } = useStore()
  const [ins, setIns] = useState<FleetInsights | null>()
  const [error, setError] = useState<unknown>()
  const load = useCallback(async () => {
    setError(undefined)
    try { await refreshSim(); setIns(await api.insights(sessionId)) } catch (e) { setError(e) }
  }, [refreshSim, sessionId])
  useEffect(() => { void load() }, [load])
  const pass = ins?.b2b_semester_pass_example

  return (
    <div className="space-y-4">
      <section className="relative overflow-hidden rounded-3xl bg-magenta p-5 text-white shadow-xl">
        <span className="pointer-events-none absolute -end-10 -top-10 size-40 rounded-full border-[14px] border-white/10" aria-hidden />
        <p className="flex items-center gap-2 text-xs font-black tracking-[0.16em]"><WalletIcon className="size-4" aria-hidden /> {t('JEENY WALLET · SIMULATED')}</p>
        {sim ? (
          <>
            <p className="mt-3 text-4xl font-black tabular-nums">{jod(sim.wallet.balance_fils)}</p>
            <p className="text-sm font-bold text-white/80">{fmtFils(sim.wallet.balance_fils)}</p>
          </>
        ) : <div className="mt-3 h-12 w-40 animate-pulse rounded-xl bg-white/20" aria-label={t('Loading…')} />}
        <button onClick={load} className="mt-3 inline-flex min-h-10 items-center gap-1 text-sm font-extrabold underline"><RefreshCw className="size-4" aria-hidden /> {t('Refresh')}</button>
      </section>
      <ErrorBox error={error} onRetry={load} />

      <Card className="space-y-2 text-plum">
        <h2 className="font-extrabold">{t('Ledger')}</h2>
        {!sim?.wallet.ledger.length && <p className="text-sm text-plum/70">{t('No payments yet. Booking a ride debits the wallet here.')}</p>}
        <ul className="divide-y divide-plum/10" aria-label={t('Wallet ledger')}>
          {sim?.wallet.ledger.map((l, i) => (
            <li key={i} className="flex items-center gap-3 py-2.5">
              <span className={`grid size-9 place-items-center rounded-xl ${l.kind === 'debit' ? 'bg-magenta/10 text-magenta' : 'bg-lime text-plum'}`}>
                {l.kind === 'debit' ? <ArrowUpRight className="size-4" aria-hidden /> : <ArrowDownLeft className="size-4" aria-hidden />}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-bold">{t(l.note)}</span>
                <span className="block text-xs text-plum/60">{l.at} · {l.kind === 'debit' ? t('Debit') : t('Refund')}</span>
              </span>
              <span className="text-end">
                <b className={`block tabular-nums ${l.kind === 'debit' ? 'text-magenta' : ''}`} dir="ltr">{l.kind === 'debit' ? '−' : '+'}{jod(l.amount_fils)}</b>
                <span className="text-[11px] text-plum/60">{fmtFils(l.amount_fils)}</span>
              </span>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="space-y-3 text-plum">
        <h2 className="flex items-center gap-2 font-extrabold"><GraduationCap className="size-5 text-magenta" aria-hidden /> {t('UniPass · semester pass')}</h2>
        {pass ? (
          <>
            <p className="text-sm text-plum/70">{t('Example the engine computed for a university-subsidised pass, based on your current fare share.')}</p>
            <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 rounded-2xl bg-white p-4 text-sm">
              <dt>{t('Trips in the semester')}</dt><dd className="font-bold tabular-nums">{pass.trips}</dd>
              <dt>{t('Fare share per trip')}</dt><dd className="font-bold tabular-nums">{jod(pass.share_fils)}</dd>
              <dt>{t('Semester total')}</dt><dd className="font-bold tabular-nums">{jod(pass.gross_fils)}</dd>
              <dt>{t('University pays')}</dt><dd className="font-bold tabular-nums">{jod(pass.institution_fils)}</dd>
              <dt className="font-black">{t('Student pays')}</dt><dd className="font-black tabular-nums text-magenta">{jod(pass.student_fils)}</dd>
            </dl>
            <Chip tone="soft">{t('Simulation data · not an offer')}</Chip>
          </>
        ) : ins === null ? (
          <p className="text-sm">{t('Not connected to the live engine in this build.')}</p>
        ) : <div className="h-24 animate-pulse rounded-2xl bg-white" aria-label={t('Loading…')} />}
      </Card>

      <Button variant="outline-lime" onClick={() => go('insights')}><BarChart3 className="size-5" aria-hidden /> {t('Fleet Insights')}</Button>
    </div>
  )
}

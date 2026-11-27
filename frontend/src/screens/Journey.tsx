import { useEffect, useState } from 'react'
import { Accessibility, ArrowLeft, Loader2, RefreshCw, ShieldCheck } from 'lucide-react'
import { api } from '../api'
import { useStore } from '../store'
import { useT } from '../useT'
import type { PlanOption } from '../types'
import { BoardingPass } from '../components/BoardingPass'
import { BestDealCard } from '../components/BestDealCard'
import { ConfirmSheet } from '../components/ConfirmSheet'
import { Button, Card, Chip, ErrorBox, Intro, MockChip } from '../components/ui'

export default function Journey() {
  const t = useT()
  const { request, plan, sim, setSim, refreshSim, go, planning, planError, runPlan } = useStore()
  const [chosen, setChosen] = useState<PlanOption | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  // staged reveal: strict query "fails" → one thing is relaxed → cards appear
  const [revealed, setRevealed] = useState<string | null>(null)
  const planKey = plan ? `${plan.plan_revision}:${plan.options.map((o) => o.plan_id).join(',')}` : null

  useEffect(() => { void refreshSim() }, [refreshSim])
  useEffect(() => {
    if (plan?.status !== 'best_deal_proposed' || !planKey) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    const id = window.setTimeout(() => setRevealed(planKey), reduce ? 0 : 1100)
    return () => window.clearTimeout(id)
  }, [plan?.status, planKey])

  const replan = async () => {
    if (!request) return
    setChosen(null); setError(undefined); setBusy(true)
    try { await runPlan(request) } finally { setBusy(false) }
  }

  if (planning) {
    return (
      <div className="space-y-4" role="status" aria-live="polite">
        <Intro title={t('Looking for your ride…')} text={t('Checking safety and accessibility rules first, then the best route.')} />
        <div className="space-y-3" aria-hidden>
          {[0, 1].map((i) => <div key={i} className="h-40 animate-pulse rounded-3xl bg-plum-2" />)}
        </div>
        <p className="flex items-center justify-center gap-2 text-sm text-white/70"><Loader2 className="size-4 animate-spin" aria-hidden /> {t('This usually takes a moment.')}</p>
      </div>
    )
  }

  if (planError && !plan) {
    return (
      <div className="space-y-4">
        <Intro title={t("We couldn't get your plan")} text={t('Nothing was booked or charged.')} />
        <Card className="space-y-3 text-plum"><ErrorBox error={planError} onRetry={replan} /></Card>
        <Button variant="outline-lime" onClick={() => go('trip')}>{t('Edit request')}</Button>
      </div>
    )
  }

  if (!request || !plan) {
    return (
      <div className="space-y-4">
        <Intro title={t('No journey yet')} text={t('Tell us about your trip first.')} />
        <Button onClick={() => go('trip')}>{t('Plan a ride')}</Button>
      </div>
    )
  }

  // server says the world moved on since this plan was made
  const stale = sim !== undefined && sim.revision > plan.plan_revision && sim.trips.length === 0
  const showCards = plan.status !== 'best_deal_proposed' || revealed === planKey

  return (
    <div className="space-y-4">
      <button onClick={() => go('trip')} className="inline-flex items-center gap-1 text-sm font-bold text-white/80"><ArrowLeft className="size-4 rtl:rotate-180" aria-hidden /> {t('Edit request')}</button>
      <div className="flex flex-wrap gap-2">
        <MockChip endpoint="plan" />
        <Chip tone="lime">{request.gender_pool === 'female_only' ? t('Female-only') : t('Male-only')}</Chip>
        <Chip tone="soft"><span className="text-white">{t('Class {c} · {n} companions · cap {x} JOD', { c: request.class_start, n: request.desired_companions, x: (request.fare_cap_fils / 1000).toFixed(2) })}</span></Chip>
      </div>

      {stale && (
        <div role="status" className="flex items-center justify-between gap-3 rounded-2xl bg-amber-100 p-3 text-sm text-plum">
          <span>{t('This plan is out of date.')}</span>
          <button onClick={replan} className="inline-flex items-center gap-1 font-extrabold text-magenta"><RefreshCw className="size-4" aria-hidden /> {t('Refresh')}</button>
        </div>
      )}
      <ErrorBox error={error ?? planError} onRetry={replan} />

      {plan.status === 'exact_match' && plan.options[0] && (
        <div className="reveal space-y-4">
          <Intro title={t('Exact match found')} text={t('Everything you asked for, as requested.')} />
          <BoardingPass option={plan.options[0]} badge={<Chip tone="lime">{t('EXACT MATCH')}</Chip>}>
            <Button busy={busy} onClick={() => setChosen(plan.options[0])}>{t('Review & confirm')}</Button>
          </BoardingPass>
        </div>
      )}

      {plan.status === 'best_deal_proposed' && (
        <>
          <Intro title={t('No exact match — here is your Best Deal')} text={t('Your safety and accessibility rules stay. We relax exactly one flexible thing at a time.')} />
          {!showCards && (
            <div role="status" aria-live="polite" className="space-y-2 rounded-2xl bg-plum-2 p-4 text-sm">
              <p className="font-bold">✕ {t('Exact match: none found')}</p>
              <p className="flex items-center gap-2 font-bold text-lime"><Loader2 className="size-4 animate-spin" aria-hidden /> {t('Relaxing one flexible thing, keeping every safety rule…')}</p>
            </div>
          )}
          {showCards && (
            <div className="reveal space-y-4">
              {plan.options.map((o, i) => <BestDealCard key={o.plan_id} option={o} rank={i} busy={busy} onChoose={setChosen} />)}
              <p className="text-center text-xs text-white/60">{t('Nothing is booked or charged until you confirm.')}</p>
            </div>
          )}
        </>
      )}

      {(plan.status === 'no_feasible_route' || plan.status === 'no_accessible_route') && (
        <Card className="reveal space-y-3 text-plum">
          <h2 className="flex items-center gap-2 text-xl font-black">
            {plan.status === 'no_accessible_route' && <Accessibility className="size-6 text-magenta" aria-hidden />}
            {plan.status === 'no_accessible_route' ? t('No accessible vehicle right now') : t('No route fits yet')}
          </h2>
          <p>{plan.reason?.message ?? t('We could not find a route that meets every rule you set.')}</p>
          {plan.reason?.code && <p className="text-xs text-plum/60">{t('code: {c}', { c: plan.reason.code })}</p>}
          <p className="flex items-start gap-2 rounded-xl bg-white p-3 text-sm"><ShieldCheck className="mt-0.5 size-5 shrink-0 text-magenta" aria-hidden />
            <span>{t('We never relax gender pool, wheelchair or ramp requirements, or your fare cap — even to find you a ride.')}</span></p>
          {plan.assistance && <p className="rounded-xl bg-lime/50 p-3 text-sm font-semibold">{plan.assistance.message} <span className="text-xs font-normal">({t('Simulated operator assistance')})</span></p>}
          <Button onClick={() => go('trip')}>{t('Change my request')}</Button>
        </Card>
      )}

      <ConfirmSheet
        option={chosen}
        planRevision={plan.plan_revision}
        onClose={() => setChosen(null)}
        onStale={replan}
        onDone={async (r) => {
          setChosen(null)
          if (r.status === 'confirmed' || r.status === 'awaiting_consent') {
            try { setSim(await api.simState(r.session_id)) } catch { /* booked screen will retry */ }
            go('booked')
          }
        }}
      />
    </div>
  )
}

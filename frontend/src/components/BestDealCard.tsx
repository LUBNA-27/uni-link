import { Sparkles } from 'lucide-react'
import { currency } from '../i18n'
import { fmtFils, fmtJod, jod } from '../format'
import { useT } from '../useT'
import type { PlanOption } from '../types'
import { Button, Chip } from './ui'
import { RouteStrip, SplitList } from './BoardingPass'

/** Best Deal option: exactly ONE relaxed soft constraint, utility, deltas. Rendering only. */
export function BestDealCard({
  option, rank, onChoose, busy,
}: { option: PlanOption; rank: number; onChoose: (o: PlanOption) => void; busy?: boolean }) {
  const t = useT()
  const f = option.fare
  const top = rank === 0
  return (
    <article className={`overflow-hidden rounded-3xl bg-lavender text-plum shadow-lg ${top ? 'ring-4 ring-lime' : ''}`} aria-label={t('Best Deal option {n}', { n: rank + 1 })}>
      <header className="flex items-center justify-between bg-lime px-5 py-2 text-plum">
        <span className="inline-flex items-center gap-1.5 text-xs font-black tracking-[0.16em]">
          <Sparkles className="size-4" aria-hidden /> {t('BEST DEAL {n}', { n: rank + 1 })}{top ? ` · ${t('TOP PICK')}` : ''}
        </span>
        {option.utility !== undefined && <span className="text-xs font-bold">{t('score {s}', { s: option.utility.toFixed(2) })}</span>}
      </header>

      <div className="p-5">
        <p className="text-xs font-bold uppercase text-plum/60">{t('What we relaxed (one thing only)')}</p>
        <p className="text-xl font-black">{option.relaxed ? t(option.relaxed) : t('Nothing — exact match')}</p>

        <div className="mt-4 grid grid-cols-2 gap-4">
          <div>
            <p className="text-xs font-bold uppercase text-plum/60">{t('Arrive')}</p>
            <p className="text-4xl font-black leading-none tabular-nums">{option.arrival}</p>
            <p className="mt-1 text-xs text-plum/60">{t('leave home {t}', { t: option.leave_home })}</p>
          </div>
          <div>
            <p className="text-xs font-bold uppercase text-plum/60">{t('Your share')}</p>
            <p className="text-3xl font-black leading-none tabular-nums text-magenta">
              <span className="me-1 text-sm font-extrabold">{currency()}</span>{fmtJod(f.your_share_fils)}
            </p>
            <p className="text-xs font-bold text-plum/70">{fmtFils(f.your_share_fils)}</p>
            {f.delta_vs_reference_fils !== undefined && (
              <p className="mt-1 text-xs text-plum/60">
                {f.delta_vs_reference_fils === 0 ? t('Matches the reference') : t('{x} vs reference', { x: jod(f.delta_vs_reference_fils, true) })}
              </p>
            )}
          </div>
        </div>

        <div className="mt-4"><RouteStrip option={option} /></div>

        {f.hypothetical_reference_fils !== undefined && (
          <p className="mt-3 text-xs text-plum/60">
            {t('Reference {x} = hypothetical same-route 4-rider price, not an available quote.', { x: jod(f.hypothetical_reference_fils) })}
          </p>
        )}
        {f.shares && f.shares.length > 1 && (
          <details className="mt-3 rounded-xl bg-white p-2 text-sm">
            <summary className="min-h-10 cursor-pointer py-2 font-bold">{t('See the fair split')}</summary>
            <SplitList option={option} />
          </details>
        )}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {option.hard_filters_passed?.map((h) => <Chip key={h} tone="soft">✓ {t(h)}</Chip>)}
        </div>

        <Button className="mt-4" variant={top ? 'primary' : 'outline-lime'} busy={busy} onClick={() => onChoose(option)}>
          {t('Choose this')} · {jod(f.your_share_fils)}
        </Button>
      </div>
    </article>
  )
}

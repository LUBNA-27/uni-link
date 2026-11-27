import { useEffect, type ButtonHTMLAttributes, type ReactNode } from 'react'
import { AlertTriangle, Loader2, X } from 'lucide-react'
import { ApiError, isMock, type Endpoint } from '../api'
import { useT } from '../useT'

type Variant = 'primary' | 'lime' | 'outline-lime' | 'ghost' | 'danger'
const V: Record<Variant, string> = {
  primary: 'bg-magenta text-white hover:bg-magenta-dark disabled:bg-plum/30',
  lime: 'bg-lime text-plum hover:brightness-95 disabled:opacity-50',
  'outline-lime': 'border-2 border-lime text-plum bg-white hover:bg-lime/20 disabled:opacity-50',
  ghost: 'text-plum/80 hover:bg-plum/10 disabled:opacity-50',
  danger: 'border-2 border-plum/30 text-plum hover:bg-plum/10 disabled:opacity-50',
}
export function Button({ variant = 'primary', busy, className = '', children, ...p }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; busy?: boolean }) {
  return (
    <button
      {...p}
      disabled={p.disabled || busy}
      className={`min-h-12 w-full rounded-2xl px-5 py-3 text-base font-extrabold transition-colors disabled:cursor-not-allowed ${V[variant]} ${className}`}
    >
      <span className="inline-flex items-center justify-center gap-2">
        {busy && <Loader2 className="size-5 animate-spin" aria-hidden />}
        {children}
      </span>
    </button>
  )
}

export function Chip({ children, tone = 'plum', className = '' }:
  { children: ReactNode; tone?: 'plum' | 'lime' | 'magenta' | 'amber' | 'soft'; className?: string }) {
  const t = {
    plum: 'bg-plum text-white',
    lime: 'bg-lime text-plum',
    magenta: 'bg-magenta text-white',
    amber: 'bg-amber-200 text-plum',
    soft: 'bg-plum/10 text-plum',
  }[tone]
  return <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-bold ${t} ${className}`}>{children}</span>
}

/** Visible provenance: every call served from mock.ts is labeled. */
export function MockChip({ endpoint }: { endpoint: Endpoint }) {
  const t = useT()
  if (!isMock(endpoint)) return <Chip tone="soft">{t('Simulation data · live engine')}</Chip>
  return <Chip tone="amber" className="border border-plum/30">{t('MOCK data · not the engine')}</Chip>
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-3xl bg-lavender p-5 shadow-lg ${className}`}>{children}</div>
}

export function ErrorBox({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const t = useT()
  if (!error) return null
  const e = error instanceof ApiError ? error : new ApiError('UNKNOWN', error instanceof Error ? error.message : String(error))
  return (
    <div role="alert" className="flex gap-3 rounded-2xl border-2 border-magenta bg-white p-4 text-plum">
      <AlertTriangle className="mt-0.5 size-5 shrink-0 text-magenta" aria-hidden />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-bold">{e.message}</p>
        <p className="mt-0.5 text-xs text-plum/60">{t('code: {c}', { c: e.code })}</p>
        {onRetry && <button onClick={onRetry} className="mt-2 text-sm font-extrabold text-magenta underline">{t('Try again')}</button>}
      </div>
    </div>
  )
}

export function Field({ label, hint, children }: { label: string; hint?: ReactNode; children: ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-sm font-bold text-plum">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-plum/60">{hint}</span>}
    </label>
  )
}
export const inputCls =
  'min-h-12 w-full rounded-xl border-2 border-plum/15 bg-white px-3 py-2 text-base text-plum placeholder:text-plum/40 focus:border-magenta'

/** Bottom sheet (modal) for confirmations and proposals. */
export function Sheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: ReactNode }) {
  const t = useT()
  useEffect(() => {
    if (!open) return
    const k = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', k)
    return () => document.removeEventListener('keydown', k)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/60" role="dialog" aria-modal="true" aria-label={title} onClick={onClose}>
      <div className="max-h-[92dvh] w-full max-w-md overflow-y-auto rounded-t-3xl bg-lavender p-5 pb-8" onClick={(e) => e.stopPropagation()}>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-extrabold text-plum">{title}</h2>
          <button onClick={onClose} aria-label={t('Close')} className="grid size-10 place-items-center rounded-full hover:bg-plum/10"><X className="size-5 text-plum" /></button>
        </div>
        {children}
      </div>
    </div>
  )
}

export function Intro({ title, text }: { title: string; text: string }) {
  return (
    <div className="text-white">
      <h1 className="text-3xl font-black leading-tight">{title}</h1>
      <p className="mt-1 text-white/75">{text}</p>
    </div>
  )
}

import { currency, getLang } from './i18n'
import type { Fils, HHMM, Weekday } from './types'

/** Integer fils → "1.86" / "1.575" (three decimals only when needed). Display only. */
export function fmtJod(fils: Fils, signed = false): string {
  const neg = fils < 0
  const abs = Math.abs(fils)
  const whole = Math.trunc(abs / 1000)
  const frac = String(abs % 1000).padStart(3, '0')
  const f = frac.endsWith('0') ? frac.slice(0, 2) : frac
  const sign = neg ? '−' : signed && fils > 0 ? '+' : ''
  return `${sign}${whole}.${f}`
}
/** "JOD 1.86" / "1.86 د.أ" — numerals stay LTR-isolated so signs and decimals never reorder in Arabic. */
export const jod = (fils: Fils, signed = false) =>
  getLang() === 'ar' ? `\u2066${fmtJod(fils, signed)}\u2069 ${currency()}` : `JOD ${fmtJod(fils, signed)}`
/** Exact integer fils, always visible next to JOD: "1,860 fils". */
export const fmtFils = (fils: Fils, signed = false) =>
  `${signed ? (fils > 0 ? '+' : fils < 0 ? '−' : '') : fils < 0 ? '−' : ''}${Math.abs(fils).toLocaleString('en-US')} ${getLang() === 'ar' ? 'فلس' : 'fils'}`

const DAYS: Weekday[] = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu']
/** YYYY-MM-DD → weekday name (Sun–Thu working week) or null for Fri/Sat. */
export function weekdayOf(date: string): Weekday | null {
  const d = new Date(`${date}T00:00:00Z`)
  if (Number.isNaN(d.getTime())) return null
  const i = d.getUTCDay() // 0 = Sun
  return i <= 4 ? DAYS[i] : null
}

export const WEEKDAYS = DAYS
export const isHHMM = (s: string): s is HHMM => /^([01]\d|2[0-3]):[0-5]\d$/.test(s)

export function newKey(): string {
  try {
    return crypto.randomUUID()
  } catch {
    return `k-${Date.now()}-${Math.random().toString(16).slice(2)}`
  }
}

import { useEffect, useRef, useState } from 'react'
import { Mic, MicOff, Package, Send } from 'lucide-react'
import { api } from '../api'
import { fmtFils, jod } from '../format'
import { useStore, type View } from '../store'
import { useT } from '../useT'
import type { ParcelQuoteResponse, TripView, VoiceIntent, VoiceIntentResponse } from '../types'
import { Button, Chip, ErrorBox, Field, inputCls, Sheet } from './ui'

/* ───────────── voice ───────────── */
interface Recognition {
  lang: string; interimResults: boolean; continuous: boolean
  onresult: ((e: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> }) => void) | null
  onend: (() => void) | null; onerror: (() => void) | null
  start: () => void; stop: () => void
}
type RecognitionCtor = new () => Recognition
const getRecognition = (): RecognitionCtor | undefined => {
  const w = window as unknown as { SpeechRecognition?: RecognitionCtor; webkitSpeechRecognition?: RecognitionCtor }
  return w.SpeechRecognition ?? w.webkitSpeechRecognition
}

/** Where each recognised intent takes the rider. Voice never books or pays: it only navigates. */
const NEXT: Partial<Record<VoiceIntent, { view: View; label: string }>> = {
  plan_trip: { view: 'trip', label: 'Plan a ride' },
  read_route: { view: 'booked', label: 'Open my pass' },
  accept_best_deal: { view: 'journey', label: 'Review the Best Deal' },
  approve_rescue: { view: 'booked', label: 'Review the change' },
  decline: { view: 'booked', label: 'Review the change' },
  shift_to_next_class: { view: 'booked', label: 'Open my pass' },
  emergency_ride: { view: 'trip', label: 'Find me a ride now' },
}

export function VoiceSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const t = useT()
  const { sessionId, lang, go, timetableConfirmed } = useStore()
  const Ctor = getRecognition()
  const rec = useRef<Recognition | null>(null)
  const [listening, setListening] = useState(false)
  const [text, setText] = useState('')
  const [res, setRes] = useState<VoiceIntentResponse | null>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()

  useEffect(() => { if (!open) { rec.current?.stop(); setListening(false); setRes(undefined); setError(undefined); setText('') } }, [open])

  const listen = () => {
    if (!Ctor) return
    if (listening) { rec.current?.stop(); return }
    const r = new Ctor()
    r.lang = lang === 'ar' ? 'ar-JO' : 'en-US'
    r.interimResults = true; r.continuous = false
    r.onresult = (e) => setText(Array.from(e.results).map((x) => x[0].transcript).join(' '))
    r.onend = () => setListening(false)
    r.onerror = () => setListening(false)
    rec.current = r; setRes(undefined); setText(''); setListening(true)
    try { r.start() } catch { setListening(false) }
  }

  const send = async () => {
    if (!text.trim()) return
    setBusy(true); setError(undefined)
    try { setRes(await api.voiceIntent(sessionId, text.trim(), lang === 'ar' ? 'ar-JO' : 'en')) }
    catch (e) { setError(e) } finally { setBusy(false) }
  }

  const next = res ? NEXT[res.intent] : undefined
  const target: View | undefined = next && (next.view === 'trip' && !timetableConfirmed ? 'schedule' : next.view)

  return (
    <Sheet open={open} onClose={onClose} title={t('Voice assistant')}>
      <div className="space-y-4 text-plum">
        <p className="text-sm">{t('Say or type what you need, e.g. “book a ride to campus” or “بدي روح عالجامعة”.')}</p>
        {Ctor ? (
          <button onClick={listen} aria-pressed={listening}
            className={`mx-auto grid size-24 place-items-center rounded-full text-white shadow-lg ${listening ? 'mic-pulse bg-magenta' : 'bg-plum'}`}
            aria-label={listening ? t('Stop listening') : t('Start listening')}>
            {listening ? <MicOff className="size-9" aria-hidden /> : <Mic className="size-9" aria-hidden />}
          </button>
        ) : (
          <p className="rounded-xl bg-white p-3 text-xs">{t('Speech input is not available in this browser. Type your request instead.')}</p>
        )}
        <div className="flex gap-2">
          <input className={inputCls} value={text} onChange={(e) => setText(e.target.value)} aria-label={t('Your request')}
            placeholder={t('Your request')} dir="auto" onKeyDown={(e) => e.key === 'Enter' && void send()} />
          <button onClick={send} disabled={busy || !text.trim()} aria-label={t('Send')}
            className="grid size-12 shrink-0 place-items-center rounded-xl bg-magenta text-white disabled:bg-plum/30"><Send className="size-5" aria-hidden /></button>
        </div>
        <ErrorBox error={error} onRetry={send} />
        {res === null && <p className="rounded-xl bg-white p-3 text-sm">{t('Voice is not connected to the live engine in this build.')}</p>}
        {res && (
          <div className="space-y-3 rounded-2xl bg-white p-4" role="status">
            <p className="text-base font-bold" dir="auto">{lang === 'ar' ? res.readback_ar : res.readback_en}</p>
            <div className="flex flex-wrap gap-1.5">
              <Chip tone="soft">{t('Confidence {c}%', { c: Math.round(res.confidence * 100) })}</Chip>
              <Chip tone="lime">{t('Nothing was booked or paid')}</Chip>
            </div>
            {next && target && <Button onClick={() => { go(target); onClose() }}>{t(next.label)}</Button>}
          </div>
        )}
      </div>
    </Sheet>
  )
}

/* ───────────── Ride & Box ───────────── */
export function BoxSheet({ open, onClose, trip }: { open: boolean; onClose: () => void; trip?: TripView }) {
  const t = useT()
  const { sessionId, go, timetableConfirmed } = useStore()
  const [size, setSize] = useState<'small' | 'medium'>('small')
  const [kg, setKg] = useState(1)
  const [valueJod, setValueJod] = useState(10)
  const [q, setQ] = useState<ParcelQuoteResponse | null>()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<unknown>()
  useEffect(() => { if (!open) { setQ(undefined); setError(undefined) } }, [open])

  const quote = async () => {
    if (!trip) return
    setBusy(true); setError(undefined)
    try {
      setQ(await api.parcelQuote({
        session_id: sessionId, trip_id: trip.trip_id, size,
        weight_g: Math.round(kg * 1000), declared_value_fils: Math.round(valueJod * 1000),
      }))
    } catch (e) { setError(e) } finally { setBusy(false) }
  }

  return (
    <Sheet open={open} onClose={onClose} title={t('Ride & Box')}>
      <div className="space-y-4 text-plum">
        <p className="flex items-start gap-2 text-sm"><Package className="mt-0.5 size-5 shrink-0 text-magenta" aria-hidden />
          {t('A sealed parcel (up to 5 kg) travels along a trip you already booked. Never offered on wheelchair trips.')}</p>
        {!trip ? (
          <>
            <p className="rounded-xl bg-white p-3 text-sm font-semibold">{t('Book a ride first — Box rides along your booked trip.')}</p>
            <Button onClick={() => { go(timetableConfirmed ? 'trip' : 'schedule'); onClose() }}>{t('Plan a ride')}</Button>
          </>
        ) : (
          <>
            <div role="radiogroup" aria-label={t('Parcel size')} className="grid grid-cols-2 gap-2">
              {(['small', 'medium'] as const).map((s) => (
                <button key={s} role="radio" aria-checked={size === s} onClick={() => setSize(s)}
                  className={`min-h-12 rounded-xl border-2 font-bold ${size === s ? 'border-magenta bg-white' : 'border-transparent bg-white/60 text-plum/70'}`}>
                  {s === 'small' ? t('Small') : t('Medium')}
                </button>
              ))}
            </div>
            <Field label={t('Weight (kg)')}><input type="number" min={0.1} max={5} step={0.1} inputMode="decimal" className={inputCls} value={kg} onChange={(e) => setKg(Number(e.target.value))} /></Field>
            <Field label={t('Declared value (JOD)')} hint={t('Used for the insurance part of the quote.')}>
              <input type="number" min={0} step={1} inputMode="decimal" className={inputCls} value={valueJod} onChange={(e) => setValueJod(Number(e.target.value))} />
            </Field>
            <ErrorBox error={error} onRetry={quote} />
            <Button busy={busy} disabled={kg <= 0} onClick={quote}>{t('Get a quote')}</Button>
            {q === null && <p className="rounded-xl bg-white p-3 text-sm">{t('Ride & Box is not connected to the live engine in this build.')}</p>}
            {q && (
              <dl className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-1 rounded-2xl bg-white p-4 text-sm">
                <dt>{t('Parcel fee')}</dt><dd className="font-bold tabular-nums">{jod(q.parcel_fee_fils)}</dd>
                <dt>{t('Insurance')}</dt><dd className="font-bold tabular-nums">{jod(q.insurance_fils)}</dd>
                <dt className="font-black">{t('Total')}</dt><dd className="font-black tabular-nums text-magenta">{jod(q.total_fils)} <span className="text-xs font-bold text-plum/60">({fmtFils(q.total_fils)})</span></dd>
                <dt className="text-plum/60">{t('Driver gets')}</dt><dd className="tabular-nums text-plum/60">{jod(q.driver_share_fils)}</dd>
                <dt className="text-plum/60">{t('Jeeny gets')}</dt><dd className="tabular-nums text-plum/60">{jod(q.jeeny_share_fils)}</dd>
                <dt className="col-span-2 mt-2 text-xs text-plum/60">{t('Corridor {k} km · quote only, no shipment is created (simulation).', { k: q.corridor_km })}</dt>
              </dl>
            )}
          </>
        )}
      </div>
    </Sheet>
  )
}

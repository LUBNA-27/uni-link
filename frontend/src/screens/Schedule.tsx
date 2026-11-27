import { useRef, useState } from 'react'
import { Camera, Check, PencilLine, Plus, Trash2 } from 'lucide-react'
import { api } from '../api'
import { isHHMM, WEEKDAYS } from '../format'
import { useStore } from '../store'
import { useT } from '../useT'
import type { ClassItem, EditableField, TimetableResponse, UncertainField } from '../types'
import { Button, Card, Chip, ErrorBox, inputCls, Intro, MockChip } from '../components/ui'

let seq = 0
const blank = (): ClassItem => ({ id: `new-${Date.now()}-${seq++}`, course: '', weekday: 'Sun', start: '08:30' })

type Mode = 'start' | 'edit' | 'review'

export default function Schedule() {
  const t = useT()
  const { sessionId, classes, uncertain, timetableConfirmed, setTimetable, go } = useStore()
  const [mode, setMode] = useState<Mode>(timetableConfirmed ? 'review' : 'start')
  const [rows, setRows] = useState<ClassItem[]>(classes)
  const [flags, setFlags] = useState<UncertainField[]>(uncertain)
  const [source, setSource] = useState<TimetableResponse['inference_source']>()
  const [busy, setBusy] = useState<'parse' | 'manual' | 'confirm' | null>(null)
  const [error, setError] = useState<unknown>()
  const fileRef = useRef<HTMLInputElement>(null)

  const run = async (kind: typeof busy, fn: () => Promise<void>) => {
    setBusy(kind); setError(undefined)
    try { await fn() } catch (e) { setError(e) } finally { setBusy(null) }
  }
  const apply = (r: TimetableResponse, next: Mode) => {
    setRows(r.classes); setFlags(r.uncertain_fields); setSource(r.inference_source); setMode(next)
  }

  const onFile = (f?: File) => f && run('parse', async () => apply(await api.parseTimetable(f, sessionId), 'review'))
  const check = () => run('manual', async () => apply(await api.manualTimetable(sessionId, rows), 'review'))
  const confirm = () => run('confirm', async () => {
    await api.confirmTimetable(sessionId, rows)
    setTimetable(rows, [], true)
    go('trip')
  })

  const isFlagged = (id: string, field: EditableField) => flags.some((u) => u.class_id === id && u.field === field)
  const ack = (id: string, field: EditableField) => setFlags((f) => f.filter((u) => !(u.class_id === id && u.field === field)))
  const edit = (id: string, patch: Partial<ClassItem>, field: EditableField) => {
    setRows((rs) => rs.map((r) => (r.id === id ? { ...r, ...patch } : r)))
    ack(id, field)
  }
  const invalid = rows.length === 0 || rows.some((r) => !r.course.trim() || !isHHMM(r.start) || (r.end !== undefined && r.end !== '' && !isHHMM(r.end)))

  if (mode === 'start') {
    return (
      <div className="space-y-4">
        <Intro title={t('Your timetable, once.')} text={t('Upload a photo of your semester timetable. We read it, you check it, and every trip after that is a single tap.')} />
        <input ref={fileRef} type="file" accept="image/*" capture="environment" className="sr-only" aria-label={t('Timetable photo')}
          onChange={(e) => onFile(e.target.files?.[0])} />
        <Button busy={busy === 'parse'} onClick={() => fileRef.current?.click()}>
          <Camera className="size-5" aria-hidden /> {t('Upload timetable photo')}
        </Button>
        <Button variant="outline-lime" onClick={() => { setRows([blank()]); setFlags([]); setMode('edit') }}>
          <PencilLine className="size-5" aria-hidden /> {t('Enter classes manually')}
        </Button>
        <ErrorBox error={error} />
        <p className="text-center text-xs text-white/60">{t('Your photo is only used to read the classes; the API contract says it is not kept by default.')}</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <Intro
        title={mode === 'edit' ? t('Add your classes') : t('Check your timetable')}
        text={mode === 'edit' ? t('Add each weekly class. You will review them next.') : t('Fix anything we got wrong. Highlighted fields need a quick look.')}
      />
      <div className="flex flex-wrap gap-2">
        {source && <Chip tone="lime">{source === 'gemini_vision' ? t('Read by Gemini Vision') : source === 'manual' ? t('Entered manually') : t('Fixture timetable (demo)')}</Chip>}
        <MockChip endpoint={source === 'manual' ? 'manual' : 'parse'} />
      </div>

      {rows.map((r) => (
        <Card key={r.id} className="space-y-3">
          <div className="grid grid-cols-[1fr_auto] gap-2">
            <input className={`${inputCls} ${isFlagged(r.id, 'course') ? 'border-amber-400 bg-amber-50' : ''}`} placeholder={t('Course (e.g. CS 201)')}
              aria-label={t('Course')} value={r.course} onChange={(e) => edit(r.id, { course: e.target.value }, 'course')} />
            <button aria-label={t('Remove class')} className="grid size-12 place-items-center rounded-xl text-plum/60 hover:bg-plum/10"
              onClick={() => setRows((rs) => rs.filter((x) => x.id !== r.id))}><Trash2 className="size-5" /></button>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <select className={inputCls} aria-label={t('Day')} value={r.weekday} onChange={(e) => edit(r.id, { weekday: e.target.value as ClassItem['weekday'] }, 'weekday')}>
              {WEEKDAYS.map((d) => <option key={d} value={d}>{t(d)}</option>)}
            </select>
            <input type="time" className={`${inputCls} ${isFlagged(r.id, 'start') ? 'border-amber-400 bg-amber-50' : ''}`} aria-label={t('Start time')}
              value={r.start} onChange={(e) => edit(r.id, { start: e.target.value }, 'start')} />
            <input className={inputCls} placeholder={t('Room')} aria-label={t('Room')} value={r.room ?? ''} onChange={(e) => edit(r.id, { room: e.target.value }, 'room')} />
          </div>
          {flags.filter((u) => u.class_id === r.id).map((u) => (
            <div key={u.field} className="flex items-center justify-between gap-2 rounded-xl bg-amber-100 p-3 text-sm text-plum" role="status">
              <span>{t(u.reason)}</span>
              <button className="inline-flex shrink-0 items-center gap-1 rounded-lg bg-plum px-3 py-2 text-xs font-bold text-white" onClick={() => ack(u.class_id, u.field)}>
                <Check className="size-4" aria-hidden /> {t('Looks right')}
              </button>
            </div>
          ))}
        </Card>
      ))}

      <Button variant="outline-lime" onClick={() => setRows((rs) => [...rs, blank()])}><Plus className="size-5" aria-hidden /> {t('Add a class')}</Button>
      <ErrorBox error={error} />
      {mode === 'edit' ? (
        <Button busy={busy === 'manual'} disabled={invalid} onClick={check}>{t('Check my classes')}</Button>
      ) : (
        <Button busy={busy === 'confirm'} disabled={invalid || flags.length > 0} onClick={confirm}>
          {flags.length > 0 ? t('Check {n} highlighted field(s) first', { n: flags.length }) : t('Confirm timetable')}
        </Button>
      )}
      <button className="w-full text-center text-sm font-bold text-white/70 underline" onClick={() => { setMode('start'); setError(undefined) }}>{t('Start over')}</button>
    </div>
  )
}

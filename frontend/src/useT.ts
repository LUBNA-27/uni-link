import { useCallback } from 'react'
import { tr, type Vars } from './i18n'
import { useStore } from './store'

/** Translation hook: re-renders when the language changes (lang lives in the store). */
export function useT() {
  const { lang } = useStore()
  return useCallback((en: string, vars?: Vars) => tr(en, vars, lang), [lang])
}

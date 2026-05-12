import { i18n } from '@/plugins/i18n'

const translationKeyPattern = /^[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+)+$/

export function translate(key: string, params?: Record<string, unknown>): string {
  if (!translationKeyPattern.test(key)) return key
  return params ? i18n.global.t(key, params) : i18n.global.t(key)
}

/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { createI18n } from 'vue-i18n'
import en from '@/locales/en'
import zhCN from '@/locales/zh-CN'
import { DEFAULT_LOCALE, LOCALE_STORAGE_KEY, type SupportedLocale } from '@/i18n/locale'

export const messages = {
  en,
  'zh-CN': zhCN
} as const

function isSupportedLocale(value: string | null): value is SupportedLocale {
  return value === 'en' || value === 'zh-CN'
}

function detectBrowserLocale(): SupportedLocale {
  if (typeof navigator === 'undefined') return DEFAULT_LOCALE
  return navigator.language.toLowerCase().startsWith('zh') ? 'zh-CN' : 'en'
}

export function resolveInitialLocale(): SupportedLocale {
  if (typeof localStorage !== 'undefined') {
    const stored = localStorage.getItem(LOCALE_STORAGE_KEY)
    if (isSupportedLocale(stored)) return stored
  }
  return detectBrowserLocale()
}

export function applyDocumentLocale(locale: SupportedLocale) {
  if (typeof document !== 'undefined') {
    document.documentElement.lang = locale
  }
}

export const i18n = createI18n({
  legacy: false,
  locale: resolveInitialLocale(),
  fallbackLocale: 'en',
  messages
})

applyDocumentLocale(i18n.global.locale.value as SupportedLocale)

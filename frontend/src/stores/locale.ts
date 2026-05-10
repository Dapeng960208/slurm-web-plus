/*
 * Copyright (c) 2023-2026 Slurm Web Plus
 *
 * This file is part of Slurm Web Plus.
 *
 * SPDX-License-Identifier: MIT
 */

import { computed } from 'vue'
import { defineStore } from 'pinia'
import { i18n, applyDocumentLocale } from '@/plugins/i18n'
import { LOCALE_STORAGE_KEY, type SupportedLocale } from '@/i18n/locale'

function isSupportedLocale(value: string): value is SupportedLocale {
  return value === 'en' || value === 'zh-CN'
}

export const useLocaleStore = defineStore('locale', () => {
  const locale = computed<SupportedLocale>({
    get: () => i18n.global.locale.value as SupportedLocale,
    set: (value) => {
      i18n.global.locale.value = value
    }
  })

  function setLocale(value: SupportedLocale) {
    if (!isSupportedLocale(value)) return
    locale.value = value
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem(LOCALE_STORAGE_KEY, value)
    }
    applyDocumentLocale(value)
  }

  return {
    locale,
    setLocale
  }
})

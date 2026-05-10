import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useLocaleStore } from '@/stores/locale'
import { i18n } from '@/plugins/i18n'

describe('locale store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    i18n.global.locale.value = 'en'
    document.documentElement.lang = 'en'
  })

  test('persists selected locale and updates document lang', () => {
    const store = useLocaleStore()

    store.setLocale('zh-CN')

    expect(i18n.global.locale.value).toBe('zh-CN')
    expect(localStorage.getItem('locale')).toBe('zh-CN')
    expect(document.documentElement.lang).toBe('zh-CN')
  })

  test('supports switching to english', () => {
    const store = useLocaleStore()

    store.setLocale('en')

    expect(i18n.global.locale.value).toBe('en')
    expect(localStorage.getItem('locale')).toBe('en')
    expect(document.documentElement.lang).toBe('en')
  })
})

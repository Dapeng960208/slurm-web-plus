import { beforeEach, describe, expect, test } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useDashboardRuntimeStore } from '@/stores/runtime/dashboard'

describe('dashboard runtime store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  test('omits default partition and other default query values', () => {
    const store = useDashboardRuntimeStore()

    expect(store.query()).toStrictEqual({})

    store.partition = 'gpu'

    expect(store.query()).toStrictEqual({ partition: 'gpu' })
  })

  test('restores dashboard query state from route query', () => {
    const store = useDashboardRuntimeStore()

    store.restoreQuery({
      range: 'day',
      resources: 'memory',
      partition: 'debug'
    })

    expect(store.range).toBe('day')
    expect(store.chartResourcesType).toBe('memory')
    expect(store.partition).toBe('debug')
  })
})

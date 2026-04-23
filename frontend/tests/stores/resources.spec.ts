import { describe, test, beforeEach, expect } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { nextTick } from 'vue'
import { useResourcesRuntimeStore } from '@/stores/runtime/resources'

describe('stores/runtime/resources.ts', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
  })

  test('showNodeNames defaults to true when not set in localStorage', () => {
    const store = useResourcesRuntimeStore()
    expect(store.showNodeNames).toBe(true)
  })

  test('showRackDiagram defaults to false and is not persisted', async () => {
    const store = useResourcesRuntimeStore()
    expect(store.showRackDiagram).toBe(false)

    store.showRackDiagram = true
    await nextTick()
    expect(store.showRackDiagram).toBe(true)
    expect(localStorage.getItem('showRackDiagram')).toBeNull()
  })

  test('showNodeNames updates state and persists to localStorage', async () => {
    const store = useResourcesRuntimeStore()
    store.showNodeNames = false
    await nextTick()
    expect(store.showNodeNames).toBe(false)
    expect(localStorage.getItem('showNodeNames')).toBe('false')

    store.showNodeNames = true
    await nextTick()
    expect(store.showNodeNames).toBe(true)
    expect(localStorage.getItem('showNodeNames')).toBe('true')
  })
})

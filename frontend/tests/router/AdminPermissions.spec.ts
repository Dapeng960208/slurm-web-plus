import { afterEach, beforeEach, describe, expect, test, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

vi.mock('@/plugins/runtimeConfiguration', () => ({
  useRuntimeConfiguration: () => ({
    api_server: 'http://localhost',
    authentication: true,
    racksdb_rows_labels: false,
    racksdb_racks_labels: false,
    version: 'test'
  })
}))

describe('router admin permissions', () => {
  beforeEach(() => {
    vi.resetModules()
    setActivePinia(createPinia())
    window.history.replaceState({}, '', '/')
  })

  afterEach(() => {
    localStorage.clear()
  })

  test('allows admin subroutes when access comes from admin-manage super-admin action', async () => {
    const [{ default: router }, { useAuthStore }, { useRuntimeStore }] = await Promise.all([
      import('@/router'),
      import('@/stores/auth'),
      import('@/stores/runtime')
    ])
    const authStore = useAuthStore()
    const runtimeStore = useRuntimeStore()

    authStore.token = 'token'
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['ops-admin'],
          actions: ['admin-manage'],
          rules: []
        },
        capabilities: {
          ai: {
            enabled: true
          },
          access_control: true
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ] as never

    await router.push({ name: 'admin-cache', params: { cluster: 'foo' } })
    await router.isReady()

    expect(router.currentRoute.value.name).toBe('admin-cache')
    expect(router.currentRoute.value.fullPath).toBe('/foo/admin/cache')
  })
})

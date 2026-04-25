import { describe, test, beforeEach, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SettingsCacheView from '@/views/settings/SettingsCache.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { init_plugins } from '../../lib/common'
import type { RouterMock } from 'vue-router-mock'

describe('settings/SettingsCache.vue', () => {
  beforeEach(() => {
    void init_plugins()
  })

  async function primeAdminRoute(router: RouterMock) {
    await router.setParams({ cluster: 'foo' })
    router.currentRoute.value.name = 'admin-cache'
  }

  function renderView() {
    return mount(SettingsCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          SettingsHeader: true,
          AdminTabs: true,
          AdminHeader: true,
          SettingsCacheStatistics: {
            props: ['cluster'],
            template: '<div data-testid="cache-statistics">statistics {{ cluster.name }}</div>'
          },
          SettingsCacheMetrics: {
            props: ['cluster'],
            template: '<div data-testid="cache-metrics">metrics {{ cluster.name }}</div>'
          }
        }
      }
    })
  }

  test('renders cache statistics and metrics when cache and metrics are enabled', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]

    await primeAdminRoute(router)
    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="cache-statistics"]').text()).toContain('statistics foo')
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="cache-metrics"]').text()).toContain('metrics foo')
    expect(wrapper.text()).not.toContain('Live cache metrics are unavailable')
  })

  test('renders cache statistics without metrics when metrics are disabled', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: false,
        cache: true
      }
    ]

    await primeAdminRoute(router)
    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="cache-statistics"]').text()).toContain('statistics foo')
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('Live cache metrics are unavailable')
  })

  test('renders permission message without cache children when cache-view is denied', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]

    await primeAdminRoute(router)
    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.text()).toContain('No permission to get cache information on this cluster.')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(0)
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Live cache metrics are unavailable')
  })

  test('renders cache disabled message without cache children when cache is turned off', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: false
      }
    ]

    await primeAdminRoute(router)
    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.text()).toContain('Cache is disabled on this cluster.')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(0)
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Live cache metrics are unavailable')
  })
})

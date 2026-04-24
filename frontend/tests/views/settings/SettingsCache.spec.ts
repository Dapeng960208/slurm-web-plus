import { describe, test, beforeEach, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SettingsCacheView from '@/views/settings/SettingsCache.vue'
import { useRuntimeStore } from '@/stores/runtime'
import { init_plugins } from '../../lib/common'

describe('settings/SettingsCache.vue', () => {
  beforeEach(() => {
    init_plugins()
  })

  function renderView() {
    return mount(SettingsCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          SettingsHeader: true,
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

  test('renders cache statistics and metrics when cache and metrics are enabled', () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['cache-view'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]

    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="cache-statistics"]').text()).toContain('statistics foo')
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="cache-metrics"]').text()).toContain('metrics foo')
    expect(wrapper.text()).not.toContain('Live cache metrics are unavailable')
  })

  test('renders cache statistics without metrics when metrics are disabled', () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['cache-view'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: false,
        cache: true
      }
    ]

    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="cache-statistics"]').text()).toContain('statistics foo')
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(0)
    expect(wrapper.text()).toContain('Live cache metrics are unavailable')
  })

  test('renders permission message without cache children when cache-view is denied', () => {
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

    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.text()).toContain('No permission to get cache information on this cluster.')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(0)
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Live cache metrics are unavailable')
  })

  test('renders cache disabled message without cache children when cache is turned off', () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['cache-view'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: false
      }
    ]

    const wrapper = renderView()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.text()).toContain('Cache is disabled on this cluster.')
    expect(wrapper.findAll('[data-testid="cache-statistics"]')).toHaveLength(0)
    expect(wrapper.findAll('[data-testid="cache-metrics"]')).toHaveLength(0)
    expect(wrapper.text()).not.toContain('Live cache metrics are unavailable')
  })
})

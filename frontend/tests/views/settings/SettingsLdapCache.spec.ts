import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SettingsLdapCacheView from '@/views/settings/SettingsLdapCache.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

const mockGatewayAPI = {
  ldap_cache_users: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('settings/SettingsLdapCache.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
  })

  test('renders cached LDAP users by cluster', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['cache-view'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users.mockResolvedValueOnce([
      { username: 'alice', fullname: 'Alice Doe' },
      { username: 'bob', fullname: null }
    ])

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('Alice Doe')
    expect(wrapper.text()).toContain('bob')
    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenCalledWith('foo')
  })

  test('shows disabled message when cluster database support is unavailable', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['cache-view'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: false
      }
    ]

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No cluster has database support enabled for LDAP user caching.')
    expect(mockGatewayAPI.ldap_cache_users).not.toHaveBeenCalled()
  })

  test('shows permission error for denied clusters', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No permission to get LDAP cache information on this cluster.')
    expect(mockGatewayAPI.ldap_cache_users).not.toHaveBeenCalled()
  })

  test('shows empty state when no cached LDAP users are present', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['cache-view'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users.mockResolvedValueOnce([])

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No cached LDAP users found on this cluster.')
  })
})

import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import SettingsLdapCacheView from '@/views/settings/SettingsLdapCache.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { RouterMock } from 'vue-router-mock'

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

function paginatedUsersResponse(items: Array<{ username: string; fullname: string | null }>, total: number, page = 1) {
  return {
    items,
    total,
    page,
    page_size: 20
  }
}

describe('settings/SettingsLdapCache.vue', () => {
  beforeEach(() => {
    void init_plugins()
    vi.clearAllMocks()
    mockGatewayAPI.ldap_cache_users.mockReset()
  })

  async function primeAdminRoute(router: RouterMock, cluster = 'foo') {
    await router.setParams({ cluster })
    router.currentRoute.value.name = 'admin-ldap-cache'
  }

  test('renders cached LDAP users by cluster', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-history-jobs'],
          rules: ['admin/ldap-cache:view:*', 'jobs-history:view:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true,
        user_metrics: true
      }
    ]
    mockGatewayAPI.ldap_cache_users.mockResolvedValueOnce(
      paginatedUsersResponse(
        [
          { username: 'alice', fullname: 'Alice Doe' },
          { username: 'bob', fullname: null }
        ],
        2
      )
    )

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true,
          RouterLink: RouterLinkStub
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Cluster foo')
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('Alice Doe')
    expect(wrapper.text()).toContain('bob')
    expect(wrapper.text()).toContain('-')
    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links.find((link) => link.props('to')?.name === 'user')).toBeDefined()
    expect(
      links.find(
        (link) =>
          link.props('to')?.name === 'user' &&
          link.props('to')?.query?.section === 'analysis'
      )
    ).toBeDefined()
    expect(links.find((link) => link.props('to')?.name === 'jobs-history')).toBeDefined()
    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenCalledWith('foo', {
      username: undefined,
      page: 1,
      page_size: 20
    })
  })

  test('renders cached LDAP users when backend still returns a legacy array', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
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

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('Alice Doe')
    expect(wrapper.text()).toContain('bob')
    expect(wrapper.text()).toContain('2 users found')
  })

  test('searches by username and resets to first page', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1))
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1))

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()
    await wrapper.get('input').setValue('ali')
    await wrapper.get('button').trigger('click')
    await flushPromises()

    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenLastCalledWith('foo', {
      username: 'ali',
      page: 1,
      page_size: 20
    })
  })

  test('supports pagination and reset', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 60, 1))
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'bob', fullname: 'Bob Doe' }], 60, 2))
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 60, 1))

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()
    const pageTwoButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === '2')
    expect(pageTwoButton).toBeDefined()
    await pageTwoButton!.trigger('click')
    await flushPromises()
    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenLastCalledWith('foo', {
      username: undefined,
      page: 2,
      page_size: 20
    })

    const resetButton = wrapper
      .findAll('button')
      .find((button) => button.text().trim() === 'Reset')
    expect(resetButton).toBeDefined()
    await resetButton!.trigger('click')
    await flushPromises()
    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenLastCalledWith('foo', {
      username: undefined,
      page: 1,
      page_size: 20
    })
  })

  test('keeps cluster state isolated', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      },
      {
        name: 'bar',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
        racksdb: true,
        infrastructure: 'bar',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1))
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'bob', fullname: 'Bob Doe' }], 1))
      .mockResolvedValueOnce(paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1))

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('ali')
    const searchButtons = wrapper.findAll('button').filter((button) => button.text().trim() === 'Search')
    await searchButtons[0].trigger('click')
    await flushPromises()

    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenNthCalledWith(1, 'foo', {
      username: undefined,
      page: 1,
      page_size: 20
    })
    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenNthCalledWith(2, 'bar', {
      username: undefined,
      page: 1,
      page_size: 20
    })
    expect(mockGatewayAPI.ldap_cache_users).toHaveBeenNthCalledWith(3, 'foo', {
      username: 'ali',
      page: 1,
      page_size: 20
    })
  })

  test('shows disabled message when cluster database support is unavailable', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: false
      }
    ]

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No cluster has database support enabled for LDAP user caching.')
    expect(mockGatewayAPI.ldap_cache_users).not.toHaveBeenCalled()
  })

  test('shows permission error for denied clusters', async () => {
    const router = init_plugins()
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

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No permission to get LDAP cache information on this cluster.')
    expect(mockGatewayAPI.ldap_cache_users).not.toHaveBeenCalled()
  })

  test('shows empty state when no cached LDAP users are present', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-cache:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users.mockResolvedValueOnce(paginatedUsersResponse([], 0))

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('No cached LDAP users found on this cluster.')
  })
})

import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import SettingsLdapCacheView from '@/views/settings/SettingsLdapCache.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { RouterMock } from 'vue-router-mock'
import { i18n } from '@/plugins/i18n'

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

function paginatedUsersResponse(
  items: Array<{ username: string; fullname: string | null }>,
  total: number,
  page = 1
) {
  return {
    items,
    total,
    page,
    page_size: 20
  }
}

const tabsStub = {
  props: ['entry'],
  template: '<div>{{ entry }}</div>'
}

describe('settings/SettingsLdapCache.vue', () => {
  beforeEach(() => {
    void init_plugins()
    vi.clearAllMocks()
    i18n.global.locale.value = 'en'
    mockGatewayAPI.ldap_cache_users.mockReset()
  })

  async function primeAdminRoute(router: RouterMock, cluster = 'foo') {
    router.currentRoute.value = {
      ...router.currentRoute.value,
      name: 'admin-ldap-users',
      params: { cluster }
    }
    await flushPromises()
  }

  test('renders cached LDAP users by cluster', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-history-jobs'],
          rules: ['admin/ldap-users:view:*', 'jobs-history:view:*']
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
          AdminTabs: tabsStub,
          AdminHeader: true,
          RouterLink: RouterLinkStub
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('users')
    expect(wrapper.text()).not.toContain('Cluster foo')
    expect(wrapper.text()).not.toContain('LDAP Cache')
    expect(wrapper.text()).toContain(i18n.global.t('settings.ldapUsers.search.label'))
    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('Alice Doe')
    expect(wrapper.text()).toContain('bob')
    expect(wrapper.text()).toContain('-')
    expect(wrapper.find('.ui-table-scroll').exists()).toBe(true)
    expect(wrapper.find('.ui-table-shell .ui-results-pagination').exists()).toBe(true)
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
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
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
          AdminTabs: tabsStub,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('alice')
    expect(wrapper.text()).toContain('Alice Doe')
    expect(wrapper.text()).toContain('bob')
    expect(wrapper.text()).toContain(i18n.global.t('settings.ldapUsers.resultsCountPlural', { count: 2 }))
  })

  test('searches by username and resets to first page', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1)
      )
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1)
      )

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: tabsStub,
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
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 60, 1)
      )
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'bob', fullname: 'Bob Doe' }], 60, 2)
      )
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 60, 1)
      )

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: tabsStub,
          AdminHeader: true
        }
      }
    })

    await flushPromises()
    const pageTwoButton = wrapper.findAll('button').find((button) => button.text().trim() === '2')
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
      .find((button) => button.text().trim() === i18n.global.t('common.buttons.reset'))
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
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      },
      {
        name: 'bar',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
        racksdb: true,
        infrastructure: 'bar',
        metrics: true,
        cache: true,
        database: true
      }
    ]
    mockGatewayAPI.ldap_cache_users
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1)
      )
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'bob', fullname: 'Bob Doe' }], 1)
      )
      .mockResolvedValueOnce(
        paginatedUsersResponse([{ username: 'alice', fullname: 'Alice Doe' }], 1)
      )

    await primeAdminRoute(router)

    const wrapper = mount(SettingsLdapCacheView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: tabsStub,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('ali')
    const searchButtons = wrapper
      .findAll('button')
      .filter((button) => button.text().trim() === i18n.global.t('common.buttons.search'))
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
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
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
          AdminTabs: tabsStub,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain(
      i18n.global.t('settings.ldapUsers.alerts.noClusterDatabase')
    )
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
          AdminTabs: tabsStub,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain(i18n.global.t('settings.ldapUsers.alerts.noPermission'))
    expect(mockGatewayAPI.ldap_cache_users).not.toHaveBeenCalled()
  })

  test('shows empty state when no cached LDAP users are present', async () => {
    const router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
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
          AdminTabs: tabsStub,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain(i18n.global.t('settings.ldapUsers.alerts.empty'))
  })
})

import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import SettingsAccessControlView from '@/views/settings/SettingsAccessControl.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { RouterMock } from 'vue-router-mock'

const mockGatewayAPI = {
  access_catalog: vi.fn(),
  access_roles: vi.fn(),
  create_access_role: vi.fn(),
  update_access_role: vi.fn(),
  delete_access_role: vi.fn(),
  access_users: vi.fn(),
  access_user_roles: vi.fn(),
  update_access_user_roles: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('views/settings/SettingsAccessControl.vue', () => {
  async function mountOnAdminRoute(router: RouterMock) {
    await router.setParams({ cluster: 'foo' })
    router.currentRoute.value.name = 'admin-access-control'
  }

  beforeEach(() => {
    void init_plugins()
    vi.clearAllMocks()
    mockGatewayAPI.access_catalog.mockReset()
    mockGatewayAPI.access_roles.mockReset()
    mockGatewayAPI.create_access_role.mockReset()
    mockGatewayAPI.update_access_role.mockReset()
    mockGatewayAPI.delete_access_role.mockReset()
    mockGatewayAPI.access_users.mockReset()
    mockGatewayAPI.access_user_roles.mockReset()
    mockGatewayAPI.update_access_user_roles.mockReset()
  })

  test('loads current-cluster roles and saves assignments in manage mode', async () => {
    const router = init_plugins()
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['admin'],
          actions: [],
          rules: ['admin/access-control:view:*', 'admin/access-control:edit:*', 'admin/access-control:delete:*']
        },
        capabilities: { access_control: true },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.beforeSettingsRoute = { params: { cluster: 'foo' } } as never

    mockGatewayAPI.access_catalog.mockResolvedValue({
      operations: ['view', 'edit', 'delete'],
      scopes: ['*', 'self'],
      groups: [
        {
          group: 'main-routes',
          label: 'Main Routes',
          resources: [
            {
              resource: 'jobs',
              label: 'Jobs',
              operations: ['view'],
              scopes: ['*']
            }
          ]
        },
        {
          group: 'settings',
          label: 'Settings',
          resources: [
            {
              resource: 'admin/access-control',
              label: 'Admin / Access Control',
              operations: ['view'],
              scopes: ['*']
            }
          ]
        }
      ],
      legacy_map: {
        'view-jobs': ['jobs:view:*']
      }
    })
    mockGatewayAPI.access_roles.mockResolvedValue([
      {
        id: 1,
        name: 'db-admin',
        description: 'Database administrators',
        actions: ['view-jobs'],
        permissions: ['jobs:view:*', 'admin/access-control:edit:*']
      }
    ])
    mockGatewayAPI.access_users.mockResolvedValue({
      items: [
        {
          username: 'alice',
          fullname: 'Alice Doe',
          policy_roles: ['user'],
          policy_actions: ['view-jobs'],
          custom_roles: [],
          custom_actions: []
        }
      ],
      total: 1,
      page: 1,
      page_size: 20
    })
    mockGatewayAPI.access_user_roles.mockResolvedValue({
      username: 'alice',
      fullname: 'Alice Doe',
      policy_roles: ['user'],
      policy_actions: ['view-jobs'],
      custom_roles: [
        {
          id: 1,
          name: 'db-admin',
          description: 'Database administrators',
          actions: ['view-jobs'],
          permissions: ['jobs:view:*', 'admin/access-control:edit:*']
        }
      ],
      custom_actions: ['view-jobs']
    })
    mockGatewayAPI.create_access_role.mockResolvedValue({
      id: 2,
      name: 'ops-viewer',
      description: 'Operations read-only',
      actions: ['view-jobs'],
      permissions: ['jobs:view:*', 'admin/access-control:view:*']
    })
    mockGatewayAPI.update_access_user_roles.mockResolvedValue({
      username: 'alice',
      fullname: 'Alice Doe',
      policy_roles: ['user'],
      policy_actions: ['view-jobs'],
      custom_roles: [
        {
          id: 1,
          name: 'db-admin',
          description: 'Database administrators',
          actions: ['view-jobs'],
          permissions: ['jobs:view:*', 'admin/access-control:edit:*']
        }
      ],
      custom_actions: ['view-jobs']
    })

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAccessControlView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.access_catalog).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.access_roles).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.access_users).toHaveBeenCalledWith('foo', {
      username: undefined,
      page: 1,
      page_size: 20
    })
    expect(mockGatewayAPI.access_user_roles).toHaveBeenCalledWith('foo', 'alice')
    expect(wrapper.text()).toContain('Role Definitions')
    expect(wrapper.text()).toContain('User Role Bindings')
    expect(wrapper.text()).toContain('db-admin')

    await wrapper.get('input[placeholder="ops-viewer"]').setValue('ops-viewer')
    await wrapper
      .get('input[placeholder="Read-only access to cluster routes."]')
      .setValue('Operations read-only')

    const rolePermissionCheckboxes = wrapper.findAll('input[type="checkbox"]').slice(0, 2)
    await rolePermissionCheckboxes[0].setValue(true)
    await rolePermissionCheckboxes[1].setValue(true)
    await wrapper.get('form').trigger('submit.prevent')

    expect(mockGatewayAPI.create_access_role).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        name: 'ops-viewer',
        description: 'Operations read-only',
        actions: ['view-jobs'],
        permissions: expect.arrayContaining(['jobs:view:*', 'admin/access-control:view:*'])
      })
    )

    const saveButton = wrapper
      .findAll('button')
      .find((node) => node.text().includes('Save Assignments'))
    expect(saveButton).toBeDefined()
    await saveButton!.trigger('click')

    expect(mockGatewayAPI.update_access_user_roles).toHaveBeenCalledWith('foo', 'alice', [1])
  })

  test('shows read-only state when the user lacks admin/access-control:edit:*', async () => {
    const router = init_plugins()
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['auditor'],
          actions: [],
          rules: ['admin/access-control:view:*']
        },
        capabilities: { access_control: true },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.beforeSettingsRoute = { params: { cluster: 'foo' } } as never

    mockGatewayAPI.access_catalog.mockResolvedValue({
      operations: ['view', 'edit', 'delete'],
      scopes: ['*', 'self'],
      groups: [
        {
          group: 'settings',
          label: 'Settings',
          resources: [
            {
              resource: 'admin/access-control',
              label: 'Admin / Access Control',
              operations: ['view'],
              scopes: ['*']
            }
          ]
        }
      ],
      legacy_map: {}
    })
    mockGatewayAPI.access_roles.mockResolvedValue([
      {
        id: 1,
        name: 'db-auditor',
        description: 'Read-only role',
        actions: [],
        permissions: ['admin/access-control:view:*']
      }
    ])
    mockGatewayAPI.access_users.mockResolvedValue({
      items: [],
      total: 0,
      page: 1,
      page_size: 20
    })

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAccessControlView, {
      global: {
        stubs: {
          SettingsTabs: true,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.access_catalog).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.access_roles).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.access_users).toHaveBeenCalledWith('foo', {
      username: undefined,
      page: 1,
      page_size: 20
    })
    expect(wrapper.text()).toContain('editing requires admin/access-control:edit:*')
    expect(wrapper.text()).toContain('No cached users match the current search.')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()
  })
})

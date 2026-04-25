import { describe, test, expect, beforeEach } from 'vitest'
import { mount, RouterLinkStub } from '@vue/test-utils'
import SettingsAccountView from '@/views/settings/SettingsAccount.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'

describe('views/settings/SettingsAccount.vue', () => {
  beforeEach(() => {
    init_plugins()
    const authStore = useAuthStore()
    authStore.username = 'alice'
    authStore.fullname = 'Alice Doe'
    authStore.groups = ['users']
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['user', 'researcher'],
          actions: ['view-history-jobs', 'view-jobs'],
          sources: {
            policy: {
              roles: ['user'],
              actions: ['view-jobs']
            },
            custom: {
              roles: ['researcher'],
              actions: ['view-history-jobs']
            },
            merged: {
              roles: ['researcher', 'user'],
              actions: ['view-history-jobs', 'view-jobs']
            }
          }
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        user_metrics: true
      }
    ]
  })

  test('renders user shortcuts', () => {
    const wrapper = mount(SettingsAccountView, {
      global: {
        stubs: {
          SettingsTabs: true,
          RouterLink: RouterLinkStub
        }
      }
    })

    const links = wrapper.findAllComponents(RouterLinkStub)
    expect(links.find((link) => link.props('to')?.name === 'my-profile')).toBeDefined()
    expect(
      links.find(
        (link) =>
          link.props('to')?.name === 'my-profile' &&
          link.props('to')?.query?.section === 'analysis'
      )
    ).toBeDefined()
    expect(links.find((link) => link.props('to')?.name === 'jobs-history')).toBeDefined()
  })

  test('renders policy, custom and merged permissions', () => {
    const wrapper = mount(SettingsAccountView, {
      global: {
        stubs: {
          SettingsTabs: true,
          RouterLink: RouterLinkStub
        }
      }
    })

    expect(wrapper.text()).toContain('Policy Roles & Actions')
    expect(wrapper.text()).toContain('Custom Roles & Actions')
    expect(wrapper.text()).toContain('Merged Roles & Actions')
    expect(wrapper.text()).toContain('researcher')
    expect(wrapper.text()).toContain('view-history-jobs')
    expect(wrapper.text()).toContain('view-jobs')
  })
})

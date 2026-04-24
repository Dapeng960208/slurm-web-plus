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
        permissions: { roles: ['user'], actions: ['view-history-jobs'] },
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
    expect(links.find((link) => link.props('to')?.name === 'user')).toBeDefined()
    expect(links.find((link) => link.props('to')?.name === 'user-analysis')).toBeDefined()
    expect(links.find((link) => link.props('to')?.name === 'jobs-history')).toBeDefined()
  })
})

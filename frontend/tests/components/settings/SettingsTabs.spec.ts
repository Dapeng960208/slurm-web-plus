import { describe, test, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { nextTick } from 'vue'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'

function mountTabs(authentication: boolean, clusters: Array<Record<string, unknown>>) {
  const wrapper = mount(SettingsTabs, {
    props: { entry: 'General' },
    global: {
      stubs: {
        RouterLink: { template: '<a><slot /></a>' }
      },
      plugins: [
        [runtimeConfiguration, { api_server: 'http://localhost', authentication }],
        createTestingPinia({ stubActions: false })
      ]
    }
  })
  useRuntimeStore().availableClusters = clusters as never
  return wrapper
}

describe('SettingsTabs.vue', () => {
  test('shows LDAP Cache tab only when authentication and database support are enabled', async () => {
    const wrapper = mountTabs(true, [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ])

    await nextTick()
    expect(wrapper.text()).toContain('LDAP Cache')
  })

  test('hides LDAP Cache tab when authentication is disabled', async () => {
    const wrapper = mountTabs(false, [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ])

    await nextTick()
    expect(wrapper.text()).not.toContain('LDAP Cache')
  })

  test('hides LDAP Cache tab when no cluster has database support', async () => {
    const wrapper = mountTabs(true, [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: false
      }
    ])

    await nextTick()
    expect(wrapper.text()).not.toContain('LDAP Cache')
  })
})

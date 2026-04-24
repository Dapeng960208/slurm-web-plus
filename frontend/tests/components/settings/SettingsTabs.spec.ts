import { describe, test, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { nextTick } from 'vue'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'

function mountTabs(
  authentication: boolean,
  clusters: Array<Record<string, unknown>>,
  settingsCluster?: string
) {
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
  const runtimeStore = useRuntimeStore()
  runtimeStore.availableClusters = clusters as never
  runtimeStore.beforeSettingsRoute = settingsCluster
    ? ({ params: { cluster: settingsCluster } } as never)
    : undefined
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

  test('shows Access Control tab when the current settings cluster supports it', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: { roles: [], actions: [] },
          capabilities: { access_control: true },
          racksdb: true,
          infrastructure: 'foo',
          metrics: true,
          cache: true
        },
        {
          name: 'bar',
          permissions: { roles: [], actions: [] },
          capabilities: { access_control: false },
          racksdb: true,
          infrastructure: 'bar',
          metrics: true,
          cache: true
        }
      ],
      'foo'
    )

    await nextTick()
    expect(wrapper.text()).toContain('Access Control')
  })

  test('shows AI tab when the current settings cluster supports it and user can manage it', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: { roles: [], actions: ['manage-ai'] },
          capabilities: {
            ai: {
              enabled: true
            }
          },
          racksdb: true,
          infrastructure: 'foo',
          metrics: true,
          cache: true
        }
      ],
      'foo'
    )

    await nextTick()
    expect(wrapper.text()).toContain('AI')
  })

  test('hides AI tab when only another cluster supports it', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: { roles: [], actions: ['manage-ai'] },
          capabilities: {
            ai: false
          },
          racksdb: true,
          infrastructure: 'foo',
          metrics: true,
          cache: true
        },
        {
          name: 'bar',
          permissions: { roles: [], actions: ['manage-ai'] },
          capabilities: {
            ai: {
              enabled: true
            }
          },
          racksdb: true,
          infrastructure: 'bar',
          metrics: true,
          cache: true
        }
      ],
      'foo'
    )

    await nextTick()
    expect(wrapper.text()).not.toContain('AI')
  })

  test('hides Access Control tab when only another cluster supports it', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: { roles: [], actions: [] },
          capabilities: { access_control: false },
          racksdb: true,
          infrastructure: 'foo',
          metrics: true,
          cache: true
        },
        {
          name: 'bar',
          permissions: { roles: [], actions: [] },
          capabilities: { access_control: true },
          racksdb: true,
          infrastructure: 'bar',
          metrics: true,
          cache: true
        }
      ],
      'foo'
    )

    await nextTick()
    expect(wrapper.text()).not.toContain('Access Control')
  })
})

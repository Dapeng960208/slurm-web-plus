import { beforeEach, describe, test, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { nextTick } from 'vue'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'
import { i18n } from '@/plugins/i18n'

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
        i18n,
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
  beforeEach(() => {
    i18n.global.locale.value = 'en'
  })

  test('does not show Users tab in the legacy settings workspace after admin-page migration', async () => {
    const wrapper = mountTabs(true, [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['admin/ldap-users:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        database: true
      }
    ])

    await nextTick()
    expect(wrapper.text()).not.toContain('Users')
  })

  test('does not show Access Control tab after admin-page migration', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: { roles: [], actions: [], rules: ['admin/access-control:view:*'] },
          capabilities: { access_control: true },
          racksdb: true,
          infrastructure: 'foo',
          metrics: true,
          cache: true
        }
      ],
      'foo'
    )

    await nextTick()
    expect(wrapper.text()).not.toContain('Access Control')
  })

  test('does not show AI tab after admin-page migration', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: { roles: [], actions: [], rules: ['admin/ai:view:*'] },
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
    expect(wrapper.text()).not.toContain('AI')
  })

  test('keeps only base settings tabs visible', async () => {
    const wrapper = mountTabs(
      true,
      [
        {
          name: 'foo',
          permissions: {
            roles: [],
            actions: [],
            rules: [
              'admin/ai:view:*',
              'admin/access-control:view:*',
              'admin/cache:view:*',
              'admin/ldap-users:view:*'
            ]
          },
          capabilities: {
            ai: {
              enabled: true
            },
            access_control: true
          },
          racksdb: true,
          infrastructure: 'foo',
          metrics: true,
          cache: true,
          database: true
        }
      ],
      'foo'
    )

    await nextTick()
    expect(wrapper.text()).toContain('General')
    expect(wrapper.text()).toContain('Errors')
    expect(wrapper.text()).toContain('Account')
    expect(wrapper.text()).not.toContain('AI')
    expect(wrapper.text()).not.toContain('Access Control')
    expect(wrapper.text()).not.toContain('Cache')
    expect(wrapper.text()).not.toContain('Users')
  })

  test('renders translated tab labels', async () => {
    const wrapper = mountTabs(true, [])

    i18n.global.locale.value = 'zh-CN'
    await nextTick()

    expect(wrapper.text()).toContain('常规')
    expect(wrapper.text()).toContain('错误')
    expect(wrapper.text()).toContain('账户')
  })
})

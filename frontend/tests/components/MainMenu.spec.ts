import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { beforeEach, describe, expect, test } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { nextTick } from 'vue'
import MainMenu from '@/components/MainMenu.vue'
import { i18n } from '@/plugins/i18n'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'

function mountMenu(props: Record<string, unknown>) {
  return shallowMount(MainMenu, {
    props,
    global: {
      plugins: [
        i18n,
        [
          runtimeConfiguration,
          {
            api_server: 'http://localhost',
            authentication: true,
            racksdb_rows_labels: false,
            racksdb_racks_labels: false,
            version: 'test-version'
          }
        ],
        createTestingPinia({
          stubActions: false
        })
      ],
      stubs: {
        RouterLink: {
          props: ['to'],
          template: '<a :data-to="to ? JSON.stringify(to) : undefined"><slot /></a>'
        },
        TransitionRoot: {
          template: '<div><slot /></div>'
        },
        TransitionChild: {
          template: '<div><slot /></div>'
        },
        Dialog: {
          template: '<div><slot /></div>'
        },
        DialogPanel: {
          template: '<div><slot /></div>'
        },
        BrandLogo: {
          props: ['framed', 'size'],
          template:
            '<div class="brand-logo-stub" :data-framed="String(framed)" :data-size="size" />'
        }
      }
    }
  })
}

describe('MainMenu.vue', () => {
  beforeEach(() => {
    i18n.global.locale.value = 'en'
  })

  test('renders the visible sidebar logo without the white frame', () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      modelValue: true
    })

    const logos = wrapper.findAll('.brand-logo-stub')

    expect(logos.length).toBeGreaterThan(0)
    expect(logos.every((logo) => logo.attributes('data-framed') === 'false')).toBe(true)
  })

  test('passes framed=false to both sidebar logo call sites', () => {
    const sourcePath = resolve(process.cwd(), 'src/components/MainMenu.vue')
    const source = readFileSync(sourcePath, 'utf8')
    const matches = source.match(/<BrandLogo size="sm" :framed="false" \/>/g) ?? []

    expect(matches).toHaveLength(2)
  })

  test('shows jobs history only with dedicated permission', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['view-history-jobs'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        persistence: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).toContain('Jobs History')
  })

  test('shows AI only when the cluster advertises AI capability and the user has ai:view:*', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['view-stats'], rules: ['ai:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        capabilities: {
          ai: {
            enabled: true
          }
        }
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).toContain('AI')

    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['view-stats'], rules: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        capabilities: {
          ai: false
        }
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).not.toContain('AI')
  })

  test('shows Admin when the cluster exposes admin permissions', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['admin'],
          actions: [],
          rules: ['admin/cache:view:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).toContain('Admin')
  })

  test('links Admin to the first accessible admin page by priority', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['admin'],
          actions: [],
          rules: ['admin/ldap-cache:view:*', 'admin/cache:view:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    const adminLink = wrapper.findAll('a').find((link) => link.text().trim() === 'Admin')

    expect(adminLink?.attributes('data-to')).toContain('"name":"admin-cache"')
  })

  test('shows Admin when permissions come from admin-manage super-admin action', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['ops-admin'],
          actions: ['admin-manage']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).toContain('Admin')
  })

  test('does not show Admin for a regular user with self-scoped job actions only', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['user'],
          actions: [],
          rules: ['jobs:view:self', 'jobs:edit:self', 'jobs:delete:self']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).not.toContain('Admin')
  })

  test('shows AI but hides Admin for a regular user with default-style AI access', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: ['user'],
          actions: [],
          rules: ['dashboard:view:*', 'analysis:view:*', 'ai:view:*', 'jobs:view:self']
        },
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
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).toContain('AI')
    expect(wrapper.text()).not.toContain('Admin')
  })

  test('updates translated navigation labels after locale switch', async () => {
    const wrapper = mountMenu({
      entry: 'dashboard',
      clusterContext: 'foo',
      modelValue: true
    })

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: ['user'], actions: [], rules: ['dashboard:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    runtimeStore.currentCluster = runtimeStore.availableClusters[0]
    await nextTick()

    expect(wrapper.text()).toContain('Dashboard')

    i18n.global.locale.value = 'zh-CN'
    await nextTick()

    expect(wrapper.text()).toContain('概览')
  })
})

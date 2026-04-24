import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import { nextTick } from 'vue'
import MainMenu from '@/components/MainMenu.vue'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'
import { useRuntimeStore } from '@/stores/runtime'

describe('MainMenu.vue', () => {
  test('renders the visible sidebar logo without the white frame', () => {
    const wrapper = shallowMount(MainMenu, {
      props: {
        entry: 'dashboard',
        modelValue: true
      },
      global: {
        plugins: [
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
            template: '<a><slot /></a>'
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
    const wrapper = shallowMount(MainMenu, {
      props: {
        entry: 'dashboard',
        clusterContext: 'foo',
        modelValue: true
      },
      global: {
        plugins: [
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
            template: '<a><slot /></a>'
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

  test('shows AI only when the cluster advertises AI capability and the user has view-ai', async () => {
    const wrapper = shallowMount(MainMenu, {
      props: {
        entry: 'dashboard',
        clusterContext: 'foo',
        modelValue: true
      },
      global: {
        plugins: [
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
            template: '<a><slot /></a>'
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

    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['view-stats', 'view-ai'] },
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
        permissions: { roles: [], actions: ['view-stats'] },
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
})

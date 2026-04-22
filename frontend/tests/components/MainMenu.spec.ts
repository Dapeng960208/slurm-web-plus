import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, test } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import MainMenu from '@/components/MainMenu.vue'
import { runtimeConfiguration } from '@/plugins/runtimeConfiguration'

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
            template: '<div class="brand-logo-stub" :data-framed="String(framed)" :data-size="size" />'
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
})

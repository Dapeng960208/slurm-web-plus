import { describe, test, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import { i18n } from '@/plugins/i18n'

describe('SettingsHeader.vue', () => {
  test('renders title and description', () => {
    const wrapper = mount(SettingsHeader, {
      global: {
        plugins: [i18n]
      },
      props: {
        title: 'settings.general.title',
        description: 'settings.general.description'
      }
    })
    const heading = wrapper.get('h1')
    expect(heading.text()).toBe('General Settings')

    const description = wrapper.get('.ui-page-description')
    expect(description.text()).toBe('Configure general application preferences.')
  })
})

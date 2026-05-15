import { describe, test, expect, beforeEach } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import RemoteSearchSelect from '@/components/forms/RemoteSearchSelect.vue'
import { init_plugins } from '../../lib/common'

describe('RemoteSearchSelect.vue', () => {
  beforeEach(() => {
    init_plugins()
  })

  test('loads remote options and emits selected single value', async () => {
    const search = async (query: string) => [
      { value: 'alice', label: 'alice', description: `query:${query}` }
    ]

    const wrapper = mount(RemoteSearchSelect, {
      props: {
        modelValue: '',
        source: { search },
        minQueryLength: 1
      }
    })

    await wrapper.get('input').setValue('ali')
    await new Promise((resolve) => setTimeout(resolve, 220))
    await flushPromises()

    expect(wrapper.text()).toContain('alice')
    await wrapper.get('li.ui-combobox-option').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['alice'])
  })

  test('renders selected tags and removes multi values', async () => {
    const wrapper = mount(RemoteSearchSelect, {
      props: {
        modelValue: ['normal', 'debug'],
        multiple: true,
        source: {
          search: async () => [
            { value: 'normal', label: 'normal' },
            { value: 'debug', label: 'debug' }
          ]
        }
      }
    })

    await flushPromises()

    expect(wrapper.findAll('.ui-search-select-tag')).toHaveLength(2)
    await wrapper.findAll('.ui-search-select-tag-remove')[0].trigger('click')

    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual([['debug']])
  })
})

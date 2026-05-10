import { describe, test, expect, beforeEach, vi } from 'vitest'
import { ref } from 'vue'
import { mount } from '@vue/test-utils'
import UserFilterSelector from '@/components/jobs/UserFilterSelector.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

const usersData = ref([
  { login: 'alice', fullname: 'Alice Doe' },
  { login: 'bob', fullname: 'Bob Smith' }
])

vi.mock('@/composables/DataGetter', () => ({
  useGatewayDataGetter: () => ({ data: usersData })
}))

describe('UserFilterSelector.vue', () => {
  beforeEach(() => {
    init_plugins()
    useRuntimeStore().jobs.filters.users = []
  })

  test('adds a manually entered username and clears the input', async () => {
    const wrapper = mount(UserFilterSelector, {
      global: {
        stubs: {
          Combobox: { template: '<div><slot /></div>' },
          ComboboxInput: {
            props: ['placeholder'],
            emits: ['change'],
            template:
              '<input :placeholder="placeholder" @input="$emit(\'change\', $event)" />'
          },
          ComboboxButton: { template: '<button type="button"><slot /></button>' },
          ComboboxOptions: { template: '<ul><slot /></ul>' },
          ComboboxOption: { template: '<li><slot :active="false" :selected="false" /></li>' }
        }
      }
    })

    await wrapper.get('input').setValue('  charlie  ')
    expect(wrapper.get('input').classes()).toContain('ui-combobox-input')
    await wrapper.get('button.ui-button-primary').trigger('click')

    expect(useRuntimeStore().jobs.filters.users).toEqual(['charlie'])
    expect(wrapper.get('button.ui-button-primary').attributes('disabled')).toBeDefined()
  })

  test('does not add empty or duplicate usernames', async () => {
    const store = useRuntimeStore()
    store.jobs.filters.users = ['alice']
    const wrapper = mount(UserFilterSelector, {
      global: {
        stubs: {
          Combobox: { template: '<div><slot /></div>' },
          ComboboxInput: {
            props: ['placeholder'],
            emits: ['change'],
            template:
              '<input :placeholder="placeholder" @input="$emit(\'change\', $event)" />'
          },
          ComboboxButton: { template: '<button type="button"><slot /></button>' },
          ComboboxOptions: { template: '<ul><slot /></ul>' },
          ComboboxOption: { template: '<li><slot :active="false" :selected="false" /></li>' }
        }
      }
    })

    await wrapper.get('input').setValue('   ')
    expect(wrapper.get('button.ui-button-primary').attributes('disabled')).toBeDefined()
    await wrapper.get('input').setValue('ALICE')
    await wrapper.get('button.ui-button-primary').trigger('click')

    expect(store.jobs.filters.users).toEqual(['alice'])
  })
})

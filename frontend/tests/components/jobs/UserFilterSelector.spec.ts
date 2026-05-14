import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import UserFilterSelector from '@/components/jobs/UserFilterSelector.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

const useGatewayDataGetter = vi.fn()

vi.mock('@/composables/DataGetter', () => ({
  useGatewayDataGetter
}))

describe('UserFilterSelector.vue', () => {
  beforeEach(() => {
    init_plugins()
    useRuntimeStore().jobs.filters.users = []
  })

  test('adds a manually entered username and clears the input', async () => {
    const wrapper = mount(UserFilterSelector)

    await wrapper.get('input').setValue('  charlie  ')
    expect(wrapper.get('input').classes()).toContain('ui-combobox-input')
    await wrapper.get('button.ui-button-primary').trigger('click')

    expect(useRuntimeStore().jobs.filters.users).toEqual(['charlie'])
    expect(useGatewayDataGetter).not.toHaveBeenCalled()
    expect(wrapper.get('button.ui-button-primary').attributes('disabled')).toBeDefined()
  })

  test('does not add empty or duplicate usernames', async () => {
    const store = useRuntimeStore()
    store.jobs.filters.users = ['alice']
    const wrapper = mount(UserFilterSelector)

    await wrapper.get('input').setValue('   ')
    expect(wrapper.get('button.ui-button-primary').attributes('disabled')).toBeDefined()
    await wrapper.get('input').setValue('ALICE')
    await wrapper.get('button.ui-button-primary').trigger('click')

    expect(store.jobs.filters.users).toEqual(['alice'])
  })
})

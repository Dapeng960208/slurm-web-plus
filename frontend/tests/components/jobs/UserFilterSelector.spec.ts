import { describe, test, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import UserFilterSelector from '@/components/jobs/UserFilterSelector.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

describe('UserFilterSelector.vue', () => {
  beforeEach(() => {
    const router = init_plugins()
    router.setParams({ cluster: 'foo' })
    useRuntimeStore().jobs.filters.users = []
  })

  test('uses remote search selector with multi-select model', async () => {
    const wrapper = mount(UserFilterSelector, {
      global: {
        stubs: {
          RemoteSearchSelect: {
            name: 'RemoteSearchSelect',
            template: '<div class="remote-search-select-stub" />',
            props: ['modelValue', 'multiple', 'source', 'minQueryLength', 'placeholder']
          }
        }
      }
    })

    const remoteSelector = wrapper.findComponent({ name: 'RemoteSearchSelect' })
    expect(remoteSelector.exists()).toBe(true)
    expect(Array.isArray(remoteSelector.props('modelValue'))).toBe(true)
    expect(remoteSelector.props('minQueryLength')).toBe(1)
  })
})

import { describe, test, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import JobsHistoryFiltersPanel from '@/components/jobs/JobsHistoryFiltersPanel.vue'

describe('JobsHistoryFiltersPanel.vue', () => {
  test('supports seconds precision in time range inputs', () => {
    const wrapper = mount(JobsHistoryFiltersPanel, {
      props: {
        open: true,
        total: 0,
        filters: {
          keyword: '',
          user: '',
          account: '',
          partition: '',
          qos: '',
          state: '',
          job_id: undefined,
          start: '',
          end: ''
        }
      },
      global: {
        stubs: {
          TransitionRoot: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          Disclosure: { template: '<div><slot :open="true" /></div>' },
          DisclosureButton: { template: '<button><slot /></button>' },
          DisclosurePanel: { template: '<div><slot /></div>' }
        }
      }
    })

    const inputs = wrapper.findAll('input[type="datetime-local"]')
    expect(inputs).toHaveLength(2)
    expect(inputs[0].attributes('step')).toBe('1')
    expect(inputs[1].attributes('step')).toBe('1')
    expect(wrapper.get('input[placeholder="Search workdir / command"]').exists()).toBe(true)
  })
})

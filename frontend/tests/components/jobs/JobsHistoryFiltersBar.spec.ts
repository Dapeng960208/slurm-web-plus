import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import JobsHistoryFiltersBar from '@/components/jobs/JobsHistoryFiltersBar.vue'

describe('JobsHistoryFiltersBar.vue', () => {
  test('renders and removes keyword filter chips', async () => {
    const filters = {
      keyword: 'sleep',
      user: '',
      account: '',
      partition: '',
      qos: '',
      state: '',
      job_id: undefined,
      start: '',
      end: ''
    }

    const wrapper = mount(JobsHistoryFiltersBar, {
      props: { filters }
    })

    expect(wrapper.text()).toContain('sleep')

    await wrapper.get('button').trigger('click')

    expect(filters.keyword).toBe('')
    expect(wrapper.emitted('search')).toHaveLength(1)
  })
})

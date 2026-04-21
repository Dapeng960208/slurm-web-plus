import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import JobFieldExitCode from '@/components/job/JobFieldExitCode.vue'

describe('JobFieldExitCode.vue', () => {
  test('renders signaled exit code using shared formatter', () => {
    const wrapper = mount(JobFieldExitCode, {
      props: {
        exit_code: {
          return_code: { infinite: false, number: 0, set: false },
          signal: { id: { infinite: false, number: 15, set: true }, name: 'TERM' },
          status: ['SIGNALED']
        }
      }
    })

    expect(wrapper.text()).toContain('SIGNALED (TERM/15)')
  })
})

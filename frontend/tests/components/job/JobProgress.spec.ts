import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import JobProgress from '@/components/job/JobProgress.vue'
import jobPending from '../../assets/job-pending.json'
import jobRunning from '../../assets/job-running.json'
import jobCompleted from '../../assets/job-completed.json'
import jobFailed from '../../assets/job-failed.json'
import jobTimeout from '../../assets/job-timeout.json'

describe('JobProgress.vue', () => {
  test('renders pending job progress as vertical timeline', () => {
    const wrapper = mount(JobProgress, {
      props: { job: jobPending }
    })

    expect(wrapper.get('[data-testid="job-progress-list"]').exists()).toBe(true)
    expect(wrapper.get('#step-submitted').attributes('data-state')).toBe('complete')
    expect(wrapper.get('#step-eligible').attributes('data-state')).toBe('complete')
    expect(wrapper.get('#step-scheduling').attributes('data-state')).toBe('current')
    expect(wrapper.get('#step-running').attributes('data-state')).toBe('pending')
    expect(wrapper.get('#step-completing').attributes('data-state')).toBe('pending')
    expect(wrapper.get('#step-terminated').attributes('data-state')).toBe('pending')
    expect(wrapper.get('#step-scheduling').attributes('aria-current')).toBeUndefined()
    expect(wrapper.text()).toContain('Submitted')
    expect(wrapper.text()).toContain('Eligible')
    expect(wrapper.text()).toContain('Scheduling')
  })

  test('renders running job progress with current running step', () => {
    const wrapper = mount(JobProgress, {
      props: { job: jobRunning }
    })

    expect(wrapper.get('#step-submitted').attributes('data-state')).toBe('complete')
    expect(wrapper.get('#step-eligible').attributes('data-state')).toBe('complete')
    expect(wrapper.get('#step-scheduling').attributes('data-state')).toBe('complete')
    expect(wrapper.get('#step-running').attributes('data-state')).toBe('current')
    expect(wrapper.get('#step-completing').attributes('data-state')).toBe('pending')
    expect(wrapper.get('#step-terminated').attributes('data-state')).toBe('pending')
    expect(wrapper.get('#step-running [aria-current="step"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('Running')
    expect(wrapper.text()).toContain('seconds elapsed')
  })

  test.each([
    ['completed', jobCompleted],
    ['failed', jobFailed],
    ['timeout', jobTimeout]
  ])('renders finished %s job progress with all steps complete', (_label, job) => {
    const wrapper = mount(JobProgress, {
      props: { job }
    })

    for (const step of [
      'submitted',
      'eligible',
      'scheduling',
      'running',
      'completing',
      'terminated'
    ]) {
      expect(wrapper.get(`#step-${step}`).attributes('data-state')).toBe('complete')
    }

    expect(wrapper.text()).toContain('Terminated')
  })
})

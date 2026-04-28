import { afterEach, describe, test, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'

describe('MetricRangeSelector.vue', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  test('opens custom range dialog and applies start and end inputs', async () => {
    const wrapper = mount(MetricRangeSelector, {
      props: {
        modelValue: 'hour',
        enableCustomWindow: true,
        startValue: '2026-04-24T09:00',
        endValue: '2026-04-24T10:00'
      }
    })

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')

    expect(wrapper.find('[data-testid="metric-range-dialog"]').exists()).toBe(true)
    await wrapper.get('[data-testid="metric-range-start"]').setValue('2026-04-24T08:30')
    await wrapper.get('[data-testid="metric-range-end"]').setValue('2026-04-24T11:45')
    await wrapper.get('[data-testid="metric-range-apply"]').trigger('click')

    expect(wrapper.emitted('apply-window')).toStrictEqual([
      [
        {
          start: '2026-04-24T08:30',
          end: '2026-04-24T11:45'
        }
      ]
    ])
    expect(wrapper.find('[data-testid="metric-range-dialog"]').exists()).toBe(false)
  })

  test('keeps dialog open when the custom range is invalid', async () => {
    const wrapper = mount(MetricRangeSelector, {
      props: {
        modelValue: 'hour',
        enableCustomWindow: true,
        startValue: '2026-04-24T09:00',
        endValue: '2026-04-24T10:00'
      }
    })

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-start"]').setValue('2026-04-24T12:00')
    await wrapper.get('[data-testid="metric-range-end"]').setValue('2026-04-24T11:00')
    await wrapper.get('[data-testid="metric-range-apply"]').trigger('click')

    expect(wrapper.emitted('apply-window')).toBeUndefined()
    expect(wrapper.text()).toContain('Start time must be earlier than end time.')
    expect(wrapper.find('[data-testid="metric-range-dialog"]').exists()).toBe(true)
  })

  test('emits reset from the custom range dialog', async () => {
    const wrapper = mount(MetricRangeSelector, {
      props: {
        modelValue: 'day',
        enableCustomWindow: true,
        startValue: '2026-04-24T09:00',
        endValue: '2026-04-24T10:00',
        resetLabel: 'Last hour'
      }
    })

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-reset"]').trigger('click')

    expect(wrapper.emitted('reset-window')).toHaveLength(1)
    expect(wrapper.find('[data-testid="metric-range-dialog"]').exists()).toBe(false)
  })

  test('fills start and end from quick custom windows', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-24T12:30'))
    const wrapper = mount(MetricRangeSelector, {
      props: {
        modelValue: 'day',
        enableCustomWindow: true,
        startValue: '2026-04-24T09:00',
        endValue: '2026-04-24T10:00'
      }
    })

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-quick-7d"]').trigger('click')

    expect((wrapper.get('[data-testid="metric-range-start"]').element as HTMLInputElement).value).toBe(
      '2026-04-17T12:30'
    )
    expect((wrapper.get('[data-testid="metric-range-end"]').element as HTMLInputElement).value).toBe(
      '2026-04-24T12:30'
    )
  })
})

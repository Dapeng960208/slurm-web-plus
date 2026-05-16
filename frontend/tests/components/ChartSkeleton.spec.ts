import { describe, expect, test } from 'vitest'
import { mount } from '@vue/test-utils'
import ChartSkeleton from '@/components/ChartSkeleton.vue'
import { init_plugins } from '../lib/common'

describe('ChartSkeleton.vue', () => {
  test('renders a lightweight chart-frame placeholder', () => {
    init_plugins()

    const wrapper = mount(ChartSkeleton)

    expect(wrapper.attributes('role')).toBe('img')
    expect(wrapper.findAll('.ui-chart-skeleton-bar')).toHaveLength(0)
    expect(wrapper.findAll('.ui-chart-skeleton-line')).toHaveLength(4)
    expect(wrapper.find('.ui-chart-skeleton-axis').exists()).toBe(true)
    expect(wrapper.find('.ui-chart-skeleton-plot').exists()).toBe(true)
    expect(wrapper.findAll('.ui-chart-skeleton-point')).toHaveLength(6)
  })
})

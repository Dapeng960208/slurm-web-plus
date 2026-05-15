import { describe, test, beforeEach, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Chart } from 'chart.js/auto'
import { useRuntimeStore } from '@/stores/runtime'
import { init_plugins, getMockClusterDataPoller } from '../../lib/common'
import ChartJobsHistogram from '@/components/dashboard/ChartJobsHistogram.vue'
import metricsJobsHour from '../../assets/metrics-jobs-hour.json'
import type { MetricJobState, MetricValue } from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'

const mockClusterDataPoller = getMockClusterDataPoller<Record<MetricJobState, MetricValue[]>>()

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

describe('ChartJobsHistogram.vue', () => {
  beforeEach(() => {
    init_plugins()
    useRuntimeStore().dashboard.reset()
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.refreshing.value = false
    ;(mockClusterDataPoller.setCluster as ReturnType<typeof vi.fn>).mockClear()
    ;(mockClusterDataPoller.setParam as ReturnType<typeof vi.fn>).mockClear()
  })
  test('should display jobs charts histogram', async () => {
    const wrapper = mount(ChartJobsHistogram, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.text()).toContain('Jobs Queue')
    expect(wrapper.classes()).not.toContain('pt-16')
    expect(wrapper.classes()).not.toContain('pb-5')
    expect(wrapper.classes()).not.toContain('mt-4')
    const placeholder = wrapper.get('.ui-chart-skeleton')
    const canvas = wrapper.get({ ref: 'chartCanvas' })

    // Start with unloaded data
    mockClusterDataPoller.loaded.value = false
    await flushPromises()

    // Check placeholder is visible and chart hidden while data is not loaded
    // Note that isVisible() does not work in this case, for unknown reason.
    expect(placeholder.attributes('style')).not.toContain('display: none;')
    expect(canvas.attributes('style')).toContain('display: none;')

    // now load data
    mockClusterDataPoller.data.value = metricsJobsHour as Record<MetricJobState, MetricValue[]>
    mockClusterDataPoller.loaded.value = true
    await flushPromises()

    // Check placeholder is now hidden and chart visible now that data is loaded
    expect(placeholder.attributes('style')).toContain('display: none;')
    expect(canvas.attributes('style')).not.toContain('display: none;')
  })
  test('should display error when unable to load data', async () => {
    const wrapper = mount(ChartJobsHistogram, {
      props: {
        cluster: 'foo'
      }
    })
    mockClusterDataPoller.unable.value = true
    await flushPromises()
    // Check error message
    expect(wrapper.getComponent(ErrorAlert).text()).toBe('Unable to retrieve jobs metrics.')
    // Chart chart and placeholder are present in DOM
    expect(wrapper.find({ ref: 'chartCanvas' }).exists()).toBeFalsy()
    expect(wrapper.find('.ui-chart-skeleton').exists()).toBeFalsy()
  })

  test('refreshes jobs metrics with partition-scoped query', async () => {
    mount(ChartJobsHistogram, {
      props: {
        cluster: 'foo'
      }
    })

    useRuntimeStore().dashboard.partition = 'gpu'
    await flushPromises()

    expect(mockClusterDataPoller.setParam).toHaveBeenCalledWith({
      range: 'hour',
      partition: 'gpu'
    })
  })

  test('clears jobs chart datasets before loading a new partition', async () => {
    const wrapper = mount(ChartJobsHistogram, {
      props: {
        cluster: 'foo'
      }
    })

    mockClusterDataPoller.data.value = metricsJobsHour as Record<MetricJobState, MetricValue[]>
    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)
    expect(chart?.data.datasets.length).toBeGreaterThan(0)

    useRuntimeStore().dashboard.partition = 'debug'
    await flushPromises()

    expect(chart?.data.datasets).toHaveLength(0)
  })

  test('does not render legacy spacing utility classes', () => {
    const wrapper = mount(ChartJobsHistogram, {
      props: {
        cluster: 'foo'
      }
    })

    expect(wrapper.html()).not.toContain('pt-16')
    expect(wrapper.html()).not.toContain('pb-5')
    expect(wrapper.html()).not.toContain('mt-4')
  })
})

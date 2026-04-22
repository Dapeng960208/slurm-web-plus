import { describe, test, beforeEach, expect, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { Chart } from 'chart.js/auto'
import { useRuntimeStore } from '@/stores/runtime'
import { init_plugins, getMockClusterDataPoller } from '../../lib/common'
import ChartResourcesHistogram from '@/components/dashboard/ChartResourcesHistogram.vue'
import metricsNodesHour from '../../assets/metrics-nodes-hour.json'
import type { MetricResourceState, MetricValue } from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'

const mockClusterDataPoller = getMockClusterDataPoller<Record<MetricResourceState, MetricValue[]>>()

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

let router

describe('ChartJobsHistogram.vue', () => {
  beforeEach(() => {
    router = init_plugins()
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.refreshing.value = false
    ;(mockClusterDataPoller.setCallback as ReturnType<typeof vi.fn>).mockClear()
    ;(mockClusterDataPoller.setCluster as ReturnType<typeof vi.fn>).mockClear()
    ;(mockClusterDataPoller.setParam as ReturnType<typeof vi.fn>).mockClear()
  })
  test('should display resources charts histogram', async () => {
    const wrapper = mount(ChartResourcesHistogram, {
      props: {
        cluster: 'foo'
      }
    })
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
    mockClusterDataPoller.data.value = metricsNodesHour as Record<
      MetricResourceState,
      MetricValue[]
    >

    mockClusterDataPoller.loaded.value = true
    await flushPromises()

    // Check placeholder is now hidden and chart visible now that data is loaded
    expect(placeholder.attributes('style')).toContain('display: none;')
    expect(canvas.attributes('style')).not.toContain('display: none;')
  })
  test('should display error when unable to load data', async () => {
    const wrapper = mount(ChartResourcesHistogram, {
      props: {
        cluster: 'foo'
      }
    })
    mockClusterDataPoller.unable.value = true
    await flushPromises()
    // Check error message
    expect(wrapper.getComponent(ErrorAlert).text()).toBe('Unable to retrieve resource metrics.')
    // Chart chart and placeholder are present in DOM
    expect(wrapper.find({ ref: 'chartCanvas' }).exists()).toBeFalsy()
    expect(wrapper.find('.ui-chart-skeleton').exists()).toBeFalsy()
  })
  test('resources types button changes should change datapoller callback with route query update', async () => {
    mount(ChartResourcesHistogram, {
      props: {
        cluster: 'foo'
      }
    })
    mockClusterDataPoller.data.value = metricsNodesHour as Record<
      MetricResourceState,
      MetricValue[]
    >
    useRuntimeStore().dashboard.chartResourcesType = 'cores'
    await flushPromises()
    expect(mockClusterDataPoller.setCallback).toHaveBeenCalledWith('metrics_cores')
    expect(router.push).toHaveBeenCalledWith({
      name: 'dashboard',
      query: {
        resources: 'cores'
      }
    })
    useRuntimeStore().dashboard.chartResourcesType = 'memory'
    await flushPromises()
    expect(mockClusterDataPoller.setCallback).toHaveBeenCalledWith('metrics_memory')
    expect(router.push).toHaveBeenCalledWith({
      name: 'dashboard',
      query: {
        resources: 'memory'
      }
    })
    useRuntimeStore().dashboard.chartResourcesType = 'gpus'
    await flushPromises()
    expect(mockClusterDataPoller.setCallback).toHaveBeenCalledWith('metrics_gpus')
    expect(router.push).toHaveBeenCalledWith({
      name: 'dashboard',
      query: {
        resources: 'gpus'
      }
    })
    useRuntimeStore().dashboard.chartResourcesType = 'nodes'
    await flushPromises()
    expect(mockClusterDataPoller.setCallback).toHaveBeenCalledWith('metrics_nodes')
    expect(router.push).toHaveBeenCalledWith({
      name: 'dashboard',
      query: {}
    })
  })

  test('restores memory resource type from route query', async () => {
    router.setQuery({
      resources: 'memory'
    })

    mount(ChartResourcesHistogram, {
      props: {
        cluster: 'foo'
      }
    })

    await flushPromises()

    expect(useRuntimeStore().dashboard.chartResourcesType).toBe('memory')
    expect(mockClusterDataPoller.setCallback).toHaveBeenCalledWith('metrics_memory')
  })

  test('memory mode formats axis ticks and tooltip values in GB', async () => {
    const wrapper = mount(ChartResourcesHistogram, {
      props: {
        cluster: 'foo'
      }
    })

    useRuntimeStore().dashboard.chartResourcesType = 'memory'
    await flushPromises()

    const canvas = wrapper.get({ ref: 'chartCanvas' }).element as HTMLCanvasElement
    const chart = Chart.getChart(canvas)

    expect(chart).toBeDefined()
    const yTickCallback = chart?.options.scales?.y?.ticks?.callback as
      | ((value: number | string) => string | number | undefined)
      | undefined
    const tooltipCallback = chart?.options.plugins?.tooltip?.callbacks?.label as
      | ((context: { parsed: { y: number }; dataset: { label?: string } }) => string)
      | undefined

    expect(yTickCallback?.(12.5)).toBe('12.5GB')
    expect(tooltipCallback?.({ parsed: { y: 12.5 }, dataset: { label: 'mixed' } })).toBe(
      'mixed: 12.5GB'
    )
  })
})

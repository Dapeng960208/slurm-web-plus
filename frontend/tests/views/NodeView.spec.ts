import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import NodeView from '@/views/NodeView.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import { getMBHumanUnit } from '@/composables/GatewayAPI'
import type { ClusterJob, ClusterNode } from '@/composables/GatewayAPI'
import * as GatewayAPI from '@/composables/GatewayAPI'
import NodeMainState from '@/components/resources/NodeMainState.vue'
import nodeAllocated from '../assets/node-allocated.json'
import jobsNode from '../assets/jobs-node.json'
import { nextTick } from 'vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'

const mockNodeDataPoller = getMockClusterDataPoller<ClusterNode>()
const mockJobsDataPoller = getMockClusterDataPoller<ClusterJob[]>()
const mockGatewayAPI = {
  node_metrics: vi.fn(),
  node_metrics_history: vi.fn()
}

const useClusterDataPoller = vi.hoisted(() => vi.fn())
vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller
}))

describe('NodeView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.restoreAllMocks()
    vi.spyOn(GatewayAPI, 'useGatewayAPI').mockReturnValue(
      mockGatewayAPI as unknown as ReturnType<typeof GatewayAPI.useGatewayAPI>
    )
    mockGatewayAPI.node_metrics.mockResolvedValue({
      cpu_usage: 33.3,
      memory_usage: 45.6,
      disk_usage: 22.1
    })
    mockGatewayAPI.node_metrics_history.mockResolvedValue({
      cpu_usage: [[1748004750000, 33.3]],
      memory_usage: [[1748004750000, 45.6]],
      disk_usage: [[1748004750000, 22.1]]
    })
    useClusterDataPoller.mockReset()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        node_metrics: false
      }
    ]
    mockNodeDataPoller.data.value = undefined
    mockNodeDataPoller.unable.value = false
    mockNodeDataPoller.loaded.value = true
    mockNodeDataPoller.initialLoading.value = false
    mockJobsDataPoller.data.value = undefined
    mockJobsDataPoller.unable.value = false
    mockJobsDataPoller.loaded.value = true
    mockJobsDataPoller.initialLoading.value = false
  })

  test('hides realtime metrics section when node metrics are disabled', async () => {
    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = nodeAllocated
    mockJobsDataPoller.data.value = jobsNode

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      },
      global: {
        stubs: {
          NodeMetricsHistoryChart: true
        }
      }
    })
    await flushPromises()

    expect(wrapper.text()).not.toContain('Realtime Metrics')
    expect(mockGatewayAPI.node_metrics).not.toHaveBeenCalled()
    expect(mockGatewayAPI.node_metrics_history).not.toHaveBeenCalled()
  })

  test('shows realtime metrics and switches history range when enabled', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        node_metrics: true
      }
    ]
    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = nodeAllocated
    mockJobsDataPoller.data.value = jobsNode

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Realtime Metrics')
    expect(wrapper.text()).toContain('Actual:')
    expect(mockGatewayAPI.node_metrics_history).toHaveBeenCalledWith('foo', 'cn1', 'hour')

    const dayButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().trim() === 'day')
    if (!dayButton) {
      throw new Error('day button not found')
    }
    await dayButton.trigger('click')
    await flushPromises()
    expect(mockGatewayAPI.node_metrics_history).toHaveBeenCalledWith('foo', 'cn1', 'day')

    const weekButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().trim() === 'week')
    if (!weekButton) {
      throw new Error('week button not found')
    }
    await weekButton.trigger('click')
    await flushPromises()
    expect(mockGatewayAPI.node_metrics_history).toHaveBeenCalledWith('foo', 'cn1', 'week')
  })

  test('display node details', async () => {
    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = nodeAllocated
    mockJobsDataPoller.data.value = jobsNode
    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })
    await nextTick()
    // Check some node fields
    expect(wrapper.get('dl div#status dd').getComponent(NodeMainState).props()).toStrictEqual({
      status: nodeAllocated.state
    })
    // Check list of jobs has the same number of items than the number of jobs running
    // on the node.
    expect(wrapper.get('dl div#jobs dd').findAll('li').length).toBe(jobsNode.length)
    expect(wrapper.get('dl div#cpu dd').text()).toBe(
      `${nodeAllocated.sockets} x ${nodeAllocated.cores} = ${nodeAllocated.cpus}`
    )
    expect(wrapper.get('dl div#arch dd').text()).toBe(nodeAllocated.architecture)
    expect(wrapper.get('dl div#memory dd').text()).toBe(getMBHumanUnit(nodeAllocated.real_memory))
    expect(wrapper.get('dl div#partitions dd').text()).toBe(nodeAllocated.partitions[0])
  })

  test('rounds CPU percentage correctly', async () => {
    // Force specific values for predictable testing
    const testNode = {
      ...nodeAllocated,
      alloc_cpus: 32, // 32 allocated
      cpus: 64 // 64 total = 50%
    }

    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = testNode
    mockJobsDataPoller.data.value = jobsNode

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })
    await nextTick()

    // CPU: 32/64 = 50%
    const cpuPercentage = wrapper.get('dl div#allocation dd ul li:first-child span').text()
    expect(cpuPercentage).toBe('50%')
  })

  test('rounds Memory percentage correctly', async () => {
    // Force specific values for predictable testing
    const testNode = {
      ...nodeAllocated,
      alloc_memory: 8000, // 8000 MB allocated
      real_memory: 16000 // 16000 MB total = 50%
    }

    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = testNode
    mockJobsDataPoller.data.value = jobsNode

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })
    await nextTick()

    // Memory: 8000/16000 = 50%
    const memoryPercentage = wrapper.get('dl div#allocation dd ul li:nth-child(2) span').text()
    expect(memoryPercentage).toBe('50%')
  })

  test('rounds GPU percentage correctly when available', async () => {
    // Force specific values for predictable testing
    const nodeWithGPU = {
      ...nodeAllocated,
      gres: 'gpu:4', // 4 GPUs available
      gres_used: 'gpu:2' // 2 GPUs used = 50%
    }

    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = nodeWithGPU
    mockJobsDataPoller.data.value = jobsNode

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })
    await nextTick()

    // GPU: 2/4 = 50%
    const gpuPercentage = wrapper.get('dl div#allocation dd ul li:nth-child(3) span').text()
    expect(gpuPercentage).toBe('50%')
  })

  test('rounds to 1 decimal place for non-integer percentages', async () => {
    // Force specific values for predictable testing
    const nodeWithPartialAllocation = {
      ...nodeAllocated,
      alloc_cpus: 15, // 15/64 = 23.4375% -> 23.4%
      cpus: 64,
      alloc_memory: 5000, // 5000/16000 = 31.25% -> 31.3%
      real_memory: 16000
    }

    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.data.value = nodeWithPartialAllocation
    mockJobsDataPoller.data.value = jobsNode

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })
    await nextTick()

    // CPU: 15/64 = 23.4375% -> 23.4%
    const cpuPercentage = wrapper.get('dl div#allocation dd ul li:first-child span').text()
    expect(cpuPercentage).toBe('23.4%')

    // Memory: 5000/16000 = 31.25% -> 31.3%
    const memoryPercentage = wrapper.get('dl div#allocation dd ul li:nth-child(2) span').text()
    expect(memoryPercentage).toBe('31.3%')
  })

  test('renders node skeleton before node data arrives', () => {
    useClusterDataPoller.mockReturnValueOnce(mockNodeDataPoller)
    useClusterDataPoller.mockReturnValueOnce(mockJobsDataPoller)
    mockNodeDataPoller.loaded.value = false
    mockNodeDataPoller.initialLoading.value = true

    const wrapper = mount(NodeView, {
      props: {
        cluster: 'foo',
        nodeName: 'cn1'
      }
    })

    expect(wrapper.text()).toContain('Node cn1')
    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
  })
})

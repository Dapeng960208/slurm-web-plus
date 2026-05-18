import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { ref } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import PartitionView from '@/views/PartitionView.vue'
import { init_plugins } from '../lib/common'

const mockGatewayAPI = {
  jobs_history: vi.fn()
}

const mockPartitions = ref([
  { name: 'normal', node_sets: 'cn[1-4],gpu[1-2]' }
])
const mockNodes = ref([
  {
    alloc_cpus: 64,
    alloc_idle_cpus: 0,
    cores: 32,
    cpus: 64,
    gres: '',
    gres_used: '',
    name: 'cn1',
    partitions: ['normal'],
    real_memory: 131072,
    reason: '',
    sockets: 2,
    state: ['ALLOCATED']
  },
  {
    alloc_cpus: 0,
    alloc_idle_cpus: 64,
    cores: 32,
    cpus: 64,
    gres: 'gpu:h100:4',
    gres_used: '',
    name: 'gpu1',
    partitions: ['normal'],
    real_memory: 131072,
    reason: '',
    sockets: 2,
    state: ['IDLE']
  }
])

vi.mock('@/composables/DataGetter', () => ({
  useClusterDataGetter: (_cluster: string, key: string) =>
    key === 'partitions'
      ? { data: mockPartitions }
      : { data: mockNodes }
}))

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

const historyJob = (
  id: number,
  submitTime: string,
  startTime: string,
  partition = 'normal'
) => ({
  id,
  snapshot_time: startTime,
  job_id: id,
  job_name: `job-${id}`,
  job_state: 'COMPLETED',
  state_reason: 'None',
  user_id: id,
  user_name: `user-${id}`,
  account: 'science',
  group: 'science',
  partition,
  qos: 'normal',
  nodes: 'cn1',
  node_count: 1,
  cpus: 16,
  priority: 0,
  tres_req_str: null,
  tres_per_job: null,
  tres_per_node: null,
  gres_detail: null,
  submit_time: submitTime,
  eligible_time: null,
  start_time: startTime,
  end_time: startTime,
  last_sched_evaluation_time: null,
  time_limit_minutes: 60,
  tres_requested: null,
  tres_allocated: null,
  used_memory_gb: null,
  usage_stats: null,
  used_cpu_cores_avg: null,
  exit_code: '0:0',
  working_directory: null,
  command: null
})

function mountPartitionView() {
  return mount(PartitionView, {
    props: {
      cluster: 'foo',
      partition: 'normal'
    },
    global: {
      stubs: {
        ClusterMainLayout: { template: '<div><slot /></div>' },
        RouterLink: { template: '<a><slot /></a>' },
        DashboardCharts: {
          props: ['cluster', 'metricsQuery', 'routeTargetName'],
          template:
            '<div data-testid="partition-dashboard-props">{{ cluster }}|{{ routeTargetName }}|{{ JSON.stringify(metricsQuery) }}</div>'
        },
        QueueWaitHistoryChart: {
          props: ['series', 'aggregation', 'windowStart', 'windowEnd'],
          template:
            '<div data-testid="partition-queue-wait-chart">{{ aggregation }}|{{ windowStart }}|{{ windowEnd }}|{{ JSON.stringify(series) }}</div>'
        }
      }
    }
  })
}

describe('PartitionView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-nodes', 'view-jobs', 'view-history-jobs']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        persistence: true
      }
    ]
    runtimeStore.dashboard.reset()
    runtimeStore.dashboard.range = 'day'
    mockGatewayAPI.jobs_history.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 500,
      jobs: [
        historyJob(1, '2026-04-24T09:00:00Z', '2026-04-24T09:10:00Z')
      ]
    })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  test('renders partition summary cards without duplicated detail blocks', async () => {
    const wrapper = mountPartitionView()
    await flushPromises()

    expect(wrapper.findAll('.ui-summary-strip .ui-summary-item')).toHaveLength(7)
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Nodes')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Total CPU')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Allocated CPU')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Total Memory')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('GPU')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Allocated Nodes')
    expect(wrapper.find('.ui-summary-strip').text()).toContain('Idle Nodes')
    expect(wrapper.text()).not.toContain('Partition Details')
    expect(wrapper.text()).not.toContain('Node Sets')
    expect(wrapper.text()).not.toContain('cn[1-4]')
    expect(wrapper.text()).not.toContain('gpu[1-2]')
    expect(wrapper.get('[data-testid="partition-dashboard-charts"]').text()).not.toContain(
      'Partition activity'
    )
    expect(wrapper.get('[data-testid="partition-dashboard-charts"]').classes()).toContain(
      'partition-metrics-panel'
    )
    expect(wrapper.get('[data-testid="partition-dashboard-props"]').text()).toContain('foo|partition|')
    expect(wrapper.get('[data-testid="partition-dashboard-props"]').text()).toContain(
      JSON.stringify({ range: 'day', partition: 'normal' })
    )
    expect(wrapper.get('[data-testid="partition-queue-wait-panel"]').text()).toContain(
      'Average Queue Wait'
    )
    expect(wrapper.get('[data-testid="partition-queue-wait-chart"]').text()).toContain('hour|')
    expect(mockGatewayAPI.jobs_history).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        partition: 'normal',
        state: 'COMPLETED',
        sort: 'submit_time',
        order: 'desc',
        page: 1,
        page_size: 500,
        start: expect.stringMatching(/T/),
        end: expect.stringMatching(/T/)
      })
    )
    expect(wrapper.get('[data-testid="partition-queue-wait-chart"]').text()).toContain(
      `[[${new Date('2026-04-24T09:00:00Z').getTime()},600]]`
    )
  })

  test('uses the shared custom metrics window for queue wait history', async () => {
    const runtimeStore = useRuntimeStore()
    runtimeStore.dashboard.setWindow({
      start: '2026-04-24T08:00',
      end: '2026-04-24T12:00'
    })

    const wrapper = mountPartitionView()
    await flushPromises()

    expect(wrapper.get('[data-testid="partition-dashboard-props"]').text()).toContain(
      JSON.stringify({
        start: '2026-04-24T08:00',
        end: '2026-04-24T12:00',
        partition: 'normal'
      })
    )
    expect(mockGatewayAPI.jobs_history).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        partition: 'normal',
        start: new Date('2026-04-24T08:00').toISOString(),
        end: new Date('2026-04-24T12:00').toISOString()
      })
    )
  })

  test('resetting the shared time selector sets an explicit last-hour history window', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-05-18T10:30:45Z'))

    const wrapper = mountPartitionView()
    await flushPromises()
    mockGatewayAPI.jobs_history.mockClear()

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-reset"]').trigger('click')
    await flushPromises()

    expect(wrapper.get('[data-testid="partition-dashboard-props"]').text()).toContain(
      JSON.stringify({
        start: '2026-05-18T17:30',
        end: '2026-05-18T18:30',
        partition: 'normal'
      })
    )
    expect(mockGatewayAPI.jobs_history).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        partition: 'normal',
        start: '2026-05-18T09:30:00.000Z',
        end: '2026-05-18T10:30:00.000Z'
      })
    )
  })

  test('loads all queue wait history pages before aggregating', async () => {
    mockGatewayAPI.jobs_history
      .mockResolvedValueOnce({
        total: 2,
        page: 1,
        page_size: 1,
        jobs: [
          historyJob(1, '2026-04-24T09:00:00Z', '2026-04-24T09:10:00Z')
        ]
      })
      .mockResolvedValueOnce({
        total: 2,
        page: 2,
        page_size: 1,
        jobs: [
          historyJob(2, '2026-04-24T10:00:00Z', '2026-04-24T10:20:00Z')
        ]
      })

    const wrapper = mountPartitionView()
    await flushPromises()

    expect(mockGatewayAPI.jobs_history).toHaveBeenNthCalledWith(
      2,
      'foo',
      expect.objectContaining({
        partition: 'normal',
        page: 2,
        page_size: 500
      })
    )
    expect(wrapper.get('[data-testid="partition-queue-wait-chart"]').text()).toContain(
      `[[${new Date('2026-04-24T09:00:00Z').getTime()},600]`
    )
    expect(wrapper.get('[data-testid="partition-queue-wait-chart"]').text()).toContain(
      `${new Date('2026-04-24T10:00:00Z').getTime()},1200`
    )
  })

  test('shows queue wait empty state without blocking realtime charts when history is unavailable', async () => {
    mockGatewayAPI.jobs_history.mockRejectedValue(new Error('history unavailable'))
    const wrapper = mountPartitionView()
    await flushPromises()

    expect(wrapper.get('[data-testid="partition-dashboard-props"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="partition-queue-wait-panel"]').text()).toContain(
      'Completed job history is currently unavailable for this partition.'
    )
  })

  test('shows queue wait disabled state without calling history when history permission is missing', async () => {
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-nodes', 'view-jobs']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        persistence: true
      }
    ]

    const wrapper = mountPartitionView()
    await flushPromises()

    expect(mockGatewayAPI.jobs_history).not.toHaveBeenCalled()
    expect(wrapper.get('[data-testid="partition-dashboard-props"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="partition-queue-wait-panel"]').text()).toContain(
      'Completed job history is not enabled or not visible for this cluster.'
    )
  })

  test('renders not found state when partition is missing', () => {
    const wrapper = mount(PartitionView, {
      props: {
        cluster: 'foo',
        partition: 'missing'
      },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' }
        }
      }
    })

    expect(wrapper.text()).toContain('Partition missing is not available on this cluster.')
  })
})

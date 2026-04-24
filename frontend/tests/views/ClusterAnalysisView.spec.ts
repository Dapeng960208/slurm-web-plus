import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import ClusterAnalysisView from '@/views/ClusterAnalysisView.vue'
import { init_plugins } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

const mockGatewayAPI = {
  stats: vi.fn(),
  jobs: vi.fn(),
  nodes: vi.fn(),
  metrics_jobs: vi.fn(),
  metrics_cores: vi.fn(),
  metrics_memory: vi.fn(),
  metrics_gpus: vi.fn(),
  jobs_history: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('ClusterAnalysisView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()

    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-stats', 'view-jobs', 'view-nodes', 'view-history-jobs']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        persistence: true
      }
    ]

    mockGatewayAPI.stats.mockResolvedValue({
      resources: {
        nodes: 2,
        cores: 64,
        memory: 262144,
        memory_allocated: 131072,
        memory_available: 131072,
        gpus: 0
      },
      jobs: {
        running: 1,
        total: 3
      }
    })
    mockGatewayAPI.jobs.mockResolvedValue([
      {
        account: 'science',
        cpus: { set: true, infinite: false, number: 32 },
        gres_detail: [],
        job_id: 1,
        job_state: ['RUNNING'],
        node_count: { set: true, infinite: false, number: 1 },
        nodes: 'cn1',
        partition: 'normal',
        priority: { set: true, infinite: false, number: 100 },
        qos: 'normal',
        sockets_per_node: { set: false, infinite: false, number: 0 },
        state_reason: 'None',
        tasks: { set: true, infinite: false, number: 32 },
        tres_per_job: '',
        tres_per_node: '',
        tres_per_socket: '',
        tres_per_task: '',
        user_name: 'alice'
      },
      {
        account: 'science',
        cpus: { set: true, infinite: false, number: 16 },
        gres_detail: [],
        job_id: 2,
        job_state: ['PENDING'],
        node_count: { set: true, infinite: false, number: 1 },
        nodes: '',
        partition: 'normal',
        priority: { set: true, infinite: false, number: 90 },
        qos: 'normal',
        sockets_per_node: { set: false, infinite: false, number: 0 },
        state_reason: 'Resources',
        tasks: { set: true, infinite: false, number: 16 },
        tres_per_job: '',
        tres_per_node: '',
        tres_per_socket: '',
        tres_per_task: '',
        user_name: 'bob'
      }
    ])
    mockGatewayAPI.nodes.mockResolvedValue([
      {
        alloc_cpus: 32,
        alloc_idle_cpus: 0,
        cores: 16,
        cpus: 32,
        gres: '',
        gres_used: '',
        name: 'cn1',
        partitions: ['normal'],
        real_memory: 131072,
        sockets: 2,
        state: ['ALLOCATED'],
        reason: ''
      },
      {
        alloc_cpus: 0,
        alloc_idle_cpus: 32,
        cores: 16,
        cpus: 32,
        gres: '',
        gres_used: '',
        name: 'cn2',
        partitions: ['normal'],
        real_memory: 131072,
        sockets: 2,
        state: ['IDLE'],
        reason: ''
      }
    ])
    mockGatewayAPI.metrics_jobs.mockResolvedValue({
      pending: [[1, 2]],
      running: [[1, 1]]
    })
    mockGatewayAPI.metrics_cores.mockResolvedValue({
      allocated: [[1, 32]],
      mixed: [[1, 0]],
      idle: [[1, 32]]
    })
    mockGatewayAPI.metrics_memory.mockResolvedValue({
      allocated: [[1, 131072]],
      idle: [[1, 131072]]
    })
    mockGatewayAPI.metrics_gpus.mockResolvedValue({
      allocated: [[1, 0]],
      mixed: [[1, 0]],
      idle: [[1, 0]]
    })
    mockGatewayAPI.jobs_history.mockResolvedValue({
      total: 1,
      page: 1,
      page_size: 200,
      jobs: [
        {
          id: 1,
          snapshot_time: '2026-04-24T10:00:00Z',
          job_id: 1,
          job_name: 'job-1',
          job_state: 'COMPLETED',
          state_reason: 'None',
          user_id: 1,
          user_name: 'alice',
          account: 'science',
          group: 'science',
          partition: 'normal',
          qos: 'normal',
          nodes: 'cn1',
          node_count: 1,
          cpus: 16,
          priority: 0,
          tres_req_str: null,
          tres_per_job: null,
          tres_per_node: null,
          gres_detail: null,
          submit_time: '2026-04-24T09:00:00Z',
          eligible_time: null,
          start_time: '2026-04-24T09:10:00Z',
          end_time: '2026-04-24T09:40:00Z',
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
        }
      ]
    })
  })

  test('renders cluster analysis workspace and recommendations', async () => {
    const wrapper = mount(ClusterAnalysisView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          RouterLink: { template: '<a><slot /></a>' }
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Cluster Efficiency')
    expect(wrapper.text()).toContain('Queue Blockers')
    expect(wrapper.text()).toContain('Resources')
    expect(wrapper.text()).toContain('Recommended Actions')
    expect(wrapper.text()).toContain('Keep admission balanced across job sizes')
    expect(mockGatewayAPI.jobs_history).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        state: 'COMPLETED',
        page_size: 200
      })
    )
  })
})

import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import JobHistoryView from '@/views/JobHistoryView.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import { init_plugins } from '../lib/common'
import PanelSkeleton from '@/components/PanelSkeleton.vue'

const mockGatewayAPI = {
  job_history_detail: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('JobHistoryView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
  })

  test('renders unknown status and zero-value fields without throwing', async () => {
    mockGatewayAPI.job_history_detail.mockResolvedValueOnce({
      id: 1,
      snapshot_time: '2026-04-20T10:00:00+00:00',
      job_id: 1234,
      job_name: 'history-job',
      job_state: null,
      state_reason: null,
      user_id: 7,
      user_name: 'alice',
      account: 'science',
      group: 'research',
      partition: 'normal',
      qos: 'debug',
      nodes: 'cn1',
      node_count: 0,
      cpus: 0,
      priority: 0,
      tres_req_str: null,
      tres_per_job: null,
      tres_per_node: null,
      gres_detail: null,
      submit_time: '2026-04-20T09:00:00+00:00',
      eligible_time: null,
      start_time: '2026-04-20T09:05:00+00:00',
      end_time: null,
      last_sched_evaluation_time: null,
      time_limit_minutes: 0,
      tres_requested: null,
      tres_allocated: null,
      used_memory_gb: null,
      exit_code: '0:0',
      working_directory: '/tmp',
      command: 'sleep 1'
    })

    const wrapper = mount(JobHistoryView, {
      props: { cluster: 'foo', id: 1 },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobBackButton: { template: '<button>Back</button>' }
        }
      }
    })

    await flushPromises()

    const badge = wrapper.getComponent(JobStatusBadge)
    expect(badge.props('status')).toStrictEqual(['UNKNOWN'])
    expect(badge.text()).toContain('UNKNOWN')
    expect(wrapper.text()).toContain('0 node, 0 CPU')
    expect(wrapper.text()).toContain('0m')
    expect(wrapper.get('#exit-code').text()).toContain('SUCCESS (0)')
    expect(wrapper.get('#max-memory').text()).toContain('-')
    expect(wrapper.text()).not.toContain('Submit Time')
    expect(wrapper.text()).not.toContain('End Time')
  })

  test('renders completed timeline, structured resources, and max memory', async () => {
    mockGatewayAPI.job_history_detail.mockResolvedValueOnce({
      id: 2,
      snapshot_time: '2026-04-20T10:00:00+00:00',
      job_id: 5678,
      job_name: 'completed-job',
      job_state: 'COMPLETED',
      state_reason: 'None',
      user_id: 7,
      user_name: 'alice',
      account: 'science',
      group: 'research',
      partition: 'normal',
      qos: 'debug',
      nodes: 'cn1',
      node_count: 1,
      cpus: 16,
      priority: 10,
      tres_req_str: 'cpu=16,mem=64G,node=1',
      tres_per_job: null,
      tres_per_node: null,
      gres_detail: null,
      submit_time: '2026-04-20T09:00:00+00:00',
      eligible_time: '2026-04-20T09:01:00+00:00',
      start_time: '2026-04-20T09:05:00+00:00',
      end_time: '2026-04-20T09:30:00+00:00',
      last_sched_evaluation_time: '2026-04-20T09:04:00+00:00',
      time_limit_minutes: 60,
      tres_requested: [
        { type: 'cpu', count: 16, id: 1, name: '' },
        { type: 'mem', count: 65536, id: 2, name: '' },
        { type: 'node', count: 1, id: 4, name: '' }
      ],
      tres_allocated: [
        { type: 'cpu', count: 16, id: 1, name: '' },
        { type: 'mem', count: 65536, id: 2, name: '' },
        { type: 'node', count: 1, id: 4, name: '' }
      ],
      used_memory_gb: 4,
      exit_code: '0:0',
      working_directory: '/tmp',
      command: 'sleep 1'
    })

    const wrapper = mount(JobHistoryView, {
      props: { cluster: 'foo', id: 2 },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobBackButton: { template: '<button>Back</button>' }
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Eligible')
    expect(wrapper.text()).toContain('Scheduling')
    expect(wrapper.text()).toContain('Completed')
    expect(wrapper.text()).toContain('Terminated')
    expect(wrapper.text()).toContain('Requested')
    expect(wrapper.text()).toContain('Allocated')
    expect(wrapper.text()).toContain('Memory: 64GB')
    expect(wrapper.text()).toContain('Max Memory')
    expect(wrapper.text()).toContain('4.00 GB')
    expect(wrapper.get('#step-terminated').text()).not.toContain('\n                  -')
    expect(wrapper.get('#exit-code').text()).toContain('SUCCESS (0)')
    expect(wrapper.text()).not.toContain('Submit Time')
    expect(wrapper.text()).not.toContain('Eligible Time')
    expect(wrapper.text()).not.toContain('Start Time')
    expect(wrapper.text()).not.toContain('End Time')
  })

  test('renders numeric exit code from object payload', async () => {
    mockGatewayAPI.job_history_detail.mockResolvedValueOnce({
      id: 3,
      snapshot_time: '2026-04-20T10:00:00+00:00',
      job_id: 9999,
      job_name: 'failed-job',
      job_state: 'FAILED',
      state_reason: 'NonZeroExitCode',
      user_id: 7,
      user_name: 'alice',
      account: 'science',
      group: 'research',
      partition: 'normal',
      qos: 'debug',
      nodes: 'cn1',
      node_count: 1,
      cpus: 4,
      priority: 10,
      tres_req_str: 'cpu=4,mem=8G,node=1',
      tres_per_job: null,
      tres_per_node: null,
      gres_detail: null,
      submit_time: '2026-04-20T09:00:00+00:00',
      eligible_time: '2026-04-20T09:01:00+00:00',
      start_time: '2026-04-20T09:05:00+00:00',
      end_time: '2026-04-20T09:30:00+00:00',
      last_sched_evaluation_time: '2026-04-20T09:04:00+00:00',
      time_limit_minutes: 60,
      tres_requested: null,
      tres_allocated: null,
      used_memory_gb: null,
      exit_code: {
        return_code: { infinite: false, number: 9, set: true },
        signal: { id: { infinite: false, number: 0, set: true }, name: 'NONE' },
        status: ['FAILED']
      },
      working_directory: '/tmp',
      command: 'false'
    })

    const wrapper = mount(JobHistoryView, {
      props: { cluster: 'foo', id: 3 },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobBackButton: { template: '<button>Back</button>' }
        }
      }
    })

    await flushPromises()

    expect(wrapper.get('#exit-code').text()).toContain('FAILED (9)')
    expect(wrapper.get('#exit-code').text()).not.toContain('[object Object]')
  })

  test('renders signaled exit code from object payload', async () => {
    mockGatewayAPI.job_history_detail.mockResolvedValueOnce({
      id: 4,
      snapshot_time: '2026-04-20T10:00:00+00:00',
      job_id: 10001,
      job_name: 'signaled-job',
      job_state: 'CANCELLED',
      state_reason: 'Signal',
      user_id: 7,
      user_name: 'alice',
      account: 'science',
      group: 'research',
      partition: 'normal',
      qos: 'debug',
      nodes: 'cn1',
      node_count: 1,
      cpus: 4,
      priority: 10,
      tres_req_str: 'cpu=4,mem=8G,node=1',
      tres_per_job: null,
      tres_per_node: null,
      gres_detail: null,
      submit_time: '2026-04-20T09:00:00+00:00',
      eligible_time: '2026-04-20T09:01:00+00:00',
      start_time: '2026-04-20T09:05:00+00:00',
      end_time: '2026-04-20T09:30:00+00:00',
      last_sched_evaluation_time: '2026-04-20T09:04:00+00:00',
      time_limit_minutes: 60,
      tres_requested: null,
      tres_allocated: null,
      used_memory_gb: null,
      exit_code: {
        return_code: { infinite: false, number: 0, set: false },
        signal: { id: { infinite: false, number: 15, set: true }, name: 'TERM' },
        status: ['SIGNALED']
      },
      working_directory: '/tmp',
      command: 'sleep 100'
    })

    const wrapper = mount(JobHistoryView, {
      props: { cluster: 'foo', id: 4 },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobBackButton: { template: '<button>Back</button>' }
        }
      }
    })

    await flushPromises()

    expect(wrapper.get('#exit-code').text()).toContain('SIGNALED (TERM/15)')
  })

  test('renders job history skeleton before the API resolves', () => {
    mockGatewayAPI.job_history_detail.mockReturnValue(new Promise(() => {}))

    const wrapper = mount(JobHistoryView, {
      props: { cluster: 'foo', id: 5 },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobBackButton: { template: '<button>Back</button>' }
        }
      }
    })

    expect(wrapper.text()).toContain('Job 5')
    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
  })
})

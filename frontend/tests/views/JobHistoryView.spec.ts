import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import JobHistoryView from '@/views/JobHistoryView.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import { init_plugins } from '../lib/common'

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
    expect(wrapper.text()).not.toContain('Submit Time')
    expect(wrapper.text()).not.toContain('End Time')
  })

  test('renders completed timeline, structured resources, and used memory', async () => {
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
    expect(wrapper.text()).toContain('4.00 GB')
    expect(wrapper.get('#used-memory').classes()).toContain('bg-emerald-50')
    expect(wrapper.get('#step-terminated').text()).not.toContain('\n                  -')
    expect(wrapper.text()).not.toContain('Submit Time')
    expect(wrapper.text()).not.toContain('Eligible Time')
    expect(wrapper.text()).not.toContain('Start Time')
    expect(wrapper.text()).not.toContain('End Time')
  })
})

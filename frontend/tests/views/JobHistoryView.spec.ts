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
      start_time: '2026-04-20T09:05:00+00:00',
      end_time: null,
      time_limit_minutes: 0,
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
  })
})

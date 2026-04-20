import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import JobsHistoryView from '@/views/JobsHistoryView.vue'
import JobStatusBadge from '@/components/job/JobStatusBadge.vue'
import JobHistoryResources from '@/components/jobs/JobHistoryResources.vue'
import { init_plugins } from '../lib/common'

const mockGatewayAPI = {
  jobs_history: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('JobsHistoryView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
  })

  test('renders split status and zero-value resources from history records', async () => {
    mockGatewayAPI.jobs_history.mockResolvedValueOnce({
      total: 1,
      page: 1,
      page_size: 50,
      jobs: [
        {
          id: 1,
          snapshot_time: '2026-04-20T10:00:00+00:00',
          job_id: 1234,
          job_name: 'history-job',
          job_state: 'RUNNING,COMPLETING',
          state_reason: 'None',
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
        }
      ]
    })

    const wrapper = mount(JobsHistoryView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobsHistoryFiltersPanel: { template: '<div />' },
          JobsHistoryFiltersBar: { template: '<div />' }
        }
      }
    })

    await flushPromises()

    const badge = wrapper.getComponent(JobStatusBadge)
    const resources = wrapper.getComponent(JobHistoryResources)
    expect(badge.props('status')).toStrictEqual(['RUNNING', 'COMPLETING'])
    expect(resources.text()).toContain('0')
    expect(wrapper.text()).toContain('QOS')
    expect(wrapper.text()).toContain('Priority')
    expect(wrapper.text()).toContain('Reason')
    expect(wrapper.text()).toContain('debug')
    expect(wrapper.text()).toContain('-')
  })
})

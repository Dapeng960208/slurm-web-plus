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
    mockGatewayAPI.jobs_history.mockResolvedValue({
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
          usage_stats: null,
          used_cpu_cores_avg: null,
          exit_code: '0:0',
          working_directory: '/tmp',
          command: 'sleep 1'
        }
      ]
    })
  })

  test('renders split status and keeps latest-first default sort', async () => {
    const wrapper = mount(JobsHistoryView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobsHistoryFiltersPanel: { template: '<div />' },
          JobsHistoryFiltersBar: { template: '<div />' },
          JobsHistorySorter: { template: '<div />' }
        }
      }
    })

    await flushPromises()

    const badge = wrapper.getComponent(JobStatusBadge)
    const resources = wrapper.getComponent(JobHistoryResources)
    expect(badge.props('status')).toStrictEqual(['RUNNING', 'COMPLETING'])
    expect(resources.text()).toContain('0')
    expect(wrapper.text()).toContain('Submit Time')
    expect(wrapper.text()).toContain(new Date('2026-04-20T09:00:00+00:00').toLocaleString())
    expect(wrapper.find('th:nth-child(2)').classes()).toContain('min-w-[11rem]')
    expect(wrapper.find('td:nth-child(2)').classes()).toContain('tabular-nums')
    expect(wrapper.text()).toContain('QOS')
    expect(wrapper.text()).toContain('Priority')
    expect(wrapper.text()).toContain('Reason')
    expect(wrapper.text()).toContain('debug')
    expect(wrapper.text()).toContain('-')
    expect(mockGatewayAPI.jobs_history).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        sort: 'submit_time',
        order: 'desc',
        page: 1,
        page_size: 25
      })
    )
  })

  test('restores sort and filters from route query', async () => {
    const router = init_plugins()
    router.setQuery({
      sort: 'user',
      order: 'asc',
      page: '3',
      start: '2026-04-20T10:11:12',
      keyword: 'sleep'
    })

    mount(JobsHistoryView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobsHistoryFiltersPanel: { template: '<div />' },
          JobsHistoryFiltersBar: { template: '<div />' },
          JobsHistorySorter: { template: '<div />' }
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.jobs_history).toHaveBeenCalledWith(
      'foo',
      expect.objectContaining({
        sort: 'user',
        order: 'asc',
        page: 3,
        start: '2026-04-20T10:11:12',
        keyword: 'sleep'
      })
    )
  })

  test('updates route query when sorter changes', async () => {
    const router = init_plugins()
    const wrapper = mount(JobsHistoryView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobsHistoryFiltersPanel: { template: '<div />' },
          JobsHistoryFiltersBar: { template: '<div />' },
          JobsHistorySorter: {
            template: '<button class="sorter" @click="$emit(\'update:sort\', \'user\')" />'
          }
        }
      }
    })

    await flushPromises()
    vi.mocked(router.push).mockClear()

    await wrapper.get('button.sorter').trigger('click')
    await flushPromises()

    expect(router.push).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'jobs-history',
        params: { cluster: 'foo' },
        query: expect.objectContaining({
          sort: 'user'
        })
      })
    )
  })

  test('renders history table skeleton before the API resolves', async () => {
    mockGatewayAPI.jobs_history.mockReturnValue(new Promise(() => {}))

    const wrapper = mount(JobsHistoryView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          JobsHistoryFiltersPanel: { template: '<div />' },
          JobsHistoryFiltersBar: { template: '<div />' },
          JobsHistorySorter: { template: '<div />' }
        }
      }
    })

    expect(wrapper.text()).toContain('Jobs History')
    expect(wrapper.findAll('[data-testid="table-skeleton-row"]').length).toBeGreaterThan(0)
  })
})

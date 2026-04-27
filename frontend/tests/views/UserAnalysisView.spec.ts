import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserAnalysisView from '@/views/UserAnalysisView.vue'
import { init_plugins } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import * as GatewayAPI from '@/composables/GatewayAPI'

const mockGatewayAPI = {
  user_metrics_history: vi.fn(),
  user_tools_analysis: vi.fn()
}

describe('UserAnalysisView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.restoreAllMocks()
    vi.spyOn(GatewayAPI, 'useGatewayAPI').mockReturnValue(
      mockGatewayAPI as unknown as ReturnType<typeof GatewayAPI.useGatewayAPI>
    )
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-jobs'],
          rules: ['user/analysis:view:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        user_metrics: true
      }
    ]
    mockGatewayAPI.user_tools_analysis.mockResolvedValue({
      username: 'root',
      profile: {
        fullname: 'Root User',
        groups: ['admins', 'science'],
        ldap_synced_at: '2026-04-24T11:55:00Z',
        ldap_found: true
      },
      generated_at: '2026-04-24T12:00:00Z',
      window: {
        start: '2026-04-24T00:00:00Z',
        end: '2026-04-24T12:00:00Z'
      },
      totals: {
        completed_jobs: 12,
        active_tools: 3,
        avg_max_memory_mb: 8192,
        avg_cpu_cores: 7.5,
        avg_runtime_seconds: 5400,
        busiest_tool: 'bwa',
        busiest_tool_jobs: 8
      },
      tool_breakdown: [
        {
          tool: 'bwa',
          jobs: 8,
          avg_max_memory_mb: 9216,
          avg_cpu_cores: 8,
          avg_runtime_seconds: 7200
        }
      ]
    })
    mockGatewayAPI.user_metrics_history.mockResolvedValue({
      window: {
        start: '2026-04-24T00:00:00Z',
        end: '2026-04-24T12:00:00Z'
      },
      totals: {
        submitted_jobs: 17,
        completed_jobs: 12
      },
      submissions: [[1745488800000, 2]],
      completions: [[1745488800000, 1]]
    })
  })

  test('loads analytics panels', async () => {
    const wrapper = mount(UserAnalysisView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserSubmissionHistoryChart: true,
          UserToolAnalysisChart: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('User Analysis')
    expect(wrapper.text()).toContain('Submission Activity')
    expect(wrapper.text()).toContain('Tool Analysis')
    expect(mockGatewayAPI.user_tools_analysis).toHaveBeenCalledWith(
      'foo',
      'root',
      expect.objectContaining({
        start: expect.stringMatching(/T/),
        end: expect.stringMatching(/T/)
      })
    )
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith(
      'foo',
      'root',
      expect.objectContaining({
        start: expect.stringMatching(/T/),
        end: expect.stringMatching(/T/)
      })
    )
  })

  test('shows disabled message when analytics is unavailable', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        permissions: {
          roles: [],
          actions: ['view-jobs'],
          rules: ['user/analysis:view:*']
        },
        user_metrics: false
      }
    ]

    const wrapper = mount(UserAnalysisView, {
      props: {
        cluster: 'foo',
        user: 'root'
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('User analytics is not enabled for this cluster.')
  })
})

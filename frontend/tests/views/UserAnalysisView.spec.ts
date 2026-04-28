import { afterEach, describe, test, expect, beforeEach, vi } from 'vitest'
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

  afterEach(() => {
    vi.useRealTimers()
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
    expect(wrapper.text()).toContain('Analysis Window')
    expect(wrapper.text()).toContain('Root User')
    expect(wrapper.text()).toContain('Groups: admins, science')
    expect(wrapper.text()).not.toContain('Username')
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

  test('applies analytics time range from the compact dialog', async () => {
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
    mockGatewayAPI.user_tools_analysis.mockClear()
    mockGatewayAPI.user_metrics_history.mockClear()

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-start"]').setValue('2026-04-24T08:30')
    await wrapper.get('[data-testid="metric-range-end"]').setValue('2026-04-24T11:45')
    await wrapper.get('[data-testid="metric-range-apply"]').trigger('click')
    await flushPromises()

    const expectedWindow = {
      start: new Date('2026-04-24T08:30').toISOString(),
      end: new Date('2026-04-24T11:45').toISOString()
    }
    expect(mockGatewayAPI.user_tools_analysis).toHaveBeenCalledWith('foo', 'root', expectedWindow)
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', expectedWindow)
  })

  test('applies predefined analytics windows from the compact dialog', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-24T12:30'))
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
    mockGatewayAPI.user_tools_analysis.mockClear()
    mockGatewayAPI.user_metrics_history.mockClear()

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-quick-15d"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-apply"]').trigger('click')
    await flushPromises()

    const expectedWindow = {
      start: new Date('2026-04-09T12:30').toISOString(),
      end: new Date('2026-04-24T12:30').toISOString()
    }
    expect(mockGatewayAPI.user_tools_analysis).toHaveBeenCalledWith('foo', 'root', expectedWindow)
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', expectedWindow)
  })

  test('applies the seven day analytics window and keeps activity data visible', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-24T12:30'))
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
    mockGatewayAPI.user_tools_analysis.mockClear()
    mockGatewayAPI.user_metrics_history.mockClear()

    await wrapper.get('[data-testid="metric-range-custom-button"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-quick-7d"]').trigger('click')
    await wrapper.get('[data-testid="metric-range-apply"]').trigger('click')
    await flushPromises()

    const expectedWindow = {
      start: new Date('2026-04-17T12:30').toISOString(),
      end: new Date('2026-04-24T12:30').toISOString()
    }
    expect(mockGatewayAPI.user_tools_analysis).toHaveBeenCalledWith('foo', 'root', expectedWindow)
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', expectedWindow)
    expect(wrapper.text()).toContain('Submitted in Range')
    expect(wrapper.text()).toContain('17')
    expect(wrapper.text()).not.toContain('No submission or completion history is available for this range.')
  })
})

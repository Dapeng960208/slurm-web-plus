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

let router: ReturnType<typeof init_plugins>

describe('UserAnalysisView.vue', () => {
  beforeEach(() => {
    router = init_plugins()
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
        avg_memory_gb: 8,
        max_memory_gb: 12,
        median_memory_gb: 7.5,
        avg_cpu_cores: 7.5,
        avg_runtime_seconds: 5400,
        busiest_tool: 'bwa',
        busiest_tool_jobs: 8
      },
      tool_breakdown: [
        {
          tool: 'bwa',
          jobs: 8,
          avg_memory_gb: 8,
          max_memory_gb: 9,
          median_memory_gb: 8,
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
          UserSubmissionHistoryChart: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('User Analysis')
    expect(wrapper.text()).toContain('Submission Activity')
    expect(wrapper.text()).toContain('Completed Job Tool Analysis')
    expect(wrapper.text()).toContain('Avg Memory')
    expect(wrapper.text()).toContain('Avg CPU')
    expect(wrapper.text()).toContain('bwa')
    expect(wrapper.text()).not.toContain('Top Tools')
    expect(wrapper.text()).not.toContain('Memory and Volume')
    expect(wrapper.text()).not.toContain('Resource Roll-up')
    expect(wrapper.text()).toContain('Analysis Window')
    expect(wrapper.text()).toContain('One shared time window for activity, usage and completed tool analysis.')
    expect(wrapper.text()).toContain('LDAP profile available')
    expect(wrapper.text()).toContain('Updated')
    expect(wrapper.text()).not.toContain('Username')
    expect(wrapper.find('.user-analytics-window-control').exists()).toBe(true)
    expect(wrapper.find('.user-analytics-main-grid').exists()).toBe(true)
    expect(wrapper.findAll('.user-analytics-metric-card')).toHaveLength(4)
    expect(wrapper.find('.ui-scroll-region').classes()).toEqual(
      expect.arrayContaining(['ui-scroll-region', 'min-h-0', 'flex-1', 'pr-1'])
    )
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

  test('loads analytics immediately on refresh when route already has a time window', async () => {
    await router.push({
      query: {
        start: '2026-04-24T08:30',
        end: '2026-04-24T11:45'
      }
    })

    mount(UserAnalysisView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserSubmissionHistoryChart: true
        }
      }
    })

    await flushPromises()

    const expectedWindow = {
      start: new Date('2026-04-24T08:30').toISOString(),
      end: new Date('2026-04-24T11:45').toISOString()
    }
    expect(mockGatewayAPI.user_tools_analysis).toHaveBeenCalledWith('foo', 'root', expectedWindow)
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', expectedWindow)
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
          UserSubmissionHistoryChart: true
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
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-04-24T12:30'))
    const wrapper = mount(UserAnalysisView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserSubmissionHistoryChart: true
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
    vi.useFakeTimers({ toFake: ['Date'] })
    vi.setSystemTime(new Date('2026-04-24T12:30'))
    const wrapper = mount(UserAnalysisView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserSubmissionHistoryChart: true
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

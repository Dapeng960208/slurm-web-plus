import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { RouterLink } from 'vue-router'
import UserView from '@/views/UserView.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import associations from '../assets/associations.json'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import * as GatewayAPI from '@/composables/GatewayAPI'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterAssociation[]>()
const mockGatewayAPI = {
  user_metrics_history: vi.fn(),
  user_activity_summary: vi.fn()
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

describe('UserView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.restoreAllMocks()
    vi.spyOn(GatewayAPI, 'useGatewayAPI').mockReturnValue(
      mockGatewayAPI as unknown as ReturnType<typeof GatewayAPI.useGatewayAPI>
    )
    mockGatewayAPI.user_activity_summary.mockResolvedValue({
      username: 'root',
      profile: {
        fullname: 'Root User',
        groups: ['admins', 'science'],
        ldap_synced_at: '2026-04-24T11:55:00Z',
        ldap_found: true
      },
      generated_at: '2026-04-24T12:00:00Z',
      totals: {
        submitted_jobs_today: 17,
        completed_jobs_today: 12,
        active_tools: 3,
        latest_submissions_per_minute: 2,
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
        },
        {
          tool: 'samtools',
          jobs: 3,
          avg_max_memory_mb: 4096,
          avg_cpu_cores: 4,
          avg_runtime_seconds: 1800
        }
      ]
    })
    mockGatewayAPI.user_metrics_history.mockResolvedValue({
      submissions: [[1745488800000, 2]]
    })
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true,
        user_metrics: false
      }
    ]
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = false
  })

  test('displays user details', async () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      }
    })
    await flushPromises()

    // Back to accounts button
    const buttons = wrapper.findAll('button')
    const backButton = buttons.find((btn) => btn.text().includes('Back to accounts'))
    expect(backButton).toBeDefined()

    // User heading
    const userHeading = wrapper.get('div#user-heading')
    expect(userHeading.text()).toContain('root')

    // root is associated with root account only
    expect(userHeading.text()).toContain('1')
    expect(userHeading.text()).toContain('account associated')

    // View jobs link
    const viewJobsLink = userHeading.getComponent(RouterLink)
    expect(viewJobsLink.props('to')).toEqual({
      name: 'jobs',
      params: { cluster: 'foo' },
      query: { users: 'root' }
    })

    // User associations table
    const userAssociationsTable = wrapper.get('table')

    // Column headers
    const columnHeaders = userAssociationsTable.get('thead').findAll('th')
    expect(columnHeaders[0].text()).toBe('Account')
    expect(columnHeaders[1].text()).toBe('Job limits')
    expect(columnHeaders[2].text()).toBe('Resource limits')
    expect(columnHeaders[3].text()).toBe('Time limits')
    expect(columnHeaders[4].text()).toBe('QOS')
    expect(userAssociationsTable.findAll('tbody tr').length).toBeGreaterThan(0)

    // Check presence of breadcrumbs
    const breadcrumbs = userAssociationsTable.findAllComponents(AccountBreadcrumb)
    expect(breadcrumbs.length).toBeGreaterThan(0)
    expect(mockGatewayAPI.user_activity_summary).not.toHaveBeenCalled()
    expect(mockGatewayAPI.user_metrics_history).not.toHaveBeenCalled()
  })

  test('shows user skeleton when data is not loaded', () => {
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = true

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      }
    })

    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
    expect(wrapper.get('#user-heading').text()).toContain('root')
  })

  test('shows error alert when unable to retrieve associations', () => {
    mockClusterDataPoller.unable.value = true
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      }
    })

    const errorAlert = wrapper.findComponent(ErrorAlert)
    expect(errorAlert.exists()).toBe(true)
    expect(errorAlert.text()).toContain('Unable to retrieve associations for cluster')
    expect(errorAlert.text()).toContain('foo')
  })

  test('shows info alert when user has no associations', () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = []

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'nonexistent'
      }
    })

    const infoAlert = wrapper.findComponent(InfoAlert)
    expect(infoAlert.exists()).toBe(true)
    expect(infoAlert.text()).toContain('User nonexistent has no associations on this cluster')
  })

  test('shows metrics content even when the user has no associations', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        user_metrics: true
      }
    ]
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = []

    const wrapper = mount(UserView, {
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

    expect(wrapper.text()).toContain('User root has no associations on this cluster')
    expect(wrapper.text()).toContain('Root User')
    expect(wrapper.text()).toContain('LDAP Groups')
    expect(wrapper.text()).toContain('Submission Activity')
    expect(wrapper.text()).toContain('Tool Analysis')
    expect(wrapper.text()).not.toContain('Account Associations')
    expect(mockGatewayAPI.user_activity_summary).toHaveBeenCalledWith('foo', 'root')
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', 'hour')
  })

  test('shows user metrics when feature is enabled and switches ranges', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        user_metrics: true
      }
    ]
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(UserView, {
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

    expect(wrapper.text()).toContain('Submission Activity')
    expect(wrapper.text()).toContain('Tool Analysis')
    expect(wrapper.text()).toContain('Root User')
    expect(wrapper.text()).toContain('admins, science')
    expect(wrapper.text()).toContain('Metrics Updated')
    expect(wrapper.text()).toContain('Submitted Today')
    expect(wrapper.text()).toContain('17')
    expect(wrapper.text()).toContain('bwa')
    expect(mockGatewayAPI.user_activity_summary).toHaveBeenCalledWith('foo', 'root')
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', 'hour')

    const dayButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().trim() === 'day')
    if (!dayButton) {
      throw new Error('day button not found')
    }
    await dayButton.trigger('click')
    await flushPromises()
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', 'day')

    const weekButton = wrapper
      .findAll('button[type="button"]')
      .find((button) => button.text().trim() === 'week')
    if (!weekButton) {
      throw new Error('week button not found')
    }
    await weekButton.trigger('click')
    await flushPromises()
    expect(mockGatewayAPI.user_metrics_history).toHaveBeenCalledWith('foo', 'root', 'week')
  })

  test('gracefully degrades when user metrics request fails', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        user_metrics: true
      }
    ]
    mockGatewayAPI.user_activity_summary.mockRejectedValueOnce(new Error('disabled'))
    mockGatewayAPI.user_metrics_history.mockRejectedValueOnce(new Error('disabled'))
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('User activity statistics are not available for this cluster')
    expect(wrapper.text()).toContain('Account Associations')
    expect(wrapper.findComponent(AccountBreadcrumb).exists()).toBe(true)
  })

  test('shows empty history and empty tool states when user metrics contain no data', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        user_metrics: true
      }
    ]
    mockGatewayAPI.user_activity_summary.mockResolvedValueOnce({
      username: 'root',
      generated_at: '2026-04-24T12:00:00Z',
      totals: {
        submitted_jobs_today: 0,
        completed_jobs_today: 0,
        active_tools: 0,
        latest_submissions_per_minute: 0,
        avg_max_memory_mb: null,
        avg_cpu_cores: null,
        avg_runtime_seconds: null,
        busiest_tool: null,
        busiest_tool_jobs: 0
      },
      tool_breakdown: []
    })
    mockGatewayAPI.user_metrics_history.mockResolvedValueOnce({
      submissions: []
    })
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('No submission history is available for this range.')
    expect(wrapper.text()).toContain('No tool activity has been recorded for this user yet.')
    expect(wrapper.text()).toContain('Submitted Today')
    expect(wrapper.text()).toContain('0')
  })
})

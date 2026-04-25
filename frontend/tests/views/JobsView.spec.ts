import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'
import JobsView from '@/views/JobsView.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import type { ClusterJob } from '@/composables/GatewayAPI'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import TableSkeletonRows from '@/components/TableSkeletonRows.vue'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterJob[]>()
const mockGatewayAPI = {
  submit_job: vi.fn(),
  update_job: vi.fn(),
  cancel_job: vi.fn()
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

function buildJob(jobId: number, userName: string, state: string[] = ['RUNNING']): ClusterJob {
  return {
    account: 'science',
    cpus: { set: true, infinite: false, number: 16 },
    gres_detail: [],
    job_id: jobId,
    job_state: state,
    node_count: { set: true, infinite: false, number: 1 },
    nodes: state.includes('PENDING') ? '' : 'cn1',
    partition: 'normal',
    priority: { set: true, infinite: false, number: 100 },
    qos: 'normal',
    sockets_per_node: { set: false, infinite: false, number: 0 },
    state_reason: state.includes('PENDING') ? 'Resources' : 'None',
    tasks: { set: true, infinite: false, number: 16 },
    tres_per_job: '',
    tres_per_node: '',
    tres_per_socket: '',
    tres_per_task: '',
    user_name: userName
  }
}

describe('JobsView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['jobs:view:*'] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    useAuthStore().username = 'alice'
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
  })

  test('displays jobs with the actions column and no batch controls', () => {
    mockClusterDataPoller.data.value = [buildJob(101, 'alice'), buildJob(202, 'bob', ['PENDING'])]

    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      }
    })

    const table = wrapper.find('main table')
    expect(table.exists()).toBeTruthy()
    const columns = table.findAll('thead th')
    expect(columns.length).toBe(9)
    expect(columns[0].text()).toBe('#ID')
    expect(columns[1].text()).toBe('State')
    expect(columns[2].text()).toBe('User (account)')
    expect(columns[3].text()).toBe('Resources')
    expect(columns[4].text()).toBe('Partition')
    expect(columns[5].text()).toBe('QOS')
    expect(columns[6].text()).toBe('Priority')
    expect(columns[7].text()).toBe('Reason')
    expect(columns[8].text()).toBe('Actions')
    expect(table.findAll('tbody tr')).toHaveLength(2)
    expect(wrapper.text()).not.toContain('Batch cancel')
    expect(wrapper.text()).not.toContain('Bulk')
  })

  test('shows error alert when unable to retrieve jobs', () => {
    mockClusterDataPoller.unable.value = true
    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(ErrorAlert).text()).toBe('Unable to retrieve jobs from cluster foo')
    expect(wrapper.find('main table').exists()).toBeFalsy()
  })

  test('shows info alert when no job exists', () => {
    mockClusterDataPoller.data.value = []
    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(InfoAlert).text()).toBe('No jobs found on cluster foo')
    expect(wrapper.find('main table').exists()).toBeFalsy()
  })

  test('shows table skeleton while jobs are loading', () => {
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = true

    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      }
    })

    expect(wrapper.find('main table').exists()).toBeTruthy()
    expect(wrapper.findComponent(TableSkeletonRows).exists()).toBe(true)
    expect(wrapper.findAll('[data-testid="table-skeleton-row"]').length).toBeGreaterThan(0)
  })

  test('shows edit and cancel only for own jobs when a regular user has self-scoped job actions', () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: ['view-own-jobs', 'edit-own-jobs', 'cancel-own-jobs'],
          rules: []
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    useAuthStore().username = 'alice'
    mockClusterDataPoller.data.value = [buildJob(101, 'alice'), buildJob(202, 'bob', ['PENDING'])]

    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      }
    })

    const rows = wrapper.findAll('tbody tr')
    expect(rows).toHaveLength(2)
    expect(rows[0].text()).toContain('Edit')
    expect(rows[0].text()).toContain('Cancel')
    expect(rows[1].text()).not.toContain('Edit')
    expect(rows[1].text()).not.toContain('Cancel')
    expect(wrapper.text()).not.toContain('Batch cancel')
  })
})

import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'
import JobsView from '@/views/JobsView.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { i18n } from '@/plugins/i18n'
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
    document.body.innerHTML = ''
  })

  test('displays jobs with the actions column and no batch controls', () => {
    mockClusterDataPoller.data.value = [buildJob(101, 'alice'), buildJob(202, 'bob', ['PENDING'])]

    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      },
      global: {
        stubs: {
          Dialog: { template: '<div><slot /></div>' },
          DialogPanel: { template: '<div><slot /></div>' },
          DialogTitle: { template: '<div><slot /></div>' },
          TransitionChild: { template: '<div><slot /></div>' },
          TransitionRoot: { template: '<div><slot /></div>' }
        }
      }
    })

    const table = wrapper.find('main table')
    expect(table.exists()).toBeTruthy()
    expect(wrapper.get('main').classes()).toEqual(
      expect.arrayContaining(['ui-content-scroll', 'flex-1', 'min-h-0', 'pb-3', 'lg:pb-4'])
    )
    expect(wrapper.find('.ui-table-scroll').exists()).toBe(true)
    expect(wrapper.find('.ui-results-dock .ui-results-pagination').exists()).toBe(true)
    expect(wrapper.find('.ui-table-shell .ui-results-pagination').exists()).toBe(false)
    expect(wrapper.find('.ui-results-workspace').classes()).toEqual(
      expect.arrayContaining(['ui-results-workspace'])
    )
    const columns = table.findAll('thead th')
    expect(columns.length).toBe(9)
    expect(columns[0].text()).toBe('#ID')
    expect(columns[1].text()).toBe(i18n.global.t('tables.jobs.columns.state'))
    expect(columns[2].text()).toBe(i18n.global.t('tables.jobs.columns.userAccount'))
    expect(columns[3].text()).toBe(i18n.global.t('tables.jobs.columns.resources'))
    expect(columns[4].text()).toBe(i18n.global.t('tables.jobs.columns.partition'))
    expect(columns[5].text()).toBe(i18n.global.t('tables.jobs.columns.qos'))
    expect(columns[6].text()).toBe(i18n.global.t('tables.jobs.columns.priority'))
    expect(columns[7].text()).toBe(i18n.global.t('tables.jobs.columns.reason'))
    expect(columns[8].text()).toBe(i18n.global.t('tables.jobs.columns.actions'))
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
    expect(wrapper.getComponent(ErrorAlert).text()).toBe(
      i18n.global.t('pages.jobs.unableToRetrieve', { cluster: 'foo' })
    )
    expect(wrapper.find('main table').exists()).toBeFalsy()
  })

  test('shows info alert when no job exists', () => {
    mockClusterDataPoller.data.value = []
    const wrapper = mount(JobsView, {
      props: {
        cluster: 'foo'
      }
    })
    expect(wrapper.getComponent(InfoAlert).text()).toBe(
      i18n.global.t('pages.jobs.noJobs', { cluster: 'foo' })
    )
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

  test('shows edit and cancel only for own jobs when a regular user has self-scoped job rules', () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['jobs:view:self', 'jobs:edit:self', 'jobs:delete:self']
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
    expect(rows[0].text()).toContain(i18n.global.t('pages.jobs.actions.edit'))
    expect(rows[0].text()).toContain(i18n.global.t('pages.jobs.actions.cancel'))
    expect(rows[1].text()).not.toContain(i18n.global.t('pages.jobs.actions.edit'))
    expect(rows[1].text()).not.toContain(i18n.global.t('pages.jobs.actions.cancel'))
    expect(wrapper.text()).not.toContain('Batch cancel')
  })

  test('submits memory per CPU when editing a job', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['jobs:view:*', 'jobs:edit:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockGatewayAPI.update_job.mockResolvedValue({ operation: 'jobs.update' })
    mockClusterDataPoller.data.value = [buildJob(101, 'alice')]

    const wrapper = mount(JobsView, {
      attachTo: document.body,
      props: {
        cluster: 'foo'
      }
    })

    await wrapper
      .findAll('tbody button')
      .find((button) => button.text() === i18n.global.t('pages.jobs.actions.edit'))!
      .trigger('click')
    await flushPromises()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.jobs.dialogs.edit.title')!
      .vm.$emit('submit', {
        partition: 'normal',
        qos: 'normal',
        priority: '100',
        memory_per_cpu_mb: '2048',
        time_limit: '',
        comment: ''
      })
    await flushPromises()

    expect(mockGatewayAPI.update_job).toHaveBeenCalledWith(
      'foo',
      101,
      expect.objectContaining({
        memory_per_cpu: { set: true, infinite: false, number: 2048 }
      })
    )
    wrapper.unmount()
  })
})

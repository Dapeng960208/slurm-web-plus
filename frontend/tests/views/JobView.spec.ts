import { nextTick } from 'vue'
import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'
import JobView from '@/views/JobView.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { i18n } from '@/plugins/i18n'
import type { ClusterIndividualJob } from '@/composables/GatewayAPI'
import jobRunning from '../assets/job-running.json'
import type { RouterMock } from 'vue-router-mock'
import PanelSkeleton from '@/components/PanelSkeleton.vue'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterIndividualJob>()
const mockGatewayAPI = {
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

let router: RouterMock

describe('JobView.vue', () => {
  beforeEach(() => {
    router = init_plugins()
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

  test('displays job details', () => {
    mockClusterDataPoller.data.value = jobRunning
    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
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

    const backButton = wrapper.findComponent(JobBackButton)
    expect(backButton.exists()).toBe(true)
    expect(backButton.props('cluster')).toBe('foo')
    expect(backButton.text()).toBe('Back to jobs')

    const summary = wrapper.get('[data-testid="detail-summary-strip"]')
    const details = wrapper.get('[data-testid="job-detail-list"]')
    const links = summary.findAllComponents({ name: 'RouterLink' })
    const userLink = links[0]
    const partitionLink = links[1]

    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.user'))
    expect(userLink.props('to')).toEqual({
      name: 'user',
      params: { cluster: 'foo', user: jobRunning.user }
    })
    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.account'))
    expect(summary.text()).toContain('-')
    expect(links).toHaveLength(2)
    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.partition'))
    expect(partitionLink.props('to')).toEqual({
      name: 'partition',
      params: { cluster: 'foo', partition: jobRunning.partition }
    })
    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.nodes'))
    expect(summary.text()).toContain(jobRunning.nodes)
    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.exitCode'))
    expect(summary.text()).toContain('SUCCESS (0)')
    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.requested'))
    expect(summary.text()).toContain(i18n.global.t('pages.job.summary.allocated'))

    const detailSections = wrapper.get('[data-testid="job-detail-sections"]')
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.sections.identityTitle'))
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.sections.payloadTitle'))
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.fields.workingDirectory'))
    const detailPartitionLinks = detailSections
      .findAllComponents({ name: 'RouterLink' })
      .filter((link) =>
        JSON.stringify(link.props('to')) ===
        JSON.stringify({
          name: 'partition',
          params: { cluster: 'foo', partition: jobRunning.partition }
        })
      )
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.fields.partition'))
    expect(detailPartitionLinks).toHaveLength(1)
    expect(wrapper.get('#workdir').text()).toContain(jobRunning.working_directory)
    expect(wrapper.get('#submit-line pre').text()).toContain(jobRunning.submit_line)
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.fields.requested'))
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.fields.allocated'))
    expect(detailSections.text()).toContain(i18n.global.t('pages.job.fields.exitCode'))
    expect(wrapper.find('.ui-scroll-region').classes()).toEqual(
      expect.arrayContaining(['ui-scroll-region', 'min-h-0', 'flex-1', 'pr-1'])
    )
  })

  test('highlights a job field from the route hash', async () => {
    await router.setHash('#workdir')
    mockClusterDataPoller.data.value = jobRunning
    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
      }
    })
    await nextTick()

    expect(wrapper.get('#workdir').text()).toContain(jobRunning.working_directory)
    expect(wrapper.get('#workdir').classes()).toContain('bg-[rgba(182,232,44,0.16)]')
    expect(wrapper.get('#script').classes()).not.toContain('bg-[rgba(182,232,44,0.16)]')
  })

  test('renders job skeleton before data arrives', () => {
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = true

    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
      }
    })

    expect(wrapper.text()).toContain(i18n.global.t('pages.job.title', { jobId: 1234 }))
    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
  })

  test('shows edit and cancel for the owner with self-scoped job rules', () => {
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
    mockClusterDataPoller.data.value = {
      ...jobRunning,
      user: 'alice'
    }

    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
      }
    })

    expect(wrapper.text()).toContain(i18n.global.t('pages.job.actions.edit'))
    expect(wrapper.text()).toContain(i18n.global.t('pages.job.actions.cancel'))
  })

  test('submits memory per CPU when editing the job', async () => {
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
    mockClusterDataPoller.data.value = jobRunning

    const wrapper = mount(JobView, {
      attachTo: document.body,
      props: {
        cluster: 'foo',
        id: 1234
      }
    })

    await wrapper
      .findAll('button')
      .find((button) => button.text() === i18n.global.t('pages.job.actions.edit'))!
      .trigger('click')
    await nextTick()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.job.dialogs.edit.title')!
      .vm.$emit('submit', {
        partition: 'normal',
        qos: 'normal',
        priority: '',
        memory_per_cpu_mb: '4096',
        time_limit: '',
        comment: ''
      })
    await nextTick()

    expect(mockGatewayAPI.update_job).toHaveBeenCalledWith(
      'foo',
      1234,
      expect.objectContaining({
        memory_per_cpu: { set: true, infinite: false, number: 4096 }
      })
    )
    wrapper.unmount()
  })

  test('hides edit and cancel for another users job under self scope', () => {
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
    mockClusterDataPoller.data.value = {
      ...jobRunning,
      user: 'bob'
    }

    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
      }
    })

    expect(wrapper.text()).not.toContain(i18n.global.t('pages.job.actions.edit'))
    expect(wrapper.text()).not.toContain(i18n.global.t('pages.job.actions.cancel'))
  })
})

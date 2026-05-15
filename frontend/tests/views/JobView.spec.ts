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

  test('displays job details as a continuous detail list', () => {
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

    expect(wrapper.find('[data-testid="detail-summary-strip"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="job-detail-grid"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="job-detail-long-fields"]').exists()).toBe(false)
    expect(wrapper.find('.ui-detail-grid').exists()).toBe(false)
    expect(wrapper.find('.ui-detail-long-stack').exists()).toBe(false)

    const detailList = wrapper.get('[data-testid="job-detail-list"]')
    expect(detailList.classes()).toContain('ui-detail-list')
    expect(detailList.findAll('.ui-detail-row').length).toBeGreaterThan(8)
    expect(detailList.text()).toContain(i18n.global.t('pages.job.fields.partition'))
    expect(detailList.text()).toContain(i18n.global.t('pages.job.fields.workingDirectory'))
    expect(detailList.text()).toContain(i18n.global.t('pages.job.fields.requested'))
    expect(detailList.text()).toContain(i18n.global.t('pages.job.fields.allocated'))
    expect(detailList.text()).toContain(i18n.global.t('pages.job.fields.exitCode'))
    expect(detailList.text()).not.toContain(i18n.global.t('pages.job.sections.identityTitle'))
    expect(detailList.text()).not.toContain(i18n.global.t('pages.job.panels.detailedTitle'))

    const userLink = detailList
      .findAllComponents({ name: 'RouterLink' })
      .find((link) => JSON.stringify(link.props('to')) === JSON.stringify({
        name: 'user',
        params: { cluster: 'foo', user: jobRunning.user }
      }))
    expect(userLink).toBeDefined()

    expect(wrapper.get('#workdir').text()).toContain(jobRunning.working_directory)
    expect(wrapper.get('#submit-line pre').text()).toContain(jobRunning.submit_line)
    expect(wrapper.get('#script').text()).toContain(jobRunning.script)
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
    expect(wrapper.get('#workdir').classes()).toContain('ui-detail-item-highlight')
    expect(wrapper.get('#script').classes()).not.toContain('ui-detail-item-highlight')
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

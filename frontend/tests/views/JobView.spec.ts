import { nextTick } from 'vue'
import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { useRuntimeStore } from '@/stores/runtime'
import { useAuthStore } from '@/stores/auth'
import JobView from '@/views/JobView.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
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
  })

  test('displays job details', () => {
    mockClusterDataPoller.data.value = jobRunning
    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
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

    expect(summary.text()).toContain('User')
    expect(userLink.props('to')).toEqual({
      name: 'user',
      params: { cluster: 'foo', user: jobRunning.user }
    })
    expect(summary.text()).toContain('Account')
    expect(summary.text()).toContain('-')
    expect(links).toHaveLength(1)
    expect(summary.text()).toContain('Partition')
    expect(summary.text()).toContain(jobRunning.partition)
    expect(summary.text()).toContain('Nodes')
    expect(summary.text()).toContain(jobRunning.nodes)
    expect(summary.text()).toContain('Exit Code')
    expect(summary.text()).toContain('SUCCESS (0)')
    expect(summary.text()).toContain('Requested')
    expect(summary.text()).toContain('Allocated')

    expect(details.text()).toContain('Working directory')
    expect(wrapper.get('#workdir').text()).toContain(jobRunning.working_directory)
    expect(details.text()).toContain('Requested')
    expect(details.text()).toContain('Allocated')
    expect(details.text()).not.toContain('Exit Code')
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

    expect(wrapper.text()).toContain('Job 1234')
    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
  })

  test('shows edit and cancel for the owner with self-scoped job actions', () => {
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

    expect(wrapper.text()).toContain('Edit')
    expect(wrapper.text()).toContain('Cancel')
  })

  test('hides edit and cancel for another users job under self scope', () => {
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

    expect(wrapper.text()).not.toContain('Edit')
    expect(wrapper.text()).not.toContain('Cancel')
  })
})

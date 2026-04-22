import { nextTick } from 'vue'
import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { useRuntimeStore } from '@/stores/runtime'
import JobView from '@/views/JobView.vue'
import JobBackButton from '@/components/job/JobBackButton.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import type { ClusterIndividualJob } from '@/composables/GatewayAPI'
import jobRunning from '../assets/job-running.json'
import type { RouterMock } from 'vue-router-mock'
import PanelSkeleton from '@/components/PanelSkeleton.vue'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterIndividualJob>()

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

let router: RouterMock

describe('JobView.vue', () => {
  beforeEach(() => {
    router = init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [] },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
  })
  test('display job details', () => {
    mockClusterDataPoller.data.value = jobRunning
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
      }
    })
    // Check JobBackButton component is rendered
    const backButton = wrapper.findComponent(JobBackButton)
    expect(backButton.exists()).toBe(true)
    expect(backButton.props('cluster')).toBe('foo')
    expect(backButton.text()).toBe('Back to jobs')

    const overview = wrapper.get('[data-testid="job-overview-grid"]')
    const details = wrapper.get('[data-testid="job-detail-list"]')
    const userLink = wrapper.get('#user').findComponent({ name: 'RouterLink' })

    expect(overview.text()).toContain('User')
    expect(userLink.props('to')).toEqual({
      name: 'user',
      params: { cluster: 'foo', user: jobRunning.user }
    })
    expect(overview.text()).toContain('Group')
    expect(overview.text()).toContain(jobRunning.group)
    expect(overview.text()).toContain('Priority')
    expect(overview.text()).toContain(jobRunning.priority.number.toString())
    expect(overview.text()).toContain('Nodes')
    expect(overview.text()).toContain(jobRunning.nodes)
    expect(overview.text()).toContain('Partition')
    expect(overview.text()).toContain(jobRunning.partition)
    expect(overview.text()).toContain('QOS')
    expect(overview.text()).toContain(jobRunning.qos)
    expect(overview.text()).toContain('Exit Code')
    expect(overview.text()).toContain('SUCCESS (0)')
    expect(wrapper.get('#account').text()).toContain('-')
    expect(wrapper.get('#account').findComponent({ name: 'RouterLink' }).exists()).toBe(false)

    expect(details.text()).toContain('Working directory')
    expect(wrapper.get('#workdir').text()).toContain(jobRunning.working_directory)
    expect(details.text()).toContain('Requested')
    expect(details.text()).toContain('Allocated')
    expect(details.text()).not.toContain('Exit Code')
  })

  test('highlight job field in route hash', async () => {
    await router.setHash('#user')
    mockClusterDataPoller.data.value = jobRunning
    const wrapper = mount(JobView, {
      props: {
        cluster: 'foo',
        id: 1234
      }
    })
    await nextTick()

    expect(wrapper.get('#user').classes('ring-2')).toBe(true)
    expect(wrapper.get('#group').classes('ring-2')).toBe(false)
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
})

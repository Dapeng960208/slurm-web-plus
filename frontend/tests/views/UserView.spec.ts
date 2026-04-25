import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import UserView from '@/views/UserView.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import associations from '../assets/associations.json'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterAssociation[]>()
const analyticsPanelsStub = {
  template: '<div>Tool Analysis</div>'
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

describe('UserView.vue', () => {
  beforeEach(() => {
    init_plugins()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: ['associations-view'] },
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
      },
      global: {
        stubs: {
          UserAnalyticsPanels: analyticsPanelsStub
        }
      }
    })
    await flushPromises()

    const buttons = wrapper.findAll('button')
    const backButton = buttons.find((btn) => btn.text().includes('Back to accounts'))
    expect(backButton).toBeDefined()

    const userHeading = wrapper.get('div#user-heading')
    expect(userHeading.text()).toContain('root')
    expect(userHeading.text()).toContain('1')
    expect(userHeading.text()).toContain('account associated')
    expect(userHeading.findAll('router-link-stub').length).toBe(1)

    const userAssociationsTable = wrapper.get('table')
    const columnHeaders = userAssociationsTable.get('thead').findAll('th')
    expect(columnHeaders[0].text()).toBe('Account')
    expect(columnHeaders[1].text()).toBe('Job limits')
    expect(columnHeaders[2].text()).toBe('Resource limits')
    expect(columnHeaders[3].text()).toBe('Time limits')
    expect(columnHeaders[4].text()).toBe('QOS')
    expect(userAssociationsTable.findAll('tbody tr').length).toBeGreaterThan(0)

    const breadcrumbs = userAssociationsTable.findAllComponents(AccountBreadcrumb)
    expect(breadcrumbs.length).toBeGreaterThan(0)
  })

  test('shows analysis shortcut when feature is enabled', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        permissions: { roles: [], actions: ['associations-view', 'view-jobs'] },
        user_metrics: true
      }
    ]
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserAnalyticsPanels: analyticsPanelsStub
        }
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('Submission and tool analytics')
    expect(wrapper.text()).toContain('Tool Analysis')
  })

  test('shows history jobs shortcut when permission is granted', async () => {
    useRuntimeStore().availableClusters = [
      {
        ...useRuntimeStore().availableClusters[0],
        permissions: { roles: [], actions: ['associations-view', 'view-history-jobs'] }
      }
    ]
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserAnalyticsPanels: analyticsPanelsStub
        }
      }
    })
    await flushPromises()

    expect(wrapper.text()).toContain('History access granted')
  })

  test('shows user skeleton when data is not loaded', () => {
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = true

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserAnalyticsPanels: analyticsPanelsStub
        }
      }
    })

    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
    expect(wrapper.get('#user-heading').text()).toContain('root')
  })

  test('shows error alert when unable to retrieve associations', () => {
    mockClusterDataPoller.unable.value = true
    mockClusterDataPoller.loaded.value = true

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'root'
      },
      global: {
        stubs: {
          UserAnalyticsPanels: analyticsPanelsStub
        }
      }
    })

    const errorAlert = wrapper.findComponent(ErrorAlert)
    expect(errorAlert.exists()).toBe(true)
    expect(errorAlert.text()).toContain('Unable to retrieve associations for cluster')
    expect(errorAlert.text()).toContain('foo')
  })

  test('shows info alert when user has no associations', () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.data.value = []

    const wrapper = mount(UserView, {
      props: {
        cluster: 'foo',
        user: 'nonexistent'
      },
      global: {
        stubs: {
          UserAnalyticsPanels: analyticsPanelsStub
        }
      }
    })

    const infoAlert = wrapper.findComponent(InfoAlert)
    expect(infoAlert.exists()).toBe(true)
    expect(infoAlert.text()).toContain('User nonexistent has no associations on this cluster')
  })
})

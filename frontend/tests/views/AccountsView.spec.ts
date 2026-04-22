import { describe, test, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import AccountsView from '@/views/AccountsView.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import associations from '../assets/associations.json'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import AccountTreeNode from '@/components/accounts/AccountTreeNode.vue'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterAssociation[]>()

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: () => mockClusterDataPoller
}))

describe('AccountsView.vue', () => {
  beforeEach(() => {
    init_plugins()
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
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = false
  })

  test('displays accounts page', () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = associations

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    expect(wrapper.get('h1').text()).toBe('Accounts')
    expect(wrapper.text()).toContain('Accounts defined on cluster')

    const uniqueAccounts = associations.filter((a) => !a.user).length
    expect(wrapper.text()).toContain(uniqueAccounts.toString())
    expect(wrapper.text()).toContain('account' + (uniqueAccounts > 1 ? 's' : ''))

    const treeNodes = wrapper.findAllComponents(AccountTreeNode)
    expect(treeNodes.length).toBeGreaterThan(0)
  })

  test('shows skeleton when data is not loaded', () => {
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = true

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    wrapper.getComponent(PanelSkeleton)
    expect(wrapper.text()).toContain('Accounts')
  })

  test('shows error alert when unable to retrieve associations', () => {
    mockClusterDataPoller.unable.value = true
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    const errorAlert = wrapper.getComponent(ErrorAlert)
    expect(errorAlert.text()).toContain('Unable to retrieve associations from cluster')
    expect(errorAlert.text()).toContain('foo')
  })

  test('shows info alert when no associations', () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = []

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    const infoAlert = wrapper.getComponent(InfoAlert)
    expect(infoAlert.text()).toContain('No association defined on cluster')
    expect(infoAlert.text()).toContain('foo')
  })
})

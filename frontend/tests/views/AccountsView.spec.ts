import { describe, test, expect, beforeEach, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AccountsView from '@/views/AccountsView.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { AccountDescription, ClusterAssociation } from '@/composables/GatewayAPI'
import associations from '../assets/associations.json'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'
import AccountTreeNode from '@/components/accounts/AccountTreeNode.vue'

const mockAssociationsPoller = getMockClusterDataPoller<ClusterAssociation[]>()
const mockAccountsPoller = getMockClusterDataPoller<AccountDescription[]>()
const mockGatewayAPI = {
  save_account: vi.fn()
}

vi.mock('@/composables/DataPoller', () => ({
  useClusterDataPoller: (_cluster: string, callback: string) =>
    callback === 'accounts' ? mockAccountsPoller : mockAssociationsPoller
}))

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('AccountsView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
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
    mockAssociationsPoller.data.value = undefined
    mockAssociationsPoller.unable.value = false
    mockAssociationsPoller.loaded.value = false
    mockAssociationsPoller.initialLoading.value = false
    mockAccountsPoller.data.value = undefined
    mockAccountsPoller.unable.value = false
    mockAccountsPoller.loaded.value = false
    mockAccountsPoller.initialLoading.value = false
    document.body.innerHTML = ''
  })

  test('displays accounts page', () => {
    mockAssociationsPoller.loaded.value = true
    mockAssociationsPoller.initialLoading.value = false
    mockAssociationsPoller.data.value = associations
    mockAccountsPoller.loaded.value = true
    mockAccountsPoller.initialLoading.value = false
    mockAccountsPoller.data.value = [
      { name: 'root', parent_account: '', qos: ['normal'] },
      { name: 'physic', parent_account: 'root', qos: ['normal'] }
    ]

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    expect(wrapper.get('h1').text()).toBe('Accounts')
    expect(wrapper.text()).toContain('Accounts defined on cluster')

    expect(wrapper.text()).toContain('2')
    expect(wrapper.text()).toContain('accounts')

    const treeNodes = wrapper.findAllComponents(AccountTreeNode)
    expect(treeNodes.length).toBeGreaterThan(0)
  })

  test('shows skeleton when data is not loaded', () => {
    mockAssociationsPoller.loaded.value = false
    mockAssociationsPoller.initialLoading.value = true
    mockAccountsPoller.loaded.value = false
    mockAccountsPoller.initialLoading.value = true

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    wrapper.getComponent(PanelSkeleton)
    expect(wrapper.text()).toContain('Accounts')
  })

  test('shows error alert when unable to retrieve accounts', () => {
    mockAssociationsPoller.unable.value = true
    mockAssociationsPoller.loaded.value = true
    mockAssociationsPoller.initialLoading.value = false
    mockAccountsPoller.loaded.value = true
    mockAccountsPoller.initialLoading.value = false
    mockAccountsPoller.data.value = []

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    const errorAlert = wrapper.getComponent(ErrorAlert)
    expect(errorAlert.text()).toContain('Unable to retrieve accounts from cluster')
    expect(errorAlert.text()).toContain('foo')
  })

  test('shows info alert when no accounts', () => {
    mockAssociationsPoller.loaded.value = true
    mockAssociationsPoller.initialLoading.value = false
    mockAssociationsPoller.data.value = []
    mockAccountsPoller.loaded.value = true
    mockAccountsPoller.initialLoading.value = false
    mockAccountsPoller.data.value = []

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    const infoAlert = wrapper.getComponent(InfoAlert)
    expect(infoAlert.text()).toContain('No account defined on cluster')
    expect(infoAlert.text()).toContain('foo')
  })

  test('creates account with organization field', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['accounts:view:*', 'accounts:edit:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockAssociationsPoller.loaded.value = true
    mockAssociationsPoller.initialLoading.value = false
    mockAssociationsPoller.data.value = associations
    mockAccountsPoller.loaded.value = true
    mockAccountsPoller.initialLoading.value = false
    mockAccountsPoller.data.value = [{ name: 'root', parent_account: '', qos: ['normal'] }]
    mockGatewayAPI.save_account.mockResolvedValue({ operation: 'accounts.update' })

    const wrapper = mount(AccountsView, {
      attachTo: document.body,
      props: {
        cluster: 'foo'
      }
    })

    await wrapper.findAll('button').find((button) => button.text() === 'Create account')!.trigger('click')
    wrapper
      .findAllComponents(ActionDialog)
      .find((component) => component.props('title') === 'Create Account')!
      .vm.$emit('submit', {
        name: 'science',
        description: 'Science',
        organization: 'Biology Lab',
        parent_account: 'root',
        qos: 'normal,study'
      })
    await flushPromises()

    expect(mockGatewayAPI.save_account).toHaveBeenCalledWith('foo', {
      name: 'science',
      description: 'Science',
      organization: 'Biology Lab',
      parent_account: 'root',
      qos: ['normal', 'study']
    })
    expect(mockAccountsPoller.setCallback).toHaveBeenCalledWith('accounts')
    expect(mockAssociationsPoller.setCallback).toHaveBeenCalledWith('associations')
    wrapper.unmount()
  })

  test('shows newly created account from accounts data even without association row', () => {
    mockAssociationsPoller.loaded.value = true
    mockAssociationsPoller.initialLoading.value = false
    mockAssociationsPoller.data.value = []
    mockAccountsPoller.loaded.value = true
    mockAccountsPoller.initialLoading.value = false
    mockAccountsPoller.data.value = [
      { name: 'science', description: 'Science', organization: 'Science', parent_account: '' }
    ]

    const wrapper = mount(AccountsView, {
      props: {
        cluster: 'foo'
      }
    })

    const treeNodes = wrapper.findAllComponents(AccountTreeNode)
    expect(treeNodes).toHaveLength(1)
    expect(treeNodes[0].props('node').account).toBe('science')
    expect(wrapper.text()).toContain('1account found')
  })
})

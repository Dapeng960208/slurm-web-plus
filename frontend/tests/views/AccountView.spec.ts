import { describe, test, expect, beforeEach, vi } from 'vitest'
import { nextTick } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { RouterLink } from 'vue-router'
import AccountView from '@/views/AccountView.vue'
import ActionDialog from '@/components/operations/ActionDialog.vue'
import { init_plugins, getMockClusterDataPoller } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { ClusterAssociation } from '@/composables/GatewayAPI'
import associations from '../assets/associations.json'
import ErrorAlert from '@/components/ErrorAlert.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import AccountBreadcrumb from '@/components/accounts/AccountBreadcrumb.vue'
import PanelSkeleton from '@/components/PanelSkeleton.vue'

const mockClusterDataPoller = getMockClusterDataPoller<ClusterAssociation[]>()
const mockGatewayAPI = {
  account: vi.fn(),
  save_account: vi.fn(),
  delete_account: vi.fn(),
  save_association: vi.fn(),
  delete_association: vi.fn()
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

describe('AccountView.vue', () => {
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
    mockClusterDataPoller.data.value = undefined
    mockClusterDataPoller.unable.value = false
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = false
    mockGatewayAPI.account.mockResolvedValue({
      name: 'root',
      description: 'Root account',
      organization: 'Core HPC'
    })
    document.body.innerHTML = ''
  })

  test('displays account details', async () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = associations as ClusterAssociation[]

    const wrapper = mount(AccountView, {
      props: {
        cluster: 'foo',
        account: 'root'
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

    await flushPromises()

    const buttons = wrapper.findAll('button')
    const backButton = buttons.find((btn) => btn.text().includes('Back to accounts'))
    expect(backButton).toBeDefined()

    const accountHeading = wrapper.get('div#account-heading')
    expect(accountHeading.text()).toContain('root')
    expect(accountHeading.text()).toContain('Account Detail')

    const viewJobsLink = accountHeading.getComponent(RouterLink)
    expect(viewJobsLink.props('to')).toEqual({
      name: 'jobs',
      params: { cluster: 'foo' },
      query: { accounts: 'root' }
    })

    const accountDefinition = wrapper.get('dl')

    expect(accountDefinition.get('div#parents dt').text()).toBe('Parent accounts')
    accountDefinition.getComponent(AccountBreadcrumb)

    expect(accountDefinition.text()).toContain('Subaccounts')
    const subaccountsSection = wrapper.get('div#subaccounts')
    const links = subaccountsSection.findAllComponents(RouterLink)
    expect(links.length).toBeGreaterThan(0)

    expect(accountDefinition.get('div#qos dt').text()).toBe('QoS')

    const jobLimitsSection = accountDefinition.get('div#limits-jobs')
    expect(jobLimitsSection.get('dt').text()).toBe('Job limits')
    expect(jobLimitsSection.get('dd').text()).toContain('Running')
    expect(jobLimitsSection.get('dd').text()).toContain('Submitted')
    expect(jobLimitsSection.get('dd').text()).toContain('Running / user')
    expect(jobLimitsSection.get('dd').text()).toContain('Submitted / user')

    const resourceLimitsSection = accountDefinition.get('div#limits-resources')
    expect(resourceLimitsSection.get('dt').text()).toBe('Resource limits')
    expect(resourceLimitsSection.get('dd').text()).toContain('Total')
    expect(resourceLimitsSection.get('dd').text()).toContain('Per job')
    expect(resourceLimitsSection.get('dd').text()).toContain('Per node')

    const timeLimitsSection = accountDefinition.get('div#limits-time')
    expect(accountDefinition.get('div#limits-time dt').text()).toBe('Time limits')
    expect(timeLimitsSection.get('dt').text()).toBe('Time limits')
    expect(timeLimitsSection.get('dd').text()).toContain('Total')
    expect(timeLimitsSection.get('dd').text()).toContain('Per job')

    const userAssociationsTable = wrapper.get('table')
    expect(wrapper.text()).toContain('User Associations')
    expect(userAssociationsTable.findAll('tbody tr').length).toBeGreaterThan(0)
  })

  test('shows account skeleton when data is not loaded', () => {
    mockClusterDataPoller.loaded.value = false
    mockClusterDataPoller.initialLoading.value = true

    const wrapper = mount(AccountView, {
      props: {
        cluster: 'foo',
        account: 'root'
      }
    })

    expect(wrapper.findComponent(PanelSkeleton).exists()).toBe(true)
    expect(wrapper.get('#account-heading').text()).toContain('root')
  })

  test('shows error alert when unable to retrieve associations', () => {
    mockClusterDataPoller.unable.value = true
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false

    const wrapper = mount(AccountView, {
      props: {
        cluster: 'foo',
        account: 'root'
      }
    })

    const errorAlert = wrapper.findComponent(ErrorAlert)
    expect(errorAlert.exists()).toBe(true)
    expect(errorAlert.text()).toContain('Unable to retrieve associations for cluster')
    expect(errorAlert.text()).toContain('foo')
  })

  test('shows info alert when account does not exist', () => {
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = []

    const wrapper = mount(AccountView, {
      props: {
        cluster: 'foo',
        account: 'nonexistent'
      }
    })

    const infoAlert = wrapper.findComponent(InfoAlert)
    expect(infoAlert.exists()).toBe(true)
    expect(infoAlert.text()).toContain('Account nonexistent does not exist on this cluster')
  })

  test('displays empty symbol when no subaccounts', async () => {
    const accountData: ClusterAssociation[] = [
      {
        account: 'leaf',
        parent_account: 'root',
        qos: [],
        user: '',
        max: associations[0].max
      }
    ]

    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = accountData
    mockGatewayAPI.account.mockResolvedValue({
      name: 'leaf',
      description: 'Leaf account',
      organization: 'Core HPC'
    })

    const wrapper = mount(AccountView, {
      props: {
        cluster: 'foo',
        account: 'leaf'
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Subaccounts')
    const subaccountsSection = wrapper.get('div#subaccounts')
    expect(subaccountsSection.get('dd').text()).toBe('∅')
  })

  test('shows info alert when account has no user associations', async () => {
    const accountData: ClusterAssociation[] = [
      {
        account: 'empty',
        parent_account: '',
        qos: [],
        user: '',
        max: associations[0].max
      }
    ]

    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = accountData
    mockGatewayAPI.account.mockResolvedValue({
      name: 'empty',
      description: 'Empty account',
      organization: 'Core HPC'
    })

    const wrapper = mount(AccountView, {
      props: {
        cluster: 'foo',
        account: 'empty'
      }
    })

    await flushPromises()

    const infoAlert = wrapper.findComponent(InfoAlert)
    expect(infoAlert.exists()).toBe(true)
    expect(infoAlert.text()).toContain('has no end-user associations')
  })

  test('adds, edits QOS, and deletes account user associations', async () => {
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['accounts:view:*', 'accounts:edit:*', 'accounts:delete:*']
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
    mockGatewayAPI.save_association.mockResolvedValue({ operation: 'accounts.associations.update' })
    mockGatewayAPI.delete_association.mockResolvedValue({ operation: 'accounts.associations.delete' })
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = [
      {
        ...(associations as ClusterAssociation[])[0],
        account: 'root',
        user: '',
        qos: ['normal']
      },
      {
        ...(associations as ClusterAssociation[])[0],
        account: 'root',
        user: 'alice',
        qos: ['normal'],
        default: { qos: 'normal' }
      }
    ] as ClusterAssociation[]

    const wrapper = mount(AccountView, {
      attachTo: document.body,
      props: {
        cluster: 'foo',
        account: 'root'
      }
    })

    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Add user')!.trigger('click')
    await nextTick()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.account.dialogs.addUserAssociation.title')!
      .vm.$emit('submit', {
        user: 'bob',
        qos: 'normal, study',
        default_qos: 'study'
      })
    await flushPromises()

    expect(mockGatewayAPI.save_association).toHaveBeenCalledWith('foo', {
      associations: [
        {
          account: 'root',
          user: 'bob',
          qos: ['normal', 'study'],
          default: { qos: 'study' }
        }
      ]
    })

    await wrapper.findAll('button').find((button) => button.text() === 'Edit QOS')!.trigger('click')
    await nextTick()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.account.dialogs.editUserQos.title')!
      .vm.$emit('submit', {
        qos: 'debug',
        default_qos: 'debug'
      })
    await flushPromises()

    expect(mockGatewayAPI.save_association).toHaveBeenLastCalledWith('foo', {
      associations: [
        {
          account: 'root',
          user: 'alice',
          qos: ['debug'],
          default: { qos: 'debug' }
        }
      ]
    })

    await wrapper.findAll('button').find((button) => button.text() === 'Delete')!.trigger('click')
    await nextTick()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.account.dialogs.deleteAssociation.title')!
      .vm.$emit('submit', {})
    await flushPromises()

    expect(mockGatewayAPI.delete_association).toHaveBeenCalledWith('foo', {
      associations: [
        {
          account: 'root',
          user: 'alice'
        }
      ]
    })
    wrapper.unmount()
  })

  test('adds user for account without account-level association row', async () => {
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
    mockGatewayAPI.account.mockResolvedValue({
      name: 'science',
      description: 'Science',
      organization: 'Science'
    })
    mockGatewayAPI.save_association.mockResolvedValue({ operation: 'accounts.associations.update' })
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = [] as ClusterAssociation[]

    const wrapper = mount(AccountView, {
      attachTo: document.body,
      props: {
        cluster: 'foo',
        account: 'science'
      }
    })
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Add user')!.trigger('click')
    await nextTick()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.account.dialogs.addUserAssociation.title')!
      .vm.$emit('submit', {
        user: 'bob',
        qos: '',
        default_qos: ''
      })
    await flushPromises()

    expect(mockGatewayAPI.save_association).toHaveBeenCalledWith('foo', {
      associations: [
        {
          account: 'science',
          user: 'bob'
        }
      ]
    })
    wrapper.unmount()
  })

  test('edits account with organization field', async () => {
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
    mockGatewayAPI.save_account.mockResolvedValue({ operation: 'accounts.update' })
    mockClusterDataPoller.loaded.value = true
    mockClusterDataPoller.initialLoading.value = false
    mockClusterDataPoller.data.value = [
      {
        ...(associations as ClusterAssociation[])[0],
        account: 'root',
        user: '',
        qos: ['normal']
      }
    ] as ClusterAssociation[]

    const wrapper = mount(AccountView, {
      attachTo: document.body,
      props: {
        cluster: 'foo',
        account: 'root'
      }
    })
    await flushPromises()

    await wrapper.findAll('button').find((button) => button.text() === 'Edit')!.trigger('click')
    await nextTick()
    wrapper
      .findAllComponents(ActionDialog)
      .find((dialog) => dialog.props('title') === 'pages.account.dialogs.edit.title')!
      .vm.$emit('submit', {
        description: 'Root account',
        organization: 'Platform Team',
        parent_account: '',
        qos: 'normal'
      })
    await flushPromises()

    expect(mockGatewayAPI.save_account).toHaveBeenCalledWith('foo', {
      name: 'root',
      description: 'Root account',
      organization: 'Platform Team',
      parent_account: undefined,
      qos: ['normal']
    })
    wrapper.unmount()
  })
})

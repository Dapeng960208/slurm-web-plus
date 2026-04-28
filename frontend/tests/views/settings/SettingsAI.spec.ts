import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import SettingsAIView from '@/views/settings/SettingsAI.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import type { RouterMock } from 'vue-router-mock'

const mockGatewayAPI = {
  ai_configs: vi.fn(),
  create_ai_config: vi.fn(),
  update_ai_config: vi.fn(),
  delete_ai_config: vi.fn(),
  validate_ai_config: vi.fn(),
  ai_admin_conversations: vi.fn(),
  ai_admin_conversation: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('views/settings/SettingsAI.vue', () => {
  function seedRuntime() {
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: [
            'admin/ai:view:*',
            'admin/ai:edit:*',
            'admin/ai:delete:*',
            'settings/ai:view:*',
            'settings/ai:edit:*',
            'settings/ai:delete:*',
            'ai:view:*'
          ]
        },
        capabilities: {
          ai: {
            enabled: true,
            streaming: true,
            providers: [{ key: 'qwen', label: 'Qwen' }]
          }
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ] as never
    runtimeStore.currentCluster = runtimeStore.availableClusters[0] as never
  }

  async function mountOnAdminRoute(router: RouterMock) {
    await router.push('/foo/admin/ai')
    await router.getPendingNavigation()
  }

  function getButtonByText(wrapper: VueWrapper, label: string) {
    const match = wrapper
      .findAll('button')
      .find((button) => button.text().trim().includes(label))
    expect(match, `button "${label}" should exist`).toBeTruthy()
    return match!
  }

  const globalStubs = {
    SettingsTabs: true,
    RouterLink: { template: '<a><slot /></a>' },
    TransitionRoot: { template: '<div><slot /></div>' },
    TransitionChild: { template: '<div><slot /></div>' },
    Dialog: { template: '<div><slot /></div>' },
    DialogPanel: { template: '<div><slot /></div>' },
    DialogTitle: { template: '<div><slot /></div>' }
  }

  beforeEach(() => {
    void init_plugins()
    vi.clearAllMocks()
    mockGatewayAPI.ai_admin_conversations.mockResolvedValue([])
    mockGatewayAPI.ai_admin_conversation.mockResolvedValue({
      id: 21,
      username: 'alice',
      title: 'Queue pressure',
      created_at: '2026-04-24T10:00:00Z',
      updated_at: '2026-04-24T10:05:00Z',
      deleted_at: null,
      deleted_by: null,
      last_message: 'GPU partition is saturated.',
      model_config_id: 1,
      messages: [
        {
          id: 101,
          role: 'user',
          content: 'How busy is the GPU queue?',
          created_at: '2026-04-24T10:00:00Z',
          model_config_id: 1,
          metadata: {}
        }
      ],
      tool_calls: []
    })
  })

  test('loads AI configs and renders masked secret details', async () => {
    const router = init_plugins()
    seedRuntime()
    mockGatewayAPI.ai_configs.mockResolvedValue([
      {
        id: 1,
        name: 'qwen-prod',
        provider: 'qwen',
        provider_label: 'Qwen',
        model: 'qwen3-coder',
        display_name: 'Qwen Prod',
        enabled: true,
        is_default: true,
        sort_order: 10,
        base_url: 'http://localhost:8000/v1',
        deployment: null,
        api_version: null,
        request_timeout: 60,
        temperature: 0.2,
        system_prompt: 'You are the cluster AI assistant.',
        extra_options: {},
        secret_configured: true,
        secret_mask: '***1234',
        last_validated_at: '2026-04-24T10:15:00Z',
        last_validation_error: null
      }
    ])

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAIView, {
      global: {
        stubs: {
          ...globalStubs,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.ai_configs).toHaveBeenCalledWith('foo')
    expect(wrapper.text()).toContain('Qwen Prod')
    expect(wrapper.text()).toContain('***1234')
    expect(wrapper.text()).toContain('Default')
    expect(wrapper.text()).toContain('Delete')
    expect(wrapper.find('[data-testid="ai-config-tag"]').exists()).toBe(true)
  })

  test('filters admin audit records and loads details only after row click', async () => {
    const router = init_plugins()
    seedRuntime()
    mockGatewayAPI.ai_configs.mockResolvedValue([])
    mockGatewayAPI.ai_admin_conversations.mockResolvedValue([
      {
        id: 21,
        username: 'alice',
        title: 'Queue pressure',
        created_at: '2026-04-24T10:00:00Z',
        updated_at: '2026-04-24T10:05:00Z',
        deleted_at: null,
        deleted_by: null,
        last_message: 'GPU partition is saturated.',
        model_config_id: 1
      },
      {
        id: 22,
        username: 'bob',
        title: 'Node capacity',
        created_at: '2026-04-24T11:00:00Z',
        updated_at: '2026-04-24T11:05:00Z',
        deleted_at: null,
        deleted_by: null,
        last_message: 'cn01 has free memory.',
        model_config_id: 1
      }
    ])

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAIView, {
      global: {
        stubs: {
          ...globalStubs,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.ai_admin_conversations).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.ai_admin_conversation).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Queue pressure')
    expect(wrapper.text()).toContain('Node capacity')

    await wrapper.get('[data-testid="audit-username-filter"]').setValue('alice')
    await flushPromises()

    expect(wrapper.text()).toContain('Queue pressure')
    expect(wrapper.text()).not.toContain('Node capacity')

    await wrapper.get('[data-testid="audit-keyword-filter"]').setValue('gpu')
    await flushPromises()

    expect(wrapper.text()).toContain('Queue pressure')

    await wrapper.find('tbody tr').trigger('click')
    await flushPromises()

    expect(mockGatewayAPI.ai_admin_conversation).toHaveBeenCalledWith('foo', 21)
    expect(wrapper.text()).toContain('How busy is the GPU queue?')
  })

  test('deletes a model configuration from the tag list', async () => {
    const router = init_plugins()
    seedRuntime()
    mockGatewayAPI.ai_configs
      .mockResolvedValueOnce([
        {
          id: 1,
          name: 'qwen-prod',
          provider: 'qwen',
          provider_label: 'Qwen',
          model: 'qwen3-coder',
          display_name: 'Qwen Prod',
          enabled: true,
          is_default: true,
          sort_order: 10,
          base_url: null,
          deployment: null,
          api_version: null,
          request_timeout: null,
          temperature: null,
          system_prompt: null,
          extra_options: {},
          secret_configured: true,
          secret_mask: '***1234',
          last_validated_at: null,
          last_validation_error: null
        }
      ])
      .mockResolvedValueOnce([])
    mockGatewayAPI.delete_ai_config.mockResolvedValue({})

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAIView, {
      global: {
        stubs: {
          ...globalStubs,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()
    await getButtonByText(wrapper, 'Delete').trigger('click')
    await flushPromises()

    expect(mockGatewayAPI.delete_ai_config).toHaveBeenCalledWith('foo', 1)
    expect(wrapper.text()).toContain('Qwen Prod deleted.')
  })

  test('creates a new AI config', async () => {
    const router = init_plugins()
    seedRuntime()
    mockGatewayAPI.ai_configs.mockResolvedValue([])
    mockGatewayAPI.create_ai_config.mockResolvedValue({
      id: 1,
      name: 'qwen-prod'
    })

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAIView, {
      global: {
        stubs: {
          ...globalStubs,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()
    await getButtonByText(wrapper, 'New model').trigger('click')
    await flushPromises()

    const textInputs = wrapper.findAll('input[type="text"]')
    await textInputs[0].setValue('qwen-prod')
    await textInputs[1].setValue('Qwen Prod')
    await textInputs[2].setValue('qwen3-coder')
    await wrapper.get('input[type="password"]').setValue('sk-secret')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockGatewayAPI.create_ai_config).toHaveBeenCalledWith('foo', {
      name: 'qwen-prod',
      provider: 'qwen',
      model: 'qwen3-coder',
      display_name: 'Qwen Prod',
      enabled: true,
      is_default: false,
      sort_order: 0,
      base_url: null,
      deployment: null,
      api_version: null,
      request_timeout: null,
      temperature: null,
      system_prompt: null,
      extra_options: {},
      api_key: 'sk-secret'
    })
  })

  test('keeps delete entry hidden when the user lacks admin delete permission', async () => {
    const router = init_plugins()
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['admin/ai:view:*', 'admin/ai:edit:*', 'settings/ai:view:*', 'settings/ai:edit:*', 'ai:view:*']
        },
        capabilities: {
          ai: {
            enabled: true,
            streaming: true,
            providers: [{ key: 'qwen', label: 'Qwen' }]
          }
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ] as never
    runtimeStore.currentCluster = runtimeStore.availableClusters[0] as never
    mockGatewayAPI.ai_configs.mockResolvedValue([
      {
        id: 1,
        name: 'qwen-prod',
        provider: 'qwen',
        provider_label: 'Qwen',
        model: 'qwen3-coder',
        display_name: 'Qwen Prod',
        enabled: true,
        is_default: true,
        sort_order: 10,
        base_url: null,
        deployment: null,
        api_version: null,
        request_timeout: null,
        temperature: null,
        system_prompt: null,
        extra_options: {},
        secret_configured: true,
        secret_mask: '***1234',
        last_validated_at: null,
        last_validation_error: null
      }
    ])

    await mountOnAdminRoute(router)

    const wrapper = mount(SettingsAIView, {
      global: {
        stubs: {
          ...globalStubs,
          AdminTabs: true,
          AdminHeader: true
        }
      }
    })

    await flushPromises()

    expect(wrapper.text()).toContain('Edit')
    expect(wrapper.text()).toContain('Test connection')
    expect(wrapper.text()).not.toContain('Delete')
  })
})

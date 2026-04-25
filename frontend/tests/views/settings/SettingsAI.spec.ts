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
  validate_ai_config: vi.fn()
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
            'settings/ai:view:*',
            'settings/ai:edit:*',
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
    await router.push({ name: 'admin-ai', params: { cluster: 'foo' } })
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
})

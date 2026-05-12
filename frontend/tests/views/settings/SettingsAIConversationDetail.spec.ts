import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { RouterLinkStub } from '@vue/test-utils'
import SettingsAIConversationDetailView from '@/views/settings/SettingsAIConversationDetail.vue'
import { init_plugins } from '../../lib/common'
import { useRuntimeStore } from '@/stores/runtime'
import { i18n } from '@/plugins/i18n'

const mockGatewayAPI = {
  ai_admin_conversation: vi.fn()
}

vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return {
    ...actual
  }
})

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('views/settings/SettingsAIConversationDetail.vue', () => {
  beforeEach(() => {
    void init_plugins()
    vi.clearAllMocks()
    i18n.global.locale.value = 'en'
  })

  function seedRuntime() {
    const runtimeStore = useRuntimeStore()
    runtimeStore.availableClusters = [
      {
        name: 'foo',
        permissions: {
          roles: [],
          actions: [],
          rules: ['admin/ai:view:*', 'ai:view:*']
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

  test('loads one admin conversation and renders messages plus tool calls', async () => {
    void init_plugins()
    seedRuntime()
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
      tool_calls: [
        {
          id: 301,
          tool_name: 'cluster_query',
          interface_key: 'stats',
          status_code: 200,
          result_summary: 'Queue load fetched.',
          status: 'ok',
          error: null,
          duration_ms: 81,
          created_at: '2026-04-24T10:00:03Z'
        }
      ]
    })

    const wrapper = mount(SettingsAIConversationDetailView, {
      props: {
        cluster: 'foo',
        conversationId: 21
      },
      global: {
        stubs: {
          AdminTabs: true,
          AdminHeader: true,
          RouterLink: RouterLinkStub
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.ai_admin_conversation).toHaveBeenCalledWith('foo', 21)
    expect(wrapper.text()).toContain('Queue pressure')
    expect(wrapper.text()).toContain('How busy is the GPU queue?')
    expect(wrapper.text()).toContain('cluster_query')
    expect(wrapper.text()).toContain('Queue load fetched.')
  })
})

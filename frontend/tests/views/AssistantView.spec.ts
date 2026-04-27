import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AssistantView from '@/views/AssistantView.vue'
import { init_plugins } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

const mockGatewayAPI = {
  ai_configs: vi.fn(),
  ai_conversations: vi.fn(),
  ai_conversation: vi.fn(),
  stream_ai_chat: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

describe('views/AssistantView.vue', () => {
  beforeEach(() => {
    init_plugins()
    vi.clearAllMocks()
    useRuntimeStore().availableClusters = [
      {
        name: 'foo',
        permissions: { roles: [], actions: [], rules: ['ai:view:*', 'admin/ai:view:*', 'admin/ai:edit:*'] },
        capabilities: {
          ai: {
            enabled: true,
            streaming: true,
            persistence: true,
            default_model_id: 1
          }
        },
        racksdb: true,
        infrastructure: 'foo',
        metrics: true,
        cache: true
      }
    ]
  })

  test('loads AI model configs and conversations', async () => {
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
    mockGatewayAPI.ai_conversations.mockResolvedValue([
      {
        id: 9,
        title: 'Queue pressure',
        created_at: '2026-04-24T10:00:00Z',
        updated_at: '2026-04-24T10:05:00Z',
        last_message: 'GPU partition is saturated.',
        model_config_id: 1
      }
    ])
    mockGatewayAPI.ai_conversation.mockResolvedValue({
      id: 9,
      title: 'Queue pressure',
      created_at: '2026-04-24T10:00:00Z',
      updated_at: '2026-04-24T10:05:00Z',
      model_config_id: 1,
      tool_calls: [
        {
          id: 1,
          tool_name: 'query_agent_interface',
          interface_key: 'jobs',
          status_code: 200,
          status: 'ok',
          duration_ms: 6,
          input_payload: { limit: 10 },
          result_summary: '10 jobs'
        }
      ],
      messages: [
        {
          id: 100,
          role: 'user',
          content: 'How busy is the GPU queue?',
          created_at: '2026-04-24T10:00:00Z',
          model_config_id: 1,
          metadata: {}
        },
        {
          id: 101,
          role: 'assistant',
          content: 'GPU partition is saturated.',
          created_at: '2026-04-24T10:00:05Z',
          model_config_id: 1,
          metadata: {}
        }
      ]
    })

    const wrapper = mount(AssistantView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          PageHeader: {
            props: ['title', 'description'],
            template: '<div><h1>{{ title }}</h1><p>{{ description }}</p><slot name="actions" /></div>'
          }
        }
      }
    })

    await flushPromises()

    expect(mockGatewayAPI.ai_configs).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.ai_conversations).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.ai_conversation).toHaveBeenCalledWith('foo', 9)
    expect(wrapper.text()).toContain('Queue pressure')
    expect(wrapper.text()).toContain('GPU partition is saturated.')
    expect(wrapper.text()).toContain('Qwen Prod')
    expect(wrapper.text()).toContain('HTTP 200')
    expect(wrapper.text()).not.toContain('{"limit":10}')
  })

  test('streams a reply with the selected model', async () => {
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
    mockGatewayAPI.ai_conversations
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 12,
          title: 'GPU capacity',
          created_at: '2026-04-24T11:00:00Z',
          updated_at: '2026-04-24T11:00:05Z',
          last_message: 'Node cn01 has the most free GPUs.',
          model_config_id: 1
        }
      ])
    mockGatewayAPI.ai_conversation.mockResolvedValue({
      id: 12,
      title: 'GPU capacity',
      created_at: '2026-04-24T11:00:00Z',
      updated_at: '2026-04-24T11:00:05Z',
      model_config_id: 1,
      tool_calls: [],
      messages: [
        {
          id: 200,
          role: 'user',
          content: 'Which node has the most free GPUs?',
          created_at: '2026-04-24T11:00:00Z',
          model_config_id: 1,
          metadata: {}
        },
        {
          id: 201,
          role: 'assistant',
          content: 'Node cn01 has the most free GPUs.',
          created_at: '2026-04-24T11:00:05Z',
          model_config_id: 1,
          metadata: {}
        }
      ]
    })
    mockGatewayAPI.stream_ai_chat.mockImplementation((_cluster, _payload, handlers) => {
      handlers.onConversation?.({ conversation_id: 12, model_config_id: 1 })
      handlers.onToolStart?.({ tool_name: 'query_agent_interface', interface_key: 'nodes', arguments: {} })
      handlers.onToolEnd?.({
        tool_name: 'query_agent_interface',
        interface_key: 'nodes',
        arguments: {},
        duration_ms: 10,
        status_code: 200,
        result_summary: '2 nodes'
      })
      handlers.onContent?.('Node cn01 has the most free GPUs.')
      handlers.onComplete?.({ conversation_id: 12, message_id: 201, model_config_id: 1 })
      handlers.onDone?.({ conversation_id: 12 })
      return {
        controller: new AbortController(),
        finished: Promise.resolve()
      }
    })

    const wrapper = mount(AssistantView, {
      props: { cluster: 'foo' },
      global: {
        stubs: {
          ClusterMainLayout: { template: '<div><slot /></div>' },
          PageHeader: {
            props: ['title', 'description'],
            template: '<div><h1>{{ title }}</h1><p>{{ description }}</p><slot name="actions" /></div>'
          }
        }
      }
    })

    await flushPromises()
    await wrapper
      .get('textarea[placeholder="Ask about a job, node resources, partitions, or another read-only cluster question."]')
      .setValue('Which node has the most free GPUs?')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockGatewayAPI.stream_ai_chat).toHaveBeenCalledWith(
      'foo',
      {
        message: 'Which node has the most free GPUs?',
        conversation_id: null,
        model_config_id: 1
      },
      expect.any(Object)
    )
    expect(wrapper.text()).toContain('Node cn01 has the most free GPUs.')
    expect(wrapper.text()).toContain('HTTP 200')
    expect(wrapper.text()).toContain('nodes')
  })
})

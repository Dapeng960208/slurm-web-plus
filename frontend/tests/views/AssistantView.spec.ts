import { beforeEach, describe, expect, test, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import AssistantView from '@/views/AssistantView.vue'
import { init_plugins } from '../lib/common'
import { useRuntimeStore } from '@/stores/runtime'

const mockGatewayAPI = {
  ai_configs: vi.fn(),
  ai_conversations: vi.fn(),
  ai_conversation: vi.fn(),
  delete_ai_conversation: vi.fn(),
  stream_ai_chat: vi.fn()
}

vi.mock('@/composables/GatewayAPI', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/composables/GatewayAPI')>()
  return {
    ...actual,
    useGatewayAPI: () => mockGatewayAPI
  }
})

function mountAssistantView() {
  return mount(AssistantView, {
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
}

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

    const wrapper = mountAssistantView()

    await flushPromises()

    expect(mockGatewayAPI.ai_configs).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.ai_conversations).toHaveBeenCalledWith('foo')
    expect(mockGatewayAPI.ai_conversation).toHaveBeenCalledWith('foo', 9)
    expect(wrapper.text()).toContain('Queue pressure')
    expect(wrapper.text()).toContain('GPU partition is saturated.')
    expect(wrapper.text()).not.toContain('Active model')
    expect(wrapper.text()).not.toContain('Qwen Prod')
    expect(wrapper.text()).not.toContain('Chat requests send the selected')
    expect(wrapper.text()).toContain('HTTP 200')
    expect(wrapper.text()).not.toContain('{"limit":10}')
    expect(wrapper.text()).not.toContain('10 jobs')

    const detailButtons = wrapper.findAll('button').filter((button) => button.text().includes('View details'))
    expect(detailButtons.length).toBeGreaterThan(0)
    await detailButtons[0].trigger('click')

    expect(wrapper.text()).toContain('10 jobs')
    expect(wrapper.text()).toContain('Tool: query_agent_interface')
  })

  test('renders markdown safely for user and assistant messages', async () => {
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
        title: 'Markdown example',
        created_at: '2026-04-24T10:00:00Z',
        updated_at: '2026-04-24T10:05:00Z',
        last_message: 'Rendered markdown',
        model_config_id: 1
      }
    ])
    mockGatewayAPI.ai_conversation.mockResolvedValue({
      id: 9,
      title: 'Markdown example',
      created_at: '2026-04-24T10:00:00Z',
      updated_at: '2026-04-24T10:05:00Z',
      model_config_id: 1,
      tool_calls: [],
      messages: [
        {
          id: 100,
          role: 'user',
          content: '**GPU queue**\n\n- pending\n- running',
          created_at: '2026-04-24T10:00:00Z',
          model_config_id: 1,
          metadata: {}
        },
        {
          id: 101,
          role: 'assistant',
          content:
            '> Saturated queue\n\n```text\npending=12\n```\n\n| State | Count |\n| --- | --- |\n| Pending | 12 |\n\n[Docs](https://example.com/docs)\n\n<script>alert(1)</script>\n<img src=x onerror=alert(1)>',
          created_at: '2026-04-24T10:00:05Z',
          model_config_id: 1,
          metadata: {}
        }
      ]
    })

    const wrapper = mountAssistantView()

    await flushPromises()

    const markdownBlocks = wrapper.findAll('.ui-markdown')
    expect(markdownBlocks).toHaveLength(2)
    expect(markdownBlocks[0].find('strong').text()).toBe('GPU queue')
    expect(markdownBlocks[0].findAll('li')).toHaveLength(2)
    expect(markdownBlocks[1].find('blockquote').exists()).toBe(true)
    expect(markdownBlocks[1].find('pre code').text()).toContain('pending=12')
    expect(markdownBlocks[1].find('table').exists()).toBe(true)

    const link = markdownBlocks[1].find('a')
    expect(link.text()).toBe('Docs')
    expect(link.attributes('href')).toBe('https://example.com/docs')
    expect(link.attributes('target')).toBe('_blank')
    expect(link.attributes('rel')).toBe('noopener noreferrer')

    expect(markdownBlocks[0].html()).not.toContain('**GPU queue**')
    expect(markdownBlocks[1].find('script').exists()).toBe(false)
    expect(markdownBlocks[1].find('img').exists()).toBe(false)
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
          content:
            '**Node cn01** has the most free GPUs.\n\n```text\nfree_gpus=4\n```\n\n[Node details](https://example.com/nodes/cn01)',
          created_at: '2026-04-24T11:00:05Z',
          model_config_id: 1,
          metadata: {}
        }
      ]
    })
    let resolveFinished: (() => void) | null = null
    mockGatewayAPI.stream_ai_chat.mockImplementation((_cluster, _payload, handlers) => {
      handlers.onConversation?.({ conversation_id: 12, model_config_id: 1 })
      handlers.onToolStart?.({ tool_name: 'query_agent_interface', interface_key: 'nodes', arguments: {} })
      handlers.onContent?.('**Node cn01** has the most free GPUs.\n\n```text\n')
      handlers.onContent?.('free_gpus=4\n```\n\n[Node details](https://example.com/nodes/cn01)')
      handlers.onToolEnd?.({
        tool_name: 'query_agent_interface',
        interface_key: 'nodes',
        arguments: {},
        duration_ms: 10,
        status_code: 200,
        result_summary: '2 nodes'
      })
      handlers.onComplete?.({ conversation_id: 12, message_id: 201, model_config_id: 1 })
      handlers.onDone?.({ conversation_id: 12 })
      return {
        controller: new AbortController(),
        finished: new Promise<void>((resolve) => {
          resolveFinished = resolve
        })
      }
    })

    const wrapper = mountAssistantView()

    await flushPromises()
    await wrapper
      .get('textarea[placeholder="Ask about a job, node resources, partitions, or another read-only cluster question."]')
      .setValue('Which node has the most free GPUs?')
    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    const pendingAssistantMessage = wrapper.findAll('.ui-markdown')[1]
    expect(pendingAssistantMessage.find('strong').text()).toBe('Node cn01')
    expect(pendingAssistantMessage.find('pre code').text()).toContain('free_gpus=4')
    expect(pendingAssistantMessage.find('a').attributes('target')).toBe('_blank')

    resolveFinished?.()
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
    expect(wrapper.text()).not.toContain('2 nodes')
    expect(wrapper.findAll('.ui-markdown')[1].find('a').attributes('rel')).toBe('noopener noreferrer')
  })

  test('shows token usage and blocks prompts that exceed the configured limit', async () => {
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
        extra_options: { context_limit: 10 },
        secret_configured: true,
        secret_mask: '***1234',
        last_validated_at: null,
        last_validation_error: null
      }
    ])
    mockGatewayAPI.ai_conversations.mockResolvedValue([])

    const wrapper = mountAssistantView()

    await flushPromises()
    expect(wrapper.text()).toContain('Estimated tokens 0 / 10')

    await wrapper
      .get('textarea[placeholder="Ask about a job, node resources, partitions, or another read-only cluster question."]')
      .setValue('Explain the current job scheduling pressure across every partition with detailed evidence.')
    await flushPromises()

    expect(wrapper.text()).toContain('Token estimate exceeds the current limit')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()

    await wrapper.get('form').trigger('submit.prevent')
    await flushPromises()

    expect(mockGatewayAPI.stream_ai_chat).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Estimated token usage exceeds the current limit')
  })
})

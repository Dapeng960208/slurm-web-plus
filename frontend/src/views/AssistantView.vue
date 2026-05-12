<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ClipboardDocumentIcon, TrashIcon } from '@heroicons/vue/24/outline'
import type {
  AIChatToolEvent,
  AIConversation,
  AIConversationMessage,
  AIConversationSummary,
  AIModelConfig,
  AIToolCallRecord,
  ClusterDescription
} from '@/composables/GatewayAPI'
import { hasClusterAIAssistant, useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import MarkdownMessage from '@/components/MarkdownMessage.vue'

type ToolRun = {
  id: number | string
  tool_name: string
  interface_key: string | null
  arguments: Record<string, unknown>
  result_summary: string | null
  error: string | null
  duration_ms: number | null
  status_code: number | null
  created_at: string | null
  status: 'running' | 'ok' | 'error'
  source: 'live' | 'history'
}

const DEFAULT_TOKEN_LIMIT = 8192
const TOKEN_LIMIT_OPTION_KEYS = ['max_context_tokens', 'context_limit', 'token_limit', 'max_tokens']
const MAX_VISIBLE_TOOL_RUNS = 5

const { cluster } = defineProps<{ cluster: string }>()

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const { t } = useI18n()

const configs = ref<AIModelConfig[]>([])
const configsLoading = ref(false)
const configsError = ref<string | null>(null)

const conversations = ref<AIConversationSummary[]>([])
const conversationsLoading = ref(false)
const conversationsError = ref<string | null>(null)

const selectedConversationId = ref<number | null>(null)
const selectedConversation = ref<AIConversation | null>(null)
const selectedConversationLoading = ref(false)
const selectedConversationError = ref<string | null>(null)

const selectedModelId = ref<number | null>(null)
const draft = ref('')
const sending = ref(false)
const sendError = ref<string | null>(null)
const lastSubmittedPrompt = ref('')
const pendingUserMessage = ref<string | null>(null)
const streamingAssistantMessage = ref('')
const toolRuns = ref<ToolRun[]>([])
const expandedToolRuns = ref<Record<string, boolean>>({})
const messageScroller = ref<HTMLElement | null>(null)
const copiedMessageId = ref<number | string | null>(null)
const deletingConversationId = ref<number | null>(null)

const clusterDetails = computed<ClusterDescription | undefined>(() =>
  runtimeStore.availableClusters.find((value) => value.name === cluster)
)
const aiAvailable = computed(() => hasClusterAIAssistant(clusterDetails.value))
const canView = computed(() => runtimeStore.hasRoutePermission(cluster, 'ai', 'view'))
const canInspectModels = computed(() => runtimeStore.hasRoutePermission(cluster, 'admin/ai', 'view'))
const canManage = computed(
  () => runtimeStore.hasRoutePermission(cluster, 'admin/ai', 'edit')
)
const enabledModels = computed(() =>
  [...configs.value]
    .filter((config) => config.enabled)
    .sort((left, right) => {
      if (left.is_default !== right.is_default) return left.is_default ? -1 : 1
      if (left.sort_order !== right.sort_order) return left.sort_order - right.sort_order
      return left.display_name.localeCompare(right.display_name)
    })
)
const selectedModelConfig = computed(
  () => enabledModels.value.find((config) => config.id === selectedModelId.value) ?? enabledModels.value[0] ?? null
)
const hasUsableModel = computed(() => {
  if (enabledModels.value.length > 0) return true
  return clusterDetails.value?.ai?.default_model_id != null
})
const renderedMessages = computed<AIConversationMessage[]>(() => {
  const messages = [...(selectedConversation.value?.messages ?? [])]
  if (pendingUserMessage.value) {
    messages.push({
      id: '__pending-user__',
      role: 'user',
      content: pendingUserMessage.value,
      created_at: null,
      model_config_id: selectedModelId.value
    })
  }
  if (sending.value || streamingAssistantMessage.value) {
    messages.push({
      id: '__pending-assistant__',
      role: 'assistant',
      content: streamingAssistantMessage.value,
      created_at: null,
      model_config_id: selectedModelId.value,
      metadata: { streaming: true }
    })
  }
  return messages
})
const historicalToolRuns = computed<ToolRun[]>(() =>
  (selectedConversation.value?.tool_calls ?? []).map((toolCall) => normalizeToolRunFromHistory(toolCall))
)
const displayToolRuns = computed<ToolRun[]>(() =>
  [...historicalToolRuns.value, ...toolRuns.value].slice(-MAX_VISIBLE_TOOL_RUNS)
)
const tokenLimit = computed(() => readTokenLimit(selectedModelConfig.value) ?? DEFAULT_TOKEN_LIMIT)
const draftTokenCount = computed(() => estimateTokens(draft.value.trim()))
const conversationTokenCount = computed(() => {
  const systemPromptTokens = estimateTokens(selectedModelConfig.value?.system_prompt ?? '')
  const messageTokens = (selectedConversation.value?.messages ?? []).reduce(
    (total, message) => total + estimateTokens(message.content) + 4,
    0
  )
  return systemPromptTokens + messageTokens
})
const estimatedTokenCount = computed(() => conversationTokenCount.value + draftTokenCount.value)
const tokenLimitExceeded = computed(() => estimatedTokenCount.value > tokenLimit.value)
const canSend = computed(
  () =>
    canView.value &&
    hasUsableModel.value &&
    draft.value.trim().length > 0 &&
    !sending.value &&
    !tokenLimitExceeded.value
)

function estimateTokens(value: string): number {
  const trimmed = value.trim()
  if (!trimmed) return 0
  const cjkChars = trimmed.match(/[\u3400-\u9fff]/g)?.length ?? 0
  const nonCjkChars = trimmed.length - cjkChars
  return Math.ceil(cjkChars * 1.5 + nonCjkChars / 4)
}

function readTokenLimit(config: AIModelConfig | null): number | null {
  if (!config) return null
  for (const key of TOKEN_LIMIT_OPTION_KEYS) {
    const rawValue = config.extra_options?.[key]
    const value = typeof rawValue === 'string' ? Number(rawValue) : rawValue
    if (typeof value === 'number' && Number.isFinite(value) && value > 0) {
      return Math.floor(value)
    }
  }
  return null
}

function formatTimestamp(value: string | null): string {
  if (!value) return t('pages.assistant.time.justNow')
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function toolRunKey(tool: ToolRun): string {
  return `${tool.source}:${tool.id}`
}

function isToolRunExpanded(tool: ToolRun): boolean {
  return expandedToolRuns.value[toolRunKey(tool)] === true
}

function toggleToolRun(tool: ToolRun) {
  const key = toolRunKey(tool)
  expandedToolRuns.value = {
    ...expandedToolRuns.value,
    [key]: !expandedToolRuns.value[key]
  }
}

function toolStatusLabel(tool: ToolRun): string {
  if (tool.status === 'running') return t('pages.assistant.toolTrace.running')
  if (typeof tool.status_code === 'number')
    return t('pages.assistant.toolTrace.http', { code: tool.status_code })
  return tool.status
}

function toolHeadline(tool: ToolRun): string {
  return tool.interface_key || tool.tool_name
}

function toolDetailLabel(tool: ToolRun): string {
  return isToolRunExpanded(tool)
    ? t('pages.assistant.toolTrace.hideDetails')
    : t('pages.assistant.toolTrace.viewDetails')
}

function formatJson(value: unknown): string {
  return JSON.stringify(value ?? {}, null, 2)
}

async function copyMessage(message: AIConversationMessage) {
  if (!navigator.clipboard?.writeText) return
  await navigator.clipboard.writeText(message.content)
  copiedMessageId.value = message.id
  window.setTimeout(() => {
    if (copiedMessageId.value === message.id) {
      copiedMessageId.value = null
    }
  }, 1600)
}

function normalizeToolRunFromHistory(toolCall: AIToolCallRecord): ToolRun {
  return {
    id: toolCall.id,
    tool_name: toolCall.tool_name,
    interface_key: toolCall.interface_key ?? null,
    arguments: { ...(toolCall.input_payload ?? {}) },
    result_summary: toolCall.result_summary ?? null,
    error: toolCall.error ?? null,
    duration_ms: toolCall.duration_ms ?? null,
    status_code: toolCall.status_code ?? null,
    created_at: toolCall.created_at ?? null,
    status: toolCall.status === 'error' ? 'error' : 'ok',
    source: 'history'
  }
}

function resetComposerState() {
  sending.value = false
  sendError.value = null
  pendingUserMessage.value = null
  streamingAssistantMessage.value = ''
  toolRuns.value = []
  expandedToolRuns.value = {}
}

function startNewConversation() {
  selectedConversationId.value = null
  selectedConversation.value = null
  selectedConversationError.value = null
  resetComposerState()
}

function ensureSelectedModel() {
  if (!canInspectModels.value) {
    selectedModelId.value = null
    return
  }
  const preferred =
    selectedConversation.value?.model_config_id ??
    clusterDetails.value?.ai?.default_model_id ??
    enabledModels.value[0]?.id ??
    null
  if (preferred && enabledModels.value.some((config) => config.id === preferred)) {
    selectedModelId.value = preferred
    return
  }
  selectedModelId.value = enabledModels.value[0]?.id ?? null
}

async function loadConfigs() {
  if (!aiAvailable.value || !canView.value || !canInspectModels.value) {
    configs.value = []
    configsError.value = null
    ensureSelectedModel()
    return
  }
  configsLoading.value = true
  configsError.value = null
  try {
    configs.value = await gateway.ai_configs(cluster)
    ensureSelectedModel()
  } catch (error: unknown) {
    configs.value = []
    configsError.value = error instanceof Error ? error.message : String(error)
  } finally {
    configsLoading.value = false
  }
}

async function loadConversation(conversationId: number) {
  selectedConversationLoading.value = true
  selectedConversationError.value = null
  try {
    const conversation = await gateway.ai_conversation(cluster, conversationId)
    selectedConversationId.value = conversation.id
    selectedConversation.value = conversation
    if (
      canInspectModels.value &&
      conversation.model_config_id &&
      enabledModels.value.some((config) => config.id === conversation.model_config_id)
    ) {
      selectedModelId.value = conversation.model_config_id
    }
  } catch (error: unknown) {
    selectedConversationError.value = error instanceof Error ? error.message : String(error)
  } finally {
    selectedConversationLoading.value = false
  }
}

async function loadConversations(preferredConversationId?: number | null) {
  if (!aiAvailable.value || !canView.value) {
    conversations.value = []
    selectedConversationId.value = null
    selectedConversation.value = null
    return
  }
  conversationsLoading.value = true
  conversationsError.value = null
  try {
    conversations.value = await gateway.ai_conversations(cluster)
    const targetId =
      preferredConversationId ?? selectedConversationId.value ?? conversations.value[0]?.id ?? null
    if (targetId) {
      await loadConversation(targetId)
    } else {
      selectedConversationId.value = null
      selectedConversation.value = null
    }
  } catch (error: unknown) {
    conversationsError.value = error instanceof Error ? error.message : String(error)
  } finally {
    conversationsLoading.value = false
  }
}

async function refreshAll() {
  await loadConfigs()
  await loadConversations()
}

function addToolRun(event: AIChatToolEvent, status: ToolRun['status']) {
  if (status === 'running') {
    toolRuns.value.push({
      tool_name: event.tool_name,
      interface_key: event.interface_key ?? null,
      arguments: { ...(event.arguments ?? {}) },
      result_summary: event.result_summary ?? null,
      error: event.error ?? null,
      duration_ms: event.duration_ms ?? null,
      status_code: event.status_code ?? null,
      created_at: null,
      id: Date.now() + toolRuns.value.length,
      status,
      source: 'live'
    })
    return
  }
  for (let index = toolRuns.value.length - 1; index >= 0; index -= 1) {
    if (
      toolRuns.value[index].tool_name === event.tool_name &&
      toolRuns.value[index].interface_key === (event.interface_key ?? null) &&
      toolRuns.value[index].status === 'running'
    ) {
      toolRuns.value[index] = {
        ...toolRuns.value[index],
        interface_key: event.interface_key ?? toolRuns.value[index].interface_key,
        arguments: { ...(event.arguments ?? toolRuns.value[index].arguments ?? {}) },
        result_summary: event.result_summary ?? null,
        error: event.error ?? null,
        duration_ms: event.duration_ms ?? null,
        status_code: event.status_code ?? null,
        status:
          typeof event.status_code === 'number' && event.status_code >= 400 ? 'error' : 'ok'
      }
      return
    }
  }
  toolRuns.value.push({
    tool_name: event.tool_name,
    interface_key: event.interface_key ?? null,
    arguments: { ...(event.arguments ?? {}) },
    result_summary: event.result_summary ?? null,
    error: event.error ?? null,
    duration_ms: event.duration_ms ?? null,
    status_code: event.status_code ?? null,
    created_at: null,
    id: Date.now() + toolRuns.value.length,
    status,
    source: 'live'
  })
}

async function deleteConversation(conversationId: number) {
  deletingConversationId.value = conversationId
  conversationsError.value = null
  try {
    await gateway.delete_ai_conversation(cluster, conversationId)
    if (selectedConversationId.value === conversationId) {
      startNewConversation()
    }
    await loadConversations()
  } catch (error: unknown) {
    conversationsError.value = error instanceof Error ? error.message : String(error)
  } finally {
    deletingConversationId.value = null
  }
}

async function submitMessage() {
  const message = draft.value.trim()
  if (tokenLimitExceeded.value) {
    sendError.value = t('pages.assistant.errors.tokenExceeded', {
      current: estimatedTokenCount.value,
      limit: tokenLimit.value
    })
    return
  }
  if (!canSend.value) return

  const sessionModelId =
    selectedModelId.value ??
    selectedConversation.value?.model_config_id ??
    clusterDetails.value?.ai?.default_model_id ??
    null
  if (!sessionModelId && canInspectModels.value) {
    sendError.value = t('pages.assistant.errors.noEnabledModel')
    return
  }

  sending.value = true
  sendError.value = null
  lastSubmittedPrompt.value = message
  pendingUserMessage.value = message
  streamingAssistantMessage.value = ''
  toolRuns.value = []
  draft.value = ''

  const session = gateway.stream_ai_chat(
    cluster,
    {
      message,
      conversation_id: selectedConversationId.value,
      model_config_id: sessionModelId ?? undefined
    },
    {
      onConversation(event) {
        selectedConversationId.value = event.conversation_id
      },
      onContent(delta) {
        streamingAssistantMessage.value += delta
      },
      onToolStart(event) {
        addToolRun(event, 'running')
      },
      onToolEnd(event) {
        addToolRun(event, typeof event.status_code === 'number' && event.status_code >= 400 ? 'error' : 'ok')
      },
      onComplete(event) {
        selectedConversationId.value = event.conversation_id
        if (typeof event.model_config_id === 'number') {
          selectedModelId.value = event.model_config_id
        }
      },
      onError(message) {
        sendError.value = message
      }
    }
  )

  try {
    await session.finished
    if (selectedConversationId.value) {
      await loadConversations(selectedConversationId.value)
    } else {
      await loadConversations()
    }
  } catch (error: unknown) {
    if (!sendError.value) {
      sendError.value = error instanceof Error ? error.message : String(error)
    }
  } finally {
    pendingUserMessage.value = null
    streamingAssistantMessage.value = ''
    sending.value = false
  }
}

function retryLastPrompt() {
  if (!lastSubmittedPrompt.value) return
  draft.value = lastSubmittedPrompt.value
}

function scrollMessagesToBottom() {
  if (!messageScroller.value) return
  messageScroller.value.scrollTop = messageScroller.value.scrollHeight
}

watch(
  () => cluster,
  async () => {
    startNewConversation()
    conversations.value = []
    configs.value = []
    await refreshAll()
  },
  { immediate: true }
)

watch(
  () => [renderedMessages.value.length, streamingAssistantMessage.value, displayToolRuns.value.length],
  async () => {
    await nextTick()
    scrollMessagesToBottom()
  }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="ai"
    :cluster="cluster"
    :breadcrumb="[{ title: 'shell.mainMenu.ai' }]"
  >
    <div class="ui-page ui-page-wide ui-content-workspace">
      <PageHeader
        kicker="pages.assistant.kicker"
        title="pages.assistant.title"
        description="pages.assistant.description"
      >
        <template #actions>
          <RouterLink
            v-if="canManage"
            :to="{ name: 'admin-ai', params: { cluster } }"
            class="ui-button-secondary"
          >
            {{ t('pages.assistant.actions.manageModels') }}
          </RouterLink>
          <button type="button" class="ui-button-primary" :disabled="sending" @click="startNewConversation">
            {{ t('pages.assistant.actions.newChat') }}
          </button>
        </template>
      </PageHeader>

      <InfoAlert v-if="!aiAvailable">
        {{ t('pages.assistant.alerts.unavailable') }}
      </InfoAlert>
      <InfoAlert v-else-if="!canView">
        {{ t('pages.assistant.alerts.noPermission') }}
      </InfoAlert>
            <ErrorAlert v-else-if="configsError">
              {{ configsError }}
            </ErrorAlert>

      <template v-else>
        <div
          data-testid="assistant-workspace"
          class="ui-assistant-workspace min-h-0 flex-1 gap-4 xl:grid-cols-[320px_minmax(0,1fr)]"
        >
          <aside class="ui-panel ui-section ui-panel-stack min-h-0 overflow-hidden">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="ui-page-kicker">{{ t('pages.assistant.history.kicker') }}</p>
                <h2 class="ui-panel-title">{{ t('pages.assistant.history.title') }}</h2>
              </div>
              <button type="button" class="ui-button-secondary" :disabled="conversationsLoading" @click="loadConversations()">
                {{ t('common.buttons.refresh') }}
              </button>
            </div>

            <ErrorAlert v-if="conversationsError">
              {{ conversationsError }}
            </ErrorAlert>

            <div v-if="conversationsLoading" class="text-[var(--color-brand-muted)]">
              <LoadingSpinner :size="5" />
              {{ t('pages.assistant.history.loading') }}
            </div>

            <InfoAlert v-else-if="conversations.length === 0">
              {{ t('pages.assistant.history.empty') }}
            </InfoAlert>

            <div v-else class="ui-scroll-region space-y-3 pr-1">
              <article
                v-for="conversation in conversations"
                :key="conversation.id"
                class="w-full rounded-[22px] border px-4 py-3 text-left transition"
                :class="
                  selectedConversationId === conversation.id
                    ? 'border-[rgba(182,232,44,0.55)] bg-[rgba(182,232,44,0.12)]'
                    : 'border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)]'
                "
              >
                <div class="flex items-start justify-between gap-3">
                  <button type="button" class="min-w-0 flex-1 text-left" @click="loadConversation(conversation.id)">
                    <p class="truncate font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ conversation.title }}
                    </p>
                  </button>
                  <button
                    type="button"
                    class="rounded-full p-2 text-[var(--color-brand-muted)] transition hover:bg-white hover:text-red-600"
                    :disabled="deletingConversationId === conversation.id"
                    :title="t('pages.assistant.history.deleteTitle')"
                    @click="deleteConversation(conversation.id)"
                  >
                    <TrashIcon class="h-4 w-4" aria-hidden="true" />
                  </button>
                </div>
                <p class="mt-3 text-xs text-[var(--color-brand-muted)]">
                  {{ t('pages.assistant.history.updated', { time: formatTimestamp(conversation.updated_at) }) }}
                </p>
              </article>
            </div>
          </aside>

          <section class="ui-panel ui-section ui-panel-stack min-w-0 min-h-0 overflow-hidden">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p class="ui-page-kicker">{{ t('pages.assistant.workspace.kicker') }}</p>
                <h2 class="ui-panel-title">
                  {{ selectedConversation?.title || t('pages.assistant.workspace.newConversation') }}
                </h2>
              </div>
              <div class="flex flex-wrap gap-2">
                <span class="ui-chip">{{ t('pages.assistant.workspace.cluster', { cluster }) }}</span>
              </div>
            </div>

            <ErrorAlert v-if="selectedConversationError">
              {{ selectedConversationError }}
            </ErrorAlert>
            <ErrorAlert v-if="sendError">
              {{ sendError }}
            </ErrorAlert>
            <InfoAlert v-if="!hasUsableModel">
              {{ t('pages.assistant.alerts.noEnabledModel') }}
            </InfoAlert>

            <div class="grid min-h-0 flex-1 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
              <div data-testid="assistant-chat-column" class="flex min-w-0 min-h-0 flex-col gap-4">
                <div
                  ref="messageScroller"
                  data-testid="assistant-message-scroller"
                  class="ui-assistant-chat-scroll ui-scroll-region min-h-0 flex-1 rounded-[28px] border border-[rgba(80,105,127,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(239,244,246,0.84))] px-4 py-4 sm:px-5"
                >
                  <div v-if="selectedConversationLoading || configsLoading" class="text-[var(--color-brand-muted)]">
                    <LoadingSpinner :size="5" />
                    {{ t('pages.assistant.workspace.loading') }}
                  </div>

                  <div v-else-if="renderedMessages.length === 0" class="flex h-full flex-col gap-6">
                    <div class="rounded-[24px] border border-[rgba(80,105,127,0.12)] bg-white/80 px-5 py-5">
                      <p class="ui-page-kicker">{{ t('pages.assistant.ready.kicker') }}</p>
                      <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                        {{ t('pages.assistant.ready.title') }}
                      </h3>
                      <p class="mt-3 text-sm leading-6 text-[var(--color-brand-muted)]">
                        {{ t('pages.assistant.ready.description') }}
                      </p>
                    </div>
                    <div class="mt-auto flex flex-wrap gap-2">
                      <button
                        type="button"
                        class="ui-button-ghost"
                        @click="draft = t('pages.assistant.prompts.summarizeClusterPrompt')"
                      >
                        {{ t('pages.assistant.prompts.summarizeCluster') }}
                      </button>
                      <button
                        type="button"
                        class="ui-button-ghost"
                        @click="draft = t('pages.assistant.prompts.bestNodeNowPrompt')"
                      >
                        {{ t('pages.assistant.prompts.bestNodeNow') }}
                      </button>
                      <button
                        type="button"
                        class="ui-button-ghost"
                        @click="draft = t('pages.assistant.prompts.analyzeJobPrompt')"
                      >
                        {{ t('pages.assistant.prompts.analyzeJob') }}
                      </button>
                    </div>
                  </div>

                  <div v-else class="space-y-4">
                    <article
                      v-for="message in renderedMessages"
                      :key="message.id"
                      class="flex"
                      :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
                    >
                      <div
                        class="max-w-3xl rounded-[24px] px-4 py-3 shadow-[var(--shadow-soft)]"
                        :class="
                          message.role === 'user'
                            ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.92),rgba(152,201,31,0.92))] text-[var(--color-brand-deep)]'
                            : 'border border-[rgba(80,105,127,0.12)] bg-white text-[var(--color-brand-ink-strong)]'
                        "
                      >
                        <div class="flex items-center justify-between gap-3 text-xs font-semibold tracking-[0.12em] uppercase">
                          <span>
                            {{
                              message.role === 'user'
                                ? t('pages.assistant.messages.user')
                                : t('pages.assistant.messages.assistant')
                            }}
                          </span>
                          <div class="flex items-center gap-2">
                            <span class="opacity-70">{{ formatTimestamp(message.created_at) }}</span>
                            <button
                              type="button"
                              class="rounded-full p-1.5 opacity-70 transition hover:bg-black/5 hover:opacity-100"
                              :title="
                                copiedMessageId === message.id
                                  ? t('pages.assistant.messages.copied')
                                  : t('pages.assistant.messages.copyMessage')
                              "
                              @click="copyMessage(message)"
                            >
                              <ClipboardDocumentIcon class="h-4 w-4" aria-hidden="true" />
                            </button>
                          </div>
                        </div>
                        <p
                          v-if="message.id === '__pending-assistant__' && !message.content"
                          class="mt-3 animate-pulse text-sm text-[var(--color-brand-muted)]"
                        >
                          {{ t('pages.assistant.messages.generating') }}
                        </p>
                        <MarkdownMessage
                          v-else
                          class="mt-3 text-sm leading-6"
                          :content="message.content"
                          :role="message.role"
                        />
                      </div>
                    </article>
                  </div>
                </div>

                <form data-testid="assistant-composer" class="shrink-0 space-y-3" @submit.prevent="submitMessage">
                  <textarea
                    v-model="draft"
                    rows="4"
                    :disabled="!canView || !hasUsableModel || sending"
                    class="block w-full rounded-[28px] border border-[rgba(80,105,127,0.16)] bg-white px-5 py-4 text-sm leading-6 text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    :placeholder="t('pages.assistant.composer.placeholder')"
                  />
                  <div class="flex flex-wrap items-center justify-between gap-3">
                    <div class="text-sm text-[var(--color-brand-muted)]">
                      <span
                        class="font-semibold"
                        :class="tokenLimitExceeded ? 'text-red-600' : 'text-[var(--color-brand-ink-strong)]'"
                      >
                        {{ t('pages.assistant.composer.estimatedTokens', { current: estimatedTokenCount, limit: tokenLimit }) }}
                      </span>
                      <p v-if="tokenLimitExceeded" class="mt-1 text-red-600">
                        {{ t('pages.assistant.composer.tokenExceededHint') }}
                      </p>
                    </div>
                    <div class="flex flex-wrap gap-2">
                      <button type="button" class="ui-button-secondary" :disabled="sending" @click="draft = ''">
                        {{ t('common.buttons.clear') }}
                      </button>
                      <button type="submit" class="ui-button-primary" :disabled="!canSend">
                        {{ t('common.buttons.send') }}
                      </button>
                    </div>
                  </div>
                </form>
              </div>

              <aside class="ui-scroll-region min-h-0 space-y-4 pr-1">
                <div class="ui-panel-soft px-4 py-4">
                  <p class="ui-page-kicker">{{ t('pages.assistant.toolTrace.kicker') }}</p>
                  <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ t('pages.assistant.toolTrace.title') }}
                  </h3>
                  <div v-if="displayToolRuns.length === 0" class="mt-3 text-sm text-[var(--color-brand-muted)]">
                    {{ t('pages.assistant.toolTrace.empty') }}
                  </div>
                  <div v-else class="mt-4 space-y-3">
                    <div
                      v-for="tool in displayToolRuns"
                      :key="toolRunKey(tool)"
                      class="rounded-[20px] border border-[rgba(80,105,127,0.12)] bg-white px-4 py-3"
                    >
                      <button type="button" class="w-full text-left" @click="toggleToolRun(tool)">
                        <div class="flex flex-col gap-2">
                          <div class="min-w-0">
                            <p class="break-words text-sm font-semibold leading-5 text-[var(--color-brand-ink-strong)]">
                              {{ toolHeadline(tool) }}
                            </p>
                          </div>
                          <div class="flex flex-wrap items-center gap-2">
                            <span class="ui-chip">
                              {{ toolStatusLabel(tool) }}
                            </span>
                            <span class="text-xs font-medium text-[var(--color-brand-muted)]">
                              {{ toolDetailLabel(tool) }}
                            </span>
                          </div>
                        </div>
                      </button>
                      <div v-if="isToolRunExpanded(tool)" class="mt-3 space-y-2">
                        <p class="text-xs text-[var(--color-brand-muted)]">
                          {{ t('pages.assistant.toolTrace.tool', { value: tool.tool_name }) }}
                        </p>
                        <p v-if="tool.interface_key" class="text-xs text-[var(--color-brand-muted)]">
                          {{ t('pages.assistant.toolTrace.interface', { value: tool.interface_key }) }}
                        </p>
                        <p class="text-xs text-[var(--color-brand-muted)]">
                          {{ t('pages.assistant.toolTrace.status', { value: toolStatusLabel(tool) }) }}
                        </p>
                        <p class="text-xs text-[var(--color-brand-muted)]">
                          {{
                            t('pages.assistant.toolTrace.duration', {
                              value:
                                tool.status === 'running'
                                  ? t('pages.assistant.toolTrace.pending')
                                  : `${tool.duration_ms ?? 0} ms`
                            })
                          }}
                        </p>
                        <p class="text-xs text-[var(--color-brand-muted)]">
                          {{ formatTimestamp(tool.created_at) }}
                        </p>
                        <p class="text-xs text-[var(--color-brand-muted)]">
                          {{ t('pages.assistant.toolTrace.tool', { value: tool.tool_name }) }}
                        </p>
                        <pre class="max-h-48 overflow-auto whitespace-pre-wrap break-words rounded-[14px] bg-[rgba(32,42,53,0.04)] px-3 py-2 font-mono text-xs leading-5 text-[var(--color-brand-muted)]">{{ formatJson(tool.arguments) }}</pre>
                        <p v-if="tool.result_summary" class="break-words text-sm leading-6 text-[var(--color-brand-muted)]">
                          {{ tool.result_summary }}
                        </p>
                        <p v-if="tool.error" class="break-words text-sm leading-6 text-red-600">
                          {{ tool.error }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="ui-panel-soft px-4 py-4">
                  <p class="ui-page-kicker">{{ t('pages.assistant.retry.kicker') }}</p>
                  <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ t('pages.assistant.retry.title') }}
                  </h3>
                  <p class="mt-3 text-sm text-[var(--color-brand-muted)]">
                    {{ lastSubmittedPrompt || t('pages.assistant.retry.empty') }}
                  </p>
                  <button
                    type="button"
                    class="ui-button-secondary mt-4"
                    :disabled="!lastSubmittedPrompt || sending"
                    @click="retryLastPrompt"
                  >
                    {{ t('pages.assistant.actions.reusePrompt') }}
                  </button>
                </div>
              </aside>
            </div>
          </section>
        </div>
      </template>
    </div>
  </ClusterMainLayout>
</template>

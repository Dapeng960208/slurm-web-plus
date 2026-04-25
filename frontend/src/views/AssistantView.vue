<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import type {
  AIChatToolEvent,
  AIConversation,
  AIConversationMessage,
  AIConversationSummary,
  AIModelConfig,
  ClusterDescription
} from '@/composables/GatewayAPI'
import { hasClusterAIAssistant, useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

type ToolRun = AIChatToolEvent & {
  id: number
  status: 'running' | 'done'
}

const { cluster } = defineProps<{ cluster: string }>()

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

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
const messageScroller = ref<HTMLElement | null>(null)

const clusterDetails = computed<ClusterDescription | undefined>(() =>
  runtimeStore.availableClusters.find((value) => value.name === cluster)
)
const aiAvailable = computed(() => hasClusterAIAssistant(clusterDetails.value))
const canView = computed(() => runtimeStore.hasRoutePermission(cluster, 'ai', 'view'))
const canManage = computed(
  () =>
    runtimeStore.hasRoutePermission(cluster, 'admin/ai', 'edit') ||
    runtimeStore.hasRoutePermission(cluster, 'settings/ai', 'edit')
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
const selectedModel = computed(
  () => enabledModels.value.find((config) => config.id === selectedModelId.value) ?? null
)
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
const canSend = computed(
  () => canView.value && enabledModels.value.length > 0 && draft.value.trim().length > 0 && !sending.value
)

function formatTimestamp(value: string | null): string {
  if (!value) return 'Just now'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function providerLabel(config: AIModelConfig | null): string {
  if (!config) return 'No model selected'
  return config.provider_label || config.provider
}

function resetComposerState() {
  sending.value = false
  sendError.value = null
  pendingUserMessage.value = null
  streamingAssistantMessage.value = ''
  toolRuns.value = []
}

function startNewConversation() {
  selectedConversationId.value = null
  selectedConversation.value = null
  selectedConversationError.value = null
  resetComposerState()
}

function ensureSelectedModel() {
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
  if (!aiAvailable.value || !canView.value) {
    configs.value = []
    selectedModelId.value = null
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
      id: Date.now() + toolRuns.value.length,
      status,
      ...event
    })
    return
  }
  for (let index = toolRuns.value.length - 1; index >= 0; index -= 1) {
    if (
      toolRuns.value[index].tool_name === event.tool_name &&
      toolRuns.value[index].status === 'running'
    ) {
      toolRuns.value[index] = {
        ...toolRuns.value[index],
        ...event,
        status: 'done'
      }
      return
    }
  }
  toolRuns.value.push({
    id: Date.now() + toolRuns.value.length,
    status,
    ...event
  })
}

async function submitMessage() {
  const message = draft.value.trim()
  if (!canSend.value) return

  const sessionModelId = selectedModelId.value
  if (!sessionModelId) {
    sendError.value = 'No enabled model is available for this cluster.'
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
      model_config_id: sessionModelId
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
        addToolRun(event, 'done')
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
  () => [renderedMessages.value.length, streamingAssistantMessage.value, toolRuns.value.length],
  async () => {
    await nextTick()
    scrollMessagesToBottom()
  }
)
</script>

<template>
  <ClusterMainLayout menu-entry="ai" :cluster="cluster" :breadcrumb="[{ title: 'AI' }]">
    <div class="ui-page ui-page-wide">
      <PageHeader
        kicker="Cluster Copilot"
        title="AI"
        description="Use enabled cluster models for multi-turn chat, model switching, and live tool trace visibility."
        :metric-value="enabledModels.length"
        metric-label="enabled models"
      >
        <template #actions>
          <RouterLink
            v-if="canManage"
            :to="{ name: 'admin-ai', params: { cluster } }"
            class="ui-button-secondary"
          >
            Manage models
          </RouterLink>
          <button type="button" class="ui-button-primary" :disabled="sending" @click="startNewConversation">
            New chat
          </button>
        </template>
      </PageHeader>

      <InfoAlert v-if="!aiAvailable">
        This cluster does not expose AI capability.
      </InfoAlert>
      <InfoAlert v-else-if="!canView">
        The current user does not have permission to use the AI workspace.
      </InfoAlert>
      <ErrorAlert v-else-if="configsError">
        {{ configsError }}
      </ErrorAlert>

      <template v-else>
        <div class="ui-summary-strip">
          <div class="ui-summary-item">
            <div class="ui-summary-label">Model</div>
            <div class="ui-summary-value">{{ selectedModel?.display_name || 'Not selected' }}</div>
            <div class="ui-summary-subtle">{{ providerLabel(selectedModel) }}</div>
          </div>
          <div class="ui-summary-item">
            <div class="ui-summary-label">Streaming</div>
            <div class="ui-summary-value">
              {{ clusterDetails?.ai?.streaming ? 'Enabled' : 'Unavailable' }}
            </div>
            <div class="ui-summary-subtle">SSE incremental responses</div>
          </div>
          <div class="ui-summary-item">
            <div class="ui-summary-label">Persistence</div>
            <div class="ui-summary-value">
              {{ clusterDetails?.ai?.persistence ? 'Enabled' : 'Unavailable' }}
            </div>
            <div class="ui-summary-subtle">User-owned conversation history</div>
          </div>
          <div class="ui-summary-item">
            <div class="ui-summary-label">Available</div>
            <div class="ui-summary-value">{{ enabledModels.length }}</div>
            <div class="ui-summary-subtle">Enabled model configs in this cluster</div>
          </div>
        </div>

        <div class="mt-4 grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
          <aside class="ui-panel ui-section ui-panel-stack">
            <div class="flex items-start justify-between gap-3">
              <div>
                <p class="ui-page-kicker">History</p>
                <h2 class="ui-panel-title">Conversations</h2>
                <p class="ui-panel-description mt-2">
                  Only your own cluster conversations are shown here.
                </p>
              </div>
              <button type="button" class="ui-button-secondary" :disabled="conversationsLoading" @click="loadConversations()">
                Refresh
              </button>
            </div>

            <div class="ui-panel-soft mt-2 px-4 py-4">
              <label class="block text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                Active model
              </label>
              <select
                v-model="selectedModelId"
                :disabled="configsLoading || enabledModels.length === 0 || sending"
                class="mt-3 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm text-[var(--color-brand-ink-strong)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
              >
                <option :value="null" disabled>Select a model</option>
                <option v-for="config in enabledModels" :key="config.id" :value="config.id">
                  {{ config.display_name }} / {{ config.model }}
                </option>
              </select>
              <p class="mt-3 text-xs text-[var(--color-brand-muted)]">
                Chat requests send the selected `model_config_id` explicitly.
              </p>
            </div>

            <ErrorAlert v-if="conversationsError">
              {{ conversationsError }}
            </ErrorAlert>

            <div v-if="conversationsLoading" class="text-[var(--color-brand-muted)]">
              <LoadingSpinner :size="5" />
              Loading conversations...
            </div>

            <InfoAlert v-else-if="conversations.length === 0">
              Start a prompt to create the first conversation.
            </InfoAlert>

            <div v-else class="space-y-3">
              <button
                v-for="conversation in conversations"
                :key="conversation.id"
                type="button"
                class="w-full rounded-[22px] border px-4 py-4 text-left transition"
                :class="
                  selectedConversationId === conversation.id
                    ? 'border-[rgba(182,232,44,0.55)] bg-[rgba(182,232,44,0.12)]'
                    : 'border-[rgba(80,105,127,0.1)] bg-[rgba(244,248,251,0.82)]'
                "
                @click="loadConversation(conversation.id)"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <p class="truncate font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ conversation.title }}
                    </p>
                    <p class="mt-1 line-clamp-2 text-sm text-[var(--color-brand-muted)]">
                      {{ conversation.last_message || 'No assistant reply yet.' }}
                    </p>
                  </div>
                  <span class="ui-chip">
                    {{
                      enabledModels.find((config) => config.id === conversation.model_config_id)?.display_name ||
                      `#${conversation.model_config_id ?? '-'}`
                    }}
                  </span>
                </div>
                <p class="mt-3 text-xs text-[var(--color-brand-muted)]">
                  Updated {{ formatTimestamp(conversation.updated_at) }}
                </p>
              </button>
            </div>
          </aside>

          <section class="ui-panel ui-section ui-panel-stack min-w-0">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <p class="ui-page-kicker">Workspace</p>
                <h2 class="ui-panel-title">
                  {{ selectedConversation?.title || 'New cluster conversation' }}
                </h2>
                <p class="ui-panel-description mt-2">
                  The assistant can only use read-only tools and must stay within current permissions.
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <span class="ui-chip">Cluster {{ cluster }}</span>
                <span class="ui-chip">{{ selectedModel?.display_name || 'No model' }}</span>
              </div>
            </div>

            <ErrorAlert v-if="selectedConversationError">
              {{ selectedConversationError }}
            </ErrorAlert>
            <ErrorAlert v-if="sendError">
              {{ sendError }}
            </ErrorAlert>
            <InfoAlert v-if="enabledModels.length === 0">
              No enabled model exists for this cluster yet. Create one in Admin > AI first.
            </InfoAlert>

            <div class="grid gap-4 lg:grid-cols-[minmax(0,1fr)_280px]">
              <div
                ref="messageScroller"
                class="min-h-[30rem] max-h-[38rem] overflow-y-auto rounded-[28px] border border-[rgba(80,105,127,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(239,244,246,0.84))] px-4 py-4 sm:px-5"
              >
                <div v-if="selectedConversationLoading || configsLoading" class="text-[var(--color-brand-muted)]">
                  <LoadingSpinner :size="5" />
                  Loading AI workspace...
                </div>

                <div v-else-if="renderedMessages.length === 0" class="flex h-full flex-col justify-between gap-6">
                  <div class="rounded-[24px] border border-[rgba(80,105,127,0.12)] bg-white/80 px-5 py-5">
                    <p class="ui-page-kicker">Ready</p>
                    <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                      Ask about jobs, nodes, partitions, or metrics in this cluster
                    </h3>
                    <p class="mt-3 text-sm leading-6 text-[var(--color-brand-muted)]">
                      Example topics include job state analysis, idle node ranking, and cluster resource summaries.
                    </p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button type="button" class="ui-button-ghost" @click="draft = 'Summarize current cluster load and queue pressure.'">
                      Summarize cluster
                    </button>
                    <button type="button" class="ui-button-ghost" @click="draft = 'Which node has the most remaining resources right now?'">
                      Best node now
                    </button>
                    <button type="button" class="ui-button-ghost" @click="draft = 'Explain the current state of job 12345 and possible reasons.'">
                      Analyze job 12345
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
                        <span>{{ message.role }}</span>
                        <span class="opacity-70">{{ formatTimestamp(message.created_at) }}</span>
                      </div>
                      <p
                        v-if="message.id === '__pending-assistant__' && !message.content"
                        class="mt-3 animate-pulse text-sm text-[var(--color-brand-muted)]"
                      >
                        Generating response...
                      </p>
                      <p v-else class="mt-3 text-sm leading-6 whitespace-pre-wrap">
                        {{ message.content }}
                      </p>
                    </div>
                  </article>
                </div>
              </div>

              <aside class="space-y-4">
                <div class="ui-panel-soft px-4 py-4">
                  <p class="ui-page-kicker">Tool Calls</p>
                  <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                    Execution trace
                  </h3>
                  <div v-if="toolRuns.length === 0" class="mt-3 text-sm text-[var(--color-brand-muted)]">
                    Tool events for the current run appear here.
                  </div>
                  <div v-else class="mt-4 space-y-3">
                    <div
                      v-for="tool in toolRuns"
                      :key="tool.id"
                      class="rounded-[20px] border border-[rgba(80,105,127,0.12)] bg-white px-4 py-3"
                    >
                      <div class="flex items-center justify-between gap-3">
                        <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
                          {{ tool.tool_name }}
                        </p>
                        <span class="ui-chip">
                          {{ tool.status === 'running' ? 'running' : `${tool.duration_ms ?? 0} ms` }}
                        </span>
                      </div>
                      <p class="mt-2 text-xs text-[var(--color-brand-muted)]">
                        {{ JSON.stringify(tool.arguments ?? {}) }}
                      </p>
                      <p v-if="tool.result_summary" class="mt-2 text-sm text-[var(--color-brand-muted)]">
                        {{ tool.result_summary }}
                      </p>
                    </div>
                  </div>
                </div>

                <div class="ui-panel-soft px-4 py-4">
                  <p class="ui-page-kicker">Retry</p>
                  <h3 class="text-base font-semibold text-[var(--color-brand-ink-strong)]">
                    Last prompt
                  </h3>
                  <p class="mt-3 text-sm text-[var(--color-brand-muted)]">
                    {{ lastSubmittedPrompt || 'No prompt sent yet.' }}
                  </p>
                  <button
                    type="button"
                    class="ui-button-secondary mt-4"
                    :disabled="!lastSubmittedPrompt || sending"
                    @click="retryLastPrompt"
                  >
                    Reuse prompt
                  </button>
                </div>
              </aside>
            </div>

            <form class="space-y-3" @submit.prevent="submitMessage">
              <textarea
                v-model="draft"
                rows="5"
                :disabled="!canView || enabledModels.length === 0 || sending"
                class="block w-full rounded-[28px] border border-[rgba(80,105,127,0.16)] bg-white px-5 py-4 text-sm leading-6 text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                placeholder="Ask about a job, node resources, partitions, or another read-only cluster question."
              />
              <div class="flex flex-wrap items-center justify-between gap-3">
                <p class="text-sm text-[var(--color-brand-muted)]">
                  Using model: {{ selectedModel?.display_name || 'Not selected' }}.
                </p>
                <div class="flex flex-wrap gap-2">
                  <button type="button" class="ui-button-secondary" :disabled="sending" @click="draft = ''">
                    Clear
                  </button>
                  <button type="submit" class="ui-button-primary" :disabled="!canSend">
                    Send
                  </button>
                </div>
              </div>
            </form>
          </section>
        </div>
      </template>
    </div>
  </ClusterMainLayout>
</template>

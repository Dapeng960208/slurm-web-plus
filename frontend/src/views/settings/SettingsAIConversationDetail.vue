<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import type { AIConversation } from '@/composables/GatewayAPI'
import { hasClusterAIAssistant, useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import AdminTabs from '@/components/admin/AdminTabs.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()

const props = defineProps<{
  cluster: string
  conversationId: number
}>()

const loading = ref(false)
const error = ref<string | null>(null)
const conversation = ref<AIConversation | null>(null)

const clusterName = computed(() => props.cluster)
const conversationId = computed(() => props.conversationId)
const currentCluster = computed(() => runtimeStore.currentCluster ?? runtimeStore.getCluster(clusterName.value))
const aiAvailable = computed(() => hasClusterAIAssistant(currentCluster.value))
const canView = computed(
  () => !!clusterName.value && runtimeStore.hasRoutePermission(clusterName.value, 'admin/ai', 'view')
)

function formatTimestamp(value: string | null): string {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

async function loadConversation() {
  if (!clusterName.value || !Number.isFinite(conversationId.value) || conversationId.value <= 0) {
    conversation.value = null
    error.value = 'Conversation id is invalid.'
    return
  }
  loading.value = true
  error.value = null
  try {
    conversation.value = await gateway.ai_admin_conversation(clusterName.value, conversationId.value)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : String(err)
    conversation.value = null
  } finally {
    loading.value = false
  }
}

watch(
  () => [clusterName.value, conversationId.value],
  async () => {
    await loadConversation()
  }
)

onMounted(async () => {
  await loadConversation()
})
</script>

<template>
  <div class="ui-section-stack">
    <AdminTabs entry="AI" :cluster="clusterName" />

    <div class="ui-panel ui-section">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <AdminHeader
          title="AI Conversation Detail"
          description="Inspect one audited conversation with full message history and tool execution records."
        />
        <div class="flex flex-wrap gap-2">
          <RouterLink :to="{ name: 'admin-ai', params: { cluster: clusterName } }" class="ui-button-secondary">
            Back to audit
          </RouterLink>
        </div>
      </div>
    </div>

    <InfoAlert v-if="!currentCluster">
      No cluster context is available for this admin route.
    </InfoAlert>
    <InfoAlert v-else-if="!aiAvailable">
      AI capability is not enabled for the current cluster.
    </InfoAlert>
    <InfoAlert v-else-if="!canView">
      The current user does not have permission to view AI audit data on this cluster.
    </InfoAlert>
    <ErrorAlert v-else-if="error">
      {{ error }}
    </ErrorAlert>

    <template v-else>
      <section class="ui-panel ui-section">
        <div v-if="loading" class="text-[var(--color-brand-muted)]">
          <LoadingSpinner :size="5" />
          Loading conversation detail...
        </div>

        <InfoAlert v-else-if="!conversation">
          Conversation detail is unavailable.
        </InfoAlert>

        <template v-else>
          <div class="ui-summary-strip">
            <div class="ui-summary-item">
              <p class="ui-summary-label">Title</p>
              <p class="ui-summary-value">{{ conversation.title }}</p>
            </div>
            <div class="ui-summary-item">
              <p class="ui-summary-label">User</p>
              <p class="ui-summary-value">{{ conversation.username || '-' }}</p>
            </div>
            <div class="ui-summary-item">
              <p class="ui-summary-label">Updated</p>
              <p class="ui-summary-value">{{ formatTimestamp(conversation.updated_at) }}</p>
            </div>
            <div class="ui-summary-item">
              <p class="ui-summary-label">State</p>
              <p class="ui-summary-value">{{ conversation.deleted_at ? 'Deleted' : 'Active' }}</p>
              <p v-if="conversation.deleted_at" class="ui-summary-subtle">
                {{ formatTimestamp(conversation.deleted_at) }}
              </p>
            </div>
          </div>

          <section class="mt-6">
            <h2 class="ui-panel-title">Messages</h2>
            <p class="ui-panel-description mt-2">
              Full conversation content is kept in chronological order and no longer competes with the main audit table.
            </p>
            <div class="mt-4 space-y-3">
              <article
                v-for="message in conversation.messages"
                :key="message.id"
                class="ui-metric-surface px-4 py-4"
              >
                <div class="flex flex-wrap items-center justify-between gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-[var(--color-brand-muted)]">
                  <span>{{ message.role }}</span>
                  <span>{{ formatTimestamp(message.created_at) }}</span>
                </div>
                <p class="mt-3 whitespace-pre-wrap break-words text-sm leading-6 text-[var(--color-brand-ink-strong)]">
                  {{ message.content }}
                </p>
              </article>
            </div>
          </section>

          <section class="mt-6">
            <h2 class="ui-panel-title">Tool calls</h2>
            <p class="ui-panel-description mt-2">
              Tool execution is separated from messages so operators can scan failures and latency without reading the full chat transcript.
            </p>
            <InfoAlert v-if="conversation.tool_calls.length === 0" class="mt-4">
              No tool calls were recorded for this conversation.
            </InfoAlert>
            <div v-else class="mt-4 ui-table-shell overflow-x-auto">
              <table class="ui-table min-w-[960px]">
                <thead>
                  <tr>
                    <th scope="col" class="py-3.5 pr-3 pl-6 text-left">Tool</th>
                    <th scope="col" class="px-3 py-3.5 text-left">Interface</th>
                    <th scope="col" class="px-3 py-3.5 text-left">Status</th>
                    <th scope="col" class="px-3 py-3.5 text-left">Code</th>
                    <th scope="col" class="px-3 py-3.5 text-left">Duration</th>
                    <th scope="col" class="px-3 py-3.5 text-left">Created</th>
                    <th scope="col" class="px-3 py-3.5 text-left">Summary</th>
                  </tr>
                </thead>
                <tbody class="text-sm text-[var(--color-brand-muted)]">
                  <tr v-for="toolCall in conversation.tool_calls" :key="toolCall.id">
                    <td class="py-4 pr-3 pl-6 align-top font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ toolCall.tool_name }}
                    </td>
                    <td class="px-3 py-4 align-top">{{ toolCall.interface_key || '-' }}</td>
                    <td class="px-3 py-4 align-top">{{ toolCall.status }}</td>
                    <td class="px-3 py-4 align-top">{{ toolCall.status_code ?? '-' }}</td>
                    <td class="px-3 py-4 align-top">{{ toolCall.duration_ms ?? 0 }} ms</td>
                    <td class="px-3 py-4 align-top">{{ formatTimestamp(toolCall.created_at ?? null) }}</td>
                    <td class="px-3 py-4 align-top">
                      <p class="max-w-[20rem] whitespace-pre-wrap break-words">
                        {{ toolCall.error || toolCall.result_summary || '-' }}
                      </p>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </template>
      </section>
    </template>
  </div>
</template>

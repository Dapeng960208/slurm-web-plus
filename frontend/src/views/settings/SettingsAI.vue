<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import type { AIConversationSummary, AIModelConfig, AIModelConfigPayload, AIProviderOption } from '@/composables/GatewayAPI'
import { hasClusterAIAssistant, useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import SettingsTabs from '@/components/settings/SettingsTabs.vue'
import SettingsHeader from '@/components/settings/SettingsHeader.vue'
import AdminTabs from '@/components/admin/AdminTabs.vue'
import AdminHeader from '@/components/admin/AdminHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import SettingsAIConfigModal from '@/components/settings/SettingsAIConfigModal.vue'

const FALLBACK_PROVIDERS: AIProviderOption[] = [
  { key: 'openai', label: 'OpenAI' },
  { key: 'azure-openai', label: 'Azure OpenAI' },
  { key: 'anthropic', label: 'Anthropic' },
  { key: 'google', label: 'Google Gemini' },
  { key: 'qwen', label: 'Qwen' },
  { key: 'deepseek', label: 'DeepSeek' },
  { key: 'kimi', label: 'Kimi' },
  { key: 'openai-compatible', label: 'OpenAI Compatible' },
  { key: 'ollama', label: 'Ollama' }
]

const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const route = useRoute()
const { t } = useI18n()

const isAdminRoute = computed(
  () => String(route.name ?? '').startsWith('admin-') || String(route.path ?? '').includes('/admin/')
)
const tabsComponent = computed(() => (isAdminRoute.value ? AdminTabs : SettingsTabs))
const headerComponent = computed(() => (isAdminRoute.value ? AdminHeader : SettingsHeader))

const loading = ref(false)
const error = ref<string | null>(null)
const submitError = ref<string | null>(null)
const submitSuccess = ref<string | null>(null)
const validatingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
const configs = ref<AIModelConfig[]>([])
const auditConversations = ref<AIConversationSummary[]>([])
const auditUsernameFilter = ref('')
const auditKeywordFilter = ref('')
const appliedAuditUsernameFilter = ref('')
const appliedAuditKeywordFilter = ref('')
const auditLoading = ref(false)
const auditError = ref<string | null>(null)
const modalOpen = ref(false)
const editingConfig = ref<AIModelConfig | null>(null)

const settingsCluster = computed(() => {
  if (runtimeStore.currentCluster) return runtimeStore.currentCluster
  const routeCluster = runtimeStore.beforeSettingsRoute?.params?.cluster
  if (typeof routeCluster === 'string') {
    const cluster = runtimeStore.getCluster(routeCluster)
    if (cluster) return cluster
  }
  return runtimeStore.getAllowedClusters()[0]
})

const currentClusterName = computed(() => settingsCluster.value?.name ?? '')
const aiAvailable = computed(() => hasClusterAIAssistant(settingsCluster.value))
const canManage = computed(
  () =>
    !!currentClusterName.value &&
    runtimeStore.hasRoutePermission(
      currentClusterName.value,
      isAdminRoute.value ? 'admin/ai' : 'settings/ai',
      'edit'
    )
)
const canDelete = computed(
  () =>
    !!currentClusterName.value &&
    runtimeStore.hasRoutePermission(
      currentClusterName.value,
      isAdminRoute.value ? 'admin/ai' : 'settings/ai',
      'delete'
    )
)
const canView = computed(
  () =>
    !!currentClusterName.value &&
    runtimeStore.hasRoutePermission(
      currentClusterName.value,
      isAdminRoute.value ? 'admin/ai' : 'settings/ai',
      'view'
    )
)
const canViewChat = computed(
  () => !!currentClusterName.value && runtimeStore.hasRoutePermission(currentClusterName.value, 'ai', 'view')
)
const providerOptions = computed(() => {
  const providers = settingsCluster.value?.ai?.providers ?? settingsCluster.value?.capabilities?.ai?.providers
  return providers && providers.length > 0 ? providers : FALLBACK_PROVIDERS
})
const sortedConfigs = computed(() =>
  [...configs.value].sort((left, right) => {
    if (left.is_default !== right.is_default) return left.is_default ? -1 : 1
    if (left.sort_order !== right.sort_order) return left.sort_order - right.sort_order
    return left.display_name.localeCompare(right.display_name)
  })
)
const filteredAuditConversations = computed(() => {
  const username = appliedAuditUsernameFilter.value.trim().toLowerCase()
  const keyword = appliedAuditKeywordFilter.value.trim().toLowerCase()
  return auditConversations.value.filter((conversation) => {
    const conversationUsername = (conversation.username ?? '').toLowerCase()
    const title = conversation.title.toLowerCase()
    return (!username || conversationUsername.includes(username)) && (!keyword || title.includes(keyword))
  })
})
function formatTimestamp(value: string | null): string {
  if (!value) return t('common.status.unavailable')
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function providerLabel(config: AIModelConfig): string {
  return (
    config.provider_label || providerOptions.value.find((option) => option.key === config.provider)?.label || config.provider
  )
}

function clearFeedback() {
  submitError.value = null
  submitSuccess.value = null
}

function applyAuditFilters() {
  appliedAuditUsernameFilter.value = auditUsernameFilter.value
  appliedAuditKeywordFilter.value = auditKeywordFilter.value
}

function resetAuditFilters() {
  auditUsernameFilter.value = ''
  auditKeywordFilter.value = ''
  applyAuditFilters()
}

function openCreateModal() {
  clearFeedback()
  editingConfig.value = null
  modalOpen.value = true
}

function openEditModal(config: AIModelConfig) {
  clearFeedback()
  editingConfig.value = config
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
}

async function loadConfigs() {
  if (!aiAvailable.value || !canView.value || !currentClusterName.value) {
    configs.value = []
    return
  }
  loading.value = true
  error.value = null
  try {
    configs.value = await gateway.ai_configs(currentClusterName.value)
  } catch (err: unknown) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    loading.value = false
  }
}

async function loadAuditConversations() {
  if (!isAdminRoute.value || !aiAvailable.value || !canView.value || !currentClusterName.value) {
    auditConversations.value = []
    return
  }
  auditLoading.value = true
  auditError.value = null
  try {
    auditConversations.value = await gateway.ai_admin_conversations(currentClusterName.value)
  } catch (err: unknown) {
    auditError.value = err instanceof Error ? err.message : String(err)
  } finally {
    auditLoading.value = false
  }
}

async function submitForm(payload: AIModelConfigPayload) {
  if (!currentClusterName.value) return
  clearFeedback()
  try {
    if (editingConfig.value === null) {
      await gateway.create_ai_config(currentClusterName.value, payload)
      submitSuccess.value = t('settings.ai.feedback.created')
    } else {
      await gateway.update_ai_config(currentClusterName.value, editingConfig.value.id, payload)
      submitSuccess.value = t('settings.ai.feedback.updated')
    }
    closeModal()
    await loadConfigs()
  } catch (err: unknown) {
    submitError.value = err instanceof Error ? err.message : String(err)
  }
}

async function toggleEnabled(config: AIModelConfig) {
  if (!currentClusterName.value) return
  clearFeedback()
  try {
    await gateway.update_ai_config(currentClusterName.value, config.id, {
      enabled: !config.enabled,
      is_default: config.enabled && config.is_default ? false : config.is_default
    })
    submitSuccess.value = t(
      config.enabled ? 'settings.ai.feedback.disabled' : 'settings.ai.feedback.enabled',
      { name: config.display_name }
    )
    await loadConfigs()
  } catch (err: unknown) {
    submitError.value = err instanceof Error ? err.message : String(err)
  }
}

async function setDefault(config: AIModelConfig) {
  if (!currentClusterName.value) return
  clearFeedback()
  try {
    await gateway.update_ai_config(currentClusterName.value, config.id, {
      enabled: true,
      is_default: true
    })
    submitSuccess.value = t('settings.ai.feedback.defaultSet', { name: config.display_name })
    await loadConfigs()
  } catch (err: unknown) {
    submitError.value = err instanceof Error ? err.message : String(err)
  }
}

async function validateConfig(config: AIModelConfig) {
  if (!currentClusterName.value) return
  clearFeedback()
  validatingId.value = config.id
  try {
    const result = await gateway.validate_ai_config(currentClusterName.value, config.id)
    submitSuccess.value = t('settings.ai.feedback.validated', {
      sample: result.sample || result.model
    })
    await loadConfigs()
  } catch (err: unknown) {
    submitError.value = err instanceof Error ? err.message : String(err)
  } finally {
    validatingId.value = null
  }
}

async function deleteConfig(config: AIModelConfig) {
  if (!currentClusterName.value) return
  clearFeedback()
  deletingId.value = config.id
  try {
    await gateway.delete_ai_config(currentClusterName.value, config.id)
    submitSuccess.value = t('settings.ai.feedback.deleted', { name: config.display_name })
    await loadConfigs()
  } catch (err: unknown) {
    submitError.value = err instanceof Error ? err.message : String(err)
  } finally {
    deletingId.value = null
  }
}

watch(
  () => currentClusterName.value,
  async () => {
    closeModal()
    clearFeedback()
    await loadConfigs()
    await loadAuditConversations()
  }
)

onMounted(async () => {
  await loadConfigs()
  await loadAuditConversations()
})
</script>

<template>
  <div class="ui-section-stack admin-ai-workspace">
    <component :is="tabsComponent" entry="ai" :cluster="currentClusterName" />

    <div class="ui-panel ui-section admin-ai-shell">
      <div class="admin-ai-hero">
        <component
          :is="headerComponent"
          title="settings.ai.title"
          description="settings.ai.description"
        />
        <div class="admin-ai-hero-actions">
          <RouterLink
            v-if="currentClusterName && canViewChat"
            :to="{ name: 'ai', params: { cluster: currentClusterName } }"
            class="ui-button-secondary"
          >
            {{ t('settings.ai.actions.goToChat') }}
          </RouterLink>
          <button
            type="button"
            class="ui-button-primary"
            :disabled="!canManage || !aiAvailable"
            :title="t('settings.ai.configs.actionTitles.create')"
            @click="openCreateModal"
          >
            {{ t('settings.ai.actions.newModel') }}
          </button>
        </div>
      </div>
    </div>

    <InfoAlert v-if="!settingsCluster">
      {{ t('settings.ai.alerts.noClusterContext') }}
    </InfoAlert>
    <InfoAlert v-else-if="!aiAvailable">
      {{ t('settings.ai.alerts.unavailable') }}
    </InfoAlert>
    <InfoAlert v-else-if="!canView">
      {{ t('settings.ai.alerts.noPermission') }}
    </InfoAlert>

    <template v-else>
      <div class="admin-ai-status-stack">
        <ErrorAlert v-if="error">
          {{ error }}
        </ErrorAlert>
        <ErrorAlert v-if="submitError">
          {{ submitError }}
        </ErrorAlert>
        <InfoAlert v-if="submitSuccess">
          {{ submitSuccess }}
        </InfoAlert>
        <InfoAlert v-if="!canManage">
          {{ t('settings.ai.alerts.readOnly') }}
        </InfoAlert>
      </div>

      <section class="ui-panel ui-section admin-ai-section">
        <div class="ui-page-tools">
          <div>
            <h2 class="ui-panel-title">{{ t('settings.ai.configs.title') }}</h2>
            <p class="ui-panel-description mt-2">
              {{ t('settings.ai.configs.description') }}
            </p>
          </div>
          <div class="ui-page-tools-end">
            <button type="button" class="ui-button-secondary" :disabled="loading" @click="loadConfigs">
              {{ t('common.buttons.refresh') }}
            </button>
          </div>
        </div>

        <div v-if="loading" class="mt-6 text-[var(--color-brand-muted)]">
          <LoadingSpinner :size="5" />
          {{ t('settings.ai.configs.loading') }}
        </div>

        <InfoAlert v-else-if="sortedConfigs.length === 0" class="mt-6">
          {{ t('settings.ai.configs.empty') }}
        </InfoAlert>

        <div v-else class="mt-6 ui-table-shell overflow-x-auto">
          <table class="ui-table min-w-[1100px]">
            <thead>
              <tr>
                <th scope="col" class="py-3.5 pr-3 pl-6 text-left">{{ t('settings.ai.configs.columns.displayName') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.provider') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.model') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.state') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.default') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.secret') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.validated') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.configs.columns.actions') }}</th>
              </tr>
            </thead>
            <tbody class="text-sm text-[var(--color-brand-muted)]">
              <tr
                v-for="config in sortedConfigs"
                :key="config.id"
                v-memo="[config, validatingId === config.id, deletingId === config.id, canManage, canDelete]"
                data-testid="ai-config-row"
              >
                <td class="py-4 pr-3 pl-6 align-top">
                  <div class="min-w-0">
                    <p class="font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ config.display_name }}
                    </p>
                    <p class="mt-1 break-all text-xs text-[var(--color-brand-muted)]">
                      {{ config.name }}
                    </p>
                  </div>
                </td>
                <td class="px-3 py-4 align-top">{{ providerLabel(config) }}</td>
                <td class="px-3 py-4 align-top">
                  <div class="min-w-0">
                    <p class="font-semibold text-[var(--color-brand-ink-strong)]">{{ config.model }}</p>
                    <p v-if="config.base_url" class="mt-1 break-all text-xs text-[var(--color-brand-muted)]">
                      {{ config.base_url }}
                    </p>
                  </div>
                </td>
                <td class="px-3 py-4 align-top">
                  <span class="ui-chip">
                    {{ config.enabled ? t('settings.ai.configs.state.enabled') : t('settings.ai.configs.state.disabled') }}
                  </span>
                </td>
                <td class="px-3 py-4 align-top">
                  <span v-if="config.is_default" class="ui-chip">{{ t('settings.ai.configs.state.default') }}</span>
                  <span v-else>-</span>
                </td>
                <td class="px-3 py-4 align-top">
                  <span v-if="config.secret_configured" class="font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ config.secret_mask || t('settings.ai.configs.state.configured') }}
                  </span>
                  <span v-else>{{ t('settings.ai.configs.state.notConfigured') }}</span>
                </td>
                <td class="px-3 py-4 align-top">
                  <p>{{ formatTimestamp(config.last_validated_at) }}</p>
                  <p v-if="config.last_validation_error" class="mt-1 max-w-56 text-xs text-[var(--color-brand-danger)]">
                    {{ config.last_validation_error }}
                  </p>
                </td>
                <td class="px-3 py-4 align-top">
                  <div class="flex flex-wrap gap-2">
                    <button
                      type="button"
                      class="ui-button-warning"
                      :disabled="!canManage"
                      :title="t('settings.ai.configs.actionTitles.edit')"
                      @click="openEditModal(config)"
                    >
                      {{ t('common.buttons.edit') }}
                    </button>
                    <button
                      type="button"
                      class="ui-button-secondary"
                      :disabled="validatingId === config.id || !canManage"
                      :title="t('settings.ai.configs.actionTitles.test')"
                      @click="validateConfig(config)"
                    >
                      {{
                        validatingId === config.id
                          ? t('settings.ai.actions.testing')
                          : t('settings.ai.actions.testConnection')
                      }}
                    </button>
                    <button
                      v-if="!config.is_default"
                      type="button"
                      class="ui-button-secondary"
                      :disabled="!canManage"
                      :title="t('settings.ai.configs.actionTitles.setDefault')"
                      @click="setDefault(config)"
                    >
                      {{ t('settings.ai.actions.setDefault') }}
                    </button>
                    <button
                      type="button"
                      class="ui-button-secondary"
                      :disabled="!canManage"
                      :title="t('settings.ai.configs.actionTitles.toggle')"
                      @click="toggleEnabled(config)"
                    >
                      {{ config.enabled ? t('common.buttons.disable') : t('common.buttons.enable') }}
                    </button>
                    <button
                      v-if="canDelete"
                      type="button"
                      class="ui-button-danger"
                      :disabled="deletingId === config.id"
                      :title="t('settings.ai.configs.actionTitles.delete')"
                      @click="deleteConfig(config)"
                    >
                      {{ deletingId === config.id ? t('settings.ai.actions.deleting') : t('common.buttons.delete') }}
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section v-if="isAdminRoute" class="ui-panel ui-section admin-ai-section admin-ai-section-muted">
        <div class="ui-page-tools">
          <div>
            <h2 class="ui-panel-title">{{ t('settings.ai.audit.title') }}</h2>
            <p class="ui-panel-description mt-2">
              {{ t('settings.ai.audit.description') }}
            </p>
          </div>
        </div>

        <ErrorAlert v-if="auditError" class="mt-5">
          {{ auditError }}
        </ErrorAlert>

        <div class="mt-5 ui-admin-search-bar">
          <div class="ui-admin-search-fields">
            <input
              v-model="auditUsernameFilter"
              data-testid="audit-username-filter"
              type="search"
              class="ui-input-field ui-admin-search-field"
              :aria-label="t('settings.ai.audit.filters.username')"
              :placeholder="t('settings.ai.audit.filters.usernamePlaceholder')"
              @keyup.enter="applyAuditFilters"
            />
            <input
              v-model="auditKeywordFilter"
              data-testid="audit-keyword-filter"
              type="search"
              class="ui-input-field ui-admin-search-field"
              :aria-label="t('settings.ai.audit.filters.title')"
              :placeholder="t('settings.ai.audit.filters.titlePlaceholder')"
              @keyup.enter="applyAuditFilters"
            />
          </div>
          <div class="ui-admin-search-actions">
            <button type="button" class="ui-button-primary" @click="applyAuditFilters">
              {{ t('common.buttons.search') }}
            </button>
            <button type="button" class="ui-button-secondary" @click="resetAuditFilters">
              {{ t('common.buttons.reset') }}
            </button>
            <button type="button" class="ui-button-secondary" :disabled="auditLoading" @click="loadAuditConversations">
              {{ t('common.buttons.refresh') }}
            </button>
          </div>
        </div>

        <div v-if="auditLoading" class="mt-6 text-[var(--color-brand-muted)]">
          <LoadingSpinner :size="5" />
          {{ t('settings.ai.audit.loading') }}
        </div>
        <InfoAlert v-else-if="auditConversations.length === 0" class="mt-6">
          {{ t('settings.ai.audit.empty') }}
        </InfoAlert>
        <InfoAlert v-else-if="filteredAuditConversations.length === 0" class="mt-6">
          {{ t('settings.ai.audit.noMatch') }}
        </InfoAlert>

        <div v-else class="mt-6 ui-table-shell overflow-x-auto">
          <table class="ui-table min-w-[980px]">
            <thead>
              <tr>
                <th scope="col" class="py-3.5 pr-3 pl-6 text-left">{{ t('settings.ai.audit.columns.title') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.audit.columns.user') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.audit.columns.state') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.audit.columns.updated') }}</th>
                <th scope="col" class="px-3 py-3.5 text-left">{{ t('settings.ai.audit.columns.details') }}</th>
              </tr>
            </thead>
            <tbody class="text-sm text-[var(--color-brand-muted)]">
              <tr
                v-for="conversation in filteredAuditConversations"
                :key="conversation.id"
                v-memo="[conversation, currentClusterName]"
              >
                <td class="py-4 pr-3 pl-6 align-top font-semibold text-[var(--color-brand-ink-strong)]">
                  <span class="block max-w-[28rem] truncate">
                    {{ conversation.title }}
                  </span>
                </td>
                <td class="px-3 py-4 align-top">{{ conversation.username || '-' }}</td>
                <td class="px-3 py-4 align-top">
                  <span class="ui-chip">
                    {{ conversation.deleted_at ? t('settings.ai.audit.state.deleted') : t('settings.ai.audit.state.active') }}
                  </span>
                </td>
                <td class="px-3 py-4 align-top">{{ formatTimestamp(conversation.updated_at) }}</td>
                <td class="px-3 py-4 align-top">
                  <RouterLink
                    :to="{
                      name: 'admin-ai-conversation',
                      params: { cluster: currentClusterName, conversationId: conversation.id }
                    }"
                    class="ui-button-secondary"
                    data-testid="audit-detail-link"
                  >
                    {{ t('settings.ai.audit.openDetail') }}
                  </RouterLink>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>

    <SettingsAIConfigModal
      :open="modalOpen"
      :config="editingConfig"
      :provider-options="providerOptions"
      @close="closeModal"
      @submit="submitForm"
    />
  </div>
</template>

<style scoped>
.admin-ai-workspace {
  gap: 1rem;
}

.admin-ai-shell {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(239, 244, 246, 0.88)),
    radial-gradient(circle at top left, rgba(182, 232, 44, 0.1), transparent 34%);
}

.admin-ai-hero {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.admin-ai-hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.admin-ai-status-stack {
  display: grid;
  gap: 0.75rem;
}

.admin-ai-section {
  border-radius: calc(var(--radius-panel) - 4px);
}

.admin-ai-section-muted {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(236, 242, 244, 0.86)),
    radial-gradient(circle at top left, rgba(80, 105, 127, 0.06), transparent 42%);
}

@media (min-width: 1024px) {
  .admin-ai-hero {
    align-items: flex-start;
    flex-direction: row;
    justify-content: space-between;
  }

  .admin-ai-hero-actions {
    justify-content: flex-end;
  }
}
</style>

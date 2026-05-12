<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
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
import FormFieldLabel from '@/components/forms/FormFieldLabel.vue'

type SecretMode = 'keep' | 'replace' | 'clear'

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
const auditLoading = ref(false)
const auditError = ref<string | null>(null)
const modalOpen = ref(false)
const editingConfigId = ref<number | null>(null)
const secretMode = ref<SecretMode>('replace')

const form = reactive({
  name: '',
  provider: 'openai',
  model: '',
  display_name: '',
  enabled: true,
  is_default: false,
  sort_order: '0',
  base_url: '',
  deployment: '',
  api_version: '',
  request_timeout: '',
  temperature: '',
  system_prompt: '',
  extra_options: '',
  api_key: ''
})

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
  const username = auditUsernameFilter.value.trim().toLowerCase()
  const keyword = auditKeywordFilter.value.trim().toLowerCase()
  return auditConversations.value.filter((conversation) => {
    const conversationUsername = (conversation.username ?? '').toLowerCase()
    const title = conversation.title.toLowerCase()
    return (!username || conversationUsername.includes(username)) && (!keyword || title.includes(keyword))
  })
})
const currentProvider = computed(() => form.provider)
const requiresDeployment = computed(() => currentProvider.value === 'azure-openai')
const requiresApiVersion = computed(() => currentProvider.value === 'azure-openai')
const supportsSecret = computed(() => currentProvider.value !== 'ollama')
const secretFieldRequired = computed(
  () => supportsSecret.value && (editingConfigId.value === null || secretMode.value === 'replace')
)

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

function resetForm() {
  form.name = ''
  form.provider = providerOptions.value[0]?.key ?? 'openai'
  form.model = ''
  form.display_name = ''
  form.enabled = true
  form.is_default = false
  form.sort_order = '0'
  form.base_url = ''
  form.deployment = ''
  form.api_version = ''
  form.request_timeout = ''
  form.temperature = ''
  form.system_prompt = ''
  form.extra_options = ''
  form.api_key = ''
}

function openCreateModal() {
  clearFeedback()
  editingConfigId.value = null
  secretMode.value = 'replace'
  resetForm()
  modalOpen.value = true
}

function openEditModal(config: AIModelConfig) {
  clearFeedback()
  editingConfigId.value = config.id
  secretMode.value = 'keep'
  form.name = config.name
  form.provider = config.provider
  form.model = config.model
  form.display_name = config.display_name
  form.enabled = config.enabled
  form.is_default = config.is_default
  form.sort_order = String(config.sort_order ?? 0)
  form.base_url = config.base_url ?? ''
  form.deployment = config.deployment ?? ''
  form.api_version = config.api_version ?? ''
  form.request_timeout = config.request_timeout == null ? '' : String(config.request_timeout)
  form.temperature = config.temperature == null ? '' : String(config.temperature)
  form.system_prompt = config.system_prompt ?? ''
  form.extra_options =
    Object.keys(config.extra_options ?? {}).length > 0
      ? JSON.stringify(config.extra_options, null, 2)
      : ''
  form.api_key = ''
  modalOpen.value = true
}

function closeModal() {
  modalOpen.value = false
  editingConfigId.value = null
  secretMode.value = 'replace'
}

function parseOptionalInteger(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number.parseInt(trimmed, 10)
  if (Number.isNaN(parsed)) throw new Error(t('settings.ai.errors.requestTimeoutInteger'))
  return parsed
}

function parseRequiredInteger(value: string, field: string): number {
  const trimmed = value.trim()
  if (!trimmed) return 0
  const parsed = Number.parseInt(trimmed, 10)
  if (Number.isNaN(parsed)) throw new Error(t('settings.ai.errors.integerField', { field }))
  return parsed
}

function parseOptionalFloat(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number.parseFloat(trimmed)
  if (Number.isNaN(parsed)) throw new Error(t('settings.ai.errors.temperatureNumeric'))
  return parsed
}

function buildPayload(): AIModelConfigPayload {
  let extra_options: Record<string, unknown> = {}
  if (form.extra_options.trim()) {
    const parsed = JSON.parse(form.extra_options)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error(t('settings.ai.errors.extraOptionsObject'))
    }
    extra_options = parsed as Record<string, unknown>
  }

  const payload: AIModelConfigPayload = {
    name: form.name.trim(),
    provider: form.provider,
    model: form.model.trim(),
    display_name: form.display_name.trim(),
    enabled: form.enabled,
    is_default: form.is_default,
    sort_order: parseRequiredInteger(form.sort_order, 'sort_order'),
    base_url: form.base_url.trim() || null,
    deployment: form.deployment.trim() || null,
    api_version: form.api_version.trim() || null,
    request_timeout: parseOptionalInteger(form.request_timeout),
    temperature: parseOptionalFloat(form.temperature),
    system_prompt: form.system_prompt.trim() || null,
    extra_options
  }

  if (editingConfigId.value === null) {
    if (supportsSecret.value && !form.api_key.trim()) {
      throw new Error(t('settings.ai.errors.apiKeyRequired'))
    }
    if (supportsSecret.value) payload.api_key = form.api_key.trim()
    return payload
  }

  if (supportsSecret.value && secretMode.value === 'replace') {
    if (!form.api_key.trim()) {
      throw new Error(t('settings.ai.errors.apiKeyReplaceRequired'))
    }
    payload.api_key = form.api_key.trim()
  } else if (supportsSecret.value && secretMode.value === 'clear') {
    payload.api_key = ''
    payload.clear_secret = true
  }
  return payload
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

async function submitForm() {
  if (!currentClusterName.value) return
  clearFeedback()
  try {
    const payload = buildPayload()
    if (editingConfigId.value === null) {
      await gateway.create_ai_config(currentClusterName.value, payload)
      submitSuccess.value = t('settings.ai.feedback.created')
    } else {
      await gateway.update_ai_config(currentClusterName.value, editingConfigId.value, payload)
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

watch(
  () => providerOptions.value,
  () => {
    if (!providerOptions.value.some((provider) => provider.key === form.provider)) {
      form.provider = providerOptions.value[0]?.key ?? 'openai'
    }
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
              <tr v-for="config in sortedConfigs" :key="config.id" data-testid="ai-config-row">
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
          <div class="ui-page-tools-end">
            <button type="button" class="ui-button-secondary" :disabled="auditLoading" @click="loadAuditConversations">
              {{ t('common.buttons.refresh') }}
            </button>
          </div>
        </div>

        <ErrorAlert v-if="auditError" class="mt-5">
          {{ auditError }}
        </ErrorAlert>

        <div class="mt-5 grid gap-3 lg:grid-cols-2">
          <label class="block">
            <span class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.ai.audit.filters.username') }}</span>
            <input
              v-model="auditUsernameFilter"
              data-testid="audit-username-filter"
              type="search"
              class="ui-input-field mt-2"
              :placeholder="t('settings.ai.audit.filters.usernamePlaceholder')"
            />
          </label>
          <label class="block">
            <span class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.ai.audit.filters.title') }}</span>
            <input
              v-model="auditKeywordFilter"
              data-testid="audit-keyword-filter"
              type="search"
              class="ui-input-field mt-2"
              :placeholder="t('settings.ai.audit.filters.titlePlaceholder')"
            />
          </label>
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
              <tr v-for="conversation in filteredAuditConversations" :key="conversation.id">
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

    <TransitionRoot as="template" :show="modalOpen">
      <Dialog as="div" class="relative z-50" @close="closeModal">
        <TransitionChild
          as="template"
          enter="ease-out duration-200"
          enter-from="opacity-0"
          enter-to="opacity-100"
          leave="ease-in duration-150"
          leave-from="opacity-100"
          leave-to="opacity-0"
        >
          <div class="fixed inset-0 bg-[rgba(32,42,53,0.7)] backdrop-blur-sm" />
        </TransitionChild>

        <div class="fixed inset-0 overflow-y-auto p-4">
          <div class="flex min-h-full items-center justify-center">
            <TransitionChild
              as="template"
              enter="ease-out duration-200"
              enter-from="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
              enter-to="opacity-100 translate-y-0 sm:scale-100"
              leave="ease-in duration-150"
              leave-from="opacity-100 translate-y-0 sm:scale-100"
              leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
            >
              <DialogPanel class="w-full max-w-4xl rounded-[32px] border border-white/10 bg-white p-6 shadow-[var(--shadow-panel)]">
                <div class="flex items-start justify-between gap-4">
                  <div>
                    <p class="ui-page-kicker">{{ t('settings.ai.modal.kicker') }}</p>
                    <DialogTitle class="text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ editingConfigId === null ? t('settings.ai.modal.createTitle') : t('settings.ai.modal.editTitle') }}
                    </DialogTitle>
                    <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
                      {{ t('settings.ai.modal.description') }}
                    </p>
                  </div>
                  <button type="button" class="ui-button-secondary" @click="closeModal">{{ t('common.buttons.close') }}</button>
                </div>

                <form class="mt-6 space-y-6" @submit.prevent="submitForm">
                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.configName"
                        required
                        hint="settings.ai.hints.configName"
                        tooltip="settings.ai.hints.configNameTooltip"
                      />
                      <input v-model="form.name" type="text" class="ui-input-field mt-2" />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.displayName"
                        required
                        hint="settings.ai.hints.displayName"
                        tooltip="settings.ai.hints.displayNameTooltip"
                      />
                      <input v-model="form.display_name" type="text" class="ui-input-field mt-2" />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.provider"
                        required
                        hint="settings.ai.hints.provider"
                        tooltip="settings.ai.hints.providerTooltip"
                      />
                      <select v-model="form.provider" class="ui-select-field mt-2">
                        <option v-for="provider in providerOptions" :key="provider.key" :value="provider.key">
                          {{ provider.label }}
                        </option>
                      </select>
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.model"
                        required
                        hint="settings.ai.hints.model"
                        tooltip="settings.ai.hints.modelTooltip"
                      />
                      <input v-model="form.model" type="text" class="ui-input-field mt-2" />
                    </label>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.baseUrl"
                        hint="settings.ai.hints.baseUrl"
                        tooltip="settings.ai.hints.baseUrlTooltip"
                      />
                      <input v-model="form.base_url" type="text" class="ui-input-field mt-2" />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.sortOrder"
                        hint="settings.ai.hints.sortOrder"
                        tooltip="settings.ai.hints.sortOrderTooltip"
                      />
                      <input v-model="form.sort_order" type="number" class="ui-input-field mt-2" />
                    </label>
                    <label v-if="requiresDeployment" class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.deployment"
                        :required="requiresDeployment"
                        hint="settings.ai.hints.deployment"
                        tooltip="settings.ai.hints.deploymentTooltip"
                      />
                      <input v-model="form.deployment" type="text" class="ui-input-field mt-2" />
                    </label>
                    <label v-if="requiresApiVersion" class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.apiVersion"
                        :required="requiresApiVersion"
                        hint="settings.ai.hints.apiVersion"
                        tooltip="settings.ai.hints.apiVersionTooltip"
                      />
                      <input v-model="form.api_version" type="text" class="ui-input-field mt-2" />
                    </label>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.requestTimeout"
                        hint="settings.ai.hints.requestTimeout"
                        tooltip="settings.ai.hints.requestTimeoutTooltip"
                      />
                      <input v-model="form.request_timeout" type="number" class="ui-input-field mt-2" />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="settings.ai.fields.temperature"
                        hint="settings.ai.hints.temperature"
                        tooltip="settings.ai.hints.temperatureTooltip"
                      />
                      <input v-model="form.temperature" type="number" step="0.1" class="ui-input-field mt-2" />
                    </label>
                  </div>

                  <div v-if="supportsSecret" class="ui-panel-soft px-4 py-4">
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">{{ t('settings.ai.secret.title') }}</p>
                        <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                          {{ t('settings.ai.hints.secretDescription') }}
                        </p>
                      </div>
                      <div v-if="editingConfigId !== null" class="flex flex-wrap gap-2">
                        <button type="button" class="ui-button-secondary" @click="secretMode = 'keep'">{{ t('settings.ai.actions.keep') }}</button>
                        <button
                          type="button"
                          class="ui-button-warning"
                          :title="t('settings.ai.hints.replaceSecretTitle')"
                          @click="secretMode = 'replace'"
                        >
                          {{ t('settings.ai.actions.replace') }}
                        </button>
                        <button
                          type="button"
                          class="ui-button-danger"
                          :title="t('settings.ai.hints.clearSecretTitle')"
                          @click="secretMode = 'clear'"
                        >
                          {{ t('settings.ai.actions.clear') }}
                        </button>
                      </div>
                    </div>
                    <label v-if="editingConfigId === null || secretMode === 'replace'" class="mt-4 block">
                      <FormFieldLabel
                        label="settings.ai.fields.apiKey"
                        :required="secretFieldRequired"
                        hint="settings.ai.hints.apiKey"
                        tooltip="settings.ai.hints.apiKeyTooltip"
                      />
                      <input
                        v-model="form.api_key"
                        type="password"
                        class="ui-input-field mt-2"
                        :placeholder="t('settings.ai.placeholders.apiKey')"
                      />
                    </label>
                  </div>

                  <label class="block">
                    <FormFieldLabel
                      label="settings.ai.fields.systemPrompt"
                      hint="settings.ai.hints.systemPrompt"
                      tooltip="settings.ai.hints.systemPromptTooltip"
                    />
                    <textarea v-model="form.system_prompt" rows="4" class="ui-textarea-field mt-2" />
                  </label>

                  <label class="block">
                    <FormFieldLabel
                      label="settings.ai.fields.extraOptions"
                      hint="settings.ai.hints.extraOptions"
                      tooltip="settings.ai.hints.extraOptionsTooltip"
                    />
                    <textarea
                      v-model="form.extra_options"
                      rows="5"
                      class="ui-textarea-field mt-2 font-mono"
                      placeholder="{ }"
                    />
                  </label>

                  <div class="flex flex-wrap gap-6">
                    <label class="flex items-center gap-2 text-sm text-[var(--color-brand-ink-strong)]">
                      <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded" />
                      {{ t('settings.ai.fields.enabled') }}
                    </label>
                    <label class="flex items-center gap-2 text-sm text-[var(--color-brand-ink-strong)]">
                      <input v-model="form.is_default" type="checkbox" class="h-4 w-4 rounded" />
                      {{ t('settings.ai.fields.isDefault') }}
                    </label>
                  </div>

                  <div class="flex flex-wrap justify-end gap-2">
                    <button type="button" class="ui-button-secondary" @click="closeModal">{{ t('common.buttons.cancel') }}</button>
                    <button
                      type="submit"
                      :class="editingConfigId === null ? 'ui-button-primary' : 'ui-button-warning'"
                      :title="
                        editingConfigId === null
                          ? t('settings.ai.submitTitles.create')
                          : t('settings.ai.submitTitles.edit')
                      "
                    >
                      {{ editingConfigId === null ? t('settings.ai.actions.createModel') : t('common.buttons.saveChanges') }}
                    </button>
                  </div>
                </form>
              </DialogPanel>
            </TransitionChild>
          </div>
        </div>
      </Dialog>
    </TransitionRoot>
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

<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import type { AIModelConfig, AIModelConfigPayload, AIProviderOption } from '@/composables/GatewayAPI'
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

const isAdminRoute = computed(() => String(route.name ?? '').startsWith('admin-'))
const tabsComponent = computed(() => (isAdminRoute.value ? AdminTabs : SettingsTabs))
const headerComponent = computed(() => (isAdminRoute.value ? AdminHeader : SettingsHeader))
const loading = ref(false)
const error = ref<string | null>(null)
const submitError = ref<string | null>(null)
const submitSuccess = ref<string | null>(null)
const validatingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
const configs = ref<AIModelConfig[]>([])
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
const enabledConfigsCount = computed(() => configs.value.filter((config) => config.enabled).length)
const defaultConfig = computed(() => configs.value.find((config) => config.is_default) ?? null)
const currentProvider = computed(() => form.provider)
const requiresDeployment = computed(() => currentProvider.value === 'azure-openai')
const requiresApiVersion = computed(() => currentProvider.value === 'azure-openai')
const supportsSecret = computed(() => currentProvider.value !== 'ollama')
const secretFieldRequired = computed(
  () => supportsSecret.value && (editingConfigId.value === null || secretMode.value === 'replace')
)

function formatTimestamp(value: string | null): string {
  if (!value) return 'Never'
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function providerLabel(config: AIModelConfig): string {
  return config.provider_label || providerOptions.value.find((option) => option.key === config.provider)?.label || config.provider
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
  if (Number.isNaN(parsed)) throw new Error('request_timeout must be an integer')
  return parsed
}

function parseRequiredInteger(value: string, field: string): number {
  const trimmed = value.trim()
  if (!trimmed) return 0
  const parsed = Number.parseInt(trimmed, 10)
  if (Number.isNaN(parsed)) throw new Error(`${field} must be an integer`)
  return parsed
}

function parseOptionalFloat(value: string): number | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  const parsed = Number.parseFloat(trimmed)
  if (Number.isNaN(parsed)) throw new Error('temperature must be numeric')
  return parsed
}

function buildPayload(): AIModelConfigPayload {
  let extra_options: Record<string, unknown> = {}
  if (form.extra_options.trim()) {
    const parsed = JSON.parse(form.extra_options)
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
      throw new Error('extra_options must be a JSON object')
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
      throw new Error('api_key is required when creating a non-Ollama model')
    }
    if (supportsSecret.value) payload.api_key = form.api_key.trim()
    return payload
  }

  if (supportsSecret.value && secretMode.value === 'replace') {
    if (!form.api_key.trim()) {
      throw new Error('Enter a new api_key before replacing the current secret')
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

async function submitForm() {
  if (!currentClusterName.value) return
  clearFeedback()
  try {
    const payload = buildPayload()
    if (editingConfigId.value === null) {
      await gateway.create_ai_config(currentClusterName.value, payload)
      submitSuccess.value = 'Model config created.'
    } else {
      await gateway.update_ai_config(currentClusterName.value, editingConfigId.value, payload)
      submitSuccess.value = 'Model config updated.'
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
    submitSuccess.value = `${config.display_name} ${config.enabled ? 'disabled' : 'enabled'}.`
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
    submitSuccess.value = `${config.display_name} is now the default model.`
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
    submitSuccess.value = `Connection validated: ${result.sample || result.model}`
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
    submitSuccess.value = `${config.display_name} deleted.`
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
})
</script>

<template>
  <div class="ui-section-stack">
    <component :is="tabsComponent" entry="AI" :cluster="currentClusterName" />

    <div class="ui-panel ui-section">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <component
          :is="headerComponent"
          title="AI"
          description="Manage cluster-scoped model configs, default model selection, connectivity checks and masked secrets."
        />
        <div class="flex flex-wrap gap-2">
          <RouterLink
            v-if="currentClusterName && canViewChat"
            :to="{ name: 'ai', params: { cluster: currentClusterName } }"
            class="ui-button-secondary"
          >
            Go to chat
          </RouterLink>
          <button
            type="button"
            class="ui-button-primary"
            :disabled="!canManage || !aiAvailable"
            title="Create a new cluster-scoped AI model configuration."
            @click="openCreateModal"
          >
            New model
          </button>
        </div>
      </div>
    </div>

    <InfoAlert v-if="!settingsCluster">
      No cluster context is available for AI settings.
    </InfoAlert>
    <InfoAlert v-else-if="!aiAvailable">
      AI capability is not enabled for the current cluster.
    </InfoAlert>
    <InfoAlert v-else-if="!canView">
      The current user does not have permission to view AI settings on this cluster.
    </InfoAlert>

    <template v-else>
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
        The current user can inspect AI settings but cannot edit them on this cluster.
      </InfoAlert>

      <section class="ui-panel ui-section">
        <div class="ui-stat-grid">
          <div class="ui-stat-card">
            <p class="ui-stat-label">Cluster</p>
            <div class="ui-stat-value text-[1.35rem]">{{ currentClusterName }}</div>
            <p class="ui-stat-subtle">Settings scope</p>
          </div>
          <div class="ui-stat-card">
            <p class="ui-stat-label">Enabled models</p>
            <div class="ui-stat-value text-[1.35rem]">{{ enabledConfigsCount }}</div>
            <p class="ui-stat-subtle">{{ configs.length }} configs total</p>
          </div>
          <div class="ui-stat-card">
            <p class="ui-stat-label">Default model</p>
            <div class="ui-stat-value text-[1.1rem]">
              {{ defaultConfig?.display_name || 'Unset' }}
            </div>
            <p class="ui-stat-subtle">Fallback for new chats</p>
          </div>
          <div class="ui-stat-card">
            <p class="ui-stat-label">Streaming</p>
            <div class="ui-stat-value text-[1.35rem]">
              {{ settingsCluster?.ai?.streaming || settingsCluster?.capabilities?.ai?.streaming ? 'SSE' : 'Off' }}
            </div>
            <p class="ui-stat-subtle">Capability reported by the cluster</p>
          </div>
        </div>
      </section>

      <section class="ui-panel ui-section">
        <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <p class="ui-page-kicker">Model Configurations</p>
            <h2 class="ui-panel-title">Cluster model list</h2>
            <p class="ui-panel-description mt-2">
              Supported providers include OpenAI, Azure OpenAI, Anthropic, Gemini, Qwen, DeepSeek, Kimi, Ollama and OpenAI-Compatible services.
            </p>
          </div>
          <button type="button" class="ui-button-secondary" :disabled="loading" @click="loadConfigs">
            Refresh
          </button>
        </div>

        <div v-if="loading" class="mt-6 text-[var(--color-brand-muted)]">
          <LoadingSpinner :size="5" />
          Loading model configs...
        </div>

        <InfoAlert v-else-if="sortedConfigs.length === 0" class="mt-6">
          No model configs exist for this cluster yet.
        </InfoAlert>

        <div v-else class="mt-6 grid gap-4 xl:grid-cols-2">
          <article
            v-for="config in sortedConfigs"
            :key="config.id"
            class="rounded-[28px] border border-[rgba(80,105,127,0.12)] bg-[linear-gradient(180deg,rgba(255,255,255,0.96),rgba(239,244,246,0.84))] px-5 py-5 shadow-[var(--shadow-soft)]"
          >
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="min-w-0">
                <div class="flex flex-wrap gap-2">
                  <span class="ui-chip">{{ providerLabel(config) }}</span>
                  <span v-if="config.enabled" class="ui-chip">Enabled</span>
                  <span v-else class="ui-chip">Disabled</span>
                  <span v-if="config.is_default" class="ui-chip">Default</span>
                  <span v-if="config.secret_configured" class="ui-chip">Secret ready</span>
                </div>
                <h3 class="mt-3 text-lg font-semibold text-[var(--color-brand-ink-strong)]">
                  {{ config.display_name }}
                </h3>
                <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                  {{ config.model }}
                </p>
              </div>
              <div class="flex flex-wrap gap-2">
                <button
                  type="button"
                  class="ui-button-warning"
                  :disabled="!canManage"
                  title="Open the editor to update provider settings, routing, prompts and secrets."
                  @click="openEditModal(config)"
                >
                  Edit
                </button>
                <button
                  type="button"
                  class="ui-button-secondary"
                  :disabled="validatingId === config.id || !canManage"
                  title="Run a live connectivity check with the current model configuration."
                  @click="validateConfig(config)"
                >
                  {{ validatingId === config.id ? 'Testing...' : 'Test connection' }}
                </button>
              </div>
            </div>

            <dl class="mt-5 grid gap-3 text-sm text-[var(--color-brand-muted)] sm:grid-cols-2">
              <div class="ui-panel-soft px-4 py-3">
                <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Config name</dt>
                <dd class="mt-1">{{ config.name }}</dd>
              </div>
              <div class="ui-panel-soft px-4 py-3">
                <dt class="font-semibold text-[var(--color-brand-ink-strong)]">secret_mask</dt>
                <dd class="mt-1">{{ config.secret_mask || 'Not configured' }}</dd>
              </div>
              <div class="ui-panel-soft px-4 py-3">
                <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Base URL</dt>
                <dd class="mt-1 break-all">{{ config.base_url || 'Default endpoint' }}</dd>
              </div>
              <div class="ui-panel-soft px-4 py-3">
                <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Sort order</dt>
                <dd class="mt-1">{{ config.sort_order }}</dd>
              </div>
              <div class="ui-panel-soft px-4 py-3">
                <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Validated</dt>
                <dd class="mt-1">{{ formatTimestamp(config.last_validated_at) }}</dd>
              </div>
              <div class="ui-panel-soft px-4 py-3">
                <dt class="font-semibold text-[var(--color-brand-ink-strong)]">Validation error</dt>
                <dd class="mt-1 line-clamp-3">{{ config.last_validation_error || 'None' }}</dd>
              </div>
            </dl>

            <div class="mt-5 flex flex-wrap gap-2">
              <button
                type="button"
                class="ui-button-secondary"
                :disabled="config.is_default || !canManage"
                title="Make this model the default target for new AI conversations."
                @click="setDefault(config)"
              >
                Set default
              </button>
              <button
                type="button"
                class="ui-button-secondary"
                :disabled="!canManage"
                title="Enable or disable this model without deleting its saved configuration."
                @click="toggleEnabled(config)"
              >
                {{ config.enabled ? 'Disable' : 'Enable' }}
              </button>
              <button
                v-if="canDelete"
                type="button"
                class="ui-button-danger"
                :disabled="deletingId === config.id"
                title="Delete this model configuration and remove its saved secret."
                @click="deleteConfig(config)"
              >
                {{ deletingId === config.id ? 'Deleting...' : 'Delete' }}
              </button>
            </div>
          </article>
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
                    <p class="ui-page-kicker">Model Editor</p>
                    <DialogTitle class="text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
                      {{ editingConfigId === null ? 'Create model config' : 'Edit model config' }}
                    </DialogTitle>
                    <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
                      Provider secrets are stored in the database and only returned as masked summaries.
                    </p>
                  </div>
                  <button type="button" class="ui-button-secondary" @click="closeModal">Close</button>
                </div>

                <form class="mt-6 space-y-6" @submit.prevent="submitForm">
                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="block">
                      <FormFieldLabel
                        label="Config name"
                        required
                        hint="Stable identifier used to recognize this saved model entry."
                        tooltip="Used inside the cluster configuration list and audit trail."
                      />
                      <input
                        v-model="form.name"
                        type="text"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="Display name"
                        required
                        hint="Friendly label shown to end users when they choose a model."
                        tooltip="This can be more readable than the provider model identifier."
                      />
                      <input
                        v-model="form.display_name"
                        type="text"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="Provider"
                        required
                        hint="Select which upstream AI service receives chat requests."
                        tooltip="Provider controls which connection options are required below."
                      />
                      <select
                        v-model="form.provider"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      >
                        <option v-for="provider in providerOptions" :key="provider.key" :value="provider.key">
                          {{ provider.label }}
                        </option>
                      </select>
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="Model"
                        required
                        hint="Provider-specific model identifier, deployment name or runtime tag."
                        tooltip="Examples: gpt-4.1, claude-3-7-sonnet, qwen-max, llama3.1."
                      />
                      <input
                        v-model="form.model"
                        type="text"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="block">
                      <FormFieldLabel
                        label="Base URL"
                        hint="Optional override when the provider is served from a custom endpoint."
                        tooltip="Leave empty to use the provider's default API base URL."
                      />
                      <input
                        v-model="form.base_url"
                        type="text"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="Sort order"
                        hint="Optional numeric weight that controls how models are ordered in the UI."
                        tooltip="Lower values appear earlier in lists; empty falls back to 0."
                      />
                      <input
                        v-model="form.sort_order"
                        type="number"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                    <label v-if="requiresDeployment" class="block">
                      <FormFieldLabel
                        label="Deployment"
                        :required="requiresDeployment"
                        hint="Azure OpenAI deployment name that routes requests to the target model."
                        tooltip="Azure uses deployment identifiers rather than raw model names at request time."
                      />
                      <input
                        v-model="form.deployment"
                        type="text"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                    <label v-if="requiresApiVersion" class="block">
                      <FormFieldLabel
                        label="API version"
                        :required="requiresApiVersion"
                        hint="Azure API version appended to requests for compatibility."
                        tooltip="Match this to the Azure OpenAI API version enabled for your deployment."
                      />
                      <input
                        v-model="form.api_version"
                        type="text"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                  </div>

                  <div class="grid gap-4 md:grid-cols-2">
                    <label class="block">
                      <FormFieldLabel
                        label="Request timeout"
                        hint="Optional timeout in seconds before chat or validation requests are aborted."
                        tooltip="Useful for slower providers or on-premise gateways."
                      />
                      <input
                        v-model="form.request_timeout"
                        type="number"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                    <label class="block">
                      <FormFieldLabel
                        label="Temperature"
                        hint="Optional sampling control for generation creativity and determinism."
                        tooltip="Leave empty to let the provider or server defaults decide."
                      />
                      <input
                        v-model="form.temperature"
                        type="number"
                        step="0.1"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      />
                    </label>
                  </div>

                  <div v-if="supportsSecret" class="ui-panel-soft px-4 py-4">
                    <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                      <div>
                        <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">Secret</p>
                        <p class="mt-1 text-sm text-[var(--color-brand-muted)]">
                          Keep the current secret, replace it, or clear it for the selected model.
                        </p>
                      </div>
                      <div v-if="editingConfigId !== null" class="flex flex-wrap gap-2">
                        <button type="button" class="ui-button-secondary" @click="secretMode = 'keep'">
                          Keep
                        </button>
                        <button
                          type="button"
                          class="ui-button-warning"
                          title="Replace the stored secret with a new API key."
                          @click="secretMode = 'replace'"
                        >
                          Replace
                        </button>
                        <button
                          type="button"
                          class="ui-button-danger"
                          title="Remove the stored secret. Future requests will fail until a new secret is set."
                          @click="secretMode = 'clear'"
                        >
                          Clear
                        </button>
                      </div>
                    </div>
                    <label v-if="editingConfigId === null || secretMode === 'replace'" class="mt-4 block">
                      <FormFieldLabel
                        label="API Key"
                        :required="secretFieldRequired"
                        hint="Credential stored securely and only returned to the UI as a masked value."
                        tooltip="Required for providers that authenticate with a bearer secret."
                      />
                      <input
                        v-model="form.api_key"
                        type="password"
                        class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                        placeholder="sk-..."
                      />
                    </label>
                  </div>

                  <label class="block">
                    <FormFieldLabel
                      label="System prompt"
                      hint="Optional instruction prefix applied to every new conversation for this model."
                      tooltip="Use this to enforce tone, scope, safety policy or cluster-specific context."
                    />
                    <textarea
                      v-model="form.system_prompt"
                      rows="4"
                      class="mt-2 block w-full rounded-[20px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-3 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    />
                  </label>

                  <label class="block">
                    <FormFieldLabel
                      label="Extra options"
                      hint="Optional JSON object for provider-specific request fields that do not have a dedicated form control."
                      tooltip="Examples include max_tokens, top_p, reasoning options or custom headers."
                    />
                    <textarea
                      v-model="form.extra_options"
                      rows="5"
                      class="mt-2 block w-full rounded-[20px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-3 font-mono text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                      placeholder="{ }"
                    />
                  </label>

                  <div class="flex flex-wrap gap-6">
                    <label class="flex items-center gap-2 text-sm text-[var(--color-brand-ink-strong)]">
                      <input v-model="form.enabled" type="checkbox" class="h-4 w-4 rounded" />
                      Enabled
                    </label>
                    <label class="flex items-center gap-2 text-sm text-[var(--color-brand-ink-strong)]">
                      <input v-model="form.is_default" type="checkbox" class="h-4 w-4 rounded" />
                      is_default
                    </label>
                  </div>

                  <div class="flex flex-wrap justify-end gap-2">
                    <button type="button" class="ui-button-secondary" @click="closeModal">Cancel</button>
                    <button
                      type="submit"
                      :class="editingConfigId === null ? 'ui-button-primary' : 'ui-button-warning'"
                      :title="
                        editingConfigId === null
                          ? 'Create a new model configuration for this cluster.'
                          : 'Save the edited model configuration to the cluster.'
                      "
                    >
                      {{ editingConfigId === null ? 'Create model' : 'Save changes' }}
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

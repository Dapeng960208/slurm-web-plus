<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import FormFieldLabel from '@/components/forms/FormFieldLabel.vue'
import type { AIModelConfig, AIModelConfigPayload, AIProviderOption } from '@/composables/GatewayAPI'

type SecretMode = 'keep' | 'replace' | 'clear'

const props = defineProps<{
  open: boolean
  config: AIModelConfig | null
  providerOptions: AIProviderOption[]
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: AIModelConfigPayload]
}>()

const { t } = useI18n()
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

const editingConfigId = computed(() => props.config?.id ?? null)
const currentProvider = computed(() => form.provider)
const requiresDeployment = computed(() => currentProvider.value === 'azure-openai')
const requiresApiVersion = computed(() => currentProvider.value === 'azure-openai')
const supportsSecret = computed(() => currentProvider.value !== 'ollama')
const secretFieldRequired = computed(
  () => supportsSecret.value && (editingConfigId.value === null || secretMode.value === 'replace')
)

function resetForm() {
  const config = props.config
  if (!config) {
    form.name = ''
    form.provider = props.providerOptions[0]?.key ?? 'openai'
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
    secretMode.value = 'replace'
    return
  }

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
  secretMode.value = 'keep'
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

function submitForm() {
  emit('submit', buildPayload())
}

watch(
  () => props.open,
  (open) => {
    if (open) resetForm()
  },
  { immediate: true }
)

watch(
  () => props.config,
  () => {
    if (props.open) resetForm()
  }
)

watch(
  () => props.providerOptions.map((provider) => provider.key).join('|'),
  () => {
    if (!props.providerOptions.some((provider) => provider.key === form.provider)) {
      form.provider = props.providerOptions[0]?.key ?? 'openai'
    }
  }
)
</script>

<template>
  <TransitionRoot as="template" :show="open">
    <Dialog as="div" class="relative z-50" @close="emit('close')">
      <TransitionChild
        as="template"
        enter="ease-out duration-200"
        enter-from="opacity-0"
        enter-to="opacity-100"
        leave="ease-in duration-150"
        leave-from="opacity-100"
        leave-to="opacity-0"
      >
        <div class="fixed inset-0 bg-[rgba(32,42,53,0.72)]" />
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
            <DialogPanel class="w-full max-w-4xl rounded-[32px] border border-white/10 bg-white p-6 shadow-[var(--shadow-modal)]">
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
                <button type="button" class="ui-button-secondary" @click="emit('close')">{{ t('common.buttons.close') }}</button>
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
                  <button type="button" class="ui-button-secondary" @click="emit('close')">{{ t('common.buttons.cancel') }}</button>
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
</template>

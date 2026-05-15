<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import FormFieldLabel from '@/components/forms/FormFieldLabel.vue'
import RemoteSearchSelect from '@/components/forms/RemoteSearchSelect.vue'
import { translate } from '@/i18n/translate'
import type { SearchSelectSource } from '@/composables/searchSelect'

export type ActionFieldType =
  | 'text'
  | 'textarea'
  | 'number'
  | 'select'
  | 'datetime-local'
  | 'search-select'
  | 'search-multi-select'
export type ActionSubmitVariant = 'primary' | 'warning' | 'danger'

export interface ActionFieldOption {
  label: string
  value: string
  disabled?: boolean
}

export interface ActionField {
  key: string
  label: string
  type?: ActionFieldType
  options?: ActionFieldOption[]
  source?: SearchSelectSource
  placeholder?: string
  required?: boolean
  hint?: string
  tooltip?: string
  minQueryLength?: number
}

const props = defineProps<{
  open: boolean
  title: string
  description?: string
  submitLabel: string
  titleParams?: Record<string, unknown>
  descriptionParams?: Record<string, unknown>
  submitLabelParams?: Record<string, unknown>
  loading?: boolean
  error?: string | null
  fields: ActionField[]
  initialValues?: Record<string, string>
  submitVariant?: ActionSubmitVariant
  submitTooltip?: string
}>()

const emit = defineEmits<{
  close: []
  submit: [payload: Record<string, string>]
}>()
const { t } = useI18n()

const form = reactive<Record<string, string>>({})
const fieldsSignature = computed(() =>
  props.fields
    .map((field) =>
      `${field.key}:${field.type ?? 'text'}:${field.options?.map((option) => option.value).join(',') ?? ''}:${field.source ? 'remote' : 'local'}`
    )
    .join('|')
)

const resolvedSubmitVariant = computed<ActionSubmitVariant>(() => {
  if (props.submitVariant) return props.submitVariant
  if (
    props.submitLabel === 'common.buttons.delete' ||
    props.submitLabel.startsWith('dialogs.') && props.submitLabel.includes('.delete')
  ) {
    return 'danger'
  }
  if (props.submitLabel === 'common.buttons.saveChanges' || props.submitLabel === 'common.buttons.edit') {
    return 'warning'
  }
  return 'primary'
})

const submitButtonClass = computed(() => {
  switch (resolvedSubmitVariant.value) {
    case 'danger':
      return 'ui-button-danger'
    case 'warning':
      return 'ui-button-warning'
    default:
      return 'ui-button-primary'
  }
})

const resolvedSubmitTooltip = computed(() => {
  if (props.submitTooltip) return translate(props.submitTooltip)
  if (props.description) return translate(props.description, props.descriptionParams)
  return t('actionDialog.confirm', { action: translate(props.submitLabel).toLowerCase() })
})

function resetForm() {
  for (const key of Object.keys(form)) {
    delete form[key]
  }
  for (const field of props.fields) {
    form[field.key] = props.initialValues?.[field.key] ?? ''
  }
}

const canSubmit = computed(() =>
  props.fields.every((field) => !field.required || form[field.key].trim().length > 0)
)

watch(
  () => props.open,
  (open) => {
    if (open) resetForm()
  },
  { immediate: true }
)

watch(
  () => [props.title, props.submitLabel, fieldsSignature.value] as const,
  () => {
    if (props.open) resetForm()
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
            <DialogPanel class="w-full max-w-2xl rounded-[32px] border border-white/10 bg-white p-6 shadow-[var(--shadow-panel)]">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="ui-page-kicker">{{ t('actionDialog.kicker') }}</p>
                  <DialogTitle class="text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ translate(title, titleParams) }}
                  </DialogTitle>
                  <p v-if="description" class="mt-2 text-sm text-[var(--color-brand-muted)]">
                    {{ translate(description, descriptionParams) }}
                  </p>
                </div>
                <button type="button" class="ui-button-secondary" @click="emit('close')">
                  {{ t('common.buttons.close') }}
                </button>
              </div>

              <form class="mt-6 space-y-4" @submit.prevent="emit('submit', { ...form })">
                <label v-for="field in fields" :key="field.key" class="block">
                  <FormFieldLabel
                    :label="field.label"
                    :required="field.required"
                    :hint="field.hint"
                    :tooltip="field.tooltip"
                  />
                  <textarea
                    v-if="field.type === 'textarea'"
                    v-model="form[field.key]"
                    rows="4"
                    class="mt-2 block w-full rounded-[20px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-3 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    :placeholder="field.placeholder ? translate(field.placeholder) : undefined"
                  />
                  <select
                    v-else-if="field.type === 'select'"
                    v-model="form[field.key]"
                    class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                  >
                    <option value="" disabled>{{
                      field.placeholder
                        ? translate(field.placeholder)
                        : t('common.forms.selectOption')
                    }}</option>
                    <option
                      v-for="option in field.options ?? []"
                      :key="option.value"
                      :value="option.value"
                      :disabled="option.disabled"
                    >
                      {{ translate(option.label) }}
                    </option>
                  </select>
                  <RemoteSearchSelect
                    v-else-if="
                      field.type === 'search-select' || field.type === 'search-multi-select'
                    "
                    :model-value="
                      field.type === 'search-multi-select'
                        ? form[field.key]
                            .split(',')
                            .map((item) => item.trim())
                            .filter((item) => item.length > 0)
                        : form[field.key]
                    "
                    :multiple="field.type === 'search-multi-select'"
                    :source="field.source!"
                    :placeholder="field.placeholder ? translate(field.placeholder) : ''"
                    :min-query-length="field.minQueryLength ?? 0"
                    @update:model-value="
                      (value) => {
                        form[field.key] = Array.isArray(value) ? value.join(', ') : value
                      }
                    "
                  />
                  <input
                    v-else
                    v-model="form[field.key]"
                    :type="
                      field.type === 'number'
                        ? 'number'
                        : field.type === 'datetime-local'
                          ? 'datetime-local'
                          : 'text'
                    "
                    class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    :placeholder="field.placeholder ? translate(field.placeholder) : undefined"
                  />
                </label>

                <p v-if="error" class="text-sm text-[var(--color-brand-danger)]">{{ error }}</p>

                <div class="flex flex-wrap justify-end gap-2">
                  <button type="button" class="ui-button-secondary" @click="emit('close')">
                    {{ t('common.buttons.cancel') }}
                  </button>
                  <button
                    type="submit"
                    :class="submitButtonClass"
                    :title="resolvedSubmitTooltip"
                    :disabled="loading || !canSubmit"
                  >
                    {{ loading ? t('common.status.working') : translate(submitLabel, submitLabelParams) }}
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

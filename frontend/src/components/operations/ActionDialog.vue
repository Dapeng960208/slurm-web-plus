<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, reactive, watch } from 'vue'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import FormFieldLabel from '@/components/forms/FormFieldLabel.vue'

export type ActionFieldType = 'text' | 'textarea' | 'number'
export type ActionSubmitVariant = 'primary' | 'warning' | 'danger'

export interface ActionField {
  key: string
  label: string
  type?: ActionFieldType
  placeholder?: string
  required?: boolean
  hint?: string
  tooltip?: string
}

const props = defineProps<{
  open: boolean
  title: string
  description?: string
  submitLabel: string
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

const form = reactive<Record<string, string>>({})

const resolvedSubmitVariant = computed<ActionSubmitVariant>(() => {
  if (props.submitVariant) return props.submitVariant
  const signal = `${props.title} ${props.submitLabel}`.toLowerCase()
  if (signal.includes('delete') || signal.includes('cancel')) return 'danger'
  if (signal.includes('edit') || signal.includes('save')) return 'warning'
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
  if (props.submitTooltip) return props.submitTooltip
  if (props.description) return props.description
  return `Confirm ${props.submitLabel.toLowerCase()}.`
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
  () => [props.open, props.initialValues, props.fields] as const,
  () => {
    if (props.open) resetForm()
  },
  { immediate: true }
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
                  <p class="ui-page-kicker">Cluster Operation</p>
                  <DialogTitle class="text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
                    {{ title }}
                  </DialogTitle>
                  <p v-if="description" class="mt-2 text-sm text-[var(--color-brand-muted)]">
                    {{ description }}
                  </p>
                </div>
                <button type="button" class="ui-button-secondary" @click="emit('close')">Close</button>
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
                    :placeholder="field.placeholder"
                  />
                  <input
                    v-else
                    v-model="form[field.key]"
                    :type="field.type === 'number' ? 'number' : 'text'"
                    class="mt-2 block w-full rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2.5 text-sm outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
                    :placeholder="field.placeholder"
                  />
                </label>

                <p v-if="error" class="text-sm text-[var(--color-brand-danger)]">{{ error }}</p>

                <div class="flex flex-wrap justify-end gap-2">
                  <button type="button" class="ui-button-secondary" @click="emit('close')">Cancel</button>
                  <button
                    type="submit"
                    :class="submitButtonClass"
                    :title="resolvedSubmitTooltip"
                    :disabled="loading || !canSubmit"
                  >
                    {{ loading ? 'Working...' : submitLabel }}
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

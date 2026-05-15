<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions
} from '@headlessui/vue'
import { CheckIcon, ChevronUpDownIcon, XMarkIcon } from '@heroicons/vue/20/solid'
import { useI18n } from 'vue-i18n'
import type { SearchSelectOption, SearchSelectSource } from '@/composables/searchSelect'

const props = withDefaults(
  defineProps<{
    modelValue: string | string[]
    source: SearchSelectSource
    multiple?: boolean
    placeholder?: string
    disabled?: boolean
    minQueryLength?: number
  }>(),
  {
    multiple: false,
    placeholder: '',
    disabled: false,
    minQueryLength: 0
  }
)

const emit = defineEmits<{
  'update:modelValue': [value: string | string[]]
}>()

const { t } = useI18n()

const query = ref('')
const options = ref<SearchSelectOption[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const requestVersion = ref(0)
let queryTimer: ReturnType<typeof setTimeout> | null = null

const selectedValues = computed<string[]>(() => {
  if (Array.isArray(props.modelValue)) return props.modelValue
  return props.modelValue ? [props.modelValue] : []
})

const selectedValueSet = computed(() => new Set(selectedValues.value))

const selectedOptions = computed(() => {
  const map = new Map(options.value.map((option) => [option.value, option]))
  return selectedValues.value.map((value) => map.get(value) ?? { value, label: value })
})

const displayValue = computed(() => {
  if (query.value) return query.value
  if (selectedOptions.value.length === 0) return ''
  return props.multiple
    ? selectedOptions.value.map((option) => option.label).join(', ')
    : selectedOptions.value[0]?.label ?? ''
})

const mergedOptions = computed(() => {
  const seen = new Set<string>()
  const result: SearchSelectOption[] = []

  for (const option of selectedOptions.value) {
    if (!seen.has(option.value)) {
      seen.add(option.value)
      result.push(option)
    }
  }
  for (const option of options.value) {
    if (!seen.has(option.value)) {
      seen.add(option.value)
      result.push(option)
    }
  }

  return result
})

const canQuery = computed(() => query.value.trim().length >= props.minQueryLength)

async function loadOptions(rawQuery: string) {
  const normalizedQuery = rawQuery.trim()
  const version = ++requestVersion.value
  loading.value = true
  error.value = null

  try {
    const result = await props.source.search(normalizedQuery)
    if (version !== requestVersion.value) return
    options.value = result
  } catch (cause) {
    if (version !== requestVersion.value) return
    error.value = cause instanceof Error ? cause.message : String(cause)
    options.value = []
  } finally {
    if (version === requestVersion.value) {
      loading.value = false
    }
  }
}

function scheduleSearch(value: string) {
  if (queryTimer) clearTimeout(queryTimer)
  queryTimer = setTimeout(() => {
    if (!canQuery.value) {
      options.value = []
      loading.value = false
      error.value = null
      return
    }
    void loadOptions(value)
  }, 180)
}

function updateQuery(event: Event) {
  query.value = (event.target as HTMLInputElement).value
}

function updateSelection(value: string | string[]) {
  if (props.multiple) {
    emit('update:modelValue', Array.isArray(value) ? value : value ? [value] : [])
    query.value = ''
    return
  }

  const nextValue = Array.isArray(value) ? (value[0] ?? '') : value
  emit('update:modelValue', nextValue)
  query.value = ''
}

function removeValue(value: string) {
  if (!props.multiple) {
    emit('update:modelValue', '')
    return
  }
  emit(
    'update:modelValue',
    selectedValues.value.filter((item) => item !== value)
  )
}

watch(
  () => props.source,
  () => {
    query.value = ''
    options.value = []
    error.value = null
    void loadOptions('')
  },
  { immediate: true }
)

watch(query, (value) => {
  scheduleSearch(value)
})

onBeforeUnmount(() => {
  if (queryTimer) clearTimeout(queryTimer)
})
</script>

<template>
  <div class="ui-search-select">
    <Combobox
      as="div"
      :model-value="multiple ? selectedValues : selectedValues[0] ?? ''"
      :multiple="multiple"
      :disabled="disabled"
      @update:model-value="updateSelection"
    >
      <div class="relative">
        <ComboboxInput
          class="ui-combobox-input"
          autocomplete="off"
          :display-value="() => displayValue"
          :placeholder="placeholder"
          @change="updateQuery"
        />
        <ComboboxButton
          class="absolute inset-y-0 right-0 flex items-center rounded-r-[18px] px-2 focus:outline-hidden"
        >
          <ChevronUpDownIcon class="h-5 w-5 text-[var(--color-brand-muted)]" aria-hidden="true" />
        </ComboboxButton>

        <ComboboxOptions
          class="ui-combobox-menu absolute z-20 mt-2 max-h-72 w-full text-sm focus:outline-none"
        >
          <li v-if="loading" class="ui-combobox-status">
            {{ t('common.status.loading') }}
          </li>
          <li v-else-if="error" class="ui-combobox-status ui-combobox-status-error">
            {{ error }}
          </li>
          <li
            v-else-if="!canQuery && minQueryLength > 0"
            class="ui-combobox-status"
          >
            {{ t('common.forms.typeMoreCharacters', { count: minQueryLength }) }}
          </li>
          <li v-else-if="mergedOptions.length === 0" class="ui-combobox-status">
            {{ t('common.forms.noMatches') }}
          </li>
          <ComboboxOption
            v-for="option in mergedOptions"
            :key="option.value"
            :value="option.value"
            as="template"
            v-slot="{ active, selected }"
          >
            <li
              :class="['ui-combobox-option', active && 'ui-combobox-option-active']"
            >
              <div class="min-w-0">
                <span :class="['block truncate', selected && 'font-semibold']">{{ option.label }}</span>
                <span
                  v-if="option.description && option.description !== option.label"
                  class="mt-0.5 block truncate text-xs opacity-75"
                >
                  {{ option.description }}
                </span>
              </div>

              <span
                v-if="selected"
                :class="[
                  'absolute inset-y-0 right-0 flex items-center pr-4',
                  active ? 'text-[var(--color-brand-deep)]' : 'text-[var(--color-brand-blue)]'
                ]"
              >
                <CheckIcon class="h-5 w-5" aria-hidden="true" />
              </span>
            </li>
          </ComboboxOption>
        </ComboboxOptions>
      </div>
    </Combobox>

    <div v-if="multiple && selectedOptions.length > 0" class="ui-search-select-tags">
      <span
        v-for="option in selectedOptions"
        :key="option.value"
        class="ui-search-select-tag"
      >
        <span class="truncate">{{ option.label }}</span>
        <button
          type="button"
          class="ui-search-select-tag-remove"
          :aria-label="t('common.buttons.remove')"
          @click="removeValue(option.value)"
        >
          <XMarkIcon class="h-3.5 w-3.5" aria-hidden="true" />
        </button>
      </span>
    </div>
  </div>
</template>

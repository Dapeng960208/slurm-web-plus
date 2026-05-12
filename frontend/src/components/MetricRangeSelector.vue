<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { MetricRange } from '@/composables/GatewayAPI'
import { translate } from '@/i18n/translate'

interface MetricWindowLocal {
  start: string
  end: string
}

interface MetricQuickWindow {
  key: string
  label: string
  days?: number
  months?: number
}

const range = defineModel<MetricRange>({ default: 'hour' })

const props = withDefaults(
  defineProps<{
    ariaLabel?: string
    enableCustomWindow?: boolean
    showPresetButtons?: boolean
    startValue?: string
    endValue?: string
    customButtonLabel?: string
    resetLabel?: string
    showQuickWindows?: boolean
    quickWindowOptions?: MetricQuickWindow[]
  }>(),
  {
    enableCustomWindow: false,
    showPresetButtons: true,
    customButtonLabel: 'common.metricRanges.custom',
    resetLabel: 'common.metricRanges.reset',
    showQuickWindows: true,
    quickWindowOptions: () => [
      { key: '1d', label: 'common.metricRanges.oneDay', days: 1 },
      { key: '3d', label: 'common.metricRanges.threeDays', days: 3 },
      { key: '7d', label: 'common.metricRanges.sevenDays', days: 7 },
      { key: '15d', label: 'common.metricRanges.fifteenDays', days: 15 },
      { key: '1m', label: 'common.metricRanges.oneMonth', months: 1 }
    ]
  }
)

const emit = defineEmits<{
  (event: 'apply-window', value: MetricWindowLocal): void
  (event: 'reset-window'): void
}>()
const { t } = useI18n()

const dialogOpen = ref(false)
const draftStart = ref('')
const draftEnd = ref('')
const windowError = ref<string | null>(null)

const orderedRanges: MetricRange[] = ['week', 'day', 'hour']

const customRangeLabel = computed(() => {
  if (!props.startValue || !props.endValue) return translate(props.customButtonLabel)
  return `${formatLocalDateTime(props.startValue)} - ${formatLocalDateTime(props.endValue)}`
})

function syncDraftWindow() {
  draftStart.value = props.startValue ?? ''
  draftEnd.value = props.endValue ?? ''
  windowError.value = null
}

function formatLocalDateTime(value: string): string {
  const [date, time = ''] = value.split('T')
  return `${date} ${time}`.trim()
}

function pad2(value: number): string {
  return value.toString().padStart(2, '0')
}

function formatDateTimeLocal(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(
    date.getHours()
  )}:${pad2(date.getMinutes())}`
}

function parseDateTimeLocal(value: string): Date | null {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function openDialog() {
  syncDraftWindow()
  dialogOpen.value = true
}

function closeDialog() {
  dialogOpen.value = false
  windowError.value = null
}

function applyQuickWindow(option: MetricQuickWindow) {
  const end = new Date()
  const start = new Date(end)
  if (option.months) {
    start.setMonth(start.getMonth() - option.months)
  } else {
    start.setDate(start.getDate() - (option.days ?? 1))
  }
  draftStart.value = formatDateTimeLocal(start)
  draftEnd.value = formatDateTimeLocal(end)
  windowError.value = null
}

function applyCustomWindow() {
  const startDate = parseDateTimeLocal(draftStart.value)
  const endDate = parseDateTimeLocal(draftEnd.value)
  if (!startDate || !endDate) {
    windowError.value = t('actionDialog.invalidDateRange')
    return
  }
  if (startDate >= endDate) {
    windowError.value = t('actionDialog.invalidDateOrder')
    return
  }
  emit('apply-window', {
    start: draftStart.value,
    end: draftEnd.value
  })
  closeDialog()
}

function resetCustomWindow() {
  emit('reset-window')
  closeDialog()
}

watch(
  () => [props.startValue, props.endValue],
  () => {
    if (!dialogOpen.value) syncDraftWindow()
  }
)
</script>

<template>
  <span
    class="relative inline-flex flex-wrap items-center gap-2"
    :aria-label="ariaLabel ?? t('actionDialog.customTimeRange')"
    @keydown.escape="closeDialog"
  >
    <span
      v-if="showPresetButtons"
      class="isolate inline-flex rounded-full shadow-[var(--shadow-soft)]"
    >
      <button
        v-for="(candidate, index) in orderedRanges"
        :key="candidate"
        type="button"
        :class="[
          range == candidate
            ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
            : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
          index === 0 ? 'rounded-l-full' : '',
          index === orderedRanges.length - 1 ? 'rounded-r-full' : '',
          'relative inline-flex items-center px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
        ]"
        @click="range = candidate"
      >
        {{ t(`common.metricRanges.${candidate}`) }}
      </button>
    </span>

    <button
      v-if="enableCustomWindow"
      type="button"
      class="ui-button-secondary max-w-full truncate px-3 py-2 text-xs"
      data-testid="metric-range-custom-button"
      @click="openDialog"
    >
      {{ customRangeLabel }}
    </button>

    <div
      v-if="enableCustomWindow && dialogOpen"
      class="absolute top-full right-0 z-30 mt-2 w-[min(92vw,22rem)] rounded-[18px] border border-[rgba(80,105,127,0.14)] bg-white p-4 text-left shadow-[var(--shadow-soft)]"
      role="dialog"
      aria-modal="true"
      :aria-label="t('actionDialog.customTimeRange')"
      data-testid="metric-range-dialog"
    >
      <div class="flex items-start justify-between gap-3">
        <div>
          <div class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
            {{ t('actionDialog.customTimeRange') }}
          </div>
          <div class="mt-1 text-xs text-[var(--color-brand-muted)]">
            {{ t('actionDialog.customTimeRangeDescription') }}
          </div>
        </div>
        <button
          type="button"
          class="ui-button-secondary px-2 py-1 text-xs"
          :aria-label="t('actionDialog.closeCustomTimeRange')"
          @click="closeDialog"
        >
          x
        </button>
      </div>

      <div class="mt-4 grid gap-3">
        <div v-if="showQuickWindows" class="flex flex-wrap gap-2">
          <button
            v-for="option in quickWindowOptions"
            :key="option.key"
            type="button"
            class="ui-button-secondary px-3 py-1.5 text-xs"
            :data-testid="`metric-range-quick-${option.key}`"
            @click="applyQuickWindow(option)"
          >
            {{ t(option.label) }}
          </button>
        </div>

        <label class="block text-xs font-semibold text-[var(--color-brand-ink-strong)]">
          {{ t('actionDialog.startTime') }}
          <input
            v-model="draftStart"
            type="datetime-local"
            class="mt-1.5 block w-full rounded-[12px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2 text-sm text-[var(--color-brand-ink-strong)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
            data-testid="metric-range-start"
          />
        </label>
        <label class="block text-xs font-semibold text-[var(--color-brand-ink-strong)]">
          {{ t('actionDialog.endTime') }}
          <input
            v-model="draftEnd"
            type="datetime-local"
            class="mt-1.5 block w-full rounded-[12px] border border-[rgba(80,105,127,0.14)] bg-white px-3 py-2 text-sm text-[var(--color-brand-ink-strong)] outline-hidden focus:border-[rgba(182,232,44,0.65)] focus:ring-4 focus:ring-[rgba(182,232,44,0.18)]"
            data-testid="metric-range-end"
          />
        </label>
      </div>

      <p v-if="windowError" class="mt-3 text-sm text-red-600">
        {{ windowError }}
      </p>

      <div class="mt-4 flex flex-wrap justify-end gap-2">
        <button
          type="button"
          class="ui-button-secondary px-3 py-2 text-xs"
          data-testid="metric-range-reset"
          @click="resetCustomWindow"
        >
          {{ translate(resetLabel) }}
        </button>
        <button
          type="button"
          class="ui-button-primary px-3 py-2 text-xs"
          data-testid="metric-range-apply"
          @click="applyCustomWindow"
        >
          {{ t('common.buttons.apply') }}
        </button>
      </div>
    </div>
  </span>
</template>

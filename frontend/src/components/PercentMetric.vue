<script setup lang="ts">
import { ChartPieIcon } from '@heroicons/vue/20/solid'
import { computed } from 'vue'
import { formatPercentValue } from '@/composables/percentages'

const props = withDefaults(
  defineProps<{
    value: number | null | undefined
    label?: string
    size?: 'sm' | 'md' | 'lg'
    maximumFractionDigits?: number
    tone?: 'default' | 'success' | 'warning' | 'danger'
  }>(),
  {
    label: undefined,
    size: 'md',
    maximumFractionDigits: 1,
    tone: 'default'
  }
)

const displayValue = computed(() => formatPercentValue(props.value, props.maximumFractionDigits))

const toneClass = computed(() => {
  if (props.tone === 'success') return 'ui-percent-badge-success'
  if (props.tone === 'warning') return 'ui-percent-badge-warning'
  if (props.tone === 'danger') return 'ui-percent-badge-danger'
  return 'ui-percent-badge-default'
})
</script>

<template>
  <span :class="['ui-percent-badge', `ui-percent-badge-${size}`, toneClass]">
    <span class="ui-percent-badge-icon-shell">
      <ChartPieIcon class="ui-percent-badge-icon" aria-hidden="true" />
    </span>
    <span class="ui-percent-badge-value">{{ displayValue }}%</span>
    <span v-if="label" class="ui-percent-badge-label">{{ label }}</span>
  </span>
</template>

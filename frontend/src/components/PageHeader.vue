<script setup lang="ts">
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    kicker?: string
    title: string
    description?: string
    metricValue?: string | number
    metricLabel?: string
  }>(),
  {
    kicker: undefined,
    description: undefined,
    metricValue: undefined,
    metricLabel: undefined
  }
)

const { t } = useI18n()
</script>

<template>
  <div class="ui-page-header">
    <div class="ui-page-copy">
      <p v-if="kicker" class="ui-page-kicker">{{ t(kicker) }}</p>
      <h1 class="ui-page-title">{{ t(title) }}</h1>
      <p v-if="description" class="ui-page-description">{{ t(description) }}</p>
    </div>
    <div v-if="$slots.actions || metricValue !== undefined" class="ui-page-aside">
      <div v-if="metricValue !== undefined" class="ui-page-metric">
        <div class="ui-page-metric-value">{{ metricValue }}</div>
        <div v-if="metricLabel" class="ui-page-metric-label">{{ t(metricLabel) }}</div>
      </div>
      <div v-if="$slots.actions" class="ui-page-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

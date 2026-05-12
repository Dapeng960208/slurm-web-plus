<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { translate } from '@/i18n/translate'

withDefaults(
  defineProps<{
    kicker?: string
    title: string
    description?: string
    metricValue?: string | number
    metricLabel?: string
    kickerParams?: Record<string, unknown>
    titleParams?: Record<string, unknown>
    descriptionParams?: Record<string, unknown>
    metricLabelParams?: Record<string, unknown>
  }>(),
  {
    kicker: undefined,
    description: undefined,
    metricValue: undefined,
    metricLabel: undefined,
    kickerParams: undefined,
    titleParams: undefined,
    descriptionParams: undefined,
    metricLabelParams: undefined
  }
)

useI18n()
</script>

<template>
  <div class="ui-page-header">
    <div class="ui-page-copy">
      <p v-if="kicker" class="ui-page-kicker">{{ translate(kicker, kickerParams) }}</p>
      <h1 class="ui-page-title">{{ translate(title, titleParams) }}</h1>
      <p v-if="description" class="ui-page-description">
        {{ translate(description, descriptionParams) }}
      </p>
    </div>
    <div v-if="$slots.actions || metricValue !== undefined" class="ui-page-aside">
      <div v-if="metricValue !== undefined" class="ui-page-metric">
        <div class="ui-page-metric-value">{{ metricValue }}</div>
        <div v-if="metricLabel" class="ui-page-metric-label">
          {{ translate(metricLabel, metricLabelParams) }}
        </div>
      </div>
      <div v-if="$slots.actions" class="ui-page-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    kicker?: string
    title: string
    description?: string
    metricValue?: string | number
    metricLabel?: string
  }>(),
  {
    kicker: 'Slurm Monitor',
    description: undefined,
    metricValue: undefined,
    metricLabel: undefined
  }
)
</script>

<template>
  <div class="ui-page-header">
    <div class="ui-page-copy">
      <p v-if="kicker" class="ui-page-kicker">{{ kicker }}</p>
      <h1 class="ui-page-title">{{ title }}</h1>
      <p v-if="description" class="ui-page-description">{{ description }}</p>
    </div>
    <div v-if="$slots.actions || metricValue !== undefined" class="ui-page-aside">
      <div v-if="metricValue !== undefined" class="ui-page-metric">
        <div class="ui-page-metric-value">{{ metricValue }}</div>
        <div v-if="metricLabel" class="ui-page-metric-label">{{ metricLabel }}</div>
      </div>
      <div v-if="$slots.actions" class="ui-page-actions">
        <slot name="actions" />
      </div>
    </div>
  </div>
</template>

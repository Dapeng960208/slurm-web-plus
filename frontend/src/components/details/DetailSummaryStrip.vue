<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'

type SummaryItem = {
  id: string
  label: string
  value: string
  subtle?: string
  to?: RouteLocationRaw
}

defineProps<{
  items: SummaryItem[]
}>()
</script>

<template>
  <div class="ui-summary-strip" data-testid="detail-summary-strip">
    <div v-for="item in items" :key="item.id" class="ui-summary-item">
      <div class="ui-summary-label">{{ item.label }}</div>
      <div class="ui-summary-value">
        <RouterLink
          v-if="item.to && item.value !== '-'"
          :to="item.to"
          class="text-[var(--color-brand-blue)] transition hover:text-[var(--color-brand-ink-strong)]"
        >
          {{ item.value }}
        </RouterLink>
        <template v-else>
          {{ item.value }}
        </template>
      </div>
      <div v-if="item.subtle" class="ui-summary-subtle">{{ item.subtle }}</div>
    </div>
  </div>
</template>

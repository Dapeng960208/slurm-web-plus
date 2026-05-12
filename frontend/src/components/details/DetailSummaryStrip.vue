<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { RouteLocationRaw } from 'vue-router'
import { translate } from '@/i18n/translate'

type SummaryItem = {
  id: string
  label: string
  value: string
  subtle?: string
  to?: RouteLocationRaw
  translateLabel?: boolean
  translateSubtle?: boolean
}

defineProps<{
  items: SummaryItem[]
}>()
</script>

<template>
  <div class="ui-summary-strip" data-testid="detail-summary-strip">
    <div v-for="item in items" :key="item.id" class="ui-summary-item">
      <div class="ui-summary-label">
        {{ item.translateLabel === false ? item.label : translate(item.label) }}
      </div>
      <div class="ui-summary-value">
        <RouterLink
          v-if="item.to && item.value !== '-'"
          :to="item.to"
          class="ui-partition-link-chip"
        >
          {{ item.value }}
        </RouterLink>
        <template v-else>
          {{ item.value }}
        </template>
      </div>
      <div v-if="item.subtle" class="ui-summary-subtle">
        {{ item.translateSubtle === false ? item.subtle : translate(item.subtle) }}
      </div>
    </div>
  </div>
</template>

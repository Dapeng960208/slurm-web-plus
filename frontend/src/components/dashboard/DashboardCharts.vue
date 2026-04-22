<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onBeforeMount } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import ChartResourcesHistogram from '@/components/dashboard/ChartResourcesHistogram.vue'
import ChartJobsHistogram from '@/components/dashboard/ChartJobsHistogram.vue'
import { isMetricRange, type MetricRange } from '@/composables/GatewayAPI'

const { cluster } = defineProps<{ cluster: string }>()

const router = useRouter()
const route = useRoute()
const runtimeStore = useRuntimeStore()

function setRange(range: MetricRange) {
  runtimeStore.dashboard.range = range
  router.push({ name: 'dashboard', query: runtimeStore.dashboard.query() as LocationQueryRaw })
}

onBeforeMount(() => {
  if (route.query.range && isMetricRange(route.query.range)) {
    runtimeStore.dashboard.range = route.query.range
  } else {
    runtimeStore.dashboard.range = 'hour'
  }
})
</script>

<template>
  <div class="ui-panel ui-section mt-6">
    <div class="mb-5 flex flex-wrap items-end justify-between gap-4">
      <div>
        <h2 class="ui-panel-title">Historical metrics</h2>
        <p class="ui-panel-description">Switch time range to compare resource pressure and job activity.</p>
      </div>
      <span class="isolate inline-flex rounded-full shadow-[var(--shadow-soft)]">
        <button
          type="button"
          :class="[
            runtimeStore.dashboard.range == 'week'
              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
              : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
            'relative inline-flex items-center rounded-l-full px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
          ]"
          @click="setRange('week')"
        >
          week
        </button>
        <button
          type="button"
          :class="[
            runtimeStore.dashboard.range == 'day'
              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
              : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
            'relative inline-flex items-center px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
          ]"
          @click="setRange('day')"
        >
          day
        </button>
        <button
          type="button"
          :class="[
            runtimeStore.dashboard.range == 'hour'
              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
              : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
            'relative inline-flex items-center rounded-r-full px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
          ]"
          @click="setRange('hour')"
        >
          hour
        </button>
      </span>
    </div>
  </div>
  <ChartResourcesHistogram v-if="runtimeStore.hasPermission('view-nodes')" :cluster="cluster" />
  <ChartJobsHistogram v-if="runtimeStore.hasPermission('view-jobs')" :cluster="cluster" />
</template>

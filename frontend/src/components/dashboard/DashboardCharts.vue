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
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
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
        <h2 class="ui-panel-title">Realtime Metrics</h2>
        <p class="ui-panel-description">Switch time range to inspect recent resource pressure and job activity.</p>
      </div>
      <MetricRangeSelector
        :model-value="runtimeStore.dashboard.range"
        aria-label="Select dashboard metrics range"
        @update:model-value="setRange"
      />
    </div>
  </div>
  <ChartResourcesHistogram v-if="runtimeStore.hasPermission('view-nodes')" :cluster="cluster" />
  <ChartJobsHistogram v-if="runtimeStore.hasPermission('view-jobs')" :cluster="cluster" />
</template>

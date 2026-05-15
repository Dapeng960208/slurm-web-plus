<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { onBeforeMount, useTemplateRef, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import type { ChartResourcesType } from '@/stores/runtime/dashboard'
import { isChartResourcesType } from '@/stores/runtime/dashboard'
import { useLiveHistogram } from '@/composables/charts/LiveHistogram'
import { formatGigabytes } from '@/composables/charts/formatters'
import type {
  DashboardMetricsQuery,
  GatewayAnyClusterApiKey,
  MetricMemoryState,
  MetricResourceState
} from '@/composables/GatewayAPI'
import ChartSkeleton from '@/components/ChartSkeleton.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'

const props = defineProps<{
  cluster: string
  metricsQuery?: DashboardMetricsQuery
  routeTargetName?: string
  compact?: boolean
}>()

const router = useRouter()
const route = useRoute()
const runtimeStore = useRuntimeStore()
const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')

type ChartResourceMetricState = MetricResourceState | MetricMemoryState

/* Note that order of keys determines the stack of metrics in histogram */
const resourceLabels: Record<string, { group: MetricResourceState[]; color: string }> = {
  unknown: {
    group: ['unknown'],
    color: 'rgb(192, 191, 188, 0.7)' // grey
  },
  down: {
    group: ['down'],
    color: 'rgb(204, 0, 0, 0.7)' // red
  },
  fail: {
    group: ['fail'],
    color: 'rgb(214, 93, 11, 0.7)' // dark orange
  },
  error: {
    group: ['error'],
    color: 'rgb(143, 23, 49, 0.7)' // dark purple
  },
  drain: {
    group: ['drain'],
    color: 'rgb(204, 0, 153, 0.7)' // purple
  },
  allocated: {
    group: ['allocated'],
    color: 'rgba(236, 183, 23, 0.7)' // ellow
  },
  mixed: {
    group: ['mixed'],
    color: 'rgba(246, 221, 56, 0.7)' // light yellow
  },
  idle: {
    group: ['idle'],
    color: 'rgb(51, 204, 51, 0.7)' // green
  }
}

const memoryLabels: Record<string, { group: MetricMemoryState[]; color: string }> = {
  'Allocated Memory': {
    group: ['allocated'],
    color: 'rgb(212, 154, 62, 0.78)' // allocated by jobs
  },
  'Available Memory': {
    group: ['idle'],
    color: 'rgb(82, 170, 78, 0.76)' // available capacity
  }
}

function resourcesTypeCallback(): GatewayAnyClusterApiKey {
  if (runtimeStore.dashboard.chartResourcesType == 'cores') {
    return 'metrics_cores'
  } else if (runtimeStore.dashboard.chartResourcesType == 'memory') {
    return 'metrics_memory'
  } else if (runtimeStore.dashboard.chartResourcesType == 'gpus') {
    return 'metrics_gpus'
  } else {
    return 'metrics_nodes'
  }
}

function formatResourceValue(value: number): string | undefined {
  if (runtimeStore.dashboard.chartResourcesType == 'memory') {
    return formatGigabytes(value)
  }
}

function resourcesLabels(): Record<
  string,
  { group: ChartResourceMetricState[]; color: string }
> {
  if (runtimeStore.dashboard.chartResourcesType == 'memory') {
    return memoryLabels as Record<string, { group: ChartResourceMetricState[]; color: string }>
  }
  return resourceLabels as Record<string, { group: ChartResourceMetricState[]; color: string }>
}

const liveChart = useLiveHistogram<ChartResourceMetricState>(
  props.cluster,
  resourcesTypeCallback(),
  chartCanvas,
  resourcesLabels(),
  runtimeStore.dashboard.range,
  props.metricsQuery ?? runtimeStore.dashboard.metricsQuery(),
  formatResourceValue
)

function currentMetricsQuery() {
  return props.metricsQuery ?? runtimeStore.dashboard.metricsQuery()
}

function setResourceType(resourceType: ChartResourcesType) {
  runtimeStore.dashboard.chartResourcesType = resourceType
  router.push({
    name: props.routeTargetName ?? 'dashboard',
    params: route.params,
    query: runtimeStore.dashboard.query() as LocationQueryRaw
  })
}

/* Clear chart datasets and set new poller callback when dashboard range is
 * modified. */
watch(
  () => runtimeStore.dashboard.chartResourcesType,
  () => {
    router.push({
      name: props.routeTargetName ?? 'dashboard',
      params: route.params,
      query: runtimeStore.dashboard.query() as LocationQueryRaw
    })
    liveChart.setLabels(resourcesLabels())
    liveChart.setCallback(resourcesTypeCallback())
  }
)

watch(
  () => [runtimeStore.dashboard.range, runtimeStore.dashboard.start, runtimeStore.dashboard.end, props.metricsQuery],
  () => {
    liveChart.setRange(runtimeStore.dashboard.range, currentMetricsQuery())
  }
)

watch(
  () => [runtimeStore.dashboard.partition, props.metricsQuery],
  () => {
    liveChart.setRange(runtimeStore.dashboard.range, currentMetricsQuery())
  }
)

watch(
  () => props.cluster,
  (new_cluster) => {
    liveChart.setCluster(new_cluster)
  }
)

onBeforeMount(() => {
  if (route.query.resources && isChartResourcesType(route.query.resources)) {
    /* Retrieve the resources criteria from query and update the store */
    runtimeStore.dashboard.chartResourcesType = route.query.resources
  }
})
</script>

<template>
  <div class="flex flex-wrap items-center justify-between gap-3 border-b border-gray-200 pb-3 dark:border-gray-700">
    <h3 class="text-base font-semibold text-gray-900 dark:text-gray-200">Resources Status</h3>
    <div class="text-right">
      <span class="ui-segmented-control">
        <button
          type="button"
          :class="[
            'ui-segmented-button',
            runtimeStore.dashboard.chartResourcesType == 'nodes' && 'ui-segmented-button-active'
          ]"
          @click="setResourceType('nodes')"
        >
          Nodes
        </button>
        <button
          type="button"
          :class="[
            'ui-segmented-button',
            runtimeStore.dashboard.chartResourcesType == 'cores' && 'ui-segmented-button-active'
          ]"
          @click="setResourceType('cores')"
        >
          Cores
        </button>
        <button
          type="button"
          :class="[
            'ui-segmented-button',
            runtimeStore.dashboard.chartResourcesType == 'memory' &&
              'ui-segmented-button-active'
          ]"
          @click="setResourceType('memory')"
        >
          Memory
        </button>
        <button
          type="button"
          :class="[
            'ui-segmented-button',
            runtimeStore.dashboard.chartResourcesType == 'gpus' && 'ui-segmented-button-active'
          ]"
          @click="setResourceType('gpus')"
        >
          GPU
        </button>
      </span>
    </div>
  </div>
  <ErrorAlert v-if="liveChart.metrics.unable.value"
    >Unable to retrieve resource metrics.</ErrorAlert
  >
  <div v-else :class="['ui-chart-shell', props.compact ? 'partition-chart-shell' : '']">
    <ChartSkeleton v-show="!liveChart.metrics.loaded.value" />
    <canvas
      v-show="liveChart.metrics.loaded.value"
      ref="chartCanvas"
      class="h-full w-full"
    ></canvas>
  </div>
</template>

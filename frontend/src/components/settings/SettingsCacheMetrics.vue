<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useTemplateRef, ref } from 'vue'
import type { ClusterDescription, MetricCacheResult } from '@/composables/GatewayAPI'
import { useLiveHistogram } from '@/composables/charts/LiveHistogram'
import ChartSkeleton from '@/components/ChartSkeleton.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'

const { cluster } = defineProps<{ cluster: ClusterDescription }>()

const range = ref<string>('hour')

function setRange(newRange: string) {
  range.value = newRange
  chart.setRange(newRange)
}

const labels: Record<string, { group: MetricCacheResult[]; color: string; invert?: boolean }> = {
  hit: {
    group: ['hit'],
    color: 'rgba(123, 191, 31, 0.78)'
  },
  miss: {
    group: ['miss'],
    color: 'rgba(216, 75, 80, 0.72)',
    invert: true
  }
}

const chartCanvas = useTemplateRef<HTMLCanvasElement>('chartCanvas')
const chart = useLiveHistogram<MetricCacheResult>(
  cluster.name,
  'metrics_cache',
  chartCanvas,
  labels,
  range.value
)
</script>

<template>
  <div class="ui-panel ui-section mt-6">
    <div class="mb-5 flex flex-wrap items-start justify-between gap-4">
      <div>
        <h3 class="ui-panel-title">Cache Metrics</h3>
        <p class="ui-panel-description mt-2">Live hit and miss activity across cache operations.</p>
      </div>
      <div class="isolate inline-flex rounded-full shadow-[var(--shadow-soft)]">
        <button
          type="button"
          id="range-week"
          :class="[
            range === 'week'
              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
              : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
            'relative inline-flex items-center rounded-l-full px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset'
          ]"
          @click="setRange('week')"
        >
          week
        </button>
        <button
          type="button"
          id="range-day"
          :class="[
            range === 'day'
              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
              : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
            'relative inline-flex items-center px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset'
          ]"
          @click="setRange('day')"
        >
          day
        </button>
        <button
          type="button"
          id="range-hour"
          :class="[
            range === 'hour'
              ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
              : 'bg-white text-[var(--color-brand-muted)] hover:bg-[rgba(182,232,44,0.12)]',
            'relative inline-flex items-center rounded-r-full px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset'
          ]"
          @click="setRange('hour')"
        >
          hour
        </button>
      </div>
    </div>

    <ErrorAlert v-if="chart.metrics.unable.value" class="mt-4">
      Unable to retrieve cache metrics.
    </ErrorAlert>
    <div v-else class="ui-chart-shell">
      <ChartSkeleton v-show="!chart.metrics.loaded.value" />
      <canvas v-show="chart.metrics.loaded.value" ref="chartCanvas" class="h-full w-full"></canvas>
    </div>
  </div>
</template>

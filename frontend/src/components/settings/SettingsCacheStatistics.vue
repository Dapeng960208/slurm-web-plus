<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { watch } from 'vue'
import type { ClusterDescription, CacheStatistics } from '@/composables/GatewayAPI'
import { useClusterDataPoller } from '@/composables/DataPoller'
import useDoughnutChart from '@/composables/charts/Doughnut'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import { ArrowPathIcon } from '@heroicons/vue/20/solid'
import { useGatewayAPI } from '@/composables/GatewayAPI'

const { cluster } = defineProps<{ cluster: ClusterDescription }>()

const gatewayAPI = useGatewayAPI()

const { data, unable, loaded } = useClusterDataPoller<CacheStatistics>(
  cluster.name,
  'cache_stats',
  30000
)

function doughnutChartData() {
  if (!data.value) return [0, 0]
  return [data.value.hit.total, data.value.miss.total]
}

const doughnutChart = useDoughnutChart(
  'chartCanvas',
  [
    { name: 'hit', color: 'rgba(123, 191, 31, 0.78)' },
    { name: 'miss', color: 'rgba(216, 75, 80, 0.72)' }
  ],
  doughnutChartData()
)

watch(
  () => data.value,
  () => doughnutChart.updateData(doughnutChartData())
)

function hitValue(key: string): number {
  if (!data.value) return 0
  return key in data.value.hit.keys ? data.value.hit.keys[key] : 0
}

async function resetCache(clusterName: string) {
  data.value = await gatewayAPI.cache_reset(clusterName)
}

function hitRateTotal(): string {
  if (!data.value) return '-'
  if (!(data.value.miss.total + data.value.hit.total)) return '-'
  return (
    ((data.value.hit.total / (data.value.miss.total + data.value.hit.total)) * 100).toFixed(2) + '%'
  )
}

function hitRateKey(key: string, value: number): string {
  if (!(hitValue(key) + value)) return '-'
  return ((hitValue(key) / (hitValue(key) + value)) * 100).toFixed(2) + '%'
}
</script>

<template>
  <ErrorAlert v-if="unable" class="mt-4">Unable to retrieve cache statistics.</ErrorAlert>
  <div v-else-if="!loaded" class="mt-4 text-[var(--color-brand-muted)]">
    <LoadingSpinner :size="5" />
    Loading statistics…
  </div>
  <div v-else-if="data" class="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(220px,0.8fr)]">
    <div class="ui-table-shell overflow-x-auto">
      <div class="border-b border-[rgba(80,105,127,0.08)] px-6 py-5">
        <h3 class="ui-panel-title">Cache Statistics</h3>
        <p class="ui-panel-description mt-2">
          Hit and miss ratios by key group, plus the total hit rate across the cluster cache.
        </p>
      </div>

      <div class="inline-block min-w-full align-middle">
        <table class="ui-table min-w-full">
          <thead>
            <tr>
              <th scope="col" class="py-3.5 pr-4 pl-6 text-left">Name</th>
              <th scope="col" class="px-4 py-3.5 text-left">Hit</th>
              <th scope="col" class="px-4 py-3.5 text-left">Miss</th>
              <th scope="col" class="px-4 py-3.5 text-left">Total</th>
              <th scope="col" class="py-3.5 pr-4 pl-4 text-left">Hit rate</th>
            </tr>
          </thead>
          <tbody class="text-sm text-[var(--color-brand-muted)]">
            <tr v-for="(value, key) in data.miss.keys" :key="key">
              <td class="py-4 pr-4 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                {{ key }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap">{{ hitValue(key) }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ value }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ value + hitValue(key) }}</td>
              <td class="py-4 pr-4 pl-4 whitespace-nowrap">{{ hitRateKey(key, value) }}</td>
            </tr>
            <tr>
              <td class="py-4 pr-4 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                Total
              </td>
              <td class="px-4 py-4 whitespace-nowrap">{{ data.hit.total }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ data.miss.total }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ data.hit.total + data.miss.total }}</td>
              <td class="py-4 pr-4 pl-4 whitespace-nowrap">{{ hitRateTotal() }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div
        v-if="cluster.permissions.actions.includes('cache-reset')"
        class="border-t border-[rgba(80,105,127,0.08)] px-6 py-4"
      >
        <button type="button" class="ui-button-secondary" @click="resetCache(cluster.name)">
          <ArrowPathIcon class="h-5 w-5" aria-hidden="true" />
          Reset statistics
        </button>
      </div>
    </div>

    <div class="ui-panel ui-section flex items-center justify-center">
      <div class="w-full max-w-72">
        <canvas ref="chartCanvas"></canvas>
      </div>
    </div>
  </div>
</template>

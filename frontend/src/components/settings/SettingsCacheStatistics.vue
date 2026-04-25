<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import type { ClusterDescription, CacheStatistics } from '@/composables/GatewayAPI'
import { useClusterDataPoller } from '@/composables/DataPoller'
import useDoughnutChart from '@/composables/charts/Doughnut'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PercentMetric from '@/components/PercentMetric.vue'
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

const cacheKeys = computed(() => {
  if (!data.value) return []
  return [...new Set([...Object.keys(data.value.hit.keys), ...Object.keys(data.value.miss.keys)])].sort()
})

const totalRequests = computed(() => {
  if (!data.value) return 0
  return data.value.hit.total + data.value.miss.total
})

const hasTraffic = computed(() => totalRequests.value > 0)

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

function missValue(key: string): number {
  if (!data.value) return 0
  return key in data.value.miss.keys ? data.value.miss.keys[key] : 0
}

async function resetCache(clusterName: string) {
  data.value = await gatewayAPI.cache_reset(clusterName)
}

function hitRateTotal(): number | null {
  if (!data.value) return null
  if (!(data.value.miss.total + data.value.hit.total)) return null
  return (data.value.hit.total / (data.value.miss.total + data.value.hit.total)) * 100
}

function hitRateKey(key: string, value: number): number | null {
  if (!(hitValue(key) + value)) return null
  return (hitValue(key) / (hitValue(key) + value)) * 100
}
</script>

<template>
  <ErrorAlert v-if="unable" class="mt-4">Unable to retrieve cache statistics.</ErrorAlert>
  <div v-else-if="!loaded" class="mt-4 text-[var(--color-brand-muted)]">
    <LoadingSpinner :size="5" />
    Loading statistics...
  </div>
  <div
    v-else-if="data"
    :class="[
      'grid gap-6',
      hasTraffic ? 'xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]' : 'grid-cols-1'
    ]"
  >
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
            <tr v-for="key in cacheKeys" :key="key">
              <td class="py-4 pr-4 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                {{ key }}
              </td>
              <td class="px-4 py-4 whitespace-nowrap">{{ hitValue(key) }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ missValue(key) }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ missValue(key) + hitValue(key) }}</td>
              <td class="py-4 pr-4 pl-4 whitespace-nowrap">
                <PercentMetric :value="hitRateKey(key, missValue(key))" size="sm" :maximum-fraction-digits="2" />
              </td>
            </tr>
            <tr>
              <td class="py-4 pr-4 pl-6 font-medium whitespace-nowrap text-[var(--color-brand-ink-strong)]">
                Total
              </td>
              <td class="px-4 py-4 whitespace-nowrap">{{ data.hit.total }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ data.miss.total }}</td>
              <td class="px-4 py-4 whitespace-nowrap">{{ data.hit.total + data.miss.total }}</td>
              <td class="py-4 pr-4 pl-4 whitespace-nowrap">
                <PercentMetric :value="hitRateTotal()" size="sm" :maximum-fraction-digits="2" />
              </td>
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

    <div class="ui-panel ui-section flex flex-col gap-6">
      <div>
        <p class="ui-page-kicker">Cache Overview</p>
        <h3 class="ui-panel-title">Traffic Snapshot</h3>
        <p class="ui-panel-description mt-2">
          {{
            hasTraffic
              ? 'Quick totals and hit quality for the current cache activity window.'
              : 'No cache requests have been recorded yet, so the chart stays hidden until traffic arrives.'
          }}
        </p>
      </div>

      <dl class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        <div class="rounded-2xl border border-[rgba(80,105,127,0.12)] bg-white/75 px-4 py-3">
          <dt class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-muted)]">
            Hit rate
          </dt>
          <dd class="mt-2">
            <PercentMetric :value="hitRateTotal()" :maximum-fraction-digits="2" />
          </dd>
        </div>
        <div class="rounded-2xl border border-[rgba(80,105,127,0.12)] bg-white/75 px-4 py-3">
          <dt class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-muted)]">
            Requests
          </dt>
          <dd class="mt-2 text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
            {{ totalRequests }}
          </dd>
        </div>
        <div class="rounded-2xl border border-[rgba(80,105,127,0.12)] bg-white/75 px-4 py-3">
          <dt class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-muted)]">
            Key groups
          </dt>
          <dd class="mt-2 text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
            {{ cacheKeys.length }}
          </dd>
        </div>
      </dl>

      <div
        v-if="!hasTraffic"
        class="rounded-[24px] border border-dashed border-[rgba(80,105,127,0.18)] bg-[rgba(244,248,251,0.86)] px-5 py-6"
      >
        <p class="text-sm font-semibold text-[var(--color-brand-ink-strong)]">
          Waiting for cache activity
        </p>
        <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
          Once the cluster records cache hits or misses, the distribution chart will appear here.
        </p>
      </div>

      <div v-show="hasTraffic" class="mx-auto w-full max-w-72">
        <canvas ref="chartCanvas" class="w-full"></canvas>
      </div>
    </div>
  </div>
</template>

<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ClusterDescription, CacheStatistics } from '@/composables/GatewayAPI'
import { useClusterDataPoller } from '@/composables/DataPoller'
import useDoughnutChart from '@/composables/charts/Doughnut'
import ErrorAlert from '@/components/ErrorAlert.vue'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
import PercentMetric from '@/components/PercentMetric.vue'
import { ArrowPathIcon } from '@heroicons/vue/20/solid'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster } = defineProps<{ cluster: ClusterDescription }>()

const gatewayAPI = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const { t, locale } = useI18n()

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

const doughnutChart = useDoughnutChart('chartCanvas', [], doughnutChartData())

function currentChartLabels() {
  return [
    { name: t('settings.cache.statistics.chart.hit'), color: 'rgba(123, 191, 31, 0.78)' },
    { name: t('settings.cache.statistics.chart.miss'), color: 'rgba(216, 75, 80, 0.72)' }
  ]
}

watch(
  () => data.value,
  () => doughnutChart.updateData(doughnutChartData())
)

watch(
  () => locale.value,
  () => doughnutChart.setLabels(currentChartLabels()),
  { immediate: true }
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
  <ErrorAlert v-if="unable" class="mt-4">{{ t('settings.cache.statistics.error') }}</ErrorAlert>
  <div v-else-if="!loaded" class="mt-4 text-[var(--color-brand-muted)]">
    <LoadingSpinner :size="5" />
    {{ t('settings.cache.statistics.loading') }}
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
        <h3 class="ui-panel-title">{{ t('settings.cache.statistics.title') }}</h3>
        <p class="ui-panel-description mt-2">
          {{ t('settings.cache.statistics.description') }}
        </p>
      </div>

      <div class="inline-block min-w-full align-middle">
        <table class="ui-table min-w-full">
          <thead>
            <tr>
              <th scope="col" class="py-3.5 pr-4 pl-6 text-left">{{ t('settings.cache.statistics.columns.name') }}</th>
              <th scope="col" class="px-4 py-3.5 text-left">{{ t('settings.cache.statistics.columns.hit') }}</th>
              <th scope="col" class="px-4 py-3.5 text-left">{{ t('settings.cache.statistics.columns.miss') }}</th>
              <th scope="col" class="px-4 py-3.5 text-left">{{ t('settings.cache.statistics.columns.total') }}</th>
              <th scope="col" class="py-3.5 pr-4 pl-4 text-left">{{ t('settings.cache.statistics.columns.hitRate') }}</th>
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
                {{ t('settings.cache.statistics.total') }}
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
        v-if="
          runtimeStore.hasRoutePermission(cluster.name, 'settings/cache', 'edit') ||
          runtimeStore.hasRoutePermission(cluster.name, 'admin/cache', 'edit')
        "
        class="border-t border-[rgba(80,105,127,0.08)] px-6 py-4"
      >
        <button type="button" class="ui-button-secondary" @click="resetCache(cluster.name)">
          <ArrowPathIcon class="h-5 w-5" aria-hidden="true" />
          {{ t('settings.cache.statistics.reset') }}
        </button>
      </div>
    </div>

    <div class="ui-panel ui-section flex flex-col gap-6">
      <div>
        <p class="ui-page-kicker">{{ t('settings.cache.statistics.overviewKicker') }}</p>
        <h3 class="ui-panel-title">{{ t('settings.cache.statistics.overviewTitle') }}</h3>
        <p class="ui-panel-description mt-2">
          {{
            hasTraffic
              ? t('settings.cache.statistics.overviewDescription')
              : t('settings.cache.statistics.overviewEmptyDescription')
          }}
        </p>
      </div>

      <dl class="grid gap-3 sm:grid-cols-3 xl:grid-cols-1">
        <div class="rounded-2xl border border-[rgba(80,105,127,0.12)] bg-white/75 px-4 py-3">
          <dt class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-muted)]">
            {{ t('settings.cache.statistics.cards.hitRate') }}
          </dt>
          <dd class="mt-2">
            <PercentMetric :value="hitRateTotal()" :maximum-fraction-digits="2" />
          </dd>
        </div>
        <div class="rounded-2xl border border-[rgba(80,105,127,0.12)] bg-white/75 px-4 py-3">
          <dt class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-muted)]">
            {{ t('settings.cache.statistics.cards.requests') }}
          </dt>
          <dd class="mt-2 text-2xl font-semibold text-[var(--color-brand-ink-strong)]">
            {{ totalRequests }}
          </dd>
        </div>
        <div class="rounded-2xl border border-[rgba(80,105,127,0.12)] bg-white/75 px-4 py-3">
          <dt class="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--color-brand-muted)]">
            {{ t('settings.cache.statistics.cards.keyGroups') }}
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
          {{ t('settings.cache.statistics.waitingTitle') }}
        </p>
        <p class="mt-2 text-sm text-[var(--color-brand-muted)]">
          {{ t('settings.cache.statistics.waitingDescription') }}
        </p>
      </div>

      <div v-show="hasTraffic" class="mx-auto w-full max-w-72">
        <canvas ref="chartCanvas" class="w-full"></canvas>
      </div>
    </div>
  </div>
</template>

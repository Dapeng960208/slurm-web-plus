<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, onBeforeMount, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useClusterDataGetter } from '@/composables/DataGetter'
import { getMBHumanUnit } from '@/composables/GatewayAPI'
import type { ClusterStats } from '@/composables/GatewayAPI'
import type { ClusterPartition } from '@/composables/GatewayAPI'
import { isMetricRange, type MetricRange } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import { useClusterDataPoller } from '@/composables/DataPoller'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import DashboardCharts from '@/components/dashboard/DashboardCharts.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import PageHeader from '@/components/PageHeader.vue'

const runtimeStore = useRuntimeStore()
const route = useRoute()
const router = useRouter()
const { t } = useI18n()

const props = defineProps<{ cluster: string }>()
const cluster = computed(() => props.cluster)

const { data, unable, loaded, setCluster, setParam } = useClusterDataPoller<ClusterStats>(
  cluster.value,
  'stats',
  10000,
  runtimeStore.dashboard.partition ? { partition: runtimeStore.dashboard.partition } : undefined
)
const canSelectPartition = computed(() =>
  runtimeStore.hasRoutePermission(cluster.value, 'jobs/filter-partitions', 'view') ||
  runtimeStore.hasRoutePermission(cluster.value, 'resources/filter-partitions', 'view')
)
const {
  data: partitions,
  loaded: partitionsLoaded,
  setCluster: setPartitionsCluster
} = useClusterDataGetter<ClusterPartition[]>(
  cluster.value,
  'partitions',
  undefined,
  canSelectPartition
)

const partitionOptions = computed(() => [
  { label: t('pages.dashboard.partitionAll'), value: '' },
  ...((partitions.value ?? []).map((partition) => ({
    label: partition.name,
    value: partition.name
  })) as Array<{ label: string; value: string }>)
])

const allowedPartitionNames = computed(() => new Set((partitions.value ?? []).map((item) => item.name)))

function syncQuery() {
  router.push({
    name: 'dashboard',
    query: runtimeStore.dashboard.query() as LocationQueryRaw
  })
}

function setRange(range: MetricRange) {
  runtimeStore.dashboard.range = range
  runtimeStore.dashboard.clearWindow()
  syncQuery()
}

function applyMetricsWindow(window: { start: string; end: string }) {
  runtimeStore.dashboard.setWindow(window)
  syncQuery()
}

function resetMetricsWindow() {
  runtimeStore.dashboard.clearWindow()
  runtimeStore.dashboard.range = 'hour'
  syncQuery()
}

onBeforeMount(() => {
  if (route.query.range && isMetricRange(route.query.range)) {
    runtimeStore.dashboard.range = route.query.range
  } else {
    runtimeStore.dashboard.range = 'hour'
  }
})

watch(
  () => route.query,
  (query) => {
    runtimeStore.dashboard.restoreQuery(query)
  },
  { immediate: true }
)

watch(
  () => cluster.value,
  (newCluster) => {
    setCluster(newCluster)
    setPartitionsCluster(newCluster)
  }
)

watch(
  [canSelectPartition, allowedPartitionNames, partitionsLoaded],
  ([canSelect, allowedPartitions, loaded]) => {
    const selectedPartition = runtimeStore.dashboard.partition
    if (!selectedPartition) return
    if (!canSelect) {
      runtimeStore.dashboard.partition = ''
      return
    }
    if (!loaded) return
    if (!allowedPartitions.has(selectedPartition)) {
      runtimeStore.dashboard.partition = ''
    }
  },
  { immediate: true }
)

const statsCards = computed(() => {
  if (!data.value) return []
  return [
    { id: 'nodes', label: t('pages.dashboard.stats.nodes'), value: String(data.value.resources.nodes) },
    { id: 'cores', label: t('pages.dashboard.stats.cores'), value: String(data.value.resources.cores) },
    {
      id: 'memory-total',
      label: t('pages.dashboard.stats.totalMemory'),
      value: getMBHumanUnit(data.value.resources.memory),
      subtle: t('pages.dashboard.stats.clusterCapacity')
    },
    {
      id: 'memory-allocated',
      label: t('pages.dashboard.stats.allocatedMemory'),
      value: getMBHumanUnit(data.value.resources.memory_allocated),
      subtle: t('pages.dashboard.stats.requestedByJobs')
    },
    {
      id: 'memory-available',
      label: t('pages.dashboard.stats.availableMemory'),
      value: getMBHumanUnit(data.value.resources.memory_available),
      subtle: t('pages.dashboard.stats.totalMinusAllocated')
    },
    {
      id: 'gpus',
      label: t('common.labels.gpu'),
      value: String(data.value.resources.gpus),
      muted: data.value.resources.gpus === 0
    },
    {
      id: 'jobs-running',
      label: t('pages.dashboard.stats.runningJobs'),
      value: String(data.value.jobs.running)
    },
    { id: 'jobs-total', label: t('pages.dashboard.stats.totalJobs'), value: String(data.value.jobs.total) }
  ]
})

watch(
  () => runtimeStore.dashboard.partition,
  (partition) => {
    if (partition && (!canSelectPartition.value || !allowedPartitionNames.value.has(partition))) {
      runtimeStore.dashboard.partition = ''
      return
    }
    setParam(partition ? { partition } : undefined)
    syncQuery()
  }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="dashboard"
    :cluster="cluster"
    :breadcrumb="[{ title: t('shell.mainMenu.dashboard') }]"
  >
    <div class="ui-page ui-page-wide ui-content-workspace">
      <PageHeader
        title="pages.dashboard.title"
        description="pages.dashboard.description"
      >
        <template #actions>
          <div data-testid="dashboard-header-tools" class="dashboard-header-tools">
            <div class="dashboard-header-summary dashboard-surface">
              <span class="dashboard-header-summary-label">{{ t('pages.dashboard.stats.totalJobs') }}</span>
              <span class="dashboard-header-summary-value">
                {{ loaded && data ? data.jobs.total : '--' }}
              </span>
            </div>
            <RouterLink :to="{ name: 'analysis', params: { cluster } }" class="ui-button-primary">
              {{ t('pages.dashboard.openAnalysis') }}
            </RouterLink>
          </div>
        </template>
      </PageHeader>

      <ErrorAlert v-if="unable">
        {{ t('pages.dashboard.errors.unableToRetrieve', { cluster }) }}
      </ErrorAlert>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack pb-2">
          <div class="dashboard-surface mt-6 px-4 py-4 sm:px-5">
            <div class="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
              <div class="min-w-0">
                <p class="dashboard-toolbar-kicker">{{ t('pages.dashboard.toolbar.kicker') }}</p>
                <h2 class="ui-panel-title">{{ t('pages.dashboard.toolbar.title') }}</h2>
                <p class="ui-panel-description">
                  {{ t('pages.dashboard.toolbar.description') }}
                </p>
              </div>
              <div data-testid="dashboard-toolbar" class="dashboard-toolbar-fields">
                <label
                  v-if="canSelectPartition"
                  class="dashboard-toolbar-field"
                >
                  <span class="dashboard-toolbar-label">{{ t('pages.dashboard.toolbar.partitionQueue') }}</span>
                  <select
                    id="dashboard-partition"
                    v-model="runtimeStore.dashboard.partition"
                    class="dashboard-toolbar-select"
                  >
                    <option
                      v-for="option in partitionOptions"
                      :key="option.value || '__all__'"
                      :value="option.value"
                    >
                      {{ option.label }}
                    </option>
                  </select>
                </label>

                <div class="dashboard-toolbar-field">
                  <span class="dashboard-toolbar-label">{{ t('common.labels.timeRange') }}</span>
                  <MetricRangeSelector
                    :model-value="runtimeStore.dashboard.range"
                    :aria-label="t('pages.dashboard.toolbar.selectMetricsRange')"
                    enable-custom-window
                    :start-value="runtimeStore.dashboard.start"
                    :end-value="runtimeStore.dashboard.end"
                    custom-button-label="common.labels.timeRange"
                    reset-label="common.metricRanges.lastHour"
                    @update:model-value="setRange"
                    @apply-window="applyMetricsWindow"
                    @reset-window="resetMetricsWindow"
                  />
                </div>
              </div>
            </div>
          </div>

          <div v-if="!unable" class="ui-stat-grid mt-4">
            <div v-for="card in statsCards" :key="card.id" class="ui-stat-card dashboard-surface">
              <p class="ui-stat-label">{{ card.label }}</p>
              <span
                :id="`metric-${card.id}`"
                :class="[
                  card.muted ? 'ui-stat-value text-[var(--color-brand-muted)]/35' : 'ui-stat-value'
                ]"
              >
                {{ card.value }}
              </span>
              <p v-if="card.subtle" class="ui-stat-subtle">{{ card.subtle }}</p>
            </div>
          </div>

          <DashboardCharts v-if="runtimeStore.getCluster(cluster)?.metrics" :cluster="cluster" />
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>

<style scoped>
.dashboard-surface {
  border-radius: calc(var(--radius-panel) - 6px);
  border: 1px solid rgba(255, 255, 255, 0.72);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.95), rgba(239, 244, 246, 0.88)),
    linear-gradient(135deg, rgba(182, 232, 44, 0.07), transparent);
  box-shadow: var(--shadow-soft);
}

.dashboard-header-tools {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: 0.75rem;
}

.dashboard-header-summary {
  display: inline-flex;
  align-items: center;
  gap: 0.85rem;
  padding: 0.7rem 0.95rem;
}

.dashboard-header-summary-label {
  color: var(--color-brand-muted);
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

.dashboard-header-summary-value {
  color: var(--color-brand-ink-strong);
  font-size: clamp(1.4rem, 1.6vw, 2rem);
  font-weight: 700;
  line-height: 1;
}

.dashboard-toolbar-kicker {
  margin-bottom: 0.35rem;
  color: var(--color-brand-muted);
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.dashboard-toolbar-fields {
  display: grid;
  gap: 0.85rem;
  width: 100%;
}

.dashboard-toolbar-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  min-height: 3rem;
  border-radius: 999px;
  border: 1px solid rgba(80, 105, 127, 0.12);
  background: rgba(255, 255, 255, 0.82);
  padding: 0.45rem 0.55rem 0.45rem 0.95rem;
}

.dashboard-toolbar-label {
  color: var(--color-brand-muted);
  font-size: 0.82rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.dashboard-toolbar-select {
  min-width: 14rem;
  border-radius: 999px;
  border: 1px solid rgba(80, 105, 127, 0.18);
  background: white;
  padding: 0.62rem 1rem;
  color: var(--color-brand-ink-strong);
  font-size: 0.92rem;
  box-shadow: var(--shadow-soft);
  outline: none;
  transition: border-color 160ms ease;
}

.dashboard-toolbar-select:focus {
  border-color: var(--color-brand-accent);
}

@media (min-width: 1024px) {
  .dashboard-toolbar-fields {
    width: auto;
    grid-template-columns: repeat(2, minmax(0, auto));
  }
}

@media (max-width: 767px) {
  .dashboard-toolbar-field {
    align-items: flex-start;
    border-radius: 1.4rem;
    flex-direction: column;
    padding: 0.85rem 0.95rem;
  }

  .dashboard-toolbar-select {
    min-width: 100%;
    width: 100%;
  }
}
</style>

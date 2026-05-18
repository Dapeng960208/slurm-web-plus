<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import DashboardCharts from '@/components/dashboard/DashboardCharts.vue'
import QueueWaitHistoryChart from '@/components/analysis/QueueWaitHistoryChart.vue'
import { useClusterDataGetter } from '@/composables/DataGetter'
import {
  getMBHumanUnit,
  getNodeGPU,
  useGatewayAPI
} from '@/composables/GatewayAPI'
import type {
  ClusterNode,
  ClusterPartition,
  DateTimeWindowQuery,
  JobHistoryRecord
} from '@/composables/GatewayAPI'
import {
  buildQueueWaitSeries,
  inferQueueWaitAggregation
} from '@/composables/queueWaitHistory'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster, partition } = defineProps<{
  cluster: string
  partition: string
}>()

const { t } = useI18n()
const gateway = useGatewayAPI()
const runtimeStore = useRuntimeStore()
const HISTORY_PAGE_SIZE = 500
const { data: partitions } = useClusterDataGetter<ClusterPartition[]>(cluster, 'partitions')
const { data: nodes } = useClusterDataGetter<ClusterNode[]>(cluster, 'nodes')
const historyJobs = ref<JobHistoryRecord[]>([])
const queueWaitLoading = ref(false)
const queueWaitUnavailable = ref(false)
const queueWaitChartWindow = ref<DateTimeWindowQuery | null>(null)
let queueWaitRequestId = 0

const clusterDetails = computed(() => runtimeStore.getCluster(cluster))
const canViewHistory = computed(
  () =>
    Boolean(clusterDetails.value?.persistence) &&
    runtimeStore.hasRoutePermission(cluster, 'jobs-history', 'view')
)

const partitionRecord = computed(() =>
  (partitions.value ?? []).find((item) => item.name === partition)
)

const partitionNodes = computed(() =>
  (nodes.value ?? []).filter((node) => node.partitions.includes(partition))
)

const totalCpu = computed(() =>
  partitionNodes.value.reduce((sum, node) => sum + node.cpus, 0)
)

const allocatedCpu = computed(() =>
  partitionNodes.value.reduce((sum, node) => sum + node.alloc_cpus, 0)
)

const totalMemory = computed(() =>
  partitionNodes.value.reduce((sum, node) => sum + node.real_memory, 0)
)

const totalGpu = computed(() =>
  partitionNodes.value.reduce(
    (sum, node) =>
      sum + getNodeGPU(node.gres).reduce((gpuTotal, item) => gpuTotal + Number(item.split(' x ')[0] ?? 0), 0),
    0
  )
)

const allocatedNodeCount = computed(() =>
  partitionNodes.value.filter((node) => node.alloc_cpus > 0).length
)

const idleNodeCount = computed(() =>
  partitionNodes.value.filter((node) => node.state.includes('IDLE')).length
)

const partitionMetricsQuery = computed(() => {
  if (runtimeStore.dashboard.start && runtimeStore.dashboard.end) {
    return {
      start: runtimeStore.dashboard.start,
      end: runtimeStore.dashboard.end,
      partition
    }
  }
  return {
    range: runtimeStore.dashboard.range,
    partition
  }
})

const queueWaitAggregation = computed(() =>
  inferQueueWaitAggregation({
    range: runtimeStore.dashboard.range,
    start: runtimeStore.dashboard.start,
    end: runtimeStore.dashboard.end
  })
)
const queueWaitSeries = computed(() =>
  buildQueueWaitSeries(historyJobs.value, queueWaitAggregation.value)
)
const queueWaitChartWindowStart = computed(() => queueWaitChartWindow.value?.start)
const queueWaitChartWindowEnd = computed(() => queueWaitChartWindow.value?.end)

function setRange(range: 'hour' | 'day' | 'week') {
  runtimeStore.dashboard.range = range
  runtimeStore.dashboard.clearWindow()
}

function applyMetricsWindow(window: { start: string; end: string }) {
  runtimeStore.dashboard.setWindow(window)
}

function resetMetricsWindow() {
  runtimeStore.dashboard.clearWindow()
  runtimeStore.dashboard.range = 'hour'
}

function rangeStartISO(range: 'hour' | 'day' | 'week'): string {
  const now = Date.now()
  const duration = {
    hour: 60 * 60 * 1000,
    day: 24 * 60 * 60 * 1000,
    week: 7 * 24 * 60 * 60 * 1000
  }[range]
  return new Date(now - duration).toISOString()
}

function resolvedQueueWaitWindow(): DateTimeWindowQuery {
  if (runtimeStore.dashboard.start && runtimeStore.dashboard.end) {
    return {
      start: new Date(runtimeStore.dashboard.start).toISOString(),
      end: new Date(runtimeStore.dashboard.end).toISOString()
    }
  }
  return {
    start: rangeStartISO(runtimeStore.dashboard.range),
    end: new Date().toISOString()
  }
}

async function loadQueueWaitHistory() {
  const requestId = ++queueWaitRequestId
  if (!partitionRecord.value || !canViewHistory.value) {
    historyJobs.value = []
    queueWaitChartWindow.value = null
    queueWaitLoading.value = false
    queueWaitUnavailable.value = false
    return
  }

  queueWaitLoading.value = true
  queueWaitUnavailable.value = false
  const window = resolvedQueueWaitWindow()
  queueWaitChartWindow.value = window

  try {
    const firstPage = await gateway.jobs_history(cluster, {
      partition,
      state: 'COMPLETED',
      sort: 'submit_time',
      order: 'desc',
      page: 1,
      page_size: HISTORY_PAGE_SIZE,
      start: window.start,
      end: window.end
    })

    const jobs = [...firstPage.jobs]
    const totalPages = Math.max(Math.ceil(firstPage.total / firstPage.page_size), 1)

    for (let page = 2; page <= totalPages; page += 1) {
      const nextPage = await gateway.jobs_history(cluster, {
        partition,
        state: 'COMPLETED',
        sort: 'submit_time',
        order: 'desc',
        page,
        page_size: HISTORY_PAGE_SIZE,
        start: window.start,
        end: window.end
      })
      jobs.push(...nextPage.jobs)
    }

    if (requestId !== queueWaitRequestId) return
    historyJobs.value = jobs
  } catch {
    if (requestId !== queueWaitRequestId) return
    historyJobs.value = []
    queueWaitUnavailable.value = true
  } finally {
    if (requestId === queueWaitRequestId) {
      queueWaitLoading.value = false
    }
  }
}

watch(
  () =>
    `${cluster}/${partition}/${partitionRecord.value?.name ?? ''}/${canViewHistory.value}/${
      runtimeStore.dashboard.range
    }/${runtimeStore.dashboard.start}/${runtimeStore.dashboard.end}`,
  () => {
    void loadQueueWaitHistory()
  },
  { immediate: true }
)
</script>

<template>
  <ClusterMainLayout
    menu-entry="resources"
    :cluster="cluster"
    :breadcrumb="[
      { title: 'shell.mainMenu.resources', routeName: 'resources' },
      { title: t('common.labels.partitions') },
      { title: partition }
    ]"
  >
    <div class="ui-page ui-page-readable ui-content-workspace">
      <PageHeader
        kicker="common.labels.partitions"
        :title="partition"
        description="pages.partition.description"
        :metric-value="partitionNodes.length"
        metric-label="pages.resources.metricLabelPlural"
      >
        <template #actions>
          <RouterLink :to="{ name: 'resources', params: { cluster } }" class="ui-button-secondary">
            {{ t('common.navigation.back') }}
          </RouterLink>
        </template>
      </PageHeader>

      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <div class="ui-section-stack partition-page-stack pb-2">
          <InfoAlert v-if="!partitionRecord">
            {{ t('pages.partition.notFound', { partition }) }}
          </InfoAlert>

          <template v-else>
            <div class="ui-summary-strip">
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.nodes') }}</div>
                <div class="ui-summary-value">{{ partitionNodes.length }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.totalCpu') }}</div>
                <div class="ui-summary-value">{{ totalCpu }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.allocatedCpu') }}</div>
                <div class="ui-summary-value">{{ allocatedCpu }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.totalMemory') }}</div>
                <div class="ui-summary-value">{{ getMBHumanUnit(totalMemory) }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.gpu') }}</div>
                <div class="ui-summary-value">{{ totalGpu }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.allocatedNodes') }}</div>
                <div class="ui-summary-value">{{ allocatedNodeCount }}</div>
              </div>
              <div class="ui-summary-item">
                <div class="ui-summary-label">{{ t('pages.partition.summary.idleNodes') }}</div>
                <div class="ui-summary-value">{{ idleNodeCount }}</div>
              </div>
            </div>

            <section class="ui-panel ui-section partition-metrics-panel" data-testid="partition-dashboard-charts">
              <div class="partition-metrics-toolbar">
                <MetricRangeSelector
                  class="partition-metrics-range"
                  :model-value="runtimeStore.dashboard.range"
                  :aria-label="t('pages.partition.metrics.selectRange')"
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
              <DashboardCharts
                class="partition-dashboard-charts"
                :cluster="cluster"
                :metrics-query="partitionMetricsQuery"
                route-target-name="partition"
                compact
              />
              <div class="ui-metric-surface partition-queue-wait-panel" data-testid="partition-queue-wait-panel">
                <div>
                  <div class="ui-stat-label">{{ t('pages.partition.queueWait.title') }}</div>
                  <div class="mt-1 text-sm text-[var(--color-brand-muted)]">
                    {{ t('pages.partition.queueWait.description') }}
                  </div>
                </div>
                <div v-if="queueWaitSeries.length" class="partition-queue-wait-chart">
                  <QueueWaitHistoryChart
                    :series="queueWaitSeries"
                    :aggregation="queueWaitAggregation"
                    :window-start="queueWaitChartWindowStart"
                    :window-end="queueWaitChartWindowEnd"
                  />
                </div>
                <div v-else class="text-sm text-[var(--color-brand-muted)]">
                  <template v-if="queueWaitLoading">
                    {{ t('pages.partition.queueWait.loading') }}
                  </template>
                  <template v-else-if="!canViewHistory">
                    {{ t('pages.partition.queueWait.disabled') }}
                  </template>
                  <template v-else-if="queueWaitUnavailable">
                    {{ t('pages.partition.queueWait.unavailable') }}
                  </template>
                  <template v-else>
                    {{ t('pages.partition.queueWait.empty') }}
                  </template>
                </div>
              </div>
            </section>
          </template>
        </div>
      </div>
    </div>
  </ClusterMainLayout>
</template>

<style scoped>
.partition-page-stack {
  gap: 1rem;
}

.partition-metrics-panel {
  display: flex;
  min-height: 0;
  flex-direction: column;
  gap: 0.85rem;
}

.partition-metrics-toolbar {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.85rem;
}

.partition-metrics-range {
  flex: 0 0 auto;
}

.partition-dashboard-charts {
  display: grid;
  gap: 0.85rem;
}

.partition-queue-wait-panel {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  padding: 1rem;
}

.partition-queue-wait-chart {
  min-height: 0;
}

:deep(.partition-chart-shell) {
  height: 13.25rem;
}

@media (max-width: 1279px) {
  :deep(.partition-chart-shell) {
    height: 12.5rem;
  }
}

@media (max-width: 767px) {
  .partition-metrics-range {
    width: 100%;
  }

  :deep(.partition-chart-shell) {
    height: 11.75rem;
  }
}
</style>

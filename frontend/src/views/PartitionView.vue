<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import PageHeader from '@/components/PageHeader.vue'
import InfoAlert from '@/components/InfoAlert.vue'
import MetricRangeSelector from '@/components/MetricRangeSelector.vue'
import DashboardCharts from '@/components/dashboard/DashboardCharts.vue'
import { useClusterDataGetter } from '@/composables/DataGetter'
import { getMBHumanUnit, getNodeGPU } from '@/composables/GatewayAPI'
import type { ClusterNode, ClusterPartition } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster, partition } = defineProps<{
  cluster: string
  partition: string
}>()

const { t } = useI18n()
const runtimeStore = useRuntimeStore()
const { data: partitions } = useClusterDataGetter<ClusterPartition[]>(cluster, 'partitions')
const { data: nodes } = useClusterDataGetter<ClusterNode[]>(cluster, 'nodes')

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

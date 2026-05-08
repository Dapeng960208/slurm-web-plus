<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { useClusterDataGetter } from '@/composables/DataGetter'
import { getMBHumanUnit } from '@/composables/GatewayAPI'
import type { ClusterStats } from '@/composables/GatewayAPI'
import type { ClusterPartition } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import { useClusterDataPoller } from '@/composables/DataPoller'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import DashboardCharts from '@/components/dashboard/DashboardCharts.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'

const runtimeStore = useRuntimeStore()
const route = useRoute()
const router = useRouter()

const props = defineProps<{ cluster: string }>()
const cluster = computed(() => props.cluster)

const { data, unable, loaded, setCluster, setParam } = useClusterDataPoller<ClusterStats>(
  cluster.value,
  'stats',
  10000,
  runtimeStore.dashboard.partition ? { partition: runtimeStore.dashboard.partition } : undefined
)
const canSelectPartition = computed(() =>
  runtimeStore.hasClusterPermission(cluster.value, 'view-partitions')
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
  { label: 'Entire cluster', value: '' },
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
    { id: 'nodes', label: 'Nodes', value: String(data.value.resources.nodes) },
    { id: 'cores', label: 'Cores', value: String(data.value.resources.cores) },
    {
      id: 'memory-total',
      label: 'Total Memory',
      value: getMBHumanUnit(data.value.resources.memory),
      subtle: 'Cluster capacity'
    },
    {
      id: 'memory-allocated',
      label: 'Allocated Memory',
      value: getMBHumanUnit(data.value.resources.memory_allocated),
      subtle: 'Requested by jobs'
    },
    {
      id: 'memory-available',
      label: 'Available Memory',
      value: getMBHumanUnit(data.value.resources.memory_available),
      subtle: 'Total minus allocated'
    },
    {
      id: 'gpus',
      label: 'GPU',
      value: String(data.value.resources.gpus),
      muted: data.value.resources.gpus === 0
    },
    { id: 'jobs-running', label: 'Running Jobs', value: String(data.value.jobs.running) },
    { id: 'jobs-total', label: 'Total Jobs', value: String(data.value.jobs.total) }
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
    :breadcrumb="[{ title: 'Dashboard' }]"
  >
    <div class="ui-page ui-page-wide">
      <PageHeader
        title="Dashboard"
        description="Live cluster statistics, workload activity and metric trends in a unified control view."
        :metric-value="loaded && data ? data.jobs.total : undefined"
        metric-label="total jobs"
      >
        <template #actions>
          <RouterLink :to="{ name: 'analysis', params: { cluster } }" class="ui-button-primary">
            Open analysis
          </RouterLink>
        </template>
      </PageHeader>

      <ErrorAlert v-if="unable"
        >Unable to retrieve statistics from cluster
        <span class="font-medium">{{ cluster }}</span></ErrorAlert
      >

      <div v-if="canSelectPartition" class="ui-panel ui-section mt-6">
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div>
            <h2 class="ui-panel-title">Cluster Scope</h2>
            <p class="ui-panel-description">Filter dashboard stats and charts by partition/queue.</p>
          </div>
          <label class="flex min-w-[15rem] flex-col gap-2 text-sm font-medium text-[var(--color-brand-ink-strong)]">
            <span>Partition / Queue</span>
            <select
              id="dashboard-partition"
              v-model="runtimeStore.dashboard.partition"
              class="rounded-full border border-[rgba(80,105,127,0.18)] bg-white px-4 py-2.5 text-sm text-[var(--color-brand-ink-strong)] shadow-[var(--shadow-soft)] outline-none transition focus:border-[var(--color-brand-accent)]"
            >
              <option v-for="option in partitionOptions" :key="option.value || '__all__'" :value="option.value">
                {{ option.label }}
              </option>
            </select>
          </label>
        </div>
      </div>

      <div v-if="!unable" class="ui-stat-grid">
        <div v-for="card in statsCards" :key="card.id" class="ui-stat-card">
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
  </ClusterMainLayout>
</template>

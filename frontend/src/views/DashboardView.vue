<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { getMBHumanUnit } from '@/composables/GatewayAPI'
import type { ClusterStats } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import { useClusterDataPoller } from '@/composables/DataPoller'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'
import DashboardCharts from '@/components/dashboard/DashboardCharts.vue'
import ErrorAlert from '@/components/ErrorAlert.vue'
import PageHeader from '@/components/PageHeader.vue'

const runtimeStore = useRuntimeStore()

const { cluster } = defineProps<{ cluster: string }>()

const { data, unable, loaded, setCluster } = useClusterDataPoller<ClusterStats>(
  cluster,
  'stats',
  10000
)

watch(
  () => cluster,
  (newCluster) => {
    setCluster(newCluster)
  }
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

      <div v-else class="ui-stat-grid">
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

      <DashboardCharts v-if="runtimeStore.getCluster(cluster).metrics" :cluster="cluster" />
    </div>
  </ClusterMainLayout>
</template>

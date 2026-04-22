<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { watch } from 'vue'
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
      />

      <ErrorAlert v-if="unable"
        >Unable to retrieve statistics from cluster
        <span class="font-medium">{{ cluster }}</span></ErrorAlert
      >

      <div v-else class="ui-stat-grid">
        <div class="ui-stat-card">
          <p class="ui-stat-label">Nodes</p>
          <span v-if="loaded && data" id="metric-nodes" class="ui-stat-value">
            {{ data.resources.nodes }}
          </span>
          <div v-else class="flex animate-pulse space-x-4">
            <div class="h-10 w-10 rounded-full bg-slate-200"></div>
          </div>
        </div>
        <div class="ui-stat-card">
          <p class="ui-stat-label">Cores</p>
          <span v-if="loaded && data" id="metric-cores" class="ui-stat-value">
            {{ data.resources.cores }}
          </span>
          <div v-else class="flex animate-pulse space-x-4">
            <div class="h-10 w-10 rounded-full bg-slate-200"></div>
          </div>
        </div>
        <div class="ui-stat-card">
          <p class="ui-stat-label">Memory</p>
          <span v-if="loaded && data" id="metric-memory" class="ui-stat-value">
            {{ getMBHumanUnit(data.resources.memory) }}
          </span>
          <div v-else class="flex animate-pulse space-x-4">
            <div class="h-10 w-10 rounded-full bg-slate-200"></div>
          </div>
        </div>
        <div class="ui-stat-card">
          <p class="ui-stat-label">GPU</p>
          <span
            v-if="loaded && data"
            id="metric-gpus"
            :class="[
              data.resources.gpus ? 'ui-stat-value' : 'ui-stat-value text-[var(--color-brand-muted)]/35'
            ]"
          >
            {{ data.resources.gpus }}
          </span>
          <div v-else class="flex animate-pulse space-x-4">
            <div class="h-10 w-10 rounded-full bg-slate-200"></div>
          </div>
        </div>
        <div class="ui-stat-card">
          <p class="ui-stat-label">Running jobs</p>
          <span v-if="loaded && data" id="metric-jobs-running" class="ui-stat-value">
            {{ data.jobs.running }}
          </span>
          <div v-else class="flex animate-pulse space-x-4">
            <div class="h-10 w-10 rounded-full bg-slate-200"></div>
          </div>
        </div>
        <div class="ui-stat-card">
          <p class="ui-stat-label">Total jobs</p>
          <span v-if="loaded && data" id="metric-jobs-total" class="ui-stat-value">
            {{ data.jobs.total }}
          </span>
          <div v-else class="flex animate-pulse space-x-4">
            <div class="h-10 w-10 rounded-full bg-slate-200"></div>
          </div>
        </div>
      </div>

      <DashboardCharts v-if="runtimeStore.getCluster(cluster).metrics" :cluster="cluster" />
    </div>
  </ClusterMainLayout>
</template>

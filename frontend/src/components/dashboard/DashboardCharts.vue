<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import type { DashboardMetricsQuery } from '@/composables/GatewayAPI'
import { useRuntimeStore } from '@/stores/runtime'
import ChartResourcesHistogram from '@/components/dashboard/ChartResourcesHistogram.vue'
import ChartJobsHistogram from '@/components/dashboard/ChartJobsHistogram.vue'

const props = defineProps<{
  cluster: string
  metricsQuery?: DashboardMetricsQuery
  routeTargetName?: string
}>()

const runtimeStore = useRuntimeStore()
const canViewResources = computed(() => runtimeStore.hasRoutePermission(props.cluster, 'resources', 'view'))
const canViewJobs = computed(() => runtimeStore.hasRoutePermission(props.cluster, 'jobs', 'view'))
</script>

<template>
  <ChartResourcesHistogram
    v-if="canViewResources"
    :cluster="props.cluster"
    :metrics-query="props.metricsQuery"
    :route-target-name="props.routeTargetName"
  />
  <ChartJobsHistogram
    v-if="canViewJobs"
    :cluster="props.cluster"
    :metrics-query="props.metricsQuery"
  />
</template>

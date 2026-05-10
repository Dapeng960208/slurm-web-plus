<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { useRuntimeStore } from '@/stores/runtime'
import ChartResourcesHistogram from '@/components/dashboard/ChartResourcesHistogram.vue'
import ChartJobsHistogram from '@/components/dashboard/ChartJobsHistogram.vue'

const { cluster } = defineProps<{ cluster: string }>()

const runtimeStore = useRuntimeStore()
const canViewResources = computed(() => runtimeStore.hasRoutePermission(cluster, 'resources', 'view'))
const canViewJobs = computed(() => runtimeStore.hasRoutePermission(cluster, 'jobs', 'view'))
</script>

<template>
  <ChartResourcesHistogram v-if="canViewResources" :cluster="cluster" />
  <ChartJobsHistogram v-if="canViewJobs" :cluster="cluster" />
</template>

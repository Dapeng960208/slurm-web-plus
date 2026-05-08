<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useRuntimeStore } from '@/stores/runtime'
import ChartResourcesHistogram from '@/components/dashboard/ChartResourcesHistogram.vue'
import ChartJobsHistogram from '@/components/dashboard/ChartJobsHistogram.vue'

const { cluster } = defineProps<{ cluster: string }>()

const runtimeStore = useRuntimeStore()
</script>

<template>
  <ChartResourcesHistogram v-if="runtimeStore.hasPermission('view-nodes')" :cluster="cluster" />
  <ChartJobsHistogram v-if="runtimeStore.hasPermission('view-jobs')" :cluster="cluster" />
</template>

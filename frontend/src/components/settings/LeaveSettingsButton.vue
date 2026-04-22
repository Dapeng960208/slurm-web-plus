<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'

const runtimeStore = useRuntimeStore()
const router = useRouter()

function leaveSettings() {
  if (runtimeStore.beforeSettingsRoute) {
    const from = runtimeStore.beforeSettingsRoute
    runtimeStore.beforeSettingsRoute = undefined
    router.push(from)
  } else if (runtimeStore.currentCluster) {
    router.push({ name: 'dashboard', params: { cluster: runtimeStore.currentCluster.name } })
  } else {
    router.push({ name: 'clusters' })
  }
}
</script>

<template>
  <button @click="leaveSettings()" type="button" class="ui-button-secondary self-start">
    <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
    Back to dashboards
  </button>
</template>

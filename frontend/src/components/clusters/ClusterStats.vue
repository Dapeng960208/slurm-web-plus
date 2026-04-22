<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useGatewayAPI } from '@/composables/GatewayAPI'
import { AuthenticationError } from '@/composables/HTTPErrors'
import { useErrorsHandler } from '@/composables/ErrorsHandler'
import { ServerIcon, PlayCircleIcon } from '@heroicons/vue/24/outline'
import { useRuntimeStore } from '@/stores/runtime'
import LoadingSpinner from '@/components/LoadingSpinner.vue'
const { clusterName } = defineProps<{ clusterName: string }>()

const runtimeStore = useRuntimeStore()
const cluster = runtimeStore.getCluster(clusterName)
const loading = ref<boolean>(true)
const { reportAuthenticationError, reportServerError } = useErrorsHandler()

const gateway = useGatewayAPI()

async function getClusterStats() {
  try {
    cluster.stats = await gateway.stats(clusterName)
  } catch (err) {
    if (err instanceof AuthenticationError) {
      reportAuthenticationError(err)
    } else if (err instanceof Error) {
      reportServerError(err)
    }
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  getClusterStats()
})
</script>

<template>
  <LoadingSpinner v-if="loading" class="animate-pulse text-[var(--color-brand-muted)]" :size="5" />
  <span v-else-if="cluster.stats" class="hidden gap-2 text-center md:flex">
    <span class="ui-panel-soft mt-1 w-24 rounded-[16px] px-2 py-2 text-xs leading-5 text-[var(--color-brand-muted)]">
      <ServerIcon class="h-6 w-full" />
      <p class="w-full">
        {{ cluster.stats.resources.nodes }} node{{ cluster.stats.resources.nodes > 1 ? 's' : '' }}
      </p>
    </span>
    <span class="ui-panel-soft mt-1 w-24 rounded-[16px] px-2 py-2 text-xs leading-5 text-[var(--color-brand-muted)]">
      <PlayCircleIcon class="h-6 w-full" />
      <p class="w-full">
        {{ cluster.stats.jobs.running }} job{{ cluster.stats.jobs.running > 1 ? 's' : '' }}
      </p>
    </span>
  </span>
</template>

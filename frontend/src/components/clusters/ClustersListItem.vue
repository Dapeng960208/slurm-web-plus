<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink, useRouter } from 'vue-router'
import { useRuntimeStore } from '@/stores/runtime'
import { useGatewayAPI, type ClusterDescription } from '@/composables/GatewayAPI'
import { AuthenticationError } from '@/composables/HTTPErrors'
import { useErrorsHandler } from '@/composables/ErrorsHandler'
import { ChevronRightIcon } from '@heroicons/vue/20/solid'
import { TagIcon } from '@heroicons/vue/20/solid'
import ClusterStats from '@/components/clusters/ClusterStats.vue'

const { clusterName } = defineProps<{ clusterName: string }>()

const runtimeStore = useRuntimeStore()
const cluster = runtimeStore.getCluster(clusterName)
const loading = ref<boolean>(true)
const { reportAuthenticationError, reportServerError } = useErrorsHandler()

const gateway = useGatewayAPI()
const router = useRouter()
const emit = defineEmits<{
  pinged: [cluster: ClusterDescription]
}>()

async function getClustersPing() {
  if (cluster.permissions.actions.length == 0) {
    loading.value = false
    emit('pinged', cluster)
    return
  }
  try {
    const response = await gateway.ping(cluster.name)
    cluster.versions = response.versions
  } catch (error) {
    if (error instanceof AuthenticationError) {
      reportAuthenticationError(error)
    } else if (error instanceof Error) {
      reportServerError(error)
      cluster.error = true
    }
  } finally {
    loading.value = false
    emit('pinged', cluster)
  }
}

onMounted(() => {
  getClustersPing()
})
</script>
<template>
  <li
    :class="[
      cluster.permissions.actions.length > 0
        ? 'cursor-pointer hover:bg-[rgba(182,232,44,0.12)]'
        : 'cursor-not-allowed bg-[rgba(239,244,246,0.8)]',
      'relative flex min-h-24 items-center justify-between px-5 py-5 sm:px-6'
    ]"
    @click="
      cluster.permissions.actions.length > 0 &&
        router.push({ name: 'dashboard', params: { cluster: cluster.name } })
    "
  >
    <span class="w-64 text-sm leading-6 font-semibold text-[var(--color-brand-ink-strong)]">
      <RouterLink :to="{ name: 'dashboard', params: { cluster: cluster.name } }">
        <span class="inset-x-0 -top-px bottom-0" />
        {{ cluster.name }}
      </RouterLink>
      <span
        v-if="cluster.versions"
        class="ui-chip ml-2 hidden md:inline-flex"
      >
        <TagIcon class="h-3" />
        Slurm {{ cluster.versions.slurm }}
      </span>
    </span>
    <ClusterStats
      v-if="
        runtimeStore.hasClusterPermission(cluster.name, 'view-stats') && !loading && !cluster.error
      "
      :cluster-name="cluster.name"
    />
    <div class="mr-0 w-64 shrink-0 items-end gap-x-4">
      <div class="hidden sm:flex sm:flex-col sm:items-end">
        <div v-if="loading" class="mt-1 flex items-center gap-x-1.5">
          <div class="flex-none rounded-full bg-[rgba(80,105,127,0.16)] p-1.5">
            <div class="h-1.5 w-1.5 rounded-full bg-[var(--color-brand-muted)]" />
          </div>
          <p class="text-xs leading-5 text-[var(--color-brand-muted)]">Loading</p>
          <ChevronRightIcon class="h-5 w-5 flex-none text-[var(--color-brand-muted)]" aria-hidden="true" />
        </div>
        <div
          v-else-if="cluster.permissions.actions.length == 0"
          class="mt-1 flex items-center gap-x-1.5"
        >
          <div class="flex-none rounded-full bg-[rgba(216,75,80,0.16)] p-1.5">
            <div class="h-1.5 w-1.5 rounded-full bg-[var(--color-brand-danger)]" />
          </div>
          <p class="text-xs leading-5 text-[var(--color-brand-muted)]">Denied</p>
        </div>
        <div v-else-if="cluster.error" class="mt-1 flex items-center gap-x-1.5">
          <div class="flex-none rounded-full bg-[rgba(239,155,40,0.18)] p-1.5">
            <div class="h-1.5 w-1.5 rounded-full bg-[var(--color-brand-warning)]" />
          </div>
          <p class="text-xs leading-5 text-[var(--color-brand-muted)]">Ongoing issue</p>
          <ChevronRightIcon class="h-5 w-5 flex-none text-[var(--color-brand-muted)]" aria-hidden="true" />
        </div>
        <div v-else class="mt-1 flex items-center gap-x-1.5">
          <div class="flex-none rounded-full bg-[rgba(123,191,31,0.16)] p-1.5">
            <div class="h-1.5 w-1.5 rounded-full bg-[var(--color-brand-success)]" />
          </div>
          <p class="text-xs leading-5 text-[var(--color-brand-muted)]">Available</p>
          <ChevronRightIcon class="h-5 w-5 flex-none text-[var(--color-brand-muted)]" aria-hidden="true" />
        </div>
      </div>
    </div>
  </li>
</template>

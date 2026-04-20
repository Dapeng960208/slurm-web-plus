<!--
  Copyright (c) 2025 Rackslab

  This file is part of Slurm-web.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import type { LocationQueryRaw } from 'vue-router'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'
import { useRuntimeStore } from '@/stores/runtime'

const { cluster, routeName = 'jobs' } = defineProps<{
  cluster: string
  routeName?: 'jobs' | 'jobs-history'
}>()

const router = useRouter()
const route = useRoute()
const runtimeStore = useRuntimeStore()

const buttonText = computed(() => {
  const returnTo = route.query.returnTo as string
  const nodeName = route.query.nodeName as string
  if (returnTo === 'node' && nodeName) return 'Back to node'
  return routeName === 'jobs-history' ? 'Back to jobs history' : 'Back to jobs'
})

/* Handle back button click. If returnTo query parameter is set to 'node',
 * navigate to node view. Otherwise, navigate to jobs view. */
function handleBackClick() {
  const returnTo = route.query.returnTo as string
  const nodeName = route.query.nodeName as string

  if (returnTo === 'node' && nodeName) {
    router.push({
      name: 'node',
      params: { cluster: cluster, nodeName: nodeName }
    })
  } else if (routeName === 'jobs-history') {
    router.push({
      name: 'jobs-history',
      params: { cluster: cluster }
    })
  } else {
    router.push({
      name: 'jobs',
      params: { cluster: runtimeStore.currentCluster?.name ?? cluster },
      query: runtimeStore.jobs.query() as LocationQueryRaw
    })
  }
}
</script>

<template>
  <button
    @click="handleBackClick"
    type="button"
    class="bg-slurmweb dark:bg-slurmweb-verydark hover:bg-slurmweb-dark focus-visible:outline-slurmweb-dark mt-8 mb-16 inline-flex items-center gap-x-2 rounded-md px-3.5 py-2.5 text-sm font-semibold text-white shadow-xs focus-visible:outline-2 focus-visible:outline-offset-2"
  >
    <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
    {{ buttonText }}
  </button>
</template>

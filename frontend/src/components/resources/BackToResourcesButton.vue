<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ChevronLeftIcon } from '@heroicons/vue/20/solid'

const { cluster } = defineProps<{ cluster: string }>()

const router = useRouter()
const route = useRoute()

const returnRoute = computed(() => {
  const validRoutes = ['resources', 'resources-diagram-nodes', 'resources-diagram-cores']
  const queryRoute = route.query.returnTo as string
  return validRoutes.includes(queryRoute) ? queryRoute : 'resources'
})

function handleBackClick() {
  router.push({ name: returnRoute.value, params: { cluster } })
}
</script>

<template>
  <button
    @click="handleBackClick"
    type="button"
    class="ui-button-secondary self-start"
  >
    <ChevronLeftIcon class="-ml-0.5 h-5 w-5" aria-hidden="true" />
    Back to resources
  </button>
</template>

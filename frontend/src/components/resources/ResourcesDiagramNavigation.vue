<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useRouter } from 'vue-router'

const { cluster, currentView } = defineProps<{
  cluster: string
  currentView: 'nodes' | 'cores'
}>()

const router = useRouter()

function switchToNodes() {
  router.push({ name: 'resources-diagram-nodes', params: { cluster } })
}

function switchToCores() {
  router.push({ name: 'resources-diagram-cores', params: { cluster } })
}
</script>

<template>
  <div class="flex justify-center">
    <span class="ui-segmented-control">
      <button
        type="button"
        :class="[
          'ui-segmented-button',
          currentView === 'nodes' && 'ui-segmented-button-active'
        ]"
        @click="switchToNodes"
      >
        Nodes
      </button>
      <button
        type="button"
        :class="[
          'ui-segmented-button',
          currentView === 'cores' && 'ui-segmented-button-active'
        ]"
        @click="switchToCores"
      >
        Cores
      </button>
    </span>
  </div>
</template>

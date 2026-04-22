<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { getNodeGPU } from '@/composables/GatewayAPI'
import type { ClusterNode } from '@/composables/GatewayAPI'

const { node } = defineProps<{
  node: ClusterNode
}>()
const nodeGPU = getNodeGPU(node.gres)
</script>

<template>
  <span v-if="nodeGPU.length" class="text-gray-500">
    {{ nodeGPU.join(', ') }}
  </span>
  <span v-else class="text-gray-400">-</span>
</template>

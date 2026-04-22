<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { jobResourcesTRES, getMBHumanUnit } from '@/composables/GatewayAPI'
import type { ClusterTRES } from '@/composables/GatewayAPI'
import {
  ServerIcon,
  CpuChipIcon,
  TableCellsIcon,
  Square3Stack3DIcon
} from '@heroicons/vue/24/outline'

const { tres, gpu } = defineProps<{
  tres: ClusterTRES[]
  gpu: { count: number; reliable: boolean }
}>()

const resources = jobResourcesTRES(tres)
</script>

<template>
  <dd
    v-if="resources.node == -1 && resources.cpu == -1 && resources.memory == -1"
    class="mt-1 text-sm leading-6 text-[var(--color-brand-muted)] sm:col-span-2 sm:mt-0"
  >
    -
  </dd>
  <dd
    v-else
    class="mt-1 text-sm leading-6 text-[var(--color-brand-muted)] sm:col-span-2 sm:mt-0"
  >
    <ul class="space-y-2">
      <li>
        <span class="inline-flex items-center"
          ><ServerIcon class="mr-1 h-5 w-5" aria-hidden="true" />Nodes: {{ resources.node }}</span
        >
      </li>
      <li>
        <span class="inline-flex items-center"
          ><CpuChipIcon class="mr-1 h-5 w-5" aria-hidden="true" />CPU: {{ resources.cpu }}</span
        >
      </li>
      <li>
        <span class="inline-flex items-center"
          ><TableCellsIcon class="mr-1 h-5 w-5" aria-hidden="true" />Memory:
          {{ getMBHumanUnit(resources.memory) }}</span
        >
      </li>
      <li v-if="gpu.count > 0">
        <span class="inline-flex items-center"
          ><Square3Stack3DIcon class="mr-1 h-5 w-5" aria-hidden="true" />GPU:
          {{ gpu.count }}
          <span v-if="!gpu.reliable" class="ml-1 text-[var(--color-brand-muted)]">~</span></span
        >
      </li>
    </ul>
  </dd>
</template>

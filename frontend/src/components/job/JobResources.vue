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
    <ul class="space-y-2.5">
      <li>
        <span class="inline-flex items-center gap-2"
          ><span
            class="inline-flex h-8 w-8 items-center justify-center rounded-[14px] bg-[rgba(182,232,44,0.14)] text-[var(--color-brand-blue)] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]"
            ><ServerIcon class="h-4 w-4" aria-hidden="true" /></span
          ><span>Nodes: {{ resources.node }}</span></span
        >
      </li>
      <li>
        <span class="inline-flex items-center gap-2"
          ><span
            class="inline-flex h-8 w-8 items-center justify-center rounded-[14px] bg-[rgba(116,165,214,0.14)] text-[var(--color-brand-blue)] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]"
            ><CpuChipIcon class="h-4 w-4" aria-hidden="true" /></span
          ><span>CPU: {{ resources.cpu }}</span></span
        >
      </li>
      <li>
        <span class="inline-flex items-center gap-2"
          ><span
            class="inline-flex h-8 w-8 items-center justify-center rounded-[14px] bg-[rgba(80,105,127,0.12)] text-[var(--color-brand-blue)] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]"
            ><TableCellsIcon class="h-4 w-4" aria-hidden="true" /></span
          ><span>Memory: {{ getMBHumanUnit(resources.memory) }}</span></span
        >
      </li>
      <li v-if="gpu.count > 0">
        <span class="inline-flex items-center gap-2"
          ><span
            class="inline-flex h-8 w-8 items-center justify-center rounded-[14px] bg-[rgba(216,75,80,0.1)] text-[var(--color-brand-blue)] shadow-[inset_0_1px_0_rgba(255,255,255,0.7)]"
            ><Square3Stack3DIcon class="h-4 w-4" aria-hidden="true" /></span
          ><span
            >GPU: {{ gpu.count }}
            <span v-if="!gpu.reliable" class="ml-1 text-[var(--color-brand-muted)]">~</span></span
          ></span
        >
      </li>
    </ul>
  </dd>
</template>

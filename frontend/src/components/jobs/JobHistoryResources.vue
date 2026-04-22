<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import type { JobHistoryRecord } from '@/composables/GatewayAPI'
import { ServerIcon, CpuChipIcon, Square3Stack3DIcon } from '@heroicons/vue/24/outline'

const { job } = defineProps<{ job: JobHistoryRecord }>()

function countGPUTRESRequest(tresRequest: string): number {
  let total = 0
  for (const rawTres of tresRequest.split(',')) {
    let tres = rawTres.split('(')[0]
    tres = tres.replace('=', ':')
    const items = tres.split(':')
    if (!['gpu', 'gres/gpu'].includes(items[0])) continue
    const count = items.length === 2 ? parseInt(items[1]) : parseInt(items[2])
    if (!Number.isNaN(count)) total += count
  }
  return total
}

const gpu = job.gres_detail ? countGPUTRESRequest(job.gres_detail) : 0
</script>

<template>
  <span class="mr-2 inline-flex">
    <ServerIcon class="mr-0.5 h-5 w-5" aria-hidden="true" />
    {{ job.node_count ?? '-' }}
  </span>
  <span class="mr-2 inline-flex">
    <CpuChipIcon class="mr-0.5 h-5 w-5" aria-hidden="true" />
    {{ job.cpus ?? '-' }}
  </span>
  <span v-if="gpu > 0" class="inline-flex">
    <Square3Stack3DIcon class="mr-0.5 h-5 w-5" aria-hidden="true" />
    {{ gpu }}
  </span>
</template>

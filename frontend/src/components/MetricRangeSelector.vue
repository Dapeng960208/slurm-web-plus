<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import type { MetricRange } from '@/composables/GatewayAPI'

const range = defineModel<MetricRange>({ required: true })

defineProps<{
  ariaLabel?: string
}>()
</script>

<template>
  <span
    class="isolate inline-flex rounded-full shadow-[var(--shadow-soft)]"
    :aria-label="ariaLabel ?? 'Select metric range'"
  >
    <button
      type="button"
      :class="[
        range == 'week'
          ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
          : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
        'relative inline-flex items-center rounded-l-full px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
      ]"
      @click="range = 'week'"
    >
      week
    </button>
    <button
      type="button"
      :class="[
        range == 'day'
          ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
          : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
        'relative inline-flex items-center px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
      ]"
      @click="range = 'day'"
    >
      day
    </button>
    <button
      type="button"
      :class="[
        range == 'hour'
          ? 'bg-[linear-gradient(135deg,rgba(182,232,44,0.95),rgba(152,201,31,0.95))] text-[var(--color-brand-deep)]'
          : 'bg-white/90 text-[var(--color-brand-muted)] hover:bg-white',
        'relative inline-flex items-center rounded-r-full px-4 py-2 text-xs font-semibold ring-1 ring-[rgba(80,105,127,0.16)] ring-inset focus:z-10'
      ]"
      @click="range = 'hour'"
    >
      hour
    </button>
  </span>
</template>

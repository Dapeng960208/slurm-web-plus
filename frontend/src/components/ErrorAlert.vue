<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { XCircleIcon } from '@heroicons/vue/20/solid'

const { showErrorsLink = true } = defineProps<{ showErrorsLink?: boolean }>()
</script>

<template>
  <div
    class="rounded-[22px] border border-[rgba(216,75,80,0.16)] bg-[rgba(255,245,245,0.92)] p-4 shadow-[var(--shadow-soft)]"
  >
    <div class="flex">
      <div class="shrink-0 rounded-full bg-[rgba(216,75,80,0.12)] p-2">
        <XCircleIcon class="h-5 w-5 text-[var(--color-brand-danger)]" aria-hidden="true" />
      </div>
      <div class="ml-3 flex-1 md:flex md:justify-between">
        <p class="text-sm leading-6 text-[var(--color-brand-danger)]"><slot></slot></p>
        <p v-if="showErrorsLink" class="mt-3 text-sm md:mt-0 md:ml-6">
          <RouterLink
            :to="{ name: 'settings-errors' }"
            class="font-medium whitespace-nowrap text-[var(--color-brand-danger)] transition hover:opacity-80"
          >
            See Errors
            <span aria-hidden="true"> &rarr;</span>
          </RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

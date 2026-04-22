<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { InformationCircleIcon } from '@heroicons/vue/20/solid'
</script>

<template>
  <div
    class="ui-panel-soft rounded-[22px] border border-[rgba(80,105,127,0.1)] bg-[rgba(255,255,255,0.78)] p-4"
  >
    <div class="flex">
      <div class="shrink-0 rounded-full bg-[rgba(80,105,127,0.12)] p-2">
        <InformationCircleIcon class="h-5 w-5 text-[var(--color-brand-blue)]" aria-hidden="true" />
      </div>
      <p class="ml-3 text-sm leading-6 text-[var(--color-brand-blue)]"><slot></slot></p>
    </div>
  </div>
</template>

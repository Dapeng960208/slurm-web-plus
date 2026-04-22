<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { formatJobExitCode } from '@/composables/GatewayAPI'
import type { ClusterJobExitCode } from '@/composables/GatewayAPI'

const { exit_code } = defineProps<{ exit_code: ClusterJobExitCode }>()
</script>

<template>
  <dd class="mt-1 text-sm leading-6 text-gray-700 sm:col-span-2 sm:mt-0 dark:text-gray-300">
    {{ formatJobExitCode(exit_code) }}
  </dd>
</template>

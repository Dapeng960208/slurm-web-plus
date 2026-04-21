<!--
  Copyright (c) 2024 Rackslab

  This file is part of Slurm-web.

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

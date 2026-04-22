<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
withDefaults(
  defineProps<{
    label?: string
  }>(),
  {
    label: 'Loading chart'
  }
)
</script>

<template>
  <div class="ui-chart-skeleton" role="img" :aria-label="label">
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-1"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-2"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-3"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-4"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-5"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-6"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-7"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-8"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-9"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-10"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-11"></span>
    <span class="ui-chart-skeleton-bar ui-chart-skeleton-bar-12"></span>
  </div>
</template>

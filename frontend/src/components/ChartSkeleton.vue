<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    label?: string
  }>(),
  {
    label: 'components.chartSkeleton.loadingChart'
  }
)

const { t } = useI18n()
</script>

<template>
  <div class="ui-chart-skeleton" role="img" :aria-label="t(label)">
    <span class="ui-chart-skeleton-line ui-chart-skeleton-line-1"></span>
    <span class="ui-chart-skeleton-line ui-chart-skeleton-line-2"></span>
    <span class="ui-chart-skeleton-line ui-chart-skeleton-line-3"></span>
    <span class="ui-chart-skeleton-line ui-chart-skeleton-line-4"></span>
    <span class="ui-chart-skeleton-axis"></span>
    <span class="ui-chart-skeleton-plot">
      <span class="ui-chart-skeleton-point ui-chart-skeleton-point-1"></span>
      <span class="ui-chart-skeleton-point ui-chart-skeleton-point-2"></span>
      <span class="ui-chart-skeleton-point ui-chart-skeleton-point-3"></span>
      <span class="ui-chart-skeleton-point ui-chart-skeleton-point-4"></span>
      <span class="ui-chart-skeleton-point ui-chart-skeleton-point-5"></span>
      <span class="ui-chart-skeleton-point ui-chart-skeleton-point-6"></span>
    </span>
  </div>
</template>

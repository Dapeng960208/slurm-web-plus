<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
}>()
</script>

<template>
  <div class="ui-page-header">
    <div class="ui-page-copy">
      <p class="ui-page-kicker">Admin Center</p>
      <h1 class="ui-page-title">
        {{ title }}
      </h1>
      <p v-if="description" class="ui-page-description">
        {{ description }}
      </p>
    </div>
  </div>
</template>

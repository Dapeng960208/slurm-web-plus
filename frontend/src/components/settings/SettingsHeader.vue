<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  title: string
  description?: string
}>()

const { t } = useI18n()
</script>

<template>
  <div class="ui-page-header">
    <div class="ui-page-copy">
      <h1 class="ui-page-title">
        {{ t(title) }}
      </h1>
      <p v-if="description" class="ui-page-description">
        {{ t(description) }}
      </p>
    </div>
  </div>
</template>

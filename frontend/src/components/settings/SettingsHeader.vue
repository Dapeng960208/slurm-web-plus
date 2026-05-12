<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { translate } from '@/i18n/translate'

defineProps<{
  title: string
  description?: string
  titleParams?: Record<string, unknown>
  descriptionParams?: Record<string, unknown>
}>()

useI18n()
</script>

<template>
  <div class="ui-page-header">
    <div class="ui-page-copy">
      <h1 class="ui-page-title">
        {{ translate(title, titleParams) }}
      </h1>
      <p v-if="description" class="ui-page-description">
        {{ translate(description, descriptionParams) }}
      </p>
    </div>
  </div>
</template>

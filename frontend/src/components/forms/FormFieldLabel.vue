<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { InformationCircleIcon } from '@heroicons/vue/20/solid'

defineProps<{
  label: string
  required?: boolean
  hint?: string
  tooltip?: string
}>()
</script>

<template>
  <div>
    <div class="ui-form-label">
      <span class="ui-form-label-text">{{ label }}</span>
      <span
        :class="[
          'ui-form-badge',
          required ? 'ui-form-badge-required' : 'ui-form-badge-optional'
        ]"
      >
        {{ required ? 'Required' : 'Optional' }}
      </span>
      <span v-if="tooltip" class="ui-help-badge" :title="tooltip" :aria-label="tooltip">
        <InformationCircleIcon class="h-4 w-4" aria-hidden="true" />
      </span>
    </div>
    <p v-if="hint" class="ui-form-hint">
      {{ hint }}
    </p>
  </div>
</template>

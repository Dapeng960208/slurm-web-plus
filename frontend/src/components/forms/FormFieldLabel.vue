<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { InformationCircleIcon } from '@heroicons/vue/20/solid'

defineProps<{
  label: string
  required?: boolean
  hint?: string
  tooltip?: string
}>()

const { t } = useI18n()
</script>

<template>
  <div>
    <div class="ui-form-label">
      <span class="ui-form-label-text">{{ t(label) }}</span>
      <span
        :class="[
          'ui-form-badge',
          required ? 'ui-form-badge-required' : 'ui-form-badge-optional'
        ]"
      >
        {{ required ? t('common.forms.required') : t('common.forms.optional') }}
      </span>
      <span v-if="tooltip" class="ui-help-badge" :title="t(tooltip)" :aria-label="t(tooltip)">
        <InformationCircleIcon class="h-4 w-4" aria-hidden="true" />
      </span>
    </div>
    <p v-if="hint" class="ui-form-hint">
      {{ t(hint) }}
    </p>
  </div>
</template>

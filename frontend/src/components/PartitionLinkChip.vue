<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterLink } from 'vue-router'
import { useI18n } from 'vue-i18n'

defineProps<{
  cluster: string
  partition: string | null | undefined
}>()

const { t } = useI18n()
</script>

<template>
  <span v-if="!partition || partition === '-'" class="text-[var(--color-brand-muted)]">-</span>
  <RouterLink
    v-else
    :to="{ name: 'partition', params: { cluster, partition } }"
    class="ui-partition-link-chip"
    :title="t('common.navigation.openPartition', { partition })"
  >
    {{ partition }}
  </RouterLink>
</template>

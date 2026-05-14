<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { computed } from 'vue'
import type { ClusterJobComment } from '@/composables/GatewayAPI'

const { comment } = defineProps<{ comment: ClusterJobComment }>()

const entries = computed(() =>
  [
    comment.administrator ? { id: 'administrator', text: comment.administrator } : null,
    comment.system ? { id: 'system', text: comment.system } : null,
    comment.job ? { id: 'job', text: comment.job } : null
  ].filter((entry): entry is { id: string; text: string } => entry !== null)
)
</script>

<template>
  <div class="ui-detail-value-shell">
    <div v-if="entries.length" class="ui-detail-comment-stack">
      <div v-for="entry in entries" :key="entry.id" class="ui-detail-comment-entry">
        <div class="ui-detail-comment-label">{{ entry.id }}</div>
        <p class="ui-detail-comment-text">{{ entry.text }}</p>
      </div>
    </div>
    <p v-else class="ui-detail-rich-text">-</p>
  </div>
</template>

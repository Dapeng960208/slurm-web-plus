<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import type { ClusterJobComment } from '@/composables/GatewayAPI'

const { comment } = defineProps<{ comment: ClusterJobComment }>()
</script>

<template>
  <dd class="ui-detail-value-shell mt-1 sm:col-span-2 sm:mt-0">
    <div class="ui-detail-comment-stack">
      <div v-if="comment.administrator" class="ui-detail-comment-entry">
        <div class="ui-detail-comment-label">administrator</div>
        <p class="ui-detail-comment-text">{{ comment.administrator }}</p>
      </div>
      <div v-if="comment.system" class="ui-detail-comment-entry">
        <div class="ui-detail-comment-label">system</div>
        <p class="ui-detail-comment-text">{{ comment.system }}</p>
      </div>
      <div v-if="comment.job" class="ui-detail-comment-entry">
        <div class="ui-detail-comment-label">job</div>
        <p class="ui-detail-comment-text">{{ comment.job }}</p>
      </div>
    </div>
  </dd>
</template>

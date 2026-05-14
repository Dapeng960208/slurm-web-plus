<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import type { RouteLocationRaw } from 'vue-router'
import { RouterLink } from 'vue-router'

const {
  field,
  monospace = false,
  to
} = defineProps<{
  field: string | number
  monospace?: boolean
  to?: RouteLocationRaw
}>()
</script>

<template>
  <div class="ui-detail-value-shell">
    <RouterLink v-if="to" :to="to" class="ui-inline-link ui-detail-rich-text">
      {{ field }}
    </RouterLink>
    <pre v-else-if="monospace" class="ui-detail-codeblock">{{ field }}</pre>
    <p v-else class="ui-detail-rich-text">
      {{ field }}
    </p>
  </div>
</template>

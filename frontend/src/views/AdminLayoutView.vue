<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterView } from 'vue-router'
import ClusterMainLayout from '@/components/ClusterMainLayout.vue'

defineProps<{ cluster: string }>()
</script>

<template>
  <ClusterMainLayout menu-entry="admin" :cluster="cluster" :breadcrumb="[{ title: 'Admin' }]">
    <div class="ui-page ui-page-readable ui-content-workspace">
      <div class="ui-scroll-region min-h-0 flex-1 pr-1">
        <RouterView />
      </div>
    </div>
  </ClusterMainLayout>
</template>

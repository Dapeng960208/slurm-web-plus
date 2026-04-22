<!--
  Copyright (c) 2023-2026 Slurm Web Plus

  This file is part of Slurm Web Plus.

  SPDX-License-Identifier: MIT
-->

<script setup lang="ts">
import { RouterView } from 'vue-router'
import LeaveSettingsButton from '@/components/settings/LeaveSettingsButton.vue'
</script>
<template>
  <div class="ui-page mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
    <LeaveSettingsButton />
    <RouterView />
  </div>
</template>
